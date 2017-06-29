#!/bin/bash

set -e

cd $(dirname $0)/../
mkdir -p test_output

if [ $# -gt 0 ]; then
    if [ "$1" == "-c" ]; then
        rm -rf test_output/*
    else
        echo "Error: unknown option '$1'"
        exit 1
    fi
fi

if [ "x$CODAR_APPDIR" == "x" ]; then
    echo "Error: set CODAR_APPDIR"
    exit 1
fi

if [ "x$CODAR_MPIX_LAUNCH" == "x" ]; then
    echo "Error: set CODAR_MPIX_LAUNCH"
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
