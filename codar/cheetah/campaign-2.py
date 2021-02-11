"""
Object oriented model to represent jobs to run on different Supercomputers or
workstations using different schedulers and runners (for running applications
on compute nodes from front end nodes), and allow pass through of scheduler
or runner specific options.

Subclasses representing specific types of schedulers, runners, and
supercomputers (machines) are specified in other modules with the corresponding
name.
"""
import os
import sys
import stat
import json
import math
import shlex
import inspect
import getpass
from pathlib import Path
from collections import OrderedDict, namedtuple
import warnings
import pdb

from codar.savanna import machines
from codar.savanna.node_layout import NodeLayout
from codar.cheetah import parameters, config, templates, exc, machine_launchers
from codar.cheetah.launchers import Launcher
from codar.cheetah.helpers import copy_to_dir, copy_to_path, get_first_list_dup
from codar.cheetah.helpers import relative_or_absolute_path, \
    relative_or_absolute_path_list, parse_timedelta_seconds
from codar.cheetah.parameters import SymLink
from codar.cheetah.adios_params import xml_has_transport
from codar.cheetah.parameters import ParamCmdLineArg
from codar.cheetah.exc import CheetahException
from codar.cheetah.run import Run
from codar.cheetah.runcomponent import RunComponent
from codar.cheetah import sweepgroup as sg


RESERVED_CODE_NAMES = {'post-process'}
sweeps_any_machine = 'MACHINE_ANY'


