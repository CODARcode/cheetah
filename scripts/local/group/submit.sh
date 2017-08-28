#!/bin/bash

cd "$(dirname $0)"
source ../campaign-env.sh
source group-env.sh

if [ -f "$CODAR_CHEETAH_MACHINE_CONFIG" ]; then
    source "$CODAR_CHEETAH_MACHINE_CONFIG"
fi

# TODO: convert from HH:MM:SS format used by pbs etc to seconds
timeout $CODAR_CHEETAH_GROUP_WALLTIME ./run-group.sh &
JOBID="PID:$!"
echo "$JOBID" > codar.cheetah.jobid.txt
