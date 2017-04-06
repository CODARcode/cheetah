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

### Fusion Application

Run XGC fusion simulation on Titan and Cori, with no data reduction, and with
SZ. Compare the following performance characteristics:

- run time - total, per node
- output file sizes - total, per node
- ADIOS I/O logging flags

With instrumentation of application (XGC) and/or ADIOS:

- data reduction bytes in/bytes out
- time in data reduction and inflation routines
- high water mark memory usage

Accuracy evaluation (future)

- Computer difference between floating point output with no compression vs
  with SZ.

Data is of two types - a mesh with custom geometry (very irregular), and
particle information. Both are five dimensional (3 spacial and 2 velocity).

### CANDLE Application

Run machine learning / genetic algorithm simulation on Beagle with parameter
sweep, and produce HTML report with results of different parameters. Capture
the following for each set of parameters:

- run time - total, per node

The parameter sweep is implemented via a swift script, either calling the
main function with different args via an embedded Python interpreter, or via
a main shell script wrapping a call a custom python interpreter.

Future work:

- add some way of evaluating solution quality, other than just wall time

## Parameter Passing Conventions

Cheetah needs to support different ways of passing parameters to applications.
It could do this by having a rich spec language for defining the exact needed
passing mechanism, or by having a simple spec language and requiring wrapper
scripts to hide the more exotic methods, or some hybrid of the two.

### Command Line

- short options vs long options
- for long options, can be '-' prefixed or '--' prefixed
- options with no arg, optional arg, or required arg
- options that can occur multiple times to form a list
- positional arguments

A possible strategy would be to assume that the app adheres to some standard,
i.e. it does not mix '-' type and '--' type long options. At the app level in
the spec file, the type of passing conventions used would be set. Then in the
parameter group section that specifies the values to sweep over, the args are
specified by name without any prefix, and Cheetah adds the appropriate values.
It could go as far as specifying detailed spec of all app params that are
useful for Cheetah, with a useful long name, and the rest of the spec uses
those friendly names. Example:

```
parameter-groups:
  app:
    parameters:
      particles:
        mechanism: command-line-long-double-dash
        type: int
        name: particles
      method:
        mechanism: command-line-positional
        type: enum
      iterations:
        mechanism: command-line-short
        type: int
        name: i
```
for command structure `app --particles=10 -i 20 atan`

Another strategy would be to make parameter specification very literal in the
parameter group section of the spec, but have to deal with escaping or quoting
the dashes in YAML, since '- ' is used to introduce a list. Some sort of
namespacing is still needed to distinguish app params vs aprun params vs
qsub or slurm params. Example:
```
parameter-groups:
  - "app:--particles": [50, 500, 5000000]
    "app:-b": ["opt1", "opt2"]
    "app:1:": ["firstpositionalval1", "firstpositionval2"]
```

### Config File

All of these could probably be handled by requiring a template, but any special
chars of the template language (e.g. to introduce a variable to replace) that
appear in the file naturally would need to be escaped. Example:

```
parameter-groups:
  - "app:config:app.ini.template:api.ini:particles": [50, 500, 50000]
```
Need a way to specify that this param is set in a config file, what template
to use, and what to call the output files (in case there are many substitutions
in same output file), the name of the variable to substitute, and the values.

Could have special support for common formats: e.g. xpath/jpath for setting
values in XML or JSON, some way of specifying how to update an INI, etc
