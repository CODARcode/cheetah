#!/bin/bash

cd $(dirname $0)
bkill $(cat codar.cheetah.jobid.txt | cut -d: -f2)
