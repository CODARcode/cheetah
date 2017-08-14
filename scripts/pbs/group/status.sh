#!/bin/bash

cd $(dirname $0)
ps -p $(cat codar.cheetah.jobid.txt | cut -d: -f2) -o time=
