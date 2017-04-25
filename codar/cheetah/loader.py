"""
Functions for loading experiment python files by path.

Requires Python 3.4+
"""
import os.path
import importlib.util
import inspect

from codar.cheetah import model

def load_experiment_class(file_path):
    """Given the path to a python module containing an experiment, load the
    module and find and return the class."""
    file_path = os.path.abspath(file_path)
    fname = os.path.basename(file_path)
    module_name = os.path.splitex(fname)[0]
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    experiment_class = None
    for m in inspect.getmembers(module):
        if not inspect.isclass(m):
            continue
        if not isinstance(m, model.Experiment):
            continue
        experiment_class = m
        break
    if experiment_class is None:
        raise ValueError('no Experiment subclass found in "%s"' % file_path)
    return experiment_class
