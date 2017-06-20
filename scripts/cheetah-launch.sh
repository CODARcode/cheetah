#!/bin/bash

##
# Wrapper script for use with swift launch_multi. The first argument must be
# the working directory to use for the command, the next argument the program
# to run, and the remaining argument are passed to the program. Does a cd to
# the working dir and saves stderr and stdout to files in the working dir.
##

function error_exit
{
	echo "$1" 1>&2
	exit 1
}

WORK_DIR=$1
PROG=$2
shift 2

cd "$WORK_DIR" || error_exit "Cannot change to work dir, aborting!"

$PROG "$@" >codar.cheetah.stdout 2>codar.cheetah.stderr
