"""
Old YAML based config example below for reference. Note that the new Python
based config has a higher level of abstraction.

experiment:
  name: pi-small-one-node
  app:
    script: run-pi.sh
  scheduler:
    type: pbs
    project: CSC242
    nodes: 1
    walltime: 01:00:00
  runner:
    type: aprun
    parameters:
      n: 1
      N: 1
  parameter-groups:
    - app-method: [mc, trap]
      app-iterations:
        range-start: 10
        range-end: 1000000000
        range-multiplier: 10
    - app-method: [atan]
      app-iterations: [10, 100, 1000]
      runner-n: [1, 2]
"""

from codar.cheetah import Experiment
from codar.cheetah import parameters as p

class PiExperiment(Experiment):
    name = "pi-small-one-node"
    # TODO: in future could support multiple executables if needed, with
    # the idea that they have same input/output/params, but are compiled
    # with different options. Could be modeled as p.ParamExecutable.
    app_exe = "pi-gmp"
    supported_machines = ['titan', 'local']

    runs = [
     p.SchedulerGroup(nodes=1,
      parameter_groups=
      [p.ParameterGroup([
        p.ParamCmdLineArg("method", 1, ["mc", "trap"]),
        p.ParamCmdLineArg("precision", 2, [10**i for i in range(1, 6)]),
        p.ParamCmdLineArg("iterations", 3, [10**i for i in range(1, 10)]),
        ]),
       p.ParameterGroup([
        p.ParamCmdLineArg("method", 1, ["atan"]),
        p.ParamCmdLineArg("precision", 2, [10**i for i in range(1, 10)]),
        p.ParamCmdLineArg("iterations", 3, [10**i for i in range(1, 6)]),
        ]),
      ]),
    ]
