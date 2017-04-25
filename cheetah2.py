#!/usr/bin/env python3
"""
Test main script for new python based cheetah config.

Usage:

 python 3 cheetah2.py /path/to/experiment.py MACHINE_NAME /path/to/out/dir

"""

import sys

from codar.cheetah.loader import load_experiment_class

def main():
    # TODO: use argparse
    eclass = load_experiment_class(sys.argv[1])
    e = eclass()
    machine_name = sys.argv[2]
    output_dir = sys.argv[3]
    e.make_experiment_run_dir(machine_name, output_dir)


if __name__ == '__main__':
    main()
