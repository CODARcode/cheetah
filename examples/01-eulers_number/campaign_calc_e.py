from codar.cheetah import Campaign
from codar.cheetah import parameters as p

from datetime import timedelta


class CalcECampaign(Campaign):
    """Example campaign for calc_e.py, that runs both methods with
    different precision and iteration counts. This could be used to
    explore the convergence rate of each method and the necessary
    decimal precision needed (and the cost of using the Decimal class with
    higher precision)."""

    # Used in job names submitted to scheduler.
    name = "e-small-one-node"

    # This application has a single executable, which we give the
    # friendly name 'pi' for later reference in parameter specification.
    # The executable path is taken relative to the application directory
    # specified on the cheetah command line.
    codes = [("calc_e", dict(exe="calc_e.py"))]

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

    # Define the range of command line arguments to pass to the calc_e.py
    # program in each of many runs. Within each Sweep, all possible
    # combinations will be generated and included in the campaign output
    # directory. Because the 'n' parameter has different meaning for the
    # two methods, we must define separate Sweep groups for each method
    # to avoid running 'factorial' with too many iterations.
    sweeps = {'MACHINE_ANY':[
     # Sweep group defines a scheduler job. If different numbers of nodes
     # or node configurations are desired, then multiple SweepGroups can
     # be used. For most simple cases, only one is needed.
     p.SweepGroup(name="all-methods-small", nodes=1,
                  walltime=timedelta(minutes=30),
      parameter_groups=
      [p.Sweep([
        p.ParamCmdLineArg("calc_e", "method", 1, ["pow"]),
        # use higher values of n for this method, since it's doing a single
        # exponentiation and not iterating like factorial
        p.ParamCmdLineArg("calc_e", "n", 2,
                          [10, 100, 1000, 1000000, 10000000]),
        p.ParamCmdLineArg("calc_e", "precision", 3,
                          [64, 128, 256, 512, 1024]),
        ]),
       p.Sweep([
        p.ParamCmdLineArg("calc_e", "method", 1, ["factorial"]),
        p.ParamCmdLineArg("calc_e", "n", 2,
                          [10, 100, 1000]),
        # explore higher precision values for this method
        p.ParamCmdLineArg("calc_e", "precision", 3,
                          [64, 128, 256, 512, 1024, 2048, 4096]),
        ]),
      ]),
    ]}
