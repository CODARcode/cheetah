# !/usr/bin/env python3

"""
Create regular jsrun command-line options from a SummitNode object.
"""
from codar.savanna.run import NodeConfig


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
        self.a = len(list(self.rs)[0].ranks)
        self.c = len(list(self.rs)[0].cpus)
        self.g = len(list(self.rs)[0].gpus)
        self.r = self.ppn / self.a
        assert self.r.is_integer(), \
            "RS/node {} must be an integer. ppn={}, ranks/rs:{}" \
            "".format(self.r, self.ppn, self.a)
        self.r = self.ppn // self.a
        self.n = self.nprocs / self.ppn
        assert self.n.is_integer(), \
            "Total no. of ranks {} must be exactly divisible by number of " \
            "ranks per node {}".format(self.nprocs, self.ppn)
        self.n = self.nprocs // self.a


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
