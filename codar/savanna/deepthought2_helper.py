class _ResourceMap:
    """
    A class to represent a set of resources that a rank maps to.
    This is a combination of hardware threads, cores, gpus, memory.
    A rank may map to multiple cores and gpus.
    """
    def __init__(self):
        self.core_ids = None
        self.gpu_ids = None


class _RANKMap:
    """
    A class to represent mapping of ranks to resources
    """
    def __init__(self, node_config):
        self.map = dict()

        # Parse the node config to extract rank and cpu mapping
        for rank_id, core_ids in enumerate(node_config.cpu):
            if len(core_ids) > 0:
                self.map[rank_id] = _ResourceMap()
                self.map[rank_id].core_ids = core_ids

        # Parse the node config to extract rank and gpu mapping
        for rank_id, gpu_ids in enumerate(node_config.gpu):
            if len(gpu_ids) > 0:
                assert rank_id in self.map.keys(), \
                    "gpu mapping exists but cpu mapping does not for rank {}" \
                    " in node layout".format(rank_id)
                self.map[rank_id].gpu_ids = gpu_ids


def create_rankfile(run):
    assert run.node_config is not None, \
        "Node Layout not found for Deepthought2. " \
        "Please provide a node layout to the Sweep using the " \
        "DTH2CPUNode or DTH2GPUNode object."

    if run.node_config:
        _create_rankfile_node_config(run.dth_rankfile, run.nprocs, run.nodes,
                                     run.nodes_assigned, run.node_config)


def _create_rankfile_node_config(rankfile_path, nprocs, num_nodes_reqd,
                                 nodes_assigned, node_config):
    rank_map = _RANKMap(node_config).map

    lines = ""
    for i in range(num_nodes_reqd):
        next_host = nodes_assigned[i]
        rank_offset = i*len(list(rank_map.keys()))

        for j, rank_id in enumerate(rank_map.keys()):
            res_map = rank_map[rank_id]
            lines += "rank {}=+n{} ".format(j+rank_offset, next_host)
            for index, core_id in enumerate(res_map.core_ids):
                lines += "slot={}:{}\n".format(core_id/10, core_id % 10)
        
            if j+rank_offset == nprocs-1:
                break

    with open(rankfile_path, 'w') as f:
        f.write(lines)
