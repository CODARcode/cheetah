import math
from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.savanna.machines import SummitNode
from codar.cheetah.parameters import SymLink
import node_layouts as node_layouts
import sweeps as sweeps
import copy


class GrayScott(Campaign):
    name = "gray_scott"

    codes = [ ("simulation", dict(exe="gray-scott", adios_xml_file='adios2.xml')),
              ("pdf_calc", dict(exe="pdf_calc", adios_xml_file='adios2.xml')), ]

    supported_machines = ['local', 'titan', 'theta', 'summit']
    kill_on_partial_failure = True
    run_dir_setup_script = None
    run_post_process_script = "cleanup.sh"
    umask = '027'
    scheduler_options = {'theta': {'project':'CSC249ADCD01', 'queue': 'default'},
                         'summit': {'project':'csc299'}}
    app_config_scripts = {'local': 'setup.sh', 'theta': 'env_setup.sh', 'summit':'env-setup.sh'}

    # Create the sweeps
    sw_posthoc               = sweeps.posthoc_analysis()
    sw_insitu_sep_nodes      = sweeps.insitu_analysis(node_layouts.separate_nodes())
    sw_insitu_shared_nodes   = sweeps.insitu_analysis(node_layouts.share_nodes())
    sw_insitu_shared_sockets = sweeps.insitu_analysis(node_layouts.share_nodes_sockets())
    sw_compression           = sweeps.asynchronous_zfp()

    # Create a SweepGroup and add the above Sweeps. Set batch job properties such as the no. of nodes, 
    sweepGroup1 = p.SweepGroup ("sg-1",
                                walltime=1200,
                                per_run_timeout=200,
                                parameter_groups=[sw_posthoc, sw_insitu_sep_nodes, sw_insitu_shared_nodes,
                                                  sw_insitu_shared_sockets, sw_compression],
                                launch_mode='default',
                                # tau_profiling=True,
                                # tau_tracing=False,
                                #nodes=16,
                                component_inputs = {'simulation': ['settings-files.json', 'settings-staging.json'], },
                                run_repetitions=2, )
    
    # Activate the SweepGroup
    sweeps = {'summit':[sweepGroup1]}

