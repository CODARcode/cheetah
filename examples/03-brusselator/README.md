# The Brusselator Reaction-Diffusion Benchmark

## Overview
The Brusselator benchmark code models a reaction-diffusion system. The code uses ADIOS to manage its data and online coupling with analyses applications. It can be found at the [adiosvm](https://github.com/pnorbert/adiosvm/tree/master/Tutorial/gray-scott) repository.

Various analysis applications are provided in the repository along with the main simulation.
In this example, we couple the simulation along with an analysis code that calculates the norm of the simulation data.
The coupling is done via the SST transport that comes bundles with ADIOS2.

`cheetah-campaign.py` shows an example campaign specification for the coupled codes.
We show how to setup the workflow and sweep over different parameters.

## Creating a campaign
To create a campaign endpoint from the specification, run the following command  
`cheetah.py create-campaign -a path-to-executables -e cheetah-campaign.py -m local -o ./campaign`.

This will create a campaign directory in the current directory.
To run the campaign,  
`cd ./campaign/[your_username] and run `run-all.sh`.

The status of the experiments can be queried as:  
`cheetah status <campaign-dir> -n`
