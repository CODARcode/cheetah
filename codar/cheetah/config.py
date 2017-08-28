"""
Cheetah paths and (in future) features for loading site configuration.
"""
import os.path

CHEETAH_PATH = os.path.realpath(os.path.join(
                     os.path.dirname(__file__), "..", ".."))

CHEETAH_PATH_SCRIPTS = os.path.join(CHEETAH_PATH, "scripts")

CHEETAH_PATH_MACHINE_CONFIG = os.path.join(CHEETAH_PATH, "machine_config")

WORKFLOW_SCRIPT = os.path.join(CHEETAH_PATH, "workflow.py")

def script_path(script_name):
    return os.path.join(CHEETAH_PATH_SCRIPTS, script_name)


def machine_submit_env_path(machine_name):
    return os.path.join(CHEETAH_PATH_MACHINE_CONFIG, machine_name,
                        'submit-env.sh')
