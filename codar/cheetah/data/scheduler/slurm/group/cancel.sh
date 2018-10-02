#!/bin/bash

cd $(dirname $0)
scancel $(cat codar.cheetah.jobid.txt | cut -d: -f2)
