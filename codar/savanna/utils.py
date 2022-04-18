import os

STDOUT_NAME = 'codar.workflow.stdout'
STDERR_NAME = 'codar.workflow.stderr'
RETURN_NAME = 'codar.workflow.return'
WALLTIME_NAME = 'codar.workflow.walltime'

def get_path(default_dir, default_name, specified_name):
    path = specified_name or default_name
    if not path.startswith("/"):
        path = os.path.join(default_dir, path)
    return path
