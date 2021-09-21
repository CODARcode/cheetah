# !/usr/bin/env python3

"""
Create regular jsrun command-line options from a SummitNode object.
"""
from codar.savanna.model import NodeConfig


class SummitNode:
    def __init__(self):
        self.cpu = [None] * 42
        self.gpu = [None] * 6


class ResourceSet:
    def __init__(self):
        self.ranks = set()
        self.cpus = set()
        self.gpus = set()


class JsrunGenerator:
    def __init__(self, nc: NodeConfig, nprocs: int):
        """
        :param nc: NodeConfig for this application
        :param nprocs: Total no. of nprocs for the Run
        """
        # jsrun -n -r -a -c -g
        self.n = None
        self.r = None
        self.a = None
        self.c = None
        self.g = None

        self.nc = nc
        self.ppn = nc.num_ranks_per_node
        self.nprocs = nprocs
        self.rs = set()
        self._create_rs()
        self._validate_all_rs()
        self._set_jsrun_options()

    def get_jsrun_opts_noerf(self):
        """
        Set jsrun options where we don't use ERF files.
        """
        pass

    def _create_rs(self):
        # Parse the cpu mapping
        for index in range(self.nc.num_ranks_per_node):
            rs = self._get_enclosing_rs(rankid=index)
            if rs is None:
                rs = ResourceSet()
                self.rs.add(rs)
                rs.ranks.add(index)
            cpulist = self.nc.cpu[index]
            assert len(cpulist) > 0, \
                "CPU map for rank {} cannot be empty".format(index)
            for cpu in cpulist:
                rs.cpus.add(cpu)

        # Parse the gpu mapping
        for index in range(self.nc.num_ranks_per_node):
            gpulist = self.nc.gpu[index]
            if len(gpulist) == 0:
                continue
            for gpu in gpulist:
                rs = self._get_enclosing_rs(rankid=index)
                gpu_rs = self._get_enclosing_rs(gpuid=gpu)
                if gpu_rs is None:
                    rs.gpus.add(gpu)
                elif rs is not gpu_rs:
                    self._merge_rs(rs, gpu_rs)
                else:  # rs == gpurs, do nothing
                    pass

    def _validate_all_rs(self):
        """
        Ensure all resource sets have similar a,c,g requirements
        """
        a = len(list(self.rs)[0].ranks)
        c = len(list(self.rs)[0].cpus)
        g = len(list(self.rs)[0].gpus)

        for rs in self.rs:
            assert len(rs.ranks) == a, \
                "No. of ranks mismatch {}, {} in resource sets" \
                "".format(len(rs.ranks), a)
            assert len(rs.cpus) == c, \
                "No. of cpus mismatch {}, {} in resource sets" \
                "".format(len(rs.cpus), c)
            assert len(rs.gpus) == g, \
                "No. of gpus mismatch {}, {} in resource sets" \
                "".format(len(rs.gpus), g)

    def _set_jsrun_options(self):
        self.n = self.nprocs / self.ppn
        assert self.n.is_integer(), \
            "Total no. of ranks {} must be exactly divisible by number of " \
            "ranks per node {}".format(self.nprocs, self.ppn)
        self.n = self.nprocs // self.ppn
        self.a = len(list(self.rs)[0].ranks)
        self.r = self.ppn / self.a
        assert self.r.is_integer(), \
            "RS/node {} must be an integer. ppn={}, ranks/rs:{}" \
            "".format(self.r, self.ppn, self.a)
        self.r = self.ppn // self.a
        self.c = len(list(self.rs)[0].cpus)
        self.g = len(list(self.rs)[0].gpus)

    def _get_enclosing_rs(self, rankid=None, gpuid=None):
        if rankid is not None:
            return self._get_enclosing_rank_rs(rankid)
        else:
            return self._get_enclosing_gpu_rs(gpuid)

    def _get_enclosing_rank_rs(self, rankid):
        for rs in self.rs:
            if rankid in rs.ranks:
                return rs
        return None

    def _get_enclosing_gpu_rs(self, gpuid):
        for rs in self.rs:
            if gpuid in rs.gpus:
                return rs
        return None

    def _merge_rs(self, rs1, rs2):
        """
        Remove rs1 and rs2 from self.rs list, merge them, and add the new rs
        to self.rs
        """
        mergedrs = ResourceSet()
        for rs in (rs1, rs2):
            for rank in rs.ranks:
                mergedrs.ranks.add(rank)
            for cpuid in rs.cpus:
                mergedrs.cpus.add(cpuid)
            for gpuid in rs.gpus:
                mergedrs.gpus.add(gpuid)

        self.rs.remove(rs1)
        self.rs.remove(rs2)
        self.rs.add(mergedrs)


