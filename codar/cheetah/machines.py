"""
Configuration for machines supported by Codar.
"""
from codar.cheetah import launchers, exc


class Machine(object):
    """Class to represent configuration of a specific Supercomputer or
    workstation, including the scheduler and runner used by the machine.
    This can be used to map an experiment to run on the machine without
    having to define machine specific parameter for every experiment
    separately."""

    def __init__(self, name, launcher_class, scheduler_name, runner_name,
                 processes_per_node=None, node_exclusive=False):
        self.name = name
        self.launcher_class = launcher_class
        self.scheduler_name = scheduler_name
        self.runner_name = runner_name
        # TODO: should the workflow script have knowledge of different
        # machines, or just generic options configured by Cheetah?
        self.processes_per_node = processes_per_node
        self.node_exclusive = node_exclusive

    def get_launcher_instance(self, output_directory, num_codes):
        return self.launcher_class(self.name, self.scheduler_name,
                                   self.runner_name, output_directory,
                                   num_codes)


# All machine names must be lowercase, to avoid conflicts with class
# definitions etc. This allows the module to act as a sort of enum
# container with all the machines.

local=Machine('local', launchers.Launcher, "local", "mpiexec")
titan=Machine('titan', launchers.Launcher, "pbs", "aprun",
              processes_per_node=16, node_exclusive=True)

# TODO: remove node exclusive restriction, which can be avoided on cori
# using correct sbatch and srun options. As a start just get feature
# parity with titan.
cori=Machine('cori', launchers.Launcher, "slurm", "srun",
             processes_per_node=32, node_exclusive=True)


def get_by_name(name):
    assert name == name.lower()
    try:
        return globals()[name]
    except KeyError:
        raise exc.MachineNotFound(name)
