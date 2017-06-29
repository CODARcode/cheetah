"""
Class model for "launchers", which are responsible for taking an application
and mediating how it is run on a super computer or local machine. The only
supported launcher currently is swift-t. Swift allows us to configure how
each run within a sweep is parallelized, and handles details of submitting to
the correct scheduler and runner when passed appropriate options.
"""
import os
import json

from shutil import copy2

from codar.cheetah import adios_transform
from codar.cheetah.parameters import ParamAdiosXML
from codar.cheetah.helpers import make_executable, swift_escape_string


class Launcher(object):
    """
    Abstract class to represent a single batch job or submission script.
    It's job is to take a scheduler group and produce a script for executing
    all runs within the scheduler group with the indicated scheduler
    parameters.

    The launcher may take configuration parameters to specify which scheduler/
    runner to use, but there is no longer an object model for schedulers and
    runners, because we are mainly interested in using swift-t which can target
    different environments with simple command line args.
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

    def __init__(self, scheduler_name, runner_name,
                 output_directory, num_codes):
        self.scheduler_name = scheduler_name
        self.runner_name = runner_name
        self.output_directory = output_directory
        self.num_codes = num_codes

    def write_submit_script(self, max_nprocs):
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


class LauncherSwift(Launcher):
    """
    Launcher that generates swift-t script and bash scripts for executing
    with appropriate options.

    TODO: currently all output goes to swift script output, need to capture
    individual run output.
    """
    name = 'swift'
    batch_script_name = 'run.swift'

    # TODO: add subclasses for pbs and slurm that pass appropriate
    # option to swift-t
    SUBMIT_TEMPLATE = """#!/bin/bash

cd {group_directory}
nohup swift-t {swift_options} -p {batch_script_name} >{submit_out_name} 2>&1 &
PID=$!
echo "{name}:$PID" > {jobid_file_name}
"""

    SUBMIT_TEMPLATE_LAUNCH_MULTI = """#!/bin/bash

cd {group_directory}
stc -p -u -I {swift_launch_multi} -r {swift_launch_multi} run.swift
nohup turbine -n {turbine_nprocs} {swift_options} run.tic >{submit_out_name} 2>&1 &
PID=$!
echo "{name}:$PID" > {jobid_file_name}
"""


    BATCH_HEADER = """
import io;
import string;

// Each row is
// [RUN_PATH, NAME1, NPROCS1, PROG1, PROG1ARG1, PROG2ARG2, ...
//  NAME2, NPROCS2, PROG2, PROG2ARG1,...]
// Note that each program may have different number of args.
string runs[][];

// Filled in for the sweep group, specifies number of args for each program,
// and the offsets into runs where each program starts. Note that one can
// be inferred from the other in a serial program, but in swift it's
// problematic not to know both ahead of time.
int num_args[];
int prog_offsets[];

"""

    BATCH_FOOTER = """

(int exit_code, string error_message) system(string work_dir, string cmd,
                                             string out_prefix)
"turbine" "1.0"
[
\"\"\"
set oldpwd [ pwd ]
cd <<work_dir>>
set cmd_tokens <<cmd>>
set <<error_message>> ""
set <<exit_code>> 0
set out_prefix <<out_prefix>>
set stdout_path "$out_prefix.stdout"
set stderr_path "$out_prefix.stderr"
if [ catch { exec "/bin/bash" "-c" $cmd_tokens > $stdout_path 2> $stderr_path } e info ] {
  if [ dict exists $info -error ] {
    set <<exit_code>> [ dict get $info -error ]
  } else {
    set <<exit_code>> [ dict get $info -code ]
  }
  set <<error_message>> "$e"
}
cd $oldpwd
\"\"\"
];

(int exit_code, string error_message) mock_system(string work_dir, string cmd,
                                                  string out_prefix)
{
    printf("[%s/%s] %s", work_dir, out_prefix, cmd);
    exit_code = 0;
    error_message = "";
}

