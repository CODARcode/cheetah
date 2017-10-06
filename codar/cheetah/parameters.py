"""
Module containing classes for specifying paramter value sets and groupings
of parameters. Used in the Experiment specification in the 'runs' variable.
"""
import itertools
from collections import defaultdict


class SweepGroup(object):
    """
    Class representing a grouping of run parameters that can be executed by
    a single scheduler job, because they share the same scheduler parameters
    (currently only # of nodes is at this level).

    How this gets converted into a script depends on the target machine and
    which scheduler (if any) that machine uses.
    """
    def __init__(self, name, nodes, parameter_groups, walltime=3600,
                 max_procs=None, per_run_timeout=None):
        self.name = name
        self.nodes = nodes
        self.max_procs = max_procs
        self.parameter_groups = parameter_groups
        self.walltime = walltime
        # TODO: allow override in Sweeps?
        self.per_run_timeout = per_run_timeout

    def get_instances(self):
        inst = []
        for group in self.parameter_groups:
            inst.extend(group.get_instances())
        return inst


class Sweep(object):
    """
    Class representing a set of parameter values to search over as
    a cross product.
    """
    def __init__(self, parameters):
        self.parameters = parameters

    def get_instances(self):
        """
        Get a list of Instance objects representing dense cross product over
        param values.

        TODO: this works great for command line options and args, but
        what about for config and other types of params? Need to setup
        a run dir and populate it with filled config templates.

        Also how to pass per run output dir? Or is just making CWD the
        per run dir enough for all cases we care about?

        TODO: should have same signature as SweepGroup version OR a
        different name.
        """
        inst_list = []
        indexes = [range(len(p)) for p in self.parameters]
        for idx_set in itertools.product(*indexes):
            inst = Instance()
            for param_i, value_i in enumerate(idx_set):
                inst.add_parameter(self.parameters[param_i], value_i)
            inst_list.append(inst)
        return inst_list


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


class Instance(object):
    """
    Represent an instance of an application with fixed parameters. An
    application may consistent of multiple codes running at the same time,
    and multiple middlewear layers (scheduler like PBS, runner like aprun,
    or swift), all of which may have their own parameters.

    Abstractly, an instance is a two-level nested dict, where the first
    level indicates the target for a parameter (application code or
    middlewear), and the second level contains the parameter values for that
    target.
    """
    def __init__(self):
        # abstract container with all param values in a hierarchy based on
        # their target
        self._parameter_values = defaultdict(dict)

        # temporary containers for staging params so derived values can
        # be calculated after all are added.
        self._simple_pv_list = defaultdict(list)
        self._derived_pv_list = defaultdict(list)

        # subset of paramaters related to application codes that will
        # need to be run
        self._code_commands = dict()

        self._values_calculated = False

    def add_parameter(self, p, idx):
        if self._values_calculated:
            raise ValueError("new parameters can't be added after get")
        pv = ParameterValue(p, idx)
        if callable(pv.value):
            self._derived_pv_list[pv.target].append(pv)
        else:
            self._simple_pv_list[pv.target].append(pv)

    @property
    def parameter_values(self):
        """Wrapper to allow delayed calculation of derived parameter values."""
        if not self._values_calculated:
            self._calculate_values()
        return self._parameter_values

    @property
    def code_commands(self):
        """Wrapper to allow delayed calculation of derived parameter values."""
        if not self._values_calculated:
            self._calculate_values()
        return self._code_commands

    def _calculate_values(self):
        for target, target_pv_list in self._simple_pv_list.items():
            target_p = self._parameter_values[target]

            # NB: not attempting to support deriving values from other
            # derived values.
            simple_value_map = dict((pv.name, pv.value)
                                    for pv in target_pv_list)
            for derived_pv in self._derived_pv_list[target]:
                derived_pv.value = derived_pv.value(simple_value_map)
                target_pv_list.append(derived_pv)

            for pv in target_pv_list:
                # Custom handling for command line param types: start
                # building up the command.
                if pv.is_type(ParamCmdLineArg):
                    if target not in self._code_commands:
                        self._code_commands[target] = CodeCommand(target)
                    self._code_commands[target].add_arg(pv.position, pv.value)
                elif pv.is_type(ParamCmdLineOption):
                    if target not in self._code_commands:
                        self._code_commands[target] = CodeCommand(target)
                    self._code_commands[target].add_option(pv.option, pv.value)
                if pv.name in target_p:
                    raise ValueError('parameter name conflict: "%s"' % pv.name)
                # Always save the value, regardless of param type.
                target_p[pv.name] = pv
        self._values_calculated = True

    def get_codes_argv(self):
        return dict([(k, cc.get_argv())
                     for (k, cc) in self.code_commands.items()])

    def as_string(self):
        """Get a command line like value for the instance. Note that this
        only includes positional and option command line args, not config
        args like adios XML. TODO: deprecate??"""
        parts = [self.exe]
        for position in range(1, 101):
            if position in self.args:
                parts.append(str(self.args[position]))
            else:
                break
        for option, value in self.options.items():
            # TODO: handle separator between option and value, e.g. '',
            # '=', or ' '.
            parts.append(option + ' ' + value)
        return " ".join(parts)

    def get_parameter_values_by_type(self, param_class):
        """
        Get a list of ParamaterValues of the specified type in the instance.
        """
        pvs = []
        for target, target_params in self.parameter_values.items():
            for name, pv in target_params.items():
                if pv.is_type(param_class):
                    pvs.append(pv)
        return pvs

    def get_nprocs(self, target):
        pv = self.parameter_values[target].get('nprocs')
        if pv is None:
            return 1
        return pv.value

    def as_dict(self):
        """
        Produce dict (mainly for for JSON seriliazation) with keys based on
        parameter names. This ignores the type of the param, it's just the
        name value pairs.
        """
        return dict((target, dict((pv.name, pv.value) for pv in d.values()))
                    for target, d in self.parameter_values.items())


