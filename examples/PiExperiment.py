from codar.cheetah import Campaign
from codar.cheetah import parameters as p

from datetime import timedelta

class PiExperiment(Campaign):
    # Used in job names submitted to scheduler.
    name = "pi-small-one-node"

    # This application has a single executable, which we give the
    # friendly name 'pi' for later reference in parameter specification.
    # The executable path is taken relative to the application directory
    # specified on the cheetah command line.
    codes = [("pi", dict(exe="pi-gmp"))]

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

    # Optionally set umask for campaign directory and all processes spawned by
    # the workflow script when the campaign is run. Note that user rx
    # must be allowed at a minimum.
    # If set must be a string suitable for passing to the umask command.
    umask = '027'

    run_post_process_script = 'pi-post-run-compare-digits.py'

    # set this and uncomment the exit(1) in the script to test
    # triggering failure.
    #run_post_process_stop_group_on_failure = True

    sweeps = [
     p.SweepGroup(name="all-methods-small", nodes=4,
                  walltime=timedelta(minutes=30),
      parameter_groups=
      [p.Sweep([
        p.ParamCmdLineArg("pi", "method", 1, ["mc", "trap"]),
        p.ParamCmdLineArg("pi", "precision", 2, [64, 128, 256, 512, 1024]),
        p.ParamCmdLineArg("pi", "iterations", 3,
                          [10, 100, 1000, 1000000, 10000000]),
        ]),
       p.Sweep([
        p.ParamCmdLineArg("pi", "method", 1, ["atan"]),
        p.ParamCmdLineArg("pi", "precision", 2,
                          [64, 128, 256, 512, 1024, 2048, 4096]),
        p.ParamCmdLineArg("pi", "iterations", 3,
                          [10, 100, 1000, 10000, 100000]),
        ]),
      ]),
    ]
