"""
Funtions to print status information for campaigns.
"""
import os
import json
from collections import defaultdict
import logging

from codar.cheetah.helpers import get_immediate_subdirs, \
                                  require_campaign_directory


def print_campaign_status(campaign_directory, filter_user=None,
                          filter_group=None, group_details=False,
                          print_logs=False, log_level='DEBUG'):
    require_campaign_directory(campaign_directory)
    user_dirs = get_immediate_subdirs(campaign_directory)
    for user in user_dirs:
        if filter_user and user not in filter_user:
            continue
        user_dir = os.path.join(campaign_directory, user)
        group_dirs = get_immediate_subdirs(user_dir)
        for group in group_dirs:
            if filter_group and group not in filter_group:
                continue
            user_group = user + '/' + group
            group_dir = os.path.join(user_dir, group)
            jobid_file_path = os.path.join(group_dir,
                                           'codar.cheetah.jobid.txt')
            if not os.path.exists(jobid_file_path):
                print(user_group, ':', 'NOT SUBMITTED')
                continue

            with open(jobid_file_path) as f:
                jobid = f.read().strip()
                jobid = jobid.split(':')[1]

            log_file_path = os.path.join(group_dir, 'codar.FOBrun.log')
            status_file_path = os.path.join(group_dir,
                                            'codar.workflow.status.json')
            walltime_file_path = os.path.join(group_dir,
                                              'codar.cheetah.walltime.txt')
            if os.path.exists(status_file_path):
                status_data, state_counts, reason_counts, rc_counts = \
                                    get_workflow_status(status_file_path)
                total = len(status_data)
                if os.path.exists(walltime_file_path):
                    ok = reason_counts['succeeded']
                    if ok < total:
                        print(user_group, ':', 'DONE,',
                              total-ok, '/', total, 'failed')
                    else:
                        print(user_group, ':', 'DONE')
                else:
                    in_progress = (state_counts['running']
                                   + state_counts['not_started'])
                    print(user_group, ':', 'IN PROGRESS,', 'job', jobid,
                          ',', total-in_progress, '/', total)
                if group_details:
                    get_workflow_status(status_file_path, True, 2)
                if print_logs:
                    _print_fobrun_log(log_file_path, log_level)
            else:
                print(user_group, ':', 'NOT STARTED')


def _print_fobrun_log(log_file_path, log_level):
    log_level_int = getattr(logging, log_level.upper(), None)
    if not isinstance(log_level_int, int):
        raise ValueError('Invalid log level: %s' % log_level)
    with open(log_file_path) as f:
        for line in f:
            line = line.strip()
            _, line_level, _ = _parse_fobrun_log_line(line)
            if line_level < log_level_int:
                continue
            print(' ', line)


def _parse_fobrun_log_line(line):
    dt_string = line[:24]
    level, message = line[24:].split(':', 1)
    level = _numeric_log_level(level)
    return dt_string, level, message


def _numeric_log_level(log_level_string):
    log_level_int = getattr(logging, log_level_string.upper(), None)
    if not isinstance(log_level_int, int):
        raise ValueError('Invalid log level: %s' % log_level_string)
    return log_level_int


def get_workflow_status(status_file_path, print_details=False, indent=0):
    with open(status_file_path) as f:
        status_data = json.load(f)

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

    if print_details:
        prefix = " " * indent
        print('%s== total runs:' % prefix, total_count)
        for k, v in state_counts.items():
            print('%sstate  %11s: %d' % (prefix, k, v))
        print('\n%s== total w/ reason:' % prefix, total_reasons)
        for k, v in reason_counts.items():
            print('%sreason %11s: %d' % (prefix, k, v))
        print('\n%s== total return codes:' % prefix, total_rc)
        for k, v in rc_counts.items():
            print('%sreturn code %d: %d' % (prefix, k, v))

    return status_data, state_counts, reason_counts, rc_counts
