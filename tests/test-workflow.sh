#!/bin/bash

set -e

cd $(dirname $0)/../
SRC_DIR=$(pwd)

TIMEOUT=10
mkdir -p test_output/workflow
PIPELINES=test_output/workflow/pipelines.json
rm -f $PIPELINES

for i in $(seq 16); do
    workdir="test_output/workflow/run$i"
    mkdir -p "$workdir"
    rm -f "$workdir"/*
    echo "[{\"name\":\"first\", \"exe\":\"$SRC_DIR/scripts/test.sh\", \"args\":[\"first\", \"$i\"], \"working_dir\":\"$workdir\"},{\"name\":\"second\", \"exe\":\"$SRC_DIR/scripts/test.sh\", \"args\":[\"second\", \"$i\"], \"working_dir\":\"$workdir\"}]" \
        >> $PIPELINES
done


./workflow.py --runner=none --max-procs=4 --producer-input-file=$PIPELINES
cat test_output/workflow/run*/*std*
