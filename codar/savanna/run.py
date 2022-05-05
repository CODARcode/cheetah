"""
Classes for tracking pipelines and the runs within each pipeline in separate
monitor threads that synchronize state.

Note that there is state tracked in these classes which is not available just
by looking at the return code. In particular, a run my be killed for several
different reasons: external signal, run timeout reached, other run in pipeline
failed (when kill on partial fail is set), or if the entire workflow is killed.

The goal here is to provide as much information as possible about why a
pipeline failed, to make an informed decision about whether it is worth
running again when the workflow is restarted, or if it's failure was more
permanent and not subject to outside forces like the job walltime expiring.

-------------------------------------------------------------------------------
#253:
We need the following features:
1. A user environment, such as a module load, should be enabled per app.
2. An app may further have environment variables that need to be set.
3. Support MPMD mode.

So, we have a launcher script that loads the global environment, and calls
the mpmd launcher command:
    module load gcc
    mpirun -n 1 ./app1.sh : -n 2 ./app2.sh

In each app.sh, now we can load the env vars:
    export OMP_NUM_THREADS=2
    ./app1

If we don't have a sh file for each app, the environment set in Popen gets
applied to all codes in the MPMD command, which is incorrect.
This approach ensures that env vars can be set per app in MPMD mode.
-------------------------------------------------------------------------------
"""

import time
import subprocess
import os
import shutil
import math
import threading
import signal
import logging
import json
import warnings
from queue import Queue
import psutil
import pdb
from pathlib import Path
import stat

from codar.savanna import tau, status, machines, summit_helper, \
    deepthought2_helper
from codar.savanna.error_messages import err_msg
from codar.savanna.exc import SavannaException
from codar.savanna.node_layout import NodeLayout, NodeConfig
from codar.savanna.utils import get_path, STDOUT_NAME, STDERR_NAME, \
    WALLTIME_NAME, RETURN_NAME
from codar.savanna.templates import EXE_LAUNCH_FILE_TEMPLATE
from codar.savanna.tau import Tau


RUN_ENVIRON_NAME = '.codar.savanna.{}.environment.json'
EXE_INFO_FNAME = '.codar.savanna.{}.exe.info.txt'

KILL_WAIT = 30
WAIT_DELAY_KILL = 30
WAIT_DELAY_GIVE_UP = 120


_log = logging.getLogger('codar.savanna.run')

