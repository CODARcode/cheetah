"""
Module containing classes for specifying paramter value sets and groupings
of parameters. Used in the Experiment specification in the 'runs' variable.
"""
import itertools
from collections import defaultdict

from codar.cheetah.exc import CheetahException


class SweepGroup(object):
    """
    Class representing a grouping of run parameters that can be executed by
    a single scheduler job, because they share the same scheduler parameters.

    Note that nodes is no longer required - if not specified, it is calculated
    based on the biggest run within the group.

    How this gets converted into a script depends on the target machine and
    which scheduler (if any) that machine uses.
    """
    def __init__(self, name, parameter_groups, component_subdirs=False,
                 component_inputs=None, walltime=3600, max_procs=None,
                 per_run_timeout=None, sosflow_profiling=False,
                 sosflow_analysis=False, nodes=None, launch_mode=None,
                 tau_profiling=False, tau_tracing=False, run_repetitions=0):
        self.name = name
        self.nodes = nodes
        self.component_subdirs=component_subdirs
        self.max_procs = max_procs
        self.parameter_groups = parameter_groups
        self.walltime = walltime
        # TODO: allow override in Sweeps?
        self.per_run_timeout = per_run_timeout
        self.sosflow_profiling = sosflow_profiling
        self.sosflow_analysis = sosflow_analysis
        self.component_inputs = component_inputs
        if launch_mode:
            if launch_mode.lower() not in ('default', 'mpmd'):
                raise CheetahException("launch mode must be None/default/mpmd")
        self.launch_mode = launch_mode
        self.tau_profiling=tau_profiling
        self.tau_tracing=tau_tracing
        self.run_repetitions = run_repetitions


