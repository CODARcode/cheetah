import time
import subprocess
import os
import shutil
import math
import threading


STDOUT_NAME = 'codar.workflow.stdout'
STDERR_NAME = 'codar.workflow.stderr'
RETURN_NAME = 'codar.workflow.return'


def _get_path(default_dir, default_name, specified_name):
    path = specified_name or default_name
    if not path.startswith("/"):
        path = os.path.join(default_dir, path)
    return path


class Run(threading.Thread):
    """Manage running a single executable within a pipeline. When start is
    called, it will launch the process with Popen and call wait in the new
    thread with a timeout, killing if the process does not finish in time."""
    def __init__(self, name, exe, args, env, working_dir, timeout=None,
                 nprocs=1, stdout_path=None, stderr_path=None,
                 return_path=None, logger=None, log_prefix=None):
        threading.Thread.__init__(self, name="Thread-Run-" + name)
        self.name = name
        self.exe = exe
        self.args = args
        self.env = env or {}
        self.working_dir = working_dir
        self.timeout = timeout
        self.nprocs = nprocs
        self.stdout_path = _get_path(working_dir, STDOUT_NAME + "." + name,
                                     stdout_path)
        self.stderr_path = _get_path(working_dir, STDERR_NAME + "." + name,
                                     stderr_path)
        self.return_path = _get_path(working_dir, RETURN_NAME + "." + name,
                                     return_path)
        self._p = None
        self._start_time = None
        self._open_files = []
        self._complete = False
        self.log_prefix = log_prefix or name
        self.logger = logger
        self.runner = None
        self.callbacks = set()

    def set_runner(self, runner):
        self.runner = runner

    def add_callback(self, fn):
        """Function takes single argument which is this run instance, and is
        called when the process is complete (either normally or killed by
        timeout)."""
        self.callbacks.add(fn)

    def remove_callback(fn):
        self.callbacks.remove(fn)

    def run(self):
        if self.runner is not None:
            args = self.runner.wrap(self)
        else:
            args = [self.exe] + self.args
        self._start_time = time.time()
        self._popen(args)
        if self.logger is not None:
            self.logger.info('%s start %d %r', self.log_prefix, self._p.pid,
                             args)
        try:
            self._p.wait(self.timeout)
        except subprocess.TimeoutExpired:
            if self.logger is not None:
                self.logger.warn('%s killing (timeout %d)', self.log_prefix,
                                 self.timeout)
            self._p.kill()
            self._p.wait()
        self._save_returncode(self._p.returncode)
        if self.logger is not None:
            self.logger.info('%s done %d %d', self.log_prefix, self._p.pid,
                             self._p.returncode)
        for callback in self.callbacks:
            callback(self)

    @classmethod
    def from_data(self, data):
        """Create Run instance from nested dictionary data structure, e.g.
        parsed from JSON. The keys 'name', 'exe', 'args' are required, all the
        other keys are optional and have the same names as the constructor
        args. Raises KeyError if a required key is missing."""
        # TODO: deeper validation
        r = Run(name=data['name'], exe=data['exe'], args=data['args'],
                env=data.get('env'), # dictionary of varname/varvalue
                working_dir=data['working_dir'],
                timeout=data.get('timeout'),
                nprocs=data.get('nprocs', 1),
                stdout_path=data.get('stdout_path'),
                stderr_path=data.get('stderr_path'),
                return_path=data.get('return_path'))
        return r

    def _popen(self, args):
        out = open(self.stdout_path, 'w')
        err = open(self.stderr_path, 'w')
        self._open_files = [out, err]
        # NOTE: it's important to maintain the calling environment,
        # which can contain LD_LIBRARY_PATH and other variables that are
        # required for modules and normal HPC operation (e.g aprun).
        # TODO: should this do a smart merge per variable, so you could
        # e.g. extend PATH or LD_LIBRARY_PATH rather tha replace it?
        env = os.environ.copy()
        env.update(self.env)
        self._p = subprocess.Popen(args, env=env, cwd=self.working_dir,
                                   stdout=out, stderr=err)

    def _save_returncode(self, rcode):
        assert rcode is not None
        with open(self.return_path, 'w') as f:
            f.write(str(rcode))

    def get_returncode(self):
        if self._p is None:
            raise ValueError('not running')
        return self._p.returncode

    def get_pid(self):
        if self._p is None:
            raise ValueError('not running')
        return self._p.pid

    def close(self):
        for f in self._open_files:
            f.close()
        self._open_files = []

    def set_logger(self, logger, log_prefix):
        self.logger = logger
        self.log_prefix = log_prefix

    def get_nodes_used(self, ppn):
        """Get number of nodes needed to run this app with the given number
        of process per node (ppn)."""
        return math.ceil(self.nprocs / ppn)


class Pipeline(object):
    def __init__(self, runs):
        self.runs = runs
        self._running = False
        self._active_runs = set()
        self.callbacks = set()
        self.total_procs = 0
        for run in runs:
            self.total_procs += run.nprocs

    def start(self, consumer, runner=None):
        """Start all runs in the pipeline, along with threads that monitor
        their progress and signal consumer when finished. Use join_all to
        wait until they are all finished."""
        self.add_callback(consumer.pipeline_finished)
        for run in self.runs:
            run.set_runner(runner)
            run.add_callback(consumer.run_finished)
            run.add_callback(self.run_finished)
            run.start()
        self._running = True
        self._active_runs = set(self.runs)
        return self.runs

    def run_finished(self, run):
        self._active_runs.remove(run)
        if not self._active_runs:
            for cb in self.callbacks:
                cb(self)

    def add_callback(self, fn):
        self.callbacks.add(fn)

    def remove_callback(self, fn):
        self.callbacks.remove(fn)

    def get_nodes_used(self, ppn):
        """Get number of nodes needed to run pipeline with the given number
        of process per node (ppn). Assumes each app run will gain exclusive
        access to the node, i.e. each app consumes at least one node, even if
        it doesn't use all available processes."""
        nodes = 0
        for run in self.runs:
            nodes += math.ceil(run.nprocs / ppn)
        return nodes

    def get_pids(self):
        assert self._running
        return [run.get_pid() for run in self.runs]

    def set_loggers(self, logger, pipeline_id):
        for run in self.runs:
            run.set_logger(logger, "%d:%s" % (pipeline_id, run.name))

    def join_all(self):
        assert self._running
        for run in runs:
            run.join()


class Runner(object):
    def wrap(self, run):
        raise NotImplemented()


class MPIRunner(Runner):
    def __init__(self, exe, nprocs_arg):
        self.exe = exe
        self.nprocs_arg = nprocs_arg

    def wrap(self, run):
        exe_path = shutil.which(self.exe)
        if exe_path is None:
            raise ValueError('Could not find "%s" in path' % self.exe)
        return [exe_path, self.nprocs_arg, str(run.nprocs), run.exe] + run.args


mpiexec = MPIRunner('mpiexec', '-n')
aprun = MPIRunner('aprun', '-n')
