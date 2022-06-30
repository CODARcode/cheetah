from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.savanna.machines import SummitNode, SpockNode, CrusherNode
from codar.cheetah.parameters import SymLink
import copy

class ProducerConsumer(Campaign):

    name = "coupling-example"
    codes = [ ("producer",  dict(exe="producer.py", env=None, adios_xml_file='adios2.xml', sleep_after=5, env_file='producer_env.sh')),]
    supported_machines = ['local', 'crusher']
    kill_on_partial_failure = True
    run_dir_setup_script = None
    run_post_process_script = None
    umask = '027'
    scheduler_options = {'crusher':{'project':'csc303'}}
    app_config_scripts = None
    
    sweep1_parameters = [
            p.ParamRunner       ('producer', 'nprocs', [16]),
            p.ParamCmdLineArg   ('producer', 'array_size_per_pe', 1, [1024*1024,]), # 1M, 2M, 10M
            p.ParamCmdLineArg   ('producer', 'num_steps', 2, [2]),
    ]

    # Crusher node layout
    #   4 cpus per rank, 4 ranks per node 
    nc = CrusherNode()
    for i in range(4):
        for j in range(4):
            nc.cpu[i*4+j] = "producer:{}".format(i)

    #   2 GPUs per rank
    for i in range(4):
        nc.gpu[i] = []
        for j in range(2):
            nc.gpu[i].append("producer:{}".format(i))

    crusher_node_layout = [nc]
    
    sweep1 = p.Sweep (parameters = sweep1_parameters, rc_dependency=None, node_layout={'crusher':crusher_node_layout})
    sweepGroup1 = p.SweepGroup ("sg-crusher",
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
                                run_repetitions=0, # <-- repeat each experiment this many times
                                # component_subdirs = True, <-- codes have their own separate workspace in the experiment directory
                                # component_inputs = {'simulation': ['some_input_file'], 'norm_calc': [SymLink('some_large_file')] } <-- inputs required by codes
                                # max_procs = 64 <-- max no. of procs to run concurrently. depends on 'nodes'
                                )
    
    # Sweep groups to be activated
    sweeps = {'crusher':[sweepGroup1]}

