"""Classes for producing pipelines."""

import json
import os
import logging
from codar.workflow.model import Pipeline

_log = logging.getLogger('codar.workflow.producer')


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
            for line in f.readlines():
                pipeline_data = json.loads(line)

                # Check if this pipeline has already been run
                id = pipeline_data['id']
                status_d = pipelines_status.get(id,{})
                status = status_d.get('state', 'not_started')

                # Add pipeline if not run before
                if status == 'not_started':
                    pipeline = Pipeline.from_data(pipeline_data)
                    _log.debug("Adding pipeline %s to list of pipelines to "
                               "be run", pipeline_data['working_dir'])
                    yield pipeline
                else:
                    _log.debug("Run %s already run. Skipping ..",
                               pipeline_data['working_dir'])