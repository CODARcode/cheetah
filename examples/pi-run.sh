#!/bin/bash

# Runner for GMP version of pi test app that computes digits of pi
# See https://github.com/CODARcode/Example-pi

OPTS=$(getopt -o o::t::m::p:: -l output-directory:,precision:,iterations:,method: -- "$@")
if [ $? != 0 ]; then echo "Failed parsing options." >&1 ; fi
eval set -- "$OPTS"

while true; do
    case "$1" in
    -o | --output-directory)
        OUTPUT_DIRECTORY="$2"
        shift 2
        ;;
    -t | --iterations)
        ITERATIONS="$2"
        shift 2
        ;;
    -p | --precision-bits)
        PRECISION="$2"
        shift 2
        ;;
    -m | --method)
        METHOD="$2"
        shift 2
        ;;
    --)
        shift
        break
        ;;
    *)
        echo "Error: unknown option '$1'"
        exit 1
    esac
done

mkdir -p "$OUTPUT_DIRECTORY"

# NOTE: Cheetah must generate an appropriate qsub pbs or slurm sbatch
# that does a cd to the executable directory before running this. Some
# apps might require running with a different working directory, so we
# may have to support other modes.
./pi-gmp $METHOD $PRECISION $ITERATIONS > "$OUTPUT_DIRECTORY"/pi_digits.txt
