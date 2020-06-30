"""Classes for producing pipelines."""

import json
import os
import logging
from codar.savanna.model import Pipeline
from codar.savanna.status import DONE, NOT_STARTED

_log = logging.getLogger('codar.savanna.producer')


class JSONFilePipelineReader(object):
    """Load pipelines from a file formatted as a new line separated list of
    JSON documents. Each JSON document must be a list containing dictionaries,
    each dictionary discribing a code to run as part of the pipeline."""

    def __init__(self, file_path):
        self.file_path = file_path

    def read_pipelines(self):

        # If the group has been run before, open status file and get the
        # status of all runs
        status_file = os.path.join(os.path.dirname(self.file_path),
                                   'codar.workflow.status.json')
        try:
            with open(status_file, 'r') as sf:
                pipelines_status = json.load(sf)
        except:
            pipelines_status = {}

        with open(self.file_path) as f:
            all_pipelines = json.load(f)

        for pipeline_data in all_pipelines:
            # Check if this pipeline has already been run
            pipe_id = pipeline_data['id']
            status_d = pipelines_status.get(pipe_id, {})
            status = status_d.get('state', NOT_STARTED)

            # Add pipeline if not done
            if status == DONE:
                _log.info("pipeline %s already done, skipping", pipe_id)
            else:
                pipeline = Pipeline.from_data(pipeline_data)
                if pipeline:
                    _log.debug("adding pipeline %s to run queue", pipe_id)
                    yield pipeline
