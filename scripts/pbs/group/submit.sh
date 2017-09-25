#!/bin/bash

cd "$(dirname $0)"
source ../campaign-env.sh
source group-env.sh

if [ -f "$CODAR_CHEETAH_MACHINE_CONFIG" ]; then
    source "$CODAR_CHEETAH_MACHINE_CONFIG"
fi

# convert walltime from seconds to HH:MM:SS format needed by PBS

secs=$CODAR_CHEETAH_GROUP_WALLTIME
PBS_WALLTIME=$(printf '%02d:%02d:%02d\n' $(($secs/3600)) $(($secs%3600/60)) $(($secs%60)))

OUTPUT=$(qsub \
        -A $CODAR_CHEETAH_SCHEDULER_ACCOUNT \
        -q $CODAR_CHEETAH_SCHEDULER_QUEUE \
        -N "$CODAR_CHEETAH_CAMPAIGN_NAME-$CODAR_CHEETAH_GROUP_NAME" \
        -l nodes=$CODAR_CHEETAH_GROUP_NODES \
        -l walltime=$PBS_WALLTIME \
        run-group.pbs)

rval=$?

if [ $rval != 0 ]; then
    echo "SUBMIT FAILED:"
    echo $OUTPUT
    exit $rval
fi

JOBID=$OUTPUT

echo "PBS:$JOBID" > codar.cheetah.jobid.txt
