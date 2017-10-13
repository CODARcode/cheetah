#!/bin/bash

cd $(dirname $0)
qdel $(cat codar.cheetah.jobid.txt | cut -d: -f2)
