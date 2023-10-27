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

from codar.savanna import tau, status, machines, summit_helper, \
    deepthought2_helper
from codar.savanna.error_messages import err_msg
from codar.savanna.exc import SavannaException
from codar.savanna.node_layout import NodeLayout, NodeConfig
from codar.savanna.run import Run
from codar.savanna.utils import get_path, STDOUT_NAME, STDERR_NAME, \
    RETURN_NAME, WALLTIME_NAME
from codar.savanna.templates import EXE_LAUNCH_FILE_TEMPLATE

_log = logging.getLogger('codar.savanna.pipeline')


class Pipeline(object):
    def __init__(self, pipe_id, runs, working_dir, apps_dir, total_nodes,
                 machine_name,
                 kill_on_partial_failure=False,
                 post_process_script=None,
                 post_process_args=None,
                 post_process_stop_on_failure=False,
                 node_layout=None, launch_mode=None):
        self.id = pipe_id
        self.runs = runs
        self.working_dir = working_dir
        self.apps_dir = apps_dir
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
        self._start_time = None
        self._walltime_path = self.working_dir+"/codar.savanna.total.walltime"

        for run in runs:
            self.total_procs += run.nprocs
            run.log_prefix = "%s:%s" % (self.id, run.name)
        # requires ppn to determine, in case node layout is not specified
        self.total_nodes = total_nodes
        self.launch_mode = launch_mode

        # List of node IDs assigned to this pipeline. Gets initialized in
        # start()
        self.nodes_assigned = Queue()

        # Keep a copy of the nodes assigned. Pop nodes from this queue to
        # assign to Runs. When a Run is done, it can push the node back into
        # this queue, but Runs that share nodes may add the same node to the
        # Queue multiple times. We need a SetQueue for this, or a way to
        # have all Runs in a shared node release nodes just once.
        self._nodes_assigned = Queue()

    @classmethod
    def from_data(cls, data):
        """Create Pipeline instance from dictionary data structure, containing
        at least "id" and "runs" keys. The "runs" key must have a list of dict,
        and each dict is parsed using Run.from_data.
        Raises KeyError if a required key is missing."""

        runs_data = data["runs"]
        working_dir = data["working_dir"]
        apps_dir = data.get("apps_dir")

        # Read tau options and ensure tau_exec is in PATH
        tau_profiling = data.get("tau_profiling", False)
        tau_tracing = data.get("tau_tracing", False)

        # Run working dir defaults to pipeline working dir, and can be
        # specified relative to pipeline working dir.
        for rd in runs_data:
            run_working_dir = rd.get("working_dir")
            if run_working_dir is None:
                run_working_dir = working_dir
            elif not run_working_dir.startswith("/"):
                run_working_dir = os.path.join(working_dir, run_working_dir)
            rd["working_dir"] = run_working_dir
            rd["tau_profiling"] = tau_profiling
            rd["tau_tracing"] = tau_tracing
            rd["apps_dir"] = apps_dir
            rd["machine"] = machines.get_by_name(data["machine_name"])
        if not isinstance(runs_data, list):
            _log.error("'runs' key must be a list of dictionaries")
            return None
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
                if run.depends_on_runs is None:
                    _log.error("Internal failure in dependency management "
                               "in %s", working_dir)
                    return None

        launch_mode = data.get("launch_mode")
        kill_on_partial_failure = data.get("kill_on_partial_failure", False)
        post_process_script = data.get("post_process_script")
        post_process_args = data.get("post_process_args", [])
        if not isinstance(post_process_args, list):
            _log.error("'post_process_args' must be a list in %s", working_dir)
            return None
        post_process_stop_on_failure = data.get("post_process_stop_on_failure")
        node_layout = data.get("node_layout")
        total_nodes = data.get("total_nodes")
        machine_name = data.get("machine_name")
        return Pipeline(pipe_id, runs=runs, working_dir=working_dir,
                        apps_dir=apps_dir,
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

        # Reorder the runs list so that runs are listed according to their
        # dependencies
        self.reorder_runs_by_dependencies()

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
                run.app_sh_setup()

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
                mpmd_run.name = "mpmd"
                mpmd_run.set_runner(runner)
                # mpmd_run.app_sh_setup()
                self.runs = [mpmd_run]

            # -------------------------------------------------------------- #
            # Temporary ERF fix #251.
            # Add jsm process running on service node
            if self.machine_name == 'summit':
                jsm_d = {"name": "jsm", "exe": "jsm",
                         "after_rc_done": None,
                         "args": [], "sched_args": None, "nprocs": 1,
                         "working_dir": self.working_dir,
                         "machine": machines.get_by_name(
                             self.machine_name),
                         "apps_dir": self.apps_dir,
                         "runner_override": True,}

                jsm_r = Run.from_data(jsm_d)
                jsm_r.app_sh_setup()
                self.runs.insert(0, jsm_r)
            # -------------------------------------------------------------- #

            for run in self.runs:
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
        self._start_time = time.time()
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

        # #--------------------------------------------------------------------#
        # # 241. Disable node sharing for Summit due to ERF issue.
        # if self.machine_name.lower() == 'summit':
        #     if len(codes_on_node) > 1:
        #         raise Exception("Node-sharing on Summit temporarily disabled "\
        #               "due to a jsrun issue.")
        # # --------------------------------------------------------------------#

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
            # -------------------------------------------------------------- #
            # Temporary ERF fix. Remove manually added jsm. #251
            if self.machine_name == 'summit':
                if len(self._active_runs) == 1:
                    # last run 'jsm' remaining
                    jsm_r = list(self._active_runs)[0]
                    parent = psutil.Process(jsm_r._p.pid)
                    if parent is not None:
                        children = parent.children(recursive=True)
                        for process in children:
                            _log.info("Found child of jsm")
                            process.send_signal(signal.SIGKILL)
                    jsm_r.kill()
            # -------------------------------------------------------------- #
            if not self._active_runs:
                # save the total runtime here to ensure it is captured
                # before the post process script is run
                self.save_walltime()
                self.run_post_process_script()
                run_done_callbacks = True
            elif self.kill_on_partial_failure and not run.succeeded:
                _log.warning('%s run %s failed, killing remaining',
                             self.log_prefix, run.name)
                self.save_walltime()
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
        stdout_path = get_path(self.working_dir,
                                STDOUT_NAME + "." + name, None)
        stderr_path = get_path(self.working_dir,
                                STDERR_NAME + "." + name, None)
        return_path = get_path(self.working_dir,
                                RETURN_NAME + "." + name, None)
        walltime_path = get_path(self.working_dir,
                                  WALLTIME_NAME + "." + name, None)

        outf = errf = None
        start_time = time.time()
        try:
            outf = open(stdout_path, 'w')
            errf = open(stderr_path, 'w')
            rval = None
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

    def save_walltime(self):
        """
        Saves the total runtime of the pipeline in a a file.
        """

        walltime = time.time() - self._start_time
        with open(self._walltime_path, 'w') as f:
            f.write(str(walltime) + "\n")

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
