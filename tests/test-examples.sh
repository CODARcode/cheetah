#!/bin/bash

set -e

cd $(dirname $0)
TESTS_DIR=$(pwd)
cd ..
CHEETAH_DIR=$(pwd)
CHEETAH="$CHEETAH_DIR"/bin/cheetah.py
OUTDIR="$TESTS_DIR"/output
mkdir -p "$OUTDIR"
rm -rf "$OUTDIR"/*

if [ $# -gt 0 ]; then
    if [ "$1" == "-c" ]; then
        rm -rf "$OUTDIR"/*
    else
        echo "Error: unknown option '$1'"
        exit 1
    fi
fi

if [ "x$CODAR_APPDIR" == "x" ]; then
    echo "Error: set CODAR_APPDIR"
    exit 1
fi

# Allow running tests using a fake temporary appdir, to avoid having to
# compile the apps for doing basic testing.
if [ "$CODAR_APPDIR" == "fake" ]; then
    CODAR_APPDIR="$OUTDIR"/apps
    mkdir -p "$CODAR_APPDIR"/Example-pi
    touch    "$CODAR_APPDIR"/Example-pi/pi-gmp
    chmod +x "$CODAR_APPDIR"/Example-pi/pi-gmp

    mkdir    "$CODAR_APPDIR"/Example-Heat_Transfer
    cp       "$TESTS_DIR"/{heat_transfer.xml,dataspaces.conf} \
             "$CODAR_APPDIR"/Example-Heat_Transfer
    touch    "$CODAR_APPDIR"/Example-Heat_Transfer/heat_transfer_adios2
    touch    "$CODAR_APPDIR"/Example-Heat_Transfer/heat_transfer_adios2_tau
    chmod +x "$CODAR_APPDIR"/Example-Heat_Transfer/heat_*_adios2*

    mkdir    "$CODAR_APPDIR"/Example-Heat_Transfer/bin
    touch    "$CODAR_APPDIR"/Example-Heat_Transfer/bin/dataspaces_server
    chmod +x "$CODAR_APPDIR"/Example-Heat_Transfer/bin/*

    mkdir -p "$CODAR_APPDIR"/Example-EXAALT
    touch    "$CODAR_APPDIR"/Example-EXAALT/pt_producer_global
    chmod +x "$CODAR_APPDIR"/Example-EXAALT/*

    mkdir    "$CODAR_APPDIR"/Example-{EXAALT,Heat_Transfer}/stage_write
    touch    "$CODAR_APPDIR"/Example-{EXAALT,Heat_Transfer}/stage_write/stage_write_tau
    touch    "$CODAR_APPDIR"/Example-{EXAALT,Heat_Transfer}/stage_write/stage_write
    chmod +x "$CODAR_APPDIR"/Example-{EXAALT,Heat_Transfer}/stage_write/*
fi

for machine in local titan cori theta; do
    echo $machine-pi
    rm -rf "$OUTDIR"/$machine-pi/*
    $CHEETAH create-campaign -e examples/PiExperiment.py -m $machine \
        -a "$CODAR_APPDIR/Example-pi/" \
        -o "$OUTDIR"/$machine-pi

    echo $machine-param_test
    rm -rf "$OUTDIR"/$machine-param_test/*
    $CHEETAH create-campaign -e examples/param_test.py -m $machine \
        -a "$CHEETAH_DIR/examples/param_test/" \
        -o "$OUTDIR"/$machine-param_test

    echo $machine-heat_transfer_node_layout
    rm -rf "$OUTDIR"/$machine-heat_transfer_node_layout/*
    $CHEETAH create-campaign -e examples/heat_transfer_node_layout.py \
        -m $machine \
        -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
        -o "$OUTDIR"/$machine-heat_transfer_node_layout
done

# run local param test and analyze results, to exercise report generator
# and status subcommand
cd "$OUTDIR"/local-param_test
$USER/run-all.sh
$CHEETAH_DI$CHEETAH status . >status.log 2>&1
$USER/test/wait.sh >/dev/null
echo "Running generate-report for local-param_test..."
$CHEETAH_DI$CHEETAH generate-report . >report.log 2>&1
rval=$?
if [ ! -s campaign_results.csv -o $rval != 0 ]; then
    echo "ERROR: generate-report for local-param_test failed"
    echo "Return value: $rval"
    exit 1
fi
report_log_path="$(pwd)"/report.log
err_warn_count=$(grep -c 'WARN\|ERR' report.log || true)
if [ $err_warn_count != 0 ]; then
    echo "ERROR: generate-report log has warnings or errors," \
         "see '$report_log_path'"
    exit 1
else
    echo "generate-report succeeded, log is at '$report_log_path'"
fi

cd $CHEETAH_DIR

echo loal-heat-simple
rm -rf "$OUTDIR"/local-heat-simple/*
$CHEETAH create-campaign -e examples/heat_transfer_simple.py -m local \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o "$OUTDIR"/local-heat-simple


# ------------- per component subdirs and inputs -----------

# Example to demonstrate running components in separate subdirs
# and specifying inputs files per component.
# Ok to generate campaign for testing, but will not run.
# Temporary example only, waiting for xgc spec file.

echo loal-heat-rc-subdirs-inputs
rm -rf "$OUTDIR"/local-heat-rc-subdirs-inputs/*
$CHEETAH create-campaign \
    -e examples/heat_transfer_simple_rc_subdirs_inputs.py -m local \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o "$OUTDIR"/local-heat-rc-subdirs-inputs

echo titan-heat-rc-subdirs-inputs
rm -rf "$OUTDIR"/titan-heat-rc-subdirs-inputs/*
$CHEETAH create-campaign \
    -e examples/heat_transfer_simple_rc_subdirs_inputs.py -m titan \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o "$OUTDIR"/titan-heat-rc-subdirs-inputs

# End ------------- per component subdirs and inputs -----------

echo titan-heat-simple
rm -rf "$OUTDIR"/titan-heat-simple/*
$CHEETAH create-campaign -e examples/heat_transfer_simple.py -m titan \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o "$OUTDIR"/titan-heat-simple

echo titan-heat-sosflow
rm -rf "$OUTDIR"/titan-heat-sosflow/*
$CHEETAH create-campaign -e examples/heat_transfer_sosflow.py -m titan \
    -a "$CODAR_APPDIR/Example-Heat_Transfer/" \
    -o "$OUTDIR"/titan-heat-sosflow

echo titan-exaalt
rm -rf "$OUTDIR"/titan-exaalt/*
$CHEETAH create-campaign -e examples/exaalt.py -m titan \
    -a "$CODAR_APPDIR/Example-EXAALT/" \
    -o "$OUTDIR"/titan-exaalt
