"""
Templates for cheetah configuration. This should be used as little as possible:
ideally scripts should be stored separately and be independently testable.
For example, bash scripts can use environment variables for customization
instead of being templates.
"""


CAMPAIGN_ENV_TEMPLATE = """
export CODAR_CHEETAH_EXPERIMENT_DIR="{experiment_dir}"
export CODAR_CHEETAH_MACHINE_CONFIG="{machine_config}"
export CODAR_WORKFLOW_SCRIPT="{workflow_script_path}"
export CODAR_WORKFLOW_RUNNER="{workflow_runner}"
export CODAR_CHEETAH_WORKFLOW_LOG_LEVEL="{workflow_debug_level}"
"""

GROUP_ENV_TEMPLATE = """
export CODAR_CHEETAH_GROUP_WALLTIME="{walltime}"
export CODAR_CHEETAH_GROUP_MAX_PROCS="{max_procs}"
export CODAR_CHEETAH_SCHEDULER_ACCOUNT="{account}"
export CODAR_CHEETAH_SCHEDULER_QUEUE="{queue}"
export CODAR_CHEETAH_CAMPAIGN_NAME="{campaign_name}"
export CODAR_CHEETAH_GROUP_NAME="{group_name}"
export CODAR_CHEETAH_GROUP_NODES="{nodes}"
"""