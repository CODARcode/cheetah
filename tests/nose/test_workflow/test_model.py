
import copy
from nose.tools import assert_equal
from codar.workflow.model import Pipeline, Run, srun, aprun

test_pipe_data = dict(
    id="1",
    node_layout=[{ 'heat': 16 }, { 'stage': 8 }],
    working_dir='/test',
    runs=[
      { 'name': 'heat',
        'exe': '/test/heat_transfer',
        'args': [],
        'nprocs': 100 },
      { 'name': 'stage',
        'exe': '/test/stage_write',
        'args': [],
        'nprocs': 25 },
    ]
)


def test_pipeline_set_node_layout():
    pipe = Pipeline.from_data(test_pipe_data)
    # ceil(100 / 16) + ceil(25 / 8) = 7 + 4 = 11
    # Note that ppn is not used when node layout has been specified.
    pipe.set_ppn(16)
    assert_equal(pipe.get_nodes_used(), 11)

    pipe.set_ppn(32)
    assert_equal(pipe.get_nodes_used(), 11)


def test_pipeline_default_node_layout():
    # Create copy of test data with node layout removed
    data2 = copy.deepcopy(test_pipe_data)
    del data2['node_layout']
    pipe2 = Pipeline.from_data(data2)
    # ceil(100 / 16) + ceil(25 / 16) = 7 + 2 = 9
    pipe2.set_ppn(16)
    assert_equal(pipe2.get_nodes_used(), 9)

    # ceil(100 / 32) + ceil(25 / 32) = 4 + 1 = 5
    pipe2.set_ppn(32)
    assert_equal(pipe2.get_nodes_used(), 5)


def test_srun_wrap():
    # test that node count is calculated correctly and passed to srun
    pipe = Pipeline.from_data(test_pipe_data)
    pipe.set_ppn(32)
    args_heat = srun.wrap(pipe.runs[0], False)
    print(args_heat)
    assert_equal(args_heat[4], '7')
    args_stage = srun.wrap(pipe.runs[1], False)
    print(args_stage)
    assert_equal(args_stage[4], '4')


def test_aprun_wrap():
    # aprun uses tasks per node rather than node count
    pipe = Pipeline.from_data(test_pipe_data)
    pipe.set_ppn(16)
    args_heat = aprun.wrap(pipe.runs[0], False)
    print(args_heat)
    assert_equal(args_heat[4], '16')
    args_stage = aprun.wrap(pipe.runs[1], False)
    print(args_stage)
    assert_equal(args_stage[4], '8')
