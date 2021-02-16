import os
import sys
import stat
import json
import math
import shlex
import inspect
import getpass
from pathlib import Path
from collections import OrderedDict
import warnings
import pdb

from codar.savanna import machines
from codar.savanna.node_layout import NodeLayout
from codar.cheetah import parameters, config, templates, exc, machine_launchers
from codar.cheetah.launchers import Launcher
from codar.cheetah.helpers import copy_to_dir, copy_to_path, copytree_to_dir
from codar.cheetah.helpers import relative_or_absolute_path, \
    relative_or_absolute_path_list, parse_timedelta_seconds
from codar.cheetah.parameters import SymLink
from codar.cheetah.adios_params import xml_has_transport
from codar.cheetah.parameters import ParamCmdLineArg
from codar.cheetah.exc import CheetahException


class RunComponent(object):
    def __init__(self, name, exe, args, sched_args, nprocs, working_dir,
                 component_inputs=None, sleep_after=None,
                 linked_with_sosflow=False, adios_xml_file=None,
                 env=None, timeout=None, hostfile=None, runner_override=False):
        self.name = name
        self.exe = exe
        self.args = args
        self.sched_args = sched_args
        self.nprocs = nprocs
        self.sleep_after = sleep_after
        self.env = env or {}
        self.timeout = timeout
        self.working_dir = working_dir
        self.component_inputs = component_inputs
        self.linked_with_sosflow = linked_with_sosflow
        self.adios_xml_file = adios_xml_file
        self.hostfile = hostfile
        self.after_rc_done = None
        self.runner_override = runner_override
        self.num_nodes = 0

    def init_2(self):
        pass

    def copy_input_files_to_workspace(self):
        """
        Copy all required input files to the working dir
        """

        # Copy adios file to work dir
        if self.adios_xml_file:
            copy_to_dir(self.adios_xml_file, self.working_dir)

        # Copy other input files marked under 'component_inputs'
        if self.component_inputs is None: return

        for input_file in self.component_inputs:
            dest = os.path.join(self.working_dir, os.path.basename(input_file))

            # input file is a symlink
            if type(input_file) == SymLink:
                os.symlink(input_file, dest)
            # input file is a regular file
            elif os.path.isfile(input_file):
                copy_to_dir(input_file, self.working_dir)
            # input file is a directory
            elif os.path.isdir(input_file):
                copytree_to_dir(input_file, dest)
            else:
                raise exc.CheetahException("Could not determine the type of "
                    "required input {}".format(input_file))

    def as_fob_data(self):
        data = dict(name=self.name,
                    exe=self.exe,
                    args=self.args,
                    sched_args=self.sched_args,
                    nprocs=self.nprocs,
                    working_dir=self.working_dir,
                    sleep_after=self.sleep_after,
                    linked_with_sosflow=self.linked_with_sosflow,
                    adios_xml_file=self.adios_xml_file,
                    hostfile=self.hostfile,
                    after_rc_done=None,
                    num_nodes=self.num_nodes,
                    runner_override=self.runner_override)
        if self.env:
            data['env'] = self.env
        if self.timeout:
            data['timeout'] = self.timeout
        if self.hostfile:
            data['hostfile'] = self.working_dir + "/" + self.hostfile
        if self.after_rc_done:
            data['after_rc_done'] = self.after_rc_done.name
        return data

