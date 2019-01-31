#!/bin/bash

function error_exit
{
	echo "$1" 1>&2
	exit 1
}

cd $(dirname $0)
source campaign-env.sh || error_exit "Failed to load compaign-env.sh, aborting"

if [ -z "$CODAR_CHEETAH_EXPERIMENT_DIR" ]; then
    error_exit "Missing env var CODAR_CHEETAH_EXPERIMENT_DIR, aborting"
fi

cd $CODAR_CHEETAH_EXPERIMENT_DIR || exit_exit "Missing experiment dir '$CODAR_CHEETAH_EXPERIMENT_DIR', aborting"
group_dirs=$(find . -maxdepth 1 -mindepth 1 -type d)
for group_dir in $group_dirs; do
    echo "Submitting $group_dir"
    cd "$group_dir" || exit_exit "Missing group dir '$group_dir', aborting"
    ./submit.sh || exit_exit "Failed to submit group '$group_dir', aborting"
    cd ..
done
