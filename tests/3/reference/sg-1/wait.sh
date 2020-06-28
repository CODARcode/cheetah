#!/bin/bash

cd $(dirname $0)
PID=$(cat codar.cheetah.jobid.txt | cut -d: -f2)
while [ -n "$(ps -p $PID -o time=)" ]; do
    sleep 1
done
if [ -f codar.cheetah.walltime.txt ]; then
    cat codar.cheetah.walltime.txt
else
    echo "ERR: walltime file 'codar.cheetah.walltime.txt' not found"
fi
