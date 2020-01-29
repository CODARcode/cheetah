
[Main](../index)

Node Layout
===========
Node Layout is a unique feature of Cheetah that allows users to obtain fine-grained process placement on to supported machines.
It allows pinning MPI ranks to specified cores and GPUs of a target system.
On some machines such as the Titan supercomputer at ORNL, it was a simple ranks-per-node, whereas on some machines such as Summit, more complex mapping can be achieved.
This mapping can be obtained by setting the node layout property in a Sweep object.

For machines with complex process mapping support, the Node Layout is an object describing a compute node of the system.
For the Summit supercomputer, the SummitNode() object represents a compute node.

SummitNode
==========
Due to the highly heterogeneous architecture of Summit and the associated `jsrun` utility to run jobs, running Cheetah on Summit mandates using the `node-layout` property of a Sweep where users have to map processes to resources on a node. See [examples/04-gray-scott/cheetah-summit.py](examples/04-gray-scott/cheetah-summit.py) to see an example.

The SummitNode object describes the architecture of a compute node of Summit.
It must be used to specify the process distribution onto the compute nodes on Summit.
Every application in the workflow must be specified on a SummitNode.
As Summit allows placing ranks from different applications on to the same compute node, two node configurations are possible: 1) applications share compute nodes, 2) applications reside on separate nodes.

To place application ranks on separate nodes, create a SummitNode object for each application.
The snippet below shows how to map ranks to resources of a SummitNode.
The format is `node.resource[index] = 'app_handle:rank_id'`, where resource can either be `'cpu'` or `'gpu'`.
Note that multiple CPUs can be mapped to a single rank, whereas multiple GPUs can be mapped to multiple ranks.
That is, a CPU core can only be mapped to a single application rank, whereas a GPU can be mapped to multiple ranks from multiple applications.
If a rank is mapped to multiple cores, they must be consecutive.
``` python
sim_node = SummitNode()
sim_node.cpu[0] = 'simulation:0'
sim_node.gpu[0] = 'simulation:0'
analysis_node = SummitNode()
analysis_node.cpu[0] = 'analysis:0'
analysis_node.gpu[0] = 'analysis:0'
node_layout = [sim_node, analysis_node]
```

To create a shared node layout, place multiple applications on the same SummitNode object.

``` python
shared_node = SummitNode()
shared_node.cpu[0] = 'simulation:0'
shared_node.cpu[1] = 'analysis:0'
node_layout = [shared_node]
```

Once the node layout using SummitNode objects is created, Cheetah calculates the number of compute nodes required depending upon the 'nprocs' property of the ParamRunner parameter.

[Main](../index)

