#!/usr/bin/env python3

import os
import sys
from setuptools import setup

def find_package_data(package_dir, data_subdir):
    search_dir = os.path.join(package_dir, data_subdir)
    paths = []
    for (path, directories, filenames) in os.walk(search_dir):
        for fname in filenames:
            fpath = os.path.join(path, fname)
            rel_fpath = fpath[len(package_dir)+1:]
            paths.append(rel_fpath)
    return paths

#print(find_package_data('codar/cheetah', 'data'))
#sys.exit()

cheetah_data = find_package_data('codar/cheetah', 'data')

setup(name='cheetah',
      version='0.5',
      description='CODAR Experiment Harness',
      long_description=open('README.md').read(),
      url='https://github.com/CODARcode/cheetah',
      packages=['codar.cheetah', 'codar.workflow'],
      package_data={'codar.cheetah': cheetah_data},
      scripts=['bin/cheetah.py', 'bin/workflow.py'],
      )
