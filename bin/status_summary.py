#!/usr/bin/env python3
"""
Script to read a workflow status file and generate a summary showing a count of
runs in each state.

Format:

{
  "1": {
    "state": "done",
    "reason": "succeeded",
    "return_codes": {
      "code01": 0,
      "code02": 0
    }
  },
  ...
}

"""

import sys
import json
from collections import defaultdict


def print_status_summary(status_data):
    total_count = len(status_data)
    total_rc = 0
    rc_counts = defaultdict(int)
    state_counts = dict(not_started=0, running=0, done=0, killed=0)
    total_reasons = 0
    reason_counts = defaultdict(int)

    for st in status_data.values():
        state_counts[st['state']] += 1
        reason = st.get('reason')
        if reason:
            reason_counts[reason] += 1
            total_reasons += 1
        return_codes = st.get('return_codes')
        if return_codes:
            for rc in return_codes.values():
                total_rc += 1
                rc_counts[rc] += 1

    print('= total runs:', total_count)
    for k, v in state_counts.items():
        print('state  %11s: %d' % (k, v))
    print('\n= total w/ reason:', total_reasons)
    for k, v in reason_counts.items():
        print('reason %11s: %d' % (k, v))
    print('\n= total return codes:', total_rc)
    for k, v in rc_counts.items():
        print('return code %d: %d' % (k, v))


def main():
    if len(sys.argv) != 2:
        print('Usage: %s /path/to/status.json' % sys.argv[0])
        sys.exit(1)

    status_file_path = sys.argv[1]
    with open(status_file_path) as f:
        status_data = json.load(f)
    print_status_summary(status_data)


if __name__ == '__main__':
    main()
