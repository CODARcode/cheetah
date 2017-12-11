"""
Functions to analyze an already completed campaign.
Parses all run directories in all sweep groups to aggregate information.
Runs sosflow analysis to collect data.
"""

from pathlib import Path
import json
from glob import glob


def parse_run_dir(run_dir):
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

    print(run_params_dict)
    exit(0)

    # Run sosflow analysis on the run_dir now.


def parse_sweep_group(sweep_group):
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
        parse_run_dir(run_dir)
    exit(0)


def analyze():
    """
    This is a post-run function.
    It walks the campaign tree and retrieves performance information
    about all completed runs.
    """

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
        parse_sweep_group("./" + sweep_group)


if __name__ == "__main__":
    analyze()