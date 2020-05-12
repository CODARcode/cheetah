from codar.cheetah import parameters as p
import node_layouts as node_layouts


#----------------------------------------------------------------------------#
def posthoc_analysis():
    sweep_parameters = [
            p.ParamRunner       ('simulation', 'nprocs', [4]),
            p.ParamCmdLineArg   ('simulation', 'settings', 1, ["settings-files.json"]),
            p.ParamADIOS2XML    ('simulation', 'sim output engine', 'SimulationOutput', 'engine', [ {'BP4':{}} ]),

            p.ParamRunner       ('pdf_calc', 'nprocs', [4]),
            p.ParamCmdLineArg   ('pdf_calc', 'infile', 1, ['gs.bp']),
            p.ParamCmdLineArg   ('pdf_calc', 'outfile', 2, ['pdf.bp']),
    ]

    sweep = p.Sweep (parameters    = sweep_parameters,
                     rc_dependency = {'pdf_calc':'simulation'},
                     node_layout   = {'summit': node_layouts.separate_nodes()})

    return sweep


#----------------------------------------------------------------------------#
def insitu_analysis(node_layout):
    sweep_parameters = [
            p.ParamRunner       ('simulation', 'nprocs', [64]),
            p.ParamCmdLineArg   ('simulation', 'settings', 1, ["settings-staging.json"]),
            p.ParamADIOS2XML    ('simulation', 'sim output engine', 'SimulationOutput', 'engine', [ {'SST':{}} ]),

            p.ParamRunner       ('pdf_calc', 'nprocs', [4,8,16,32]),
            p.ParamCmdLineArg   ('pdf_calc', 'infile', 1, ['gs.bp']),
            p.ParamCmdLineArg   ('pdf_calc', 'outfile', 2, ['pdf.bp']),
    ]

    sweep = p.Sweep (parameters    = sweep_parameters,
                     rc_dependency = None,
                     node_layout   = {'summit': node_layout})

    return sweep


#----------------------------------------------------------------------------#
def asynchronous_zfp():
    sweep_parameters = [
            p.ParamRunner       ('simulation', 'nprocs', [64]),
            p.ParamCmdLineArg   ('simulation', 'settings', 1, ["settings-files.json"]),
            p.ParamADIOS2XML    ('simulation', 'sim output engine', 'SimulationOutput', 'engine', [ {'BP4':{}} ]),

            p.ParamRunner       ('pdf_calc', 'nprocs', [8]),
            p.ParamCmdLineArg   ('pdf_calc', 'infile', 1, ['gs.bp']),
            p.ParamCmdLineArg   ('pdf_calc', 'outfile', 2, ['pdf.bp']),
            p.ParamCmdLineArg   ('pdf_calc', 'bins', 3, [100]),
            p.ParamCmdLineArg   ('pdf_calc', 'write_orig_data', 4, ['YES']),
            p.ParamADIOS2XML    ('pdf_calc', 'zfp compression', 'PDFAnalysisOutput', 'var_operation', [ {"U": {"zfp": {'accuracy':0.001}}},
                                                                                                        {"U": {"zfp": {'accuracy':0.0001}}} ]),
    ]

    sweep = p.Sweep (parameters    = sweep_parameters,
                     rc_dependency = {'pdf_calc':'simulation'},
                     node_layout   = {'summit': node_layouts.separate_nodes()})

    return sweep

