#!/bin/bash

if [ -f "$CODAR_CHEETAH_MACHINE_CONFIG" ]; then
    source "$CODAR_CHEETAH_MACHINE_CONFIG"
fi

cd $CODAR_CHEETAH_EXPERIMENT_DIR/$CODAR_CHEETAH_GROUP_DIR

JOBID=$(qsub \
        -A $CODAR_CHEETAH_SCHEDULER_ACCOUNT \
        -q $CODAR_CHEETAH_SCHEDULER_QUEUE \
        -N "$CODAR_CHEETAH_CAMPAIGN_NAME-$CODAR_CHEETAH_GROUP_NAME" \
        -l nodes=$CODAR_CHEETAH_GROUP_NODES \
        -l walltime=$CODAR_CHEETAH_GROUP_WALLTIME \
        run-group.pbs)

echo "$JOBID" > codar.cheetah.jobid.txt
