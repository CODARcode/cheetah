"""
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

from codar import cheetah

class PiExperiment(Experiment):
    machines = [cheetah.MachineTitan, cheetah.MachineLocal]
    name = "pi-small-one-node"

    app_script = "run-pi.sh"

    runs = [
     SchedulerGroup(nodes=1,
      [ParameterGroup([
        ParamCmdLineArg("method", 1, ["mc", "trap"]),
        ParamCmdLineArg("precision", 2, [10**i for i in range(1, 10)]),
        ParamCmdLineArg("iterations", 3, [10**i for i in range(1, 10)]),
        ]),
       ParameterGroup([
        ParamCmdLineArg("method", 1, ["mc", "trap"]),
        ParamCmdLineArg("precision", 2, [10**i for i in range(1, 10)]),
        ParamCmdLineArg("iterations", 3, [10**i for i in range(1, 10)]),
        ParamRunner("cpus", 1),
        ParamRunner("tasks", 1),
        ]),
      ]),
    ]
