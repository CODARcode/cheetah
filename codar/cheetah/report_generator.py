"""
Generate performance report from a completed campaign.
This module parses all run directories in all sweep groups to aggregate
information.
Runs sosflow analysis to collect data.

All parameters specified in the spec file must be used as column headers in
an output csv file.
"""

import os
from pathlib import Path
import json
import csv
from codar.cheetah.sos_flow_analysis import sos_flow_analysis
from codar.cheetah.helpers import get_immediate_subdirs


class _RunParser:
    def __init__(self, run_dir):
        """
        Class to parse a run directory.
        :param run_dir:
        """

        self.run_dir = run_dir
        self.serialized_run_params = {}
        self.fob_dict = {}
        self.rc_names = []
        self.rc_working_dir = {}

        # sos_flow sees exes in the perf data that it collects. Form a
        # mapping of rc_exe:rc_name so that we can get the rc_name from the
        # exe from sos data
        self.rc_name_exe = {}

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

    def read_sos_perf_data(self):
        """

        :return: True if sos data was found, False otherwise
        """

        # Don't look for any sosflow data if it's not enabled on any of
        # the run components.
        if not any(run.get('sosflow', False) for run in self.fob_dict['runs']):
            return False

        sos_perf_results = sos_flow_analysis(self.run_dir)
        if sos_perf_results is None:
            return False

        # keys in sos_perf_results are full exe paths. Get the rc name from
        # the exe path
        for rc_exe in sos_perf_results:
            rc_name = self.rc_name_exe[rc_exe]
            self.serialized_run_params[rc_name + "__time"] = \
                sos_perf_results[rc_exe]["time"]
            self.serialized_run_params[rc_name + "__adios_time"] = \
                sos_perf_results[rc_exe]["adios_time"]
            # serialized_run_params[rc_name + "__adios_data"] = \
            # sos_perf_results[rc_exe]["adios_data"]
            self.serialized_run_params['timer_type'] = 'sosflow'

        return True

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
    def __init__(self, out_file_name):
        # A list of dicts. Each dict contains metadata and performance
        # information about the run
        self.parsed_runs = []

        # Unique application parameters that will be used as headers for csv
        #  output
        self.unique_keys = set()

        # Name of the output (csv) file where the performance report will be
        #  written
        self.output_filename = out_file_name

        # Temp var to keep track of the current user campaign
        self.current_campaign_user = None

    def parse_campaign(self):
        """

        :return:
        """

        print("Parsing campaign ...")

        # Traverse user campaigns
        self.parse_user_campaigns()

        # Write the parsed results to csv
        self.write_output()

    def parse_user_campaigns(self):
        """

        :return:
        """

        # At the top level, a campaign consists of user-level campaigns
        user_dirs = get_immediate_subdirs("./")

        # Traverse user campaigns
        for subdir in user_dirs:
            print("Parsing campaign for " + subdir)
            self.current_campaign_user = subdir

            # Verify that current dir is a user-level campaign endpoint by
            # checking for the presence of the campaign-env.sh file.
            assert (os.path.isfile(os.path.join(subdir, "campaign-env.sh"))), \
                "Current directory is not a user-level campaign"

            # Walk through sweep groups
            sweep_groups = get_immediate_subdirs("./" + subdir)
            if not sweep_groups:
                print("No sweep groups found")
                return

            for sweep_group in sweep_groups:
                self.parse_sweep_group("./" + subdir + "/" + sweep_group)

    def parse_sweep_group(self, sweep_group):
        """
        Parse sweep group and get post-run performance information
        """

        # Check if group was run by checking if status file exists
        status_file = sweep_group + "/codar.workflow.status.json"
        if not Path(status_file).is_file():
            print("WARN: Could not find file " + status_file +
                  ". Skipping sweep group")
            return

        # Read status file
        try:
            with open(status_file, 'r') as f:
                status_json = json.load(f)
        except:
            print("ERROR: Could not read status file " + status_file)
            return

        # Get the return codes of all runs.
        # If any rc has failed, don't parse the run dir.
        successful_runs = []
        for run_dir, values in status_json.items():
            rc_return_codes = status_json[run_dir]['return_codes']
            for rc, rc_return_code in rc_return_codes.items():
                if rc_return_code != 0:
                    break
            successful_runs.append(os.path.join(str(sweep_group), run_dir))

        # Parse runs that have succeeded
        for run_dir in successful_runs:
            self.parse_run_dir(run_dir)

    def parse_run_dir(self, run_dir):
        """
        Parse run directory of a sweep group
        """

        print("Parsing " + run_dir)
        rp = _RunParser(run_dir)

        # Re-verify that all run components have exited cleanly by
        # checking their codar.workflow.return.[rc_name] file.
        # This includes internally spawned RCs such as sos_flow.
        # First, get the names of run-components by reading the
        # codar.cheetah.fobs.json file.

        try:
            # Open fob json file
            rp.read_fob_json()

            # Get names of all run components
            rp.get_rc_names()

            # Check the return type of all components to ensure the run
            # exited cleanly
            if not rp.verify_run_successful():
                return

            # Read the application run parameters from run-params.json
            rp.get_run_params()
        except:
            return

        # Append the node layout info from codar.cheetah.fob.json
        rp.read_node_layout()

        # Run sosflow analysis on the run_dir. If sos data is not available,
        #  read timing information recorded by Cheetah
        if not rp.read_sos_perf_data():
            rp.get_cheetah_perf_data()

        # Get the sizes of the output adios files.
        # The sizes were calculated by the post-processing function after the
        # run finished.
        # For every file, create two columns: 'adios_file_1' and
        # 'adios_file_1_size', and so on.
        rp.read_adios_output_file_sizes()

        # Get the output of du instead of reading sos data for output data size
        # This is hacky. I am assuming that this file contains output of du.
        # dir_size = -1
        # post_process_file = run_dir + "/codar.workflow.stdout.post-process"
        # if Path(post_process_file).is_file():
        #     f = open(post_process_file, "r")
        #     lines = f.readlines()
        #     lastline = lines[-1]
        #     dir_size = int(re.search(r'\d+', lastline).group())
        #
        # serialized_run_params["dir_size"] = dir_size

        # Add run dir to the list of csv columns
        rp.serialized_run_params["run_dir"] = run_dir

        # Note the user who made this run
        rp.serialized_run_params["user"] = self.current_campaign_user

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
        print("Writing output to file " + self.output_filename)
        with open(self.output_filename, 'w') as f:
            dict_writer = csv.DictWriter(f, sorted(self.unique_keys))
            dict_writer.writeheader()
            dict_writer.writerows(self.parsed_runs)


def generate_report(out_file_name="./campaign_results.csv"):
    """
    This is a post-run function.
    It walks the campaign tree and retrieves performance information
    about all completed runs.
    """

    # Ensure this is a campaign by checking for the presence of the
    # .campaign file
    assert (os.path.isfile("./.campaign")), "Current directory is not a " \
                                            "top-level campaign"

    rg = _ReportGenerator(out_file_name)
    rg.parse_campaign()