class Sweep(object):
    """
    Class representing a set of parameter values to search over as
    a cross product.
    """
    def __init__(self, parameters, node_layout=None, rc_dependency=None):
        self.parameters = parameters
        self.node_layout = node_layout
        self.rc_dependency = rc_dependency

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
        # Do in two steps, to support derived params across codes / run
        # components. First step builds a two level dict with top level
        # keys being target/code name, next level being simple param
        # values for that target.
        simple_value_map = {} # passed to fn for derived params
        for target, target_pv_list in self._simple_pv_list.items():
            # NB: not attempting to support deriving values from other
            # derived values.
            simple_value_map[target] = dict((pv.name, pv.value)
                                            for pv in target_pv_list)

        targets = (set(self._simple_pv_list.keys())
                 | set(self._derived_pv_list.keys()))
        for target in targets:
            target_p = self._parameter_values[target]

            target_pv_list = self._simple_pv_list[target]

            for derived_pv in self._derived_pv_list[target]:
                derived_pv.value = derived_pv.value(simple_value_map)
                target_pv_list.append(derived_pv)

            for pv in target_pv_list:
                # Add a command for any code that has at least one param
                # of any type, even if no command line args or opts.
                if target not in self._code_commands:
                    self._code_commands[target] = CodeCommand(target)

                # Custom handling for command line param types
                if pv.is_type(ParamCmdLineArg):
                    self._code_commands[target].add_arg(pv.position, pv.value)
                elif pv.is_type(ParamCmdLineOption):
                    self._code_commands[target].add_option(pv.option, pv.value)
                if pv.name in target_p:
                    raise ValueError('parameter name conflict: "%s"' % pv.name)
                # Always save the value, regardless of param type.
                target_p[pv.name] = pv
        self._values_calculated = True

    def get_codes_argv(self):
        """Get an _unordered_ dict mapping code name to list of args for
        that code. Higher levels of model are responsible for re-ordering
        as needed."""
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

    def get_hostfile(self, target):
        pv = self.parameter_values[target].get('hostfile')
        if pv:
            return pv.value
        return None

    def get_sched_opts(self, target):
        pv = self.parameter_values[target].get('sched_opts')
        if pv:
            return pv.value
        return None

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
            if value is not None:
                argv.append(str(value))
        return argv


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
        assert type(values) == list, "Parameter value must be a list"

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
        adios_transform:<group_name>:<var_name>
        adios_transport:<group_name>

    Note that the filename is specified in the code definition.
    """
    def __init__(self, target, name, adios_xml_tags, values):
        Param.__init__(self, target, name, values)
        parts = adios_xml_tags.split(":")
        if len(parts) < 2:
            raise ValueError("bad format for ParamAdiosXML name")
        # param_type = adios_transform or adios_transport
        self.param_type = parts[0]
        self.group_name = parts[1]

        # if param_type is transform
        if len(parts) == 3:
            self.var_name = parts[2]


class ParamADIOS2XML(Param):
    """
    Class to represent ADIOS2 XML file parameter options
    """
    def __init__(self, rc, name, io_name, operation_name, values):
        """

        :param rc: name of the run component
        :param io_name: name of the io object in the xml file
        :param operation_name: engine/transport/var_operation
        :param values: a list of dicts of the type
        [ { engine_name: {parameters} },
          { engine_name: {parameters} },
          { var_name: {operation_name: {parameters}}}
        ]
        Examples:
        [ {"BPFile": {'Threads':1}},
          {"BPFile": {"ProfileUnits": "Microseconds"}}
        ]
        [ { “T”: { “zfp”: {“rate”:18, “accuracy”: 0.01} } },
          { “T”: { “zfp”: {“rate”:18, “accuracy”: 0.001} } },
          { “T”: { “zfp”: {“rate”:18, “accuracy”: 0.0001} } },
          { “T”: { “sz”:  {“rate”:18, “accuracy”: 0.01} } },
        ]
        """

        Param.__init__(self, rc, name, values)
        self.rc = rc
        self.io_name = io_name
        self.operation_name = operation_name
        self.values = values

        if operation_name not in ("engine", "transport", "var_operation"):
            raise CheetahException("{0} not a valid adios xml "
                                   "object".format(operation_name))

        for key_dict in values:
            assert (type(key_dict) == dict)
            assert (len(key_dict) == 1)
            vals_dict = key_dict.values()
            assert len(vals_dict) == 1
            vals = list(vals_dict)[0]
            assert (type(vals) == dict)
            if operation_name == 'var_operation':
                assert(len(vals) == 1)


class ParamConfig(Param):
    """
    Class to represent a simple literal string replace in a config file.

    Note that the filename must be added to the inputs list as well, to be
    copied to each run directory.
    """
    def __init__(self, target, name, config_filename, match_string, values):
        Param.__init__(self, target, name, values)
        self.config_filename = config_filename
        self.match_string = match_string


class ParamKeyValue(Param):
    """
    Class to represent replacement of the value in a config file with
    'k = v' formatted lines. This should work with various formats, including
    fortran namelist and INI, by ignoring lines that don't match the
    simple k = v pattern. It has the advantage of being flexible, but the
    disadvantage of not understanding sections or other more complicated
    structure in config files. Also does not do any quoting - if required,
    the spec writer should include literal quotes around the values.

    Note that the filename must be added to the inputs list as well, to be
    copied to each run directory.
    """
    def __init__(self, target, name, config_filename, key_name, values):
        Param.__init__(self, target, name, values)
        self.config_filename = config_filename
        self.key_name = key_name


class ParamCmdLineOption(Param):
    """Specification for parameters that are based as a labeled command line
    option. The option must contain the prefix, e.g. '--output-file' not
    'output-file'."""

    def __init__(self, target, name, option, values):
        Param.__init__(self, target, name, values)
        self.option = option


class ParamEnvVar(Param):
    def __init__(self, target, name, option, values):
        Param.__init__(self, target, name, values)
        self.option = option


class ParamSchedulerArgs(Param):
    def __init__(self, target, values):
        Param.__init__(self, target, "sched_opts", values)
        assert ((type(values) == list) and (type(values[0]) == dict)), \
            "ParamSchedulerArgs must be a list containing a single dict"


class ParamRunner(Param):
    """Specification for parameters that are passed to the runner, e.g.
    mpirun, mpilaunch, srun, apirun, but usually still associated with a
    specific application code."""
    def __init__(self, target, name, values):
        Param.__init__(self, target, name, values)


class SummitOpts():
    def __init__(self):
        pass


class SymLink(str):
    """
    Class to represent symbolic links as an input type for a run component
    """
    def __init__(self, source):
        self.source = source
