from codar.cheetah import Campaign
from codar.cheetah import parameters as p

class HeatTransfer(Campaign):
    """Small example to run the heat_transfer application with stage_write,
    using no compression, zfp, or sz. All other options are fixed, so there
    are only three runs."""

    name = "heat-transfer-small"
    codes = dict(heat="heat_transfer_adios2",
                 stage="stage_write/stage_write")
    supported_machines = ['local', 'titan']
    inputs = ["heat_transfer.xml"]

    sweeps = [
     p.SweepGroup(nodes=1,
      parameter_groups=
      [p.Sweep([
        p.ParamRunner("stage", "nprocs", [2]),
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
