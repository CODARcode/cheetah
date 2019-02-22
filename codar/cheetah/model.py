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

from codar.cheetah import machines, parameters, config, templates, exc
from codar.cheetah.helpers import copy_to_dir, copy_to_path
from codar.cheetah.helpers import relative_or_absolute_path, \
    relative_or_absolute_path_list, parse_timedelta_seconds
from codar.cheetah.parameters import SymLink
from codar.cheetah.adios_params import xml_has_transport
from codar.cheetah.parameters import ParamCmdLineArg
from codar.cheetah.exc import CheetahException


RESERVED_CODE_NAMES = set(['post-process'])


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

    # None means use default
    tau_config = None

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

        # Resolve relative code exe pahts. Checking for existence is not
        # done until make_experiment_run_dir is called to simplify unit
        # testing.
        for code_name, code in self.codes.items():
            exe_path = code['exe']
            if not exe_path.startswith('/'):
                exe_path = os.path.join(self.app_dir, exe_path)
                code['exe'] = exe_path

        if self.tau_config is None:
            self.tau_config = config.etc_path('tau.conf')
        elif not self.tau_config.startswith('/'):
            self.tau_config = os.path.join(self.app_dir, self.tau_config)

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

    def make_experiment_run_dir(self, output_dir, _check_code_paths=True, runner_extra=""):
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
            runner_extra=runner_extra,
            workflow_debug_level="DEBUG",
            umask=(self.umask or ""),
            codar_python=self.python_path,
        )
        campaign_env_path = os.path.join(output_dir, 'campaign-env.sh')
        with open(campaign_env_path, 'w') as f:
            f.write(campaign_env)

        # Traverse through sweep groups
        for group_i, group in enumerate(self.sweeps):
            # each scheduler group gets it's own subdir
            # TODO: support alternate template for dirs?
            group_name = group.name
            group_output_dir = os.path.join(output_dir, group_name)
            launcher = self.machine.get_launcher_instance(group_output_dir,
                                                          len(self.codes))
            group_runs = []
            group_run_offset = 0
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
                    if node_layout is None:
                        node_layout = NodeLayout.default_no_share_layout(
                                            self.machine.processes_per_node,
                                            self.codes.keys())
                    else:
                        node_layout = NodeLayout(node_layout)

                    # TODO: validate node layout against machine model

                    # Summit override. Don't support MPMD yet.
                    if self.machine.name.lower() == "summit":
                        if group.launch_mode.lower() == 'mpmd':
                            print("MPMD not supported on Summit yet."
                                  "Changing to default launch mode.")
                            group.launch_mode = 'default'

                    sweep_runs = [Run(inst, self.codes, self.app_dir,
                                      os.path.join(
                                          group_output_dir,
                                          'run-{}.{}'.format(
                                              group_run_offset + i,
                                              repeat_index)),
                                      self.inputs,
                                      node_layout,
                                      group.rc_dependency,
                                      group.component_subdirs,
                                      group.sosflow_profiling,
                                      group.sosflow_analysis,
                                      group.component_inputs)
                                  for i, inst in enumerate(
                            sweep.get_instances())]
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
                rc_dependency=group.rc_dependency,
                component_subdirs=group.component_subdirs,
                walltime=group.walltime,
                timeout=group.per_run_timeout,
                node_exclusive=self.machine.node_exclusive,
                tau_config=self.tau_config,
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
                raise ValueError("top level run groups must be SweepGroup")
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


