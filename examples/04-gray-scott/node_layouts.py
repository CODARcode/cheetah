from codar.savanna.machines import SummitNode

#----------------------------------------------------------------------------#
def separate_nodes():
    """
    Create a node layout where the simulation and the analysis ranks reside
    on separate nodes.
    """

    # Create a node layout for the simulation
    # Lets have max 20 ranks evenly spread out between 2 sockets
    sim_node = SummitNode()
    for i in range(10):
        sim_node.cpu[i] = "simulation:{}".format(i)
        sim_node.cpu[21+i] = "simulation:{}".format(10+i)

    # Create a node layout for the analysis.
    # Lets have max 10 ranks evenly spread out
    analysis_node = SummitNode()
    for i in range(5):
        analysis_node.cpu[i] = "pdf_calc:{}".format(i)
        analysis_node.cpu[21+i] = "pdf_calc:{}".format(5+i)

    # Return a list object
    return [sim_node, analysis_node]


#----------------------------------------------------------------------------#
def share_nodes():
    """
    Create a shared node layout where the simulation and analysis ranks share
    compute nodes
    """
    
    shared_node = SummitNode()
    for i in range(20):
        shared_node.cpu[i] = "simulation:{}".format(i)
        shared_node.cpu[21+i] = "pdf_calc:{}".format(i)

    return [shared_node]


#----------------------------------------------------------------------------#
def share_nodes_sockets():
    """
    Create a shared node layout where the simulation and analysis ranks share
    compute nodes. Furthermore, they share sockets of the node.
    """

    shared_sockets = SummitNode()
    for i in range(10):
        shared_sockets.cpu[i] = "simulation:{}".format(i)
        shared_sockets.cpu[21+i] = "simulation:{}".format(10+i)
    
    for i in range(10):
        shared_sockets.cpu[10+i] = "pdf_calc:{}".format(i)
        shared_sockets.cpu[21+10+i] = "pdf_calc:{}".format(10+i)

    return [shared_sockets]

