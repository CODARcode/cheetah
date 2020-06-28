#!/bin/bash

cd $(dirname $0)

# nruns ncodes max_procs timeout kill_on_partial_failure
./test-workflow.py 10 2 4 10 1 1
