# Cheetah - the CODAR Experiment Harness

## Overview
Cheetah is an experiment harness for running codesign experiments to study the effects of online data analysis at the exascale. It provides a way to run large campaigns of experiments to understand the advantages and tradeoffs of different compression and reduction algorithms run using different orchestration mechanisms. Experiments can be run to analyze data offline, in situ (via a function that is part of the application), or online (in a separate, stand-alone application). The workflow may be composed so that different executables reside on separate nodes, or share compute nodes, in addition to fine-tuning the number of processes per node.

Users create a campaign specification file in Python that describes the applications that form the workflow, and the parameters that they are interested in exploring. Cheetah creates the campaign endpoint on the target machine, and users can then launch experiments using the generated submission script.

Cheetah's runtime framework, **Savanna**, translates experiment metadata into scheduler calls for the underlying system and manages the allocated resources for running experiments. Savanna contains *definitions* for different supercomputers; based upon this information about the target machine, Savanna uses the appropriate scheduler interface (*aprun*, *jsrun*, *slurm*) and the corresponding scheduler options to launch experiments.

Cheetah is centered around [ADIOS](https://adios2.readthedocs.io/en/latest/index.html), a middleware library that provides an I/O framework along with a publish-subscribe API for exchanging data in memory. Typically, all ADIOS-specific settings are set in an XML file that is read by the application. Cheetah provides an interface to edit ADIOS XML files to tune I/O options.

![Cheetah Architecture](docs/cheetah-arch.jpg?raw=true "Architecture of Cheetah")

To use Cheetah, users must first write a **campaign specification file** in Python. This file contains:

* which MPI programs to launch in parallel
* what computing resources to give to those programs
* which configuration files to copy to each experiment's directory
* the ability to *sweep* over different parameters of interest
    * lists of possible values for parameters (including computing resources); the cartesian product of those parameter spaces defines the number of experiments in the campaign  
* how many times to repeat each experiment to collect enough statistics to estimate the variability of the results.
* Setting the coupling mechanism in ADIOS (SST, BPFile, SST RDMA, SSC, InsituMPI)  

## Installation
* Dependency: Linux, Python 3.5+
* On supercomputers it should be installed at a location accessible from the parallel file system
* To install Cheetah, do:
  ```bash
  git clone git@github.com:CODARcode/cheetah.git
  cd cheetah          
  python3 -m venv venv-cheetah
  source venv-cheetah/bin/activate
  pip install --editable .
  ```
* Cheetah has been tested so far on Summit, Theta, Cori, and standalone Linux computers

##### Setting up a Cheetah environment
   ```bash
   source <cheetah dir>/venv-cheetah/bin/activate
   ```

## Campaign specification file

![Cheetah Object Model](docs/cheetah-model.jpg?raw=true "Cheetah Object Model")

The campaign specification file allows various options to setup and execute the workflow.
A campaign is a collection of **SweepGroup** objects which represent a batch job for the underlying system.
Each SweepGroup consists of one or more **Sweep** objects which represent a collection of parameter values that must be explored.

[examples/03-brusselator/cheetah-campaign.py](examples/03-brusselator/cheetah-campaign.py) explains the format of the specification file in detail. 

#### Node Sharing
A workflow may be composed so that multiple applications share a compute node if the underlying system permits it. Of the supercomputers currently supported by Cheetah, Summit and Cori allow node sharing, whereas Titan and Theta do not. As of now, Cheetah supports node sharing on Summit, whereas node sharing for Cori is currently under development. Additionally, users may want to set the number of processes spawned per node, as all cores of a node are used to spawn MPI processes by default.

To do so, users must utilize the `node-layout` property of a Sweep that sets up the orchestration mechanism for all experiments in the Sweep.  
[examples/03-brusselator/cheetah-campaign.py](examples/03-brusselator/cheetah-campaign.py) shows how to use `node-layout` to set the number of MPI processes per node.


#### Supported Systems
System Name | Cheetah Support | System supports Node-Sharing | Cheetah Node-Sharing Support 
:-----------| :---------------| :----------------------------| :---------------------------
Local Linux machines | :white_check_mark: | N/A | N/A
Summit | :white_check_mark: | :white_check_mark: | :white_check_mark:
Titan | :white_check_mark: | :x: | N/A
Theta | :white_check_mark: | :x: | N/A
Cori | :white_check_mark: | :white_check_mark: | In progress


### Running on Summit
Due to the highly heterogeneous architecture of Summit and the associated `jsrun` utility to run jobs, running Cheetah on Summit mandates using the `node-layout` property of a Sweep where users have to map processes to resources on a node. See [examples/04-gray-scott/cheetah-summit.py](examples/04-gray-scott/cheetah-summit.py) to see an example.


## Usage
* **Creating a Campaign**:  
  To generate a campaign, run
  ```bash
  cheetah create-campaign -a <dir with configs & binaries> \
  	     -o <campaign-dir> -e <specification>.py -m <supercomputer>
  ```  

  This creates a campaign directory specified as *campaign-dir*.
  The experiments are organized into separate subdirectories that contain
  all the necessary executables and configuration files to run each experiment separately if necessary.
  Each such directory would also contain its own log files so that one can later examine what went
  wrong with a particular experiment.

* **Launching the Campaign**  
  The top level directory of the campaign contains <b>run-all.sh</b> file that one can use to launch
  the whole set of experiments on the allocated resources.

    ```bash
    cd <campaign>/<username>  
    ./run-all.sh  
    ```
  
    Users may explicitly set the number of nodes in the specification file, or allow Cheetah to calculate the minimum number of nodes required to run a SweepGroup.

    All SweepGroups in the campaign can be launched using the `run-all.sh` script or a SweepGroup can be launched independently using its `submit.sh` launch script.  
    
    ** **Pro Tip** ** : If all experiments within a group do not complete in the allotted time, re-launching the group will only run the experiments that were not run.  

* **Campaign Monitoring**  
    As campaign runs, one can examine its progress with
    ```bash
    cheetah status <campaign dir> -n
    ```  

* **Generating a Performance Report**  
    When the campaign is done, a detailed performance report can be generated using 
    ```bash
    cheetah generate-report <campaign dir>
    ```  
    This creates a csv file with metadata and performance information for the entire campaign. 


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
    
## Examples
For more examples of using Cheetah, see the examples directory.

  - [Calculating Euler's number](https://github.com/CODARcode/cheetah/tree/master/examples/01-eulers_number)
  - [Using Cheetah to run coupled applications](https://github.com/CODARcode/cheetah/tree/master/examples/02-coupling)
  - [Brusselator](https://github.com/CODARcode/cheetah/tree/master/examples/03-brusselator)
  - [The Gray-Scott Reaction-Diffusion Benchmark](https://github.com/CODARcode/cheetah/tree/master/examples/04-gray-scott)
  - [Gray-Scott with compression, Z-Checker and FTK](https://github.com/CODARcode/cheetah/tree/master/examples/05-gray-scott-compression)

## API
<!-- * [Cheetah](https://codarcode.github.io/cheetah/cheetah/html/index.html) -->
<!-- * [Savanna](https://codarcode.github.io/cheetah/savanna/html/index.html) -->
[Cheetah/Savanna]( https://codarcode.github.io/cheetah/cheetah_savanna/html )
