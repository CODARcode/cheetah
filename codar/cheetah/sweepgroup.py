"""
SweepGroup class
"""
import os

from codar.cheetah.exc import CheetahException
from codar.cheetah import sweep
from codar.cheetah import config
from codar.cheetah import helpers as ch_util
from codar.cheetah.helpers import get_first_list_dup

class SweepGroup(object):
    """
    Class representing a grouping of run parameters that can be executed by
    a single scheduler job, because they share the same scheduler parameters.

    Note that nodes is no longer required - if not specified, it is calculated
    based on the biggest run within the group.

    How this gets converted into a script depends on the target machine and
    which scheduler (if any) that machine uses.
    """
    def __init__(self,
                 name,
                 sweeps,
                 component_subdirs=False,
                 component_inputs=None,
                 walltime=3600,
                 max_procs=None,
                 per_run_timeout=None,
                 sosflow_profiling=False,
                 sosflow_analysis=False,
                 nodes=None,
                 launch_mode=None,
                 tau_profiling=False,
                 tau_tracing=False,
                 num_trials=1,
                 max_concurrent=-1):
        """

        """
        self.name = name
        self.nodes = nodes
        self.component_subdirs = component_subdirs
        self.max_procs = max_procs
        self.sweeps = sweeps
        self.walltime = walltime
        # TODO: allow override in Sweeps?
        self.per_run_timeout = per_run_timeout
        self.sosflow_profiling = sosflow_profiling
        self.sosflow_analysis = sosflow_analysis
        self.component_inputs = component_inputs

        self.launch_mode = launch_mode
        self.tau_profiling = tau_profiling
        self.tau_tracing = tau_tracing
        self.num_trials = num_trials

        # num sweeps that can be run concurrently
        self.max_concurrent = max_concurrent

        # Child SweepGroups that depend on this to finish
        self.children = None

        if self.launch_mode is not None:
            self.launch_mode = self.launch_mode.lower()

        self._parent_campaign = None
        self._machine = None
        self._global_run_objs = None
        self._path = None
        self._id_file = ".sweepgroup"
        self.min_nodes = None

    def init_2(self, parent_path, machine, g_run_objs):
        """
        Initialize rest of the attributes of the SweepGroup
        """
        self._parent_path = parent_path
        self._machine = machine
        self._global_run_objs = g_run_objs

    def validate(self):
        """
        Ensure sg looks ok before creating dirs
        """

        # Assert launch mode is correct
        if self.launch_mode is not None:
            assert self.launch_mode in ('default', 'mpmd'), \
                "launch_mode for SweepGroup {} must be one of default/mpmd, " \
                "but found {}".format(self.name, self.launch_mode)

        # Assert campaign root is set
        assert self._parent_campaign is not None, \
            "Internal error. parent_campaign for SweepGroup is None"

        # Assert sweep group doesn't exist already
        self._assert_no_exist()

        # Assert Sweep names are unique
        self._assert_unique_sweep_names()

    def create_sweep_group(self):
        """
        Create the Sweep Group directory
        """
        
        # Create top-level sweep group dir
        os.makedirs(self._path)

        # Init remaining variables/attributes of the sweep objs
        self._init_sweeps()

        # Copy generic scheduler scripts
        self._copy_scheduler_scripts()

        # for s in self.sweeps:
        #   sw.create_sweep(s)

        # Calculate the minimum no. of nodes required
        self.min_nodes = max([s.min_nodes for s in self.sweeps])
        if self.nodes is not None:
            assert self.nodes >= self.min_nodes, \
                "Nodes for group is too low, need at least {}, " \
                "got {}".format(self.min_nodes, self.nodes)

        # Create fob manifest


    def _init_sweeps(self):
        """
        Further initialize sweep objects and validate them
        """
        for s in self.sweeps:
            s.init_2(parent_path = self._path,
                     global_run_objs = self._global_run_objs,
                     component_subdirs = self.component_subdirs,
                     component_inputs = self.component_inputs,
                     num_trials = self.num_trials,
                     launch_mode = self.launch_mode)

            s.validate()

    def _copy_scheduler_scripts(self):
        script_dir = os.path.join(config.CHEETAH_PATH_SCHEDULER,
                                  self._machine.scheduler_name, "group")
        assert os.path.isdir(script_dir), \
            "Internal error. Could not find {}".format(script_dir)

        ch_util.copytree_to_dir(script_dir, self._path)

    def _assert_no_exist(self):
        """
        Ensure sweep group doesn't already exist
        """

        # Return if the campaign dir doesn't exist
        if not os.path.isdir(self._parent_campaign): return

        # Assert sweep group dir doesn't exist
        assert os.path.isdir(self._path) is False, \
            "Sweep group {} already exists".format(self.name)

    def _assert_unique_sweep_names(self):
        """
        Assert names of Sweep names in this SG are unique
        """

        sweep_names = [s.name for s in self.sweeps]
        dup_item = get_first_list_dup(sweep_names)
        assert dup_item is None, \
            "Found duplicate Sweep name {} in SweepGroup {}".format(
                dup_item, self.name)
