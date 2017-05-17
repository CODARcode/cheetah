from codar.cheetah import Experiment
from codar.cheetah import parameters as p

class HeatMap(Experiment):
    name = "heatmap-example"
    codes = dict(heat="heat_transfer_adios2",
                 stage="stage_write/stage_write")
    supported_machines = ['swift']

    runs = [
     p.SchedulerGroup(nodes=1,
      parameter_groups=
      [p.ParameterGroup([
        p.ParamRunner("stage", "nprocs", [2]),
        p.ParamCmdLineArg("stage", "input", 1, ["heat.pb"]),
        p.ParamCmdLineArg("stage", "output", 2, ["staged.pb"]),
        p.ParamCmdLineArg("stage", "method", 3, ["FLEXPATH", "DATASPACES"]),
        p.ParamCmdLineArg("heat", "output", 1, ["heat"]),
        p.ParamCmdLineArg("heat", "xprocs", 2, [4]),
        p.ParamCmdLineArg("heat", "yprocs", 3, [3]),
        p.ParamRunner("heat", "nprocs", [12]),
        p.ParamCmdLineArg("heat", "xsize", 4, [40]),
        p.ParamCmdLineArg("heat", "ysize", 5, [50]),
        p.ParamCmdLineArg("heat", "steps", 6, [6]),
        p.ParamCmdLineArg("heat", "iterations", 2, [500]),
        ]),
      ]),
    ]
