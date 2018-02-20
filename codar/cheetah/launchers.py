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
import subprocess

from codar.cheetah import adios_params, config, templates
from codar.savanna.parameters import ParamAdiosXML
from codar.cheetah.helpers import parse_timedelta_seconds


TAU_PROFILE_PATTERN = "codar.cheetah.tau-{code}"


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
                               max_nprocs, processes_per_node, nodes,
                               component_subdirs, walltime, node_exclusive,
                               timeout, machine,
                               sosd_path=None,
                               sos_analysis_path=None,
                               tau_config=None,
                               kill_on_partial_failure=False,
                               run_post_process_script=None,
                               run_post_process_stop_on_failure=False,
                               scheduler_options=None,
                               run_dir_setup_script=None):
        """Copy scripts for the appropriate scheduler to group directory,
        and write environment configuration"""
        script_dir = os.path.join(config.CHEETAH_PATH_SCRIPTS,
                                  self.scheduler_name, 'group')
        if not os.path.isdir(script_dir):
            raise ValueError("scheduler '%s' is not yet supported"
                             % self.scheduler_name)
        if scheduler_options is None:
            scheduler_options = {}
        shutil.copytree(script_dir, self.output_directory)
        env_path = os.path.join(self.output_directory, 'group-env.sh')
        group_env = templates.GROUP_ENV_TEMPLATE.format(
            walltime=parse_timedelta_seconds(walltime),
            max_procs=max_nprocs,
            processes_per_node=processes_per_node,
            nodes=nodes,
            node_exclusive=node_exclusive,
            account=scheduler_options.get('project', ''),
            queue=scheduler_options.get('queue', ''),
            # TODO: require name be valid for all schedulers
            campaign_name='codar.cheetah.'+campaign_name,
            group_name=group_name,
            constraint=scheduler_options.get('constraint', ''),
            license=scheduler_options.get('license', '')
        )
        with open(env_path, 'w') as f:
            f.write(group_env)

        fobs_path = os.path.join(self.output_directory, 'fobs.json')
        with open(fobs_path, 'w') as f:
            for i, run in enumerate(runs):
                # TODO: abstract this to higher levels
                os.makedirs(run.run_path, exist_ok=True)

                # Create working dir for each component
                for rc in run.run_components:
                    os.makedirs(rc.working_dir, exist_ok=True)

                if run.sosflow:
                    run.insert_sosflow(sosd_path, sos_analysis_path,
                                       run.run_path, machine.processes_per_node)

                if tau_config is not None:
                    shutil.copy(tau_config, run.run_path)

                # Copy the global input files common to all components
                for input_rpath in run.inputs:
                    shutil.copy2(input_rpath, run.run_path)

                # Copy input files requested by each component
                for rc in run.run_components:
                    if rc.component_inputs is not None:
                        for input_file in rc.component_inputs:
                            file_path = os.path.abspath(os.path.join(
                                                run.codes_path, input_file))
                            shutil.copy(file_path, rc.working_dir)

                # ADIOS XML param support
                adios_xml_params = \
                    run.instance.get_parameter_values_by_type(ParamAdiosXML)
                for pv in adios_xml_params:
                    xml_filepath = os.path.join(run.run_path, pv.xml_filename)
                    if pv.param_type == "adios_transform":
                        adios_params.adios_xml_transform(
                            xml_filepath,pv.group_name, pv.var_name, pv.value)
                    elif pv.param_type == "adios_transport":
                        # value could be
                        # "MPI_AGGREGATE:num_aggregators=64;num_osts"
                        # extract the method name and the method options
                        method_name = pv.value
                        method_opts = ""
                        if ":" in pv.value:
                            value_tokens = pv.value.split(":", 1)
                            method_name = value_tokens[0]
                            method_opts = value_tokens[1]

                        adios_params.adios_xml_transport(
                            xml_filepath, pv.group_name, method_name, method_opts)
                    else:
                        raise "Unrecognized adios param"

                # save code commands as text
                params_path_txt = os.path.join(run.run_path,
                                               self.run_command_name)
                with open(params_path_txt, 'w') as params_f:
                    for rc in run.run_components:
                        params_f.write(' '.join(map(shlex.quote,
                                                    [rc.exe] + rc.args)))
                        params_f.write('\n')

                # save params as JSON for use in post-processing, more
                # useful for post-processing scripts then the command
                # text
                params_path_json = os.path.join(run.run_path,
                                                self.run_json_name)
                run_data = run.get_app_param_dict()
                with open(params_path_json, 'w') as params_f:
                    json.dump(run_data, params_f, indent=2)

                fob_runs = []
                for j, rc in enumerate(run.run_components):

                    tau_profile_dir = os.path.join(run.run_path,
                                TAU_PROFILE_PATTERN.format(code=rc.name))
                    os.makedirs(tau_profile_dir)

                    rc.env["PROFILEDIR"] = tau_profile_dir

                    if timeout is not None:
                        rc.timeout = parse_timedelta_seconds(timeout)

                    fob_runs.append(rc.as_fob_data())

                fob = dict(id=run.run_id, runs=fob_runs,
                           working_dir=run.run_path,
                           kill_on_partial_failure=kill_on_partial_failure,
                           post_process_script=run_post_process_script,
                           post_process_stop_on_failure=
                                run_post_process_stop_on_failure,
                           post_process_args=[params_path_json],
                           node_layout=run.node_layout.as_data_list())
                fob_s = json.dumps(fob)

                # write to file run dir
                run_fob_path = os.path.join(run.run_path,
                                            "codar.cheetah.fob.json")
                with open(run_fob_path, "w") as runf:
                    runf.write(fob_s)
                    runf.write("\n")

                if run_dir_setup_script is not None:
                    self._execute_run_dir_setup_script(run.run_path,
                                                       run_dir_setup_script)

                # append to fob list file in group dir
                f.write(fob_s)
                f.write("\n")

    def _execute_run_dir_setup_script(self, run_dir, script_path):
        """Raises subprocess.CalledProcessError on failure."""
        subprocess.check_call([script_path], cwd=run_dir)

    def read_jobid(self):
        jobid_file_path = os.path.join(self.output_directory,
                                       self.jobid_file_name)
        with open(jobid_file_path) as f:
            jobid = f.read()
        return jobid


