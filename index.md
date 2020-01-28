Cheetah
=======

Cheetah is an experiment harness designed to explore online analysis and reduction of scientific data. Built around the ADIOS ecosystem, it provides a Python-based specification to create a multi-user campaign that can be run to explore the impact of various parameters on an composite application workflow.
Users can setup experiments to explore various compression algoriths, and perform reduction synchronously, asynchronously, on-node, and off-node.

Using Python, users can create an abstract campaign specification that is transparent of low-level details such as the scheduler used on the underlying system.
Cheetah generates a campaign end-point on the target machine using the specification provided by the user. The campaign endpoint consists of an independent workspace for each experiment, and scripts to launch batch jobs to run the experiments. The runtime framework for orchestrating application workflow is termed **_Savanna_**.

Once a campaign is started, Cheetah can be used to query the status of running experiments. Finally, Cheetah can be used to generate a report for a completed campaign.


### The four steps of campaign management
There are 4 steps to conducting a parametric study using Cheetah.
1. Create a Python-based abstract campaign specification
2. Use Cheetah to generate a campaign endpoint on the target system
3. Run the campaign
4. Generate a performance report for a completed campaign

1. Campaign Specification
-------------------------

#### Global Campaign Options
Here we define the global options .. 


#### Creating a SweepGroup
SweepGroup:
A SweepGroup is a collection of Sweeps that inherit some common launch characteristics as described below.
Every SweepGroup is launched as a batch job.
Users can add multiple Sweeps to a SweepGroup.

Using the constructor, create a SweepGroup as follows:

```Python
class SweepGroup(name, walltime, per_run_timeout, parameter_groups,  
              (optional) launch_mode, (optional) nodes,  
              (optional) component_subdirs, (optional) component_inputs) )
```

    name - Choose a name for the SweepGroup  

walltime - The total walltime to run the SweepGroup, in minutes
per_run_timeout - Timeout for each experiment in the SweepGroup, in minutes
parameter_groups - A list of Sweep objects for this SweepGroup.
launch_mode - (optional) 'Default' (default) or 'MPMD'. This represents how the applications in an experiment are launched. In default mode, all applications are run concurrently (expect dependencies) as separate MPI_COMM_WORLD. In MPMD mode, all applications are launched in MPMD mode if it is supported on the underlying system. Dependencies between applications are not supported if launch_mode is set to 'MPMD'.
nodes - (optional) The number of nodes to be assigned to the SweepGroup. Increasing the number of nodes can increase the number of concurrently running experiments. By default, Cheetah sets this to the minimum number of nodes required to run an experiment in the SweepGroup. *Pro tip*: Cheetah traverses the experiment manifest linearly, launching experiments if adequate nodes are available. So .. 
component_subdirs - (optional). Default - False. Set it to True if individual applications in the experiment must run in their own working directory.
component_inputs - (optional). Specify if component applications in an experiment need input data that must be copied to the working directory when the campaign is created. Mark it as a Symlink to avoid copying large files in every experiment working directory.
run_repetitions - (optional) The number of times every experiment in the SweepGroup must be repeated. Default: 0 (run once, no repititions). Savanna runs experiments so that all experiments are run first before running them again.






