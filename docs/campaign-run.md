Running a Campaign
==================

Once a campaign endpoint has been created, the `run-all.sh` script can be used to launch the full campaign. Or, SweepGroups can be launched individually. Each sub-directory with the user's space is a SweepGroup which can be launched as a separate job. The `submit.sh` script can be used to launch a SweepGroup. Care must be taken to ensure a SweepGroup is not executed multiple times concurrently.
Every SweepGroup contains a `fobs.json` file, which is a manifest of all the experiments in that group.
Experiments are labelled run-x.iteration-y, where iteration-y represents the repetitions of the same experiment.
When is campaign starts running, Savanna reads the fobs.json file and starts running experiments dpeneding on the node availability. Savanna maintains a linear list of the experiments and starts running the next experiment only when some experiments complete and nodes become available.
For example, if there are 10 experiments that require 16 nodes each and 64 nodes have been allocated to the SweepGroup, Savanna runs 4 experiments concurrently.


Monitor a running campaign
--------------------------

The status of a running campaign can be queried using 
`cheetah status path-to-campaign`. See cheetah help for a list of options to `cheetah status`.

A campaign can be resubmitted so that experiments which could not be started on the previous run due to insufficient allocation time can be run. Re-submitting a campaign or specific SweepGroups allocates a new set of nodes to run experiments that could not be run previously.

At runtime, Savanna creates the following files:
`codar.FOBrun.log` - A log written by Savanna that shows various actions taken by Savanna such as starting an experiment, experiment completion, 

