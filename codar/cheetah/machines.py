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

    def __init__(self, name, launcher_class, scheduler_name, runner_name):
        self.name = name
        self.launcher_class = launcher_class
        self.scheduler_name = scheduler_name
        self.runner_name = runner_name

    def get_launcher_instance(self, output_directory, num_codes):
        return self.launcher_class(self.name, self.scheduler_name,
                                   self.runner_name, output_directory,
                                   num_codes)


# All machine names must be lowercase, to avoid conflicts with class
# definitions etc. This allows the module to act as a sort of enum
# container with all the machines.

local=Machine('local', launchers.Launcher, "local", "mpiexec")
titan=Machine('titan', launchers.Launcher, "pbs", "aprun")


def get_by_name(name):
    assert name == name.lower()
    try:
        return globals()[name]
    except KeyError:
        raise exc.MachineNotFound(name)