class Run(object):
    """
    Class representing how to actually run an instance on a given environment,
    including how to generate arg arrays for executing each code required for
    the application.

    TODO: create a model shared between workflow and cheetah, i.e. codar.model
    """
    def __init__(self, instance, codes, codes_path, run_path, inputs,
                 node_layout, rc_dependency, component_subdirs,
                 sosflow_profiling, sosflow_analyis, component_inputs=None):
        self.instance = instance
        self.codes = codes
        self.codes_path = codes_path
        self.run_path = run_path
        self.run_id = os.path.basename(run_path)
        self.inputs = inputs
        # Note: the layout will be modified if sosflow is set, so it's
        # important to use a copy.
        self.node_layout = node_layout.copy()
        self.component_subdirs = component_subdirs
        self.sosflow_profiling = sosflow_profiling
        self.sosflow_analysis = sosflow_analyis
        self.component_inputs = component_inputs
        self.total_nodes = 0
        self.run_components = self._get_run_components()

        # Get the RCs that this rc depends on
        # This must be done before the total no. of nodes are calculated
        # below
        self._populate_rc_dependency(rc_dependency)

        # Set the total nodes after the run components are initialized above
        self._set_total_nodes()

        # Filename in the run dir that will store the size of the run dir
        # prior to submitting the campaign
        self._pre_submit_dir_size_fname = \
            ".codar.cheetah.pre_submit_dir_size.out"

    def _get_run_components(self):
        comps = []
        codes_argv = self._get_codes_argv_ordered()
        for (target, argv) in codes_argv.items():
            exe_path = self.codes[target]['exe']
            sleep_after = self.codes[target].get('sleep_after', 0)

            # Set separate subdirs for individual components if requested
            if self.component_subdirs:
                working_dir = os.path.join(self.run_path, target)
            else:
                working_dir = self.run_path

            component_inputs = None
            if self.component_inputs:
                component_inputs = self.component_inputs.get(target)
            if component_inputs:
                # Get the full path of inputs
                # Separate the strings from symlinks to preserve their type
                str_inputs = [input for input in component_inputs if type(
                    input) == str]
                str_inputs = relative_or_absolute_path_list(self.codes_path,
                                                            str_inputs)

                symlinks = [input for input in component_inputs if type(
                    input) == SymLink]
                symlinks = relative_or_absolute_path_list(self.codes_path,
                                                          symlinks)
                symlinks = [SymLink(input) for input in symlinks]
                component_inputs = str_inputs + symlinks

            linked_with_sosflow = self.codes[target].get(
                'linked_with_sosflow', False)

            adios_xml_file = self.codes[target].get('adios_xml_file', None)
            if adios_xml_file:
                adios_xml_file = relative_or_absolute_path(
                    self.codes_path, adios_xml_file)

            sched_args = self.instance.get_sched_opts(target)

            comp = RunComponent(name=target, exe=exe_path, args=argv,
                                sched_args=sched_args,
                                nprocs=self.instance.get_nprocs(target),
                                sleep_after=sleep_after,
                                working_dir=working_dir,
                                component_inputs=component_inputs,
                                linked_with_sosflow=linked_with_sosflow,
                                adios_xml_file=adios_xml_file,
                                hostfile=self.instance.get_hostfile(target))
            comps.append(comp)
        return comps

    def _populate_rc_dependency(self, rc_dependency):
        """
        Populate the after_rc_done field for every RC with object references
        depending on the rc_dependency group parameter
        """
        if rc_dependency is not None:
            for k,v in rc_dependency.items():
                assert type(k) is str, "rc_dependency dictionary key must " \
                                        "be code name"
                assert v is not None, "Dict value cannot be None"
                assert type(v) is str, "rc_dependency dictionary value must " \
                                       "be a string"

                k_rc = self._get_rc_by_name(k)
                k_rc.after_rc_done = v

                # k_rc = self._get_rc_by_name(k)
                # assert k_rc is not None, "RC {0} not found".format(k)
                # v_rc = self._get_rc_by_name(v)
                # assert v_rc is not None, "RC {0} not found".format(v)
                # k_rc.after_rc_done = v_rc

    def get_fob_data_list(self):
        return [comp.as_fob_data() for comp in self.run_components]

    def _get_codes_argv_ordered(self):
        """Wrapper around instance.get_codes_argv which uses correct order
        from self.codes OrderedDict."""
        codes_argv = self.instance.get_codes_argv()
        undefined_codes = set(codes_argv.keys()) - set(self.codes.keys())
        if undefined_codes:
            raise exc.CampaignParseError(
                'Parameter references undefined codes(s): %s'
                % ','.join(undefined_codes))
        # Note that a given Run may not use all codes, e.g. for base
        # case app runs that don't use adios stage_write or dataspaces.
        return OrderedDict((k, codes_argv[k]) for k in self.codes.keys()
                           if k in codes_argv)

    def get_total_nprocs(self):
        return sum(rc.nprocs for rc in self.run_components)

    def _get_rc_by_name(self, name):
        for rc in self.run_components:
            if rc.name == name:
                return rc

        raise CheetahException("Did not find run component with name {0}"
                               .format(name))

    def _set_total_nodes(self):
        """Get the total number of nodes that will be required by the Run.
        NOTE: if run after insert_sosflow, then this WILL include the sosflow
        nodes, otherwise it will not. Node-sharing not supported yet."""

        num_nodes_rc = {}
        for rc in self.run_components:
            code_node = self.node_layout.get_node_containing_code(rc.name)
            code_procs_per_node = code_node[rc.name]
            num_nodes_rc[rc.name] = int(math.ceil(rc.nprocs /
                                                  code_procs_per_node))

        # RC dependency handling
        # @TODO need better algorithm to do this
        top_rc = [[rc] for rc in self.run_components if rc.after_rc_done is
                  None]
        assert len(top_rc) > 0, "Circular task dependency found"

        def add_to_top_rc(tmprc):
            if type(tmprc) is str:
                tmprc = self._get_rc_by_name(tmprc)
            top_rc_serialized = [r for l in top_rc for r in l]
            after_rc_done_obj = self._get_rc_by_name(tmprc.after_rc_done)
            if after_rc_done_obj not in top_rc_serialized:
                add_to_top_rc(after_rc_done_obj.after_rc_done)
            for l in top_rc:
                if after_rc_done_obj in l:
                    if tmprc not in l:
                        l.append(tmprc)
                        break

        for rc in self.run_components:
            if rc.after_rc_done is not None:
                add_to_top_rc(rc)

        total_nodes = 0
        for rc_list in top_rc:
            max_nodes = max(num_nodes_rc[rc.name] for rc in rc_list)
            total_nodes += max_nodes

        self.total_nodes = total_nodes

    def _get_total_sosflow_component_nodes(self):
        """Get the total number of nodes that will be required by the components
        that will use sosflow.
        This will be less than or equal to the total number of nodes in the Run.
        Node-sharing not supported yet.
        This should not include the nodes required by sosflow."""
        num_nodes = 0
        for rc in self.run_components:
            if rc.linked_with_sosflow:
                code_node = self.node_layout.get_node_containing_code(rc.name)
                code_procs_per_node = code_node[rc.name]
                num_nodes += int(math.ceil(rc.nprocs / code_procs_per_node))

        return num_nodes

    def get_app_param_dict(self):
        """Return dictionary containing only the app parameters
        (does not include nprocs or exe paths)."""
        return self.instance.as_dict()

    def add_dataspaces_support(self, machine):
        """
        Add support for dataspaces.
        Check RC Adios xml files to see if any transport methods are marked
        for coupling with DATASPACES/DIMES.
        For stage_write, check command line args to see if DATASPACES/DIMES
        is specified.
        :param machine: The current machine. I dont like this here.
        :return:
        """

        rcs_for_coupling = {'dimes': set(), 'dataspaces': set()}
        # Search in all RC's adios xml file if any transport is set for
        # coupling with DATASPACES/DIMES
        # This is case sensitive
        for rc in self.run_components:
            if rc.adios_xml_file:
                f_xml = os.path.join(rc.working_dir, os.path.basename(
                    rc.adios_xml_file))

                # The xml file may have both dataspaces and dimes in
                # different groups. If any group has dataspaces
                # enabled, this rc should be marked as a dataspaces client
                # Order is important here. First search for dataspaces.
                if xml_has_transport(f_xml, "DATASPACES"):
                    rcs_for_coupling['dataspaces'].add(rc)
                if xml_has_transport(f_xml, "DIMES"):
                    rcs_for_coupling['dimes'].add(rc)

        # Special handling for stage_write
        # Check command line args for string to be one of DATASPACES/DIMES
        for rc in self.run_components:
            if "stage_write" in rc.exe:
                param_values = self.instance.parameter_values[rc.name]
                cmdlineargs = [val.value for val in param_values.values() if
                               (val.is_type(ParamCmdLineArg) and
                               type(val.value) == str)]
                if 'DATASPACES' in cmdlineargs:
                    rcs_for_coupling['dataspaces'].add(rc)
                elif'DIMES' in cmdlineargs:
                    rcs_for_coupling['dimes'].add(rc)

        if rcs_for_coupling['dimes'] or rcs_for_coupling['dataspaces']:
            self._insert_dataspaces_rc(rcs_for_coupling, machine)

        # Create symlink in rc working_dir to dataspaces output conf file
        rc_list = list(rcs_for_coupling['dimes']) + list(rcs_for_coupling[
                                                           'dataspaces'])
        src = os.path.join(self.run_path, "conf")
        for rc in rc_list:
            dst = os.path.join(rc.working_dir, "conf")
            if src != dst:
                os.symlink(src, dst)

    def _insert_dataspaces_rc(self, client_rcs, machine):
        """
        Add dataspaces support for this run.
        Creates a new RC with dataspaces server as the exe.
        :param client_rcs: Dist of sets for clients coupling using
        dataspaces or dimes
        :param machine_name: Current machine
        :return:
        """

        # Sanity check. rc list for coupling must have >1 RCs
        for transport_type in client_rcs:
            if len(client_rcs[transport_type]) == 1:
                raise exc.CheetahException("Atleast 2 codes needed for "
                                           "coupling with DATASPACES/DIMES. "
                                           "Found 1.")

        # Check that codes has dataspaces_server exe
        ds_server = None
        sleep_after = 0
        for code in self.codes:
            exe = self.codes[code]['exe']
            if 'dataspaces_server' in exe:
                ds_server = exe
                ds_rc_name = code
                sleep_after = self.codes[code].get('sleep_after', 0)

        if not ds_server:
            raise exc.CheetahException("Dataspaces server needs to be "
                                       "specified in codes")

        # Copy the configuration file dataspaces.conf
        ds_conf = os.path.join(self.codes_path, "dataspaces.conf")
        if not os.path.isfile(ds_conf):
            raise exc.CheetahException("Could not find dataspaces.conf in "
                                       + self.codes_path)
        dst = os.path.join(self.run_path, "dataspaces.conf")
        copy_to_path(ds_conf, dst)

        # Get the no. of dataspaces and dimes clients.
        # RCs that have both must be counted as dataspaces clients
        num_ds_clients = sum(rc.nprocs for rc in client_rcs['dataspaces'])
        unique_dimes_rcs = client_rcs['dimes'] - client_rcs['dataspaces']
        num_dimes_clients = sum(rc.nprocs for rc in unique_dimes_rcs)

        num_servers = config.get_dataspaces_num_servers(num_dimes_clients,
                                                        num_ds_clients)
        assert num_servers > 0

        rc_name = "dataspaces_server"
        args = ['-s', str(num_servers), '-c', str(num_ds_clients +
                                                  num_dimes_clients)]

        # Get the node layout
        node_layout = None
        for d in self.node_layout.layout_list:
            if ds_rc_name == list(d.keys())[0]:
                node_layout = d[ds_rc_name]
        if node_layout is None:
            node_layout = machine.dataspaces_servers_per_node

        rc = RunComponent(rc_name, ds_server, args,
                          nprocs=num_servers, sleep_after=sleep_after,
                          working_dir=self.run_path)

        self.node_layout.add_node({rc_name: node_layout})
        self.run_components.insert(0, rc)

    def insert_sosflow(self, sosd_path, sos_analysis_path, run_path, ppn):
        """Insert a new component at start of list to launch sosflow daemon.
        Should be called only once."""
        assert self.run_components[0].name != 'sosflow'

        # sos_args must be calculated before adding sosflow as a RunComponent,
        # as get_total_nodes() needs to return only application nodes and not
        # any nodes required by sosflow.

        num_listeners = self._get_total_sosflow_component_nodes()
        # return if no components are setup to use sosflow. That is,
        # sosflow=False in `codes` for all components
        if num_listeners == 0:
            return

        # From Kevin Huck, U of Oregon
        max_listeners_per_aggregator = 64
        num_aggregators = math.ceil(num_listeners/max_listeners_per_aggregator)

        # Add sos aggregators to be run
        #   common aggregator parameters
        sos_args = [
            '-l', str(num_listeners),
            '-a', str(num_aggregators),
            '-w', shlex.quote(run_path)
        ]
        sos_cmd = ' '.join([sosd_path] + sos_args)
        sos_fork_cmd = sos_cmd + ' -k @LISTENER_RANK@ -r listener'

        #   now add each aggregator, starting with the analysis aggregator
        listener_node_offset = 0
        for i in range(num_aggregators):
            sosd_args = sos_args + [
                '-k', str(i),
                '-r', 'aggregator',
            ]

            rc_name = 'sosflow_aggregator_' + str(i)
            rc_exe_path = sosd_path

            # If sos analysis is enabled, the first aggregator should be
            # the sos analysis script instead of a plain sosd aggregator.
            if i == 0 and self.sosflow_analysis:
                rc_name = "sosflow_analysis"
                rc_exe_path = sos_analysis_path
                sosd_args = [sosd_path] + sosd_args

            self.node_layout.add_node({rc_name: 1})

            rc = RunComponent(rc_name,
                              rc_exe_path, sosd_args,
                              nprocs=1, sleep_after=5,
                              working_dir=self.run_path)
            rc.env['sos_cmd'] = sos_cmd
            rc.env['SOS_FORK_COMMAND'] = sos_fork_cmd
            rc.env['SOS_CMD_PORT'] = '22500'
            rc.env['SOS_EVPATH_MEETUP'] = run_path
            rc.env['TAU_SOS'] = '1'
            self.run_components.insert(i, rc)

            listener_node_offset += 1

        # add env vars to each run, including sosflow daemon
        # NOTE: not sure how many if any are required for sosd, but
        # should not hurt to have them, and simplifies the offset
        # calculation
        for rc in self.run_components:
            # ignore component if not setup to use sosflow
            if not rc.linked_with_sosflow:
                continue

            # TODO: is this actually used directly?
            rc.env['sos_cmd'] = sos_cmd
            rc.env['SOS_FORK_COMMAND'] = sos_fork_cmd

            code_node = self.node_layout.get_node_containing_code(rc.name)

            # TODO: we don't yet know how SOSFLOW will support apps that
            # do node shairng, so for now require that there is no
            # sharing.
            assert len(code_node) == 1

            code_procs_per_node = code_node[rc.name]
            code_nodes = int(math.ceil(rc.nprocs / code_procs_per_node))

            # Set the TCP port that the listener will listen to,
            # and the port that clients will attempt to connect to.
            rc.env['SOS_CMD_PORT'] = '22500'

            # Set the directory where the SOS listeners and aggregators
            # will use to establish EVPath links to each other
            rc.env['SOS_EVPATH_MEETUP'] = run_path

            # Tell TAU that it should connect to SOS
            # and send TAU data to SOS when adios_close(),
            # adios_advance_step() calls are made,
            # and when the application terminates.
            rc.env['TAU_SOS'] = '1'

            # Tell SOS how many application ranks per node there are
            # How do you get this information?
            # TODO: This will change when we have the ability to set a
            # different number of procs per node
            rc.env['SOS_APP_RANKS_PER_NODE'] = str(code_procs_per_node)

            # Tell SOS what 'rank' it's listeners should start with
            # the aggregator was 'rank' 0, so this node's listener will be 1
            # This offset is the node count where this fob component starts
            rc.env['SOS_LISTENER_RANK_OFFSET'] = str(listener_node_offset)

            # TODO: this assumes node exclusive. To support node sharing
            # with custom layouts, will need to know layout here and
            # calculate actual node usage. This potentially duplicates
            # functionality needed in workflow, should eventual converge
            # so they are using the same model.
            listener_node_offset += code_nodes


