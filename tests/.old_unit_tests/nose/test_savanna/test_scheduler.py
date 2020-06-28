

from nose.tools import assert_equal, assert_in

from codar.savanna.scheduler import JobList


def test_job_list():
    jl = JobList(lambda x: x, [23, 2, 256, 17, 99])
    assert_equal(jl.pop_job(17), 17)
    assert_equal(jl.pop_job(255), 99)
    assert_equal(jl.pop_job(50), 23)
    assert_equal(jl.pop_job(1024), 256)
    assert_equal(jl.pop_job(1), None)
    assert_equal(jl.pop_job(256), 2)

    assert_equal(len(jl), 0)
    try:
        jl.pop_job(100)
    except IndexError as e:
        assert_in('empty', str(e))
    else:
        assert False, 'expected IndexError, got no error'
