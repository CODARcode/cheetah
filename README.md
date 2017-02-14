# CODAR Cheetah - The CODAR Experiment Harness

## Overview

The CODAR Experiment Harness is designed to run Exascale science applications
using different parameters and components to determine the best combination
for deployment on different super computers.

## Design (WIP)

There are several components to the experiment harness:

- Experiment configuration, a directory containing
  - a master YAML config file (custom schema defined for cheetah)
    - define templates to use and a range of values to pass,
      e.g. command line args
  - scheduler (SLURM, PBS) and swift templates
  - application config file templates
- Standard for output directory
  - Includes copy of master experiment YAML config file 
  - Contains performance logs, in structured text and/or easily parsible log
    files
  - Can optionally include application output files, subject to YAML config
    (may be very large and not needed for some experiments)
- Accuracy measurement
  - Compare no compression application output with reduced output, calculate
    L(x)s norm, other stats
- Build configuration (future)
  - Script building application with different options, when needed for the
    experiment.
  - Initially just use a set of bash scripts
- Report generation (future)
  - Graphs of performance data

## Initial Examples

Run XGC fusion simulation on Titan and Cori, with no data reduction, and with
SZ. Compare the following performance characteristics:

- run time - total, per node
- output file sizes - total, per node
- ADIOS I/O logging flags

With instrumentation of application (XGC) and/or ADIOS:

- data reduction bytes in/bytes out
- time in data reduction and inflation routines
- high water mark memory usage

TODO: add cancer machine learning app example
