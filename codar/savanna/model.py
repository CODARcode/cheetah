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
import math
import threading
import signal
import logging
from queue import Queue
import copy
import pdb

from codar.savanna import status, machines, summit_helper, deepthought2_helper
from codar.savanna.exc import SavannaException
from codar.savanna.node_layout import NodeLayout


STDOUT_NAME = 'codar.workflow.stdout'
STDERR_NAME = 'codar.workflow.stderr'
RETURN_NAME = 'codar.workflow.return'
WALLTIME_NAME = 'codar.workflow.walltime'

KILL_WAIT = 30
WAIT_DELAY_KILL = 30
WAIT_DELAY_GIVE_UP = 120


_log = logging.getLogger('codar.savanna.model')


def _get_path(default_dir, default_name, specified_name):
    path = specified_name or default_name
    if not path.startswith("/"):
        path = os.path.join(default_dir, path)
    return path


class NodeConfig:
    def __init__(self):
        """
        Intended to look like
        cpu = [ 0=[], 1=[], 2=[], 3=[] ]
        gpu = [ 0=[], 1=[], 2=[], 3=[] ]
        """
        self.num_ranks_per_node = 0
        self.cpu = []
        self.gpu = []


class Run(threading.Thread):
    """Manage running a single executable within a pipeline. When start is
    called, it will launch the process with Popen and call wait in the new
    thread with a timeout, killing if the process does not finish in time."""
    def __init__(self, name, exe, args, sched_args, env, working_dir,
                 timeout=None, nprocs=1, res_set=None,
                 stdout_path=None, stderr_path=None,
                 return_path=None, walltime_path=None,
                 log_prefix=None, sleep_after=None,
                 depends_on_runs=None, hostfile=None,
                 runner_override=False):
        threading.Thread.__init__(self, name="Thread-Run-" + name)
        self.name = name
        self.exe = exe
        self.args = args
        self.sched_args = sched_args
        self.env = env or {}
        self.working_dir = working_dir
        self.timeout = timeout
        self.nprocs = nprocs

        # res_set, nrs, and rs_per_host represent resource_set definition,
        # total no. of resource sets, and the no. of resource sets per host
        # respectively. Reqd for Summit.
        self.res_set = res_set

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

        self.machine = None

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
                working_dir=data['working_dir'],
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
                runner_override=data.get('runner_override'))

        return r

    @classmethod
    def mpmd_run(cls, runs):
        """
        Returns a new Run object
        """

        # For Summit, just return runs. The ERF helper will handle it. For
        # other machines, return a single aggregated Run object

        if runs[0].machine.name.lower() == 'summit':
            # create a run object, name it 'mpmd', and add runs as child runs
            r = Run(name='mpmd', exe=None, args=None, sched_args=None,
                    env=runs[0].env, working_dir=runs[0].working_dir,
                    timeout=runs[0].timeout, nprocs=None, res_set=None,
                    stdout_path=None, stderr_path=None, return_path=None,
                    walltime_path=None, sleep_after=None,
                    depends_on_runs=None, hostfile=None, runner_override=None)

            # Pipeline sets the machine for its runs, so you have to
            # explicitly do it here as well.
            r.machine = runs[0].machine

            r.child_runs = runs
            return r

        if len(runs) == 1:
            return runs

        # this is for regular mpmd launches that where the launch command is
        # a ':' separated list of individual app launches
        mpmd_args = runs[0].args
        for run in runs[1:]:
            run_args = run.runner.wrap(run)
            del run_args[0]
            mpmd_args.extend(":")
            mpmd_args.extend(run_args)
            # no need to set run.nodes = sum(child run.nodes)

        r = runs[0]
        r.args = mpmd_args
        return r

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

        if self.machine.name.lower() == 'summit':
            self.erf_file = self.working_dir + "/" + self.name + ".erf_input"

            # for mpmd runs
            if self.child_runs is not None:
                summit_helper.create_erf_file_mpmd(self)
            else:
                summit_helper.create_erf_file(self)

        if 'deepthought2' in self.machine.name.lower():
            if self.node_config is not None:
                self.dth_rankfile = self.working_dir + '/' + self.name + \
                                    ".rankfile"
                deepthought2_helper.create_rankfile(self)

        # if self.machine.name.lower() == 'summit':
        #     # are we releasing when the run finishes, or when the pipeline
        #     # finishes? reqd. for dependency mgmt
        #     self.add_callback(self._release_nodes)

        if self.runner is not None:
            args = self.runner.wrap(self, self.sched_args)
        else:
            args = [self.exe] + self.args

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
        _log.info('%s start pid=%d pgid=%d args=%r',
                  self.log_prefix, self._p.pid, self._pgid, args)
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
        os.killpg(self._pgid, signal.SIGCONT)
        os.killpg(self._pgid, signal.SIGTERM)
        time.sleep(KILL_WAIT)
        try:
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
        _log.debug('%s LD_LIBRARY_PATH=%s', self.log_prefix,
                   env.get('LD_LIBRARY_PATH', ''))
        self._p = subprocess.Popen(args, env=env, cwd=self.working_dir,
                                   stdout=out, stderr=err,
                                   preexec_fn=os.setpgrp)
        self._pgid = os.getpgid(self._p.pid)

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

    def close(self):
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


