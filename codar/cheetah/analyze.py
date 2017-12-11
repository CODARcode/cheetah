"""
Functions to analyze an already completed campaign.
Parses all run directories in all sweep groups to aggregate information.
Runs sosflow analysis to collect data.
"""

from pathlib import Path
import json
from glob import glob


def parse_run_dir(run_dir):
    print(run_dir)


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
        print("Could not status file " + status_file)

    # Get the return codes of all runs.
    # If any rc has failed, don't parse the run dir.
    successful_runs = []
    for run_dir, values in status_json.items():
        rc_return_codes = status_json[run_dir]['return_codes']
        for rc, rc_return_code in rc_return_codes.items():
            if rc_return_code != 0:
                break
        successful_runs.append(sweep_group + "./" + run_dir)

    # Parse runs that have succeeded
    for run_dir in successful_runs:
        parse_run_dir(run_dir)
    exit(0)


def analyze():
    """
    Walk the campaign tree and get information from all run directories.
    """

    # Analyze should only be run in the campaign top-level directory.
    # Verify that current dir is the campaign endpoint.
    campaign_env_file = Path("./campaign-env.sh")
    assert (campaign_env_file.is_file()),\
        "Current directory does not seem to be a campaign endpoint"

    # Walk through sweep groups
    sweep_groups = glob('*/')
    if not sweep_groups:
        print ("No sweep groups found")
        return

    for sweep_group in sweep_groups:
        parse_sweep_group("./" + sweep_group)


if __name__ == "__main__":
    analyze()