"""
TODO: when using swift-t, it can handle submission to PBS and
apirun/srun/mpiexec/mpiluanch, so it probably makes the scheduler/runner
class model unnecessary. Instead can have a SwiftLauncher with subclasses
for local, pbs, and slurm.
"""
import os
import json

from codar.cheetah import helpers


class Scheduler(object):
    """
    Class to represent a job on a scheduler like PBS, SLURM, or Local
    (for no scheduler). Maps conceptual names like 'nodes' to the specific
    command line arguments that need to be passed. Holds a reference to
    the corresponding runner (e.g. aprun or srun).

    It's job is to take a scheduler group and produce a script for executing
    all runs within the scheduler group with the indicated scheduler
    parameters.

    TODO: add another layer of abstraction that encapsulates templating
    and parameters for each scheduler, that could be used by other projects.
    This contains a lot of details specific to how we want to organize the
    output directories and keep track of the jobid and define run and monitor
    scripts, that is very specific to cheetah.
    """
    name = None # subclass must set

    # TODO: these variables names are becoming confusing
    submit_script_name = 'submit.sh'
    wait_script_name = 'wait.sh'
    status_script_name = 'status.sh'
    submit_out_name = 'codar.cheetah.submit-output.txt'
    run_command_name = 'codar.cheetah.run-params.txt'
    run_json_name = 'codar.cheetah.run-params.json'
    run_out_name = 'codar.cheetah.run-output.txt'
    batch_script_name = None
    batch_walltime_name = 'codar.cheetah.walltime.txt'
    jobid_file_name = 'codar.cheetah.jobid.txt'

    def __init__(self, runner, output_directory):
        self.runner = runner
        self.output_directory = output_directory

    def write_submit_script(self):
        """
        Must at minimum produce a single script 'run.sh' within the
        output_directory that will run the batch in the background or submit
        the job to a real scheduler. Must also generate a file
        'codar.cheetah.jobid.txt' in the output directory that can be read by
        the monitor script to wait on the job (or process).

        TODO: make executable
        """
        # subclass must implement
        raise NotImplemented()

    def write_status_script(self):
        """
        Save script that prints how long batch has been running, or an empty
        string if it's complete.
        """
        # subclass must implement
        raise NotImplemented()

    def write_wait_script(self):
        """
        Save script that waits for the batch to complete, and prints the
        total batch walltime.
        """
        # subclass must implement
        raise NotImplemented()

    def write_batch_script(self, runs):
        """
        Must at minimum produce a single script 'run.sh' within the
        group_output_dir that will run the batch in the background or submit
        the job to a real scheduler. May also produce other auxiliary scripts,
        e.g. sbatch or pbs files. The 'run.sh' file must generate a file
        'codar.cheetah.jobid.txt' in the group output dir that can be read by
        the monitor script to wait on the job.
        """
        # subclass must implement
        raise NotImplemented()

    def read_jobid(self):
        jobid_file_path = os.path.join(self.output_directory,
                                       self.jobid_file_name)
        with open(jobid_file_path) as f:
            jobid = f.read()
        return jobid

    def write_monitor_script(self):
        """Must at minimum produce a script 'monitor.sh' which will monitor the
        progress of the job after 'run.sh' produced by `write_batch_script`
        is run. The 'run.sh' script will run the experiment batch in the
        background, and this script will monitor it's progress and optionally
        trigger actions, such as sending an email or running result
        analysis."""
        # subclass must implement
        raise NotImplemented()


