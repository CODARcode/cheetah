"""
Sweep class
"""
import os
import itertools
from codar.cheetah.run import Run
from codar.cheetah.parameters import Instance
from collections import namedtuple
from codar.savanna.node_layout import NodeLayout


class Sweep(object):
    """
    Class representing a set of parameter values to search over as
    a cross product.
    """
    def __init__(self, name, parameters, node_layout=None,
                 rc_dependency=None, num_trials=1):
        self.name = name
        self.parameters = parameters
        self.rc_dependency = rc_dependency
        self.num_trials = num_trials

        self._runs = None
        self._parent_path = None
        self._runs_opts = None
        self.global_run_objs = None
        self._path = None

    def init_2(self, parent_path, g_run_objs, component_subdirs,
               component_inputs, num_trials, launch_mode='default'):
        """
        Function to initialize rest of the Sweep attributes
        """
        RunOpts = namedtuple('RunOpts',
                             'component_subdirs component_inputs launch_mode')

        self._runs_opts=RunOpts(component_subdirs=component_subdirs,
                                component_inputs=component_inputs,
                                launch_mode=launch_mode)

        self._parent_path = parent_path
        self.global_run_objs = g_run_objs
        self.num_trials = num_trials

        # Set self path
        self._path = os.path.join(self._parent_path, self.name)

        # Set the node layout object
        machine = self.global_run_objs.machine
        _node_layout = None
        if self.node_layout is not None:
            _node_layout = self.node_layout.get(machine.name, None)
        self.node_layout = NodeLayout(_node_layout)

        # Ensure launch mode is supported on this machine
        self._validate_launch_mode()

    def validate(self):
        """
        Assert sweep dir doesn't already exist.
        """
        assert self._path is not None, \
            "Internal error. Sweep {} does not have path set".format(self.name)

        # Assert sweep does not exist already
        self._assert_no_exist()

    def create_sweep(self):
        """
        Create the Sweep directory hierarchy consisting of all Runs.
        """
        
        # Create the top-level Sweep dir
        os.makedirs(self._path)

        for i, param_inst in enumerate(self._get_instances()):
            for j in range(self.num_trials):
                run_workdir = os.path.join(self._path,
                                           'run-{}.trial-{}'.format(i,j))
                r = Run(param_inst, self.global_run_objs.codes,
                        self.global_run_objs.appdir, run_workdir,
                        self.global_run_objs.inputs,
                        self.global_run_objs.machine,
                        self.node_layout,
                        self.rc_dependency,
                        self._runs_opts.component_subdirs,
                        self._runs_opts.component_inputs,
                        sosflow_profiling=None,
                        sosflow_analyis=None)
                r.init_2()
                self._runs.append(r)

    def _assert_no_exist(self):
        """
        Assert sweep dir does not exist already.
        """

        # Return if the parent sweep group dir doesn't exist
        if not os.path.isdir(self._parent_path): return

        # Assert sweep dir doesn't exist
        assert os.path.isdir(self._path) is False, \
            "Sweep {} already exists".format(self.name)

    def _get_instances(self):
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

    def _validate_launch_mode(self):
        """
        Ensure that the launch mode (could be MPMD) is supported on the
        target machine
        """

        launch_mode = self._runs_opts.launch_mode
        machine = self.global_run_objs.machine

        if launch_mode is not None:
            if launch_mode.lower() == 'mpmd':
                assert machine.machine_properties.supports_mpmd is True, \
                    "MPMD mode not supported on {}".format(machine.name)
