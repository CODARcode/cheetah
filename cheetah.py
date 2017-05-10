#!/usr/bin/env python3
"""
Test main script for new python based cheetah config.

Usage:

 python3 cheetah.py -e /path/to/experiment.py -a /path/to/app/dir/ -m MACHINE_NAME -o /path/to/out/dir/

"""

import os
import argparse

from codar.cheetah.loader import load_experiment_class

def parse_args():
    parser = argparse.ArgumentParser(description="Cheetah experiment harness")
    parser.add_argument('-e', '--experiment-spec', required=True,
            help="Path to Python module containinig an experiment definition")
    parser.add_argument('-a', '--app-directory', required=True,
            help="Path to application directory containing executables")
    parser.add_argument('-m', '--machine', required=True,
            help="Name of machine to generate runner for")
    parser.add_argument('-o', '--output-directory', required=True,
            help="Output location where run scripts are saved")
    return parser.parse_args()

def main():
    args = parse_args()
    eclass = load_experiment_class(args.experiment_spec)
    machine_name = args.machine
    # TODO: handle case where cheetah is run on local linux but target
    # different machine with different locations for app and output
    app_dir = os.path.abspath(args.app_directory)
    output_dir = os.path.abspath(args.output_directory)

    e = eclass(machine_name, app_dir)
    e.make_experiment_run_dir(output_dir)


if __name__ == '__main__':
    main()
