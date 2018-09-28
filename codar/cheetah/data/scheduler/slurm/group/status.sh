#!/bin/bash

cd $(dirname $0)
squeue -j $(cat codar.cheetah.jobid.txt | cut -d: -f2)
