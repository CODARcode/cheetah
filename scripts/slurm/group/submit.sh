#!/bin/bash

cd "$(dirname $0)"
source ../campaign-env.sh
source group-env.sh

if [ -f "$CODAR_CHEETAH_MACHINE_CONFIG" ]; then
    source "$CODAR_CHEETAH_MACHINE_CONFIG"
fi

# convert walltime from seconds to HH:MM:SS format needed by PBS

secs=$CODAR_CHEETAH_GROUP_WALLTIME
SLURM_WALLTIME=$(printf '%02d:%02d:%02d\n' $(($secs/3600)) $(($secs%3600/60)) $(($secs%60)))

OUTPUT=$(sbatch --parsable \
        -A $CODAR_CHEETAH_SCHEDULER_ACCOUNT \
        -p $CODAR_CHEETAH_SCHEDULER_QUEUE \
        -J "$CODAR_CHEETAH_CAMPAIGN_NAME-$CODAR_CHEETAH_GROUP_NAME" \
        -N $CODAR_CHEETAH_GROUP_NODES \
        -t $SLURM_WALLTIME \
        -C haswell \ # TODO: add option to use knl
        -L SCRATCH,project \ # TODO: add option to configure filesystems
        run-group.sbatch)

rval=$?

if [ $rval != 0 ]; then
    echo "SUBMIT FAILED:"
    echo $OUTPUT
    exit $rval
fi

JOBID=$OUTPUT

echo "SLURM:$JOBID" > codar.cheetah.jobid.txt
