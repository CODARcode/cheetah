#!/bin/bash

if [ ! -f codar.cheetah.jobid.txt ]; then
    echo "Job ID file 'codar.cheetah.jobid.txt' not found"
    exit 1
fi

cd $(dirname $0)
ps -p $(cat codar.cheetah.jobid.txt | cut -d: -f2) -o time=
