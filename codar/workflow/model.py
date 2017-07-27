import time
import subprocess
import os.path
import shlex


STDOUT_NAME = 'codar.workflow.stdout'
STDERR_NAME = 'codar.workflow.stderr'
RETURN_NAME = 'codar.workflow.return'


def _get_path(default_dir, default_name, specified_name):
    path = specified_name or default_name
    if not path.startswith("/"):
        path = os.path.join(default_dir, path)
    return path


class Run(object):
    def __init__(self, name, exe, args, env, working_dir, timeout=None,
                 nprocs=1, stdout_path=None, stderr_path=None,
                 return_path=None, logger=None, log_prefix=None):
        self.name = name
        self.exe = exe
        self.args = args
        self.env = env
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

    def start(self, runner=None):
        if runner is not None:
            args = runner.wrap(self)
        else:
            args = [self.exe] + self.args
        if self.logger is not None:
            cmd = ' '.join(shlex.quote(arg) for arg in args)
            self.logger.info('%s start %r', self.log_prefix, cmd)
        self._start_time = time.time()
        self._popen(args)

    @classmethod
    def from_data(self, data):
        """Create Run instance from nested dictionary data structure, e.g.
        parsed from JSON. The keys 'name', 'exe', 'args' are required, all the
        other keys are optional and have the same names as the constructor
        args. Raises KeyError if a required key is missing."""
        # TODO: deeper validation
        r = Run(name=data["name"], exe=data['exe'], args=data['args'],
                env=data.get('env'), # dictionary of varname/varvalue
                working_dir=data.get('working_dir'),
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
        self._p = subprocess.Popen(args, env=self.env, cwd=self.working_dir,
                                   stdout=out, stderr=err)

    def poll(self):
        if self._complete:
            return self.get_returncode()
        if self._p is None:
            raise ValueError('not running')
        rval = self._p.poll()
        if self.logger is not None:
            self.logger.debug('%s poll %s', self.log_prefix, rval)
        if rval is None:
            # check if timeout has been reached and kill if it has
            if (self.timeout is not None
                    and time.time() - self._start_time > self.timeout):
                if self.logger is not None:
                    self.logger.warn('%s killing (timeout %d)', self.log_prefix,
                                     self.timeout)
                self._p.kill()
                rval = self._p.wait()
        if rval is not None:
            self._complete = True
            if self.logger is not None:
                self.logger.warn('%s complete: %d', self.log_prefix, rval)
            self._save_returncode(rval)
            self.close()
        return rval

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


class Pipeline(object):
    def __init__(self, runs):
        self.runs = runs
        self._running = False
        self.total_procs = 0
        for run in runs:
            self.total_procs += run.nprocs

    def start(self, runner=None):
        for run in self.runs:
            run.start(runner)
        self._running = True

    def get_pids(self):
        assert self._running
        return [run.get_pid() for run in self.runs]

    def poll_all_nprocs(self):
        assert self._running
        return [(run.poll(), run.nprocs, run.get_pid()) for run in self.runs]

    def set_loggers(self, logger, pipeline_id):
        for run in self.runs:
            run.set_logger(logger, "%d:%s" % (pipeline_id, run.name))


class Runner(object):
    def wrap(self, run):
        raise NotImplemented()


class MPIRunner(Runner):
    def __init__(self, exe, nprocs_arg):
        self.exe = exe
        self.nprocs_arg = nprocs_arg

    def wrap(self, run):
        return [self.exe, self.nprocs_arg, str(run.nprocs), run.exe] + run.args


mpiexec = MPIRunner('mpiexec', '-n')
aprun = MPIRunner('aprun', '-n')
