from codar.savanna import machines
from codar.cheetah import launchers

machine_launchers = dict()
machine_launchers[machines.local] = launchers.Launcher
machine_launchers[machines.sdg_tm76] = launchers.Launcher
machine_launchers[machines.rhea] = launchers.Launcher
machine_launchers[machines.rhea_gpu] = launchers.Launcher
machine_launchers[machines.cori] = launchers.Launcher
machine_launchers[machines.theta] = launchers.Launcher
machine_launchers[machines.titan] = launchers.Launcher
machine_launchers[machines.summit] = launchers.Launcher
machine_launchers[machines.deepthought2_cpu] = launchers.Launcher
machine_launchers[machines.deepthought2_gpu] = launchers.Launcher


def get_launcher(machine, output_directory, num_codes):
    return machine_launchers[machine](machine.name,
                                      machine.scheduler_name,
                                      machine.runner_name,
                                      output_directory, num_codes)
