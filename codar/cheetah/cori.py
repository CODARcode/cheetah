"""
"""
from codar.cheetah import machines
from codar.cheetah import launchers
from codar.cheetah import schedulers


class Cori(machines.Machine):
    def __init__(self):
        self.name = "cori-haswell"
        self.launcher = launchers.Launcher
        self.scheduler = schedulers.slurm
        # the runner_name below can be obtained from the scheduler
        # self.runner_name = "srun"
        self.processes_per_node = 32
        self.node_partitioning_available = True

    def is_partitioning_valid(self, app_ranks_node_partition):
        """
        Validate the compute node partitioning requested by the user.
        Input is a list of integers representing no. of app ranks per compute node requested.
        e.g. [8,2] could represent the user requesting 8 simulation and 2 staging processes
            per compute node.
        also, [8,2,0] could represent 8 heat, 2 stage, and 0 viz processes on the compute node,
        all viz processes are spawned on separate, dedicated nodes.
        """
        if sum(app_ranks_node_partition) > self.processes_per_node:
            return False
        return True

    def get_num_nodes_required(self,
                               total_requested_app_ranks,
                               app_ranks_node_partition):
        """
        This function returns the no. of nodes that will be required to
        run the experiment.
        It depends on the total no. of processes requested and
        the partition characteristics.
        For example, run heat with 128 processes total,
        and stage with 64 processes total,
        viz with 32 processes total, with
        node partitioning set to [8,2,0], that is,
        8 heat and 2 stage processes per compute node, and viz processes
        on dedicated nodes.
        so, what is the no. of nodes that will be required by this setup?

        This is a generic procedure that will work even if node_partitioning
        is not set. That is, if app_ranks_node_partition = [0,0,0] which
        indicates all apps run on dedicated nodes.
        """
        num_nodes_required = 0

        # Get num nodes required by apps participating in the node partitioning
        # heat and stage in the above example
        num_nodes_required = \
            int(max([math.ceil(total_requested_app_ranks[i] /
                               app_ranks_node_partition[i])
                     for (i, j) in enumerate(total_requested_app_ranks)
                     if app_ranks_node_partition[i] != 0]))

        # Get num nodes required by apps not participating in the node partitioning
        # that is the viz app in the above example
        num_nodes_required = num_nodes_required + \
                             sum([math.ceil(x/self.processes_per_node)
                                  for (i, x) in enumerate(total_requested_app_ranks)
                                  if app_ranks_node_partition[i] == 0])

        return num_nodes_required
