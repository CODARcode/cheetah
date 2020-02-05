[Main](../index)

Contents
--------
* TOC
{:toc}

Creating a Campaign Specification
---------------------------------
Cheetah provides a Python-based specification format to create a campaign of experiments to explore various aspects of online data analysis and reduction.
This section describes the specification format and the specification object model.

## Cheetah Object Model

![Cheetah Object Model](cheetah-model.jpg?raw=true "Cheetah Object Model")

The figure above describes Cheetah's object model.  
A campaign is a collection of **SweepGroup** objects which represent a batch job for the underlying system.  
Each SweepGroup consists of one or more **Sweep** objects which represent a collection of parameter values that must be explored.

## Specification Format
The snippet below shows the generic structure of a campaign spec file.
``` python
class GrayScott(Campaign):
    name = "gray_scott"
    
    # List applications that form the workflow
    codes = = [ {'app_handle', {exe=, adios_xml_file=, sleep_after=, runner_override=}, ]
    
    # Global campaign options
    run_post_process_script =
    scheduler_options =
    app_config_scripts =

    # Create a parameter sweep object
    sweep1_parameters = [ .. ]
    sweep1 = Sweep (sweep1_parameters)
    
    # Create the layout for the MPI ranks
    shared_virtual_node = SummitNode()
    my_layout = [shared_virtual_node]
    sweep1.node_layout = my_layout

    # Create a SweepGroup object (== job on the underlying system)
    sg1 = SweepGroup(sweep1, ...)

    # SweepGroups to be activated in the campaign 
    sweeps=[sg1]
```

See the [examples](https://github.com/CODARcode/cheetah/tree/dev/examples) for real campaign spec files.

Different components of the spec file are explained below.

## Global Campaign Options
Here we define the global options .. 

** **Pro Tip** ** : Use the `run_post_process_script` experiment option in the specification file to cleanup large files after an experiment completes.
Cheetah automatically captures the sizes of all output ADIOS files when the experiment completes.

## Creating a SweepGroup
SweepGroup:
A SweepGroup is a collection of Sweeps that inherit some common launch characteristics as described below.
Every SweepGroup is launched as a batch job.
Users can add multiple Sweeps to a SweepGroup.

Using the constructor, create a SweepGroup as follows:

``` python
class SweepGroup(name, walltime, per_run_timeout, parameter_groups,  
                 (optional) launch_mode, (optional) nodes,  
                 (optional) component_subdirs, (optional) component_inputs) )
```

    `name` - Choose a name for the SweepGroup  

    `walltime` - The total walltime to run the SweepGroup, in minutes  

    `per_run_timeout` - Timeout for each experiment in the SweepGroup, in minutes

    `parameter_groups` - A list of Sweep objects for this SweepGroup.

    `launch_mode` - (optional) 'Default' (default) or 'MPMD'. This represents how the applications in an experiment are launched. In default mode, all applications are run concurrently (expect dependencies) as separate MPI\_COMM\_WORLD. In MPMD mode, all applications are launched in MPMD mode if it is supported on the underlying system. Dependencies between applications are not supported if `launch_mode` is set to 'MPMD'.

    `nodes` - (optional) The number of nodes to be assigned to the SweepGroup. Increasing the number of nodes can increase the number of concurrently running experiments. By default, Cheetah sets this to the minimum number of nodes required to run an experiment in the SweepGroup. *Pro tip*: Cheetah traverses the experiment manifest linearly, launching experiments if adequate nodes are available. So .. 

    `component_subdirs` - (optional). Default - False. Set it to True if individual applications in the experiment must run in their own working directory.

    `component_inputs` - (optional). Specify if component applications in an experiment need input data that must be copied to the working directory when the campaign is created. Mark it as a Symlink to avoid copying large files in every experiment working directory.

    `run_repetitions` - (optional) The number of times every experiment in the SweepGroup must be repeated. Default: 0 (run once, no repititions). Savanna runs experiments so that all experiments are run first before running them again. Every repetition is created as a separate experiment with its own, independent workspace by Cheetah.



## Creating a Sweep

``` python
class Sweep(parameters, node_layout, rc_dependency)
```

    `parameters`: A list of parameters that describe 1) how to run all applications in the workflow, 2) how to sweep over parameters values. Parameters are described in the section on Parameter Types.

    `node_layout`: It describes the distribution of MPI ranks on to compute resources. In simple cases, it denotes the number of MPI ranks per node. For more complex cases such as the Summit supercomputer, it denotes how to pin ranks to cores/gpus on a compute node. See section on [Node Layout](node-layout).

    `rc_dependency`: A dictionary that describes the dependency between run components (rc). For example, if an analysis application in the workflow depends on the simulation to complete, this is where it should be marked. Format: `{'analysis_app':'main_simulation'}`

    Cheetah serializes a Sweep consisting of multiple Parameter types such that the number of experiments created is a cross product of the parameter values in the sweep.




