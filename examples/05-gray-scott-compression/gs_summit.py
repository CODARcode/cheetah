from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.savanna.machines import SummitNode
from datetime import timedelta
import math

class GrayScott(Campaign):
    name = "Gray-Scott-compression"
    codes = [("gray-scott", dict(exe="gray-scott", sleep_after=1)), ("compress", dict(exe="compress")),
             ("zchecker", dict(exe="zchecker")), ("ftk", dict(exe="ftk")) ]
    supported_machines = ['local', 'theta', 'summit']
    scheduler_options = {
        "theta": {
            "queue": "debug-flat-quad",
            "project": "CSC249ADCD01",
        },
        "summit": {
            "project": "csc299",
        }
    }

    umask = '027'

    print("Here:1")

    shared_node = SummitNode()
    for i in range(4):
        shared_node.cpu[i] = "gray-scott:{}".format(i)
    shared_node.cpu[4] = "compress:0"
    for i in range(5, 5+4):
        shared_node.cpu[i] = "zchecker:{}".format(i-5)
    shared_node.cpu[9] = "ftk:0"
    shared_node_layout = [shared_node]
    
    print("Here:2")

    sweep_parameters = \
    [
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
        p.ParamRunner('ftk', 'nprocs', [1] )
    ]

    print("Here:3")

    sweep1 = p.Sweep(parameters = sweep_parameters, node_layout={'summit':shared_node_layout})

    print("Here:4")

    sweeps = \
    [
        p.SweepGroup(
            name = "gsc",
            walltime = timedelta(minutes=30),
            component_subdirs = True,
            component_inputs = {
                'gray-scott': ['settings.json','adios2.xml'],
                'compress': ['adios2.xml','sz.config', 'zfp.config', 'mgard.config'],
                'zchecker': ['zc.config','adios2.xml'],
                'ftk': ['adios2.xml']                      
            },
            parameter_groups = [sweep1]
        )
    ]

    print("Here:5")

