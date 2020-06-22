from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.cheetah.parameters import SymLink
from codar.savanna.machines import SummitNode
import math
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
              ("mean_calc", dict(exe="mean_calculator.py",  adios_xml_file='adios2.xml', runner_override=False))
            ]

    # CAMPAIGN SETTINGS
    #------------------
    # A list of machines that this campaign is supported on
    supported_machines = ['local', 'titan', 'theta', 'summit']

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
                         'summit': {'project':'CSC299'}}

    # Setup your environment. Loading modules, setting the LD_LIBRARY_PATH etc.
    # Ensure this script is executable
    app_config_scripts = {'local': 'setup.sh', 'summit': 'env_setup.sh'}

    # PARAMETER SWEEPS
    #-----------------
    # Setup how the workflow is run, and what values to 'sweep' over
    # Use ParamCmdLineArg to setup a command line arg, ParamCmdLineOption to setup a command line option, and so on.
    sweep1_parameters = [
            p.ParamRunner       ('producer', 'nprocs', [128]),
            p.ParamRunner       ('mean_calc', 'nprocs', [36]),
            p.ParamCmdLineArg   ('producer', 'array_size_per_pe', 1, [1024*1024]), # 1M, 2M, 10M
            p.ParamCmdLineArg   ('producer', 'num_steps', 2, [10]),
            p.ParamADIOS2XML    ('producer', 'staging', 'producer', 'engine', [ {"SST": {}} ]),
    ]

    shared_node = SummitNode()
    for i in range(18):
        shared_node.cpu[i] = "producer:{}".format(math.floor(i / 6))
        shared_node.cpu[i + 21] = "producer:{}".format(math.floor((i + 18) / 6))
    for i in range(3):
        shared_node.cpu[i + 18] = "mean_calc:0"
        shared_node.cpu[i + 18 + 21] = "mean_calc:0"
    for i in range(6):
        shared_node.gpu[i] = ["producer:{}".format(i)]
    shared_node_layout = [shared_node]
    
    
    shared_node_1_per_rank = SummitNode()
    for i in range(18):
        shared_node_1_per_rank.cpu[i] = "producer:{}".format(i)
        shared_node_1_per_rank.cpu[i + 21] = "producer:{}".format(i+18)
    for i in range(3):
        shared_node_1_per_rank.cpu[i + 18] = "mean_calc:{}".format(i)
        shared_node_1_per_rank.cpu[i + 18 + 21] = "mean_calc:{}".format(i+3)
    for i in range(6):
        shared_node_1_per_rank.gpu[i] = ["producer:{}".format(i)]
    shared_node_layout_2 = [shared_node_1_per_rank]
    
    shared_node_shared_gpu = SummitNode()
    for i in range(18):
        shared_node_shared_gpu.cpu[i] = "producer:{}".format(math.floor(i / 6))
        shared_node_shared_gpu.cpu[i + 21] = "producer:{}".format(math.floor((i + 18) / 6))
    for i in range(3):
        shared_node_shared_gpu.cpu[i + 18] = "mean_calc:0"
        shared_node_shared_gpu.cpu[i + 18 + 21] = "mean_calc:0"
    shared_node_shared_gpu.gpu[0] = ["producer:0"]
    shared_node_shared_gpu.gpu[1] = ["producer:0", "producer:1",]
    shared_node_shared_gpu.gpu[2] = ["producer:0", "producer:1",'mean_calc:0']
    shared_node_layout_3 = [shared_node_shared_gpu]
    
    sep_node_producer = SummitNode()
    sep_node_mean_calc = SummitNode()
    for i in range(18):
        sep_node_producer.cpu[i] = "producer:{}".format(math.floor(i / 6))
    for i in range(3):
        sep_node_mean_calc.cpu[i + 18] = "mean_calc:0"
        sep_node_mean_calc.cpu[i + 18 + 21] = "mean_calc:0"
    for i in range(3):
        sep_node_producer.gpu[i] = ["producer:{}".format(i)]
    sep_node_layout = [sep_node_producer, sep_node_mean_calc]

    # Create a sweep
    # node_layout represents no. of processes per node
    sweep1 = p.Sweep (node_layout = {'summit': shared_node_layout },
                      parameters = sweep1_parameters, rc_dependency=None)
    sweep2 = p.Sweep (node_layout = {'summit': shared_node_layout_2 },
                      parameters = sweep1_parameters, rc_dependency=None)
    sweep3 = p.Sweep (node_layout = {'summit': shared_node_layout_3 },
                      parameters = sweep1_parameters, rc_dependency=None)
    sweep4 = p.Sweep (node_layout = {'summit': sep_node_layout},
                      parameters = sweep1_parameters, rc_dependency=None)

    # Create a sweep group from the above sweep. You can place multiple sweeps in the group.
    # Each group is submitted as a separate job.
    sweepGroup1 = p.SweepGroup ("sg-1",
                                walltime=300,
                                per_run_timeout=60,
                                parameter_groups=[sweep1, sweep2, sweep3, sweep4],
                                launch_mode='default',  # or MPMD
                                # optional:
                                # tau_profiling=True,
                                # tau_tracing=False,
                                # nodes=10,
                                # component_subdirs = True, <-- codes have their own separate workspace in the experiment directory
                                # component_inputs = {'producer': ['some_input_file'], 'norm_calc': [SymLink('some_large_file')] } <-- inputs required by codes
                                # max_procs = 64 <-- max no. of procs to run concurrently. depends on 'nodes'
                                )

    # Sweep groups to be activated
    sweeps = {'summit': [sweepGroup1]}

