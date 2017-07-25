"""Classes for monitoring running process and signaling consumer when
complete."""

import time


class PipelineMonitor(object):
    def __init__(self, check_interval=5):
        self.check_interval = check_interval
        self.consumer = None
        self.pipelines = []
        self._run = True
        self._running_pids = set()

    def set_consumer(self, consumer):
        self.consumer = consumer

    def add_pipeline(self, pipeline):
        self.pipelines.append(pipeline)
        for pid in pipeline.get_pids():
            self._running_pids.add(pid)

    def stop(self):
        self._run = False

    def run(self):
        while self._run or self._running_pids:
            for pipeline in self.pipelines:
                polls_nprocs = pipeline.poll_all_nprocs()
                for poll, nprocs, pid in polls_nprocs:
                    if poll is None:
                        continue
                    if pid not in self._running_pids:
                        continue
                    self._running_pids.remove(pid)
                    self.consumer.procs_finished(nprocs)
            time.sleep(self.check_interval)
