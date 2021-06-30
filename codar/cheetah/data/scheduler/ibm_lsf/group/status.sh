#!/bin/bash

cd $(dirname $0)
bjobs $(cat codar.cheetah.jobid.txt | cut -d '<' -f2 | cut -d '>' -f1)

