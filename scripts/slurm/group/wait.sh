#!/bin/bash

cd $(dirname $0)
JOBID=$(cat codar.cheetah.jobid.txt | cut -d: -f2)
while true; do
    state=$(squeue -o '%t' -j $JOBID)
    case "$state" in
    BF|CA|CD|F|NF|PR|TO)
        break
        ;;
    esac
    sleep 1
done
cat codar.cheetah.walltime.txt
