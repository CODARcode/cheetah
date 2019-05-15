from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.cheetah.parameters import SymLink
import copy


class Brusselator(Campaign):
    name = "gray_scott"

    codes = [ ("simulation", dict(exe="gray-scott",
                                  adios_xml_file='adios2.xml')),
              ("pdf_calc", dict(exe="pdf_calc", adios_xml_file='adios2.xml')),
            ]

    supported_machines = ['local', 'titan', 'theta']
    kill_on_partial_failure = True
    run_dir_setup_script = None
    # run_post_process_script = "post-process.sh"
    umask = '027'
    scheduler_options = {'titan': {'project':'CSC249ADCD01', 'queue': 'batch'}}
    app_config_scripts = {'local': 'setup.sh', 'titan': 'env_setup.sh'}

    sweep1_parameters = [
            p.ParamRunner       ('simulation', 'nprocs', [2]),
            p.ParamCmdLineArg   ('simulation', 'settings', 1, ["settings.json"]),
            p.ParamConfig       ('simulation', 'feed_rate_U', 'settings.json', 'F', [0.01,0.02]),
            p.ParamConfig       ('simulation', 'kill_rate_V', 'settings.json', 'k', [0.048]),
            p.ParamEnvVar       ('simulation', 'openmp', 'OMP_NUM_THREADS', [4]),
            p.ParamADIOS2XML    ('simulation', 'SimulationOutput', 'engine', [ {'SST':{}} ]),

            p.ParamRunner       ('pdf_calc', 'nprocs', [1]),
            p.ParamCmdLineArg   ('pdf_calc', 'infile', 1, ['gs.bp']),
            p.ParamCmdLineArg   ('pdf_calc', 'outfile', 2, ['pdf']),
    ]

    #sweep1 = p.Sweep (parameters=sweep1_parameters, node_layout = {'titan': [{'simulation':16}, ] })
    sweep1 = p.Sweep (parameters = sweep1_parameters)

    sweep2_parameters = copy.deepcopy(sweep1_parameters)
    sweep2 = p.Sweep (node_layout = {'local': [{'simulation':16}, {'pdf_calc':4} ] },
                      parameters = sweep2_parameters)

    sweepGroup1 = p.SweepGroup ("sg-1", walltime=600, per_run_timeout=120,
                                #component_inputs = {"simulation": sim_input},
                                parameter_groups=[sweep1,sweep2], launch_mode='default',
                                nodes=3,
                                rc_dependency={'pdf_calc':'simulation',},
                                run_repetitions=0,
                                )
    sweeps = [sweepGroup1]

