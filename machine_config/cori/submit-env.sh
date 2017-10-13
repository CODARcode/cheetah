#!/bin/bash

source $MODULESHOME/init/bash

# savanna packages pre-installed on cori
module load python/3.6-anaconda-4.4 cray-mpich/7.6.0
spack load adios@1.12.0 flexpath@1.12
