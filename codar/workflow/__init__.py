"""Classes for running pipelines of MPI tasks based on a specified
total process limit. The system is designed to use three threads:

1. consumer thread: get pipelines from queue and execute them when process
 slots become available. Stops when a None pipeline is received.

2. producer thread: add pipelines to queue. Can be from file or from network
 service.

3. monitor thread: monitor processes spawned by consumer threads and signal
 when process slots become free
"""

from codar.workflow.model import Pipeline, Run, mpiexec, aprun
