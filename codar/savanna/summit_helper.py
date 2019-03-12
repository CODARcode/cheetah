from codar.savanna.machines import SummitNode
import math


def get_nodes_reqd(res_set, nrs):
    """Get the no. of nodes that will be required based on the resource set
    and the no. of resource sets"""

    return math.ceil(nrs/res_set.rs_per_host)
