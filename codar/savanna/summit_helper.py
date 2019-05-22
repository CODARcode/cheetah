from codar.savanna.machines import SummitNode
import math


def get_nodes_reqd(res_set, nrs):
    """Get the no. of nodes that will be required based on the resource set
    and the no. of resource sets"""

    return math.ceil(nrs/res_set.rs_per_host)


def create_erf_file(run):
    assert not ((run.res_set is None) and (run.node_config is None)), \
        "Both resource set info and node config info cannot be none"

    if run.node_config:
        _create_erf_file_node_config(run.erf_file, run.exe, run.args,
                                     run.nprocs, run.nodes,
                                     run.nodes_assigned, run.node_config)
    else:  # if run.res_set:
        _create_erf_file_res_set(run, run.nodes_assigned, run.res_set)


def _create_erf_file_res_set(run, nodes_assigned, res_set):
    pass


def _create_erf_file_node_config(erf_file_path, run_exe, run_args,
                                 nprocs, num_nodes_reqd, nodes_assigned,
                                 node_config):
    str = _get_first_erf_block(run_exe, run_args)
    for i in range(num_nodes_reqd):
        next_host = nodes_assigned[i]
        rank_offset = i * node_config.num_ranks_per_node
        for j in range(node_config.num_ranks_per_node):
            rank_id = rank_offset+j
            str += '\nrank: {}: {{ host: {}; cpu: '.format(rank_id,
                                                           next_host)
            for index, core_id in enumerate(node_config.cpu[j]):
                if index > 0:
                    str += ', '
                str += "{{{}-{}}}".format(core_id*4, core_id*4+3)

            if len(node_config.gpu[j]) > 0:
                str += " ; gpu: {"

            for gpu_id in node_config.gpu[j]:
                str += "{},".format(gpu_id)

            # Remove the last comma
            str = str[:-1]
            str += "}"

            str += " } : app 0"
            if rank_id == nprocs-1:
                break

    # jsrun fails without this line break
    str += "\n"
    with open(erf_file_path, 'w') as f:
        f.write(str)


def _get_first_erf_block(run_exe, run_args):
    str = "app 0: {} ".format(run_exe) + " ".join(run_args) + "\n"
    str += "cpu_index_using: logical\n"
    str += "overlapping_rs: warn\n"
    str += "skip_missing_cpu: warn\n"
    str += "skip_missing_gpu: allow\n"
    str += "skip_missing_mem: allow\n"
    str += "oversubscribe_cpu: warn\n"
    str += "oversubscribe_gpu: allow\n"
    str += "oversubscribe_mem: allow\n"
    str += "launch_distribution: packed"
    return str

# app 0: js_task_info
# cpu_index_using: logical
# overlapping_rs: warn
# skip_missing_cpu: warn
# skip_missing_gpu: allow
# skip_missing_mem: allow
# oversubscribe_cpu: warn
# oversubscribe_gpu: allow
# oversubscribe_mem: allow
# launch_distribution: packed
# rank: 0: { host: 1; cpu: {0-3}, {4-11} ; gpu: {0,1} } : app 0
# rank: 1: { host: 1; cpu: {4-7}, {0-3,8-11} ; gpu: {0,1} } : app 0
# rank: 2: { host: 1; cpu: {8-11}, {0-7} ; gpu: {0,1} } : app 0
# rank: 3: { host: 1; cpu: {84-87}, {88-95} ; gpu: {3,4} } : app 0
# rank: 4: { host: 1; cpu: {88-91}, {84-87,92-95} ; gpu: {3,4} } : app 0
# rank: 5: { host: 1; cpu: {92-95}, {84-91} ; gpu: {3,4} } : app 0

# MY NOTES:
# 1 PE may be mapped to multiple CPUs
# jsrun does allow one CPU to be mapped to multiple ranks. We don't allow it.
# 1 GPU may be mapped to multiple ranks
#   of the same application?
