#!/usr/bin/env python3

from common_workflow import run_workflow, STATUS_FILE

if __name__ == '__main__':
    nruns = 10
    ncodes = 2
    max_procs = 4
    max_nodes = None
    processes_per_node = None
    timeout = 5
    kill_on_partial_failure = False

    p = run_workflow(nruns, ncodes, max_procs, max_nodes, processes_per_node,
                     timeout, kill_on_partial_failure,
                     test_script='test-children.sh',
                     test_script_args=['4'],
                     sleep_after=[5, 0])
    p.wait()
    with open(STATUS_FILE) as f:
        print(f.read())
