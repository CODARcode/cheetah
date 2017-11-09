#!/bin/bash

source $MODULESHOME/init/bash

# copied in part from /ccs/proj/csc143/CODAR_Demo/titan.gnu/tau/sourceme.sh

module load python/3.5.1
export LD_LIBRARY_PATH=/ccs/proj/csc143/CODAR_Demo/titan.gnu/adios/lib/:$LD_LIBRARY_PATH
