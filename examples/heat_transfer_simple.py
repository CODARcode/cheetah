#
# This example illustrates the format of a Cheetah configuration file
#
from codar.cheetah import Campaign, Code
from codar.cheetah import parameters as p

class HeatTransfer(Campaign):
    """Small example to run the heat_transfer application with stage_write,
    using no compression, zfp, or sz. All other options are fixed, so there
    are only three runs."""

    name = "heat-transfer-simple"

    # This applications consists of two codes, with nicknames "heat" and
    # "stage", exe locations as specified, and a delay of 5 seconds
    # between starting stage and heat.
    codes = [
        Code(name='stage',
             exe='stage_write/stage_write',
             sleep_after=5,
             command_line_args=["input", "output", "rmethod", "ropt",
                                "wmethod", "wopt", "variables",
                                "transform", "decomp"]),
        Code(name='heat',
             exe="heat_transfer_adios2",
             sleep_after=0,
             command_line_args=["output", "xprocs", "yprocs", "xsize",
                                "ysize", "steps", "iterations"],
             command_line_options=[...],
             other_parameters=[
                 p.ParamAdiosXML("transport",
                                 "adios_transport:heat_transfer.xml:heat")
             ])
    ]

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

    # Options to pass to the scheduler (PBS or slurm). These are set per
    # target machine, since likely different options will be needed for
    # each.
    scheduler_options = {
        "titan": { "project": "CSC242",
                   "queue": "debug" }
    }

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
     p.SweepGroup("small_scale",
                  nodes=4, # Number of nodes to run on
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
      [p.Sweep(

        # First, the parameters for the STAGE program

        # ParamRunner passes an argument to launch_multi_swift
        # nprocs: Number of processors (aka process) to use
        {
            "stage": {
                "nprocs": [2],
                "input": ["heat.bp"],
                "output": ["staged.bp"],
                "rmethod": ["FLEXPATH"],
                "ropt": [""],
                "wmethod": ["MPI"],
                "wopt": [""],
                "variables": ["T,dT"],
                "transform": ["none", "zfp:accuracy=.001", "sz:accuracy=.001"],
                "decomp": [2],
            },

            "heat": {
                "nprocs": lambda pm: pm["xprocs"] * pm["yprocs"],
                "output": ["heat"],
                "xprocs": [4],
                "yprocs": [3],
                "xsize": [40],
                "ysize": [50],
                "steps": [6],
                "iterations": [5],
                "transport": ["MPI_AGGREGATE:num_aggregators=4;num_osts=44",
                              "POSIX",
                              "FLEXPATH"],
            }
        }),
      ]),
    ]
