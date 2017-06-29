#!/bin/bash

cd $(dirname $0)/../
mkdir -p test_output

if [ "x$CODAR_APPDIR" == "x" ]; then
    echo "Error: set CODAR_APPDIR"
    exit 1
fi

if [ "x$CODAR_LAUNCH_MULTI" == "x" ]; then
    echo "Error: set CODAR_LAUNCH_MULTI"
    exit 1
fi

export CODAR_LAUNCH_MULTI

./cheetah.py -e examples/PiExperiment.py -m local \
    -a "$CODAR_APPDIR/Example-pi/" \
    -o test_output/pi

./cheetah.py -e examples/PiExperiment.py -m local_launch_multi \
    -a "$CODAR_APPDIR/Example-pi/" \
    -o test_output/pi-launch-multi

./cheetah.py -e examples/heat_transfer_small.py -m local_launch_multi \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o test_output/heat-lauch-multi
