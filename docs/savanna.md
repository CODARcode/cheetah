
[Main](../index)

## Directory structure of the campaign

Cheetah allows multiple users to run under the same campaign. Thus, when a campaign is created, Cheetah generates a user directory at the top-level by default.
```bash
<campaign dir>/<username>
```

Every SweepGroup in the specification file is generated as a sub-directory in the campaign with a submit script for launching the group.



All Sweeps in a SweepGroups are serialized into experiments with a unique name of the format `run-<x>.iteration-<y>`, where `x` represents the run id in increasing order starting from 0, and
  `y` represents its repetition index.  
All experiments have their own directory and can be run concurrently and independently of each other if there are sufficient compute resources available for Savanna to launch them.

Each group contains `fobs.json`, which is a group-level metadata file describing all experiments and global options of the group. Other files such as `campaign-env.sh` and `group-env.sh` contain additional Cheetah metadata.
`codar.FOBrun.log` is a log file maintained by Savanna to log runtime execution of experiments.  
The stdout and stderr of each application in an experiment is redirected to `codar.workflow.stdout.<app-name>` and `codar.workflow.stderr.<app-name>` respectively.  
Similarly, Savanna creates files to store the runtime of each workflow component and its return code.

** **Pro Tip** ** : Use the `run_post_process_script` experiment option in the specification file to cleanup large files after an experiment completes.
Cheetah automatically captures the sizes of all output ADIOS files when the experiment completes.
    
[Main](../index)

