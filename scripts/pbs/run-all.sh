#!/bin/bash
set -e

cd /home/bda/codar/cheetah/test_output/titan-heat
start=$(date +%s)
for group_dir in group-*; do
    echo -n "Start $group_dir ... "
    cd "$group_dir"
    ./submit.sh
    ./wait.sh
    cd ..
done
end=$(date +%s)
echo $(($end - $start)) > codar.cheetah.walltime.txt
