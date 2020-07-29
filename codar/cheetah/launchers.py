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
import subprocess
import math
import pdb

from codar.cheetah import adios_params, config, templates, exc
from codar.cheetah.parameters import ParamAdiosXML, ParamADIOS2XML, \
    ParamConfig, ParamKeyValue, ParamEnvVar
from codar.cheetah.helpers import parse_timedelta_seconds
from codar.cheetah.helpers import copy_to_dir, copytree_to_dir, dir_size, \
    json_config_set_option, relative_or_absolute_path, copy_to_path
from codar.cheetah.parameters import SymLink
from codar.cheetah.adios2_interface import get_adios_version
from codar.cheetah import adios2_interface as adios2


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

    def create_group_directory(self, campaign_name, app_dir, group_name, runs,
                               max_nprocs, nodes, launch_mode,
                               component_subdirs, walltime, node_exclusive,
                               timeout, machine,
                               sosd_path=None,
                               sos_analysis_path=None,
                               tau_profiling=False, tau_tracing=False,
                               kill_on_partial_failure=False,
                               run_post_process_script=None,
                               run_post_process_stop_on_failure=False,
                               scheduler_options=None,
                               run_dir_setup_script=None):
        """Copy scripts for the appropriate scheduler to group directory,
        and write environment configuration. Returns required number of nodes,
        which will be calculated if the passed nodes is None"""
        script_dir = os.path.join(config.CHEETAH_PATH_SCHEDULER,
                                  self.scheduler_name, 'group')
        if not os.path.isdir(script_dir):
            raise ValueError("scheduler '%s' is not yet supported (path '%s')"
                             % (self.scheduler_name, script_dir))
        if scheduler_options is None:
            scheduler_options = {}
        copytree_to_dir(script_dir, self.output_directory)

        fobs_path = os.path.join(self.output_directory, 'fobs.json')
        min_nodes = 1

        f = open(fobs_path, 'w')
        fob_list = []
        for i, run in enumerate(runs):
            # TODO: abstract this to higher levels
            os.makedirs(run.run_path, exist_ok=True)

            # Create working dir for each component
            for rc in run.run_components:
                os.makedirs(rc.working_dir, exist_ok=True)

            if run.sosflow_profiling:
                run.insert_sosflow(sosd_path, sos_analysis_path,
                                   run.run_path,
                                   machine.processes_per_node)

            # Copy the global input files common to all components
            for input_rpath in run.inputs:
                copy_to_dir(input_rpath, run.run_path)

            # Copy input files requested by each component
            # save working dirs for later use
            working_dirs = {} # map component name to path
            for rc in run.run_components:
                working_dirs[rc.name] = rc.working_dir

                # if rc has an adios xml file, copy it to working dir
                if rc.adios_xml_file:
                    copy_to_dir(rc.adios_xml_file, rc.working_dir)

                # now copy other inputs marked under component_inputs
                if rc.component_inputs is not None:
                    for input_file in rc.component_inputs:
                        dest = os.path.join(rc.working_dir,
                                            os.path.basename(
                                                input_file))
                        # input type is symlink
                        if type(input_file) == SymLink:
                            os.symlink(input_file, dest)

                        # input type is a regular file
                        elif os.path.isfile(input_file):
                            copy_to_dir(input_file, rc.working_dir)

                        # Input file is a directory
                        elif os.path.isdir(input_file):
                            copytree_to_dir(input_file, dest)

                        else:
                            raise exc.CheetahException \
                                ("Could not component input {}"
                                 .format(input_file))

            # ADIOS XML param support
            adios_xml_params = \
                run.instance.get_parameter_values_by_type(ParamAdiosXML) or \
                run.instance.get_parameter_values_by_type(ParamADIOS2XML)
            for pv in adios_xml_params:
                working_dir = working_dirs[pv.target]

                # dirty way of getting the adios xml filename of the rc
                # that is represented by pv.target
                rc_adios_xml = self._get_rc_adios_xml_filename(
                    run, pv.target)
                xml_filepath = os.path.join(working_dir,
                                            os.path.basename(rc_adios_xml))

                # Check if this is adios1 or adios2
                adios_version = get_adios_version(rc_adios_xml)

                if adios_version == 1:
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
                            xml_filepath, pv.group_name, method_name,
                            method_opts)
                    else:
                        raise exc.CheetahException("Unrecognized adios param")

                else:   # adios version == 2
                    operation_value = list(pv.value.keys())[0]
                    if pv.operation_name in ('engine', 'transport'):
                        parameters = list(pv.value.values())[0]
                        if pv.operation_name == 'engine':
                            adios2.set_engine(xml_filepath, pv.io_name,
                                              operation_value, parameters)
                        else:
                            adios2.set_transport(xml_filepath, pv.io_name,
                                                 operation_value, parameters)
                    else:   # operation_name == 'var_operation'
                        var_name = list(pv.value.keys())[0]
                        var_name_dict = pv.value[var_name]
                        var_operation_value = list(var_name_dict.keys())[0]
                        var_op_dict = var_name_dict[var_operation_value]
                        parameters = var_op_dict
                        adios2.set_var_operation(xml_filepath, pv.io_name,
                                                 var_name,
                                                 var_operation_value,
                                                 parameters)

            # Calculate the no. of nodes required by this run.
            # This must be done after dataspaces support is added.
            if run.total_nodes > min_nodes:
                min_nodes = run.total_nodes

            # Generic config file support. Note: slurps entire
            # config file into memory, requires adding file to
            # campaign 'inputs' option.
            config_params = \
                run.instance.get_parameter_values_by_type(ParamConfig)
            for pv in config_params:
                working_dir = working_dirs[pv.target]
                src_filepath = relative_or_absolute_path(app_dir,
                                                         pv.config_filename)
                # Allow for relative pathnames in the spec
                src_filename = pv.config_filename
                if pv.config_filename[0] == '/':
                    src_filename = os.path.basename(src_filepath)
                config_filepath = os.path.join(working_dir,
                                               src_filename)
                if not os.path.isfile(config_filepath):
                    copy_to_path(src_filepath, config_filepath)
                lines = []
                # read and modify lines
                # hack: handle json files. currently works only on singly
                # nested json files
                if config_filepath.endswith(".json"):
                    json_config_set_option(config_filepath, pv.match_string,
                                           pv.value)
                else:  # handle other file types
                    with open(config_filepath) as config_f:
                        for line in config_f:
                            line = line.replace(pv.match_string, pv.value)
                            lines.append(line)
                    # rewrite file with modified lines
                    with open(config_filepath, 'w') as config_f:
                        config_f.write("".join(lines))

            # Key value config file support. Note: slurps entire
            # config file into memory, requires adding file to
            # campaign 'inputs' option.
            kv_params = \
                run.instance.get_parameter_values_by_type(ParamKeyValue)
            for pv in kv_params:
                working_dir = working_dirs[pv.target]
                src_filepath = relative_or_absolute_path(app_dir,
                                                         pv.config_filename)
                # Allow for relative pathnames in the spec
                src_filename = pv.config_filename
                if pv.config_filename[0] == '/':
                    src_filename = os.path.basename(src_filepath)
                kv_filepath = os.path.join(working_dir, src_filename)
                if not os.path.isfile(kv_filepath):
                    copy_to_path(src_filepath, kv_filepath)
                lines = []
                # read and modify lines
                key_found = False
                with open(kv_filepath) as kv_f:
                    for line in kv_f:
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            k = parts[0].strip()
                            if k == pv.key_name:
                                # assume all k=v type formats will
                                # support no spaces around equals
                                line = k + '=' + str(pv.value)
                                # preserve a user comment if it exists
                                if '!' in parts[1]:
                                    line = line + " !" + \
                                           parts[1].strip().split('!')[1]
                                line = line + '\n'
                                key_found = True
                        lines.append(line)
                    assert key_found, \
                        "Issue parsing a ParamKeyValue: Could not find key {}"\
                        " in config file {}".format(pv.key_name, src_filepath)
                # rewrite file with modified lines
                with open(kv_filepath, 'w') as kv_f:
                    kv_f.write("".join(lines))

            # Env var parameter values
            kv_params = run.instance.get_parameter_values_by_type(ParamEnvVar)
            for pv in kv_params:
                rc = run._get_rc_by_name(pv.target)
                rc.env[pv.option] = str(pv.value)

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
                if timeout is not None:
                    rc.timeout = parse_timedelta_seconds(timeout)

                fob_runs.append(rc.as_fob_data())

            fob = dict(id=run.run_id, launch_mode=launch_mode, runs=fob_runs,
                       working_dir=run.run_path, apps_dir=app_dir,
                       kill_on_partial_failure=kill_on_partial_failure,
                       post_process_script=run_post_process_script,
                       post_process_stop_on_failure=
                            run_post_process_stop_on_failure,
                       post_process_args=[params_path_json],
                       node_layout=run.node_layout.serialize_to_dict(),
                       total_nodes=run.total_nodes,
                       machine_name=machine.name,
                       tau_profiling=tau_profiling, tau_tracing=tau_tracing)
            fob_list.append(fob)

            # write to file run dir
            run_fob_path = os.path.join(run.run_path,
                                        "codar.cheetah.fob.json")
            with open(run_fob_path, "w") as runf:
                runf.write(json.dumps(fob, sort_keys=True, indent=4))
                runf.write("\n")

            if run_dir_setup_script is not None:
                self._execute_run_dir_setup_script(run.run_path,
                                                   run_dir_setup_script)

            # Get the size of the run dir. This should be the last step
            # in the creation of the run dir.
            self._get_pre_submit_dir_size(run)

        # Write fob_list to group-level json file
        f.write(json.dumps(fob_list, sort_keys=True, indent=4))
        f.close()

        if nodes is None:
            nodes = min_nodes
        elif nodes < min_nodes:
            raise exc.CheetahException(
                "nodes for group is too low, need at least %d, got %d"
                % (min_nodes, nodes))

        # TODO: what case does this handle? should have a test case for
        # it.
        if machine.node_exclusive:
            group_ppn = machine.processes_per_node
        else:
            group_ppn = math.ceil((max_nprocs) / nodes)

        env_path = os.path.join(self.output_directory, 'group-env.sh')
        group_env = templates.GROUP_ENV_TEMPLATE.format(
            walltime=parse_timedelta_seconds(walltime),
            max_procs=max_nprocs,
            processes_per_node=group_ppn,
            nodes=nodes,
            node_exclusive=node_exclusive,
            account=scheduler_options.get('project', ''),
            queue=scheduler_options.get('queue', ''),
            reservation=scheduler_options.get('reservation', ''),
            # TODO: require name be valid for all schedulers
            campaign_name='codar.cheetah.'+campaign_name,
            group_name=group_name,
            constraint=scheduler_options.get('constraint', ''),
            license=scheduler_options.get('license', ''),
            machine_name=machine.name
        )
        with open(env_path, 'w') as f:
            f.write(group_env)

        return nodes

    def _get_pre_submit_dir_size(self, run):
        """
        Get and write the size of the run directory prior to running the
        campaign. This will be needed to calculate the size of the data
        output by the experiment.
        Write byte count to file .codar.cheetah.pre_submit_dir_size.out
        :param run: Object of type Run
        """

        run_dir_size = dir_size(run.run_path)
        # add length of the file that will be written below
        run_dir_size += len(str(run_dir_size))

        # write dir size to a file in the run dir
        f_out = os.path.join(run.run_path, run._pre_submit_dir_size_fname)
        with open(f_out, 'w') as f:
            f.write(str(run_dir_size))

    def _execute_run_dir_setup_script(self, run_dir, script_path):
        """Raises subprocess.CalledProcessError on failure."""
        subprocess.check_call([script_path], cwd=run_dir)

    def _get_rc_adios_xml_filename(self, run, rc_name):
        adios_xml_file = None
        for rc in run.run_components:
            if rc_name == rc.name:
                adios_xml_file = rc.adios_xml_file

        if adios_xml_file is None:
            raise exc.CheetahException("An ADIOS XML file was not found "
                                       "for {}. Set the adios_xml_file "
                                       "option for the component in "
                                       "codes.".format(rc_name))
        return adios_xml_file

    def read_jobid(self):
        jobid_file_path = os.path.join(self.output_directory,
                                       self.jobid_file_name)
        with open(jobid_file_path) as f:
            jobid = f.read()
        return jobid


