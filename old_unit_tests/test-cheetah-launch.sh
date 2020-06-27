#!/bin/bash

SRC_DIR=$(dirname $0)/../

mkdir /tmp/cheetah-launch
touch /tmp/cheetah-launch/{a,b,c}
rm codar.cheetah.std* >/dev/null
echo "Should list contents of /tmp/cheetah-launch with -l -a:"
$SRC_DIR/scripts/cheetah-launch.sh /tmp/cheetah-launch ls -l -a

cat /tmp/cheetah-launch/codar.cheetah.std*
