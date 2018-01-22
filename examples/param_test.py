from codar.cheetah import Campaign
from codar.cheetah import parameters as p

from datetime import timedelta


class param_test(Campaign):
    """
    Fake campaign designed to exercise all param types. Instead of real codes,
    bash scripts that echo args and cat files are used.

    NOTE: ParamAdiosXML is exercised by heat_transfer_*.py, not used here,
    all other types should be included.
    """
    # Used in job names submitted to scheduler.
    name = "param_test"

    # Scripts that just print args and exit. print1.sh also cats it's
    # config file.
    codes = [("print1", dict(exe="print1.sh")),
             ("print2", dict(exe="print2.sh")),
             ("print3", dict(exe="print3.sh"))]

    # Files to be copied from app dir to all run component directories,
    # e.g. for use with ParamConfig and ParamAdiosXML.
    inputs = ["all.conf"]

    # Document which machines the campaign is designed to run on. An
    # error will be raised if a different machine is specified on the
    # cheetah command line.
    supported_machines = ['local', 'cori', 'titan', 'theta']

    # Per machine scheduler options. Keys are the machine name, values
    # are dicts of name value pairs for the options for that machine.
    # Options must be explicitly supported by Cheetah, this is not
    # currently a generic mechanism.
    scheduler_options = {
        "cori": {
            "queue": "debug",
            "constraint": "haswell",
            "license": "SCRATCH,project",
        },
        "titan": {
            "queue": "debug",
            "project": "csc242",
        },
        "theta": {
            "queue": "debug-flat-quad",
            "project": "CSC249ADCD01",
        }
    }

    sweeps = [
     p.SweepGroup(name="test", nodes=4, walltime=timedelta(minutes=5),
      component_subdirs=True,
      component_inputs={
          'print1': ['print1.conf'],
          'print2': ['print2.ini'],
          'print3': ['print3.xml'],
      },
      parameter_groups=
      [p.Sweep([
        p.ParamCmdLineArg("print1", "arg1", 1, ["val1", "val2"]),
        p.ParamCmdLineArg("print1", "arg2", 2, [64, 128]),
        p.ParamCmdLineOption("print1", "opt1", "--opt1", [0.2, 0.3]),
        p.ParamCmdLineOption("print1", "derived", "--derived",
                   lambda d: d["print1"]["arg2"] * d["print2"]["opt1"]),
        p.ParamKeyValue("print1", "config1", "print1.conf", "config1",
                        ["c1", "c2"]),

        p.ParamCmdLineArg("print2", "arg1", 1, ["1lav"]),
        p.ParamCmdLineArg("print2", "arg2", 2, [2]),
        p.ParamCmdLineOption("print2", "opt1", "--opt1", [-100]),
        p.ParamKeyValue("print2", "kvconfig", "print2.ini", "mykey",
                        ["cv1", "cv2"]),

        p.ParamCmdLineArg("print3", "arg1", 1, ["val3.1"]),
        p.ParamConfig("print3", "xmlconfig", "print3.xml", "WIDGET_VALUE",
                      ["somevalue"]),
        ]),
      ]),
    ]
