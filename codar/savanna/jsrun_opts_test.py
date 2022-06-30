# !/usr/bin/env python3
from codar.savanna.jsrun_opts import JsrunGenerator
from codar.savanna.machines import SummitNode


class NodeConfig:
    def __init__(self):
        """
        Intended to look like
        cpu = [ 0=[], 1=[], 2=[], 3=[] ]
        gpu = [ 0=[], 1=[], 2=[], 3=[] ]
        """
        self.num_ranks_per_node = 0
        self.cpu = []
        self.gpu = []

    def populate(self, s: SummitNode):
        # Parse the CPU mapping
        for i in range(42):
            rank_info = s.cpu[i]

            # if the core is not mapped, go to the next one
            if rank_info is None:
                continue

            rank_id = rank_info.split(':')[1]

            # append core id to the rank id of this run
            self.cpu[int(rank_id)].append(i)

        # Parse the GPU mapping
        for i in range(6):
            rank_list = s.gpu[i]
            if rank_list is not None:
                for rank_info in rank_list:
                    rank_id = rank_info.split(':')[1]
                    self.gpu[int(rank_id)].append(i)

        # Set the no. of ranks on the node
        self.num_ranks_per_node = len(self.cpu)

    @classmethod
    def create_from_nodelayout(cls, nl):
        """
        """
        # The first list element is SummitNode
        s = nl[0]

        # Create the NodeConfig. Set ppn.
        ranks = set()
        for cpumap in s.cpu:
            if cpumap is None:
                continue
            rankid = int(cpumap.split(":")[1])
            ranks.add(rankid)
        ppn = len(ranks)

        nc = NodeConfig()
        for i in range(ppn):
            nc.cpu.append([])
            nc.gpu.append([])
        nc.populate(s)
        return nc


def test1():
    """
    Simple test. One application. 32 CPU ranks per node. No gpus.
    """
    nl = []
    s = SummitNode()
    for i in range(32):
        s.cpu[i] = "sim:{}".format(i)

    nl.append(s)
    nprocs = 64
    nc = NodeConfig.create_from_nodelayout(nl)
    j = JsrunGenerator(nc, nprocs)
    _verify_jsrun(j, n=64, r=32, a=1, c=1, g=0)


def test2():
    """
    One application. 6 ranks per node, 7 cpus per rank, 1 gpu per rank
    """
    nl = []
    s = SummitNode()

    # 6 ranks per node, 7 cpus per rank, 1 gpu per rank
    for i in range(6):
        for j in range(7):
            s.cpu[i*7+j] = "sim:{}".format(i)
        s.gpu[i] = list()
        s.gpu[i].append("sim:{}".format(i))

    nl.append(s)
    nprocs = 12
    nc = NodeConfig.create_from_nodelayout(nl)
    j = JsrunGenerator(nc, nprocs)
    _verify_jsrun(j, n=12, r=6, a=1, c=7, g=1)


def test3():
    """
    The GTC test case.
    """
    nl = []
    s = SummitNode()
    for i in range(6):
        for j in range(7):
            s.cpu[i*7+j] = "sim:{}".format(i)
        s.gpu[i] = []
        # add the six ranks
        for j in range(6):
            s.gpu[i].append("sim:{}".format(j))

    nl.append(s)
    nprocs = 12
    nc = NodeConfig.create_from_nodelayout(nl)
    j = JsrunGenerator(nc, nprocs)
    _verify_jsrun(j, n=2, r=1, a=6, c=42, g=6)


def test4():
    """
    The iRFLoop case. 1 rank on the node using all cpus.
    """
    nl = []
    s = SummitNode()
    for i in range(42):
        s.cpu[i] = "sim:0"

    nl.append(s)
    nprocs = 1
    nc = NodeConfig.create_from_nodelayout(nl)
    j = JsrunGenerator(nc, nprocs)
    _verify_jsrun(j, n=1, r=1, a=1, c=42, g=0)


def test5():
    """
    Jong's XGC test case. 192 processes, 32 RS per node, no gpus
    """
    nl = []
    s = SummitNode()
    for i in range(32):
        s.cpu[i] = "sim:{}".format(i)
    
    nl.append(s)
    nprocs = 192
    nc = NodeConfig.create_from_nodelayout(nl)
    j = JsrunGenerator(nc, nprocs)
    _verify_jsrun(j, n=192, r=32, a=1, c=1, g=0)


def _verify_jsrun(j, n, r, a, c, g):
    import inspect
    caller_f = inspect.stack()[1][3]
    status = "succeeded"

    print("Verifying {}".format(caller_f))
    for vals in [[j.n, n, "n"], [j.r, r, "r"], [j.a, a, "a"], [j.c, c, "c"],
                 [j.g, g, "g"]]:

        if not vals[0] == vals[1]:
            status = "failed"
            print("Error: {} : received {}, expected {}"
                  "".format(vals[2], vals[0], vals[1]))

    print("{} {}\n".format(caller_f, status))


# --------------------------------------------------------------------------- #
if __name__ == '__main__':
    test1()
    test2()
    test3()
    test4()
    test5()
