#!/bin/bash

# Note: slurm uses parent dir of sbatch script as working dir by default

source ../campaign-env.sh
source group-env.sh

if [ -f "$CODAR_CHEETAH_MACHINE_CONFIG" ]; then
    source "$CODAR_CHEETAH_MACHINE_CONFIG"
fi

if [ -n "$CODAR_CHEETAH_GROUP_NODE_EXCLUSIVE" ]; then
    max_args="--max-nodes=$CODAR_CHEETAH_GROUP_NODES --processes-per-node=$CODAR_CHEETAH_GROUP_PROCESSES_PER_NODE"
else
    max_args="--max-procs=$CODAR_CHEETAH_GROUP_MAX_PROCS"
fi

start=$(date +%s)

# Main application run
"$CODAR_WORKFLOW_SCRIPT" --runner=$CODAR_WORKFLOW_RUNNER \
 $max_args \
 --producer-input-file=fobs.json \
 --log-file=codar.FOBrun.log \
 --status-file=codar.workflow.status.json \
 --log-level=$CODAR_CHEETAH_WORKFLOW_LOG_LEVEL

end=$(date +%s)
echo $(($end - $start)) > codar.cheetah.walltime.txt

# TODO: Post processing
#"{post_processing}" "{group_directory}"
