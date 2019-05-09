import os.path
import shutil
import json
import getpass

from nose.tools import assert_equal

from codar.cheetah import exc
from codar.cheetah.model import Campaign
from codar.savanna.model import NodeLayout
from codar.cheetah.parameters import SweepGroup, Sweep
from codar.cheetah.parameters import ParamRunner, ParamCmdLineArg, \
                                ParamAdiosXML

from test_cheetah import TEST_OUTPUT_DIR


class TestCampaign(Campaign):
    name = 'test_campaign'
    supported_machines = ['local', 'titan', 'cori']
    codes = [('test', dict(exe='test'))]
    sweeps = [
        SweepGroup(name='test_group', nodes=1, parameter_groups=[
          Sweep([ParamCmdLineArg('test', 'arg', 1, ['a', 'b'])])
        ])
    ]


def test_bad_scheduler_options():
    class BadCampaign(TestCampaign):
        name = 'bad_scheduler_options'
        scheduler_options = { 'titan': dict(notanoption='test') }

    try:
        c = BadCampaign('titan', '/test')
    except ValueError as e:
        assert 'notanoption' in str(e), "Bad error message: " + str(e)
    else:
        assert False, 'expected ValueError from bad option'


def test_default_scheduler_options():
    class DefaultOptionCampaign(TestCampaign):
        name = 'default_options'
        # Alternate license option, use default constraint and queue
        scheduler_options = { 'cori': dict(license='SCRATCH') }

    c = DefaultOptionCampaign('cori', '/test')
    assert_equal(c.machine_scheduler_options['license'], 'SCRATCH')
    assert_equal(c.machine_scheduler_options['constraint'], 'haswell')
    assert_equal(c.machine_scheduler_options['queue'], 'debug')


def test_codes_ordering():
    class TestMultiExeCampaign(TestCampaign):
        codes = [('first', dict(exe='testa')),
                 ('second', dict(exe='testb')),
                 ('third', dict(exe='testc')),
                 ('fourth', dict(exe='testd')),
                 ('fifth', dict(exe='teste')),
                 ('sixth', dict(exe='testf')),
                 ('seventh', dict(exe='testg'))]
        sweeps = [
            SweepGroup(name='test_group', parameter_groups=[
              Sweep([
                ParamCmdLineArg('first', 'arg', 1, ['a', 'b']),
                ParamCmdLineArg('second', 'arg', 1, ['2']),
                ParamCmdLineArg('third', 'arg', 1, ['3']),
                ParamCmdLineArg('fourth', 'arg', 1, ['4']),
                ParamCmdLineArg('fifth', 'arg', 1, ['5', 'five']),
                ParamCmdLineArg('sixth', 'arg', 1, ['6']),
                ParamCmdLineArg('seventh', 'arg', 1, ['7']),
              ])
            ])
        ]

    c = TestMultiExeCampaign('titan', '/test')
    out_dir = os.path.join(TEST_OUTPUT_DIR,
                           'test_model', 'test_codes_ordering')
    fob_path = os.path.join(out_dir, getpass.getuser(),
                            'test_group', 'fobs.json')
    shutil.rmtree(out_dir, ignore_errors=True) # clean up any old test output
    c.make_experiment_run_dir(out_dir, _check_code_paths=False)

    correct_order = list(c.codes.keys())

    with open(fob_path) as f:
        fobs = json.load(f)

    for fob in fobs:
        fob_order = [run['name'] for run in fob['runs']]
        assert_equal(fob_order, correct_order)


def test_error_campaign_undefined_code():
    class TestUndefinedCodeCampaign(TestCampaign):
        codes = [('test', dict(exe='test'))]
        sweeps = [
            SweepGroup(name='test_group', nodes=1, parameter_groups=[
              Sweep([
                ParamCmdLineArg('test', 'arg', 1, ['a', 'b']),
                ParamCmdLineArg('code_dne', 'arg', 1, ['11', 'arg2'])
              ])
            ])
        ]

    try:
        c = TestUndefinedCodeCampaign('titan', '/test')
        out_dir = os.path.join(TEST_OUTPUT_DIR,
                           'test_model', 'test_error_campaign_undefined_code')
        fob_path = os.path.join(out_dir, getpass.getuser(),
                                'test_group', 'fobs.json')
        shutil.rmtree(out_dir, ignore_errors=True)
        c.make_experiment_run_dir(out_dir, _check_code_paths=False)
    except exc.CheetahException as e:
        assert 'undefined code' in str(e), str(e)
        assert 'code_dne' in str(e), str(e)
    else:
        assert False, 'error not raised on param using unknown code'


