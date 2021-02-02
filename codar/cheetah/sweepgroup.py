"""
SweepGroup class
"""
import os

from codar.cheetah.exc import CheetahException
from codar.cheetah import sweep
from codar.cheetah import config

class SweepGroup(object):
    """
    Class representing a grouping of run parameters that can be executed by
    a single scheduler job, because they share the same scheduler parameters.

    Note that nodes is no longer required - if not specified, it is calculated
    based on the biggest run within the group.

    How this gets converted into a script depends on the target machine and
    which scheduler (if any) that machine uses.
    """
    def __init__(self, name, sweeps,
                 component_subdirs=False, component_inputs=None,
                 walltime=3600, max_procs=None, per_run_timeout=None,
                 sosflow_profiling=False, sosflow_analysis=False,
                 nodes=None, launch_mode=None, tau_profiling=False,
                 tau_tracing=False, num_trials=1,
                 max_concurrent=-1):
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
        self._path = None
        self._id_file = ".sweepgroup"

    def set_parent_campaign(self, parent_campaign):
        self._parent_campaign = parent_campaign
        self._path = os.path.join(self._parent_campaign, self.name)

    def set_machine(self, machine):
        self._machine = machine

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

        # Validate sweeps
        for s in self.sweeps:
            s.set_parent_sg(self._path)
            s.validate()

    def create_sweep_group_dir(self):
        """
        Create the Sweep Group directory
        """
        
        # Create top-level sweep group dir
        os.makedirs(self._path)

        # Copy generic scheduler scripts
        self._copy_scheduler_scripts()

    def _copy_scheduler_scripts(self):
        script_dir = os.path.join(config.CHEETAH_PATH_SCHEDULER,
                                  self._machine.scheduler_name, "group")
        assert os.path.isdir(script_dir), \
            "Internal error. Could not find {}".format(script_dir)
        

    def _assert_no_exist(self):
        """
        Ensure sweep group doesn't already exist
        """

        # Return if the campaign dir doesn't exist
        if not os.path.isdir(self._parent_campaign): return

        # Assert sweep group dir doesn't exist
        assert os.path.isdir(self._path) is False, \
            "Sweep group {} already exists".format(self.name)