(int exit_codes[], string error_messages[]) launch_multi(
                                string work_dir, string procs[],
                                string progs[], string args[][])
{
    for (int i=0; i < num_progs; i=i+1)
    {
        string quoted_args[];

        // Attempt to quote args for shell system call in tcl. Since this is a
        // placeholder implementation, not worth trying to make it perfect.
        for (int j=0; j<size(args[i]); j=j+1)
        {
            quoted_args[j] = "\\"" + replace_all(args[i][j], "\\"", "\\\\\\"", 0)
                           + "\\"";
        }
        string cmd = progs[i] + " " + string_join(quoted_args, " ");
        string out_prefix = "codar.cheetah." + fromint(i);
        if (use_mock_system)
        {
            (exit_codes[i], error_messages[i]) = mock_system(work_dir, cmd,
                                                             out_prefix);
        }
        else
        {
            (exit_codes[i], error_messages[i]) = system(work_dir, cmd,
                                                        out_prefix);
        }
    }
}

int run_exit_codes[][];
string run_error_messages[][];

for (int i=0; i<size(runs); i=i+1)
{
    dir_name = runs[i][0];
    string nprocs[];
    string progs[];
    string args[][];

    for (int j=0; j<num_progs; j=j+1)
    {
        // NB: the logical name is at prog_offsets[j], which is unused by this
        // script
        nprocs[j] = runs[i][prog_offsets[j]+1];
        progs[j] = runs[i][prog_offsets[j]+2];
        for (int k=0; k<num_args[j]; k=k+1)
        {
            args[j][k] = runs[i][prog_offsets[j]+3+k];
        }
    }
    (run_exit_codes[i], run_error_messages[i]) = launch_multi(dir_name, nprocs,
                                                              progs, args);
}


for (int i=0; i<size(runs); i=i+1)
{
    for (int j=0; j<num_progs; j=j+1)
    {
        printf("[%d] %d (%s)", i,
               run_exit_codes[i][j], run_error_messages[i][j]);
    }
}
"""

    BATCH_FOOTER_LAUNCH_MULTI = """

int launch_return_codes[];

for (int i=0; i<size(runs); i=i+1)
{
    dir_name = runs[i][0];
    int nprocs[];
    string progs[];
    string argv[][];
    string envs[][];

    for (int j=0; j<num_progs; j=j+1)
    {
        nprocs[j] = toint(runs[i][prog_offsets[j]+1]);
        progs[j] = "CHEETAH_LAUNCH";
        argv[j][0] = dir_name;
        argv[j][1] = runs[i][prog_offsets[j]]; // logical prog name
        argv[j][2] = runs[i][prog_offsets[j]+2]; // prog exe
        for (int k=3; k<num_args[j]+3; k=k+1)
        {
            string arg = runs[i][prog_offsets[j]+k];
            if (strlen(arg) == 0)
            {
                // workaround for bug in launch_multi that misses empty args
                argv[j][k] = "\\"\\"";
            }
            else
            {
                argv[j][k] = arg;
            }
        }
    }
    launch_return_codes[i] = @par=sum_integer(nprocs) launch_multi(nprocs,
                                                           progs, argv, envs);
}


