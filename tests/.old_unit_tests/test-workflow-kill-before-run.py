#!/usr/bin/env python3

from common_workflow import run_workflow, STATUS_FILE

if __name__ == '__main__':
    nruns = 10
    ncodes = 2
    max_procs = 4
    max_nodes = None
    processes_per_node = None
    timeout = 10
    kill_on_partial_failure = True

    p = run_workflow(nruns, ncodes, max_procs, max_nodes, processes_per_node,
                     timeout, kill_on_partial_failure,
                     test_script='test-immediate-fail.sh',
                     sleep_after=[5, 0])
    p.wait()
    with open(STATUS_FILE) as f:
        print(f.read())
