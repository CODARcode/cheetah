"""
Object oriented model to represent jobs to run on different Supercomputers or
workstations using different schedulers and runners (for running applications
on compute nodes from front end nodes), and allow pass through of scheduler
or runner specific options.
"""
import itertools
import os


class SchedulerBatch(object):
    """
    Class to represent a job on a scheduler like PBS, SLURM, or Local
    (for no scheduler). Maps conceptual names like 'nodes' to the specific
    command line arguments that need to be passed. Holds a reference to
    the corresponding runner (e.g. aprun or srun).
    """
    def __init__(self, name, runner):
        self.name = name
        self.runner = runner

    def write_batch_script(self, group_output_dir, param_group):
        # subclass must implement
        raise NotImplemented()


class LocalBatch(SchedulerBatch):
    """
    Batch type that ignores all scheduler options and runs the command directly
    on the local machine with bash, one at a time with no parallelism.
    """
    HEADER = """
#!/bin/bash

set -x
set -e

"""

    def __init__(self):
        SchedulerBatch.__init__(self, 'local', LocalRunner())

    def write_batch_script(self, group_output_dir, param_group):
        script_path = os.path.join(group_output_dir, 'run.sh')
        with open(script_path, 'w') as f:
            f.write(self.HEADER)
            for run in param_group.get_runs():
                for line in self.runner.wrap_app_command(run)
                    f.write(line)
                    f.write('\n')
        return script_path


class Runner(object):
    def __init__(self, name):
        self.name = name

    def wrap_app_command(command_dir, app_command):
        raise NotImplemented()


class LocalRunner(Runner):
    def __init__(self):
        Runner.__init__(self, 'local')

    def wrap_app_command(command_dir, app_command):
        """
        Run directly, just at cd before/after to arrange separate working
        dir per run.

        TODO: how to pass runner params?

        NOTE: assumes CWD is batch directory within the experiment output dir.
        """
        return ['cd "%s"' % command_dir, app_command, 'cd ..']


class Machine(object):
    """
    Class to represent configuration of a specific Supercomputer or
    workstation, including the scheduler and runner used by the machine.
    This can be used to map an experiment to run on the machine without
    having to define machine specific parameter for every experiment
    separately.
    """

    def __init__(self, scheduler_class, runner_class):
        self.scheduler_class = scheduler_class
        self.runner_class = runner_class


class Experiment(object):
    # subclasses must populate these
    name = None
    app_script = None
    machines = []
    runs = []

    def __init__(self):
        # check that subclasses set configuration
        # TODO: better errors
        # TODO: is class variables best way to model this??
        assert self.name is not None
        assert self.app_script is not None
        assert len(self.machines) > 0
        assert len(self.runs) > 0

    def _get_machine(self, machine_name):
        machine = None
        for m in self.machines:
            if m.name == machine_name:
                machine = m
        if machine is None:
            raise ValueError("machine '%s' not supported by experiment '%s'"
                             % (machine_name, self.name))
        return machine

    def make_experiment_run_dir(self, machine_name, output_dir):
        machine = self._get_machine(machine_name)
        scheduler = machine.scheduler_class(machine.runner_class())
        os.makedirs(output_dir, exists_ok=True)
        for group_i, group in enumerate(self.runs):
            # top level should be SchedulerGroup, open scheduler file
            if not isinstance(group, SchedulerGroup):
                raise ValueError("top level run groups must be SchedulerGroup")
            # each scheduler group gets it's own subdir
            # TODO: support alternate template for dirs?
            group_output_dir = os.path.join(output_dir, "group-%03d")
            os.makedirs(group_output_dir, exists_ok=True)
            scheduler.write_batch_script(group_output_dir, group)


class SchedulerGroup(object):
    """
    Class representing a grouping of run parameters that can be executed by
    a single scheduler job, because they share the same scheduler parameters
    (currently only # of nodes is at this level).

    How this gets converted into a script depends on the target machine and
    which scheduler (if any) that machine uses.
    """
    def __init__(self, nodes, parameter_groups):
        self.nodes = nodes
        self.paramater_groups = parameter_groups

    def get_runs(self, group_output_dir):
        runs = []
        for group in self.parameter_groups:
            runs.extend(group.get_runs())
        return runs


class ParameterGroup(object):
    """
    Class representing a set of parameter values to search over as
    a cross product.
    """
    def __init__(self, parameters):
        self.parameters = parameters

    def get_runs(self):
        """
        Get a list of strings representing all the runs over the cross
        product.

        TODO: this works great for command line options and args, but
        what about for config and other types of params? Need to setup
        a run dir and populate it with filled config templates.

        Also how to pass per run output dir? Or is just making CWD the
        per run dir enough for all cases we care about?
        """
        runs = []
        indexes = [range(p.size()) for p in self.parameters]
        for idx_set in itertools.product(*indexes):
            cmd = Command()
            for param_i, value_i in enumerate(idx_set):
                cmd.add_parameter(self.parameters[param_i], value_i)
            runs.append(cmd.as_string())
        return runs


class Command(object):
    """
    Helper class for building up a command by parts.
    """
    def __init__(self):
        self.args = {}
        self.options = {}

    def add_parameter(self, p, idx):
        if isinstance(p, ParamCmdLineArg):
            self.args[p.position] = p.values[idx]
        if isinstance(p, ParamCmdLineOption):
            self.options[p.option] = p.values[idx]

    def as_string(self):
        parts = []
        position = 1
        while True:
            if position in self.args:
                parts.append(str(self.args[position]))
        for option, value in self.options.items():
            # TODO: handle separator between option and value, e.g. '',
            # '=', or ' '.
            parts.append(option + ' ' + value)
        return " ".join(parts)


class ParamCmdLineArg(object):
    """Specification for parameters that are based as a positional command line
    argument."""
    def __init__(self, name, position, values):
        self.name = name
        self.position = position
        self.values = values

    def __get__(self, idx):
        return self.values[idx]


class ParamCmdLineOption(object):
    """Specification for parameters that are based as a labeled command line
    option. The option must contain the prefix, e.g. '--output-file' not
    'output-file'."""

    def __init__(self, name, option, values):
        self.name = name
        self.option = option
        self.values = values

    def __get__(self, idx):
        return self.values[idx]
