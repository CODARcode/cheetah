
[Main](../index)

Campaign Directory Structure
============================

Cheetah allows multiple users to run under the same campaign. Thus, when a campaign is created, Cheetah generates a user directory at the top-level by default.
```bash
<campaign dir>/<username>
```


Every SweepGroup in the specification file is generated as a sub-directory in the campaign with a submit script for launching the group.

All Sweeps in a SweepGroups are serialized into experiments with a unique name of the format `run-<x>.iteration-<y>`, where `x` represents the run id in increasing order starting from 0, and
  `y` represents its repetition index.  
All experiments have their own directory and can be run concurrently and independently of each other if there are sufficient compute resources available for Savanna to launch them.

Each group contains `fobs.json`, which is a group-level metadata file describing all experiments and global options of the group. Other files such as `campaign-env.sh` and `group-env.sh` contain additional Cheetah metadata.

An example of an campaign directory is shown below.
``` bash
|____user1/
| |____campaign-env.sh
| |____params.json
| |____sweepgroup1/
| | |____group-env.sh
| | |____fobs.json
| | |____run-0.iteration-0/
| | | |____codar.cheetah.fob.json
| | | |____codar.cheetah.run-params.json
| | | |____codar.cheetah.run-params.txt
| | | |____codar.cheetah.tau-a
| | | |____tau.conf
| | | |____codar.cheetah.tau-b
| | |____run-group.lsf
| | |____submit.sh
| | |____cancel.sh
| |____sg-1
| |____run-all.sh
```


[Main](../index)

