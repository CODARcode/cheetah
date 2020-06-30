import shutil
import logging


TAU_PROFILE_PATTERN = "codar.savanna.tau-profiles.{}"
TAU_TRACE_PATTERN = "codar.savanna.tau-traces.{}"
_log = logging.getLogger('codar.savanna.model')


def find_tau_exec():
    """
    Find full path to tau_exec in $PATH
    # TODO: Try loading module if tau_exec not in path.
    """

    # Find in PATH
    tau_exec = shutil.which("tau_exec")
    if tau_exec:
        _log.info("Found tau_exec at {}".format(tau_exec))
    return tau_exec
