#!/bin/bash

# Use workflow script to run jobs in group. Assumes environment configuration
# has already been done by calling script (submit.sh).

cd "$(dirname $0)"

if [ -n "$CODAR_CHEETAH_UMASK" ]; then
    umask "$CODAR_CHEETAH_UMASK"
fi

start=$(date +%s)

# Main application run
"$CODAR_PYTHON" "$CODAR_WORKFLOW_SCRIPT" --runner=$CODAR_WORKFLOW_RUNNER \
 --max-nodes=$CODAR_CHEETAH_GROUP_MAX_PROCS \
 --processes-per-node=1 \
 --producer-input-file=fobs.json \
 --log-file=codar.FOBrun.log \
 --machine-name=$CODAR_CHEETAH_MACHINE_NAME \
 --status-file=codar.workflow.status.json \
 --log-level=$CODAR_CHEETAH_WORKFLOW_LOG_LEVEL

end=$(date +%s)
echo $(($end - $start)) > codar.cheetah.walltime.txt

# TODO: Post processing
#"{post_processing}" "{group_directory}"
