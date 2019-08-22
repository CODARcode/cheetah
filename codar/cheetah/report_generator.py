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
import csv
import subprocess
from codar.cheetah.helpers import get_immediate_subdirs, \
                                  require_campaign_directory


class _RunParser:
    def __init__(self, run_dir, exit_status, user_run_script):
        """
        Class to parse a run directory.
        :param run_dir:
        """

        self.run_dir = run_dir
        self.exit_status = exit_status
        self.user_run_script = user_run_script

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

    def get_cheetah_perf_data(self):
        for rc_name in self.rc_names:
            walltime_fname = "codar.workflow.walltime." + rc_name
            filepath = os.path.join(self.rc_working_dir[rc_name],
                                    walltime_fname)
            if Path(filepath).is_file():
                with open(filepath) as f:
                    line = f.readline()
                walltime_str = str(round(float(line), 2))
                self.serialized_run_params[rc_name + "__time"] = walltime_str
                self.serialized_run_params['timer_type'] = 'cheetah'

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
        else:
            print("Adios output file size data not found")

    def read_node_layout(self):
        """

        :return:
        """
        for rc_layout_d in (self.fob_dict.get('node_layout') or []):
            rc_name_layout = list(rc_layout_d.items())[0]
            if 'sosflow_aggregator' not in rc_name_layout[0]:
                node_layout_key = 'node_layout_' + rc_name_layout[0]
                self.serialized_run_params[node_layout_key] = rc_name_layout[1]

    def execute_user_run_script(self):
        if self.exit_status != 'succeeded':
            return
        if self.user_run_script is not None:
            subprocess.check_call(os.path.abspath(self.user_run_script),
                                  cwd=self.run_dir)

        user_file = os.path.join(self.run_dir, "cheetah_user_report.json")

        try:
            with open(user_file) as f:
                user_report_d = json.load(f)
        except:
            print("Could not find cheetah_user_report.json. Skipping "
                  "capturing user report.")
            return

        for key,value in user_report_d.items():
            self.serialized_run_params[key] = value

    def verify_run_successful(self):
        """

        :return:
        """

        # Open status return files for all RCs to verify they exited cleanly
        for rc in self.rc_names:
            return_code_file = os.path.join(self.rc_working_dir[rc],
                                            "codar.workflow.return." + rc)
            if not Path(return_code_file).is_file():
                print("WARN: Could not find file " + return_code_file +
                      ". Skipping run directory.")
                return False
            with open(return_code_file) as f:
                line = f.readline()
                ret_code = int(line.strip())
                if ret_code != 0:
                    print("WARN: Run component " + rc +
                          " in " + self.run_dir + " did not exit cleanly. " 
                                                  "Skipping run directory.")
                    return False
        return True

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
    def __init__(self, campaign_directory, user_run_script, output_filename):
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

        # Name of the output (csv) file where the performance report will be
        #  written
        self.output_filename = output_filename

        # Tmp var to keep track of the current user campaign
        self.current_campaign_user = None

        # Dict that holds the exit status of runs
        self.run_status = {}

    def parse_campaign(self):
        """

        :return:
        """

        print("Parsing campaign", self.campaign_directory, "...")

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
            print("Parsing sweep groups for", user, "...")
            self.current_campaign_user = user

            user_dir = os.path.join(self.campaign_directory, user)

            # Verify that current dir is a user-level campaign endpoint by
            # checking for the presence of the campaign-env.sh file.
            assert (os.path.isfile(os.path.join(user_dir, "campaign-env.sh"))), \
                "Current directory is not a user-level campaign"

            # Walk through sweep groups
            sweep_groups = get_immediate_subdirs(user_dir)
            if not sweep_groups:
                print("No sweep groups found")
                return

            for sweep_group in sweep_groups:
                group_dir = os.path.join(user_dir, sweep_group)
                self.parse_sweep_group(group_dir)

    def parse_sweep_group(self, group_dir):
        """
        Parse sweep group and get post-run performance information
        """

        print("Parsing sweep group " + group_dir)

        # Check if group was run by checking if status file exists
        status_file = os.path.join(group_dir, "codar.workflow.status.json")

        # Read status file
        try:
            with open(status_file, 'r') as f:
                status_json = json.load(f)
        except:
            print("ERROR: Could not read status file " + status_file)
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

        print("Parsing run", run_dir[len(self.campaign_directory)-1:])
        rp = _RunParser(run_dir, exit_status, self.user_run_script)

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
        if exit_status == 'succeeded':
            # Run sosflow analysis on the run_dir. If sos data is not
            # available, read timing information recorded by Cheetah
            rp.get_cheetah_perf_data()

            # Get the sizes of the output adios files.
            # The sizes were calculated by the post-processing function
            # after the run finished.
            # For every file, create two columns: 'adios_file_1' and
            # 'adios_file_1_size', and so on.
            rp.read_adios_output_file_sizes()

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
        print("Done generating report.")
        print("Writing output to " + self.output_filename)
        with open(self.output_filename, 'w') as f:
            dict_writer = csv.DictWriter(f, sorted(self.unique_keys))
            dict_writer.writeheader()
            dict_writer.writerows(self.parsed_runs)


def generate_report(campaign_directory, user_run_script, output_file_path):
    """
    This is a post-run function.
    It walks the campaign tree and retrieves performance information
    about all completed runs.
    """

    # Ensure this is a campaign by checking for the presence of the
    # .campaign file
    require_campaign_directory(campaign_directory)

    rg = _ReportGenerator(campaign_directory, user_run_script, output_file_path)
    rg.parse_campaign()


if __name__ == "__main__":
    generate_report(sys.argv[1], sys.argv[2])

