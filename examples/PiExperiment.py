from codar.cheetah import Experiment
from codar.cheetah import parameters as p

class PiExperiment(Experiment):
    name = "pi-small-one-node"
    # TODO: in future could support multiple executables if needed, with
    # the idea that they have same input/output/params, but are compiled
    # with different options. Could be modeled as p.ParamExecutable.
    codes = dict(pi="pi-gmp")
    supported_machines = ['swift']

    sweeps = [
     p.SchedulerGroup(nodes=1,
      parameter_groups=
      [p.ParameterGroup([
        p.ParamCmdLineArg("pi", "method", 1, ["mc", "trap"]),
        p.ParamCmdLineArg("pi", "precision", 2, [64, 128, 256, 512, 1024]),
        p.ParamCmdLineArg("pi", "iterations", 3,
                          [10, 100, 1000, 1000000, 10000000]),
        ]),
       p.ParameterGroup([
        p.ParamCmdLineArg("pi", "method", 1, ["atan"]),
        p.ParamCmdLineArg("pi", "precision", 2,
                          [64, 128, 256, 512, 1024, 2048, 4096]),
        p.ParamCmdLineArg("pi", "iterations", 3,
                          [10, 100, 1000, 10000, 100000]),
        ]),
      ]),
    ]
