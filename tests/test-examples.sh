#!/bin/bash

cd $(dirname $0)/../
mkdir -p test_output

if [ "x$CODAR_APPDIR" == "x" ]; then
    echo "Error: set CODAR_APPDIR"
    exit 1
fi

./cheetah.py -e examples/PiExperiment.py -m local \
    -a "$CODAR_APPDIR/Example-pi/" \
    -o test_output/pi

./cheetah.py -e examples/heatmap.py -m local \
    -a "$CODAR_APPDIR/Example-heatmap/" \
    -o test_output/heatmap
