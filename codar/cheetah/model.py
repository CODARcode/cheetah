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

from codar.cheetah import machines, parameters, helpers


RUN_ALL_TEMPLATE = """#!/bin/bash
set -e

cd {experiment_dir}
start=$(date +%s)
for group_dir in group-*; do
    echo -n "Start $group_dir ... "
    cd "$group_dir"
    ./submit.sh
    ./wait.sh
    cd ..
done
end=$(date +%s)
echo $(($end - $start)) > codar.cheetah.walltime.txt
"""


class Experiment(object):
    """An experiment class specifies an application, a set of parameter to
    sweep over, and a set of supported target machine. A specific instance
    binds the experiment to a specific machine within the set of supported
    machines, and supports generating a set of scripts to run the experiment
    on that machine."""

    # subclasses must populate these
    name = None
    app_exe = None # TODO: how to handle location of exe on different machines?
    supported_machines = []
    runs = []

    def __init__(self, machine_name, app_dir):
        # check that subclasses set configuration
        # TODO: better errors
        # TODO: is class variables best way to model this??
        assert self.name is not None
        assert self.app_exe is not None
        assert len(self.supported_machines) > 0
        assert len(self.runs) > 0
        self.machine = self._get_machine(machine_name)
        self.app_dir = app_dir
        self.app_exe_path = os.path.join(app_dir, self.app_exe)

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
        run. """
        os.makedirs(output_dir, exist_ok=True)
        for group_i, group in enumerate(self.runs):
            # top level should be SchedulerGroup, open scheduler file
            if not isinstance(group, parameters.SchedulerGroup):
                raise ValueError("top level run groups must be SchedulerGroup")
            # each scheduler group gets it's own subdir
            # TODO: support alternate template for dirs?
            group_output_dir = os.path.join(output_dir,
                                            "group-%03d" % (group_i+1))
            os.makedirs(group_output_dir, exist_ok=True)
            scheduler = self.machine.get_scheduler_instance(group_output_dir)
            scheduler.write_submit_script()
            scheduler.write_status_script()
            scheduler.write_wait_script()
            scheduler.write_batch_script(self.app_exe_path, group)
        run_all_path = os.path.join(output_dir, "run-all.sh")
        with open(run_all_path, "w") as f:
            f.write(RUN_ALL_TEMPLATE.format(experiment_dir=output_dir))
        helpers.make_executable(run_all_path)
