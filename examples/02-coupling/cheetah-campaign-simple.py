from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.savanna.machines import SummitNode
from codar.savanna.machines import DTH2CPUNode
from codar.cheetah.parameters import SymLink
import copy

class ProducerConsumer(Campaign):

    # A name for the campaign
    name = "coupling-example"

    # WORKFLOW SETUP
    #---------------
    # A list of the codes that will be part of the workflow
    # If there is an adios xml file associated with the codes, list it here
    # 'sleep_after' represents the time gap after which the next code is spawned
    # Use runner_override to run the code without the default launcher (mpirun/aprun/jsrun etc.). This runs the 
    #   code as a serial application
    codes = [ ("producer",  dict(exe="producer.py",         adios_xml_file='adios2.xml', sleep_after=5)),
            ]

    # CAMPAIGN SETTINGS
    #------------------
    # A list of machines that this campaign is supported on
    supported_machines = ['local', 'titan', 'theta', 'summit', 'deepthought2_cpu', 'sdg_tm76']

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
    scheduler_options = {'theta': {'project': '', 'queue': 'batch'},
                         'summit': {'project':''}}

    # Setup your environment. Loading modules, setting the LD_LIBRARY_PATH etc.
    # Ensure this script is executable
    app_config_scripts = {'local': 'setup.sh', 'summit': 'env_setup.sh'}

    # PARAMETER SWEEPS
    #-----------------
    # Setup how the workflow is run, and what values to 'sweep' over
    # Use ParamCmdLineArg to setup a command line arg, ParamCmdLineOption to setup a command line option, and so on.
    sweep1_parameters = [
            p.ParamRunner       ('producer', 'nprocs', [2]),
            p.ParamCmdLineArg   ('producer', 'array_size_per_pe', 1, [1024*1024,]), # 1M, 2M, 10M
            p.ParamCmdLineArg   ('producer', 'num_steps', 2, [2]),
            p.ParamADIOS2XML    ('producer', 'engine_sst', 'producer', 'engine', [ {"BP4": {}} ]),
    ]

    # Create a sweep
    # node_layout represents no. of processes per node
    sweep1 = p.Sweep (parameters = sweep1_parameters, rc_dependency=None)

    # Create a sweep group from the above sweep. You can place multiple sweeps in the group.
    # Each group is submitted as a separate job.
    sweepGroup1 = p.SweepGroup ("sg-1",
                                walltime=300,
                                per_run_timeout=60,
                                parameter_groups=[sweep1],
                                launch_mode='default',  # or MPMD
                                tau_profiling=False,
                                tau_tracing=False,
                                # optional:
                                # nodes=10,
                                # tau_profiling=True,
                                # tau_tracing=False,
                                # run_repetitions=2, # <-- repeat each experiment this many times
                                # component_subdirs = True, <-- codes have their own separate workspace in the experiment directory
                                # component_inputs = {'simulation': ['some_input_file'], 'norm_calc': [SymLink('some_large_file')] } <-- inputs required by codes
                                # max_procs = 64 <-- max no. of procs to run concurrently. depends on 'nodes'
                                )

    # Sweep groups to be activated
    sweeps = {'MACHINE_ANY': [sweepGroup1]}

