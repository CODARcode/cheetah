"""
Functions for loading experiment python files by path.

Requires Python 3.3+
"""
import os.path
import importlib.machinery
import inspect

from codar.cheetah import model, exc

def load_experiment_class(file_path):
    """Given the path to a python module containing an experiment, load the
    module and find and return the class."""
    file_path = os.path.abspath(file_path)
    fname = os.path.basename(file_path)
    module_name = os.path.splitext(fname)[0]
    loader = importlib.machinery.SourceFileLoader(module_name, file_path)
    module = loader.load_module()
    experiment_class = None
    for m in inspect.getmembers(module, inspect.isclass):
        mvalue = m[1]
        if (not issubclass(mvalue, model.Campaign)
                or mvalue == model.Campaign):
            continue
        experiment_class = mvalue
        break
    if experiment_class is None:
        raise exc.CampaignParseError(
                'no Campaign subclass found in "%s"' % file_path)
    return experiment_class