## Parameter Types
Parameter types represent different types of parameters that can be setup to run experiments. These include command line arguments, environment variables, configuration files, key-value parameter files, ADIOS XML files, and scheduler arguments.

### ParamRunner

``` python
class ParamRunner(app_handle, 'nprocs', [values])
```
> E.g. _ParamRunner ('simulation', 'nprocs', [512, 1024, 2048])_

The ParamRunner parameter type is used to run an application. For now, we support `'nprocs'` as a runner parameter, which represents the number of MPI ranks that must be launched.
values is a list of integers to be tested. For examples, setting values to [4,8,16] would create 3 experiments for the 3 parameter values provided. On a workstation, this would be launched as `mpirun -np <nprocs> <app_handle> ...`.

### ParamCmdLineArg
``` python
ParamCmdLineArg(app_handle, name, position, [values])
```
> E.g. _ParamCmdLineArg ('simulation, 'input file name', 1, ['settings.json'])_

    ParamCmdLineArg represent command line arguments provided to the application when it is launched.

    `app_handle`: An application id or handle as specified in the 'codes' property of the campaign.

    `name`: A user-defined name to describe the command line argument

    `position`: The position of the argument during the application's launch (starting from 1).

    `[values]`: A list of values to be tested.

### ParamCmdLineOption
``` python
ParamCmdLineOption(app_handle, name, option, [values]) 
```
> E.g. _ParamCmdLineOption ('pdf\_calc', 'input file', '-i', ['brus.bp'])_

    ParamCmdLineOption represents labelled command line options of the format `--par val`.

    `app_handle`: An application id or handle as specified in the 'codes' property of the campaign.

    `name`: A user-defined name to describe the parameter

    `option`: The name of the command line option (e.g. `--output_file`)

    `[values]`: A list of values to be tested.

### ParamADIOS2XML
``` python
ParamADIOS2XML(app_handle, name, adios_object, operation_type, [values])
```
> E.g. _ParamADIOS2XML ('simulation', 'sim output', 'engine', values=  
                        [ {"BPFile": {'Threads':1}}, {"BPFile": {"ProfileUnits": "Microseconds"}} ]_  
> E.g. _ParamADIOS2XML ('simulation', 'sim output', 'var_operation', values=  
                        [ { “T”: { “zfp”: {“rate”:18, “accuracy”: 0.001} } }]_

    ParamADIOS2XML allow setting parameters in the application's ADIOS XML file.

    `app_handle`: An application id or handle as specified in the 'codes' property of the campaign.

    `name`: A user-defined name to describe the parameter

    `adios_object`: The type of the ADIOS object in the XML file. One of: engine, transport, var_operation.

    `operation_type`: The type of ADIOS operation to be set. One of engine/transport/var_operation.

    `[values]`: A list of values to be tested. Here, every list element must be a dictionary to allow setting options for the parameter value, in the following format:  
    _{ adios object_name: {parameter values} }_


### ParamEnvVar
``` python
ParamEnvVar(app_handle, name, option, values)
```
> E.g. _ParamEnvVar('simulation', 'openmp num threads', 'OMP\_NUM\_THREADS', [4])_

    Set a environment variable. To set multiple environment variables, create multiple ParamEnvVar objects.

    `app_handle`: An application id or handle as specified in the 'codes' property of the campaign.

    `name`: A user-defined name to describe the parameter

    `option`: The environment variable to be set

    `values`: A list of values to be tested.

### ParamConfig
``` python
ParamConfig(app_handle, name, config_file, key, value)
```
> E.g. _ParamConfig ("simulation", "num timesteps", "settings.json", "timesteps", [50, 100] )_

    Set the value for a key in a configuration file, such as a json file (supports single level of nesting).

    `app_handle`: An application id or handle as specified in the 'codes' property of the campaign.

    `name`: A user-defined name to describe the parameter

    `config_file`: Name of a configuration file.

    `key`: Name of the key in the configuration file.

    `values`: A list of values to be tested.

### ParamKeyValue
``` python
ParamKeyValue(app_handle, name, config_file, key, value)
```
> E.g. _ParamKeyValue ("simulation", "num timesteps", "config.txt", 'psi', [0.2, 0.3] )_

    A special case of a ParamConfig file that allows setting a key in a generic key-value config file where lines are in the format _key=value_.

    `app_handle`: An application id or handle as specified in the 'codes' property of the campaign.

    `name`: A user-defined name to describe the parameter

    `config_file`: Name of a configuration file.

    `key`: Name of the key in the configuration file.

    `values`: A list of values to be tested.


[Main](../index)