for (int i=0; i<size(runs); i=i+1)
{
    printf("[%d] %d", i, launch_return_codes[i]);
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

    def write_submit_script(self, max_nprocs):
        submit_path = os.path.join(self.output_directory,
                                   self.submit_script_name)
        swift_options = ""
        if self.scheduler_name == "PBS":
            # TODO: untested stub for how we might do this. Note that we may
            # still need to maintain a Runner model, still wrapping my
            # head around what Swift provides for that.
            swift_options = "-m pbs"

        if self.runner_name == "launch_multi":
            mpix_launch_path = os.getenv('CODAR_MPIX_LAUNCH')
            if mpix_launch_path is None:
                raise ValueError("Missing required env var CODAR_MPIX_LAUNCH")
            # the lib actually lives in the src subdir
            mpix_launch_path = os.path.join(mpix_launch_path, 'src')
            body = self.SUBMIT_TEMPLATE_LAUNCH_MULTI.format(
                        group_directory=self.output_directory,
                        batch_script_name=self.batch_script_name,
                        submit_out_name=self.submit_out_name,
                        jobid_file_name=self.jobid_file_name,
                        name=self.name,
                        swift_options=swift_options,
                        # TODO: hacky, add site specific cheetah config file
                        # for this?
                        swift_launch_multi=mpix_launch_path,
                        turbine_nprocs=max_nprocs+1) # NB: +1 for ADLB master
        else:
            body = self.SUBMIT_TEMPLATE.format(
                        group_directory=self.output_directory,
                        batch_script_name=self.batch_script_name,
                        submit_out_name=self.submit_out_name,
                        jobid_file_name=self.jobid_file_name,
                        name=self.name,
                        swift_options=swift_options)

        with open(submit_path, 'w') as f:
             f.write(body)
        make_executable(submit_path)
        return submit_path

    def write_batch_script(self, runs, mock=False):
        script_path = os.path.join(self.output_directory,
                                   self.batch_script_name)
        prog_offsets_written = False
        with open(script_path, 'w') as f:
            if self.runner_name == "launch_multi":
                f.write('import launch;\nimport stats;\n')
            f.write(self.BATCH_HEADER)
            if mock:
                f.write('boolean use_mock_system = true;\n')
            else:
                f.write('boolean use_mock_system = false;\n')
            f.write('int num_progs = %d;\n' % self.num_codes)
            for i, run in enumerate(runs):
                # TODO: abstract this to higher levels
                os.makedirs(run.run_path, exist_ok=True)

                for input_rpath in run.inputs:
                    copy2(input_rpath, run.run_path+"/.")

                codes_argv_nprocs = run.get_codes_argv_with_exe_and_nprocs()

                # ADIOS XML param support
                adios_transform_params = \
                    run.instance.get_parameter_values_by_type(ParamAdiosXML)
                for pv in adios_transform_params:
                    xml_filepath = os.path.join(run.run_path, pv.xml_filename)
                    adios_transform.adios_xml_transform(xml_filepath,
                                        pv.group_name, pv.var_name, pv.value)

                if not prog_offsets_written:
                    offset = 1 # skip first element which is working directory
                    for j, (_, argv, _) in enumerate(codes_argv_nprocs):
                        f.write('num_args[%d] = %d;\n' % (j, len(argv)-1))
                        f.write('prog_offsets[%d] = %d;\n' % (j, offset))
                        # next prog starts after name, nprocs, prog, and args
                        # of current prog
                        offset += 2 + len(argv)
                    prog_offsets_written = True

                # save code commands as text
                params_path_txt = os.path.join(run.run_path,
                                               self.run_command_name)
                with open(params_path_txt, 'w') as params_f:
                    for _, argv, _ in codes_argv_nprocs:
                        params_f.write(' '.join(argv))
                        params_f.write('\n')

                # save params as JSON for use in post-processing, more
                # useful for post-processing scripts then the command
                # text
                params_path_json = os.path.join(run.run_path,
                                                self.run_json_name)
                run_data = run.as_dict()
                with open(params_path_json, 'w') as params_f:
                    json.dump(run_data, params_f, indent=2)

                # write a swift string array with variable number of
                # elements, first is the command directory, then list
                # of elements with parallelism followed by command
                # followed by a variable number of args.
                f.write('runs[%d] = ["%s"'
                        % (i, swift_escape_string(run.run_path)))
                for j, (pname, argv, nprocs) in enumerate(codes_argv_nprocs):
                    quoted_argv = ['"%s"' % swift_escape_string(arg)
                                   for arg in argv]
                    f.write(', "%s", ' % pname)
                    f.write('"%d", ' % nprocs)
                    f.write(', '.join(quoted_argv))
                f.write('];\n')
            if self.runner_name == "launch_multi":
                bin_path = os.path.normpath(os.path.join(
                                        os.path.dirname(__file__),
                                        '..', '..', 'scripts'))
                # TODO: hacky, add this path to a cheetah site config?
                f.write(self.BATCH_FOOTER_LAUNCH_MULTI.replace(
                    "CHEETAH_LAUNCH",
                    os.path.join(bin_path, 'cheetah-launch.sh'))
                )
            else:
                f.write(self.BATCH_FOOTER)
        make_executable(script_path)
        return script_path

    def write_status_script(self):
        script_path = os.path.join(self.output_directory,
                                   self.status_script_name)
        with open(script_path, 'w') as f:
            f.write(self.STATUS_TEMPLATE.format(
                        jobid_file_name=self.jobid_file_name))
        make_executable(script_path)
        return script_path

    def write_wait_script(self):
        script_path = os.path.join(self.output_directory,
                                   self.wait_script_name)
        with open(script_path, 'w') as f:
            f.write(self.WAIT_TEMPLATE.format(
                                jobid_file_name=self.jobid_file_name,
                                batch_walltime_name=self.batch_walltime_name))
        make_executable(script_path)
        return script_path
