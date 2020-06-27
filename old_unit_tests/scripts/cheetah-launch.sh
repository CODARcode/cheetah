#!/bin/bash

##
# Wrapper script for use with swift launch_multi. Arguments:
#  1: the working directory to use for the command
#  2: logical name of program from cheetah campaign definition
#  3: program executable
# The remaining argument are passed to the program. Does a cd to
# the working dir and saves stderr and stdout to files in the working
# dir containing the logical program name.
##

function error_exit
{
	echo "$1" 1>&2
	exit 1
}

WORK_DIR=$1
PROG_NAME=$2
PROG=$3
shift 3

cd "$WORK_DIR" || error_exit "Cannot change to work dir, aborting!"

export PROFILEDIR="tau-profile-$PROG_NAME"
export TRACEDIR="tau-trace-$PROG_NAME"
export TAU_PROFILE=1
export TAU_TRACE=1

echo "Cheetah: launching $PROG_NAME at $WORK_DIR"

# NOTE: low relolution, but alternatives have inconsistent platform
# support
start_time=$(date +%s)
$PROG "$@" >codar.cheetah.$PROG_NAME.stdout 2>codar.cheetah.$PROG_NAME.stderr
end_time=$(date +%s)
echo $(($end_time - $start_time)) > codar.cheetah.$PROG_NAME.walltime.txt
