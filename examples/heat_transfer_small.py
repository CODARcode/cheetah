#
# This example illustrates the format of a Cheetah configuration file
#
from codar.cheetah import Campaign
from codar.cheetah import parameters as p

class HeatTransfer(Campaign):
    """Small example to run the heat_transfer application with stage_write,
    using no compression, zfp, or sz. All other options are fixed, so there
    are only three runs."""

    name = "heat-transfer-small"

    # This applications consists of two codes, with nicknames "heat" and
    # "stage" and locations as specified
    codes = dict(heat="heat_transfer_adios2",
                 stage="stage_write/stage_write")

    # The application is designed to run on two machines.
    # (These are magic strings known to Cheetah.)
    supported_machines = ['local', 'titan']

    # Inputs are copied to each "run directory" -- directory created by
    # Cheetah for each run
    inputs = ["heat_transfer.xml"]

    # If the heat or stage code fails (nonzero exit code) during a run,
    # kill the other code if still running. This is useful for multi-code
    # apps that require all codes to complete for useful results. This
    # is usually the case when using an adios stage code.
    kill_on_partial_failure = True

    # Options to pass to the scheduler (PBS or slurm)
    project = "CSC242"
    queue = "debug"

    sweeps = [

     # Each SweepGroup specifies a set of runs to be performed on a specified
     # number of nodes. Here we have 1 SweepGroup, which will run on 4 nodes.
     # On titan each executable consumes an entire node, even if it
     # doesn't make use of all processes on the node, so this will run
     # the first two instances at the same time across four nodes, and
     # start the last instance as soon as one of those two instances
     # finish. On a supercomputer without this limitation, with nodes
     # that have >14 processes, all three could be submitted at the same
     # time with one node unused.
     p.SweepGroup(nodes=4, # Number of nodes to run on
                  walltime=3600,# Required. Set walltime for scheduler job.
                  per_run_timeout=600,
                                # Optional. If set, each run in the sweep
                                # group will be killed if not complete
                                # after this many seconds.
                  max_procs=28, # Optional. Set max number of processes to run
                                # in parallel. Must fit on the nodes
                                # specified for each target machine, and
                                # each run in the sweep group must use no
                                # more then this number of processes. If
                                # not specified, will be set to the max
                                # of any individual run. Can be used to
                                # do runs in parallel, i.e. setting to 28
                                # for this experiment will allow two runs
                                # at a time, since 28/14=2.

      # Within a SweepGroup, each parameter_group specifies arguments for
      # each of the parameters required for each code. Number of runs is the
      # product of the number of options specified. Below, it is 3, as only
      # one parameter has >1 arguments. There are two types of parameters
      # used below: system ("ParamRunner") and positional command line
      # arguments (ParamCmdLineArg). Also supported: command line options
      # (ParamCmdLineOption), ADIOS XML config file (ParamAdiosXML)

      parameter_groups=
      [p.Sweep([

        # First, the parameters for the STAGE program

        # ParamRunner passes an argument to launch_multi_swift
        # nprocs: Number of processors (aka process) to use
        p.ParamRunner("stage", "nprocs", [2]),

        # ParamCmdLineArg passes a positional argument to the application
        # Arguments are:
          # 1) Code name (e.g., "stage"),
          # 2) Logical name for parameter, used in output;
          # 3) positional argument number;
          # 4) options
        p.ParamCmdLineArg("stage", "input", 1, ["heat.bp"]),
        p.ParamCmdLineArg("stage", "output", 2, ["staged.bp"]),
        p.ParamCmdLineArg("stage", "rmethod", 3, ["FLEXPATH"]),
        p.ParamCmdLineArg("stage", "ropt", 4, [""]),
        p.ParamCmdLineArg("stage", "wmethod", 5, ["MPI"]),
        p.ParamCmdLineArg("stage", "wopt", 6, [""]),
        p.ParamCmdLineArg("stage", "variables", 7, ["T,dT"]),
        p.ParamCmdLineArg("stage", "transform", 8,
                          ["none", "zfp:accuracy=.001", "sz:accuracy=.001"]),
        p.ParamCmdLineArg("stage", "decomp", 9, [2]),

        # Second, the parameters for the HEAT program

        p.ParamRunner("heat", "nprocs", [12]),
        p.ParamCmdLineArg("heat", "output", 1, ["heat"]),
        p.ParamCmdLineArg("heat", "xprocs", 2, [4]),
        p.ParamCmdLineArg("heat", "yprocs", 3, [3]),
        p.ParamCmdLineArg("heat", "xsize", 4, [40]),
        p.ParamCmdLineArg("heat", "ysize", 5, [50]),
        p.ParamCmdLineArg("heat", "steps", 6, [6]),
        p.ParamCmdLineArg("heat", "iterations", 7, [5]),
        ]),
      ]),
    ]
