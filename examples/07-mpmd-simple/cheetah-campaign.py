from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.savanna.machines import SummitNode, CrusherNode
from codar.savanna.machines import DTH2CPUNode
from codar.cheetah.parameters import SymLink
import copy

class ProducerConsumer(Campaign):
    name = "coupling-example"
    codes = [ ("p1", dict(exe="p1")),
              ("p2", dict(exe="p2"))
            ]
    
    supported_machines = ['local', 'summit', 'crusher']
    kill_on_partial_failure = True
    run_dir_setup_script = None
    run_post_process_script = None
    umask = '027'
    scheduler_options = {'summit': {'project':'csc143'}, 'crusher':{'project':'csc299'}}
    app_config_scripts = None
    
    sweep1_parameters = [
            p.ParamRunner ('p1', 'nprocs', [2]),
            p.ParamRunner ('p2', 'nprocs', [3]),

            p.ParamEnvVar ('p1', 'openmp', 'OMP_NUM_THREADS', [1]),
            p.ParamEnvVar ('p2', 'openmp', 'OMP_NUM_THREADS', [2]),
    ]

    summit_nc = SummitNode()
    for i in range(20):
        summit_nc.cpu[i]    = "p1:{}".format(i)
        summit_nc.cpu[i+21] = "p2:{}".format(i)

    sweep1 = p.Sweep (parameters = sweep1_parameters, 
                      node_layout={'summit': [summit_nc]})

    sg1 = p.SweepGroup ("sg-mpmd",
                        walltime=60,
                        per_run_timeout=60,
                        parameter_groups=[sweep1],
                        launch_mode='mpmd',
                        )
    
    sg2 = copy.deepcopy(sg1)
    sg2.name = "sg-nompmd"
    sg2.launch_mode = 'default'

    sg3 = copy.deepcopy(sg1)
    sg3.name = "sg-nompmd-tau"
    sg3.launch_mode = 'default'
    sg3.tau_profiling = True

    sg4 = copy.deepcopy(sg1)
    sg4.name = "sg-mpmd-tau"
    sg4.launch_mode = 'mpmd'
    sg4.tau_profiling = True
    
    sweeps = {'MACHINE_ANY':[sg1, sg2, sg3, sg4]}

