#!/bin/bash

spack load adios2@2.6.0
spack load py-mpi4py
export PYTHONPATH=/home/kmehta/spack/opt/spack/linux-debian10-sandybridge/gcc-8.3.0/adios2-2.6.0-vbzu74xnnhdkui4iexoh7vezngqtgkap/lib/python3/dist-packages/:$PYTHONPATH

