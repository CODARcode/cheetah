from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.cheetah.parameters import SymLink
import copy

class Brusselator(Campaign):

    # A name for the campaign
    name = "Brusselator"

    # A list of the codes that will be part of the workflow
    # If there is an adios xml file associated with the codes, list it here
    # 'sleep_after' represents the time gap after which the next code is spawned
    codes = [ ("simulation", dict(exe="simulation/Brusselator", adios_xml_file='adios2_config.xml', sleep_after=None)),
              ("norm_calc",  dict(exe="analysis/norm_calc",     adios_xml_file='adios2_config.xml', ))
            ]

    # A list of machines that this campaign must be supported on
    supported_machines = ['local', 'titan', 'theta']

    # Option to kill an experiment (just one experiment, not the full sweep or campaign) if one of the codes fails
    kill_on_partial_failure = True

    # Some pre-processing in the experiment directory
    # This is performed when the campaign directory is created (before the campaign is launched)
    run_dir_setup_script = None

    # A post-processing script to be run in the experiment directory after the experiment completes
    # For example, removing some large files after the experiment is done
    run_post_process_script = None

    # umask applied to your directory in the campaign so that colleagues can view files
    umask = '027'

    # Scheduler information: job queue, account-id etc. Leave it to None if running on a local machine
    scheduler_options = {'titan': {'project':'CSC249ADCD01', 'queue': 'batch'}}

    # Setup your environment. Loading modules, setting the LD_LIBRARY_PATH etc.
    # Ensure this script is executable
    app_config_scripts = {'local': 'setup.sh', 'titan': 'env_setup.sh'}

    # Create the sweep parameters for a sweep 
    sweep1_parameters = [
            p.ParamRunner        ('simulation', 'nprocs', [4,]), # <-- how to sweep over values
            p.ParamCmdLineArg    ('simulation', 'output', 1, ['bru.bp']),
            p.ParamCmdLineArg    ('simulation', 'nx', 2, [32]),
            p.ParamCmdLineArg    ('simulation', 'ny', 3, [32]),
            p.ParamCmdLineArg    ('simulation', 'nz', 4, [32]),
            p.ParamCmdLineArg    ('simulation', 'steps', 5, [10,20,50]),  # sweep over these values. creates cross-product of runs with 'nprocs' above
            p.ParamCmdLineArg    ('simulation', 'plotgap', 6, [1]),

            p.ParamRunner        ('norm_calc', 'nprocs', [1]),
            p.ParamCmdLineArg    ('norm_calc', 'infile', 1, ['bru.bp']),
            p.ParamCmdLineArg    ('norm_calc', 'outfile', 2, ['norm_calc.out.bp']),
            p.ParamCmdLineArg    ('norm_calc', 'write_norms_only', 3, [1]),
            
            # p.ParamADIOS2XML     ('simulation', 'SimulationOutput', 'engine', [ {"InSituMPI": {}} ]),
            p.ParamADIOS2XML     ('simulation', 'SimulationOutput', 'engine', [ {"BPFile": {}} ]),
            # p.ParamADIOS2XML     ('simulation', 'SimulationOutput', 'engine', [ {"BPFile": {'Threads':1}},
            # p.ParamADIOS2XML     ('simulation', 'SimulationOutput', 'engine', [ {"BPFile": {'Threads':1}}, {"BPFile": {"ProfileUnits": "Microseconds"}} ]),
            
            # Use ParamCmdLineOption for named arguments
            # p.ParamCmdLineOption ('plotting', 'input_stream', '-i', ['bru.bp']),

            # How to set options in a key-value configuration file. Input file can be a json file.
            # File path can be relative to the path specified in '-a' or it can be absolute.
            # File will be copied to the working_dir automatically by Cheetah.
            # p.ParamKeyValue   ('simulation', 'feed_rate', 'input.conf', 'key', ['value']),

            # Sweep over environment variables
            # p.ParamEnvVar     ('simulation', 'openmp_stuff', 'OMP_NUM_THREADS', [4,8]),

            # Pass additional scheduler arguments.
            # p.ParamSchedulerArgs ('simulation', [{'-f':'hosts.txt'}])
    ]

    # Create a sweep
    # node_layout represents no. of processes per node
    sweep1 = p.Sweep (node_layout = {'titan': [{'simulation':16}, {'norm_calc': 4}] },  # simulation: 16 ppn, norm_calc: 4 ppn
                      parameters = sweep1_parameters)

    # Create a sweep group from the above sweep. You can place multiple sweeps in the group.
    # Each group is submitted as a separate job.
    sweepGroup1 = p.SweepGroup ("sg-tmp",
                                walltime=300,
                                per_run_timeout=60,
                                parameter_groups=[sweep1],
                                launch_mode='default',  # or MPMD
                                rc_dependency={'norm_calc':'simulation'},
                                # optional:
                                # nodes=10,
                                # component_subdirs = True, <-- codes have their own separate workspace in the experiment directory
                                # component_inputs = {'simulation': ['some_input_file'], 'norm_calc': [SymLink('some_large_file')] } <-- inputs required by codes
                                # max_procs = 64 <-- max no. of procs to run concurrently. depends on 'nodes'
                                )

    sweepGroup2 = copy.deepcopy(sweepGroup1)
    sweepGroup2.name = 'sg-2'
    
    # Sweep groups to be activated
    sweeps = [sweepGroup1, sweepGroup2]

