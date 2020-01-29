Cheetah
=======

* TOC
{:toc}


## Introduction
Cheetah is an experiment harness designed as part of the Exascale Computing Project (ECP)'s Co-design Center for Online Data Analysis and Reduction (CODAR) project. 

It allows conducting parametric studies to explore various aspect of online analysis and reduction of scientific data.
Built around the ADIOS ecosystem, it provides a **Python**-based specification to create a multi-user campaign that can be run to explore the impact of various parameters on an composite application workflow.

Users can setup experiments to explore various compression algoriths, and perform reduction synchronously, asynchronously, on-node, and off-node.

Users create an abstract campaign specification that is transparent of low-level details such as the scheduler used on the underlying system.
Cheetah provides an API to explore fine-grained mapping of MPI ranks to compute resources.
Cheetah generates a campaign end-point on the target machine using the specification provided by the user.
The campaign endpoint consists of an independent workspace for each experiment, and scripts to launch batch jobs to run the experiments.
The runtime framework, termed **_Savanna_**, translates the abstract specification into low-level details and orchestrates workflows for the underlying target system.

Once a campaign is started, Cheetah can be used to query the status of running experiments. Finally, Cheetah can be used to generate a report for a completed campaign.


## Campaign Management using Cheetah
There are 4 steps to conducting a parametric study using Cheetah.

1. ### [Create a Python-based abstract campaign specification](docs/campaign-spec)

    - #### The [Node Layout](docs/node-layout) Interface

2. ### [Generate a campaign endpoint on the target system](docs/campaign-create)
3. ### [Run the campaign using _Savanna_](docs/campaign-run)
4. ### [Generate a performance report for a completed campaign](docs/perf-report)

