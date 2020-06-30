"""
Generate performance report from a completed campaign.
This module parses all run directories in all sweep groups to aggregate
information.
Runs sosflow analysis to collect data.

All parameters specified in the spec file must be used as column headers in
an output csv file.
"""

import os
import sys
from pathlib import Path
import json
import pdb
import logging
import csv
import subprocess
import shutil
from codar.cheetah.helpers import get_immediate_subdirs, \
                                  require_campaign_directory, find_subdir_path
from codar.cheetah.error_messages import e_msg
from codar.savanna import tau

_log = logging.getLogger(' ')


class _RunParser:
    def __init__(self, run_dir, exit_status, user_run_script, tau_metrics):
        """
        Class to parse a run directory.
        :param run_dir:
        """

        self.run_dir = run_dir
        self.exit_status = exit_status
        self.user_run_script = user_run_script
        self.tau_metrics = tau_metrics

        self.serialized_run_params = {}
        self.fob_dict = {}
        self.rc_names = []
        self.rc_working_dir = {}

        # sos_flow sees exes in the perf data that it collects. Form a
        # mapping of rc_exe:rc_name so that we can get the rc_name from the
        # exe from sos data
        self.rc_name_exe = {}

        # Store the run's exit status as a column in the csv output
        self.serialized_run_params['exit_status'] = self.exit_status

        _log.debug("Parsing run {}".format(run_dir))

    def read_fob_json(self):
        fob_json_filename = os.path.join(self.run_dir,
                                         "codar.cheetah.fob.json")
        with open(fob_json_filename, 'r') as f:
            self.fob_dict = json.load(f)

    def get_rc_names(self):
        # Get rc names
        for rc in self.fob_dict['runs']:
            rc_name = rc['name']
            rc_exe_name = rc['exe']
            rc_working_dir = rc['working_dir']
            self.rc_names.append(rc_name)
            self.rc_working_dir[rc_name] = rc_working_dir

            # sos_flow sees an rc exe as
            # '/var/opt/cray/alps/spool/16406362/xgc-es+tau', whereas
            # cheetah sees
            # '/lustre/atlas/proj-shared/csc143/kmehta/xgc/xgc-es+tau'.
            # That is, the exe paths are different. So, just get the rc_exe
            # name and not the path as the key. e.g. "xgc-es+tau":"xgc"
            exe_basename = os.path.basename(rc_exe_name)
            self.rc_name_exe[exe_basename] = rc_name

    def get_run_params(self):
        # Now form dict of user codes and run params by reading
        # codar.cheetah.run-params.json.

        run_params_json_filename = os.path.join(self.run_dir,
                                               "codar.cheetah.run-params.json")
        with open(run_params_json_filename, "r") as f:
            run_params_dict = json.load(f)

        # Serialize nested dict and add to list of parsed run dicts
        self.serialize_params_nested_dict(run_params_dict)

    def get_cheetah_perf_data(self, run_dir):
        """
        Read codar.savanna.total.workflow and the codar.workflow.walltime.<rc>
        files
        """

        # Get the total workflow runtime
        total_runtime = "N/A"
        total_time_fname = "codar.savanna.total.walltime"
        total_runtime_path = os.path.join(run_dir, total_time_fname)
        if os.path.isfile(total_runtime_path):
            with open(total_runtime_path) as f:
                line = f.readline()
                total_runtime = str(round(float(line),2))

        # Write the total time
        total_time_key = 'total_workflow_walltime_savanna'
        self.serialized_run_params[total_time_key] = total_runtime

        # Get the runtimes of individual components apps
        for rc_name in self.rc_names:
            walltime_fname = "codar.workflow.walltime." + rc_name
            filepath = os.path.join(run_dir, walltime_fname)
            #pdb.set_trace()
            if os.path.isfile(filepath):
            # if Path(filepath).is_file():
                with open(filepath) as f:
                    line = f.readline()
                walltime_str = str(round(float(line), 2))
                self.serialized_run_params[rc_name + "__walltime_savanna"] =\
                    walltime_str

        _log.debug("Cheetah perf data obtained in {}".format(run_dir))

    def read_adios_output_file_sizes(self):
        """

        :return:
        """

        # @TODO: The name of the file must be fetched from somewhere
        md_fname = ".codar.adios_file_sizes.out.json"
        adios_filesizes_json = os.path.join(self.run_dir, md_fname)
        if Path(adios_filesizes_json).is_file():
            with open(adios_filesizes_json, 'r') as f:
                adios_sizes_d = json.load(f)
            file_count = 0
            for key, value in adios_sizes_d.items():
                file_count = file_count + 1
                new_key = "adios_file_" + str(file_count)
                self.serialized_run_params[new_key] = key
                size_key = new_key + "_size"
                self.serialized_run_params[size_key] = value
            _log.debug("Read output adios file sizes")
        else:
            _log.debug("Adios output file size data not found")

    def read_node_layout(self):
        """

        :return:
        """
        for rc_layout_d in (self.fob_dict.get('node_layout') or []):
            rc_name_layout = list(rc_layout_d.items())[0]
            if 'sosflow_aggregator' not in rc_name_layout[0]:
                node_layout_key = 'node_layout_' + rc_name_layout[0]
                self.serialized_run_params[node_layout_key] = rc_name_layout[1]

    def collect_tau_metrics(self):
        """
        Run pprof and write to pprof.out in each run directory if tau
        profiling was turned ON. Run tau utilities to create trace.otf if
        tracing was turned ON.
        """

        # Profiling ON
        if self.fob_dict['tau_profiling']:
            for rc_name in self.rc_names:
                profile_dir_name= tau.TAU_PROFILE_PATTERN.format(rc_name)
                profile_dir_path = find_subdir_path(self.run_dir,
                                                    profile_dir_name)
                if not profile_dir_path:
                    _log.debug("No tau profiles found for {}".format(rc_name))
                    continue

                _log.debug("Tau profiles found for {}".format(rc_name))

                if not shutil.which('pprof'):
                    _log.warning(e_msg['PPROF_NOT_FOUND'])
                    return

                pprof_out = os.path.join(profile_dir_path, "pprof.out")
                pprof_out_f = open(pprof_out, "w")
                subprocess.run(["pprof"], cwd=profile_dir_path,
                               stdout=pprof_out_f, stderr=pprof_out_f)

        else:
            _log.debug("No TAU profiles found")

        # Tracing ON
        if self.fob_dict['tau_tracing']:
            for rc_name in self.rc_names:
                trace_dir_name = tau.TAU_TRACE_PATTERN.format(rc_name)
                trace_dir_path = find_subdir_path(self.run_dir,
                                                    trace_dir_name)
                if not trace_dir_path:
                    _log.debug("No tau traces found for {}".format(rc_name))
                    continue

                trace_out = os.path.join(trace_dir_path, "trace.out")
                trace_out_f = open(trace_out, "w")

                # Run tau_treemerge.pl
                if not shutil.which('tau_treemerge.pl'):
                    _log.warning(e_msg['TAU_TREEMERGE_NOT_FOUND'])
                    return

                subprocess.run(['tau_treemerge.pl'], cwd=trace_dir_path,
                               stdout=trace_out_f, stderr=trace_out_f)

                # Run tau2otf
                otf_args = ["tau2otf", "tau.trc", "tau.edf", "trace.otf"]
                subprocess.run(otf_args, cwd=trace_dir_path,
                               stdout=trace_out_f, stderr=trace_out_f)
            
                _log.debug("Tau traces found for {}".format(rc_name))
        else:
            _log.debug("No TAU traces found")

    def execute_user_run_script(self):
        if self.user_run_script is not None:
            subprocess.check_call(os.path.abspath(self.user_run_script),
                                  cwd=self.run_dir)

        user_file = os.path.join(self.run_dir, "cheetah_user_report.json")

        try:
            with open(user_file) as f:
                user_report_d = json.load(f)
                _log.debug('Found cheetah_user_report.json')
        except:
            _log.debug("No cheetah_user_report.json found")
            return

        for key,value in user_report_d.items():
            self.serialized_run_params[key] = value

    def serialize_params_nested_dict(self, nested_run_params_dict):
        """
        codar.cheetah.run-params.json has the structure:
        {
            app1: {
                param1: value1
                param2: value2
            }
            app2: {
                param1: value1
                param2: value2
            }
        }

        Serialize this structure so that we have
        {app1__param1: value1, app1__param2:value2, and so on}.
        """
        for key in nested_run_params_dict:
            for nested_key in nested_run_params_dict[key]:
                new_key = key + "__" + nested_key
                self.serialized_run_params[new_key] = \
                    nested_run_params_dict[key][nested_key]


