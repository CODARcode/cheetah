"""Classes for 'consuming' pipelines - running groups of MPI tasks based on a
specified total process limit."""

import queue
import threading
import math


class PipelineRunner(object):
    """Runner that assumes a homogonous set of nodes, and can be node limited
    or process limited."""

    def __init__(self, runner, monitor, max_procs=None, max_nodes=None,
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
        self._run = True
        self.free_procs = max_procs
        self.free_nodes = max_nodes
        self.free_cv = threading.Condition()
        self.monitor = monitor
        self.logger = logger
        monitor.set_consumer(self)

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
            pipeline.start(self.runner)
            self.monitor.add_pipeline(pipeline)
            pipeline_id += 1
