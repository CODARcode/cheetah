#!/bin/bash

# savanna packages pre-installed on titan
module load adios/1.12.0 flexpath/1.12

# swift pre-installed on titan
export PATH=~wozniak/Public/sfw/login/swift-t/stc/bin:~wozniak/Public/sfw/login/swift-t/turbine/bin:$PATH
export TITAN=true
export LD_LIBRARY_PATH=/sw/xk6/deeplearning/1.0/sles11.3_gnu4.9.3/lib:/sw/xk6/deeplearning/1.0/sles11.3_gnu4.9.3/cuda/lib64:/opt/gcc/4.9.3/snos/lib64

# swift extension
export CODAR_MPIX_LAUNCH=/lustre/atlas/world-shared/csc143/kmehta/mpix_launch_swift/src
