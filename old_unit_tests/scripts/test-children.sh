#!/bin/bash

cd $(dirname $0)

NCHILDREN=$1

echo Launching ignore term child
./test-ignore-term.sh &

echo Launching $NCHILDREN children...
for i in $(seq 1 $NCHILDREN); do
    ./test.sh child$i "$@" &
done
echo done launching all background children

./test.sh foreground "$@"
