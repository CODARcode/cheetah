"""Main program for executing workflow script with different producers and
runners."""

import argparse
import threading
import logging
import signal
import os

from codar.savanna.producer import JSONFilePipelineReader
from codar.savanna.consumer import PipelineRunner
from codar.savanna.runners import mpiexec, aprun, srun, jsrun


consumer = None


def parse_args():
    parser = argparse.ArgumentParser(description='HPC Worflow script')
    parser.add_argument('--max-nodes', type=int, required=True)
    parser.add_argument('--processes-per-node', type=int, required=True)
    parser.add_argument('--runner', choices=['mpiexec', 'aprun', 'srun', 'jsrun','none'], required=True)
    parser.add_argument('--runner_extra', default="")

    parser.add_argument('--producer', choices=['file'], default='file')
    parser.add_argument('--producer-input-file')
    parser.add_argument('--log-file')
    parser.add_argument('--log-level',
                        choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL'],
                        default='INFO')
    parser.add_argument('--status-file')

    args = parser.parse_args()

    return args


def main():
    global consumer

    args = parse_args()

    if args.runner == 'mpiexec':
        runner = mpiexec
    elif args.runner == 'aprun':
        runner = aprun
    elif args.runner == 'srun':
        runner = srun
    elif args.runner == 'jsrun':
        runner = jsrun
    elif args.runner == 'none':
        runner = None
    else:
        # Note: arg parser should have caught this already
        raise ValueError('Unknown runner: %s' % args.runner)

    runner.AddExtra(args.runner_extra)
    logger = logging.getLogger('codar.savanna')
    if args.log_file:
        handler = logging.FileHandler(args.log_file)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(args.log_level)
    else:
        logger.addHandler(logging.NullHandler())

    logger.info('starting savanna job %s', get_job_id())

    consumer = PipelineRunner(runner=runner,
                              max_nodes=args.max_nodes,
                              processes_per_node=args.processes_per_node,
                              status_file=args.status_file)

    producer = JSONFilePipelineReader(args.producer_input_file)

    t_consumer = threading.Thread(target=consumer.run_pipelines)
    t_consumer.start()

    # producer runs in this main thread
    for pipeline in producer.read_pipelines():
        consumer.add_pipeline(pipeline)

    # signal that there are no more pipelines and thread should exit
    # when reached
    consumer.stop()

    # set up signal handlers for graceful exit
    def handle_signal_kill_consumer(signum, frame):
        consumer.kill_all()

    signal.signal(signal.SIGTERM, handle_signal_kill_consumer)
    signal.signal(signal.SIGINT,  handle_signal_kill_consumer)

    # All threads created for workflow are non-daemon, so the
    # interpreter will not exit until all threads exit. Doing an
    # explicit join on the consumer thread is not necessary, and
    # actually causes problems because Python can't handle signals if
    # the main thread is in a join, since that is basically pure C code
    # (pthread_join).


def get_job_id():
    scheduler_vars = dict(
        SLURM='SLURM_JOB_ID',
        PBS='PBS_JOBID',
        COBALT='COBALT_JOBID'
        )
    for name, var in scheduler_vars.items():
        val = os.environ.get(var)
        if val:
            return '%s:%s' % (name, val)
    # fall back to using pid
    return 'PID:%s' % os.getpid()


# allow this module to be run as a script from within a pip/setuptools
# installed distribution
if __name__ == '__main__':
    main()
