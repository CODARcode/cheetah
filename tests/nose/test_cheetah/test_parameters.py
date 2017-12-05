
from nose.tools import assert_equal

from codar.cheetah.parameters import Instance, ParamRunner, ParamCmdLineArg

def test_instance_nprocs_only():
    ds_nprocs = ParamRunner('dataspaces', 'nprocs', [1])
    ds_arg1   = ParamCmdLineArg('dataspaces', 'arg1', 1, ['val1'])

    core_nprocs = ParamRunner('core', 'nprocs', [96])

    inst = Instance()
    inst.add_parameter(ds_nprocs, 0)
    inst.add_parameter(ds_arg1, 0)
    inst.add_parameter(core_nprocs, 0)

    codes_argv = inst.get_codes_argv()

    assert_equal(len(codes_argv), 2)
    argv_map = dict(codes_argv)

    assert_equal(argv_map['dataspaces'], ['val1'])
    assert_equal(argv_map['core'], [])


def test_derived_params():
    code1_arg1 = ParamCmdLineArg('code1', 'arg1', 1, [7])
    code1_arg2 = ParamCmdLineArg('code1', 'arg2', 2, lambda d: d['arg1'] * 10)
    inst = Instance()

    inst.add_parameter(code1_arg1, 0)
    inst.add_parameter(code1_arg2, 0)

    codes_argv = inst.get_codes_argv()

    assert_equal(len(codes_argv), 1)
    assert_equal(len(codes_argv['code1']), 2)
    argv_map = dict(codes_argv)

    assert_equal(argv_map['code1'], ['7', '70'])
