from codar.cheetah import Campaign
from codar.cheetah import parameters as p

from datetime import timedelta


class GrayScott(Campaign):
    name = "Gray-Scott-compression"
    codes = [("gray-scott", dict(exe="gray-scott", sleep_after=1)), ("compression", dict(exe="compression")) ]
    supported_machines = ['local', 'theta']
    scheduler_options = {
        "theta": {
            "queue": "debug-flat-quad",
            "project": "CSC249ADCD01",
        }
    }
    umask = '027'
    sweeps = {'MACHINE_ANY':[
     p.SweepGroup(name="gsc",
                  walltime=timedelta(minutes=30),
                  component_subdirs=True,
                  component_inputs={
                      'gray-scott': ['settings.json','adios2.xml'],
                      'compression': ['adios2.xml','sz.config','zc.config']
                  },
      parameter_groups=
      [p.Sweep([
          p.ParamCmdLineArg("gray-scott", "settings", 1, ["settings.json"]),
          p.ParamConfig("gray-scott", "L", "settings.json", "L",
                          [32]),
          p.ParamConfig("gray-scott", "noise", "settings.json", "noise",
                          [0.01]),
          p.ParamRunner('gray-scott', 'nprocs', [4] ),
          p.ParamCmdLineArg("compression", "input", 1, ["../gray-scott/gs.bp"]),
          p.ParamCmdLineArg("compression", "output", 2, ["CompressionOutput.bp"]),
          p.ParamCmdLineArg("compression", "compressor", 3, ["1"]),          
          p.ParamRunner('compression', 'nprocs', [1] )          
        ]),
      ]),
    ]}

