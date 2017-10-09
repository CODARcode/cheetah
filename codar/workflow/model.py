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
"""
import time
import subprocess
import os
import shutil
import math
import threading

from codar.workflow import status


STDOUT_NAME = 'codar.workflow.stdout'
STDERR_NAME = 'codar.workflow.stderr'
RETURN_NAME = 'codar.workflow.return'
WALLTIME_NAME = 'codar.workflow.walltime'


def _get_path(default_dir, default_name, specified_name):
    path = specified_name or default_name
    if not path.startswith("/"):
        path = os.path.join(default_dir, path)
    return path


class Run(threading.Thread):
    """Manage running a single executable within a pipeline. When start is
    called, it will launch the process with Popen and call wait in the new
    thread with a timeout, killing if the process does not finish in time."""
    def __init__(self, name, exe, args, env, working_dir, timeout=None,
                 nprocs=1, stdout_path=None, stderr_path=None,
                 return_path=None, walltime_path=None,
                 logger=None, log_prefix=None, sleep_after=None):
        threading.Thread.__init__(self, name="Thread-Run-" + name)
        self.name = name
        self.exe = exe
        self.args = args
        self.env = env or {}
        self.working_dir = working_dir
        self.timeout = timeout
        self.nprocs = nprocs
        self.stdout_path = _get_path(working_dir, STDOUT_NAME + "." + name,
                                     stdout_path)
        self.stderr_path = _get_path(working_dir, STDERR_NAME + "." + name,
                                     stderr_path)
        self.return_path = _get_path(working_dir, RETURN_NAME + "." + name,
                                     return_path)
        self.walltime_path = _get_path(working_dir, WALLTIME_NAME + "." + name,
                                       walltime_path)
        self.sleep_after = sleep_after
        self._p = None
        self._open_files = []

        self._start_time = None

        self._state_lock = threading.Lock()
        self._end_time = None # if set, run is done
        self._killed = False  # distinguish between natural done and killed
        self._timed_out = False # or timeout

        self.log_prefix = log_prefix or name
        self.logger = logger
        self.runner = None
        self.callbacks = set()

    def set_runner(self, runner):
        self.runner = runner

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
    def succeeded(self):
        """True if the run is done, finished normally, and had 0 return value.
        Raises ValueError if the run is not complete."""
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

    def run(self):
        if self.runner is not None:
            args = self.runner.wrap(self)
        else:
            args = [self.exe] + self.args
        self._start_time = time.time()
        self._popen(args)
        if self.logger is not None:
            self.logger.info('%s start %d %r', self.log_prefix, self._p.pid,
                             args)
        try:
            self._p.wait(self.timeout)
        except subprocess.TimeoutExpired:
            if self.logger is not None:
                self.logger.warn('%s killing (timeout %d)', self.log_prefix,
                                 self.timeout)
            self._p.kill()
            self._p.wait()
            with self._state_lock:
                self._end_time = time.time()
                if self._p.returncode != 0:
                    # check return code in case it completes while handling
                    # the exception before kill.
                    self._timed_out = True
        else:
            with self._state_lock:
                self._end_time = time.time()

        self._save_returncode(self._p.returncode)
        self._save_walltime(self._end_time - self._start_time)
        if self.logger is not None:
            self.logger.info('%s done %d %d', self.log_prefix, self._p.pid,
                             self._p.returncode)
        for callback in self.callbacks:
            callback(self)

    def kill(self):
        """Kill process and cause run thread to complete after the wait
        returns. If the run is already done, does nothing. If the process is
        killed, it will mark the state as killed so it can be re-run on
        workflow restart. Thread safe."""
        if self._p is None:
            raise ValueError('not running')

        with self._state_lock:
            if self._end_time is not None:
                # already finished naturally
                return
            self._killed = True

        if self.logger is not None:
            self.logger.warn('%s kill requested', self.log_prefix)
        self._p.kill()

    @classmethod
    def from_data(self, data):
        """Create Run instance from nested dictionary data structure, e.g.
        parsed from JSON. The keys 'name', 'exe', 'args' are required, all the
        other keys are optional and have the same names as the constructor
        args. Raises KeyError if a required key is missing."""
        # TODO: deeper validation
        r = Run(name=data['name'], exe=data['exe'], args=data['args'],
                env=data.get('env'), # dictionary of varname/varvalue
                working_dir=data['working_dir'],
                timeout=data.get('timeout'),
                nprocs=data.get('nprocs', 1),
                stdout_path=data.get('stdout_path'),
                stderr_path=data.get('stderr_path'),
                return_path=data.get('return_path'),
                walltime_path=data.get('walltime_path'),
                sleep_after=data.get('sleep_after'))
        return r

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
        env.update(self.env)
        self._p = subprocess.Popen(args, env=env, cwd=self.working_dir,
                                   stdout=out, stderr=err)

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
            raise ValueError('not running')
        return self._p.returncode

    def get_pid(self):
        if self._p is None:
            raise ValueError('not running')
        return self._p.pid

    def close(self):
        for f in self._open_files:
            f.close()
        self._open_files = []

    def set_logger(self, logger, log_prefix):
        self.logger = logger
        self.log_prefix = log_prefix

    def get_nodes_used(self, ppn):
        """Get number of nodes needed to run this app with the given number
        of process per node (ppn)."""
        return math.ceil(self.nprocs / ppn)


class Pipeline(object):
    def __init__(self, pipe_id, runs, kill_on_partial_failure=False,
                 post_process_script=None,
                 post_process_args=None,
                 post_process_stop_on_failure=False):
        self.id = pipe_id
        self.runs = runs
        self.kill_on_partial_failure = kill_on_partial_failure
        self.post_process_script = post_process_script
        self.post_process_args = post_process_args
        self.post_process_stop_on_failure = post_process_stop_on_failure

        self._state_lock = threading.Lock()
        self._running = False
        self._force_killed = False
        self._active_runs = set()

        self._pipe_thread = None
        self._post_thread = None
        self.done_callbacks = set()
        self.fatal_callbacks = set()
        self.total_procs = 0
        self.logger = None
        self.log_prefix = None
        for run in runs:
            self.total_procs += run.nprocs

    @classmethod
    def from_data(self, data):
        """Create Pipeline instance from dictionary data structure, containing
        at least "id" and "runs" keys. The "runs" key must have a list of dict,
        and each dict is parsed using Run.as_data.
        Raises KeyError if a required key is missing."""
        runs_data = data["runs"]
        if not isinstance(runs_data, list):
            raise ValueError("'runs' key must be a list of dictionaries")
        pipe_id = str(data["id"])
        runs = [Run.from_data(rd) for rd in runs_data]
        kill_on_partial_failure = data.get("kill_on_partial_failure", False)
        post_process_script = data.get("post_process_script")
        post_process_args = data.get("post_process_args", [])
        if not isinstance(post_process_args, list):
            raise ValueError("'post_process_args' must be a list")
        post_process_stop_on_failure = data.get("post_process_stop_on_failure")
        return Pipeline(pipe_id, runs=runs,
                    kill_on_partial_failure=kill_on_partial_failure,
                    post_process_script=post_process_script,
                    post_process_args=post_process_args,
                    post_process_stop_on_failure=post_process_stop_on_failure)

    def start(self, consumer, runner=None):
        # Mark all runs as active before they are actually started
        # in a separate thread, so other methods know the state.
        self.add_done_callback(consumer.pipeline_finished)
        self.add_fatal_callback(consumer.pipeline_fatal)
        with self._state_lock:
            for run in self.runs:
                run.set_runner(runner)
                run.add_callback(consumer.run_finished)
                run.add_callback(self.run_finished)
                self._active_runs.add(run)
            self._running = True

            # Next start pipeline runs in separate thread and return
            # immediately, so we can inject a wait time between starting runs.
            self._pipe_thread = threading.Thread(target=self._start)
            self._pipe_thread.start()

    def _start(self):
        """Start all runs in the pipeline, along with threads that monitor
        their progress and signal consumer when finished. Use join_all to
        wait until they are all finished."""
        for run in self.runs:
            run.start()
            if run.sleep_after:
                time.sleep(run.sleep_after)

    def run_finished(self, run):
        assert self._running
        run_done_callbacks = False
        with self._state_lock:
            self._active_runs.remove(run)
            if not self._active_runs:
                self.run_post_process_script()
                run_done_callbacks = True
            elif self.kill_on_partial_failure and run.get_returncode() != 0:
                if self.logger is not None:
                    self.logger.warn('%s run %s failed, killing remaining',
                                     self.log_prefix, run.name)
                # if configured, kill all runs in the pipeline if one of
                # them has a nonzero exit code. Still allow post process to
                # run if set.
                for run2 in self._active_runs:
                    run2.kill()

        # Note: must be done without lock, since callbacks may call
        # get_state or other methods that acquire lock.
        if run_done_callbacks:
            self._execute_done_callbacks()

    def run_post_process_script(self):
        if self.post_process_script is None:
            return None
        if self._force_killed:
            return None
        self._post_thread = threading.Thread(target=self._post_process_thread)
        self._post_thread.start()

    def _post_process_thread(self):
        args = [self.post_process_script] + self.post_process_args
        try:
            rval = subprocess.call(args)
        except subprocess.SubprocessError as e:
            if self.logger is not None:
                self.logger.warn(
                    "pipe '%s' failed to run post process script: %s",
                    self.id, str(e))
            rval = None
        if rval != 0 and self.post_process_stop_on_failure:
            self._execute_fatal_callbacks()

    def add_done_callback(self, fn):
        self.done_callbacks.add(fn)

    def remove_done_callback(self, fn):
        self.done_callbacks.remove(fn)

    def _execute_done_callbacks(self):
        # NOTE: must be called w/o any locks!
        for cb in self.done_callbacks:
            cb(self)

    def add_fatal_callback(self, fn):
        self.fatal_callbacks.add(fn)

    def remove_fatal_callback(self, fn):
        self.fatal_callbacks.remove(fn)

    def _execute_fatal_callbacks(self):
        # NOTE: must be called w/o any locks!
        for cb in self.fatal_callbacks:
            cb(self)

    def get_nodes_used(self, ppn):
        """Get number of nodes needed to run pipeline with the given number
        of process per node (ppn). Assumes each app run will gain exclusive
        access to the node, i.e. each app consumes at least one node, even if
        it doesn't use all available processes."""
        nodes = 0
        for run in self.runs:
            nodes += math.ceil(run.nprocs / ppn)
        return nodes

    def get_state(self):
        with self._state_lock:
            if not self._running:
                return status.PipelineState(self.id, status.NOT_STARTED)
            elif self._force_killed:
                return status.PipelineState(self.id, status.KILLED)
            elif self._active_runs:
                return status.PipelineState(self.id, status.RUNNING)
            # done
            return_codes = dict((r.name, r.get_returncode())
                                for r in self.runs)
            reason = status.REASON_SUCCEEDED
            for r in self.runs:
                # timeout reason takes priority over generic failure, it
                # means that it may succeed if re-run with a more
                # generous timeout or if it happens to run faster (in
                # case of non-deterministic runs).
                if r.timed_out:
                    reason = status.REASON_TIMEOUT
                    break
                if r.get_returncode() != 0:
                    reason = status.REASON_FAILED
            return status.PipelineState(self.id, status.DONE,
                                        reason, return_codes)

    def get_pids(self):
        assert self._running
        return [run.get_pid() for run in self.runs]

    def set_loggers(self, logger):
        self.logger = logger
        self.log_prefix = self.id
        for run in self.runs:
            run.set_logger(logger, "%s:%s" % (self.id, run.name))

    def force_kill_all(self):
        """
        Kill all runs and don't run post processing. Note that this call may
        block waiting for all runs to be started, to avoid confusing races.
        If the pipeline is already done, this does nothing. If one or more
        runs are still active, or have not yet been marked as finished, then
        it will mark the entire pipeline as killed so it can be re-run from
        scratch on a restart if desired.
        """
        assert self._running
        # Make sure _active_runs is fully populated by start thread.
        self._pipe_thread.join()
        with self._state_lock:
            if not self._active_runs:
                # already complete, don't kill
                return
            self._force_killed = True

        for run in self._active_runs:
            run.kill()

    def join_all(self):
        assert self._running
        self._pipe_thread.join()
        for run in self.runs:
            run.join()
        # Note: the _post_thread is set in the last run_finished
        # callback, which will be executed in one of the run threads
        # joined above, so this is guarenteed to be set if post process
        # has been configured and force kill was not called.
        if self._post_thread is not None:
            self._post_thread.join()


class Runner(object):
    def wrap(self, run):
        raise NotImplemented()


class MPIRunner(Runner):
    def __init__(self, exe, nprocs_arg):
        self.exe = exe
        self.nprocs_arg = nprocs_arg

    def wrap(self, run):
        exe_path = shutil.which(self.exe)
        if exe_path is None:
            raise ValueError('Could not find "%s" in path' % self.exe)
        return [exe_path, self.nprocs_arg, str(run.nprocs), run.exe] + run.args


mpiexec = MPIRunner('mpiexec', '-n')
aprun = MPIRunner('aprun', '-n')
