"""
Configuration for machines supported by Codar.
"""
from codar.cheetah import launchers, exc


# Note: not all schedulers support all options, the purpose of this is
# just basic validation to catch mispelling or completely unsupported
# options. Some options have different names, we favor PBS naming when
# possible. For example, queue is mapped to partition on cori/slurm.
# TODO: deeper validation, probably bring back a scheduler model.
SCHEDULER_OPTIONS = set(["project", "queue", "constraint", "license"])


class Machine(object):
    """Class to represent configuration of a specific Supercomputer or
    workstation, including the scheduler and runner used by the machine.
    This can be used to map an experiment to run on the machine without
    having to define machine specific parameter for every experiment
    separately."""

    def __init__(self, name, launcher_class, scheduler_name, runner_name,
                 processes_per_node=None, node_exclusive=False,
                 scheduler_options=None, dataspaces_servers_per_node=1):
        self.name = name
        self.launcher_class = launcher_class
        self.scheduler_name = scheduler_name
        self.runner_name = runner_name
        # TODO: should the workflow script have knowledge of different
        # machines, or just generic options configured by Cheetah?
        self.processes_per_node = processes_per_node
        self.node_exclusive = node_exclusive
        _check_known_scheduler_options(SCHEDULER_OPTIONS, scheduler_options)
        self.scheduler_options = scheduler_options or {}
        self.dataspaces_servers_per_node = dataspaces_servers_per_node

    def get_launcher_instance(self, output_directory, num_codes):
        return self.launcher_class(self.name, self.scheduler_name,
                                   self.runner_name, output_directory,
                                   num_codes)

    def get_scheduler_options(self, options):
        """Validate supplied options and add default values where missing.
        Returns a new dictionary."""
        supported_set = set(self.scheduler_options.keys())
        _check_known_scheduler_options(supported_set, options)
        new_options = dict(self.scheduler_options)
        new_options.update(options)
        return new_options


def _check_known_scheduler_options(supported_set, options):
    if options is None:
        return
    unknown = set(options.keys()) - supported_set
    if unknown:
        raise ValueError("Unsupported scheduler option(s): "
                         + ",".join(opt for opt in unknown))


# All machine names must be lowercase, to avoid conflicts with class
# definitions etc. This allows the module to act as a sort of enum
# container with all the machines.

# NOTE: set process per node to avoid errors with sosflow calculations
local=Machine('local', launchers.Launcher, "local", "mpiexec",
              processes_per_node=1)

titan=Machine('titan', launchers.Launcher, "pbs", "aprun",
              processes_per_node=16, node_exclusive=True,
              scheduler_options=dict(project="", queue="debug"),
              dataspaces_servers_per_node=4)

# TODO: remove node exclusive restriction, which can be avoided on cori
# using correct sbatch and srun options. As a start just get feature
# parity with titan.
cori=Machine('cori', launchers.Launcher, "slurm", "srun",
             processes_per_node=32, node_exclusive=True,
             dataspaces_servers_per_node=4,
             scheduler_options=dict(project="",
                                    queue="debug",
                                    constraint="haswell",
                                    license="SCRATCH,project"))


theta=Machine('theta', launchers.Launcher, "cobalt", "aprun",
              processes_per_node=64, node_exclusive=True,
              dataspaces_servers_per_node=8,
              scheduler_options=dict(project="",
                                     queue="debug-flat-quad"))



def get_by_name(name):
    assert name == name.lower()
    try:
        return globals()[name]
    except KeyError:
        raise exc.MachineNotFound(name)
