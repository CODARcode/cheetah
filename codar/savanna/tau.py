import shutil
import logging
import os


TAU_PROFILE_PATTERN = "codar.savanna.tau-profiles.{}"
TAU_TRACE_PATTERN = "codar.savanna.tau-traces.{}"
_log = logging.getLogger('codar.savanna.model')


class Tau:
    def __init__(self, tau_exec, profiling_enabled, tracing_enabled,
                 run_workingdir, run_name):
        self.tau_exec = tau_exec
        self.env = {}
        self.profiling_enabled = profiling_enabled
        self.tracing_enabled = tracing_enabled
        self.profile_dir = None
        self.trace_dir = None

        self._find_tau_exec()
        self._add_tau_support(run_workingdir, run_name)

    def _add_tau_support(self, run_workingdir, run_name):
        """
        Set the exe to tau_exec and add tau env vars to self.env
        """

        self.env['TAU_PROFILE'] = "0"
        self.env['TAU_TRACE'] = "0"

        # Profiling
        if self.profiling_enabled:
            profiledir = os.path.join(run_workingdir,
                                      TAU_PROFILE_PATTERN.format(run_name))
            self.env['TAU_PROFILE'] = "1"
            self.env['PROFILEDIR'] = profiledir
            if not os.path.exists(profiledir):
                os.makedirs(profiledir)

        # Tracing
        if self.tracing_enabled:
            tracedir = os.path.join(run_workingdir,
                                    TAU_TRACE_PATTERN.format(run_name))
            self.env['TAU_TRACE'] = "1"
            self.env['TRACEDIR'] = tracedir
            if not os.path.exists(tracedir):
                os.makedirs(tracedir)

    def _find_tau_exec(self):
        """
        Assert tau_exec is in $PATH and executable
        """

        # Otherwise, find tau_exec in $PATH
        self.tau_exec = shutil.which("tau_exec")
        assert self.tau_exec is not None, \
            "FATAL: Could not find tau_exec in PATH"

        assert os.access(self.tau_exec, os.X_OK), \
            "FATAL: {} does not seem valid or executable" \
            "".format(self.tau_exec)

        _log.info("Found tau_exec at {}".format(self.tau_exec))
