#!/usr/bin/env python3

import os
import sys
from setuptools import setup, find_packages

def find_package_data(package_dir, data_subdir):
    search_dir = os.path.join(package_dir, data_subdir)
    paths = []
    for (path, directories, filenames) in os.walk(search_dir):
        for fname in filenames:
            fpath = os.path.join(path, fname)
            rel_fpath = fpath[len(package_dir)+1:]
            paths.append(rel_fpath)
    return paths

cheetah_data = find_package_data('codar/cheetah', 'data')

setup(name='cheetah',
      version='0.5.1',
      description='CODAR Experiment Harness',
      long_description=open('README.md').read(),
      url='https://github.com/CODARcode/cheetah',
      packages=find_packages(),
      package_data={'codar.cheetah': cheetah_data},
      include_package_data=True,
      scripts=['bin/cheetah', 'bin/workflow.py'],
      #install_requires="numpy>=1.11.0",
      )
