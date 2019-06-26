from codar.cheetah import Campaign
from codar.cheetah import parameters as p

class Workflow_Name(Campaign):

    name =  # string

    codes = []  # list of dicts
    
    supported_machines = ['local', 'titan']

    app_config_scripts = # dict
    
    inputs =
    
    kill_on_partial_failure = True/False

    run_dir_setup_script = 

    run_post_process_script = 

    sosd_path = 

    scheduler_options = {
            "titan": { "project": "",
                       "queue": "batch" }
    }

    sweeps = [
     p.SweepGroup("name",
                  nodes =
                  walltime =
                  per_run_timeout =
                  component_subdirs = True/False
                  sosflow = True/False
                  component_inputs =


      parameter_groups = [
        
          p.Sweep([

              node_layout = 

              p.ParamRunner("<app_component>", "nprocs", [2048]),

              p.ParamCmdLineOption(...),
              p.ParamCmdLineArg(...),
              p.ParamADIOSXML(...),
              p.ParamKeyValue(...),

        ]),
      ]),
    ]
