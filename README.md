# CODAR Cheetah - The CODAR Experiment Harness

## Overview

The CODAR Experiment Harness is designed to run Exascale science applications
using different parameters and components to determine the best combination
for deployment on different supercomputers.

To use Cheetah, the user first writes a "campaign" specification file.
Cheetah takes this specification, and generates a set of swift and bash
scripts to execute the application many times with each of the parameter sets,
and organize the results of each run in separate subdirectories. Once
generated, the `run-all.sh` script in the output directory can be used
to run the campaign.

## Requirements

Cheetah v0.1 requires a modern Linux install with Python 3.4 or greater
and CODAR Savanna v0.5. See the
[savanna documentation](https://github.com/CODARcode/savanna)
for installation instructions.

## Tutorial for Running Heat Transfer example with Cheetah

1. Install Savanna and build the Heat Transfer example (see savanna
   instructions). This tutorial will assume spack was used for the
   installation, and uses bash for environment setup examples.

2. Download the Cheetah v0.1 release from github and unpack the release
   [tarball](https://github.com/CODARcode/cheetah/archive/v0.1.tar.gz).

3. Set up environment for cheetah (this can be added to your ~/.bashrc
   file for convenience, after spack environment is loaded):

```
source <(spack module loads --dependencies adios)
spack load stc turbine mpix-launch-swift
export CODAR_MPIX_LAUNCH=$(spack find -p mpix-launch-swift | grep mpix-launch | awk '{ print $2 }')
```

4. Make a directory for storing campaigns, for example:

```
mkdir -p ~/codar/campaigns
```

5. Generate a campaign from the example, which will run Heat\_Transfer
   with stage\_write three times, once with no compression, once with
   zfp, and once with sz:

```
cd /path/to/cheetah
./cheetah.py -e examples/heat_transfer_small.py \
 -a /path/to/Example-Heat_Transfer \
 -m local -o ~/codar/campaigns/heat
```

6. Run the campaign:

```
cd ~/codar/campaigns/heat
./run-all.sh
```

For results, see `group-001/run-00*`. To debug failures, look at
`group-001/codar.cheetah.submit-output.txt` first, then at the stdout
and stderr files in each of the run directories.

## Campaign Specification

The campaign is specified as a python class that extends
`codar.cheetah.Campaign`. To define your own campaign, it is recommended to
start with the
[heat transfer example campaign](examples/heat_transfer_small.py).

Note that this is an early release and the campaign definition is not
stable yet. Here is a quick overview of the current structure and
supported parameter types:

- name - a descriptive name for the campaign
- codes - dictionary of different codes that make up the application,
  where keys are logical names and values are paths to the executable
  relative to the application root directory. Many simple applications will
  have only one code.
- supported\_machines - list of machines that the campaign is designed
  to run on. Currently only 'local' and 'titan' are supported.
- inputs - list of files relative to the application root directory to
  copy to the working directory for each application run. If the file is
  an adios config file, ParamAdiosXML can be used to modify it's
  contents as part of the parameter sweep.
- project - for running on titan, set the project allocation to use.
  Ignored when using local machine.
- queue - for running on titan, set the PBS queue to use.
- sweeps - list of SweepGroup objects, defining instances of the
  application to run and what parameters to use.
- SweepGroup - each sweep group specifies the number of nodes (ignored
  for local runs), and a set of parameter groups. This represents a
  single submission to the scheduler, and each sweep group will be in a
  different subdirectory of the output directory.
- Sweep - a sweep is a specification of all the parameters that must be
  passed to each code in the application, together with metadata like
  the number of MPI processes to use for each code, and lists of all
  values that the parameters should take on for this part of the
  campaign. Within the sweep, a cross product of all the values will be
  taken to generate all the instances to run. For simple campaigns that
  need to do a full cross product of parameter values, only one
  SweepGroup containing one Sweep is needed.
- ParamX - all parameter types have at least three elements:
  - target - which code the parameter is for. The value must be one of
    the keys in the codes dictionary.
  - name - logical name for the parameter. This is used as a key in the JSON
    file that is generated to describe the parameter values used for a
    run in the output directory. For each target, there can be only one
    parameter with a given name.
  - values - the list of values the parameter should take on for the
    sweep
  Different parameter types will have other parameters as well.
- ParamRunner - currently used only for the special 'nprocs' parameter
  to specify how many processes to use for each code.
- ParamCmdLineArg - positional arguments to pass to the code executable.
  The third argument is the position, starting from 1. All positions
  from 1 to the max must be included.
- ParamCmdLineOption - the third argument is the full option name,
  including any dashes, e.g. '--iterations' or '-iterations' depending
  on the convention used by the code. Note that this is distinct from
  the name, but a good choice for name is the option with the dashes
  removed.
