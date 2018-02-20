"""
Classes to represent different types of parameters passed to applications.
"""
from collections import defaultdict


class ParameterValue(object):
    """
    Convenience classes for tracking a specific value of a parameter.
    Proxies to underlying parameter object, adds a `value` instance
    variable.

    TODO: this is kind of hacky, is there a better way?
    """
    def __init__(self, parameter, value_index):
        self._parameter = parameter
        self.value = parameter.values[value_index]

    def __getattr__(self, name):
        if hasattr(self._parameter, name):
            return getattr(self._parameter, name)
        raise AttributeError(name)

    def is_type(self, parameter_class):
        return isinstance(self._parameter, parameter_class)




class Param(object):
    """Abstract base class representing a parameter to an application. This
    includes any method for modifying the run characteristics of an
    application - command line, config file, environment variables, different
    executable built with diffrent compiler flags.

    Every parameter must have a unique name, and must target a specific
    application or middleware, e.g. pbs, aprun, or one of the science
    codes that make up an application.

    Note that if a science application has only one code, it will likely still
    involve middlewhere targets like PBS. Using a different target is one way
    to model those.

    TODO: is it useful to separate the definition of a param and it's values?

    TODO: should we require that the name be unique across all targets, or
    just within each target? Global uniqueness allows for a simple list of
    dict representation of instances, but two level nested dicts may be
    more powerful (first level is target, second level is params)."""

    def __init__(self, target, name, values=None):
        self.target = target
        self.name = name

        # allow a function to be specified instead of list of values, for
        # derived parameters. Wrap in a list to simplify the cross
        # product calculation, calculate during generation when the
        # other values are known.
        if callable(values):
            values = [values]

        self.values = values

    def __get__(self, idx):
        return self.values[idx]

    def __len__(self):
        return len(self.values)


class ParamCmdLineArg(Param):
    """Specification for parameters that are based as a positional command line
    argument."""
    def __init__(self, target, name, position, values=None):
        Param.__init__(self, target, name, values)
        self.position = position


class ParamAdiosXML(Param):
    """
    Class to represent ADIOS XML Transform.

    The transform config is encoded in the name, so transforms on different
    variables can be included in the sweep.

    Format:
        adios_transform:<xml_filename>:<group_name>:<var_name>
        adios_transport:<xml_filename>:<group_name>

    Note that the filename is assumed to be relative to the app directory
    specified as a Cheetah command line argument.
    """
    def __init__(self, target, name, adios_xml_tags, values=None):
        Param.__init__(self, target, name, values)
        parts = adios_xml_tags.split(":")
        if len(parts) < 3:
            raise ValueError("bad format for ParamAdiosXML name")
        # param_type = adios_transform or adios_transport
        self.param_type = parts[0]
        self.xml_filename = parts[1]
        self.group_name = parts[2]

        # if param_type is transform
        if len(parts) == 4:
            self.var_name = parts[3]


class ParamCmdLineOption(Param):
    """Specification for parameters that are based as a labeled command line
    option. The option must contain the prefix, e.g. '--output-file' not
    'output-file'."""

    def __init__(self, target, name, option, values=None):
        Param.__init__(self, target, name, values)
        self.option = option


class ParamRunner(Param):
    """Specification for parameters that are passed to the runner, e.g.
    mpirun, mpilaunch, srun, apirun, but usually still associated with a
    specific application code."""
    def __init__(self, target, name, values=None):
        Param.__init__(self, target, name, values)
