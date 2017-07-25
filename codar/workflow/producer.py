"""Classes for producing pipelines."""

import json
from cheetah.workflow.model import Run, Pipeline


class JSONFilePipelineReader(object):
    def __init__(self, file_path):
        self.file_path = file_path

    def read_pipelines(self):
        with open(self.file_path) as f:
            for line in f.readlines():
                run_data_list = json.loads(line)
                runs = [Run.from_data(run_data) for run_data in run_data_list]
                pipeline = Pipeline(runs)
                yield pipeline
