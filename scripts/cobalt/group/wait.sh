#!/bin/bash

cd $(dirname $0)
JOBID=$(cat codar.cheetah.jobid.txt | cut -d: -f2)
while [ "$(qstat -f $JOBID | grep job_state | awk -F' = ' '{ print $2 }')" != "C" ]; do
    sleep 1
done
cat codar.cheetah.walltime.txt
