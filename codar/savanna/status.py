"""
Class for maintaining state of all FOB runs that the workflow consumer is
managing. State is saved in a JSON file, overwritten on each state change.
"""

import json
import os
import threading
from collections import defaultdict


NOT_STARTED = 'not_started'
RUNNING = 'running'
DONE = 'done'
KILLED = 'killed'

REASON_TIMEOUT = 'timeout'
REASON_FAILED = 'failed'
REASON_SUCCEEDED = 'succeeded'
REASON_EXCEPTION = 'exception'
REASON_NOFIT = 'nofit'


class WorkflowStatus(threading.Thread):
    def __init__(self, file_path):
        threading.Thread.__init__(self, name='Thread-status-0')
        self.file_path = file_path
        self._lock = threading.Lock()
        self._state = defaultdict(dict)

        # If status file exists from a previous run, load it first, so that
        # you dont overwrite it only with runs from this job
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                self._state = json.load(f)

    def set_state(self, pipeline_state):
        with self._lock:
            self._state[pipeline_state.id] = pipeline_state.as_data()
            self._save()

    def _save(self):
        """Save state to file_path. Must be called with lock acquired!"""
        with open(self.file_path, 'w') as f:
            json.dump(self._state, f, indent=2)


class PipelineState(object):
    def __init__(self, pipeline_id, state, reason=None, return_codes=None):
        self.id = pipeline_id
        self.state = state
        self.reason = reason
        self.return_codes = return_codes or {}

    def as_data(self):
        # NB: don't include id, that is used as the key
        return dict(state=self.state, reason=self.reason,
                    return_codes=self.return_codes)
