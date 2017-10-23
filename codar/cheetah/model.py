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
import json
import math
import shutil
import inspect
from collections import OrderedDict

from codar.cheetah import machines, parameters, helpers, config, templates


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
    inputs = []
    inputs_fullpath = []

    # If set and there are multiple codes making up the application,
    # kill all remaining codes if one code fails.
    kill_on_partial_failure = False

    # Optional. If set, passed single argument which is the absolute
    # path to a JSON file containing the FOB definition for the run.
    # The path can be absolute (starts with /), or relative to the app
    # directory (if does not start with /).
    # If the script has nonzero exit status, then the entire sweep group
    # can optionally be stopped. This can be used to detect errors early.
    run_post_process_script = None
    run_post_process_stop_group_on_failure = False

    # Schedular options. Not used when using machine 'local', required
    # when using super computers.
    scheduler_options = {}

    # None means use default
    tau_config = None

    # None means use 'sosd' in the app dir
    # TODO: make this part of machine config? Or does it make sense to
    # have per-app binaries for sos?
    sosd_path = None

    # Optional. If set, passed single argument which is the absolute
    # path to a JSON file containing all runs. Must be relative to the
    # app directory, just like codes values. It will be run from the
    # top level experiment directory.
    # TODO: this is broken. It should really be a group post process
    # script now, and it could be passed as an arg to the workflow
    # script.
    post_process_script = None

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
        for input_rpath in self.inputs:
            self.inputs_fullpath.append(os.path.join(self.app_dir, input_rpath))

        if not isinstance(self.codes, OrderedDict):
            self.codes = OrderedDict(self.codes)

        conflict_names = set(self.codes.keys()) & RESERVED_CODE_NAMES
        if conflict_names:
            raise ValueError('Code names conflict with reserved names: '
                + ", ".join(str(name) for name in conflict_names))

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
            self.tau_config = os.path.join(self.app_dir, self.sosd_path)

        o = self.scheduler_options.get(machine_name, {})
        # TODO: deeper validation with knowledge of scheduler
        self.machine_scheduler_options = self.machine.get_scheduler_options(o)

    def _get_machine(self, machine_name):
        machine = None
        for m in self.supported_machines:
            if m == machine_name:
                machine = machines.get_by_name(m)
        if machine is None:
            raise ValueError("machine '%s' not supported by experiment '%s'"
                             % (machine_name, self.name))
        return machine

    def make_experiment_run_dir(self, output_dir):
        """Produce scripts and directory structure for running the experiment.

        Directory structure will be a subdirectory for each scheduler group,
        and within each scheduler group directory, a subdirectory for each
        run."""
        output_dir = os.path.abspath(output_dir)
        run_all_script = os.path.join(config.CHEETAH_PATH_SCRIPTS,
                                      self.machine.scheduler_name,
                                      'run-all.sh')
        os.makedirs(output_dir, exist_ok=True)

        # Check if campaign dir already has groups with the same name
        self._assert_unique_group_names(output_dir)

        # Create run script and campaign environment info file
        shutil.copy2(run_all_script, output_dir)

        campaign_env = templates.CAMPAIGN_ENV_TEMPLATE.format(
            experiment_dir=output_dir,
            machine_config=config.machine_submit_env_path(self.machine.name),
            workflow_script_path=config.WORKFLOW_SCRIPT,
            workflow_runner=self.machine.runner_name,
            workflow_debug_level="DEBUG"
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
                                        self.codes)
                group_runs = [Run(inst, self.codes, self.app_dir,
                                  os.path.join(group_output_dir,
                                               'run-%03d' % i),
                                  self.inputs_fullpath,
                                  node_layout=node_layout)
                              for i, inst in enumerate(sweep.get_instances())]
            self.runs.extend(group_runs)
            if group.max_procs is None:
                max_procs = max([r.get_total_nprocs() for r in group_runs])
            else:
                procs_per_run = max([r.get_total_nprocs() for r in group_runs])
                if group.max_procs < procs_per_run:
                    # TODO: improve error message, specifying which
                    # group and by how much it's off etc
                    raise ValueError("max_procs for group is too low")
                max_procs = group.max_procs
            if self.machine.node_exclusive:
                group_ppn = self.machine.processes_per_node
            else:
                group_ppn = math.ceil((max_procs) / group.nodes)
            # TODO: refactor so we can just pass the campaign and group
            # objects, i.e. add methods so launcher can get all info it needs
            # and simplify this loop.
            launcher.create_group_directory(
                self.name, group_name,
                group_runs,
                max_procs,
                processes_per_node=group_ppn,
                nodes=group.nodes,
                walltime=group.walltime,
                timeout=group.per_run_timeout,
                node_exclusive=self.machine.node_exclusive,
                tau_config=self.tau_config,
                kill_on_partial_failure=self.kill_on_partial_failure,
                run_post_process_script=self.run_post_process_script,
                run_post_process_stop_on_failure=
                    self.run_post_process_stop_group_on_failure,
                scheduler_options=self.machine_scheduler_options,
                machine=self.machine,
                sosflow=group.sosflow,
                sosd_path=self.sosd_path,
                node_layout=node_layout)

        # TODO: track directories and ids and add to this file
        all_params_json_path = os.path.join(output_dir, "params.json")
        with open(all_params_json_path, "w") as f:
            json.dump([run.get_app_param_dict()
                       for run in self.runs], f, indent=2)

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

    @classmethod
    def default_no_share_layout(cls, ppn, codes):
        """Create a layout object for the specified codes and ppn, where each
        code uses max procs on it's own node."""
        layout = [{ code: ppn } for code in codes.keys()]
        return cls(layout)