class RunComponent(object):
    def __init__(self, name, exe, args, sched_args, nprocs, working_dir,
                 component_inputs=None, sleep_after=None,
                 linked_with_sosflow=False, adios_xml_file=None,
                 env=None, timeout=None, hostfile=None):
        self.name = name
        self.exe = exe
        self.args = args
        self.sched_args = sched_args
        self.nprocs = nprocs
        self.sleep_after = sleep_after
        self.env = env or {}
        self.timeout = timeout
        self.working_dir = working_dir
        self.component_inputs = component_inputs
        self.linked_with_sosflow = linked_with_sosflow
        self.adios_xml_file = adios_xml_file
        self.hostfile = hostfile
        self.after_rc_done = None

    def as_fob_data(self):
        data = dict(name=self.name,
                    exe=self.exe,
                    args=self.args,
                    sched_args=self.sched_args,
                    nprocs=self.nprocs,
                    working_dir=self.working_dir,
                    sleep_after=self.sleep_after,
                    linked_with_sosflow=self.linked_with_sosflow,
                    adios_xml_file=self.adios_xml_file,
                    hostfile=self.hostfile,
                    after_rc_done=self.after_rc_done)
        if self.env:
            data['env'] = self.env
        if self.timeout:
            data['timeout'] = self.timeout
        if self.hostfile:
            data['hostfile'] = self.working_dir + "/" + self.hostfile
        return data
