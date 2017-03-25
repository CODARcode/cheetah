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
    print(e.parameter_sets)
    e.generate_execute_dir(out_dir)


def parameter_set_to_cross_product_iter(data):
    """
    Convert a parameter set specifiation defining the values that each
    parameter can take (as a list or range spec) to a cross product of
    the parameter values as a list of dicts.
    """
    params = sorted(data.keys())
    param_value_lists = [parse_parameter_list(data[k]) for k in params]
    return (params, itertools.product(*param_value_lists))


def parse_parameter_list(data):
    if isinstance(data, dict):
        # range specification
        try:
            start = data['range-start']
            end = data['range-end']
            if 'range-increment' in data:
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


def get_run_command(runner, app_script, run_params, default_params, outpath):
    """
    Given the runner, e.g. 'aprun', the app script, e.g. 'my-app.sh', the
    parameters for this particular run, default parameters, and the result
    dir for this run, produce a string suitable for insertion into a scheduler
    script.
    """
    params = default_params
    params.update(run_params)
    runner_command = runner
    app_command = app_script + ' --output-directory="' + outpath + '"'
    for k, v in params.items():
        v = str(v)
        if k.startswith('runner-'):
            k = k[len('runner-'):]
            # TODO: quoting
            app_command += ' -' + k + ' ' + v
        elif k.startswith('app-'):
            # TODO: quoting
            app_command += ' --' + k + '=' + v
    return runner_command + ' ' + app_command


class Experiment(object):
    def __init__(self, data):
        self._data = data
        self.experiment = data.get('experiment')
        self.app_script = self.experiment['app']['script']
        if self.experiment is None:
            raise ValueError('Missing top level experiment key')
        self.scheduler = self.experiment.get('scheduler')
        if self.scheduler is None:
            raise ValueError('Missing scheduler key in experiment')
        self.runner = self.scheduler['runner']
        self.runner_defaults = self.scheduler['runner-defaults']
        self.scheduler_type = self.scheduler['type']
        self.parameter_sets = []
        for pset in self.experiment['parameter-sets']:
            self.parameter_sets.append(
                parameter_set_to_cross_product_iter(pset))

    def generate_execute_dir(self, outdir):
        try:
            os.mkdir(outdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        i = 1
        for pset_keys, pset_iter in self.parameter_sets:
            for param_tuple in pset_iter:
                run_resultdir = os.path.join(outdir, 'results-%03d' % i)
                params = dict(zip(pset_keys, param_tuple))
                cmd = get_run_command(self.runner, self.app_script, params,
                                      self.runner_defaults, run_resultdir)
                print(cmd)
                i += 1


if __name__ == '__main__':
    test_parse(sys.argv[1], sys.argv[2])
