"""
This is a stripped-down implementation of the Savanna workflow tool.
It provides basic functionality to create a Pipeline (workflow) of
Runs (applications).
This can be used to create and test different executor backends for 
running/submitting jobs on Summit.
An example backend with jsrun is provided, and a skeleton framework
for PMIx is created.
"""

import pdb
import math
import os
import threading
from jsrun_backend import JsrunExecutor
import pmix_backend


#----------------------------------------------------------------------------#
class MachineNode:
    def __init__(self, num_cpus, num_gpus):
        # self.id = id
        self.cpu = [None] * num_cpus
        self.gpu = [None] * num_gpus


#----------------------------------------------------------------------------#
class SummitNode():
    def __init__(self):
        MachineNode.__init__(self, 42, 6)

    def to_dict(self):
        d = {}
        d['cpu'] = self.cpu
        d['gpu'] = self.gpu
        return d


#----------------------------------------------------------------------------#
class NodeConfig:
    def __init__(self):
        """An internal serialization layer for the VirtualNode.
        Get a list of all ranks on a node.
        Intended to look like
        cpu = [ 0=[], 1=[], 2=[], 3=[] ]
        gpu = [ 0=[], 1=[], 2=[], 3=[] ]
        """
        self.num_ranks_per_node = 0
        self.cpu = []
        self.gpu = []


#----------------------------------------------------------------------------#
class PmixExecutor():
    def __init__(self, run):
        self.run = run

    def execute(self):
        pass


#----------------------------------------------------------------------------#
class Run(threading.Thread):
    """Represents an application instance
    """
    def __init__(self, name, exe, args, nprocs):
        threading.Thread.__init__(self)
        self.name = name
        self.exe = exe
        self.args = args
        self.nprocs = nprocs
        self.nodes = 0
        self.nodes_assigned = None
        self.working_dir = "./"
        self.node_config = None
        self.erf_file = None

        # Max runtime for this application, in seconds. 
        self.timeout = 60

        # Redirect stdout and stderr
        # stdout_path = "{}.stdout".format(self.name)
        # stderr_path = "{}.stderr".format(self.name)
        # self.args.extend(['>', stdout_path])
        # self.args.extend(['2>', stderr_path])

        # Set the backend here
        self._backend_executor = JsrunExecutor(self)

    def run(self):
        assert self.nodes > 0
        self._backend_executor.execute()

#----------------------------------------------------------------------------#
class Pipeline():
    """A Pipeline is a workflow, or a collection of applications that form 
    the workflow.
    For this example, it is just a collection of applications (Run objects) 
    that run concurrently. No dependencies or other complex stuff.
    """
    def __init__(self, runs):
        """
        """

        # Store Runs as a dict indexed by the run name
        self.runs = {}
        for s in runs:
            self.runs[s.name] = s
        
        # Ensure unique run names
        s = set()
        for r in self.runs:
            s.add(r)
        assert len(s) == len(list(self.runs.keys())), \
            "Error: Duplicate run names found."

    def run(self, layouts, num_nodes):
        for layout in layouts:
            self._parse_layout(layout)
        assert num_nodes >= self.min_nodes()

        # Launch each run in separate thread 
        for s in self.runs.values():
            s.start()

        # Wait for all Runs to complete
        for s in self.runs.values():
            s.join()

        print("Done")

    def min_nodes(self):
        """The minimum no. of Summit nodes required to run this pipeline.
        """
        return max([r.nodes for r in list(self.runs.values())])

    def _parse_layout(self, layout_info):
        """Parse the SummitNode layout
        """

        # 1. Set the no. of nodes required for this Run
        # Get the ranks per node for each run
        num_ranks_per_run = {}
        for rank_info in layout_info['cpu']:
            if rank_info is not None:
                run_name = rank_info.split(':')[0]
                rank_id = int(rank_info.split(':')[1])
                if run_name not in list(num_ranks_per_run.keys()):
                    num_ranks_per_run[run_name] = set()
                num_ranks_per_run[run_name].add(rank_id)

        # set the no. of nodes for the codes on this node
        for code in num_ranks_per_run:
            run = self.runs[code]
            run.nodes = math.ceil(run.nprocs/len(num_ranks_per_run[code]))

        # 2. Create the node config for each Run
        # Add run to codes_on_node and create nodeconfig for each run
        for run_name in num_ranks_per_run.keys():
            num_ranks_per_node = len(num_ranks_per_run[run_name])
            run = self.runs[run_name]
            run.node_config = NodeConfig()
            run.node_config.num_ranks_per_node = num_ranks_per_node
            for i in range(num_ranks_per_node):
                # Every rank for this run has a list of cpu and gpu cores
                run.node_config.cpu.append([])
                run.node_config.gpu.append([])

        # Loop over the cpu core mapping
        for i in range(len(layout_info['cpu'])):
            rank_info = layout_info['cpu'][i]

            # if the core is not mapped, go to the next one
            if rank_info is None:
                continue

            run_name = rank_info.split(':')[0]
            rank_id = rank_info.split(':')[1]
            run = self.runs[run_name]

            # append core id to the rank id of this run
            run.node_config.cpu[int(rank_id)].append(i)

        # Loop over the gpu mapping
        for i in range(len(layout_info['gpu'])):
            rank_list = layout_info['gpu'][i]
            if rank_list is not None:
                for rank_info in rank_list:
                    run_name = rank_info.split(':')[0]
                    rank_id = rank_info.split(':')[1]
                    run = self.runs[run_name]
                    run.node_config.gpu[int(rank_id)].append(i)

