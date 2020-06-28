Cheetah - An Experiment Harness and Campaign Management System
==============================================================

Overview
--------

Cheetah is an experiment harness for running codesign experiments to study the effects of online data analysis at the exascale. It provides a way to run large campaigns of experiments to understand the advantages and tradeoffs of different compression and reduction algorithms run using different orchestration mechanisms. Experiments can be run to analyze data offline, in situ (via a function that is part of the application), or online (in a separate, stand-alone application). The workflow may be composed so that different executables reside on separate nodes, or share compute nodes, in addition to fine-tuning the number of processes per node.

Users create a campaign specification file in Python that describes the applications that form the workflow, and the parameters that they are interested in exploring. Cheetah creates the campaign endpoint on the target machine, and users can then launch experiments using the generated submission script.

Cheetah's runtime framework, **Savanna**, translates experiment metadata into scheduler calls for the underlying system and manages the allocated resources for running experiments. Savanna contains *definitions* for different supercomputers; based upon this information about the target machine, Savanna uses the appropriate scheduler interface (*aprun*, *jsrun*, *slurm*) and the corresponding scheduler options to launch experiments.

Cheetah is centered around [ADIOS](https://adios2.readthedocs.io/en/latest/index.html), a middleware library that provides an I/O framework along with a publish-subscribe API for exchanging data in memory. Typically, all ADIOS-specific settings are set in an XML file that is read by the application. Cheetah provides an interface to edit ADIOS XML files to tune I/O options.


Installation
------------
* Dependency: Linux, Python 3.5+
* On supercomputers it should be installed at a location accessible from the parallel file system
* Cheetah can be installed via the Spack package manager as `spack install codar-cheetah@develop`.
* Users can also download Cheetah and set the PATH:

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

Documentation
-------------
The recommended start is to go through the [Cheetah Tutorial](https://github.com/CODARcode/cheetah/blob/dev/docs/Tutorials/Cheetah-Tutorial-ECP-AM-2020.pptx) under docs/Tutorials.    
The Cheetah documentation can be found at [https://codarcode.github.io/cheetah](https://codarcode.github.io/cheetah/index).

Releases
--------
The current release is [1.1.0](https://github.com/CODARcode/cheetah/releases/tag/v1.1.0).

### Supported Systems
System Name | Cheetah Support | System supports Node-Sharing | Cheetah Node-Sharing Support 
:-----------| :---------------| :----------------------------| :---------------------------
Local Linux machines | :white_check_mark: | N/A | N/A
Summit | :white_check_mark: | :white_check_mark: | :white_check_mark:
Rhea| :white_check_mark: | In progress | In progress
Titan | :white_check_mark: | :x: | N/A
Theta | :white_check_mark: | :x: | N/A
Cori | :white_check_mark: | :white_check_mark: | In progress

Authors
-------
The primary authors of Cheetah are Bryce Allen (University of Chicago) and Kshitij Mehta (ORNL).
All contributors are listed [here](https://github.com/CODARcode/cheetah/graphs/contributors).

Citing Cheetah
--------------
To refer to Cheetah in a publication, please cite the following paper:
* K. Mehta et al., "A Codesign Framework for Online Data Analysis and Reduction," 2019 IEEE/ACM Workflows in Support of Large-Scale Science (WORKS), Denver, CO, USA, 2019, pp. 11-20.  
doi: 10.1109/WORKS49585.2019.00007  
URL: http://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=8943548&isnumber=8943488

Examples
--------
For more examples of using Cheetah, see the examples directory.

  - [Calculating Euler's number](https://github.com/CODARcode/cheetah/tree/master/examples/01-eulers_number)
  - [Using Cheetah to run coupled applications](https://github.com/CODARcode/cheetah/tree/master/examples/02-coupling)
  - [Brusselator](https://github.com/CODARcode/cheetah/tree/master/examples/03-brusselator)
  - [The Gray-Scott Reaction-Diffusion Benchmark](https://github.com/CODARcode/cheetah/tree/master/examples/04-gray-scott)
  - [Gray-Scott with compression, Z-Checker and FTK](https://github.com/CODARcode/cheetah/tree/master/examples/05-gray-scott-compression)

Contributing
------------
Cheetah is open source and we invite the community to collaborate. Create a pull-request to add your changes to the `dev` branch.

Reporting Bugs
--------------
Please open an issue on the [github issues](https://github.com/CODARcode/cheetah/issues) page to report a bug.

License
-------

