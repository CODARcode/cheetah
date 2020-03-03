#!/usr/bin/env python3

#
# Distributed under the OSI-approved Apache License, Version 2.0.  See
# accompanying file Copyright.txt for details.
#
# helloBPReaderHeatMap2D.py
#
#
#  Created on: Dec 5th, 2017
#      Author: William F Godoy godoywf@ornl.gov
#

from mpi4py import MPI
import numpy
import adios2
import time
import sys

# MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# ADIOS portion
adios = adios2.ADIOS("adios2.xml", comm, adios2.DebugON)
ioRead = adios.DeclareIO("producer")

ibpStream = ioRead.Open('diagnostics.bp', adios2.Mode.Read, MPI.COMM_WORLD)

while(True):
    time.sleep(2)
    stepstat = ibpStream.BeginStep()
    if stepstat == adios2.StepStatus.EndOfStream:
        if rank==0:
            print("{} encountered end of stream. Exiting ..".format(sys.argv[0]))
        break
    
    curStep = ibpStream.CurrentStep()
    if rank == 0:
        print("Parsing step {}".format(curStep))

    var_psi = ioRead.InquireVariable("psi")
    assert var_psi is not None, "could not find psi"
    psi_size = var_psi.Shape()
    if rank == 0:
        print ("Size of psi: {}".format(psi_size))
    
    var_psi.SetSelection([ [psi_size[0]//size * rank], [psi_size[0]//size] ])

    inSize = var_psi.SelectionSize()
    if curStep == 0:
        psi = numpy.zeros(inSize, dtype=numpy.int)
    
    ibpStream.Get(var_psi, psi)
    ibpStream.EndStep()
    print("Rank {}: Mean of values of psi in step {}: {}".format(rank, curStep, numpy.mean(psi)))

ibpStream.Close()

