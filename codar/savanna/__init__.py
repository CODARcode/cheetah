"""Classes for running pipelines of MPI tasks based on a specified
total process limit. The system is designed to use two + N threads:

1. consumer thread: get pipelines from queue and execute them when process
   slots become available. Stops when a None pipeline is received.

2. producer thread: add pipelines to queue. Can be from file or from network
   service.

3. monitor threads: each process spawned by the consumer thread has a monitor
   thread that blocks on the processes completing with a timeout, and kills the
   process if it's not done after the timeout is reached.
"""

from codar.savanna.pipeline import Pipeline
from codar.savanna.run import Run
from codar.savanna.runners import mpiexec, aprun, jsrun
from codar.savanna.consumer import PipelineRunner