class Run(threading.Thread):
    """Manage running a single executable within a pipeline. When start is
    called, it will launch the process with Popen and call wait in the new
    thread with a timeout, killing if the process does not finish in time."""
    def __init__(self, name, exe, args, sched_args, env,
                 user_env_file, working_dir, apps_dir,
                 machine, timeout=None, nprocs=1, res_set=None,
                 stdout_path=None, stderr_path=None,
                 return_path=None, walltime_path=None,
                 log_prefix=None, sleep_after=None,
                 depends_on_runs=None, hostfile=None,
                 runner_override=False,
                 tau_profiling=False, tau_tracing=False, tau_exec='tau_exec'):
        threading.Thread.__init__(self, name="Thread-Run-" + name)
        self.name = name
        self.exe = exe
        self.args = args
        if args: self.args = list(filter(None, args))
        self.sched_args = sched_args
        self.user_env_file = user_env_file
        self.env = env or {}
        self.working_dir = working_dir
        self.apps_dir = apps_dir
        self.machine = machine
        self.timeout = timeout
        self.nprocs = nprocs

        # A script to export user-defined env vars and call the app without
        # any scheduler args. This is the leaf node in the script invokations.
        self.app_sh = None

        # Get the path to the exe
        self._find_exe()

        # Check tau options and set self.exe to tau_exec
        self.tau_profiler = None
        if tau_profiling or tau_tracing:
            self._add_tau_support(tau_exec, tau_profiling, tau_tracing)
        self.tau_check_done = True

        # res_set, nrs, and rs_per_host represent resource_set definition,
        # total no. of resource sets, and the no. of resource sets per host
        # respectively. Reqd for Summit.
        self.res_set = res_set

        self.stdout_path = get_path(working_dir, STDOUT_NAME + "." +
                                    name, stdout_path)
        self.stderr_path = get_path(working_dir, STDERR_NAME + "." +
                                    name, stderr_path)
        self.return_path = get_path(working_dir, RETURN_NAME + "." +
                                    name, return_path)
        self.walltime_path = get_path(working_dir, WALLTIME_NAME + "." +
                                      name, walltime_path)
        self.sleep_after = sleep_after
        self._p = None
        self._pgid = None
        self._open_files = []

        self._start_time = None

        self._state_lock = threading.Lock()
        self._end_time = None # if set, run is done
        self._killed = False  # distinguish between natural done and killed
        self._timeout_pending = False # avoid double kill while waiting
                                      # on timeout
        self._timed_out = False # or timeout

        self._exception = False # or python exception in run method

        self.log_prefix = log_prefix or name
        self.runner = None
        self.callbacks = set()

        self._kill_thread = None

        # calculated by Pipeline based on node layout
        self.nodes = None
        self.tasks_per_node = None

        # Get a list of runs that self depends on
        self.depends_on_runs = depends_on_runs

        # mpi hostfile option
        self.hostfile = hostfile

        # nodes assigned needed for Summit
        self.nodes_assigned = None

        # node_config for node-sharing on summit
        self.node_config = None

        # erf_file needed for summit
        self.erf_file = None

        # rankfile for the DeepThought2 machine. Don't know where else to
        # put this option right now.
        self.dth_rankfile = None

        # An override option to launch the code without the machine runner (
        # aprun/jsrun/srun etc.
        self.runner_override = runner_override

        # For mpmd mode on machines such as Summit, keep a list of child runs
        self.child_runs = None

        # Add stdout and stderr redirection to args
        _args = self.args or []
        # Disable adding redirection to args. Causes issues with jsrun.
        # _args.extend(['>', self.stdout_path, '2>', self.stderr_path])
        self.args = _args

        # Create the launch command (e.g. mpirun -np 2 ./a.out), write it to
        # a script, and launch the script instead of running mpirun
        # directly. This way, a user specified env can be setup before the
        # app is launched. See #246.
        self.exe_launch_script_path = None

        # Slurm options that could be set after parsind node layout
        self.cpus_per_task = None
        self.threads_per_core = None
        self.tasks_per_gpu = None
        self.gpus_per_task = None

    @classmethod
    def from_data(cls, data):
        """Create Run instance from nested dictionary data structure, e.g.
        parsed from JSON. The keys 'name', 'exe', 'args' are required, all the
        other keys are optional and have the same names as the constructor
        args. Raises KeyError if a required key is missing."""
        # TODO: deeper validation
        r = Run(name=data['name'], exe=data['exe'], args=data['args'],
                sched_args=data['sched_args'],
                env=data.get('env'),  # dictionary of varname/varvalue
                user_env_file=data.get('env_file'),
                working_dir=data['working_dir'],
                machine=data['machine'],
                apps_dir=data['apps_dir'],
                timeout=data.get('timeout'),
                nprocs=data.get('nprocs', 1),
                res_set=data.get('res_set'),
                stdout_path=data.get('stdout_path'),
                stderr_path=data.get('stderr_path'),
                return_path=data.get('return_path'),
                walltime_path=data.get('walltime_path'),
                sleep_after=data.get('sleep_after'),
                depends_on_runs=data.get('after_rc_done'),
                hostfile=data.get('hostfile'),
                runner_override=data.get('runner_override'),
                tau_profiling=data.get('tau_profiling', False),
                tau_tracing=data.get('tau_tracing', False))

        return r

    @classmethod
    def mpmd_run(cls, runs):
        """
        Returns a new Run object
        """

        if len(runs) == 1:
            return runs

        # For Summit, just return runs. The ERF helper will handle it. For
        # other machines, return a single aggregated Run object

        # If any of the runs request their own environment, display message
        # that this cannot be done.
        for r in runs:
            if r.user_env_file is not None:
                warnings.warn("Cannot load per-app env_file in MPMD mode. "
                              "Ignoring {}. Consider the app_config_scripts "
                              "option to setup an environment."
                              "".format(r.user_env_file))
                r.user_env_file = None

        # if runs[0].machine.name.lower() == 'summit':
        # create a run object, name it 'mpmd', and add runs as child runs
        r = Run(name='mpmd', exe=None, args=None, sched_args=None,
                env=None, working_dir=runs[0].working_dir,
                machine=runs[0].machine, apps_dir=runs[0].apps_dir,
                timeout=runs[0].timeout, nprocs=None, res_set=None,
                stdout_path=None, stderr_path=None, return_path=None,
                walltime_path=None, sleep_after=None, user_env_file=None,
                depends_on_runs=None, hostfile=None, runner_override=None)

        # Pipeline sets the machine for its runs, so you have to
        # explicitly do it here as well.
        r.machine = runs[0].machine

        r.child_runs = runs
        # return r

        # this is for regular mpmd launches that where the launch command is
        # a ':' separated list of individual app launches
        # mpmd_args = runs[0].args
        # for run in runs[1:]:
        #     run_args = run.runner.wrap(run, run.sched_args)
        #     del run_args[0]
        #     mpmd_args.extend(":")
        #     mpmd_args.extend(run_args)
            # no need to set run.nodes = sum(child run.nodes)

        # r = runs[0]
        # r.args = mpmd_args
        return r

    def app_sh_setup(self):
        """
        Create a bash script that sets any environment variables defined in
        ParamEnvVar, and call the main app without MPI args.
        A launcher script *launch.sh sets the environment for an app and calls
        the app script. e.g. mpirun -np 2 ./app.sh.
        See #253 and its related documentation above.
        # tau_exec should be included here
        """

        assert self.exe is not None
        assert self.tau_check_done

        # Create the file contents
        # 1. export user-defined and tau env vars
        outstr = "#!/bin/bash\n\n"
        for k,v in self.env.items():
            outstr += "export {}={}\n".format(k,v)
        if self.tau_profiler:
            for k,v in self.tau_profiler.env.items():
                outstr += "export {}={}\n".format(k, v)

        # 2. Call the app executable along with its args
        outstr += "\n" + self.exe + " "
        if self.args:
            outstr += ' '.join(self.args)

        # Write contents out in to app_sh
        app_sh_path = Path.joinpath(Path(self.working_dir),
                                    ".codar.savanna.{}.sh".format(self.name))

        with open(app_sh_path, "w") as f:
            f.write(outstr)
        app_sh_path.chmod(app_sh_path.stat().st_mode | stat.S_IEXEC)

        self.app_sh = str(app_sh_path.absolute())

    def _add_tau_support(self, tau_exec, tau_profiling, tau_tracing):
        """
        Create a Tau object and set the exe to tau_exec
        """

        self.tau_profiler = Tau(tau_exec, tau_profiling, tau_tracing,
                                self.working_dir, self.name)

        # Adjust self's exe and paths. Set exe to tau_exec
        assert self.exe is not None
        _args = [self.exe] + self.args
        self.args = _args.copy()
        self.exe = self.tau_profiler.tau_exec

    def set_runner(self, runner):
        self.runner = runner
        if self.runner_override:
            self.runner = None

    @property
    def timed_out(self):
        """True if the run is done and was killed because it exceeded the
        specified run timeout. Raises ValueError if the run is not complete."""
        if self._end_time is None:
            raise ValueError("timed out state not available until run is done")
        return self._timed_out

    @property
    def killed(self):
        """True if the run is done and the kill method was called. Note that
        this will _NOT_ be true if an external kill signal caused the process
        to exit. Raises ValueError if the run is not complete."""
        if self._end_time is None:
            raise ValueError("killed state not available until run is done")
        return self._killed

    @property
    def exception(self):
        """True if there was a python exception in the run method. When this
        is the case, the state of the underlying process is unknown - it may
        have been started or not."""
        return self._exception

    @property
    def succeeded(self):
        """True if the run is done, finished normally, and had 0 return value.
        Raises ValueError if the run is not complete."""
        if self._exception:
            return False
        if self._end_time is None:
            raise ValueError("succeeded state not available until run is done")
        return (not self._killed and not self._timed_out
                and self._p.returncode == 0)

    def add_callback(self, fn):
        """Function takes single argument which is this run instance, and is
        called when the process is complete (either normally or killed by
        timeout). Callbacks must not block."""
        self.callbacks.add(fn)

    def remove_callback(self, fn):
        self.callbacks.remove(fn)

    def _find_exe(self):
        """
        Find the absolute path of the exe in the app dir pointed to by -a
        during campaign creation time, or in $PATH.
        $PATH takes precedence over apps_dir.
        """

        # Fucking exception for MPMD mode on Summit. The top-level run
        # object is an empty placeholder, so its exe is None. The actual runs
        # are in its child runs.
        if self.exe is None:
            return

        env = os.environ.copy()
        env['PATH'] = self.apps_dir + ":" + env['PATH']
        env.update(self.env)

        exe_path = shutil.which(self.exe, path=env['PATH'])
        if exe_path is not None:
            self.exe = exe_path

        # # Write the exe path to file
        # --- We really don't need this. ---
        # exe_info_file = self.working_dir + "/" + \
        #                 EXE_INFO_FNAME.format(self.name)
        # with open(exe_info_file, 'w') as f:
        #     f.write(self.exe)

    def _set_slurm_opts(self):
        """
        Set slurm options cpus_per_task, threads_per_code, tasks_per_gpu,
        and gpus_per_task required if this is a Slurm machine
        Entry into this function is because self.node_config is not None.
        @TODO: Put this into a Slurm adapter.
        """

        # 1. cpus per task.
        self.cpus_per_task = len(self.node_config.cpu[0])

        # 2. GPUs per task
        if len(self.node_config.gpu) == 0: return
        self.gpus_per_task = len(self.node_config.gpu[0])

        # 3. Tasks per gpu
        # Commenting out as ntasks_per_gpu does not exist in Slurm 
        # even though OLCF docs say so
        # tasks_per_gpu = {}
        # for gpumap in self.node_config.gpu:
        #     for gpuid in gpumap:
        #         if gpuid not in tasks_per_gpu:
        #             tasks_per_gpu[gpuid] = 0
        #         tasks_per_gpu[gpuid] = tasks_per_gpu[gpuid] + 1
        # l = list(tasks_per_gpu.values())
        # self.tasks_per_gpu = l[0]

    def run(self):
        try:
            self._run()
        except:
            # Treat this as a special type of failure, in case it's
            # something specific to this run or pipeline. If it affects
            # all pipelines, then they should all eventually fail.
            # We could force a workflow kill in this case, but this less
            # drastic approach may provide extra information and won't
            # take much longer.
            self._exception = True  # Note: state lock not required
            _log.exception('exception in Run thread')
            # attempt to execute callbacks, so more threads could be run
            try:
                self._run_callbacks()
            except:
                _log.exception(
                       'exception in Run callbacks after Run thread exception')

    def _run(self):
        # Wait for runs that self depends on to finish
        if self.depends_on_runs is not None:
            threading.Thread.join(self.depends_on_runs)

        # Create ERF file for Summit
        if self.machine.name.lower() == 'summit':
            self.erf_file = self.working_dir + "/" + self.name + ".erf_input"

            # for mpmd runs
            if self.child_runs is not None:
                summit_helper.create_erf_file_mpmd(self)
            else:
                if self.runner is not None:
                    summit_helper.create_erf_file(self)

        if 'deepthought2' in self.machine.name.lower():
            if self.node_config is not None:
                self.dth_rankfile = self.working_dir + '/' + self.name + \
                                    ".rankfile"
                deepthought2_helper.create_rankfile(self)

        if self.node_config is not None:
            self._set_slurm_opts()  # Set slurm opts if this is a Slurm machine

        # if self.machine.name.lower() == 'summit':
        #     # are we releasing when the run finishes, or when the pipeline
        #     # finishes? reqd. for dependency mgmt
        #     self.add_callback(self._release_nodes)

        if self.runner is not None:
            args = self.runner.wrap(self, self.sched_args)
        else:
            args = [self.app_sh]

        # Write args to the launch script, and launch this script. #246
        self._create_launch_script(' '.join(args))
        args = ['bash', self.exe_launch_script_path]

        self._start_time = time.time()
        with self._state_lock:
            if self._killed:
                _log.info('%s not starting, killed before start',
                          self.log_prefix)
                self._end_time = time.time()
            else:
                self._popen(args)
        if self._p is None:
            self._run_callbacks()
            return

        try:
            self._p.wait(self.timeout)
        except subprocess.TimeoutExpired:
            _log.warning('%s killing (timeout %d)', self.log_prefix,
                         self.timeout)
            with self._state_lock:
                self._timeout_pending = True
            if not self._killed:
                self._term_kill()
                self._p.wait()
                with self._state_lock:
                    if self._p.returncode != 0:
                        # check return code in case it completes while handling
                        # the exception before kill.
                        self._timed_out = True
                    self._timeout_pending = False
                    # TODO will this call the release_nodes callback?

        self._pgroup_wait()
        with self._state_lock:
            self._end_time = time.time()
        _log.info('%s done %d %d', self.log_prefix, self._p.pid,
                  self._p.returncode)
        self._save_walltime(self._end_time - self._start_time)
        self._save_returncode(self._p.returncode)
        self._close_files()
        self._run_callbacks()

    def _run_callbacks(self):
        _log.debug('%s _run_callbacks', self.log_prefix)
        for callback in self.callbacks:
            callback(self)

    def kill(self):
        """Kill process and cause run thread to complete after the wait
        returns. If the run is already done, does nothing. If the process is
        killed, it will mark the state as killed so it can be re-run on
        workflow restart. Thread safe."""
        with self._state_lock:
            if self._killed:
                # avoid double kill - there is a delay between this
                # being called and end_time being set, and kill after
                # partial failure can result in multiple async calls
                return
            if self._timeout_pending:
                return
            if self._end_time is not None:
                # already finished naturally
                return
            self._killed = True

        if self._p is not None:
            _log.warning('%s kill requested', self.log_prefix)
            self._kill_thread = threading.Thread(target=self._term_kill)
            self._kill_thread.start()

    def _term_kill(self):
        """Issue signals to entire process group. First give processes a
        chance to exit cleanly with CONT+TERM, then attempt to KILL after
        a delay."""
        _log.debug('%s _term_kill', self.log_prefix)
        try:
            os.killpg(self._pgid, signal.SIGCONT)
            os.killpg(self._pgid, signal.SIGTERM)
            time.sleep(KILL_WAIT)
            os.killpg(self._pgid, signal.SIGKILL)
        except ProcessLookupError:
            # this happens if all processes in the pgroup have already
            # exited and the group no longer exists, which is what should
            # happen in most cases
            pass

    def _pgroup_wait(self):
        """Wait until the process group lead by this run no longer exists.
        Assumes that it should already be exiting normally (e.g. the parent
        has already exited). If WAIT_DELAY_KILL is reached in expontential
        back off and the group still exists, SIGKILL is sent to the group.
        If WAIT_DELAY_GIVE_UP is reached, an error is logged and the function
        will return. Inspired by proctrack_pgid plugin from slurm."""
        _log.debug('%s _pgroup_wait max delay %d'
                   % (self.log_prefix, WAIT_DELAY_GIVE_UP))
        delay = 1
        signum = 0  # 0 is the null signal, does error checking only
        while True:
            try:
                os.killpg(self._pgid, signum)
            except ProcessLookupError:
                # pgroup no longer exists, we are done waiting
                _log.debug('%s Checking if pgroup exists .. not found', 
                           self.log_prefix)
                break
            # else pgroup still exists
            time.sleep(delay)
            delay *= 2
            if delay > WAIT_DELAY_KILL:
                signum = signal.SIGKILL
                _log.warning('%s pgroup still exists, sending KILL, '
                             'next delay=%d', self.log_prefix, delay)
            if delay > WAIT_DELAY_GIVE_UP:
                _log.error('%s pgroup did not exit', self.log_prefix)
                break

    def _create_launch_script(self, app_launch_command):
        """
        Create a launch script that will be launched as `bash
        thisscript.sh`, instead of directly launching an executable using
        e.g. mpirun -np 2 ./a.out
        Related to #246, wherein users need to set their own env before
        running an application.
        """

        exe_launch_fpath = ".codar.savanna.{}.launch.sh".format(self.name)
        self.exe_launch_script_path = \
                os.path.join(self.working_dir, exe_launch_fpath)

        # 1. Read the user-specified env
        userenv = ":"  # bash no-op
        if self.user_env_file is not None:
            try:
                with open(self.user_env_file, "r") as f:
                    userenv = f.read()
            except:
                raise SavannaException(
                    "Could not read {}".format(self.user_env_file))

        # 2. Create the application launcher script
        try:
            with open(self.exe_launch_script_path, "w") as f:
                s = EXE_LAUNCH_FILE_TEMPLATE.format(
                    user_defined_env_setup = userenv,
                    app_launch_command = app_launch_command)
                f.write(s)
        except:
            e = err_msg['f_creat'].format(self.exe_launch_script_path)
            raise SavannaException(e)

    def _popen(self, args):
        out = open(self.stdout_path, 'w')
        err = open(self.stderr_path, 'w')
        self._open_files = [out, err]
        # NOTE: it's important to maintain the calling environment,
        # which can contain LD_LIBRARY_PATH and other variables that are
        # required for modules and normal HPC operation (e.g aprun).
        # TODO: should this do a smart merge per variable, so you could
        # e.g. extend PATH or LD_LIBRARY_PATH rather tha replace it?
        env = os.environ.copy()
        env['PATH'] = self.apps_dir + ":" + env['PATH']
        # env.update(self.env)

        # Write the environment information to file
        env_out_name = RUN_ENVIRON_NAME.format(self.name)
        env_out_path = os.path.join(self.working_dir, env_out_name)
        try:
            with open(env_out_path, 'w') as f:
                json.dump(env, f, indent=4)
        except:  # Continue if it fails, not fatal
            _log.warning(err_msg['rc_env_out_fail'].format(self.name,
                                                           env_out_path))

        _log.debug("{} {}, LD_LIBRARY_PATH:{}".format(
            self.log_prefix, self.env, env.get('LD_LIBRARY_PATH', '')))

        # Flatten the args into a single string, and redirect stdout and
        # stderr using bash options > and 2> . Can't use stdout and stderr in
        # Popen because mpmd mode which has a single long command redirects
        # all applications' output to a single file. Set shell=True in the
        # Popen call. Doesn't work for Summit with ERF files. See #201

        # -------------------------------------------------------------------#
        # #241 Broken erf functionality. I am disabling redirection of
        # stdout and stderr, which causes all runs to redirect to the same
        # file when run under MPMD mode. Note that without erf, codes are
        # NOT written to a shell script first before running.

        # if self.machine.name.lower() != 'summit':
        #     _args = args
        #     args = ' '.join(_args)
        #     self._p = subprocess.Popen(args, env=env, cwd=self.working_dir,
        #                                shell=True, preexec_fn=os.setpgrp)
        # else:
        self._p = subprocess.Popen(args, env=env, cwd=self.working_dir,
                                   stdout=out, stderr=err,
                                   preexec_fn=os.setpgrp)

        self._pgid = os.getpgid(self._p.pid)

        _log.info('%s start pid=%d pgid=%d args=%r',
                  self.log_prefix, self._p.pid, self._pgid, args)

    def _save_returncode(self, rcode):
        assert rcode is not None
        with open(self.return_path, 'w') as f:
            f.write(str(rcode) + "\n")

    def _save_walltime(self, walltime):
        # TODO: put in JSON file along with return code instead of
        # separate files?
        with open(self.walltime_path, 'w') as f:
            f.write(str(walltime) + "\n")

    def get_returncode(self):
        if self._p is None:
            return None
        return self._p.returncode

    def get_pid(self):
        if self._p is None:
            raise ValueError('not running')
        return self._p.pid

    def _close_files(self):
        for f in self._open_files:
            f.close()
        self._open_files = []

    def join(self):
        threading.Thread.join(self)
        if self._kill_thread is not None:
            self._kill_thread.join()

    def get_nodes_used(self):
        """Get number of nodes needed to run this app. Requires that the
        pipeline set_ppn method has been called to set this and tasks_per_node
        on each run."""
        return self.nodes

    def _release_nodes(self):
        pass

    def create_node_config(self):
        pass
