"""
Module containing classes for specifying paramter value sets and groupings
of parameters. Used in the Experiment specification in the 'runs' variable.
"""
import itertools


class SchedulerGroup(object):
    """
    Class representing a grouping of run parameters that can be executed by
    a single scheduler job, because they share the same scheduler parameters
    (currently only # of nodes is at this level).

    How this gets converted into a script depends on the target machine and
    which scheduler (if any) that machine uses.
    """
    def __init__(self, nodes, parameter_groups):
        self.nodes = nodes
        self.parameter_groups = parameter_groups

    def get_runs(self, exes, group_output_dir):
        runs = []
        for group in self.parameter_groups:
            runs.extend(group.get_runs(exes))
        return runs


class ParameterGroup(object):
    """
    Class representing a set of parameter values to search over as
    a cross product.
    """
    def __init__(self, parameters):
        self.parameters = parameters

    def get_runs(self, exe):
        """
        Get a list of Command objects representing all the runs over the cross
        product.

        TODO: this works great for command line options and args, but
        what about for config and other types of params? Need to setup
        a run dir and populate it with filled config templates.

        Also how to pass per run output dir? Or is just making CWD the
        per run dir enough for all cases we care about?

        TODO: should have same signature as SchedulerGroup version OR a
        different name.
        """
        runs = []
        indexes = [range(len(p)) for p in self.parameters]
        for idx_set in itertools.product(*indexes):
            cmd = Command(exe)
            for param_i, value_i in enumerate(idx_set):
                cmd.add_parameter(self.parameters[param_i], value_i)
            runs.append(cmd)
        return runs


class Command(object):
    """
    Helper class for building up a command by parts.
    """
    def __init__(self, exe):
        self.exe = exe
        self.args = {}
        self.options = {}
        # list of touples (param, idx)
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


class ParamCmdLineOption(object):
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
        self.position = position