class Campaign(object):
    """An experiment class specifies an application, a set of parameter to
    sweep over, and a set of supported target machine. A specific instance
    binds the experiment to a specific machine within the set of supported
    machines, and supports generating a set of scripts to run the experiment
    on that machine."""

    # subclasses must populate these
    name = None
    codes = []
    supported_machines = []
    sweep_groups = []
    inputs = [] # copied to top level run directory
    umask = None

    # If set and there are multiple codes making up the application,
    # kill all remaining codes if one code fails.
    kill_on_partial_failure = False

    # Optional. If set, passed single argument which is the absolute
    # path to a JSON file containing the FOB definition for the run.
    # The path can be absolute (starts with /), or relative to the
    # directory containing the spec file (if does not start with /).
    # If the script has nonzero exit status, then the entire sweep group
    # can optionally be stopped. This can be used to detect errors early.
    run_post_process_script = None
    run_post_process_stop_group_on_failure = False

    # Optional. Designed to set up application specific environment
    # variables and load environment modules. Must be a dictionary with
    # machine name keys and values pointing at bash scripts. The
    # appropriate machine script will be sourced before running the workflow
    # script, and all the codes in the application will inherit that
    # environment. Can be an absolute path, or a path relative to the
    # directory containg the campaign definition.
    app_config_scripts = None

    # Script to be run for each run directory. The working dir will be
    # set to the run dir and no arguments will be passed. It will be
    # run as the last step, so all files created by cheetah, like the
    # FOB file, will be present. If the value is non-None and does not
    # begin with '/', the path will be assumed to be relative to the
    # directory containing the campaign spec.
    # @TODO: This must be per sweep group
    run_dir_setup_script = None

    # Schedular options. Not used when using machine 'local', required
    # when using super computers.
    scheduler_options = {}

    # None means use 'sosd' in the app dir
    # TODO: make this part of machine config? Or does it make sense to
    # have per-app binaries for sos?
    sosd_path = None
    sos_analysis_path = None
    sosd_num_aggregators = 1

    # Optional. If set, passed single argument which is the absolute
    # path to a JSON file containing all runs. Must be relative to the
    # app directory, just like codes values. It will be run from the
    # top level experiment directory.
    # TODO: this is broken. It should really be a group post process
    # script now, and it could be passed as an arg to the workflow
    # script.
    post_process_script = None

    # By default the workflow script running on compute nodes in the
    # campaign will use the same executable (possibly in a virtualenv)
    # as the cheetah.py command used to create the campaign. If needed,
    # specs can override this.
    python_path = sys.executable

    # A file that identifies a directory as a multi-user campaign
    _id_file = ".campaign"

    def __init__(self, machine_name, app_dir):
        # Check that subclasses set configuration
        # TODO: better errors
        # TODO: is class variables best way to model this??
        assert self.name is not None
        assert len(self.codes) > 0
        assert len(self.supported_machines) > 0
        assert len(self.sweep_groups) > 0
        self.machine = self._get_machine(machine_name)
        self.app_dir = os.path.abspath(app_dir)
        self.runs = []
        self.root_dir = None
        self._id_file = ".campaign"

        # Allow inputs to be either absolute paths or relative to app_dir
        self.inputs = relative_or_absolute_path_list(self.app_dir, self.inputs)

        if not isinstance(self.codes, OrderedDict):
            self.codes = OrderedDict(self.codes)

        # Check for conflicting names
        self._assert_no_name_conflicts()

        # Set path of a Run post process script
        if self.run_post_process_script is not None:
            self.run_post_process_script = \
                self._experiment_relative_path(self.run_post_process_script)

        # Set SOS options: path to daemon and analysis code
        self._set_sos_paths()

        # Set scheduler options
        o = self.scheduler_options.get(machine_name, {})
        # TODO: deeper validation with knowledge of scheduler
        self.machine_scheduler_options = self.machine.get_scheduler_options(o)

        # Set path of the run_dir_setup_script
        if self.run_dir_setup_script is not None:
            self.run_dir_setup_script = \
                self._experiment_relative_path(self.run_dir_setup_script)

        # Set path to the machine_app_config_script
        self._set_machine_app_config_script(machine_name)

        # Set umask so that everyone may be able to view everyone else's
        # campaign files
        self._set_umask()

        # Create a list of all Sweep Groups for this machine
        self._get_all_mc_sg()

        # Basic type checking and verification after getting SGs
        self._assert_members_type()

        # Validate component inputs
        self._validate_component_inputs()

        # A Global run info object that can be passed to lower layers - SG,
        # Sweep, Run, RunComponent.
        self.GlobalRunInfo = namedtuple('GlobalRunInfo',
                                        'codes appdir inputs machinename')

    def add_to_campaign(self, sg):
        """
        Add Sweep Groups to an existing campaign.
        """
        sg.create_sweep_group_root(sg, self.root_dir)

    def create_campaign_dirs(self, output_dir, _check_code_paths=False):
        """Produce scripts and directory structure for running the experiment.

        Directory structure will be a subdirectory for each scheduler group,
        and within each scheduler group directory, a subdirectory for each
        run."""

        # Create a list of SG objects of this campaign
        # self._init_sweep_groups()

        self.root_dir = os.path.abspath(output_dir)
        g_run_objs = self._gather_global_run_objs()

        # Ensure sweep groups look ok before we creating the campaign dirs
        for sg in self.sweep_groups:
            sg.init_2(parent_path=self.root_dir, machine=self.machine,
                      global_run_objs=g_run_objs)
            sg.set_parent_path(self.root_dir)
            sg.set_machine(self.machine)
            sg.set_global_run_objs(g_run_objs)
            sg.validate()

        # Create the campaign root dir
        self._create_campaign_root()

        # Create the individual sweep groups
        for sg in self.sweep_groups:
            sg.create_sweep_group(sg, self.root_dir)

    def _gather_global_run_objs(self):
        """
        Create a named tuple of run objects and information that can be
        passed on to the lower layers - SweepGroup, Sweep, Run, RunComponent
        """

        g_run_info = self.GlobalRunInfo(codes=self.codes,
                                        appdir=self.app_dir,
                                        inputs=self.inputs,
                                        machinename=self.machine)
        return g_run_info

    def _get_machine(self, machine_name):
        machine = None
        for m in self.supported_machines:
            if m == machine_name:
                machine = machines.get_by_name(m)
        if machine is None:
            raise exc.CheetahException(
                "machine '%s' not supported by experiment '%s'"
                % (machine_name, self.name))
        return machine

    def _check_code_paths(self):
        if not os.path.isdir(self.app_dir):
            raise exc.CheetahException(
                'specified app directory "%s" does not exist' % self.app_dir)
        for code_name, code in self.codes.items():
            exe_path = code['exe']
            if not os.path.isfile(exe_path):
                raise exc.CheetahException(
                    'code "%s" exe at "%s" is not a file'
                    % (code_name, exe_path))
            if not os.access(exe_path, os.X_OK):
                raise exc.CheetahException(
                    'code "%s" exe at "%s" is not executable by current user'
                    % (code_name, exe_path))

    def _assert_unique_sg_names(self, campaign_dir):
        """Assert new groups being added to the campaign do not have the
        same name as existing groups.
        """

        sg_names = [sg.name for sg in self.sweep_groups]
        dupl = get_first_list_dup(sg_names)
        assert dupl is None, \
            "Found duplicate Sweep Group name {}".format(dupl.name)

    def _assert_sg_dont_exist(self):
        """
        Assert Sweep Groups don't exist already
        """
        existing_groups = next(os.walk(campaign_dir))[1]
        common_groups = set(requested_group_names) & set(existing_groups)
        if common_groups:
            raise FileExistsError("One or more SweepGroups already exist: "
                                  + ", ".join(common_groups))

    def _experiment_relative_path(self, p):
        if p.startswith("/"):
            return p
        experiment_spec_path = inspect.getsourcefile(self.__class__)
        experiment_dir = os.path.dirname(experiment_spec_path)
        return os.path.join(experiment_dir, p)

    def _assert_no_name_conflicts(self):
        """
        Assert that no code names conflict with reserved names
        """
        conflict_names = set(self.codes.keys()) & RESERVED_CODE_NAMES
        if conflict_names:
            raise exc.CheetahException(
                'Code names conflict with reserved names: '
                + ", ".join(str(name) for name in conflict_names))

    def _set_sos_paths(self):
        """
        Set paths to the SOSflow daemon and analysis code.
        """

        # Path to the SOS daemon
        if self.sosd_path is None:
            self.sosd_path = os.path.join(self.app_dir, 'sosd')
        elif not self.sosd_path.startswith('/'):
            self.sosd_path = os.path.join(self.app_dir, self.sosd_path)

        # Path to the SOS analysis code
        if self.sos_analysis_path is None:
            self.sos_analysis_path = os.path.join(self.app_dir,
                                                  'sos_wrapper.sh')
        elif not self.sos_analysis_path.startswith('/'):
            self.sos_analysis_path = os.path.join(self.app_dir,
                                                  self.sos_analysis_path)

    def _set_machine_app_config_script(self, machine_name):
        """
        Get the path to the app_config_script.
        """
        self.machine_app_config_script = None
        if self.app_config_scripts is not None:
            assert isinstance(self.app_config_scripts, dict), \
                "app_config_scripts must be a dictionary"
            script = self.app_config_scripts.get(machine_name)
            if script is not None:
                self.machine_app_config_script = \
                    self._experiment_relative_path(script)

    def _set_umask(self):
        """
        This allows users to set the umask so that their campaign data is
        readable by other users.
        """
        if self.umask:
            umask_int = int(self.umask, 8)
            if ((umask_int & stat.S_IXUSR) or (umask_int & stat.S_IRUSR)):
                raise exc.CheetahException(
                        'bad umask, user r-x must be allowed')
            os.umask(umask_int)

    def _get_all_mc_sg(self):
        """
        Create a list of all the SweepGroups for this machine.
        For backwards compatibility, self.sweep_groups may be a list of
        Sweep Groups for the current machine, or a dictionary of SGs per
        machine.
        """
        if type(self.sweep_groups) == dict:
            _sg_this_mc = self.sweep_groups.get(self.machine.name, None) or []
            _sg_any_mc = self.sweep_groups.get(sweeps_any_machine, None) or []

            self.sweep_groups = []
            self.sweep_groups.extend(_sg_this_mc)
            self.sweep_groups.extend(_sg_any_mc)

            assert len(self.sweep_groups) > 0, \
                "No sweep groups found for this system"

    def _validate_component_inputs(self):
        """
        Validate component inputs
        """
        for group_i, group in enumerate(self.sweep_groups):
            code_names = list(self.codes.keys())
            if group.component_inputs is not None:
                c_input_keys = list(group.component_inputs.keys())
                for key in c_input_keys:
                    assert key in code_names, \
                        "Error in component_inputs for {}. '{}' not a valid " \
                        "code name".format(group.name, key)

    def _assert_members_type(self):
        """
        Assert the type of the object members
        """

        # Assert sweep_groups is list
        assert isinstance(self.sweep_groups, list), \
            "sweep_groups must a list of SweepGroup objects"

        # Assert elements in sweep_groups are SweepGroup objects
        for sg in self.sweep_groups:
            assert isinstance(sg, sg.SweepGroup), \
                "Incorrect object type. Found {} instead of SweepGroup in " \
                "sweep_groups".format(type(sg))

    def _create_campaign_root(self):
        """
        Create the top level campaign root dir along with the user-level dir.
        Create top-level metadata files.
        """
        
        # Create top-level root dir
        os.makedirs(self.root_dir, exist_ok=True)
        
        # Write .campaign id file
        Path(os.path.join(self.root_dir, self._id_file)).touch()
        
        # Create user directory under root
        user_dir = os.path.join(self.root_dir, getpass.getuser())
        os.makedirs(user_dir, exist_ok=True)
        
        # Write the top-level run-all.sh script to the user dir
        run_all_sh = os.path.join(config.CHEETAH_PATH_SCHEDULER,
                                  self.machine.scheduler_name, 
                                  "run-all.sh")
        copy_to_dir(run_all_sh, user_dir)

        # Write campaign-env.sh
        camp_env = templates.CAMPAIGN_ENV_TEMPLATE.format(
            experiment_dir = self.root_dir,
            machine_config = config.machine_submit_env_path(self.machine.name),
            app_config = self.machine_app_config_script or "",
            workflow_script_path = config.WORKFLOW_SCRIPT,
            workflow_runner = self.machine.runner_name,
            workflow_debug_level = "DEBUG",
            umask = (self.umask or ""),
            codar_python = self.python_path,
        )
        camp_env_fpath = os.path.join(self.root_dir, 'campaign-env.sh')
        with open(camp_env_fpath, 'w') as f:
            f.write(camp_env)