class Run(object):
    """
    Class representing how to actually run an instance on a given environment,
    including how to generate arg arrays for executing each code required for
    the application.

    TODO: create a model shared between workflow and cheetah, i.e. codar.model
    """
    def __init__(self, instance, codes, codes_path, run_path, inputs,
                 node_layout):
        self.instance = instance
        self.codes = codes
        self.codes_path = codes_path
        self.run_path = run_path
        self.run_id = os.path.basename(run_path)
        self.inputs = inputs
        self.node_layout = node_layout
        self.run_components = self._get_run_components()

    def _get_run_components(self):
        comps = []
        codes_argv = self._get_codes_argv_ordered()
        for (target, argv) in codes_argv.items():
            exe_path = self.codes[target]['exe']
            if not exe_path.startswith('/'):
                exe_path = os.path.join(self.codes_path, exe_path)
            sleep_after = self.codes[target].get('sleep_after', 0)
            comp = RunComponent(name=target, exe=exe_path, args=argv,
                                nprocs=self.instance.get_nprocs(target),
                                sleep_after=sleep_after)
            comps.append(comp)
        return comps

    def get_fob_data_list(self):
        return [comp.as_fob_data() for comp in self.run_components]

    def _get_codes_argv_ordered(self):
        """Wrapper around instance.get_codes_argv which uses correct order
        from self.codes OrderedDict."""
        codes_argv = self.instance.get_codes_argv()
        # Note that a given Run may not use all codes, e.g. for base
        # case app runs that don't use adios stage_write or dataspaces.
        return OrderedDict((k, codes_argv[k]) for k in self.codes.keys()
                           if k in codes_argv)

    def get_total_nprocs(self):
        return sum(rc.nprocs for rc in self.run_components)

    def get_app_param_dict(self):
        """Return dictionary containing only the app parameters
        (does not include nprocs or exe paths)."""
        return self.instance.as_dict()

    def insert_sosflow(self, sosd_path, run_path, num_aggregators, ppn):
        """Insert a new component at start of list to launch sosflow daemon.
        Should be called only once."""
        assert self.run_components[0].name != 'sosflow'
        self.node_layout.add_node({ 'sosflow': 1 })
        sos_args = [
            '-l', str(self.get_total_nprocs()),
            '-a', str(num_aggregators),
            '-w', str(run_path)
        ]
        sos_cmd = ' '.join([sosd_path] + sos_args)
        sos_fork_cmd = sos_cmd + ' -k @LISTENER_RANK@ -r listener'
        sosd_args = sos_args + [
            '-k', '0',
            '-r', 'aggregator',
        ]

        # Insert sosd component so it runs at start after 5 seconds
        rc = RunComponent('sosflow', sosd_path, sosd_args,
                          nprocs=1, sleep_after=5)
        self.run_components.insert(0, rc)

        node_offset = 0

        # add env vars to each run, including sosflow daemon
        # NOTE: not sure how many if any are required for sosd, but
        # should not hurt to have them, and simplifies the offset
        # calculation
        for rc in self.run_components:
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
            rc.env['SOS_APP_RANKS_PER_NODE'] = str(code_nodes)

            # Tell SOS what 'rank' it's listeners should start with
            # the aggregator was 'rank' 0, so this node's listener will be 1
            # This offset is the node count where this fob component starts
            rc.env['SOS_LISTENER_RANK_OFFSET'] = str(node_offset)

            # TODO: this assumes node exclusive. To support node sharing
            # with custom layouts, will need to know layout here and
            # calculate actual node usage. This potentially duplicates
            # functionality needed in workflow, should eventual converge
            # so they are using the same model.
            node_offset += code_nodes


class RunComponent(object):
    def __init__(self, name, exe, args, nprocs, sleep_after=None,
                 env=None, timeout=None):
        self.name = name
        self.exe = exe
        self.args = args
        self.nprocs = nprocs
        self.sleep_after = sleep_after
        self.env = env or {}
        self.timeout = timeout

    def as_fob_data(self):
        data = dict(name=self.name,
                    exe=self.exe,
                    args=self.args,
                    nprocs=self.nprocs,
                    sleep_after=self.sleep_after)
        if self.env:
            data['env'] = self.env
        if self.timeout:
            data['timeout'] = self.timeout
        return data
