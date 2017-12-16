"""
Functions to analyze an already completed campaign.
Parses all run directories in all sweep groups to aggregate information.
Runs sosflow analysis to collect data.

All parameters specified in the spec file must be used as column headers in
an output csv file.
"""

from pathlib import Path
import json
from glob import glob
import csv


def __serialize_params_nested_dict(nested_run_params_dict):
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
    serialized_dict = {}
    for key in nested_run_params_dict:
        for nested_key in nested_run_params_dict[key]:
            new_key = key + "__" + nested_key
            serialized_dict[new_key] = nested_run_params_dict[key][nested_key]

    return serialized_dict


def __parse_run_dir(run_dir, parsed_runs, unique_keys):
    """
    Parse run directory of a sweep group
    """

    # Re-verify that all run components have exited cleanly by
    # checking their codar.workflow.return.[rc_name] file.
    # This includes internally spawned RCs such as sos_flow.
    # First, get the names of run-components by reading the
    # codar.cheetah.fobs.json file.

    # Open fob json file
    fob_json_filename = run_dir + "/" + "codar.cheetah.fob.json"
    try:
        with open(fob_json_filename, 'r') as f:
            fob_dict = json.load(f)
    except:
        print("ERROR: Could not read file " + fob_json_filename)
        return

    # Get rc names
    rc_names = []
    for rc in fob_dict['runs']:
        rc_names.append(rc['name'])

    # Open status return files for all RCs to verify they exited cleanly
    for rc in rc_names:
        with(open(run_dir + "/" + "codar.workflow.return." + rc)) as f:
            line = f.readline()
            ret_code = int(line.strip())
            if ret_code != 0:
                print("WARN: Run component " + rc +
                      " in " + run_dir + " has not exited cleanly. "
                      "Skipping run directory.")
                return

    # Now form dict of user codes and run params by reading
    # codar.cheetah.run-params.json.
    try:
        run_params_json_filename = run_dir + "/" + \
                                   "codar.cheetah.run-params.json"
        with open(run_params_json_filename, "r") as f:
            run_params_dict = json.load(f)
    except:
        print("WARN: Could not open " + run_params_json_filename +
              ". Skipping " + run_dir)
        return

    # Serialize nested dict and add to list of parsed run dicts
    serialized_run_params = __serialize_params_nested_dict(run_params_dict)
    parsed_runs.append(serialized_run_params)

    # Add any new params discovered in this run dir to unique keys
    for key in serialized_run_params:
        unique_keys.add(key)

    # Run sosflow analysis on the run_dir now.


def __parse_sweep_group(sweep_group, parsed_runs, unique_keys):
    """
    Parse sweep group and get post-run performance information
    """

    # Check if group was run by checking if status file exists
    status_file = Path(sweep_group + "/codar.workflow.status.json")
    if not status_file.is_file():
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
        successful_runs.append(sweep_group + "/" + run_dir)

    # Parse runs that have succeeded
    for run_dir in successful_runs:
        __parse_run_dir(run_dir, parsed_runs, unique_keys)


def analyze():
    """
    This is a post-run function.
    It walks the campaign tree and retrieves performance information
    about all completed runs.
    """
    
    # A list of dicts. Each dict contains metadata and performance information
    # about the run.
    parsed_runs = []
    
    # Unique application parameters that can be used as headers for csv output
    unique_keys = set()
    
    # This should only be run in the campaign top-level directory.
    # Verify that current dir is the campaign endpoint
    # by checking for the presence of the campaign-env.sh file.
    campaign_env_file = Path("./campaign-env.sh")
    assert (campaign_env_file.is_file()),\
        "Current directory does not seem to be a campaign endpoint"

    # Walk through sweep groups
    sweep_groups = glob('*/')
    if not sweep_groups:
        print("No sweep groups found")
        return

    for sweep_group in sweep_groups:
        __parse_sweep_group("./" + sweep_group, parsed_runs, unique_keys)

    # Write the parsed results to csv
    with open('campaign_results.csv', 'w') as f:
        dict_writer = csv.DictWriter(f, sorted(unique_keys))
        dict_writer.writeheader()
        dict_writer.writerows(parsed_runs)


if __name__ == "__main__":
    analyze()
