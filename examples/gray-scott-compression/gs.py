from codar.cheetah import Campaign
from codar.cheetah import parameters as p

from datetime import timedelta


class GrayScott(Campaign):
    name = "Gray-Scott-A"
    codes = [("gray-scott", dict(exe="gray-scott", sleep_after=1)), ("pdf_calc", dict(exe="zchecker")) ]
    supported_machines = ['local', 'theta']
    scheduler_options = {
        "theta": {
            "queue": "debug-flat-quad",
            "project": "CSC249ADCD01",
        }
    }
    umask = '027'
    sweeps = [
     p.SweepGroup(name="Gray-Scott-A",
                  walltime=timedelta(minutes=30),
                  component_subdirs=True,
                  component_inputs={
                      'gray-scott': ['settingsA.json','adios2.xml'],
                      'pdf_calc': ['adios2.xml','sz.config','zc.config']
                  },
      parameter_groups=
      [p.Sweep([
          p.ParamCmdLineArg("gray-scott", "settings", 1, ["settingsA.json"]),
          p.ParamConfig("gray-scott", "L", "settingsA.json", "L",
                          [32, 64]),
          p.ParamConfig("gray-scott", "noise", "settingsA.json", "noise",
                          [0.01, 0.1]),
          p.ParamRunner('gray-scott', 'nprocs', [4] ),
          p.ParamCmdLineArg("pdf_calc", "input", 1, ["../gray-scott/gsA.bp"]),
          p.ParamCmdLineArg("pdf_calc", "output", 2, ["pdfA.bp"]),
          p.ParamCmdLineArg("pdf_calc", "slices", 3, [100]),
          p.ParamRunner('pdf_calc', 'nprocs', [1] )          
        ]),
      ]),
    ]

