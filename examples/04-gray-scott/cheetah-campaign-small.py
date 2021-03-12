from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.cheetah.parameters import SymLink
from codar.cheetah.model import MPMDGroup
import copy


class GrayScott(Campaign):
    # A name for the campaign
    name = "gray_scott"

    # Define your workflow. Setup the applications that form the workflow.
    # exe may be an absolute path.
    # The adios xml file is automatically copied to the campaign directory.
    # 'runner_override' may be used to launch the code on a login/service node as a serial code
    #   without a runner such as aprun/srun/jsrun etc.
    codes = [ 
              ("simulation", dict(exe="gray-scott", adios_xml_file='adios2.xml')),
              ("pdf_calc", dict(exe="pdf_calc", adios_xml_file='adios2.xml', runner_override=False)),
              ("sim2", dict(exe="gray-scott", adios_xml_file='adios2.xml')),
              ("pdf2", dict(exe="pdf_calc", adios_xml_file='adios2.xml', runner_override=False)),
              ("analysis", dict(exe="ls")), 
            ]

    # List of machines on which this code can be run
    supported_machines = ['local', 'titan', 'theta']

    # Kill an experiment right away if any workflow components fail (just the experiment, not the whole group)
    kill_on_partial_failure = True

    # Any setup that you may need to do in an experiment directory before the experiment is run
    run_dir_setup_script = None

    # A post-process script that is run for every experiment after the experiment completes
    run_post_process_script = None

    # Directory permissions for the campaign sub-directories
    umask = '027'

    # Options for the underlying scheduler on the target system. Specify the project ID and job queue here.
    scheduler_options = {'theta': {'project':'CSC249ADCD01', 'queue': 'default'}}

    # A way to setup your environment before the experiment runs. Export environment variables such as LD_LIBRARY_PATH here.
    app_config_scripts = {'local': 'setup.sh', 'theta': 'env_setup.sh'}

    # Setup the sweep parameters for a Sweep
    sweep1_parameters = [
            # ParamRunner 'nprocs' specifies the no. of ranks to be spawned 
            p.ParamRunner       ('simulation', 'nprocs', [2]),

            # Create a ParamCmdLineArg parameter to specify a command line argument to run the application
            p.ParamCmdLineArg   ('simulation', 'settings', 1, ["settings.json"]),

            # Edit key-value pairs in the json file
            # Sweep over two values for the F key in the json file. Alongwith 4 values for the nprocs property for 
            #   the pdf_calc code, this Sweep will create 2*4 = 8 experiments.
            p.ParamConfig       ('simulation', 'feed_rate_U', 'settings.json', 'F', [0.01]),
            p.ParamConfig       ('simulation', 'kill_rate_V', 'settings.json', 'k', [0.048]),

            # Setup an environment variable
            # p.ParamEnvVar       ('simulation', 'openmp', 'OMP_NUM_THREADS', [4]),

            # Change the engine for the 'SimulationOutput' IO object in the adios xml file to SST for coupling.
            # As both the applications use the same xml file, you need to do this just once.
            p.ParamADIOS2XML    ('simulation', 'sim output engine', 'SimulationOutput', 'engine', [ {'InSituMPI':{}} ]),

            # Now setup options for the pdf_calc application.
            # Sweep over four values for the nprocs 
            p.ParamRunner       ('pdf_calc', 'nprocs', [1]),
            p.ParamCmdLineArg   ('pdf_calc', 'infile', 1, ['gs.bp']),
            p.ParamCmdLineArg   ('pdf_calc', 'outfile', 2, ['pdf.bp']),
            
            p.ParamRunner       ('analysis', 'nprocs', [1]),
            p.ParamRunner       ('sim2', 'nprocs', [2]),
            p.ParamCmdLineArg   ('sim2', 'settings', 1, ["settings-2.json"]),
            p.ParamConfig       ('sim2', 'output_filename', 'settings-2.json', 'output', ["gs-2.bp"]),
            p.ParamConfig       ('sim2', 'feed_rate_U', 'settings-2.json', 'F', [0.01]),
            p.ParamConfig       ('sim2', 'kill_rate_V', 'settings-2.json', 'k', [0.048]),
            p.ParamADIOS2XML    ('sim2', 'sim output engine', 'SimulationOutput', 'engine', [ {'InSituMPI':{}} ]),
            p.ParamRunner       ('pdf2', 'nprocs', [1]),
            p.ParamCmdLineArg   ('pdf2', 'infile', 1, ['gs-2.bp']),
            p.ParamCmdLineArg   ('pdf2', 'outfile', 2, ['pdf-2.bp']),
    ]

    # Create a Sweep object. This one does not define a node-layout, and thus, all cores of a compute node will be 
    #   utilized and mapped to application ranks.
    sweep1 = p.Sweep (parameters = sweep1_parameters, mpmd_launch = [MPMDGroup('simulation','pdf_calc'), MPMDGroup('sim2', 'pdf2')])

    # Create a SweepGroup and add the above Sweeps. Set batch job properties such as the no. of nodes, 
    sweepGroup1 = p.SweepGroup ("sg-1", # A unique name for the SweepGroup
                                walltime=3600,  # Total runtime for the SweepGroup
                                per_run_timeout=600,    # Timeout for each experiment                                
                                parameter_groups=[sweep1],   # Sweeps to include in this group
                                # nodes=128,  # No. of nodes for the batch job.
                                # tau_profiling=True,
                                # tau_tracing=False,
                                run_repetitions=0,  # No. of times each experiment in the group must be repeated (Total no. of runs here will be 3)
                                )
    
    # Activate the SweepGroup
    sweeps = {'MACHINE_ANY':[sweepGroup1]}

