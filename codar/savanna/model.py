"""
Classes for modeling execution of HPC workflows. Abstractly a workflow is
viewed as a collection of codes with unique names, and each code has a
collection of uniquely names parameters. Parameter values are always assumed
to be strings and not validation is done (that is the responsibilty of the
application). In addition to code specific parameters, there are execution
parameters that apply to all codes, e.g. the number of MPI processes.
"""

import itertools

from codar.savanna.parameters import ParamCmdLineArg, \
    ParamCmdLineOption, ParamAdiosXML

from codar.savanna import exc


STANDARD_NAMES = set(['nprocs'])


class Code(object):
    """
    Class for specifying the parameters of a science code.
    Designed to be extensible, support performance instrumentation (e.g. using
    TAU and SOSFLOW) and provide information necesary to do advanced node and
    core placement.

    Some science applications will consiste of multiple codes - a unique name
    is required for each code to identify it in workflows. Each parameter to
    each code must also have a unique name. This class is designed to take
    a dictionary mapping these unique parameter names to a specific value and
    produce a CodeExecution object which describes how to actually execute
    the code on specific hardware.

    Note that all Codes have an implicit 'nprocs' parameter used to specify
    the number of MPI processes to use.

    :ivar name: friendly name for code
    :ivar exe: path to executable; should generally be a relative path with
        the base path set for multiple codes.
    :ivar command_line_args: list of strings, names of positional command line
        args
    :ivar command_line_options: list of CmdLineOption instances
    :ivar default_values: set default values for parameters if they are
        not specified. dict with parameter name keys and string values.
    """
    def __init__(self, name, exe, command_line_args, command_line_options,
                 parameters=None, adios_xml_file=None, default_values=None):
        self.name = name
        self.exe = exe
        self.command_line_args = command_line_args or []
        self.command_line_options = command_line_options or {}
        self.adios_xml_file = adios_xml_file
        self.parameters = parameters or {}
        self.default_values = default_values or {}
        self.parameter_names = self._get_parameter_names()

    def _get_parameter_names(self):
        arg_names = set(self.command_line_args)
        opt_names = set([opt.name for opt in self.command_line_options])
        p_names = set([p.name for p in self.parameters])
        dups = set()
        for pairs in itertools.combinations([arg_names, opt_names, p_names,
                                             STANDARD_NAMES], 2):
            dups.update(pairs[0] & pairs[1])

        if dups:
            raise exc.ParameterNameException('duplicate parameter names: %s'
                                             % ','.join(dups))
        return (arg_names | opt_names | p_names)

    def get_code_command(self, parameter_dict):
        """
        Given a dictionary of parameter names to parameter values,
        return an CodeCommand object that can be used to execute the code
        with the specified parameter values.
        """
        with_defaults = dict(self.default_values)
        with_defaults.update(parameter_dict)
        return CodeCommand(self, with_defaults)


def _create_command_line_args(code_name, names):
    return [ParamCmdLineArg(code_name, name, i)
            for (i, name) in enumerate(names)]


class CommandLineOption(object):
    """
    :ivar name: unique friendly name for parameter
    :ivar option: string used to specify the option on the command line with
        prefix, e.g. '--output'
    """
    def __init__(self, name, option):
        self.name = name
        self.option = option


class CodeCommand(object):
    """
    A code with a specified set of parameter values that can be executed.
    Forms the command line to execute and has callouts to setup up the
    necessary config files.

    :ivar code: the abstract code object
    :ivar exe: the executable; may be a relative path
    :ivar argv: command line to execute the command, not including the
        executable
    """
    def __init__(self, code, parameter_dict):
        self.code = code
        self.exe = code.exe
        self.parameter_dict = parameter_dict
        self.argv = []
        self.nprocs = parameter_dict.get('nprocs', '1')
        parameter_names = set(parameter_dict.keys())
        parameter_found = set()
        max_arg_position = 0
        # options first, then position args
        # TODO: do we need config to control this?
        for opt in code.command_line_options:
            value = parameter_dict.get(opt.name)
            if value is None:
                continue
            parameter_found.add(opt.name)
            self.argv.append(opt.option)
            self.argv.append(value)
        empty_arg = None
        for i, arg_name in enumerate(code.command_line_args):
            value = parameter_dict.get(arg_name)
            if value is None:
                empty_arg = (i, arg_name)
                break
            if empty_arg is not None:
                raise exc.ParameterValueException(
                    'missing positional command line argument "%s" at %d'
                    % (arg_name, i+1))
            self.argv.append(value)
            parameter_found.add(arg_name)
        unknown_names = (parameter_names - parameter_found - STANDARD_NAMES
                         - set([p.name for name in code.parameters]))

        if unknown_names:
            raise exc.ParameterNameException(
                    'unknown parameter names (%s) for code "%s"'
                    % (','.join(unknown_names), self.code.name))


    def get_argv(self):
        return list(self.argv)
