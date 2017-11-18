#!/bin/bash

cd "$(dirname $0)"
source ../campaign-env.sh
source group-env.sh

if [ -f "$CODAR_CHEETAH_MACHINE_CONFIG" ]; then
    source "$CODAR_CHEETAH_MACHINE_CONFIG"
fi

# Cobalt qsub supports both HH:MM:SS and minutes, use the former for
# consistency with PBS.
secs=$CODAR_CHEETAH_GROUP_WALLTIME
HMS_WALLTIME=$(printf '%02d:%02d:%02d\n' $(($secs/3600)) $(($secs%3600/60)) $(($secs%60)))

OUTPUT=$(qsub \
        --project=$CODAR_CHEETAH_SCHEDULER_ACCOUNT \
        --queue=$CODAR_CHEETAH_SCHEDULER_QUEUE \
        --nodecount=$CODAR_CHEETAH_GROUP_NODES \
        --time $HMS_WALLTIME \
        --jobname="$CODAR_CHEETAH_CAMPAIGN_NAME-$CODAR_CHEETAH_GROUP_NAME" \
        run-group.cobalt)

rval=$?

if [ $rval != 0 ]; then
    echo "SUBMIT FAILED:"
    echo $OUTPUT
    exit $rval
fi

JOBID=$OUTPUT

echo "COBALT:$JOBID" > codar.cheetah.jobid.txt
