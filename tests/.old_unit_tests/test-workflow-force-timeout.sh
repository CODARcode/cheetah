#!/bin/bash

cd $(dirname $0)

# nruns ncodes max_procs timeout
./test-workflow.py 10 2 4 2
