#!/bin/bash

set -e

cd $(dirname $0)/../
CHEETAH_DIR=$(pwd)
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

for machine in local titan cori theta; do
    echo $machine-pi
    rm -rf test_output/$machine-pi/*
    ./cheetah.py -e examples/PiExperiment.py -m $machine \
        -a "$CODAR_APPDIR/Example-pi/" \
        -o test_output/$machine-pi

    echo $machine-param_test
    rm -rf test_output/$machine-param_test/*
    ./cheetah.py -e examples/param_test.py -m $machine \
        -a "$CHEETAH_DIR/examples/param_test/" \
        -o test_output/$machine-param_test
done

echo loal-heat-simple
rm -rf test_output/local-heat-simple/*
./cheetah.py -e examples/heat_transfer_simple.py -m local \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o test_output/local-heat-simple


# ------------- per component subdirs and inputs -----------

# Example to demonstrate running components in separate subdirs
# and specifying inputs files per component.
# Ok to generate campaign for testing, but will not run.
# Temporary example only, waiting for xgc spec file.

echo loal-heat-rc-subdirs-inputs
rm -rf test_output/local-heat-rc-subdirs-inputs/*
./cheetah.py -e examples/heat_transfer_simple_rc_subdirs_inputs.py -m local \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o test_output/local-heat-rc-subdirs-inputs

echo titan-heat-rc-subdirs-inputs
rm -rf test_output/titan-heat-rc-subdirs-inputs/*
./cheetah.py -e examples/heat_transfer_simple_rc_subdirs_inputs.py -m titan \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o test_output/titan-heat-rc-subdirs-inputs

# End ------------- per component subdirs and inputs -----------

echo titan-heat-simple
rm -rf test_output/titan-heat-simple/*
./cheetah.py -e examples/heat_transfer_simple.py -m titan \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o test_output/titan-heat-simple

echo titan-heat-sosflow
rm -rf test_output/titan-heat-sosflow/*
./cheetah.py -e examples/heat_transfer_sosflow.py -m titan \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o test_output/titan-heat-sosflow

echo titan-exaalt
rm -rf test_output/titan-exaalt/*
./cheetah.py -e examples/exaalt.py -m titan \
    -a "$CODAR_APPDIR/Example-EXAALT/" \
    -o test_output/titan-exaalt
