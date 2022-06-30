EXE_LAUNCH_FILE_TEMPLATE = """
#!/bin/bash

# Bash script will terminate if any following commands fail
set -e

# User-defined environment setup
{user_defined_env_setup}

# Launch the application
{app_launch_command}

"""
