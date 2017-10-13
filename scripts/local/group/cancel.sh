#!/bin/bash

cd $(dirname $0)

if [ ! -f codar.cheetah.jobid.txt ]; then
    echo "Job ID file 'codar.cheetah.jobid.txt' not found"
    exit 1
fi

kill $(cat codar.cheetah.jobid.txt | cut -d: -f2)
