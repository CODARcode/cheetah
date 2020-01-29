Cheetah
=======

Cheetah is an experiment harness designed to explore online analysis and reduction of scientific data. Built around the ADIOS ecosystem, it provides a Python-based specification to create a multi-user campaign that can be run to explore the impact of various parameters on an composite application workflow.
Users can setup experiments to explore various compression algoriths, and perform reduction synchronously, asynchronously, on-node, and off-node.

Using Python, users can create an abstract campaign specification that is transparent of low-level details such as the scheduler used on the underlying system.
Cheetah generates a campaign end-point on the target machine using the specification provided by the user. The campaign endpoint consists of an independent workspace for each experiment, and scripts to launch batch jobs to run the experiments. The runtime framework for orchestrating application workflow is termed **_Savanna_**.

Once a campaign is started, Cheetah can be used to query the status of running experiments. Finally, Cheetah can be used to generate a report for a completed campaign.


### The four steps of campaign management
There are 4 steps to conducting a parametric study using Cheetah.
1. [Create a Python-based abstract campaign specification](docs/campaign-spec)
2. Use Cheetah to generate a campaign endpoint on the target system
3. Run the campaign
4. Generate a performance report for a completed campaign

  

