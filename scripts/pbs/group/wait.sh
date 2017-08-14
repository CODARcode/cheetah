#!/bin/bash

cd $(dirname $0)
PID=$(cat codar.cheetah.jobid.txt | cut -d: -f2)
while [ -n "$(ps -p $PID -o time=)" ]; do
    sleep 1
done
cat codar.cheetah.walltime.txt
