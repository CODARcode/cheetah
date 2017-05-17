"""
Configuration for machines supported by Codar.
"""
from codar.cheetah import runners, schedulers, exc


class Machine(object):
    """Class to represent configuration of a specific Supercomputer or
    workstation, including the scheduler and runner used by the machine.
    This can be used to map an experiment to run on the machine without
    having to define machine specific parameter for every experiment
    separately."""

    def __init__(self, scheduler_class, runner_class):
        self.scheduler_class = scheduler_class
        self.runner_class = runner_class

    def get_scheduler_instance(self, output_directory):
        return self.scheduler_class(self.runner_class(), output_directory)


# All machine names must be lowercase, to avoid conflicts with class
# definitions etc. This allows the module to act as a sort of enum
# container with all the machines.
titan=Machine(schedulers.SchedulerPBS, runners.RunnerCray)
local=Machine(schedulers.SchedulerLocal, runners.RunnerLocal)
swift=Machine(schedulers.SchedulerSwift, runners.RunnerLocal)


def get_by_name(name):
    assert name == name.lower()
    try:
        return globals()[name]
    except KeyError:
        raise exc.MachineNotFound(name)