class SchedulerLocal(Scheduler):
    """
    DEPRECATED

    Batch type that ignores all scheduler options and runs the command directly
    on the local machine with bash, one at a time with no parallelism.

    An instance ties the scheduler together with a specific runner. Some
    schedulers may require a certain type of runner, but others may support
    multiple runners.
    """
    name = 'local'
    batch_script_name = 'local-run.sh'

    SUBMIT_TEMPLATE = """#!/bin/bash

cd {group_directory}
nohup bash {batch_script_name} >{submit_out_name} 2>&1 &
PID=$!
echo "{name}:$PID" > {jobid_file_name}
"""

    BATCH_HEADER = """#!/bin/bash

set -x
set -e

batch_start=$(date +%s)
"""

    BATCH_FOOTER = """batch_end=$(date +%s)
echo $(($batch_end - $batch_start)) > {batch_walltime_name}
"""

    WAIT_TEMPLATE = """#!/bin/bash

cd $(dirname $0)
PID=$(cat {jobid_file_name} | cut -d: -f2)
while [ -n "$(ps -p $PID -o time=)" ]; do
    sleep 1
done
cat {batch_walltime_name}
"""

    STATUS_TEMPLATE = """#!/bin/bash

cd $(dirname $0)
ps -p $(cat {jobid_file_name} | cut -d: -f2) -o time=
"""


    def write_submit_script(self):
        submit_path = os.path.join(self.output_directory,
                                   self.submit_script_name)
        with open(submit_path, 'w') as f:
            body = self.SUBMIT_TEMPLATE.format(
                        group_directory=self.output_directory,
                        batch_script_name=self.batch_script_name,
                        submit_out_name=self.submit_out_name,
                        jobid_file_name=self.jobid_file_name,
                        name=self.name)
            f.write(body)
        helpers.make_executable(submit_path)
        return submit_path

    def write_batch_script(self, runs):
        script_path = os.path.join(self.output_directory,
                                   self.batch_script_name)
        with open(script_path, 'w') as f:
            # ignore all scheduler parameters for local runs, and just
            # use a fixed hearder
            f.write(self.BATCH_HEADER)
            for i, run in enumerate(runs):
                # TODO: abstract this to higher levels
                command_dir = 'run-%03d' % (i+1)
                command_path = os.path.join(self.output_directory, command_dir)
                os.makedirs(command_path, exist_ok=True)
                run.set_output_directory(command_path)
                run_string = run.as_string()
                run_data = run.as_dict()
                # save command as text
                params_path_txt = os.path.join(command_path,
                                               self.run_command_name)
                with open(params_path_txt, 'w') as params_f:
                    params_f.write(run_string)
                    params_f.write('\n')
                # save params as JSON for use in post-processing, more
                # useful for post-processing scripts then the command
                # text
                # Possible alternative: single JSON file at top level
                # with all run dirs and params for each run
                params_path_json = os.path.join(command_path,
                                                self.run_json_name)
                with open(params_path_json, 'w') as params_f:
                    json.dump(run_data, params_f, indent=2)

                # add to batch script
                lines = self.runner.wrap_app_command(command_dir,
                                                     self.run_out_name,
                                                     run_string)
                if lines:
                    f.write('\n'.join(lines))
                    f.write('\n')
            f.write(self.BATCH_FOOTER.format(
                        batch_walltime_name=self.batch_walltime_name))
        helpers.make_executable(script_path)
        return script_path

    def write_status_script(self):
        script_path = os.path.join(self.output_directory,
                                   self.status_script_name)
        with open(script_path, 'w') as f:
            f.write(self.STATUS_TEMPLATE.format(
                        jobid_file_name=self.jobid_file_name))
        helpers.make_executable(script_path)
        return script_path

    def write_wait_script(self):
        script_path = os.path.join(self.output_directory,
                                   self.wait_script_name)
        with open(script_path, 'w') as f:
            f.write(self.WAIT_TEMPLATE.format(
                                jobid_file_name=self.jobid_file_name,
                                batch_walltime_name=self.batch_walltime_name))
        helpers.make_executable(script_path)
        return script_path


