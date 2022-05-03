from codar.savanna.machines import SummitNode
from codar.savanna.error_messages import err_msg
import math
import pdb

# Snippet below lets pycharm understand the 'Run' object so that we can
# create type hints. Cannot import it as it would create a cyclic import
if False:
    from codar.savanna.run import Run


class _ResourceMap:
    """
    A class to represent a set of resources that a rank maps to.
    This is a combination of hardware threads, cores, gpus, memory.
    A rank may map to multiple cores and gpus.
    """
    def __init__(self):
        self.core_ids = None
        self.gpu_ids = None


class _ERFMap:
    """
    A class to represent erf-style mapping of ranks to resources
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


def get_nodes_reqd(res_set, nrs):
    """Get the no. of nodes that will be required based on the resource set
    and the no. of resource sets"""

    return math.ceil(nrs/res_set.rs_per_host)


def create_erf_file_mpmd(run: 'Run'):
    # assert that the mpmd run has child runs
    assert run.child_runs is not None, err_msg['mpmd_run_error']

    # assert that all child runs have a node config object
    for crun in run.child_runs:
        assert crun.node_config is not None, err_msg['run_node_config_missing']

    # start creating the erf file
    # 1. add the first set of lines that define the executables
    erf_str = ""
    app_index = 0
    crun: Run  # type hint
    for crun in run.child_runs:
        erf_str += "app {}: {}".format(app_index, crun.app_sh) + "\n"
        app_index += 1

    # 2. Add the rest of the initial block
    erf_str += _get_first_erf_block()

    # 3. Add the rank to resource mapping for each app in the mpmd run
    global_rank_id = 0
    for app_id, crun in enumerate(run.child_runs):
        erf_map = _ERFMap(crun.node_config).map
        erf_str += _get_erf_map_str_block(crun.nprocs, erf_map, crun.nodes,
                                          crun.nodes_assigned, app_id,
                                          global_rank_id)
        global_rank_id = global_rank_id + crun.nprocs

    # 4. Add a newline. jsrun apparently fails without it.
    erf_str += '\n'

    # 5. Done. Write the erf text to file.
    with open(run.erf_file, 'w') as f:
        f.write(erf_str)


def create_erf_file(run):
    assert not ((run.res_set is None) and (run.node_config is None)), \
        "Node Layout not found for Summit. Please provide a node layout " \
        "to the Sweep using the SummitNode object."

    if run.node_config:
        _create_erf_file_node_config(run.erf_file, run.app_sh,
                                     run.nprocs, run.nodes,
                                     run.nodes_assigned, run.node_config)
    else:  # if run.res_set:
        _create_erf_file_res_set(run, run.nodes_assigned, run.res_set)


def _create_erf_file_res_set(run, nodes_assigned, res_set):
    pass


def _create_erf_file_node_config(erf_file_path, run_app_sh,
                                 nprocs, num_nodes_reqd,
                                 nodes_assigned, node_config):

    # Write first line defining app
    # exe_filename = _create_exe_script(run_dir, run_name, run_exe, run_args)
    str = "app 0: {}".format(run_app_sh) + "\n"

    # Get the initial block of text
    str += _get_first_erf_block()

    # Retrieve the erf rank to resource mapping from the node config
    erf_map = _ERFMap(node_config).map

    # Get the erf text for the rank to resource mapping
    str += _get_erf_map_str_block(nprocs, erf_map, num_nodes_reqd,
                                  nodes_assigned, 0, 0)

    # Add a newline as jsrun fails without this line break
    str += "\n"

    # Done. Write all the erf text to file
    with open(erf_file_path, 'w') as f:
        f.write(str)


def _get_erf_map_str_block(nprocs, erf_map, num_nodes_reqd, nodes_assigned,
                           app_id, starting_global_rank_id):
    str = ""
    for i in range(num_nodes_reqd):
        next_host = nodes_assigned[i]
        rank_offset = starting_global_rank_id + i*len(list(erf_map.keys()))

        for i, rank_id in enumerate(erf_map.keys()):
            res_map = erf_map[rank_id]
            str += '\nrank: {}: {{ host: {}; cpu: '.format(i+rank_offset,
                                                           next_host)
            core_start = res_map.core_ids[0]
            core_end = res_map.core_ids[-1]

            str += "{{{}-{}}}".format(core_start*4, core_end*4+3)

            if res_map.gpu_ids:
                str += " ; gpu: {"

                for gpu_id in res_map.gpu_ids:
                    str += "{},".format(gpu_id)

                # Remove the last comma
                str = str[:-1]
                str += "}"

            str += " }} : app {}".format(app_id)

            if i+rank_offset-starting_global_rank_id == nprocs-1:
                break
    return str


def _create_exe_script(run_dir, handle, exe, args):
    """
    Create a run*.sh executable file to run this executable.
    You cannot have 'exe 1> stdout 2> stderr' in the erf file, so you need
    to have a 'run-x.sh' in the erf file which has the stdout and stderr
    redirection operators in it.
    """
    exe_filename = None

    str = "{} ".format(exe) + " ".join(args)
    exe_filename = run_dir + '/.savanna.run.{}.sh'.format(handle)
    try:
        with open(exe_filename,'w') as f:
            f.write(str)
    except:
        print(err_msg['f_create'].format(exe_filename))
        # To exit or not to exit

    return exe_filename


def _get_first_erf_block():
    str = "cpu_index_using: logical\n"
    str += "overlapping_rs: warn\n"
    str += "skip_missing_cpu: warn\n"
    str += "skip_missing_gpu: allow\n"
    str += "skip_missing_mem: allow\n"
    str += "oversubscribe_cpu: error\n"
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
