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

for machine in local titan cori; do
    rm -rf test_output/$machine-pi/*
    ./cheetah.py -e examples/PiExperiment.py -m $machine \
        -a "$CODAR_APPDIR/Example-pi/" \
        -o test_output/$machine-pi
done

rm -rf test_output/local-heat-simple/*
./cheetah.py -e examples/heat_transfer_simple.py -m local \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o test_output/local-heat-simple

rm -rf test_output/titan-heat-simple/*
./cheetah.py -e examples/heat_transfer_simple.py -m titan \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o test_output/titan-heat-simple

rm -rf test_output/titan-heat-sosflow/*
./cheetah.py -e examples/heat_transfer_sosflow.py -m titan \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o test_output/titan-heat-sosflow

rm -rf test_output/titan-exaalt/*
./cheetah.py -e examples/exaalt.py -m titan \
    -a "$CODAR_APPDIR/Example-EXAALT/" \
    -o test_output/titan-exaalt