class SchedulerSwift(Scheduler):
    """
    Batch type that uses swift scripts.

    TODO: currently all output goes to swift script output, need to capture
    individual run output.
    """
    name = 'swift'
    batch_script_name = 'run.swift'

    # TODO: add subclasses for pbs and slurm that pass appropriate
    # option to swift-t
    SUBMIT_TEMPLATE = """#!/bin/bash

cd {group_directory}
nohup swift-t -p {batch_script_name} >{submit_out_name} 2>&1 &
PID=$!
echo "{name}:$PID" > {jobid_file_name}
"""

    BATCH_HEADER = """
import io;
import string;

string runs[][];
"""

    BATCH_FOOTER = """

(int exit_code, string error_message) system(string work_dir, string cmd)
"turbine" "1.0"
[
\"\"\"
set oldpwd [ pwd ]
cd <<work_dir>>
set cmd_tokens <<cmd>>
set <<error_message>> ""
set <<exit_code>> 0
if [ catch { exec {*}$cmd_tokens > /dev/stdout } e info ] {
  set <<exit_code>> [ dict get $info -error ]
  set <<error_message>> "$e"
}
cd $oldpwd
\"\"\"
];

(int exit_codes[], string error_messages[]) launch_multi(
                                string work_dir, string procs[],
                                string progs[], string args[][])
{
    for (int i=0; i < num_progs; i=i+1)
    {
        string cmd = progs[i] + " " + join(args[i], " ");
        (exit_codes[i], error_messages[i]) = system(work_dir, cmd);
    }
}

int run_exit_codes[][];
string run_error_messages[][];

for (int i=0; i<size(runs); i=i+1)
{
    dir_name = runs[i][0];
    string procs[];
    string progs[];
    string args[][];

    for (int j=0; j<num_progs; j=j+1)
    {
        procs[j] = runs[i][1+j*2];
        string prog_args = runs[i][2+j*2];
        parts = split(prog_args, " ");
        progs[j] = parts[0];
        for (int k=1; k<size(parts); k=k+1)
        {
            args[j][k-1] = parts[k];
        }
    }
    //printf("%s %s %s %s", dir_name, procs[0], progs[0], args[0][0]);
    (run_exit_codes[i], run_error_messages[i]) = launch_multi(dir_name, procs,
                                                              progs, args);
}


for (int i=0; i<size(runs); i=i+1)
{
    printf("run %d:", i);
    for (int j=0; j<num_progs; j=j+1)
    {
        printf(" %d (%s)", run_exit_codes[i][j], run_error_messages[i][j]);
    }
}
"""

    WAIT_TEMPLATE = """#!/bin/bash

cd $(dirname $0)
PID=$(cat {jobid_file_name} | cut -d: -f2)
while [ -n "$(ps -p $PID -o time=)" ]; do
    sleep 1
done
cat {batch_walltime_name}
"""

    STATUS_TEMPLATE = """#!/bin/bash

cd $(dirname $0)
ps -p $(cat {jobid_file_name} | cut -d: -f2) -o time=
"""


    def write_submit_script(self):
        submit_path = os.path.join(self.output_directory,
                                   self.submit_script_name)
        with open(submit_path, 'w') as f:
            body = self.SUBMIT_TEMPLATE.format(
                        group_directory=self.output_directory,
                        batch_script_name=self.batch_script_name,
                        submit_out_name=self.submit_out_name,
                        jobid_file_name=self.jobid_file_name,
                        name=self.name)
            f.write(body)
        helpers.make_executable(submit_path)
        return submit_path

    def write_batch_script(self, runs):
        script_path = os.path.join(self.output_directory,
                                   self.batch_script_name)
        with open(script_path, 'w') as f:
            f.write(self.BATCH_HEADER)
            f.write('int num_progs = 1;\n')
            for i, run in enumerate(runs):
                # TODO: abstract this to higher levels
                os.makedirs(run.run_path, exist_ok=True)

                codes_argv_nprocs = run.get_codes_argv_with_exe_and_nprocs()

                # save code commands as text
                params_path_txt = os.path.join(run.run_path,
                                               self.run_command_name)
                with open(params_path_txt, 'w') as params_f:
                    for argv, _ in codes_argv_nprocs:
                        params_f.write(' '.join(argv))
                        params_f.write('\n')

                # save params as JSON for use in post-processing, more
                # useful for post-processing scripts then the command
                # text
                params_path_json = os.path.join(run.run_path,
                                                self.run_json_name)
                run_data = run.instance.as_dict()
                with open(params_path_json, 'w') as params_f:
                    json.dump(run_data, params_f, indent=2)

                # write a swift string array with variable number of
                # elements, first is the command directory, then pairs
                # of elements with parallelism followed by command to
                # execute.
                f.write('runs[%d] = ["%s"' % (i, run.run_path))
                for argv, nprocs in codes_argv_nprocs:
                    # TODO: this is terrible, only works if args don't
                    # require quoting. Should pass as variable arrays
                    # and just set the lengths at the top for decoding.
                    command_string = ' '.join(argv)
                    f.write(', "%s", "%s"' % (nprocs, ' '.join(argv)))
                f.write('];\n')
            f.write(self.BATCH_FOOTER)
        helpers.make_executable(script_path)
        return script_path

    def write_status_script(self):
        script_path = os.path.join(self.output_directory,
                                   self.status_script_name)
        with open(script_path, 'w') as f:
            f.write(self.STATUS_TEMPLATE.format(
                        jobid_file_name=self.jobid_file_name))
        helpers.make_executable(script_path)
        return script_path

    def write_wait_script(self):
        script_path = os.path.join(self.output_directory,
                                   self.wait_script_name)
        with open(script_path, 'w') as f:
            f.write(self.WAIT_TEMPLATE.format(
                                jobid_file_name=self.jobid_file_name,
                                batch_walltime_name=self.batch_walltime_name))
        helpers.make_executable(script_path)
        return script_path



class SchedulerPBS(Scheduler):
    # TODO: this is broken, just copied and started refactor from pbs
    # module
    name = 'local'
    batch_script_name = 'job.pbs'

    supported_params = ['name', 'project', 'nodes', 'walltime']

    HEADER_TEMPLATE = """#!/bin/bash
#PBS -N {name}
#PBS -A {project}
#PBS -l nodes={nodes}
#PBS -l walltime={walltime}

    """

    # The standard strategy for getting scheduler output files to appear in
    # a certain directory are to cd to that directory before running qsub.
    SUBMIT_TEMPLATE = """#!/bin/bash

cd "{scheduler_directory}"
qsub {batch_script_name}
"""

    def write_batch_script(self, group):
        """
        Open and write a PBS file to the specified path and return the open file
        object for further writing. Caller is responsible for closing the file.

        TODO: rather than passing back a file, this should probably return
        an object with an 'add_run' function. There should also be a template
        for the run output dir set somewhere - maybe other modules handle that,
        it should not be scheduler specific.
        """
        pbs_path = os.path.join(scheduler_dir_path, PBS_NAME)
        f = open(pbs_path, "w")
        f.write(PBS_FORMAT_TEMPLATE.format(name=name, project=project,
                                           nodes=nodes, walltime=walltime))
        return f


    def write_submit_script(self, script_out_path, scheduler_dir_path):
        """
        Write a bash script that will submit a PBS file generated by
        `open_pbs_file` with the correct working directory and enironment.
        This is the end user (experiment runner)'s entry point to start the
        experiment.
        """
        with open(script_out_path, 'w') as f:
            f.write(SUBMIT_FORMAT_TEMPLATE.format(
                        scheduler_directory=scheduler_dir_path,
                        pbs_name=PBS_NAME))