# TEST CODE BELOW. KEEP FOR FUTURE TEST SUITE DEVELOPMENT.
#
# def _verify_jsrun(j, n, r, a, c, g):
#     import inspect
#     caller_f = inspect.stack()[1][3]
#     status = "succeeded"
#
#     print("Verifying {}".format(caller_f))
#     for vals in [[j.n, n, "n"], [j.r, r, "r"], [j.a, a, "a"], [j.c, c, "c"],
#                  [j.g, g, "g"]]:
#
#         if not vals[0] == vals[1]:
#             status = "failed"
#             print("Error: {} : received {}, expected {}"
#                   "".format(vals[2], vals[0], vals[1]))
#
#     print("{} {}\n".format(caller_f, status))
#
#
# class SummitNode:
#     def __init__(self):
#         self.cpu = [None] * 42
#         self.gpu = [None] * 6
#
#
# class NodeConfig:
#     def __init__(self):
#         """
#         Intended to look like
#         cpu = [ 0=[], 1=[], 2=[], 3=[] ]
#         gpu = [ 0=[], 1=[], 2=[], 3=[] ]
#         """
#         self.num_ranks = 0
#         self.cpu = []
#         self.gpu = []
#
#     def populate(self, s: SummitNode):
#         # Parse the CPU mapping
#         for i in range(42):
#             rank_info = s.cpu[i]
#
#             # if the core is not mapped, go to the next one
#             if rank_info is None:
#                 continue
#
#             run_name = rank_info.split(':')[0]
#             rank_id = rank_info.split(':')[1]
#
#             # append core id to the rank id of this run
#             self.cpu[int(rank_id)].append(i)
#
#         # Parse the GPU mapping
#         for i in range(6):
#             rank_list = s.gpu[i]
#             if rank_list is not None:
#                 for rank_info in rank_list:
#                     run_name = rank_info.split(':')[0]
#                     rank_id = rank_info.split(':')[1]
#                     self.gpu[int(rank_id)].append(i)
#
#         # Set the no. of ranks on the node
#         self.num_ranks = len(self.cpu)
#
#     @classmethod
#     def create_from_nodelayout(self, nl):
#         """
#         """
#         # The first list element is SummitNode
#         s = nl[0]
#
#         # Create the NodeConfig. Set ppn.
#         ranks = set()
#         for cpumap in s.cpu:
#             if cpumap is None:
#                 continue
#             rankid = int(cpumap.split(":")[1])
#             ranks.add(rankid)
#         ppn = len(ranks)
#
#         nc = NodeConfig()
#         for i in range(ppn):
#             nc.cpu.append([])
#             nc.gpu.append([])
#         nc.populate(s)
#         return nc
#
# def test1():
#     """
#     Simple test. One application. 32 CPU ranks per node. No gpus.
#     """
#     nl = []
#     s = SummitNode()
#     for i in range(32):
#         s.cpu[i] = "sim:{}".format(i)
#
#     nl.append(s)
#     nprocs = 64
#     nc = NodeConfig.create_from_nodelayout(nl)
#     j = JsrunGenerator(nc, nprocs)
#     _verify_jsrun(j, n=2, r=32, a=1, c=1, g=0)
#
#
# def test2():
#     """
#     One application. 6 ranks per node, 7 cpus per rank, 1 gpu per rank
#     """
#     nl = []
#     s = SummitNode()
#
#     # 6 ranks per node, 7 cpus per rank, 1 gpu per rank
#     for i in range(6):
#         for j in range(7):
#             s.cpu[i * 7 + j] = "sim:{}".format(i)
#         s.gpu[i] = list()
#         s.gpu[i].append("sim:{}".format(i))
#
#     nl.append(s)
#     nprocs = 12
#     nc = NodeConfig.create_from_nodelayout(nl)
#     j = JsrunGenerator(nc, nprocs)
#     _verify_jsrun(j, n=2, r=6, a=1, c=7, g=1)
#
#
# def test3():
#     """
#     The GTC test case.
#     """
#     nl = []
#     s = SummitNode()
#     for i in range(6):
#         for j in range(7):
#             s.cpu[i * 7 + j] = "sim:{}".format(i)
#         s.gpu[i] = []
#         # add the six ranks
#         for j in range(6):
#             s.gpu[i].append("sim:{}".format(j))
#
#     nl.append(s)
#     nprocs = 12
#     nc = NodeConfig.create_from_nodelayout(nl)
#     j = JsrunGenerator(nc, nprocs)
#     _verify_jsrun(j, n=2, r=1, a=6, c=42, g=6)
#
#
# def test4():
#     """
#     The iRFLoop case. 1 rank on the node using all cpus.
#     """
#     nl = []
#     s = SummitNode()
#     for i in range(42):
#         s.cpu[i] = "sim:0"
#
#     nl.append(s)
#     nprocs = 1
#     nc = NodeConfig.create_from_nodelayout(nl)
#     j = JsrunGenerator(nc, nprocs)
#     _verify_jsrun(j, n=1, r=1, a=1, c=42, g=0)
#
#
#
# if __name__ == '__main__':
#     test1()
#     test2()
#     test3()
#     test4()
