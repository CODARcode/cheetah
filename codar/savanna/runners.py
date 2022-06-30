import shutil
import math
from codar.savanna import machines
from codar.savanna.jsrun_opts import JsrunGenerator
from codar.savanna.run import Run


class Runner(object):
    def wrap(self, run, sched_args):
        raise NotImplemented()


class MPIRunner(Runner):
    def __init__(self, exe, nprocs_arg, nodes_arg=None,
                 tasks_per_node_arg=None, hostfile=None,
                 cpus_per_task_arg=None, threads_per_core_arg=None,
                 tasks_per_gpu_arg=None, gpus_per_task_arg=None):
        self.exe = exe
        self.nprocs_arg = nprocs_arg
        self.nodes_arg = nodes_arg
        self.cpus_per_task_arg=cpus_per_task_arg
        self.threads_per_core_arg=threads_per_core_arg
        self.tasks_per_node_arg = tasks_per_node_arg
        self.hostfile = hostfile
        self.tasks_per_gpu_arg = tasks_per_gpu_arg
        self.gpus_per_task_arg = gpus_per_task_arg

    def wrap(self, run: Run, sched_args, find_in_path=True):
        if run.child_runs is None:
            return self._wrap_single(run, sched_args, find_in_path)
        else:
            return self._wrap_mpmd(run, sched_args, find_in_path)

    def _wrap_single(self, run, sched_args, find_in_path=True):
        runner_args = []
        runner_args += [self.exe, self.nprocs_arg, str(run.nprocs)]

        if sched_args:
            for (k, v) in sched_args.items():
                runner_args += [k, v]

        if self.nodes_arg:
            runner_args += [self.nodes_arg, str(run.nodes)]
        if self.tasks_per_node_arg:
            runner_args += [self.tasks_per_node_arg, str(run.tasks_per_node)]
        if run.cpus_per_task is not None:
            runner_args += [self.cpus_per_task_arg.format(str(
                run.cpus_per_task))]
        if run.threads_per_core is not None:
            runner_args += [self.threads_per_core_arg.format(str(
                run.threads_per_core))]
        if run.hostfile is not None:
            runner_args += [self.hostfile, str(run.hostfile)]
        if run.tasks_per_gpu is not None:
            runner_args += [self.tasks_per_gpu_arg.format(str(
                run.tasks_per_gpu))]
        if run.gpus_per_task is not None:
            runner_args += [self.gpus_per_task_arg.format(str(
                run.gpus_per_task))]

        return runner_args + [run.app_sh]

    def _wrap_mpmd(self, run:Run, sched_args, find_in_path=True):
        args = self._wrap_single(run.child_runs[0], run.child_runs[0].sched_args, find_in_path)

        for r in run.child_runs[1:]:
            _args = self._wrap_single(r, r.sched_args, find_in_path)
            args += [" : "] + _args[1:]

        return args


class DTH2Runner(Runner):
    def __init__(self, cuda_enabled=0):
        self.exe = 'mpirun'
        self.nprocs_arg = '-np'
        self.tasks_per_node_arg = '-N'
        self.rankfile = '--rankfile'
        self.bindings = '--report-bindings'
        self.env = '-x'
        self.cuda_enabled = cuda_enabled

    def wrap(self, run, sched_args, find_in_path=True):
        if find_in_path:
            exe_path = shutil.which(self.exe)
        else:
            # for test cases
            exe_path = self.exe
        if exe_path is None:
            raise ValueError('Could not find "%s" in path' % self.exe)

        runner_args = [exe_path,
                       '--mca', 'mpi_cuda_support', str(self.cuda_enabled),
                       self.nprocs_arg, str(run.nodes),
                       '--report-bindings']

        if run.dth_rankfile is not None:
            runner_args += ['--rankfile', run.dth_rankfile]
        else:
            runner_args += [self.tasks_per_node_arg, str(run.tasks_per_node)]

        # What are you trying to do here? Set environment variables? That is
        # already done by the Run in popen. OR did you try to just add
        # self.env here, which is set to '-x' above?
        # for k, v in run.env:
        #     runner_args += [self.env, str(k), str(v)]

        return runner_args + [run.app_sh]


class SummitRunner(Runner):
    def __init__(self):
        self.exe = 'jsrun'
        self.nrs_arg = '-n'
        self.tasks_per_rs_arg = '-a'
        self.cpus_per_rs_arg = '-c'
        self.gpus_per_rs_arg = '-g'
        self.rs_per_host_arg = '-r'
        self.launch_distribution_arg = '-d'
        self.bind_arg = '-b'
        self.machine = machines.summit

    def wrap(self, run, sched_args):
        """
        Call either the ERF file feature or regular jsrun command-line
        functionality to submit tasks.
        """

        #--------------------------------------------------------------------#
        # #241: ERF files broken on Summit. Switch to regular jsrun options.
        # This disables MPMD runs and node sharing, which is handled in
        # cheetah.model .
        # return self._wrap_jsrun_noerf(run, sched_args)
        # --------------------------------------------------------------------#
        return self._wrap_erf(run, sched_args)

    def _wrap_erf(self, run, sched_args):
        """
        Use the ERF feature to launch tasks with jsrun.
        """
        runner_args = ['jsrun', '--erf_input', run.erf_file]
        return runner_args

    def _wrap_jsrun_noerf(self, run, sched_args):
        """
        Use regular, command-line options to jsrun to launch tasks, instead
        of using ERF files for jsrun.
        """

        j = JsrunGenerator(run.node_config, run.nprocs)

        nrs = j.n
        rs_per_host = j.r
        tasks_per_rs = j.a
        cpus_per_task = j.c
        gpus_per_rs = j.g

        runner_args = [self.exe,
                       self.nrs_arg, str(nrs),
                       self.rs_per_host_arg, str(rs_per_host),
                       self.tasks_per_rs_arg, str(tasks_per_rs),
                       self.cpus_per_rs_arg, str(cpus_per_task),
                       self.gpus_per_rs_arg, str(gpus_per_rs),
                       # "-b", "packed:{}".format(cpus_per_task//tasks_per_rs),
                       self.launch_distribution_arg, "packed",
                       ]

        # When you have more cpus per rank, usually OMP_NUM_THREADS is set,
        # and the option '-b packed:7' is provided.
        if cpus_per_task > 1:
            bind_value = cpus_per_task//tasks_per_rs
            runner_args.extend([self.bind_arg, "packed:{}".format(bind_value)])

        if sched_args:
            for (k, v) in sched_args.items():
                runner_args += [str(k), str(v)]

        return runner_args + [run.app_sh]


mpiexec = MPIRunner('mpiexec', '-n', hostfile='--hostfile')
aprun = MPIRunner('aprun', '-n', tasks_per_node_arg='-N', hostfile='-L')
srun = MPIRunner('srun', '-n', nodes_arg='-N', hostfile='-w',
                 cpus_per_task_arg='--cpus-per-task={}',
                 threads_per_core_arg='--threads-per-core={}',
                 tasks_per_gpu_arg='--ntasks-per-gpu={}',
                 gpus_per_task_arg='--gpus-per-task={}')
mpirunc = DTH2Runner(0)
mpirung = DTH2Runner(1)
jsrun = SummitRunner()
