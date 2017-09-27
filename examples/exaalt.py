from codar.cheetah import Campaign
from codar.cheetah import parameters as p

class Exaalt(Campaign):
    name = "Exaalt"
    codes = [("stage_write", dict(exe="stage_write/stage_write")),
             ("exaalt", dict(exe="pt_producer_global"))]

    supported_machines = ['titan']

    project = "PROJECT123"
    queue = "batch"

    kill_on_partial_failure = True

    inputs = ["states_list.txt"]

    sweeps = [

        # Staging and compression enabled
        p.SweepGroup(nodes=320,
            parameter_groups =
            [
            p.Sweep([

                p.ParamRunner("exaalt", "nprocs", [4096]),
                p.ParamCmdLineArg("exaalt", "states_list_file", 1,
                                  ["states_list.txt"]),
                #two million states
                p.ParamCmdLineArg("exaalt", "no_of_states", 2, [2097152]),
                p.ParamCmdLineArg("exaalt", "bp_output_file", 3, ["output.bp"]),
                p.ParamCmdLineArg("exaalt", "transport_method", 4,
                                  ["FLEXPATH"]),
                p.ParamCmdLineArg("exaalt", "transport_variables", 5, [""]),
                p.ParamCmdLineArg("exaalt", "transport_options", 6, ["none"]),

                p.ParamRunner("stage_write", "nprocs", [512,1024]),
                p.ParamCmdLineArg("stage_write", "input_bp_file", 1,
                                  ["output.bp"]),
                p.ParamCmdLineArg("stage_write", "output_bp_file", 2,
                                  ["staged.bp"]),
                p.ParamCmdLineArg("stage_write", "adios_read_method", 3,
                                  ["FLEXPATH"]),
                p.ParamCmdLineArg("stage_write", "read_method_params", 4, [""]),
                p.ParamCmdLineArg("stage_write", "adios_write_method", 5,
                                  ["POSIX"]),
                p.ParamCmdLineArg("stage_write",
                                  "write_method_params", 6, [""]),
                p.ParamCmdLineArg("stage_write", "variables_to_transform", 7,
                 ["atom_id,atom_type,px,py,pz,imx,imy,imz,atom_vid,vx,vy,vz"]),
                p.ParamCmdLineArg("stage_write", "transform_params", 8,
                                  ["none","zlib:9", "bzip2:9"]),
            ]),
        ]),

        # No staging or compression. Simulation writes data to disk.
        # This is the baseline test case.
        p.SweepGroup(nodes=256,
            parameter_groups =
            [
            p.Sweep([
                p.ParamRunner("exaalt", "nprocs", [4096]),
                p.ParamCmdLineArg("exaalt", "states_list_file", 1,
                                  ["states_list.txt"]),
                p.ParamCmdLineArg("exaalt", "no_of_states", 2,
                                  [10485760]),
                p.ParamCmdLineArg("exaalt", "bp_output_file", 3,
                                  ["output.bp"]),
                p.ParamCmdLineArg("exaalt", "transport_method", 4, ["POSIX"]),
                p.ParamCmdLineArg("exaalt", "transport_variables", 5, [""]),
                p.ParamCmdLineArg("exaalt", "transport_options", 6, ["none"]),
            ]),
        ]),
    ]
