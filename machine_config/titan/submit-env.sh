#!/bin/bash

source $MODULESHOME/init/bash

# copied in part from /ccs/proj/csc143/CODAR_Demo/titan.gnu/tau/sourceme.sh

module load python/3.5.1
module load papi
module load cmake
module load flexpath/1.12
module load dataspaces/1.6.2
module load adios/1.12.0

# TODO: are these necessary and sufficiently general? Also this won't
# work if user is not a member of csc143.
BASEDIR=/ccs/proj/csc143/CODAR_Demo/titan.gnu
export TAU_ROOT=${BASEDIR}/tau
export SOS_ROOT=${BASEDIR}/sos_flow
TAU_ARCH=craycnl
TAU_CONFIG=tau-gnu-mpi-pthread-pdt-sos-adios

# set TAU makefile
export TAU_MAKEFILE=${TAU_ROOT}/${TAU_ARCH}/lib/Makefile.${TAU_CONFIG}
# Add TAU to the path
export PATH=${TAU_ROOT}/${TAU_ARCH}/bin:${PATH}
# Add SOS to the path
export PATH=${SOS_ROOT}/bin:${PATH}
# Add ADIOS to the path
export PATH=${ADIOS_DIR}/bin:${PATH}
