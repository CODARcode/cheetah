#!/bin/bash

cd "$(dirname $0)"
source ../campaign-env.sh
source group-env.sh

if [ -f "$CODAR_CHEETAH_MACHINE_CONFIG" ]; then
    source "$CODAR_CHEETAH_MACHINE_CONFIG"
fi

# Don't submit job if all experiments have been run
if [ -f codar.workflow.status.json ]; then
    grep state codar.workflow.status.json | grep -q 'not_started'
    if [ $? != 0 ]; then
        echo "No more experiments remaining. Skipping group .."
        exit
    fi
fi

# Copy the env setup to the Sweep Group
if [ -n "$CODAR_CHEETAH_APP_CONFIG" ]; then
  ENV_SETUP_SCRIPT="codar.savanna.env_setup.$CODAR_CHEETAH_MACHINE_NAME"
  cp "$CODAR_CHEETAH_APP_CONFIG" "$ENV_SETUP_SCRIPT"
fi

# Gather flags for gpumps and SMT level to be passed on to -alloc_flags
alloc_flags=

# convert walltime from seconds to HH:MM format needed by LSF
secs=$CODAR_CHEETAH_GROUP_WALLTIME
LSF_WALLTIME=$(printf '%02d:%02d\n' $(($secs/3600)) $(($secs%3600/60)))

extra_args=""
if [ -n "$CODAR_CHEETAH_SCHEDULER_RESERVATION" ]; then
  extra_args="$extra_args -U $CODAR_CHEETAH_SCHEDULER_RESERVATION"
fi

OUTPUT=$(bsub \
        -P $CODAR_CHEETAH_SCHEDULER_ACCOUNT \
        -J "$CODAR_CHEETAH_CAMPAIGN_NAME-$CODAR_CHEETAH_GROUP_NAME" \
        -nnodes $CODAR_CHEETAH_GROUP_NODES \
        -W $LSF_WALLTIME \
        -alloc_flags "gpudefault NVME" \
        $extra_args \
        run-group.lsf)

rval=$?

if [ $rval != 0 ]; then
    echo "SUBMIT FAILED:"
    echo $OUTPUT
    exit $rval
fi

JOBID=$OUTPUT

echo "LSF:$JOBID" > codar.cheetah.jobid.txt

