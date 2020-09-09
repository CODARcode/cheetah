"""
Funtions to print status information for campaigns.
"""
import os
import sys
import json
from collections import defaultdict
import logging
import glob

from codar.cheetah.helpers import get_immediate_subdirs, \
                                  require_campaign_directory


def print_campaign_status(campaign_directory, filter_user=None,
                          filter_group=None, filter_run=None,
                          filter_code=None,
                          group_summary=False,
                          run_summary=False,
                          print_logs=False, log_level='DEBUG',
                          return_codes=False, print_output=False,
                          show_parameters=False):
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

            fob_file_path = os.path.join(group_dir, 'fobs.json')
            code_names = _get_group_code_names(fob_file_path)
            log_file_path = os.path.join(group_dir, 'codar.FOBrun.log')
            status_file_path = os.path.join(group_dir,
                                            'codar.workflow.status.json')
            walltime_file_path = os.path.join(group_dir,
                                              'codar.cheetah.walltime.txt')
            if os.path.exists(status_file_path):
                status_data, state_counts, reason_counts, rc_counts = \
                                    get_workflow_status(status_file_path)
                total = len(status_data)
                ok = reason_counts['succeeded']
                if os.path.exists(walltime_file_path):
                    if ok < total:
                        print(user_group, ':', 'DONE,',
                              ok, '/', total, 'succeeded')
                    else:
                        print(user_group, ':', 'DONE')
                else:
                    in_progress = (state_counts['running']
                                   + state_counts['not_started'])
                    if state_counts['running'] > 0:
                        print(user_group, ':', 'IN PROGRESS,', 'job', jobid,
                              ',', ok, '/', total, 'succeeded')
                    elif state_counts['not_started'] > 0:
                        print(user_group, ':', 'DONE; INCOMPLETE,',
                              ok, '/', total, 'succeeded')
                    else:  # some runs were killed due to timeout or cancel.sh
                        print(user_group, ':', 'DONE,',
                              ok, '/', total, 'succeeded')
                if group_summary:
                    get_workflow_status(status_file_path, print_counts=True,
                                        indent=2)
                if return_codes or show_parameters or run_summary:
                    get_workflow_status(status_file_path,
                                        print_return_codes=return_codes,
                                        indent=2,
                                        filter_run=filter_run,
                                        filter_code=filter_code,
                                        run_summary=run_summary,
                                        print_parameters=show_parameters,
                                        code_names=code_names)
                if print_logs:
                    _print_fobrun_log(log_file_path, log_level, filter_run)
                if print_output:
                    _print_group_code_output(group_dir, filter_run,
                                             filter_code)
            else:
                print(user_group, ':', 'NOT STARTED')


def _get_group_code_names(fob_file_path):
    """Extract code names from first run in fobs file."""
    with open(fob_file_path) as f:
        data = json.load(f)[0]
        return [r['name'] for r in data['runs']]


def _print_fobrun_log(log_file_path, log_level, filter_run=None):
    log_level_int = getattr(logging, log_level.upper(), None)
    if not isinstance(log_level_int, int):
        raise ValueError('Invalid log level: %s' % log_level)
    with open(log_file_path) as f:
        for line in f:
            line = line.strip()
            _, line_level, _ = _parse_fobrun_log_line(line)
            if line_level < log_level_int:
                continue
            if filter_run:
                found = False
                for fr in filter_run:
                    if fr in line:
                        found = True
                        break
                if not found:
                    continue
            print(' ', line)


def _print_group_code_output(group_dir, filter_run=None, filter_code=None):
    run_dirs = get_immediate_subdirs(group_dir)
    for run_name in run_dirs:
        if filter_run and run_name not in filter_run:
            continue
        run_dir = os.path.join(group_dir, run_name)
        _print_run_code_output(run_name, run_dir, filter_code)


