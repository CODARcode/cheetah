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
from codar.cheetah.helpers import copy_to_dir, copy_to_path
from codar.cheetah.helpers import relative_or_absolute_path, \
    relative_or_absolute_path_list, parse_timedelta_seconds
from codar.cheetah.parameters import SymLink
from codar.cheetah.adios_params import xml_has_transport
from codar.cheetah.parameters import ParamCmdLineArg
from codar.cheetah.exc import CheetahException
from codar.cheetah.runcomponent import RunComponent

class Run(object):
    """
    Class representing how to actually run an instance on a given environment,
    including how to generate arg arrays for executing each code required for
    the application.

    TODO: create a model shared between workflow and cheetah, i.e. codar.model
    """
    def __init__(self, instance, codes, codes_path, run_path, inputs,
                 machine, node_layout, rc_dependency, component_subdirs,
                 sosflow_profiling, sosflow_analyis, component_inputs=None):
        self.instance = instance
        self.codes = codes
        self.codes_path = codes_path
        self.run_path = run_path
        self.run_id = os.path.basename(run_path)
        self.inputs = inputs
        self.machine = machine
        # Note: the layout will be modified if sosflow is set, so it's
        # important to use a copy.
        self.node_layout = node_layout.copy()
        self.component_subdirs = component_subdirs
        self.sosflow_profiling = sosflow_profiling
        self.sosflow_analysis = sosflow_analyis
        self.component_inputs = component_inputs
        self.total_nodes = 0
        self.run_components = self._get_run_components()

        # populate nodelayout to contain all RCs
        # self.node_layout.populate_remaining([rc.name for rc in
        #                                      self.run_components],
        #                                     self.machine.processes_per_node)

        # Get the RCs that this rc depends on
        # This must be done before the total no. of nodes are calculated
        # below
        self._populate_rc_dependency(rc_dependency)

        # Set the total nodes after the run components are initialized above
        self._set_total_nodes()

        # Filename in the run dir that will store the size of the run dir
        # prior to submitting the campaign
        self._pre_submit_dir_size_fname = \
            ".codar.cheetah.pre_submit_dir_size.out"

    def _get_run_components(self):
        comps = []
        codes_argv = self._get_codes_argv_ordered()
        for (target, argv) in codes_argv.items():
            exe_path = self.codes[target]['exe']
            sleep_after = self.codes[target].get('sleep_after', 0)
            runner_override = self.codes[target].get('runner_override', False)
            assert type(runner_override) == bool, \
                "The runner_override property for the " + target + " codes " \
                "object must be a boolean value True/False"

            # Set separate subdirs for individual components if requested
            if self.component_subdirs:
                working_dir = os.path.join(self.run_path, target)
            else:
                working_dir = self.run_path

            component_inputs = None
            if self.component_inputs:
                component_inputs = self.component_inputs.get(target)
            if component_inputs:
                assert type(component_inputs) is list, \
                    "component_inputs for {} must be a list.".format(target)
                # Get the full path of inputs
                # Separate the strings from symlinks to preserve their type
                str_inputs = [input for input in component_inputs if type(
                    input) == str]
                str_inputs = relative_or_absolute_path_list(self.codes_path,
                                                            str_inputs)

                symlinks = [input for input in component_inputs if type(
                    input) == SymLink]
                symlinks = relative_or_absolute_path_list(self.codes_path,
                                                          symlinks)
                symlinks = [SymLink(input) for input in symlinks]
                component_inputs = str_inputs + symlinks

            linked_with_sosflow = self.codes[target].get(
                'linked_with_sosflow', False)

            adios_xml_file = self.codes[target].get('adios_xml_file', None)
            if adios_xml_file:
                adios_xml_file = relative_or_absolute_path(
                    self.codes_path, adios_xml_file)

            sched_args = self.instance.get_sched_opts(target)

            comp = RunComponent(name=target, exe=exe_path, args=argv,
                                sched_args=sched_args,
                                nprocs=self.instance.get_nprocs(target),
                                sleep_after=sleep_after,
                                working_dir=working_dir,
                                component_inputs=component_inputs,
                                linked_with_sosflow=linked_with_sosflow,
                                adios_xml_file=adios_xml_file,
                                hostfile=self.instance.get_hostfile(target),
                                runner_override=runner_override)
            comps.append(comp)
        return comps

    def _populate_rc_dependency(self, rc_dependency):
        """
        Retrieve the object reference for RCs and populate their
        after_rc_done field with object references
        """
        if rc_dependency is not None:
            for k,v in rc_dependency.items():
                assert type(k) is str, "rc_dependency dictionary key must " \
                                        "be code name"
                assert v is not None, "Dict value cannot be None"
                assert type(v) is str, "rc_dependency dictionary value must " \
                                       "be a string"

                k_rc = self._get_rc_by_name(k)
                v_rc = self._get_rc_by_name(v)
                k_rc.after_rc_done = v_rc

                # k_rc = self._get_rc_by_name(k)
                # assert k_rc is not None, "RC {0} not found".format(k)
                # v_rc = self._get_rc_by_name(v)
                # assert v_rc is not None, "RC {0} not found".format(v)
                # k_rc.after_rc_done = v_rc

    def get_fob_data_list(self):
        return [comp.as_fob_data() for comp in self.run_components]

    def _get_codes_argv_ordered(self):
        """Wrapper around instance.get_codes_argv which uses correct order
        from self.codes OrderedDict."""
        codes_argv = self.instance.get_codes_argv()
        undefined_codes = set(codes_argv.keys()) - set(self.codes.keys())
        if undefined_codes:
            raise exc.CampaignParseError(
                'Parameter references undefined codes(s): %s'
                % ','.join(undefined_codes))
        # Note that a given Run may not use all codes, e.g. for base
        # case app runs that don't use adios stage_write or dataspaces.
        return OrderedDict((k, codes_argv[k]) for k in self.codes.keys()
                           if k in codes_argv)

    def get_total_nprocs(self):
        return sum(rc.nprocs for rc in self.run_components)

    def _get_rc_by_name(self, name):
        for rc in self.run_components:
            if rc.name == name:
                return rc

        raise CheetahException("Did not find run component with name {0}"
                               .format(name))

    def _set_total_nodes(self):
        """
        Get the total number of nodes that will be required by the Run.
        Group codes based upon the node layout (separate/shared nodes),
        then consider the dependency between components to calculate the
        total no. of nodes.
        TODO This functionality exists in Savanna already.
        """

        # num_nodes_rc = {}
        # for rc in self.run_components:
        #     code_node = self.node_layout.get_node_containing_code(rc.name)
        #     code_procs_per_node = code_node[rc.name]
        #     num_nodes_rc[rc.name] = int(math.ceil(rc.nprocs /
        #                                           code_procs_per_node))

        # group codes by node
        code_groups = self.node_layout.group_codes_by_node()

        # now further group codes based on the dependency
        self._group_codes_by_dependencies(code_groups)

        # Get the max no. of nodes required based on the node layout
        group_max_nodes = []
        for code_group in code_groups:
            group_max = 0
            for codename in code_group:
                rc = self._get_rc_by_name(codename)
                # FIXME: Cleanup this hack
                # For summit: its something like {'xgc':{0,1,2,4,5}}, i.e.
                #   its a dict of sets. For other machines, its a dict of
                #   int that represents ppn.
                if isinstance(self.node_layout.layout_list[0],
                              machines.MachineNode):
                    num_nodes_code = math.ceil(
                        rc.nprocs/len(code_group[codename]))
                else:
                    num_nodes_code = math.ceil(
                        rc.nprocs / code_group[codename])
                rc.num_nodes = num_nodes_code
                group_max = max(group_max, num_nodes_code)
            group_max_nodes.append(group_max)

        self.total_nodes = sum(group_max_nodes)

    def _group_codes_by_dependencies(self, code_groups):
        """Group RCs based upon the dependencies.
        Input is a list of dictionaries where the key is the code and value
        is the no. of ranks on a node"""

        def parse_dicts(l_d):
            for d in l_d:
                for rc_name in d:
                    rc = self._get_rc_by_name(rc_name)
                    if rc.after_rc_done:
                        if rc.after_rc_done.name not in list(d.keys()):
                            target_d = None
                            for d2 in l_d:
                                if rc.after_rc_done.name in list(d2.keys()):
                                    target_d = d2
                                    break
                            assert target_d is not None, \
                                "Internal dependency management error! " \
                                "Could not find rc {} in codes".format(
                                    rc.after_rc_done.name)
                            target_d[rc_name] = d[rc_name]
                            del d[rc_name]
                            return False
            return True

        done = False
        while not done:
            done = parse_dicts(code_groups)

    def get_app_param_dict(self):
        """Return dictionary containing only the app parameters
        (does not include nprocs or exe paths)."""
        return self.instance.as_dict()

