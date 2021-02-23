import savanna

#----------------------------------------------------------------------------#
def node_layout_to_json(layouts):
    """Temporary Cheetah functionality to serialize VirtualNode objects
    """
    d = []
    for nl in layouts:
        d.append(nl.to_dict())
    return d


def num_nodes_available():
    """Placeholder for fetching the number of allocated nodes
    """

    # Put a try-except for testing. At runtime, you can get 
    # the no. of nodes in this allocating by inspecting the
    # LSB_HOSTS env var.
    try:
        hosts = os.environ.get['LSB_HOSTS']
    except:  # Mock values for testing purposes
        hosts = "batch4 h4cn1 h4cn2"

    s = set()
    for h in hosts.split():
        if ('batch' not in h) and ('login' not in h):
            s.add(h)
    return len(s)

#----------------------------------------------------------------------------#
# Create the applications (objects of class Run)
#s = Run(name='simulation', exe='gray-scott', 
#        args=['settings-files.json'], nprocs=32)
s = savanna.Run(name='simulation', exe='hostname', args=[], nprocs=2)

# Create a pipeline (workflow) of concurrently running applications
p = savanna.Pipeline(runs=[s])

# Create a mapping of ranks to resources using the VirtualNode model
node = savanna.SummitNode()
for i in range(32):
    node.cpu[i] = "simulation:{}".format(i)
node_layout = [node]

# Temporary Cheetah functionality to serialize VirtualNode objects
d = node_layout_to_json(node_layout)

# Launch the pipeline
p.run(d, num_nodes_available())

