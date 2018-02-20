"""
Module containing classes for specifying paramter value sets and groupings
of parameters. Used in the Experiment specification in the 'runs' variable.
"""
import itertools


class SweepGroup(object):
    """
    Class representing a grouping of run parameters that can be executed by
    a single scheduler job, because they share the same scheduler parameters
    (currently only # of nodes is at this level).

    How this gets converted into a script depends on the target machine and
    which scheduler (if any) that machine uses.
    """
    def __init__(self, name, nodes, parameter_groups, component_subdirs=False,
                 component_inputs=None, walltime=3600, max_procs=None,
                 per_run_timeout=None, sosflow=False, sosflow_analysis=False):
        self.name = name
        self.nodes = nodes
        self.component_subdirs=component_subdirs
        self.max_procs = max_procs
        self.parameter_groups = parameter_groups
        self.walltime = walltime
        # TODO: allow override in Sweeps?
        self.per_run_timeout = per_run_timeout
        self.sosflow = sosflow
        self.sosflow_analysis = sosflow_analysis
        self.component_inputs = component_inputs


class Sweep(object):
    """
    Class representing a set of parameter values to search over as
    a cross product.
    """
    def __init__(self, parameters, node_layout=None):
        self.parameters = parameters
        self.node_layout = node_layout

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

