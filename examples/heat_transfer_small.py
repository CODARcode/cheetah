from codar.cheetah import Campaign
from codar.cheetah import parameters as p

class HeatMap(Campaign):
    name = "heatmap-example"
    codes = dict(heat="heat_transfer_adios1",
                 stage="stage_write/stage_write")
    supported_machines = ['local', 'local_launch_multi']
    inputs = ["heat_transfer.xml"]

    sweeps = [
     p.SweepGroup(nodes=1,
      parameter_groups=
      [p.Sweep([
        p.ParamRunner("stage", "nprocs", [1]),
        p.ParamCmdLineArg("stage", "input", 1, ["heat.pb"]),
        p.ParamCmdLineArg("stage", "output", 2, ["staged.pb"]),
        p.ParamCmdLineArg("stage", "rmethod", 3, ["FLEXPATH"]),
        p.ParamCmdLineArg("stage", "ropt", 4, [""]),
        p.ParamCmdLineArg("stage", "wmethod", 5, ["MPI"]),
        p.ParamCmdLineArg("stage", "wopt", 6, [""]),
        p.ParamCmdLineArg("stage", "decomp", 7, [2]),
        p.ParamCmdLineArg("heat", "output", 1, ["heat"]),
        p.ParamCmdLineArg("heat", "xprocs", 2, [1]),
        p.ParamCmdLineArg("heat", "yprocs", 3, [2]),
        p.ParamRunner("heat", "nprocs", [2]),
        p.ParamAdiosXML("heat", "adios_transform:heat_transfer.xml:heat:T",
                        ["none", "zfp:accuracy=.001", "sz"]),
        p.ParamCmdLineArg("heat", "xsize", 4, [10]),
        p.ParamCmdLineArg("heat", "ysize", 5, [10]),
        p.ParamCmdLineArg("heat", "steps", 6, [6]),
        p.ParamCmdLineArg("heat", "iterations", 7, [10]),
        ]),
      ]),
    ]
