#!/bin/bash

cd $(dirname $0)
qstat $(cat codar.cheetah.jobid.txt | cut -d: -f2)
