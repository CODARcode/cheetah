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
from collections import OrderedDict

from codar.cheetah import machines, parameters, helpers, config, templates


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

    # Schedular options. Not used when using machine 'local', required
    # if using 'titan'.
    project = "" # project allocation to use
    queue = "" # scheduler queue to submit to

    # None means use default
    tau_config = None

    # Optional. If set, passed single argument which is the absolute
    # path to a JSON file containing all runs. Must be relative to the
    # app directory, just like codes values. It will be run from the
    # top level experiment directory. TODO: could allow absolute paths
    # too
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

        if self.tau_config is None:
            self.tau_config = config.etc_path('tau.conf')
        elif not self.tau_config.startswith('/'):
            self.tau_config = os.path.join(self.app_dir, self.tau_config)

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
        shutil.copy2(run_all_script, output_dir)

        campaign_env = templates.CAMPAIGN_ENV_TEMPLATE.format(
            experiment_dir=output_dir,
            machine_config=config.machine_submit_env_path(self.machine.name),
            workflow_script_path=config.WORKFLOW_SCRIPT,
            workflow_runner=self.machine.runner_name,
            workflow_debug_level="DEBUG",
            workflow_kill_on_partial_failure=self.kill_on_partial_failure
        )
        campaign_env_path = os.path.join(output_dir, 'campaign-env.sh')
        with open(campaign_env_path, 'w') as f:
            f.write(campaign_env)

        for group_i, group in enumerate(self.sweeps):
            # top level should be SweepGroup, open scheduler file
            if not isinstance(group, parameters.SweepGroup):
                raise ValueError("top level run groups must be SweepGroup")
            # each scheduler group gets it's own subdir
            # TODO: support alternate template for dirs?
            group_name = "group-%03d" % (group_i+1)
            group_output_dir = os.path.join(output_dir, group_name)
            launcher = self.machine.get_launcher_instance(group_output_dir,
                                                          len(self.codes))
            group_instances = group.get_instances()
            group_runs = [Run(inst, self.codes, self.app_dir,
                              os.path.join(group_output_dir, 'run-%03d' % i),
                              self.inputs_fullpath)
                          for i, inst in enumerate(group_instances)]
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
            launcher.create_group_directory(self.name, group_name,
                                            group_runs,
                                            max_procs,
                                            processes_per_node=group_ppn,
                                            queue=self.queue,
                                            nodes=group.nodes,
                                            project=self.project,
                                            walltime=group.walltime,
                                            timeout=group.per_run_timeout,
                                            node_exclusive=
                                                self.machine.node_exclusive,
                                            tau_config=self.tau_config)

        # TODO: track directories and ids and add to this file
        all_params_json_path = os.path.join(output_dir, "params.json")
        with open(all_params_json_path, "w") as f:
            json.dump([run.as_dict() for run in self.runs], f, indent=2)


class Run(object):
    """
    Class representing how to actually run an instance on a given environment,
    including how to generate arg arrays for executing each code required for
    the application.
    """
    def __init__(self, instance, codes, codes_path, run_path, inputs):
        self.instance = instance
        self.codes = codes
        self.codes_path = codes_path
        self.run_path = run_path
        self.inputs = inputs

    def get_codes_argv_with_exe_and_nprocs(self):
        """
        Return list of tuples with target name, argv lists, and nprocs.
        The 0th element of each argv is the application executable
        (absolute path).

        TODO: less hacky way of handling nprocs and other middlewear params.
        """
        argv_nprocs_list = []
        for (target, argv) in self.instance.get_codes_argv().items():
            exe_path = self.codes[target]['exe']
            if not exe_path.startswith('/'):
                exe_path = os.path.join(self.codes_path, exe_path)
            nprocs = self.instance.get_nprocs(target)
            sleep_after = self.codes[target].get('sleep_after', 0)
            item = (target, [exe_path] + argv, nprocs, sleep_after)
            argv_nprocs_list.append(item)
        return argv_nprocs_list

    def get_total_nprocs(self):
        total_nprocs = 0
        for (target, argv) in self.instance.get_codes_argv().items():
            total_nprocs += self.instance.get_nprocs(target)
        return total_nprocs

    def as_dict(self):
        return self.instance.as_dict()
