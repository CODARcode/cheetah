#!/usr/bin/env python3

import sys
import os
import json
import shutil
from subprocess import check_call, check_output


def test_workflow(nruns, ncodes, max_procs, max_nodes, processes_per_node,
                  timeout, kill_on_partial_failure):
    cheetah_dir = os.path.abspath(os.path.join(
                            os.path.dirname(__file__), '..'))
    out_dir = os.path.join(cheetah_dir, 'test_output', 'workflow')
    if kill_on_partial_failure:
        test_script = os.path.join(cheetah_dir, 'scripts', 'test-randfail.sh')
    else:
        test_script = os.path.join(cheetah_dir, 'scripts', 'test.sh')

    # clean up after old runs, ignore if doesn't exist
    shutil.rmtree(out_dir, ignore_errors=True)

    # recreate
    os.makedirs(out_dir)

    # generate pipelines file and save
    pipelines_file_path = os.path.join(out_dir, 'pipelines.json')
    with open(pipelines_file_path, 'w') as f:
        for i in range(nruns):
            work_dir = os.path.join(out_dir, 'run%02d' % (i+1))
            os.makedirs(work_dir)
            # dynamicly construct a pipeline
            pipeline_data = []
            for j in range(ncodes):
                run_data = dict(name='code%02d' % (j+1),
                                exe=test_script,
                                args=['test spaces', str(i), str(j),
                                      'test \' quote'],
                                working_dir=work_dir,
                                env=dict(CODAR_WORKFLOW_PIPE=str(i),
                                         CODAR_WORKFLOW_CODE=str(j)),
                                timeout=timeout)
                pipeline_data.append(run_data)
            json.dump(pipeline_data, f)
            f.write('\n')

    if max_procs is not None:
        max_args = ['--max-procs=%d' % max_procs]
    else:
        max_args = ['--max-nodes=%d' % max_nodes,
                    '--processes-per-node=%d' % processes_per_node]

    if kill_on_partial_failure:
        max_args += ['--kill-on-partial-failure']

    check_call([cheetah_dir + '/workflow.py', '--runner=none',
                '--producer-input-file=%s' % pipelines_file_path,
                '--log-file=%s' % os.path.join(out_dir, 'run.log'),
                '--log-level=DEBUG'] + max_args)
    times = check_output('grep "^start\\|end" "%s"/run*/*std* | grep -v "ENV "'
                         % out_dir, shell=True)
    times = times.decode('utf8')
    for line in times.split('\n'):
        print(line[len(out_dir)+1:])

    rcodes = check_output('grep "" "%s"/run*/*return*' % out_dir, shell=True)
    rcodes = rcodes.decode('utf8')
    for line in rcodes.split('\n'):
        print(line[len(out_dir)+1:])


if __name__ == '__main__':
    nruns = 10
    ncodes = 2
    max_procs = 4
    max_nodes = None
    processes_per_node = None
    timeout = 10
    kill_on_partial_failure = False
    if len(sys.argv) > 1:
        nruns = int(sys.argv[1])
    if len(sys.argv) > 2:
        ncodes = int(sys.argv[2])
    if len(sys.argv) > 3:
        max_procs = int(sys.argv[3])
    if len(sys.argv) > 4:
        timeout = int(sys.argv[4])
    if len(sys.argv) > 5:
        max_nodes = max_procs
        max_procs = None
        processes_per_node = int(sys.argv[5])
    if len(sys.argv) > 6:
        kill_on_partial_failure = True

    test_workflow(nruns, ncodes, max_procs, max_nodes, processes_per_node,
                  timeout, kill_on_partial_failure)
