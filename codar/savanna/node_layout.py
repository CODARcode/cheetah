import pdb
import copy
from codar.savanna.machines import MachineNode


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
        assert isinstance(layout_list, list), "Node Layout must be a list"
        for item in layout_list:
            assert isinstance(item, dict) or isinstance(item, MachineNode), \
                "Items in a node layout must be a dict or a Machine Node " \
                "depending on your target system"

        # # For now, only allow codes to be in one node grouping
        # key_sets = [set(d.keys()) for d in layout_list]
        # for i, ks in enumerate(key_sets[:-1]):
        #     for j in range(i+1, len(key_sets)):
        #         shared = ks & key_sets[j]
        #         if shared:
        #             raise ValueError("code(s) appear multiple times: "
        #                              + ",".join(shared))
        self.layout_list = layout_list
        self.layout_map = {}
        for d in layout_list:
            if type(d) == dict:
                for k in d.keys():
                    self.layout_map[k] = d

        self._validate()

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

    def _validate(self):
        """Validate the layout.
        Includes code to check layout on Summit that could be a
        dict/nodeconfig."""

        code_occurences = set()

        # Check if codes appear multiple times in the node-layout
        for layout_info in self.layout_list:
            if isinstance(layout_info, MachineNode):
                codes_in_config = set()
                layout_info.validate_layout()

                # Get the unique codes in the nodeconfig and check if they
                # are already in code_occurences
                for core_map in layout_info.cpu:
                    if core_map is not None:
                        codename = core_map.split(':')[0]
                        codes_in_config.add(codename)
                for codename in codes_in_config:
                    if codename in code_occurences:
                        raise ValueError("{} found in node-layout multiple "
                                         "times".format(codename))
                    code_occurences.add(codename)

            elif type(layout_info) == dict:
                for k in layout_info:
                    if k in code_occurences:
                        raise ValueError("{} found in node-layout multiple "
                                         "times").format(k)
                    code_occurences.add(k)

    def validate(self, ppn, codes_per_node, shared_nodes):
        """Given a machine ppn and max numer of codes (e.g. 4 on cori),
        raise a ValueError if the specified layout won't fit.
        Dont modify this yet, this is being used by the tests

        TODO:
        Ensure that all of them are of the same type, i.e. either virtual
        node or code:ppn mapping.
        For virtual nodes, verify that the same code does not appear in
        multiple vnodes. also ensure that for Summit, contiguous cores are
        mapped to ranks of a code
        """
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
        return self.layout_list

    def serialize_to_dict(self):
        """Get a copy of the data list passed to the constructor,
        suitable for JSON serialization."""
        data_list = []
        for elem in self.layout_list:
            if isinstance(elem, MachineNode):
                data_list.append(elem.to_json())
            else:
                data_list.append(elem)

        return data_list

    def copy(self):
        return NodeLayout(self.as_data_list())

    def group_codes_by_node(self):
        """Return a list of dicts, where each list represents codes on a
        node, and a dict key for ppn
        Example: [ {sim,analysis1}, {analysis2}, {viz} ].
        Must take Summit NodeConfigs into account

        FIXME: Returns different things for different machines.
        Returns a list of cpu mappings for Summit, and list of ppn for other
        machines"""

        code_groups = []

        # loop over the different layouts
        for layout_info in self.layout_list:

            # if this is a node-config
            if isinstance(layout_info, MachineNode):
                unique_codes = {}
                # loop over the cpu core mappings and get the code name
                for core_mapping in layout_info.cpu:
                    if core_mapping is not None:
                        codename = core_mapping.split(':')[0]
                        rank_id = int(core_mapping.split(':')[1])
                        if codename not in unique_codes:
                            unique_codes[codename] = set()
                        unique_codes[codename].add(rank_id)
                code_groups.append(unique_codes)

            # if this is a dict
            elif type(layout_info) == dict:
                code_groups.append(copy.deepcopy(layout_info))

        return code_groups

    def populate_remaining(self, rc_names, ppn):
        code_groups = self.group_codes_by_node()
        codes_covered = []
        for code_group in code_groups:
            k = list(code_group.keys())
            for key in k:
                codes_covered.append(key)
        for rc_name in rc_names:
            if rc_name not in codes_covered:
                self.add_node({rc_name: ppn})

    @classmethod
    def default_no_share_layout(cls, ppn, code_names):
        """Create a layout object for the specified codes and ppn, where each
        code uses max procs on it's own node."""
        layout = [{ code: ppn } for code in code_names]
        return cls(layout)