class CodeCommand(object):
    """
    Helper class to build up command args and options as we go. Does not
    know about the path to it's executable, that is part of the execution
    environment which is added during realization.
    """
    def __init__(self, target):
        self.target = target
        self.args = {}
        self.options = {}

    def add_arg(self, position, value):
        """
        Allows adding positional args out of order.

        TODO: better error handling.
        """
        if not isinstance(position, int):
            raise ValueError('arg position must be an int')
        if position in self.args:
            raise ValueError('arg already exists at position %d' % position)
        self.args[position] = value

    def add_option(self, option, value):
        if option in self.args:
            raise ValueError('option "%s" already exists' % option)
        self.options[option] = value

    def get_argv(self):
        argv = []
        for position in range(1, 101):
            # TODO: better error handling
            if position in self.args:
                argv.append(str(self.args[position]))
            else:
                break
        for option, value in self.options.items():
            # TODO: handle separator between option and value, e.g. '',
            # '=', or ' '?
            argv.append(option)
            argv.append(str(value))
        return argv


class Command(object):
    """
    DEPRECATED.

    Helper class for building up a command by parts.
    """
    def __init__(self, exe):
        self.exe = exe
        self.args = {}
        self.options = {}
        # TODO: namespace param names somehow
        self.parameters = dict(exe=exe)

    def set_output_directory(self, value):
        """
        Add output directory information. Not known at initial object
        create time, filled in by higher level code.
        """
        self.parameters['output_directory'] = value

    def add_parameter(self, p, idx):
        value = p.values[idx]
        if isinstance(p, ParamCmdLineArg):
            self.args[p.position] = value
        if isinstance(p, ParamCmdLineOption):
            self.options[p.option] = value
        if p.name in self.parameters:
            raise ValueError('parameter name conflict: "%s"' % p.name)
        self.parameters[p.name] = value

    def as_string(self):
        parts = [self.exe]
        for position in range(1, 101):
            if position in self.args:
                parts.append(str(self.args[position]))
            else:
                break
        for option, value in self.options.items():
            # TODO: handle separator between option and value, e.g. '',
            # '=', or ' '.
            parts.append(option + ' ' + value)
        return " ".join(parts)

    def as_dict(self):
        """
        Produce dict (mainly for for JSON seriliazation) with keys based on
        parameter names. This ignores the type of the param, it's just the
        name value pairs.
        """
        return dict(self.parameters)


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

    def __init__(self, target, name, values):
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
    def __init__(self, target, name, position, values):
        Param.__init__(self, target, name, values)
        self.position = position


class ParamAdiosXML(Param):
    """
    Class to represent ADIOS XML Transform.

    The transform config is encoded in the name, so transforms on different
    variables can be included in the sweep.

    Format:
        adios_transform:<xml_filename>:<group_name>:<var_name>

    Note that the filename is assumed to be relative to the app directory
    specified as a Cheetah command line argument.
    """
    def __init__(self, target, name, values):
        Param.__init__(self, target, name, values)
        parts = name.split(":")
        if len(parts) != 4 or parts[0] != "adios_transform":
            raise ValueError("bad format for ParamAdiosXML name")
        self.xml_filename = parts[1]
        self.group_name = parts[2]
        self.var_name = parts[3]


class ParamCmdLineOption(Param):
    """Specification for parameters that are based as a labeled command line
    option. The option must contain the prefix, e.g. '--output-file' not
    'output-file'."""

    def __init__(self, target, name, option, values):
        Param.__init__(self, target, name, values)
        self.option = option


class ParamRunner(Param):
    """Specification for parameters that are passed to the runner, e.g.
    mpirun, mpilaunch, srun, apirun, but usually still associated with a
    specific application code."""
    def __init__(self, target, name, values):
        Param.__init__(self, target, name, values)
