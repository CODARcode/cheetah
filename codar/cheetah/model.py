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


class Campaign(object):
    """An experiment class specifies an application, a set of parameter to
    sweep over, and a set of supported target machine. A specific instance
    binds the experiment to a specific machine within the set of supported
    machines, and supports generating a set of scripts to run the experiment
    on that machine."""

    # subclasses must populate these
    name = None
    codes = {}
    supported_machines = []
    sweeps = []
    inputs = []
    inputs_fullpath = []

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
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        for group_i, group in enumerate(self.sweeps):
            # top level should be SweepGroup, open scheduler file
            if not isinstance(group, parameters.SweepGroup):
                raise ValueError("top level run groups must be SweepGroup")
            # each scheduler group gets it's own subdir
            # TODO: support alternate template for dirs?
            group_output_dir = os.path.join(output_dir,
                                            "group-%03d" % (group_i+1))
            os.makedirs(group_output_dir, exist_ok=True)
            launcher = self.machine.get_launcher_instance(group_output_dir,
                                                          len(self.codes))
            group_instances = group.get_instances()
            group_runs = [Run(inst, self.codes, self.app_dir,
                              os.path.join(group_output_dir, 'run-%03d' % i),
                              self.inputs_fullpath)
                          for i, inst in enumerate(group_instances)]
            self.runs.extend(group_runs)
            launcher.write_submit_script()
            launcher.write_status_script()
            launcher.write_wait_script()
            launcher.write_batch_script(group_runs)
        run_all_path = os.path.join(output_dir, "run-all.sh")
        all_params_json_path = os.path.join(output_dir, "params.json")
        with open(run_all_path, "w") as f:
            f.write(RUN_ALL_TEMPLATE.format(experiment_dir=output_dir))
            if self.post_process_script:
                pps_path = os.path.join(self.app_dir, self.post_process_script)
                f.write('\n%s %s\n' % (pps_path, all_params_json_path))
        helpers.make_executable(run_all_path)
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
        Return list of tuples with argv lists and nprocs. The 0th element of
        each argv is the application executable (absolute path).

        TODO: less hacky way of handling nprocs and other middlewear params.
        """
        argv_nprocs_list = []
        for (target, argv) in self.instance.get_codes_argv().items():
            relative_exe = self.codes[target]
            exe_path = os.path.join(self.codes_path, relative_exe)
            nprocs = self.instance.parameters[target].get('nprocs', "1")
            argv_nprocs_list.append(([exe_path] + argv, nprocs))
        return argv_nprocs_list

    def as_dict(self):
        return self.instance.as_dict()
