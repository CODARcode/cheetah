#!/bin/bash

cd "$(dirname $0)"
source ../campaign-env.sh
source group-env.sh

GROUP_DIR=$(pwd)

if [ -f "$CODAR_CHEETAH_MACHINE_CONFIG" ]; then
    source "$CODAR_CHEETAH_MACHINE_CONFIG"
fi

JOBID=$(qsub \
        -A $CODAR_CHEETAH_SCHEDULER_ACCOUNT \
        -q $CODAR_CHEETAH_SCHEDULER_QUEUE \
        -N "$CODAR_CHEETAH_CAMPAIGN_NAME-$CODAR_CHEETAH_GROUP_NAME" \
        -l nodes=$CODAR_CHEETAH_GROUP_NODES \
        -l walltime=$CODAR_CHEETAH_GROUP_WALLTIME \
        run-group.pbs "$GROUP_DIR")

echo "$JOBID" > codar.cheetah.jobid.txt
