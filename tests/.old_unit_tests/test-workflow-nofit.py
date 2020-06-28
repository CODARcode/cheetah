#!/usr/bin/env python3

# Test what happens when a FOB that won't fit on given max nodes is
# submitted to workflow.

import sys

from common_workflow import run_workflow, STATUS_FILE, LOG_FILE


if __name__ == '__main__':
    nruns = 10
    ncodes = 3
    max_procs = None
    max_nodes = 4
    processes_per_node = 16
    # 4 * 16 = 64 total procs available, but with node exclusive, they
    # can't all necessarily be used. In this case, the first code needs
    # only one proc but still takes one node, second code takes two, and
    # thrid code also requires two, so 5 nodes are required and only 4
    # are allowed.
    codes_nprocs = [1, 32, 17]
    timeout = 20
    kill_on_partial_failure = False

    p = run_workflow(nruns, ncodes, max_procs, max_nodes, processes_per_node,
                     timeout, kill_on_partial_failure,
                     codes_nprocs=codes_nprocs)
    p.wait()

    with open(STATUS_FILE) as f:
        print("STATUS")
        print(f.read())

    with open(LOG_FILE) as f:
        print("LOG")
        print(f.read())
