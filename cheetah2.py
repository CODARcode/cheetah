#!/usr/bin/env python3
"""
Test main script for new python based cheetah config.

Usage:

 python3 cheetah2.py /path/to/experiment.py /path/to/app/exe MACHINE_NAME /path/to/out/dir

"""

import os
import sys

from codar.cheetah.loader import load_experiment_class

def main():
    # TODO: use argparse
    eclass = load_experiment_class(sys.argv[1])
    machine_name = sys.argv[2]
    # TODO: handle case where cheetah is run on local linux but target
    # different machine with different locations for app and output
    app_dir = os.path.abspath(sys.argv[3])
    output_dir = os.path.abspath(sys.argv[4])

    e = eclass(machine_name, app_dir)
    e.make_experiment_run_dir(output_dir)


if __name__ == '__main__':
    main()