class _ReportGenerator:
    """

    """
    def __init__(self, campaign_directory, user_run_script,
                 tau_metrics, output_filename):
        # A list of dicts. Each dict contains metadata and performance
        # information about the run
        self.parsed_runs = []

        # Unique application parameters that will be used as headers for csv
        #  output
        self.unique_keys = set()

        self.campaign_directory = campaign_directory

        # A user-defined script that must be run in each run directory to
        # get additional results. Script MUST write a single level json file
        #  named 'cheetah_user_report.json' for Cheetah to report the
        # additional results.
        self.user_run_script = user_run_script

        # Bool that denotes if tau metrics must be collected.
        # Runs pprof for tau profiles, and generates otf file for traces.
        self.tau_metrics = tau_metrics

        # Name of the output (csv) file where the performance report will be
        #  written
        self.output_filename = output_filename

        # Tmp var to keep track of the current user campaign
        self.current_campaign_user = None

        # Dict that holds the exit status of runs
        self.run_status = {}

        _log.info("Campaign directory: {}, user script: {}, tau metric "
                  "collection: {}, output report in: {}".format(
            campaign_directory, user_run_script, tau_metrics, output_filename))

    def parse_campaign(self):
        """
        """

        campaign_id_file = os.path.join(self.campaign_directory, ".campaign")
        assert os.path.isfile(campaign_id_file),\
            "{} is not the campaign root directory".format(campaign_id_file)

        _log.info("Parsing campaign {}".format(self.campaign_directory))

        # Traverse user campaigns
        self.parse_user_campaigns()

        # Write the parsed results to csv
        self.write_output()

    def parse_user_campaigns(self):
        """

        :return:
        """

        # At the top level, a campaign consists of user-level campaigns
        user_dirs = get_immediate_subdirs(self.campaign_directory)

        # Traverse user campaigns
        for user in user_dirs:
            if '__pycache__' in user:
                continue

            _log.info("Parsing sweep groups for {}".format(user))
            self.current_campaign_user = user

            user_dir = os.path.join(self.campaign_directory, user)

            # Verify that current dir is a user-level campaign endpoint by
            # checking for the presence of the campaign-env.sh file.
            campaign_env = os.path.join(user_dir, "campaign-env.sh")
            assert (os.path.isfile(campaign_env)),\
                "ERROR: Could not find campaign_env.sh at {}".format(user_dir)

            # Walk through sweep groups
            sweep_groups = get_immediate_subdirs(user_dir)
            if not sweep_groups:
                _log.info("No sweep groups found")
                return

            for sweep_group in sweep_groups:
                group_dir = os.path.join(user_dir, sweep_group)
                self.parse_sweep_group(group_dir)

    def parse_sweep_group(self, group_dir):
        """
        Parse sweep group and get post-run performance information
        """

        _log.info("Parsing sweep group {}".format(group_dir))

        # Check if group was run by checking if status file exists
        status_file = os.path.join(group_dir, "codar.workflow.status.json")

        # Read status file
        try:
            with open(status_file, 'r') as f:
                status_json = json.load(f)
        except:
            _log.error("Could not read status file {}".format(status_file))
            return

        # Parse runs that have completed
        run_status = {}
        for run_dir, values in status_json.items():
            if status_json[run_dir]['state'] == 'done':
                run_status[run_dir] = status_json[run_dir]['reason']

        for run_dir, exit_status in run_status.items():
            self.parse_run_dir(os.path.join(group_dir,run_dir), exit_status)

    def parse_run_dir(self, run_dir, exit_status):
        """
        Parse run directory of a sweep group
        """

        _log.info("Parsing run {}".format(run_dir))
        rp = _RunParser(run_dir, exit_status, self.user_run_script,
                        self.tau_metrics)

        # Re-verify that all run components have exited cleanly by
        # checking their codar.workflow.return.[rc_name] file.
        # This includes internally spawned RCs such as sos_flow.
        # First, get the names of run-components by reading the
        # codar.cheetah.fobs.json file.

        # Add run dir to the list of csv columns
        rp.serialized_run_params["run_dir"] = run_dir

        # Note the user who made this run
        rp.serialized_run_params["user"] = self.current_campaign_user

        # Open fob json file
        rp.read_fob_json()

        # Get names of all run components
        rp.get_rc_names()

        # Read the application run parameters from run-params.json
        rp.get_run_params()

        # Append the node layout info from codar.cheetah.fob.json
        rp.read_node_layout()

        # Get timing information if the experiment was successful,
        # else leave the fields blank
        rp.get_cheetah_perf_data(run_dir)

        # Get the sizes of the output adios files.
        # The sizes were calculated by the post-processing function
        # after the run finished.
        # For every file, create two columns: 'adios_file_1' and
        # 'adios_file_1_size', and so on.
        rp.read_adios_output_file_sizes()

        # Collect tau metrics
        if self.tau_metrics:
            rp.collect_tau_metrics()

        # Run the user-defined run script
        rp.execute_user_run_script()

        # Add any new params discovered in this run dir to unique_keys
        for key in rp.serialized_run_params:
            self.unique_keys.add(key)

        # Add the performance results to list of parsed runs
        self.parsed_runs.append(rp.serialized_run_params)

    def write_output(self):
        """

        :return:
        """
        _log.info("Done generating report.")
        _log.info("Writing output to {}".format(self.output_filename))
        with open(self.output_filename, 'w') as f:
            dict_writer = csv.DictWriter(f, sorted(self.unique_keys))
            dict_writer.writeheader()
            dict_writer.writerows(self.parsed_runs)


def generate_report(campaign_directory, user_run_script,
                    tau_metrics, output_file_path, verbose_level):
    """
    This is a post-run function.
    It walks the campaign tree and retrieves performance information
    about all completed runs.
    """

    # logging.basicConfig(level=logging.INFO)
    if verbose_level:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Ensure this is a campaign by checking for the presence of the
    # .campaign file
    require_campaign_directory(campaign_directory)

    rg = _ReportGenerator(campaign_directory, user_run_script,
                          tau_metrics, output_file_path)
    rg.parse_campaign()


if __name__ == "__main__":
    generate_report(sys.argv[1], sys.argv[2], True)
