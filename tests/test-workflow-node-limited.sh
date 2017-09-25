#!/bin/bash

cd $(dirname $0)

# nruns ncodes max_nodes timeout ppn
./test-workflow.py 10 2 4 10 4
