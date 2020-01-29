
[Main](../index)

* TOC
{:toc}

Savanna
=======

Architecture
------------

![Architecture of Savanna](savanna-arch.pdf?raw=true "Savanna Architecture")

## Directory structure of the campaign

 
Savanna Files
-------------
At runtime, Savanna creates the following files:
`codar.FOBrun.log` - A log written by Savanna that shows various actions taken by Savanna such as starting an experiment, experiment completion, 
The stdout and stderr of each application in an experiment is redirected to `codar.workflow.stdout.<app-name>` and `codar.workflow.stderr.<app-name>` respectively.  
Similarly, Savanna creates files to store the runtime of each workflow component and its return code.

[Main](../index)

