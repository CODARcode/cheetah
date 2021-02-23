import os
import signal
import subprocess
import summit_helper

#----------------------------------------------------------------------------#
class JsrunExecutor():
    """Jsrun executor for an application on Summit
    """
    def __init__(self, run):
        self.run = run
        self.erf_file = "{}.erf_input".format(self.run.name)
        self.pid = None

    def execute(self):
        self._assign_nodes()
        summit_helper.create_erf_file(self.erf_file, self.run.name,
            self.run.working_dir, self.run.exe, self.run.args, self.run.nprocs,
            self.run.nodes, self.run.nodes_assigned, self.run.node_config)
        self._submit()
        self._wait()
    
    def _assign_nodes(self):
        """Assign hostids to the Run.
        These are relative indices, thus they always start from 1.
        """
        assert self.run.nodes > 0
        self.run.nodes_assigned = []
        for i in range(self.run.nodes):
            self.run.nodes_assigned.append(i+1)

    def _submit(self):
        """Submit a jsrun using Popen
        """
        submit_cmd = "jsrun --erf_input {}".format(self.erf_file)
        popen_args = list(submit_cmd.split())
        stdout_path = "{}.stdout".format(self.run.name)
        stderr_path = "{}.stderr".format(self.run.name)
        f_out = open(stdout_path, "w")
        f_err = open(stderr_path, "w")
        self.pid = subprocess.Popen(popen_args, cwd=self.run.working_dir, 
                                    stdout=f_out, stderr=f_err)

    def _wait(self):
        """Wait for a running Popen instance to complete
        """
        try:
            self.pid.wait(self.run.timeout)
        except subprocess.TimeoutExpired:
            self._kill()
    
    def _kill(self):
        """Kill a Run that seems to have timedout.
        """
        os.killpg(os.getpgid(self.pid.pid, signal.SIGTERM))