def _print_run_code_output(run_name, run_dir, filter_code=None):
    # Note: this also handles experiments using component subdirs, where
    # the files are in a subdirectory with the code's name
    out_files = (glob.glob(os.path.join(run_dir, 'codar.workflow.stdout.*'))
                +glob.glob(os.path.join(run_dir, '*/codar.workflow.stdout.*')))
    err_files = (glob.glob(os.path.join(run_dir, 'codar.workflow.stderr.*'))
                +glob.glob(os.path.join(run_dir, '*/codar.workflow.stderr.*')))

    outputs = defaultdict(dict) # key is code name, values are
                                # dict { 'out': '...', 'err': '...'}
    for fpath in out_files:
        fname = os.path.basename(fpath)
        parts = fname.split('.')
        code = parts[-1]
        outputs[code]['out'] = fpath
    for fpath in err_files:
        fname = os.path.basename(fpath)
        parts = fname.split('.')
        code = parts[-1]
        outputs[code]['err'] = fpath

    for code in sorted(outputs.keys()):
        if filter_code and code not in filter_code:
            continue
        for k in ['out', 'err']:
            if k not in outputs[code]:
                continue
            fpath = outputs[code][k]
            size = os.path.getsize(fpath)
            print('>>>', run_name, code, 'std' + k, '(%d bytes)' % size)
            # TODO: Encountering non utf-8 chars is unlikely,
            # but may get binary data, should handle that case better.
            with open(fpath, encoding='utf-8', errors='backslashreplace') as f:
                for line in f:
                    # Hack to make utf-8 work even if python terminal
                    # default is ascii (seems necessary on cori for example).
                    # Maybe there is a cleaner way?
                    line_bytes = line.encode('utf-8',
                                             errors='backslashreplace')
                    sys.stdout.buffer.write(line_bytes)
            print()


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


def get_workflow_status(status_file_path, print_counts=False, indent=0,
                        print_return_codes=False, filter_run=None,
                        print_parameters=False,
                        filter_code=None, run_summary=False,
                        code_names=None):
    with open(status_file_path) as f:
        status_data = json.load(f)

    group_path = os.path.dirname(status_file_path)

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

    prefix = " " * indent
    if print_counts:
        print('%s== total runs:' % prefix, total_count)
        for k in sorted(state_counts.keys()):
            v = state_counts[k]
            print('%sstate  %11s: %d' % (prefix, k, v))
        print('\n%s== total w/ reason:' % prefix, total_reasons)
        for k in sorted(reason_counts.keys()):
            v = reason_counts[k]
            print('%sreason %11s: %d' % (prefix, k, v))
        print('\n%s== total return codes:' % prefix, total_rc)
        for k in sorted(rc_counts.keys()):
            v = rc_counts[k]
            print('%sreturn code %d: %d' % (prefix, k, v))
        print()

    if print_return_codes or print_parameters or run_summary:
        for run_name in sorted(status_data.keys()):
            if filter_run and run_name not in filter_run:
                continue
            run_data = status_data[run_name]

            reason = run_data.get('reason')
            if reason:
                sr_string = run_data['state'] + '; ' + reason
            else:
                sr_string = run_data['state']
            print(prefix + run_name + ':', sr_string)
            if not (print_return_codes or print_parameters):
                continue
            run_path = os.path.join(group_path, run_name)
            param_json_path = os.path.join(run_path,
                                           'codar.cheetah.run-params.json')
            rc = run_data.get('return_codes', {})
            with open(param_json_path) as f:
                all_params = json.load(f)
                for code_name in code_names:
                    if filter_code and code_name not in filter_code:
                        continue
                    # Note: return code could be None for some codes, so
                    # must use %s instead of %d
                    print('%s%s: %s'
                          % (prefix * 2, code_name, rc.get(code_name)))
                    if print_parameters:
                        code_params = all_params.get(code_name)
                        if not code_params:
                            # Note: middleware components like sosd and
                            # dataspaces will not be in the params file.
                            # TODO: should we change that?
                            continue
                        for k in sorted(code_params.keys()):
                            v = code_params[k]
                            print('%s%s=%s' % (prefix * 3, k, v))
        print()

    return status_data, state_counts, reason_counts, rc_counts