def test_error_campaign_missing_adios_xml():
    class TestMissingAdiosXMLCampaign(TestCampaign):
        codes = [('test', dict(exe='test'))]
        sweeps = [
            SweepGroup(name='test_group', nodes=1, parameter_groups=[
              Sweep([
                ParamCmdLineArg('test', 'arg', 1, ['a', 'b']),
                ParamAdiosXML('test', 'transport', 'adios_transport:test',
                        ['MPI_AGGREGATE:num_aggregators=4;num_osts=44',
                         'POSIX',
                         'FLEXPATH']),
              ])
            ])
        ]

    try:
        c = TestMissingAdiosXMLCampaign('titan', '/test')
        out_dir = os.path.join(TEST_OUTPUT_DIR,
                       'test_model', 'test_error_campaign_missing_adios_xml')
        shutil.rmtree(out_dir, ignore_errors=True)
        c.make_experiment_run_dir(out_dir, _check_code_paths=False)
    except exc.CheetahException as e:
        assert 'ADIOS XML file was not found' in str(e), str(e)
    else:
        assert False, 'error not raised on missing ADIOS XML file'


def test_error_nodes_too_small():
    class TestNotEnoughNodesCampaign(TestCampaign):
        codes = [('test1', dict(exe='test1')),
                 ('test2', dict(exe='test2'))]
        sweeps = [
            SweepGroup(name='test_group', nodes=1, parameter_groups=[
              Sweep([
                ParamCmdLineArg('test1', 'arg1', 1, ['a', 'b']),
                ParamCmdLineArg('test1', 'arg2', 2, ['1', '2']),
                ParamCmdLineArg('test2', 'arg1', 1, ['y', 'z']),
                ParamCmdLineArg('test2', 'arg2', 2, ['-1', '-2']),
              ])
            ])
        ]

    try:
        c = TestNotEnoughNodesCampaign('titan', '/test')
        out_dir = os.path.join(TEST_OUTPUT_DIR,
                           'test_model', 'test_error_not_enough_nodes')
        fob_path = os.path.join(out_dir, 'test_group', 'fobs.json')
        shutil.rmtree(out_dir, ignore_errors=True)
        c.make_experiment_run_dir(out_dir, _check_code_paths=False)
    except exc.CheetahException as e:
        assert 'nodes for group is too low' in str(e), str(e)
        assert 'need at least 2' in str(e), str(e)
        assert 'got 1' in str(e), str(e)
    else:
        assert False, 'error not raised on param using unknown code'


def test_node_layout_repeated_code():
    layout = [{ 'stage': 3, 'heat': 10}, { 'ds': 1, 'heat': 5 }]
    try:
        nl = NodeLayout(layout)
    except ValueError as e:
        assert 'heat' in str(e), str(e)
    else:
        assert False, 'error not raised on repeated code'


def test_node_layout_bad_ppn():
    layout = [{ 'stage': 3, 'heat': 10}, { 'ds': 12 }]
    nl = NodeLayout(layout)
    try:
        nl.validate(12, 2, 2)
    except ValueError as e:
        assert 'ppn > max' in str(e), str(e)
    else:
        assert False, 'error not raised on repeated code'


def test_node_layout_bad_codes_per_node():
    layout = [{ 'stage': 3, 'core': 4, 'edge': 4 }, { 'ds': 12 }]
    nl = NodeLayout(layout)
    try:
        nl.validate(12, 2, 2)
    except ValueError as e:
        assert 'codes > max' in str(e), str(e)
    else:
        assert False, 'error not raised on repeated code'


def test_node_layout_bad_shared_nodes():
    layout = [{ 'stage': 3, 'core': 4, 'edge': 4 }, { 'ds': 10, 'heat': 5 }]
    nl = NodeLayout(layout)
    try:
        nl.validate(24, 4, 1)
    except ValueError as e:
        assert 'shared nodes > max' in str(e), str(e)
    else:
        assert False, 'error not raised on repeated code'


def test_error_missing_app_dir():
    try:
        c = TestCampaign('titan', '/tmp/codar.cheetah.dne')
        out_dir = os.path.join(TEST_OUTPUT_DIR,
                       'test_model', 'test_error_missing_app_dir')
        c.make_experiment_run_dir(out_dir)
    except exc.CheetahException as e:
        assert '/tmp/codar.cheetah.dne' in str(e), str(e)
        assert 'does not exist' in str(e), str(e)
    else:
        assert False, 'error not raised on missing app dir'
