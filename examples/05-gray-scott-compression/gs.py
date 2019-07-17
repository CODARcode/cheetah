from codar.cheetah import Campaign
from codar.cheetah import parameters as p

from datetime import timedelta


class GrayScott(Campaign):
    name = "Gray-Scott-compression"
    codes = [("gray-scott", dict(exe="gray-scott", sleep_after=1)), ("compress", dict(exe="compress")),
             ("zchecker", dict(exe="zchecker")), ("ftk", dict(exe="ftk")) ]
    supported_machines = ['local', 'theta']
    scheduler_options = {
        "theta": {
            "queue": "debug-flat-quad",
            "project": "CSC249ADCD01",
        }
    }
    umask = '027'
    sweeps = [
     p.SweepGroup(name="gsc",
                  walltime=timedelta(minutes=30),
                  component_subdirs=True,
                  component_inputs={
                      'gray-scott': ['settings.json','adios2.xml'],
                      'compress': ['adios2.xml','sz.config', 'zfp.config', 'mgard.config'],
                      'zchecker': ['zc.config','adios2.xml'],
                      'ftk': ['adios2.xml']                      
                  },
      parameter_groups=
      [p.Sweep([
          p.ParamCmdLineArg("gray-scott", "settings", 1, ["settings.json"]),
          p.ParamConfig("gray-scott", "L", "settings.json", "L",
                          [32]),
          p.ParamConfig("gray-scott", "noise", "settings.json", "noise",
                          [0.01]),
          p.ParamRunner('gray-scott', 'nprocs', [4] ),
          p.ParamCmdLineArg("compress", "compressor", 1, [3]),
          p.ParamCmdLineArg("compress", "input", 2, ["../gray-scott/gs.bp"]),          
          p.ParamCmdLineArg("compress", "original_output", 3, ["OriginalOutput.bp"]),
          p.ParamCmdLineArg("compress", "compressed_output", 4, ["CompressedOutput.bp"]),
          p.ParamCmdLineArg("compress", "decompressed_output", 5, ["DecompressedOutput.bp"]),          
          p.ParamKeyValue("compress", "tolerance", "mgard.config", "tolerance", [1.E-8, 1.E-1]),
          p.ParamRunner('compress', 'nprocs', [1] ),
          p.ParamCmdLineArg("zchecker", "original", 1, ["../compress/OriginalOutput.bp"]),
          p.ParamCmdLineArg("zchecker", "decompressed", 2, ["../compress/DecompressedOutput.bp"]),
          p.ParamRunner('zchecker', 'nprocs', [4] ),
          p.ParamCmdLineArg("ftk", "original", 1, ["../compress/OriginalOutput.bp"]),
          p.ParamCmdLineArg("ftk", "decompressed", 2, ["../compress/DecompressedOutput.bp"]),
          p.ParamCmdLineArg("ftk", "ftk_output", 3, ["FTK.bp"]),
          p.ParamCmdLineArg("ftk", "nthreads", 4, [4]),          
          p.ParamRunner('ftk', 'nprocs', [1] ),          
          
        ]),
      ]),
    ]

