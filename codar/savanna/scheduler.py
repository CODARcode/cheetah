"""
Classes related to finding a job that can run on available resources. Does
not assume any knowledge of how long each job will take. Designed for greedy
search of a job that will fit whenever resources are freed.

In the context of Cheetah workflows, it's unlikely that there will be more than
a few hundred jobs, so it's not worth optimizing the python search code very
much. It is however worth making sure that a job is run when resources are
available, since super computer resources are expensive. Basically it's worth
doing some work in python to make sure we start a big unit of work on compute
nodes.
"""

import bisect
import threading

class Scheduler:
    def __init__(self):
        pass


class JobList(object):
    """Manage a job list that can find and remove the highest cost job that
    doesn't exceed max_cost and insert new jobs.

    The job objects can be any type, but a key function must be provided
    that takes an instance of a job and returns it's cost.

    Uses a coordinated pair of sort list for costs and jobs, along with
    the bisect module. A linked list might be more efficient, since the
    list copy on insert and delete may dominate the time to do a linear
    search of a small list, but it's likely fine either way for the
    sizes we will encounter."""
    def __init__(self, costfn, initial_jobs=None):
        self._costfn = costfn
        if initial_jobs:
            self._jobs = list(initial_jobs)
            self._jobs.sort(key=costfn)
            self._costs = [costfn(job) for job in self._jobs]
        else:
            self._jobs = []
            self._costs = []
        self._lock = threading.Lock()

    def add_job(self, job):
        cost = self._costfn(job)
        with self._lock:
            i = bisect.bisect_right(self._costs, cost)
            self._costs.insert(i, cost)
            self._jobs.insert(i, job)

    def pop_job(self, max_cost):
        """Get the highest cost job that doesn't exceed max_cost, and remove
        it from the job list. Raises IndexError if the job list is empty,
        returns None if no suitable jobs exist in the list."""
        with self._lock:
            if len(self) == 0:
                raise IndexError('pop called on empty job list')
            i = bisect.bisect_right(self._costs, max_cost)
            if i:
                job = self._jobs[i-1]
                del self._jobs[i-1]
                del self._costs[i-1]
                return job
            return None

    def __len__(self):
        return len(self._costs)
