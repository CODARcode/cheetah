"""
Object oriented model to represent jobs to run on different Supercomputers or
workstations using different schedulers and runners (for running applications
on compute nodes from front end nodes), and allow pass through of scheduler
or runner specific options.
"""
import itertools


class SchedulerJob(object):
    """
    Class to represent a job on a scheduler like PBS, SLURM, or Local
    (for no scheduler). Maps conceptual names like 'nodes' to the specific
    command line arguments that need to be passed.
    """
    def __init__(self, name, runner):
        self.name = name
        self.runner = runner
        self.lines = []

    def add_application_run(self, app_command):
        """
        Add a run of the application with a fixed set of parameters to this
        job.
        """
        full_command = self.runner.wrap_app_command(app_command)
        self.lines.append(full_command)

    def get_script(self, account, constraints, nodes):
        # subclass must implement
        raise NotImplemented()


class LocalJob(SchedulerJob):
    """
    Job that ignores all scheduler options and runs the command directly
    on the local machine with bash, one at a time with no parallelism.
    """
    TEMPLATE = """
#!/bin/bash

set -x
set -e
"""

    def __init__(self):
        SchedulerJob.__init__(self, 'local', LocalRunner())

    def get_script(self, account, constrains, nodes):
        return "#!/bin/bash\n\n"


class Runner(object):
    def __init__(self, name):
        self.name = name


class LocalRunner(Runner):
    def __init__(self):
        Runner.__init__(self, 'local')


class Machine(object):
    """
    Class to represent configuration of a specific Supercomputer or
    workstation, including the scheduler and runner used by the machine.
    This can be used to map an experiment to run on the machine without
    having to define machine specific parameter for every experiment
    separately.
    """

    def __init__(self, scheduler, runner):
        self.scheduler = scheduler
        self.runner = runner


class Experiment(object):
    def __init__(self, name):
        self.name = name


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
    def __init__(self):
        self.args = {}
        self.options = {}

    def add_parameter(self, p, idx):
        if isinstance(p, ParamCmdLineArg):
            self.args[p.position] = p.values[idx]

    def as_string(self):
        parts = []
        position = 1
        while True:
            if position in self.args:
                parts.append(str(self.args[position]))
        for name, value in self.options.items():
            # NOTE: the value should include the opt name in required
            # format, e.g. --long vs -s vs -longtype2
            parts.append(value)
        return " ".join(parts)


class ParamCmdLineArg(object):
    def __init__(self, name, position, values):
        self.name = name
        self.position = position
        self.values = values

    def __get__(self, idx):
        return self.values[idx]