class Pipeline(object):
    def __init__(self, pipe_id, runs, working_dir, total_nodes, machine_name,
                 kill_on_partial_failure=False,
                 post_process_script=None,
                 post_process_args=None,
                 post_process_stop_on_failure=False,
                 node_layout=None, launch_mode=None):
        self.id = pipe_id
        self.runs = runs
        self.working_dir = working_dir
        self.kill_on_partial_failure = kill_on_partial_failure
        self.post_process_script = post_process_script
        self.post_process_args = post_process_args
        self.post_process_stop_on_failure = post_process_stop_on_failure
        self.node_layout = node_layout
        self.machine_name = machine_name

        self._state_lock = threading.Lock()
        self._running = False
        self._force_killed = False
        self._active_runs = set()

        self._pipe_thread = None
        self._post_thread = None
        self.done_callbacks = set()
        self.fatal_callbacks = set()
        self.total_procs = 0
        self.log_prefix = self.id
        for run in runs:
            self.total_procs += run.nprocs
            run.log_prefix = "%s:%s" % (self.id, run.name)
            run.machine = machines.get_by_name(machine_name)
        # requires ppn to determine, in case node layout is not specified
        self.total_nodes = total_nodes
        self.launch_mode = launch_mode

        # List of node IDs assigned to this pipeline. Get initialized in
        # start()
        self.nodes_assigned = Queue()

        # Keep a copy of the nodes assigned. Pop nodes from this queue to
        # assign to Runs. When a Run is done, it can push the node back into
        # this queue, but Runs that share nodes may add the same node to the
        # Queue multiple times. We need a SetQueue for this, or a way to
        # have all Runs in a shared node release nodes just once.
        self._nodes_assigned = Queue()

        # Reorder the runs list so that runs are listed according to their
        # dependencies
        self.reorder_runs_by_dependencies()

        # TODO: ensure that all the node layouts contain either a virtual
        #  node object or a regular codename:ppn mapping
        # self._validate_node_layout()

    @classmethod
    def from_data(cls, data):
        """Create Pipeline instance from dictionary data structure, containing
        at least "id" and "runs" keys. The "runs" key must have a list of dict,
        and each dict is parsed using Run.from_data.
        Raises KeyError if a required key is missing."""
        runs_data = data["runs"]
        working_dir = data["working_dir"]
        # Run working dir defaults to pipeline working dir, and can be
        # specified relative to pipeline working dir.
        for rd in runs_data:
            run_working_dir = rd.get("working_dir")
            if run_working_dir is None:
                run_working_dir = working_dir
            elif not run_working_dir.startswith("/"):
                run_working_dir = os.path.join(working_dir, run_working_dir)
            rd["working_dir"] = run_working_dir
        if not isinstance(runs_data, list):
            raise ValueError("'runs' key must be a list of dictionaries")
        pipe_id = str(data["id"])
        runs = [Run.from_data(rd) for rd in runs_data]

        # Get run objects on which each run depends
        # Replace run names in depends_on_runs with object references
        for run in runs:
            if run.depends_on_runs is not None:
                for tmp_run in runs:
                    if run.depends_on_runs == tmp_run.name:
                        run.depends_on_runs = tmp_run
                        break
                assert run.depends_on_runs is not None, \
                    "Internal failure in dependency management"

        launch_mode = data.get("launch_mode")
        kill_on_partial_failure = data.get("kill_on_partial_failure", False)
        post_process_script = data.get("post_process_script")
        post_process_args = data.get("post_process_args", [])
        if not isinstance(post_process_args, list):
            raise ValueError("'post_process_args' must be a list")
        post_process_stop_on_failure = data.get("post_process_stop_on_failure")
        node_layout = data.get("node_layout")
        total_nodes = data.get("total_nodes")
        machine_name = data.get("machine_name")
        return Pipeline(pipe_id, runs=runs, working_dir=working_dir,
                        kill_on_partial_failure=kill_on_partial_failure,
                        post_process_script=post_process_script,
                        post_process_args=post_process_args,
                        post_process_stop_on_failure=
                        post_process_stop_on_failure,
                        node_layout=node_layout,
                        launch_mode=launch_mode,
                        total_nodes=total_nodes,
                        machine_name=machine_name)

    def reorder_runs_by_dependencies(self):
        """
        Reorder the runs list so that runs appear in the order in which they
        must be launched.
        This requires parsing their dependencies information.

        Keep iterating through the runs list, finding the root-level run at
        every iteration (one with no dependencies) until all runs are examined.
        Watch out for cyclic dependencies.

        This algorithm will work as far as there is only one code on which a
        code can depend on.
        """
        ordered_runs = []
        while len(ordered_runs) < len(self.runs):
            cyclic_dep = True

            # first retrieve all runs with no dependencies
            for run in self.runs:
                if run in ordered_runs:
                    continue
                if run.depends_on_runs is None:
                    cyclic_dep = False
                    ordered_runs.append(run)

            # now get all runs whose depends_on are in ordered_runs
            # this order of processing is important
            for run in self.runs:
                if run in ordered_runs:
                    continue
                if run.depends_on_runs in ordered_runs:
                    cyclic_dep = False
                    ordered_runs.append(run)

            assert not cyclic_dep, "Cyclic dependency found amongst " \
                                   "applications"

        self.runs = ordered_runs

    def start(self, consumer, nodes_assigned, runner=None):
        # Mark all runs as active before they are actually started
        # in a separate thread, so other methods know the state.

        for node_name in nodes_assigned:
            self.nodes_assigned.put(node_name)
            # self.nodes_assigned.put(machine.node_class(node_name))

        # Make a copy of the nodes_assigned. copy.deepcopy does not work
        # self._nodes_assigned = copy.deepcopy(self.nodes_assigned)
        for node in list(self.nodes_assigned.queue):
            self._nodes_assigned.put(node)

        self.add_done_callback(consumer.pipeline_finished)
        self.add_fatal_callback(consumer.pipeline_fatal)

        with self._state_lock:
            for run in self.runs:
                run.set_runner(runner)

            # Parse the node layout and set the run information.
            # This requires self.nodes_assigned.
            # Summit and DeepThought2 support VirtualNode interfaces
            # Note that the NodeConfig/VirtualNode objects have not been
            # created at this point, so use the following to check the node
            # layout type. This must be done before an mpmd run obj is created.
            layout_type = self.node_layout[0].get('__info_type__') or None
            if layout_type == 'NodeConfig':
                self._parse_node_layouts()

            launch_mode = self.launch_mode or 'None'
            if launch_mode.lower() == 'mpmd':
                mpmd_run = Run.mpmd_run(self.runs)
                mpmd_run.nodes = self.total_nodes
                self.runs = [mpmd_run]

            for run in self.runs:
                run.set_runner(runner)

                # Commenting out the callback to consumer.run_finished that
                # releases the nodes held by a run.
                # Now this is called when the pipeline finishes

                # run.add_callback(consumer.run_finished)

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

        _log.debug("Pipeline {} launching run components".format(self.id))
        for run in self.runs:
            run.start()
            if run.sleep_after:
                time.sleep(run.sleep_after)

    def _parse_node_layouts(self):
        """Only for Summit right now."""

        # for layout in self.node_layout:
        #     self._parse_node_layout(layout)

        # get a list containing a list of codes on the same node
        codes_on_node = []
        for layout in self.node_layout:
            codes_on_node.append(list(self._extract_codes_on_node(layout)))

        # check for dependencies and re-arrange codes in this list
        self._rearrange_codes_by_dependencies(codes_on_node)

        # Get num nodes required to run this layout
        for l in codes_on_node:
            if len(l) == 0:
                continue

            num_nodes_reqd_for_layout = max([code.nodes for code in l])

            # Ensure required nodes are available
            num_nodes_in_queue = len(list(self._nodes_assigned.queue))
            assert num_nodes_in_queue >= num_nodes_reqd_for_layout, \
                "Do not have sufficient nodes to run the layout. " \
                "Need {}, found {}".format(num_nodes_reqd_for_layout,
                                           num_nodes_in_queue)

            # Get a list of nodes required for this run
            nodes_assigned_to_layout = []
            for i in range(num_nodes_reqd_for_layout):
                nodes_assigned_to_layout.append(self._nodes_assigned.get())

            # Assign nodes to runs
            for run in l:
                run.nodes_assigned = nodes_assigned_to_layout

    def _extract_codes_on_node(self, layout_info):
        """
        Gets the unique codes on the node.
        Also sets the no. of nodes required by each code.
        """

        codes_on_node = set()

        # 1. Set the no. of nodes required for this Run
        # Get the ranks per node for each run
        num_ranks_per_run = {}
        for rank_info in layout_info['cpu']:
            if rank_info is not None:
                run_name = rank_info.split(':')[0]
                rank_id = int(rank_info.split(':')[1])
                if run_name not in list(num_ranks_per_run.keys()):
                    num_ranks_per_run[run_name] = set()
                num_ranks_per_run[run_name].add(rank_id)

        # set the no. of nodes for the codes on this node
        for code in num_ranks_per_run:
            run = self._get_run_by_name(code)
            run.nodes = math.ceil(run.nprocs/len(num_ranks_per_run[code]))

        # 2. Create the node config for each Run
        # Add run to codes_on_node and create nodeconfig for each run
        for run_name in num_ranks_per_run.keys():
            num_ranks_per_node = len(num_ranks_per_run[run_name])
            run = self._get_run_by_name(run_name)
            codes_on_node.add(run)
            run.node_config = NodeConfig()
            run.node_config.num_ranks_per_node = num_ranks_per_node
            for i in range(num_ranks_per_node):
                # Every rank for this run has a list of cpu and gpu cores
                run.node_config.cpu.append([])
                run.node_config.gpu.append([])

        # Loop over the cpu core mapping
        for i in range(len(layout_info['cpu'])):
            rank_info = layout_info['cpu'][i]

            # if the core is not mapped, go to the next one
            if rank_info is None:
                continue

            run_name = rank_info.split(':')[0]
            rank_id = rank_info.split(':')[1]
            run = self._get_run_by_name(run_name)

            # append core id to the rank id of this run
            run.node_config.cpu[int(rank_id)].append(i)

        # Loop over the gpu mapping
        for i in range(len(layout_info['gpu'])):
            rank_list = layout_info['gpu'][i]
            if rank_list is not None:
                for rank_info in rank_list:
                    run_name = rank_info.split(':')[0]
                    rank_id = rank_info.split(':')[1]
                    run = self._get_run_by_name(run_name)
                    run.node_config.gpu[int(rank_id)].append(i)

        return list(codes_on_node)

    def _rearrange_codes_by_dependencies(self, nl):
        """
        Input is a nested list of lists, where the inner lists represents
        codes sharing a compute node.
        This function rearranges those codes by dependencies so that codes
        that are run in order are placed on the same node.
        """

        def parse_lists(_nl):
            """
            dont judge me
            """
            for l in _nl:
                for code in l:
                    if code.depends_on_runs:
                        t = code.depends_on_runs
                        if t not in l:
                            for ol in _nl:
                                if t in ol:
                                    ol.append(code)
                                    l.remove(code)
                                    return False
            return True

        done = False
        while not done:
            done = parse_lists(nl)

    def run_finished(self, run):
        assert self._running
        run_done_callbacks = False

        # release_nodes doesn't do anything at this time. Runs do not
        # release nodes back to the pipeline, as it is non-trivial to
        # release nodes to the pipeline when Runs share nodes.
        self._release_nodes(run.nodes_assigned)

        with self._state_lock:
            self._active_runs.remove(run)
            if not self._active_runs:
                self.run_post_process_script()
                run_done_callbacks = True
            elif self.kill_on_partial_failure and not run.succeeded:
                _log.warning('%s run %s failed, killing remaining',
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
        # TODO: make sure this doesn't conflict with other names
        name = 'post-process'
        stdout_path = _get_path(self.working_dir,
                                STDOUT_NAME + "." + name, None)
        stderr_path = _get_path(self.working_dir,
                                STDERR_NAME + "." + name, None)
        return_path = _get_path(self.working_dir,
                                RETURN_NAME + "." + name, None)
        walltime_path = _get_path(self.working_dir,
                                  WALLTIME_NAME + "." + name, None)

        outf = errf = None
        start_time = time.time()
        try:
            outf = open(stdout_path, 'w')
            errf = open(stderr_path, 'w')
            rval = subprocess.call(args, stdout=outf, stderr=errf,
                                   cwd=self.working_dir, timeout=120)
        except subprocess.SubprocessError as e:
            _log.warning("pipe '%s' failed to run post process script: %s",
                         self.id, str(e))
            rval = None
        finally:
            end_time = time.time()
            if outf is not None:
                outf.close()
            if errf is not None:
                errf.close()
            with open(return_path, 'w') as rf:
                rf.write(str(rval))
                rf.write('\n')
            with open(walltime_path, 'w') as wf:
                wf.write(str(end_time - start_time) + '\n')
        if rval != 0 and self.post_process_stop_on_failure:
            self._execute_fatal_callbacks()

    def add_done_callback(self, fn):
        self.done_callbacks.add(fn)

    def remove_done_callback(self, fn):
        self.done_callbacks.remove(fn)

    def _execute_done_callbacks(self):
        # NOTE: must be called w/o any locks!
        _log.debug('%s _execute_done_callbacks', self.log_prefix)
        for cb in self.done_callbacks:
            cb(self)

    def add_fatal_callback(self, fn):
        self.fatal_callbacks.add(fn)

    def remove_fatal_callback(self, fn):
        self.fatal_callbacks.remove(fn)

    def _execute_fatal_callbacks(self):
        # NOTE: must be called w/o any locks!
        _log.debug('%s _execute_fatal_callbacks', self.log_prefix)
        for cb in self.fatal_callbacks:
            cb(self)

    def _release_nodes(self, nodes_assigned_to_run):
        pass

    def _get_run_by_name(self, run_name):
        for run in self.runs:
            if run.name == run_name:
                return run

    def get_nodes_used(self):
        if self.total_nodes is None:
            raise ValueError("set_ppn must be called before getting "
                             "node usage")
        return self.total_nodes

    def set_ppn(self, ppn):
        """Determine number of nodes needed to run pipeline with the specified
        node layout or full occupancy layout with ppn. Also updates runs
        to set node and task per node counts.
        TODO: This should be set by Cheetah in fobs.json"""

        # Return if you are using VirtualNode for node layout, as the
        # parsing is done differently for VirtualNode
        # At this point, the node layout is not an object of VirtualNode
        layout_type = self.node_layout[0].get('__info_type__') or None
        if layout_type == 'NodeConfig':
            return

        if self.node_layout is None:
            run_names = [run.name for run in self.runs]
            node_layout = NodeLayout.default_no_share_layout(ppn, run_names)
        else:
            node_layout = NodeLayout(self.node_layout)

        for run in self.runs:
            run_node = node_layout.get_node_containing_code(run.name)

            # node sharing is not yet supported
            assert len(run_node) == 1

            run.tasks_per_node = run_node[run.name]
            if run.tasks_per_node > run.nprocs:
                run.tasks_per_node = run.nprocs
            run.nodes = int(math.ceil(run.nprocs / run.tasks_per_node))

    def set_total_nodes(self):
        """
        To be deprecated
        """
        pass

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
            # Collapse reason into single value, giving priority to
            # exception and timeout.
            # TODO: It might be more informative to
            # report all states, i.e. make reason a list.
            reason = status.REASON_SUCCEEDED
            if any(r.exception for r in self.runs):
                reason = status.REASON_EXCEPTION
            elif any(r.timed_out for r in self.runs):
                reason = status.REASON_TIMEOUT
            elif any((r.get_returncode() != 0) for r in self.runs):
                reason = status.REASON_FAILED
            return status.PipelineState(self.id, status.DONE,
                                        reason, return_codes)

    def get_pids(self):
        assert self._running
        return [run.get_pid() for run in self.runs]

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
