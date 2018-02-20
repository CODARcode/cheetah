
from nose.tools import assert_equal

from codar.savanna.model import Code, CommandLineOption
from codar.savanna import exc


def test_code_command():
    c = Code(name='test',
             exe='bin/test',
             command_line_args=['arg1', 'arg2', 'arg3', 'arg4'],
             command_line_options=[
                CommandLineOption('opt1', '--opt1'),
                CommandLineOption('opt2', '--opt2')
             ],
    )

    cc = c.get_code_command({
            'arg1': 'val1',
            'arg2': 'val2',
            'arg3': 'val3',
            'arg4': 'val4',
            'opt1': 'oval1',
            'opt2': 'oval2'})

    args = cc.get_argv()
    assert_equal(args,
        ['--opt1', 'oval1', '--opt2', 'oval2', 'val1', 'val2', 'val3', 'val4'])


def test_unknown_param_name():
    c = Code(name='test',
             exe='bin/test',
             command_line_args=['arg1', 'arg2', 'arg3', 'arg4'],
             command_line_options=[
                CommandLineOption('opt1', '--opt1'),
                CommandLineOption('opt2', '--opt2')
             ],
    )

    try:
        cc = c.get_code_command({
            'arg1': 'val1',
            'arg2': 'val2',
            'arg3': 'val3',
            'arg4': 'val4',
            'opt1': 'oval1',
            'opt2': 'oval2',
            'unknown1': 'u1',
            'unknown2': 'u2' })
    except exc.ParameterNameException as e:
        assert 'unknown1' in str(e)
        assert 'unknown2' in str(e)
    else:
        assert False, 'no error on passing unknown parameter names'
