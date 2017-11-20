#!/bin/bash

cd "$(dirname $0)"
source ../campaign-env.sh
source group-env.sh

if [ -f "$CODAR_CHEETAH_MACHINE_CONFIG" ]; then
    source "$CODAR_CHEETAH_MACHINE_CONFIG"
fi

if [ -n "$CODAR_CHEETAH_APP_CONFIG" ]; then
    source "$CODAR_CHEETAH_APP_CONFIG"
fi

timeout $CODAR_CHEETAH_GROUP_WALLTIME ./run-group.sh &
JOBID="PID:$!"
echo "$JOBID" > codar.cheetah.jobid.txt
