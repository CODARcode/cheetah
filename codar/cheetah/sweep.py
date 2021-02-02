"""
Sweep class
"""
import os
import itertools

class Sweep(object):
    """
    Class representing a set of parameter values to search over as
    a cross product.
    """
    def __init__(self, name, parameters, node_layout=None, rc_dependency=None):
        self.name = name
        self.parameters = parameters
        self.node_layout = node_layout
        self.rc_dependency = rc_dependency

    def set_parent_sg(self, sg_path):
        self._parent_sg = sg_path
        self._path = os.path.join(self._parent_sg, self.name)

    def validate(self):
        """
        Assert sweep dir doesn't already exist.
        """
        assert self._path is not None, \
            "Internal error. Sweep {} does not have path set".format(self.name)

        # Assert sweep does not exist already
        self._assert_no_exist()

    def _assert_no_exist(self):
        """
        Assert sweep dir does not exist already.
        """

        # Return if the parent sweep group dir doesn't exist
        if not os.path.isdir(self._parent_sg): return

        # Assert sweep dir doesn't exist
        assert os.path.isdir(self._path) is False, \
            "Sweep {} already exists".format(self.name)

    def get_instances(self):
        """
        Get a list of Instance objects representing dense cross product over
        param values.

        TODO: this works great for command line options and args, but
        what about for config and other types of params? Need to setup
        a run dir and populate it with filled config templates.

        Also how to pass per run output dir? Or is just making CWD the
        per run dir enough for all cases we care about?

        TODO: should have same signature as SweepGroup version OR a
        different name.
        """
        inst_list = []
        indexes = [range(len(p)) for p in self.parameters]
        for idx_set in itertools.product(*indexes):
            inst = Instance()
            for param_i, value_i in enumerate(idx_set):
                inst.add_parameter(self.parameters[param_i], value_i)
            inst_list.append(inst)
        return inst_list
