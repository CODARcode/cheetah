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
from collections import OrderedDict
import warnings
import pdb

from codar.savanna import machines
from codar.savanna.node_layout import NodeLayout
from codar.cheetah import parameters, config, templates, exc, machine_launchers
from codar.cheetah.launchers import Launcher
from codar.cheetah.helpers import copy_to_dir, copy_to_path
from codar.cheetah.helpers import relative_or_absolute_path, \
    relative_or_absolute_path_list, parse_timedelta_seconds
from codar.cheetah.parameters import SymLink
from codar.cheetah.adios_params import xml_has_transport
from codar.cheetah.parameters import ParamCmdLineArg
from codar.cheetah.exc import CheetahException
from codar.cheetah.run import Run
from codar.cheetah.runcomponent import RunComponent


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
    sweeps = []
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
        # check that subclasses set configuration
        # TODO: better errors
        # TODO: is class variables best way to model this??
        assert self.name is not None
        assert len(self.codes) > 0
        assert len(self.supported_machines) > 0
        assert len(self.sweeps) > 0
        self.machine = self._get_machine(machine_name)
        self.app_dir = os.path.abspath(app_dir)
        self.runs = []

        # allow inputs to be either aboslute paths or relative to
        # app_dir
        self.inputs = relative_or_absolute_path_list(self.app_dir, self.inputs)

        if not isinstance(self.codes, OrderedDict):
            self.codes = OrderedDict(self.codes)

        conflict_names = set(self.codes.keys()) & RESERVED_CODE_NAMES
        if conflict_names:
            raise exc.CheetahException(
                'Code names conflict with reserved names: '
                + ", ".join(str(name) for name in conflict_names))

        if self.run_post_process_script is not None:
            self.run_post_process_script = self._experiment_relative_path(
                                                self.run_post_process_script)

        if self.sosd_path is None:
            self.sosd_path = os.path.join(self.app_dir, 'sosd')
        elif not self.sosd_path.startswith('/'):
            self.sosd_path = os.path.join(self.app_dir, self.sosd_path)

        if self.sos_analysis_path is None:
            self.sos_analysis_path = os.path.join(self.app_dir,
                                                  'sos_wrapper.sh')
        elif not self.sos_analysis_path.startswith('/'):
            self.sos_analysis_path = os.path.join(self.app_dir,
                                                  self.sos_analysis_path)

        o = self.scheduler_options.get(machine_name, {})
        # TODO: deeper validation with knowledge of scheduler
        self.machine_scheduler_options = self.machine.get_scheduler_options(o)

        if self.run_dir_setup_script is not None:
            self.run_dir_setup_script = self._experiment_relative_path(
                                                self.run_dir_setup_script)

        self.machine_app_config_script = None
        if self.app_config_scripts is not None:
            assert isinstance(self.app_config_scripts, dict)
            script = self.app_config_scripts.get(machine_name)
            if script is not None:
                self.machine_app_config_script = \
                    self._experiment_relative_path(script)

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

    def make_experiment_run_dir(self, output_dir, _check_code_paths=False):
        """Produce scripts and directory structure for running the experiment.

        Directory structure will be a subdirectory for each scheduler group,
        and within each scheduler group directory, a subdirectory for each
        run."""

        # set to False for unit tests
        if _check_code_paths:
            self._check_code_paths()

        if self.umask:
            umask_int = int(self.umask, 8)
            if ((umask_int & stat.S_IXUSR) or (umask_int & stat.S_IRUSR)):
                raise exc.CheetahException(
                        'bad umask, user r-x must be allowed')
            os.umask(umask_int)

        # Get the sweep groups for this machine
        if type(self.sweeps) == dict:
            _sweeps_this_mc = self.sweeps.get(self.machine.name, None) or []
            _sweeps_any_mc = self.sweeps.get(sweeps_any_machine, None) or []

            self.sweeps = []
            self.sweeps.extend(_sweeps_this_mc)
            self.sweeps.extend(_sweeps_any_mc)

            assert len(self.sweeps) > 0, "No sweep groups found."

        # Create the top level campaign directory
        _output_dir = os.path.abspath(output_dir)
        os.makedirs(_output_dir, exist_ok=True)

        # Write campaign id file at the top-level campaign directory
        id_fpath = os.path.join(_output_dir, self._id_file)
        Path(id_fpath).touch()

        # Create a directory for the user and set it as the campaign location
        output_dir = os.path.join(_output_dir, getpass.getuser())
        run_all_script = os.path.join(config.CHEETAH_PATH_SCHEDULER,
                                      self.machine.scheduler_name,
                                      'run-all.sh')
        os.makedirs(output_dir, exist_ok=True)

        # Check if campaign dir already has groups with the same name
        self._assert_unique_group_names(output_dir)

        # Create run script and campaign environment info file
        copy_to_dir(run_all_script, output_dir)

        campaign_env = templates.CAMPAIGN_ENV_TEMPLATE.format(
            experiment_dir=output_dir,
            machine_config=config.machine_submit_env_path(self.machine.name),
            app_config=self.machine_app_config_script or "",
            workflow_script_path=config.WORKFLOW_SCRIPT,
            workflow_runner=self.machine.runner_name,
            workflow_debug_level="DEBUG",
            umask=(self.umask or ""),
            codar_python=self.python_path,
        )
        campaign_env_path = os.path.join(output_dir, 'campaign-env.sh')
        with open(campaign_env_path, 'w') as f:
            f.write(campaign_env)

        # Traverse through sweep groups
        for group_i, group in enumerate(self.sweeps):
            # Validate component inputs.
            #   1. Ensure all keys are valid code names
            code_names = list(self.codes.keys())
            if group.component_inputs is not None:
                c_input_keys = list(group.component_inputs.keys())
                for key in c_input_keys:
                    assert key in code_names, \
                        "Error in component_inputs for {}. '{}' not a valid " \
                        "code name".format(group.name, key)

            # each scheduler group gets it's own subdir
            # TODO: support alternate template for dirs?
            group_name = group.name
            group_output_dir = os.path.join(output_dir, group_name)
            launcher = Launcher(self.machine.name, self.machine.scheduler_name,
                                self.machine.runner_name, group_output_dir,
                                len(self.codes))
            group_runs = []
            for repeat_index in range(0, group.run_repetitions+1):
                group_run_offset = 0
                for sweep in group.parameter_groups:
                    # node layout is map of machine names to layout for each
                    # machine. If unspecified, or certain machine is
                    # unspecified, use default.
                    if sweep.node_layout is None:
                        node_layout = None
                    else:
                        node_layout = sweep.node_layout.get(self.machine.name)

                    # Summit requires a node layout
                    if self.machine.name.lower() == "summit":
                        assert node_layout is not None, \
                            "Must provide a node layout for a Sweep on Summit"

                    if node_layout is None:
                        node_layout = NodeLayout.default_no_share_layout(
                                            self.machine.processes_per_node,
                                            self.codes.keys())
                    else:
                        node_layout = NodeLayout(node_layout)

                    # TODO: validate node layout against machine model

                    sweep_runs = [Run(inst, self.codes, self.app_dir,
                                      os.path.join(
                                          group_output_dir,
                                          'run-{}.iteration-{}'.format(
                                              group_run_offset + i,
                                              repeat_index)),
                                      self.inputs,
                                      self.machine,
                                      node_layout,
                                      sweep.rc_dependency,
                                      group.component_subdirs,
                                      group.sosflow_profiling,
                                      group.sosflow_analysis,
                                      group.component_inputs)
                                  for i, inst in enumerate(
                            sweep.get_instances())]

                    # we dont support mpmd mode with dependencies
                    try:
                        if group.launch_mode.lower() == 'mpmd':
                            assert sweep.rc_dependency is None, \
                                "Dependencies in MPMD mode not supported"
                    except AttributeError:
                        pass

                    # we dont support mpmd on deepthought2
                    try:
                        if self.machine.machine_name.lower() == 'deepthought2':
                            assert group.launch_mode.lower() not in 'mpmd',\
                                "mpmd mode not implemented for deepthought2"
                    except AttributeError:
                        pass

                    group_runs.extend(sweep_runs)
                    group_run_offset += len(sweep_runs)
            self.runs.extend(group_runs)

            if group.max_procs is None:
                max_procs = max([r.get_total_nprocs() for r in group_runs])
            else:
                procs_per_run = max([r.get_total_nprocs() for r in group_runs])
                if group.max_procs < procs_per_run:
                    # TODO: improve error message, specifying which
                    # group and by how much it's off etc
                    raise exc.CheetahException("max_procs for group is too low")
                max_procs = group.max_procs

            if group.per_run_timeout:
                per_run_seconds = parse_timedelta_seconds(group.per_run_timeout)
                walltime_guess = (per_run_seconds * len(group_runs)) + 60
                walltime_group = parse_timedelta_seconds(group.walltime)
                if walltime_group < walltime_guess:
                    warnings.warn('group "%s" walltime %d is less than '
                                  '(per_run_timeout * nruns) + 60 = %d, '
                                  'it is recommended to set it higher to '
                                  'avoid problems with the workflow '
                                  'engine being killed before it can write '
                                  'all status information'
                                % (group.name, walltime_group, walltime_guess))

            # TODO: refactor so we can just pass the campaign and group
            # objects, i.e. add methods so launcher can get all info it needs
            # and simplify this loop.
            group.nodes = launcher.create_group_directory(
                self.name, self.app_dir, group_name,
                group_runs,
                max_procs,
                nodes=group.nodes,
                launch_mode=group.launch_mode,
                component_subdirs=group.component_subdirs,
                walltime=group.walltime,
                timeout=group.per_run_timeout,
                node_exclusive=self.machine.node_exclusive,
                tau_profiling=group.tau_profiling,
                tau_tracing=group.tau_tracing,
                machine=self.machine,
                sosd_path=self.sosd_path,
                sos_analysis_path=self.sos_analysis_path,
                kill_on_partial_failure=self.kill_on_partial_failure,
                run_post_process_script=self.run_post_process_script,
                run_post_process_stop_on_failure=
                    self.run_post_process_stop_group_on_failure,
                scheduler_options=self.machine_scheduler_options,
                run_dir_setup_script=self.run_dir_setup_script)

        # TODO: track directories and ids and add to this file
        all_params_json_path = os.path.join(output_dir, "params.json")
        with open(all_params_json_path, "w") as f:
            json.dump([run.get_app_param_dict()
                       for run in self.runs], f, indent=2)

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

    def _assert_unique_group_names(self, campaign_dir):
        """Assert new groups being added to the campaign do not have the
        same name as existing groups.
        """
        requested_group_names = []
        for group_i, group in enumerate(self.sweeps):
            if not isinstance(group, parameters.SweepGroup):
                raise ValueError("'sweeps' must be a list of SweepGroup "
                                 "objects. Some objects are of type "
                                 "{}".format(type(group)))
            requested_group_names.append(group.name)

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

