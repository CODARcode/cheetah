"""
Class model for "launchers", which are responsible for taking an application
and mediating how it is run on a super computer or local machine. The only
supported launcher currently is swift-t. Swift allows us to configure how
each run within a sweep is parallelized, and handles details of submitting to
the correct scheduler and runner when passed appropriate options.
"""
import os
import json
import shlex
import shutil

from codar.cheetah import adios_transform, config, templates
from codar.cheetah.parameters import ParamAdiosXML
from codar.cheetah.helpers import make_executable, swift_escape_string, \
    parse_timedelta_seconds


class Launcher(object):
    """
    Class to represent a single batch job or submission script.
    It's job is to take a scheduler group and produce a script for executing
    all runs within the scheduler group with the indicated scheduler
    parameters.

    The launcher may take configuration parameters to specify which scheduler/
    runner to use, but there is no longer an object model for schedulers and
    runners.
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

    def __init__(self, machine_name, scheduler_name, runner_name,
                 output_directory, num_codes):
        self.machine_name = machine_name
        self.scheduler_name = scheduler_name
        self.runner_name = runner_name
        self.output_directory = output_directory
        self.num_codes = num_codes

    def create_group_directory(self, campaign_name, group_name, runs,
                               max_nprocs, processes_per_node, queue, nodes,
                               project, walltime, node_exclusive,
                               timeout):
        """Copy scripts for the appropriate scheduler to group directory,
        and write environment configuration"""
        script_dir = os.path.join(config.CHEETAH_PATH_SCRIPTS,
                                  self.scheduler_name, 'group')
        if not os.path.isdir(script_dir):
            raise ValueError("scheduler '%s' is not yet supported"
                             % self.scheduler_name)
        shutil.copytree(script_dir, self.output_directory)
        env_path = os.path.join(self.output_directory, 'group-env.sh')
        group_env = templates.GROUP_ENV_TEMPLATE.format(
            walltime=parse_timedelta_seconds(walltime),
            max_procs=max_nprocs,
            processes_per_node=processes_per_node,
            nodes=nodes,
            node_exclusive=node_exclusive,
            account=project,
            queue=queue,
            # TODO: require name be valid for all schedulers
            campaign_name='codar.cheetah.'+campaign_name,
            group_name=group_name
        )
        with open(env_path, 'w') as f:
            f.write(group_env)

        fobs_path = os.path.join(self.output_directory, 'fobs.json')
        with open(fobs_path, 'w') as f:
            for i, run in enumerate(runs):
                # TODO: abstract this to higher levels
                os.makedirs(run.run_path, exist_ok=True)

                for input_rpath in run.inputs:
                    shutil.copy2(input_rpath, run.run_path+"/.")

                codes_argv_nprocs = run.get_codes_argv_with_exe_and_nprocs()

                # ADIOS XML param support
                adios_transform_params = \
                    run.instance.get_parameter_values_by_type(ParamAdiosXML)
                for pv in adios_transform_params:
                    xml_filepath = os.path.join(run.run_path, pv.xml_filename)
                    adios_transform.adios_xml_transform(xml_filepath,
                                        pv.group_name, pv.var_name, pv.value)

                # save code commands as text
                params_path_txt = os.path.join(run.run_path,
                                               self.run_command_name)
                with open(params_path_txt, 'w') as params_f:
                    for _, argv, _, _ in codes_argv_nprocs:
                        params_f.write(' '.join(map(shlex.quote, argv)))
                        params_f.write('\n')

                # save params as JSON for use in post-processing, more
                # useful for post-processing scripts then the command
                # text
                params_path_json = os.path.join(run.run_path,
                                                self.run_json_name)
                run_data = run.as_dict()
                with open(params_path_json, 'w') as params_f:
                    json.dump(run_data, params_f, indent=2)

                fob = []
                for j, (pname, argv, nprocs, sleep_after) in enumerate(
                                                            codes_argv_nprocs):
                    # TODO: add env for tau
                    data = dict(name=pname,
                                exe=argv[0],
                                args=argv[1:],
                                working_dir=run.run_path,
                                nprocs=nprocs,
                                sleep_after=sleep_after)
                    if timeout is not None:
                        data["timeout"] = parse_timedelta_seconds(timeout)
                    fob.append(data)
                f.write(json.dumps(fob))
                f.write("\n")


    def read_jobid(self):
        jobid_file_path = os.path.join(self.output_directory,
                                       self.jobid_file_name)
        with open(jobid_file_path) as f:
            jobid = f.read()
        return jobid
