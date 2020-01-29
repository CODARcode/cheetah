
[Main](../index)

Running a Campaign
==================

Once a campaign endpoint has been created, the `run-all.sh` script can be used to launch the full campaign. Each sub-directory with the user's space is a SweepGroup which represents a _job_ on the underlying system. The `run-all.sh` launches all SweepGroups individually.

Alternatively, users may launch a specific SweepGroup by executing the `submit.sh` script in the SweepGroup directory.

Every SweepGroup contains a `fobs.json` file, which is a manifest of all the experiments in that group.

Experiments are labelled `run-x.iteration-y`, where iteration-y represents the repetitions of the same experiment.

When a campaign starts running, Savanna reads the fobs.json file and starts running experiments dpeneding on the node availability. Savanna traverses the manifest in a linear fashion and launches an experiment as resources become available.
For example, if there are 10 experiments that require 16 nodes each and 64 nodes have been allocated to the SweepGroup, Savanna runs 4 experiments concurrently.


Re-submitting a SweepGroup
--------------------------
A SweepGroup (batch job) may finish running when all experiments in the group complete, or if the SweepGroup runs out of its allocated time. If a SweepGroup finishes due to time limitations without running all experiments, users may re-submit the SweepGroup. Upon doing so, Cheetah runs only those experiments that could not be launched during the previous execution. 
At runtime, Savanna maintains the status of all experiments in `codar.workflow.status.json`. Upon re-submitting a SweepGroup, experiments marked `not_started` are launched.
Note that re-submitting a SweepGroup does _not_ re-run experiments that were launched previously, irrespective of their return status (success/failure).

Monitoring a running campaign
--------------------------

The status of a running campaign can be queried using 
`cheetah status /path/to/campaign`. See cheetah help for a list of options to `cheetah status`.


[Savanna](savanna) explains the campaign directory structure and how experiments in a SweepGroup are run using Savanna, the runtime engine used by Cheetah.

[Main](../index)

