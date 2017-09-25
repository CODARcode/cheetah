"""Classes for 'consuming' pipelines - running groups of MPI tasks based on a
specified total process limit."""

import queue
import threading
import math


class PipelineRunner(object):
    """Runner that assumes a homogonous set of nodes, and can be node limited
    or process limited."""

    def __init__(self, runner, max_procs=None, max_nodes=None,
                 logger=None, processes_per_node=None):
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
        self._running_pipelines = set()
        self._running_pipelines_lock = threading.Lock()

    def add_pipeline(self, p):
        self.q.put(p)

    def stop(self):
        self.q.put(None)

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
        with self._running_pipelines_lock:
            self._running_pipelines.remove(pipeline)

    def run_pipelines(self):
        """Main loop of consumer thread."""
        # TODO: should client be responsible for setting this in the
        # JSON input data?
        pipeline_id = 0
        while True:
            pipeline = self.q.get()
            if pipeline is None:
                return
            with self.free_cv:
                if self.max_procs is not None:
                    self.free_cv.wait_for(
                        lambda: self.free_procs >= pipeline.total_procs)
                    self.free_procs -= pipeline.total_procs
                else:
                    self.free_cv.wait_for(
                        lambda: self.free_nodes
                                >= pipeline.get_nodes_used(self.ppn))
                    self.free_nodes -= pipeline.get_nodes_used(self.ppn)
            if self.logger is not None:
                pipeline.set_loggers(self.logger, pipeline_id)
            pipeline.start(self, self.runner)
            with self._running_pipelines_lock:
                self._running_pipelines.add(pipeline)
            pipeline_id += 1

        # Wait for any pipelines that are still running to complete. Use
        # a copy since the monitor threads may be removing pipelines as
        # they complete (and joining an already complete pipeline is
        # harmless).
        with self._running_pipelines_lock:
            still_running = list(self._running_pipelines)
        for pipeline in still_running:
            pipeline.join_all()
