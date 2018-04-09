"""
Cheetah paths and (in future) features for loading site configuration.
"""
import os.path
import math
from codar.cheetah import exc

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


def etc_path(conf_name):
    return os.path.join(CHEETAH_PATH, "etc", conf_name)


def get_dataspaces_num_servers(num_clients, transport_type):
    """
    Get the number of dataspaces server instances that must be created for a
    given number of client processes.
    :param num_clients: no. of client processes that connect via dataspaces
    :param transport_type: type of transport. either dataspaces/dimes
    :return:
    """

    # From Philip Davis at Rutgers
    # Create 1 server per 32 clients
    # @TODO Is this specific to Titan?

    if transport_type == 'DIMES':
        return math.ceil(num_clients/1024)
    elif transport_type == 'DATASPACES':
        return math.ceil(num_clients / 32)
    else:
        raise exc.CheetahException("Unexpected dataspaces transport type. "
                                   "Expected DATASPACES or DIMES, received "
                                   + transport_type)
