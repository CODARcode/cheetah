"""Classes for 'consuming' pipelines - running groups of MPI tasks based on a
specified total process limit."""

import queue
import threading


class PipelineRunner(object):
    def __init__(self, max_procs, runner, monitor):
        self.max_procs = max_procs
        self.runner = runner
        self.q = queue.Queue()
        self.pipelines = []
        self._run = True
        self.free_procs = max_procs
        self.free_procs_cv = threading.Condition()
        self.monitor = monitor
        monitor.set_consumer(self)

    def add_pipeline(self, p):
        self.q.put(p)

    def procs_finished(self, count):
        """Monitor thread should call this as processes complete."""
        with self.free_procs_cv:
            self.free_procs += count
            self.free_procs_cv.notify()

    def run_pipelines(self):
        """Main loop of consumer thread."""
        while True:
            pipeline = self.q.get()
            if pipeline is None:
                return
            with self.free_procs_cv:
                self.free_procs_cv.wait_for(
                    lambda: self.free_procs >= pipeline.total_procs)
                self.free_procs -= pipeline.total_procs
            pipeline.start(self.runner)
            self.monitor.add_pipeline(pipeline)
