#!/usr/bin/env python

####!/ccs/home/iyakushin/.conda/envs/Test11/bin/python

#
# Distributed under the OSI-approved Apache License, Version 2.0.  See
# accompanying file Copyright.txt for details.
#
# This is a simple producer code that writes a 1D array over n timesteps.
# Data is written using ADIOS.

from mpi4py import MPI
import adios2
import numpy as np
import sys
import time


def parse_input_args(local_arr_size, num_steps):
    if len(sys.argv) != 3:
        if rank == 0:
            print_usage()
        sys.exit(-1)

    local_arr_size = int(sys.argv[1])
    num_steps = int(sys.argv[2])
    return (local_arr_size, num_steps)

def print_usage():
    print ("Input arguments needed: size-per-process number-of-timesteps")

def set_val(myarray, arr_size, stepid, rank):
    time.sleep(1)
    for i in range(arr_size):
        myarray[i] = stepid*i + rank*100


# MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Parse input args
local_arr_size = 1024*1024
num_steps = 10
(local_arr_size, num_steps) = parse_input_args(local_arr_size, num_steps)
if rank==0:
    print ("{} size-per-process: {}, num-steps: {}".format(sys.argv[0], local_arr_size, num_steps))

# User data
myArray = np.arange(local_arr_size)
nx = myArray.size

# ADIOS
adios = adios2.ADIOS("adios2.xml", comm, adios2.DebugON)
#adios = adios2.ADIOS("adios2.xml", adios2.DebugON)

# IO
bpIO = adios.DeclareIO("producer")

# Variables
bpArray = bpIO.DefineVariable("psi", myArray, [size * nx], [rank * nx], [nx],
                              adios2.ConstantDims)

# Engine
bpFileWriter = bpIO.Open("diagnostics.bp", adios2.Mode.Write, MPI.COMM_WORLD)
#bpFileWriter = bpIO.Open("diagnostics.bp", adios2.Mode.Write)

for t in range(0, 10):
    set_val(myArray, local_arr_size, t, rank)
    if rank == 0:
        print ("Step {}:".format(t))
    bpFileWriter.BeginStep()
    bpFileWriter.Put(bpArray, myArray)
    bpFileWriter.EndStep()

bpFileWriter.Close()

