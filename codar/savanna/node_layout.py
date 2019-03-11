class NodeLayout(object):
    """Class representing options on how to organize a multi-exe task across
    many nodes. It is the scheduler model's job to take this and produce the
    correct scheduler and runner options to make this happen, or raise an error
    if it's not possible. Note that this will generally be different for each
    machine unless it is very simple and suppored uniformly by all desired
    machines.

    A layout is represented as a list of dictionaries, where each dictionary
    described codes to be run together on a single node. The keys are
    the names of the codes, and the values are the number of processes to
    assign to each.
    """

    def __init__(self, layout_list):
        # TODO: better validation
        assert isinstance(layout_list, list)
        for item in layout_list:
            assert isinstance(item, dict)
        # For now, only allow codes to be in one node grouping
        key_sets = [set(d.keys()) for d in layout_list]
        for i, ks in enumerate(key_sets[:-1]):
            for j in range(i+1, len(key_sets)):
                shared = ks & key_sets[j]
                if shared:
                    raise ValueError("code(s) appear multiple times: "
                                     + ",".join(shared))
        self.layout_list = layout_list
        self.layout_map = {}
        for d in layout_list:
            for k in d.keys():
                self.layout_map[k] = d

    def add_node(self, node_dict):
        """Add a node to an existing layout, e.g. add sosflow."""
        node_dict = dict(node_dict) # copy
        self.layout_list.append(node_dict)
        for k in node_dict.keys():
            self.layout_map[k] = node_dict

    def get_node_containing_code(self, code):
        """Get node dict containing the specified code. Raises KeyError if
        not found."""
        return self.layout_map[code]

    def codes_per_node(self):
        return max(len(d) for d in self.layout_list)

    def shared_nodes(self):
        return sum(1 for d in self.layout_list if len(d) > 1)

    def ppn(self):
        return max(sum(d.values()) for d in self.layout_list)

    def validate(self, ppn, codes_per_node, shared_nodes):
        """Given a machine ppn and max numer of codes (e.g. 4 on cori),
        raise a ValueError if the specified layout won't fit."""
        layout_codes_per_node = self.codes_per_node()
        if layout_codes_per_node > codes_per_node:
            raise ValueError("Node layout error: %d codes > max %d"
                             % (layout_codes_per_node, codes_per_node))
        layout_ppn = self.ppn()
        if layout_ppn > ppn:
            raise ValueError("Node layout error: %d ppn > max %d"
                             % (layout_ppn, ppn))

        layout_shared_nodes = self.shared_nodes()
        if layout_shared_nodes > shared_nodes:
            raise ValueError("Node layout error: %d shared nodes > max %d"
                             % (layout_shared_nodes, shared_nodes))

    def as_data_list(self):
        """Get a copy of the data list passed to the constructor,
        suitable for JSON serialization."""
        return list(self.layout_list)

    def copy(self):
        return NodeLayout(self.as_data_list())

    @classmethod
    def default_no_share_layout(cls, ppn, code_names):
        """Create a layout object for the specified codes and ppn, where each
        code uses max procs on it's own node."""
        layout = [{ code: ppn } for code in code_names]
        return cls(layout)
