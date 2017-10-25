"""Classes for producing pipelines."""

import json
from codar.workflow.model import Pipeline


class JSONFilePipelineReader(object):
    """Load pipelines from a file formatted as a new line separated list of
    JSON documents. Each JSON document must be a list containing dictionaries,
    each dictionary discribing a code to run as part of the pipeline."""

    def __init__(self, file_path):
        self.file_path = file_path

    def read_pipelines(self):
        with open(self.file_path) as f:
            for line in f.readlines():
                pipeline_data = json.loads(line)
                pipeline = Pipeline.from_data(pipeline_data)
                yield pipeline
