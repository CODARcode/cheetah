#!/usr/bin/env python3

import itertools
import errno
import os
import sys

import yaml


def test_parse(experiment_spec_path, out_dir):
    with open(experiment_spec_path) as f:
        data = yaml.load(f)
    print(data)
    e = Experiment(data)
    for cmd in e.get_commands():
        print(cmd)


def parameter_group_to_cross_product_iter(data):
    """
    Convert a parameter group specifiation defining the values that each
    parameter can take (as a list or range spec) to a cross product of
    the parameter values as a list of dicts.
    """
    param_names = sorted(data.keys())
    param_value_lists = [parse_parameter_list(data[k]) for k in param_names]
    return [dict(zip(param_names, values))
            for values in itertools.product(*param_value_lists)]


def parse_parameter_list(data):
    """
    Given a dict containing 'range-start', 'range-end', and optionally
    one of 'range-increment' or 'range-multiplier', produce an iterator of
    values from start to end _inclusive_ using the specified increment or
    multiplier. Defaults to an increment of 1 if not specified.

    Given a list, return as is.
    """
    if isinstance(data, dict):
        # range specification
        try:
            start = data['range-start']
            end = data['range-end']
            if 'range-increment' in data:
                if 'range_multiplier' in data:
                    raise ValueError(
                        'specify one of range-multiplier or range-increment, '
                        'not both')
                return range(start, end+1, data['range-increment'])
            elif 'range-multiplier' in data:
                multiplier = data['range-multiplier']
                values = []
                value = start
                while value <= end:
                    values.append(value)
                    value *= multiplier
                return values
            else:
                # default to increment of 1
                return range(start, end+1)
        except KeyError as e:
            raise ValueError('Missing required range key: %s' % str(e))
    elif isinstance(data, list):
        return data
    else:
        raise ValueError('Expected list or dict of range-* keys')


class AbstractParameterLayer(object):
    """
    Base class for Scheduler and Runner, both of which have a type and
    parameters.
    """
    TYPES = [] # subclasses must override

    def __init__(self, data):
        try:
            self.type = data['type']
            if self.type not in self.TYPES:
                raise ValueError('Unknown type: %s' % self.type)
            self.parameters = data.get('parameters', {})
        except KeyError as e:
            raise ValueError('Missing required key in scheduler data: %s' % e)


class Scheduler(AbstractParameterLayer):
    TYPES = ['pbs']


class Runner(AbstractParameterLayer):
    TYPES = ['aprun']


class App(object):
    def __init__(self, data):
        try:
            self.script = data['script']
            self.max_walltime = data['max-walltime']
        except KeyError as e:
            raise ValueError('Missing required key in app data: %s' % e)


class RunParameters(object):
    """
    Parameters to run a single instance of the application.
    """
    def __init__(self, data):
        self.app = {}
        self.runner = {}
        for k, v in data.items():
            if k.startswith('app-'):
                k = k[len('app-'):]
                self.app[k] = v
            elif k.startswith('runner-'):
                k = k[len('runner-'):]
                self.runner[k] = v
            else:
                raise ValueError('parameter group keys must start with "app-"'
                                 ' or "runner-" (got "%s")' % k)

    def get_command(self, runner, app_script):
        app_command = app_script
        runner_command = runner
        for k, v in self.app.items():
            v = str(v)
            app_command += ' --' + k + '=' + v
        for k, v in self.runner.items():
            v = str(v)
            # TODO: quoting
            runner_command += ' -' + k + ' ' + v
        return runner_command + ' ' + app_command


class Experiment(object):
    def __init__(self, data):
        self._data = data
        try:
            self.experiment = data['experiment']
            self.app = App(self.experiment['app'])
            self.scheduler = Scheduler(self.experiment['scheduler'])
            self.runner = Runner(self.experiment['runner'])
            self.run_parameters_list = []
            for pgroup in self.experiment['parameter-groups']:
                for pdict in parameter_group_to_cross_product_iter(pgroup):
                    self.run_parameters_list.append(RunParameters(pdict))
        except KeyError as e:
            raise ValueError('Missing required key in experiment: %s' % e)

    def get_commands(self):
        return [rp.get_command(self.runner.type, self.app.script)
                for rp in self.run_parameters_list]


if __name__ == '__main__':
    test_parse(sys.argv[1], sys.argv[2])
