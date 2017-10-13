import os
import json
import shutil
from subprocess import check_call, check_output, Popen

CHEETAH_DIR = os.path.abspath(os.path.join(
                        os.path.dirname(__file__), '..'))
OUT_DIR = os.path.join(CHEETAH_DIR, 'test_output', 'workflow')
STATUS_FILE = os.path.join(OUT_DIR, 'status.json')

def test_workflow(*args, **kw):
    p = run_workflow(*args, **kw)
    p.wait()
    show_results()


def run_workflow(nruns, ncodes, max_procs, max_nodes, processes_per_node,
                 timeout, kill_on_partial_failure):
    if kill_on_partial_failure:
        test_script = os.path.join(CHEETAH_DIR, 'scripts', 'test-randfail.sh')
    else:
        test_script = os.path.join(CHEETAH_DIR, 'scripts', 'test.sh')

    # clean up after old runs, ignore if doesn't exist
    shutil.rmtree(OUT_DIR, ignore_errors=True)

    # recreate
    os.makedirs(OUT_DIR)

    # generate pipelines file and save
    pipelines_file_path = os.path.join(OUT_DIR, 'pipelines.json')
    with open(pipelines_file_path, 'w') as f:
        for i in range(nruns):
            work_dir = os.path.join(OUT_DIR, 'run%02d' % (i+1))
            os.makedirs(work_dir)
            # dynamicly construct a pipeline
            runs_data = []
            for j in range(ncodes):
                run_data = dict(name='code%02d' % (j+1),
                                exe=test_script,
                                args=['test spaces', str(i), str(j),
                                      'test \' quote'],
                                env=dict(CODAR_WORKFLOW_PIPE=str(i),
                                         CODAR_WORKFLOW_CODE=str(j)),
                                timeout=timeout)
                runs_data.append(run_data)
            pipeline_data = dict(id=str(i), runs=runs_data,
                working_dir=work_dir,
                kill_on_partial_failure=kill_on_partial_failure)
            json.dump(pipeline_data, f)
            f.write('\n')

    if max_procs is not None:
        max_args = ['--max-procs=%d' % max_procs]
    else:
        max_args = ['--max-nodes=%d' % max_nodes,
                    '--processes-per-node=%d' % processes_per_node]

    p = Popen([CHEETAH_DIR + '/workflow.py', '--runner=none',
               '--producer-input-file=%s' % pipelines_file_path,
               '--status-file=%s' % STATUS_FILE,
               '--log-file=%s' % os.path.join(OUT_DIR, 'run.log'),
               '--log-level=DEBUG'] + max_args)
    return p


def show_results():
    times = check_output('grep "^start\\|end" "%s"/run*/*std* | grep -v "ENV "'
                         % OUT_DIR, shell=True)
    times = times.decode('utf8')
    for line in times.split('\n'):
        print(line[len(OUT_DIR)+1:])

    rcodes = check_output('grep "" "%s"/run*/*return*' % OUT_DIR, shell=True)
    rcodes = rcodes.decode('utf8')
    for line in rcodes.split('\n'):
        print(line[len(OUT_DIR)+1:])

    with open(STATUS_FILE) as f:
        print(f.read())
