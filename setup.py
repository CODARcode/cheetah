#!/usr/bin/env python3

from distutils.core import setup
import os


# Copy necessary scripts
tree = os.walk('scripts')
data_files = []
for dirname, subdirs, filenames in tree:
    filelist = []
    for filename in filenames:
        filelist.append(os.path.join(dirname, filename))
    data_files.append((dirname, filelist))


setup(name='cheetah',
      version='0.5',
      description='CODAR Experiment Harness',
      url='https://github.com/CODARcode/cheetah',
      packages=['codar'],
      data_files=data_files
      )
