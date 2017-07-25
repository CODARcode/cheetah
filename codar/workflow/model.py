STDOUT_NAME = 'codar.workflow.stdout.txt'
STDERR_NAME = 'codar.workflow.stderr.txt'


def _get_path(default_dir, default_name, specified_name):
    path = specified_name or default_name
    if not path.startswith("/"):
        path = os.path.join(default_dir, path)
    return path


class Run(object):
    def __init__(self, exe, args, env, working_dir, timeout, nprocs=1,
                 stdout_path=None, stderr_path=None):
        self.exe = exe
        self.args = args
        self.env = env
        self.working_dir = working_dir
        self.timeout = timeout
        self.nprocs = nprocs
        self.stdout_path = _get_path(working_dir, STDOUT_NAME, stdout_path)
        self.stderr_path = _get_path(working_dir, STDERR_NAME, stderr_path)
        self._p = None

    def start(self, runner=None):
        if runner is not None:
            args = runner.wrap(self)
        else:
            args = [self.exe] + self.args
        self._popen(args)

    @classmethod
    def from_data(self, data):
        """Create Run instance from nested dictionary data structure, e.g.
        parsed from JSON. The keys 'exe' and 'args' are required, all the
        other keys are optional and have the same names as the constructor
        args. Raises KeyError if a required key is missing."""
        # TODO: deeper validation
        r = Run(exe=data['exe'], args=data['args'],
                env=data.get('env'), # dictionary of varname/varvalue
                working_dir=data.get('working_dir'),
                timeout=data.get('timeout'),
                nprocs=data.get('nprocs', 1),
                stdout_path=data.get('stdout_path'),
                stderr_path=data.get('stderr_path'))

    def _popen(self, args):
        out = open(self.stdout_path, 'w')
        err = open(self.stderr_path, 'w')
        self._p = subprocess.Popen(args, env=self.env, cwd=self.working_dir,
                                   stdout=out, stderr=err)

    def poll(self):
        if self._p is None:
            raise ValueError('not running')
        return self._p.poll()

    def get_returncode(self):
        if self._p is None:
            raise ValueError('not running')
        return self._p.return_code

    def get_pid(self):
        if self._p is None:
            raise ValueError('not running')
        return self._p.pid

    def close(self):
        self._p.stdout.close()
        self._p.stderr.close()


class Pipeline(object):
    def __init__(self, runs):
        self.runs = runs
        self._running = False
        self.total_procs = 0
        for run in runs:
            self.total_procs += run.nprocs

    def start(self, runner=None):
        for run in runs:
            run.start(runner)
        self._running = True

    def get_pids(self):
        return [run.get_pid() for run in self.runs]


class Runner(object):
    def wrap(self, run):
        raise NotImplemented()


class MPIRunner(Runner):
    def __init__(self, exe, nproc_arg):
        self.exe = exe
        self.nprocs_arg = nprocs_arg

    def wrap(self, run):
        return [self.exe, self.nprocs_arg, str(run.nprocs), run.exe] + run.args


mpiexec = MPIRunner('mpiexec', '-n')
aprun = MPIRunner('aprun', '-n')
