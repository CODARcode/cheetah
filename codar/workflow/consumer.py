"""Classes for 'consuming' pipelines - running groups of MPI tasks based on a
specified total process limit."""

import queue
import threading

from codar.workflow import status


class PipelineRunner(object):
    """Runner that assumes a homogonous set of nodes, and can be node limited
    or process limited."""

    def __init__(self, runner, max_procs=None, max_nodes=None,
                 logger=None, processes_per_node=None, status_file=None):
        if not (bool(max_procs) ^ bool(max_nodes)):
            raise ValueError("specify one of max_procs and max_nodes")
        if max_nodes and processes_per_node is None:
            raise ValueError("max_nodes requires processes_per_node")
        self.max_procs = max_procs
        self.max_nodes = max_nodes
        self.ppn = processes_per_node
        self.runner = runner
        self.q = queue.Queue()
        self.pipelines = []
        self.free_procs = max_procs
        self.free_nodes = max_nodes
        self.free_cv = threading.Condition()
        self.logger = logger
        self._pipeline_ids = set()
        self._running_pipelines = set()
        self._state_lock = threading.Lock()
        self._process_pipelines = True
        self._allow_new_pipelines = True
        self._killed = False
        if status_file is not None:
            self._status = status.WorkflowStatus(status_file)
        else:
            self._status = None

    def add_pipeline(self, p):
        with self._state_lock:
            if not self._allow_new_pipelines:
                raise ValueError(
                    "new pipelines are not allowed after stop or kill")
            if p.id in self._pipeline_ids:
                raise ValueError("duplicate pipeline id: %s" % p.id)
            self._pipeline_ids.add(p.id)
            if self._status is not None:
                self._status.set_state(p.get_state())
            self.q.put(p)

    def stop(self):
        """Signal to stop when all pipelines are finished. Don't allow adding
        new pipelines."""
        with self._state_lock:
            # NB: Queue is thread save, but we don't want to allow a
            # pipeline to be added at the same time stop is being
            # executed, which would allow a non-None pipeline to be
            # appended after the None without raising an error.
            self._allow_new_pipelines = False
            self.q.put(None)

    def kill_all(self):
        """Kill all running processes spawned by this consumer and don't
        start any new processes."""

        if self.logger is not None:
            self.logger.warn("killing all pipelines and exiting consumer")

        with self._state_lock:
            self._killed = True
            self._allow_new_pipelines = False
            self._process_pipelines = False
            still_running = list(self._running_pipelines)
            self.q.put(None) # unblock queue get in run thread

        with self.free_cv:
            # signal pipeline run thread to stop waiting. It checks for
            # stage change after waking up.
            self.free_cv.notify()

        for pipe in still_running:
            pipe.force_kill_all()
        # NB: the run_pipelines methods will block waiting for the
        # pipelines, so we don't need to do that here. Callers that want
        # to block can call join on the consumer thread.

    def run_finished(self, run):
        """Monitor thread(s) should call this as runs complete."""
        with self.free_cv:
            if self.max_procs is not None:
                self.free_procs += run.nprocs
            else:
                self.free_nodes += run.get_nodes_used(self.ppn)
            self.free_cv.notify()

    def pipeline_finished(self, pipeline):
        """Monitor thread(s) should call this as pipelines complete."""
        with self._state_lock:
            self._running_pipelines.remove(pipeline)
            if self._status is not None:
                self._status.set_state(pipeline.get_state())

    def pipeline_fatal(self, pipeline):
        if self.logger is not None:
            self.logger.error("fatal error in pipeline '%s'" % pipeline.id)
        self.kill_all()

    def _pipeline_can_run(self, pipeline):
        # NOTE: requires free_cv lock
        if self.max_procs is not None:
            return (self.free_procs >= pipeline.total_procs)
        else:
            return (self.free_nodes >= pipeline.get_nodes_used(self.ppn))

    def run_pipelines(self):
        """Main loop of consumer thread. Does not return until all child
        threads are complete."""
        # TODO: should client be responsible for setting this in the
        # JSON input data?
        while True:
            pipeline = self.q.get() # NB: this blocks on empty queue
            if pipeline is None:
                break
            with self.free_cv:
                while not self._pipeline_can_run(pipeline):
                    # allow exiting wait loop if signaled by another
                    # thread
                    if not self._process_pipelines:
                        break
                    self.free_cv.wait()

                if self._process_pipelines:
                    if self.max_procs is not None:
                        self.free_procs -= pipeline.total_procs
                    else:
                        self.free_nodes -= pipeline.get_nodes_used(self.ppn)

            with self._state_lock:
                # check state in case kill was issued while we were
                # waiting
                if not self._process_pipelines:
                    break

                if self.logger is not None:
                    pipeline.set_loggers(self.logger)
                pipeline.start(self, self.runner)
                self._running_pipelines.add(pipeline)
                if self._status is not None:
                    self._status.set_state(pipeline.get_state())

        # Wait for any pipelines that are still running to complete. Use
        # a copy since the monitor threads may be removing pipelines as
        # they complete (and joining an already complete pipeline is
        # harmless).
        still_running = list(self._running_pipelines)
        for pipeline in still_running:
            pipeline.join_all()
