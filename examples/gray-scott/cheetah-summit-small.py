from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.cheetah.parameters import SymLink
from codar.savanna.machines import SummitNode
import copy


def get_sweeps(ref_sweep_params):

    total_nprocs = 256
    all_sweeps = []

    # Sep nodes
    for sim_nprocs in range(total_nprocs//2, total_nprocs-32, 32):
        if (256%sim_nprocs != 0):
            continue 
        new_sweep_params = copy.deepcopy(ref_sweep_params)
        pdf_calc_nprocs = total_nprocs - sim_nprocs
        new_sweep_params[0].values = [sim_nprocs]
        new_sweep_params[1].values = [pdf_calc_nprocs]
     
        nc = SummitNode()
        nc2 = SummitNode()
        for i in range(sim_nprocs):
            if i < 16:
                nc.cpu[i] = "simulation:{}".format(i)
            elif i < 32:
                nc.cpu[i+5] = "simulation:{}".format(i)
        for i in range(pdf_calc_nprocs):
            if i < 16:
                nc2.cpu[i] = "pdf_calc:{}".format(i)
            elif i < 32:
                nc2.cpu[i+5] = "pdf_calc:{}".format(i)
        node_layout = [nc,nc2]
        sweep = p.Sweep (parameters = new_sweep_params, node_layout={'summit': node_layout})
        all_sweeps.append(sweep)

    # Share nodes
    ppn=32
    for pdf_calc_ppn in (4,8,16):
        sim_ppn = ppn - pdf_calc_ppn
        sim_nprocs = sim_ppn * 8
        if (256%sim_nprocs != 0):
            continue
        pdf_calc_nprocs = pdf_calc_ppn * 8
        new_sweep_params = copy.deepcopy(ref_sweep_params)
        new_sweep_params[0].values = [sim_nprocs]
        new_sweep_params[1].values = [pdf_calc_nprocs]
        nc = SummitNode()
        for i in range(sim_ppn):
            nc.cpu[i] = "simulation:{}".format(i)
        for i in range(sim_ppn, pdf_calc_ppn):
            nc.cpu[i] = "pdf_calc:{}".format(i)
        node_layout = [nc]
        sweep = p.Sweep (parameters = new_sweep_params, node_layout={'summit': node_layout})
        all_sweeps.append(sweep)

    return all_sweeps


class Gray_Scott(Campaign):
    name = "gray_scott"

    codes = [ ("simulation", dict(exe="gray-scott",
                                  adios_xml_file='adios2.xml')),
              ("pdf_calc", dict(exe="pdf_calc", adios_xml_file='adios2.xml')),
            ]

    supported_machines = ['local', 'titan', 'theta', 'summit']
    kill_on_partial_failure = True
    run_dir_setup_script = None
    run_post_process_script = "post-process.sh"
    umask = '027'
    scheduler_options = {'titan': {'project':'CSC249ADCD01', 'queue': 'batch'}, 'summit': {'project': 'csc299'} }
    app_config_scripts = {'local': 'setup.sh', 'titan': 'env_setup.sh', 'summit': 'setup.sh'}

    # Create a reference sweep parameter set
    sim_nprocs = p.ParamRunner     ('simulation', 'nprocs', [16])
    pdf_nprocs = p.ParamRunner     ('pdf_calc', 'nprocs', [16])

    sim_cla1 = p.ParamCmdLineArg   ('simulation', 'settings', 1, ["settings.json"])
    adios_engine = p.ParamADIOS2XML ('simulation', 'SimulationOutput', 'engine', [ {"SST":{}} ])
    settings_L = p.ParamConfig   ('simulation', 'domain_size', 'settings.json', 'L', [256])
    settings_num_steps = p.ParamConfig   ('simulation', 'num_steps', 'settings.json', 'steps', [50])
    settings_plot_gap = p.ParamConfig   ('simulation', 'plot_gap', 'settings.json', 'plotgap', [10])

    pdf_cla1 = p.ParamCmdLineArg   ('pdf_calc', 'infile', 1, ['gs.bp'])
    pdf_cla2 = p.ParamCmdLineArg   ('pdf_calc', 'outfile', 2, ['pdf'])

    ref_sweep_parameters = [sim_nprocs, pdf_nprocs, sim_cla1, adios_engine, settings_num_steps, settings_plot_gap, pdf_cla1, pdf_cla2]

    # Create new sweeps from the reference set
    all_sweeps = get_sweeps(ref_sweep_parameters)

    sweepGroup1 = p.SweepGroup ("sg-1", walltime=300*1*len(all_sweeps), per_run_timeout=300,
                                parameter_groups=all_sweeps, launch_mode='default',
                                nodes=12,
                                run_repetitions=0,
                                )
    sweeps = [sweepGroup1]


# Can you sweep over nprocs using the same node config, keeping nnodes constant? YES.
# Can you sweep over node-config for a constant nnodes?
    # depends - will that change nprocs for a code? YES. Then, no, you cannot sweep over node-config in the same group.
# Its very good that you can have multiple sweeps in a job

