from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.cheetah.parameters import SymLink
from codar.savanna.machines import SummitNode
import math
import copy

class ProducerConsumer(Campaign):

    name = "coupling-example"
    codes = [ 
              ("cleanup", dict(exe="cleanup.sh")),
              ("sim1", dict(exe="sim1.py", adios_xml_file='adios2.xml')),
              ("sim2", dict(exe="sim2.py", adios_xml_file='adios2.xml')),
              ("anly1", dict(exe="anly1.py", adios_xml_file='adios2.xml')),
              ("anly2", dict(exe="anly2.py", adios_xml_file='adios2.xml')),
              ("anlyc", dict(exe="anlyc.py", adios_xml_file='adios2.xml')),
              ("postproc", dict(exe="post-process.sh")),
            ]

    supported_machines = ['local', 'titan', 'theta', 'summit']
    kill_on_partial_failure = True
    run_dir_setup_script = None
    run_post_process_script = None
    umask = '027'
    scheduler_options = {'theta': {'project': '', 'queue': 'batch'},
                         'summit': {'project':'CSC299'}}
    app_config_scripts = {'local': 'localsetup.sh', 'summit': 'summit_env_setup.sh'}

    sweep1_parameters = [
            p.ParamRunner('cleanup', 'nprocs', [1]),
            p.ParamRunner('sim1', 'nprocs', [16]),
            p.ParamRunner('sim2', 'nprocs', [32]),
            p.ParamRunner('anly1', 'nprocs', [16]),
            p.ParamRunner('anly2', 'nprocs', [16]),
            p.ParamRunner('anlyc', 'nprocs', [16]),
            p.ParamRunner('postproc', 'nprocs', [1]),

            p.ParamCmdLineArg('sim1', 'size_per_pe', 1, [32]),
            p.ParamCmdLineArg('sim1', 'nsteps', 2, [5]),
            p.ParamCmdLineArg('sim2', 'size_per_pe', 1, [32]),
            p.ParamCmdLineArg('sim2', 'nsteps', 2, [5]),
    ]


    preprocN = SummitNode()
    preprocN.cpu[0] = 'cleanup:0'

    simNodeL = SummitNode()
    for i in range(8):
        simNodeL.cpu[i] = 'sim1:{}'.format(i)

    simNode2L = SummitNode()
    for i in range(8):
        simNode2L.cpu[i] = 'sim2:{}'.format(i)

    anlyL = SummitNode()
    for i in range(8):
        anlyL.cpu[i] = 'anly1:{}'.format(i)
    for i in range(8):
        anlyL.cpu[21+i] = 'anly2:{}'.format(i)

    anlyCL = SummitNode()
    for i in range(8):
        anlyCL.cpu[i] = "anlyc:{}".format(i)

    postprocL = SummitNode()
    for i in range(1):
        postprocL.cpu[i] = "postproc:{}".format(i)
    
    
    sweep1 = p.Sweep (node_layout = {'summit': [preprocN, simNodeL, simNode2L, anlyL, anlyCL, postprocL] },
            parameters = sweep1_parameters, rc_dependency={'anly1':'sim1', 'anly2':'sim2','anlyc':'anly1', 'postproc':'anlyc','cleanup':'postproc'})

    sweepGroup1 = p.SweepGroup ("sg-1",
                                walltime=300,
                                per_run_timeout=60,
                                parameter_groups=[sweep1],
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
    sweeps = {'MACHINE_ANY': [sweepGroup1]}

