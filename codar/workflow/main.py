"""Main program for executing workflow script with different producers and
runners."""


import argparse
import threading

from codar.workflow.producer import JSONFilePipelineReader
from codar.workflow.consumer import PipelineRunner
from codar.workflow.monitor import PipelineMonitor
from codar.workflow.model import Pipeline, Run, mpiexec, aprun


def parse_args():
    parser = argparse.ArgumentParser(description='HPC Worflow script')
    parser.add_argument('--max-procs', type=int, required=True)
    parser.add_argument('--runner', choices=['mpiexec', 'aprun', 'none'],
                        required=True)
    parser.add_argument('--producer', choices=['file'], default='file')
    parser.add_argument('--producer-input-file')

    return parser.parse_args()


def main():
    args = parse_args()

    if args.runner == 'mpiexec':
        runner = mpiexec
    elif args.runner == 'aprun':
        runner = aprun
    else:
        runner = None
    monitor = PipelineMonitor()
    consumer = PipelineRunner(args.max_procs, runner, monitor)
    producer = JSONFilePipelineReader(args.producer_input_file)

    t_consumer = threading.Thread(target=consumer.run_pipelines)
    t_consumer.start()

    t_monitor = threading.Thread(target=monitor.run)
    t_monitor.start()

    # producer runs in this main thread
    for pipeline in producer.read_pipelines():
        consumer.add_pipeline(pipeline)

    # signal that there are no more pipelines and thread should exit
    # when reached
    consumer.add_pipeline(None)

    # wait for consumer to finish all the pipelines
    t_consumer.join()

    # signal monitor to finish after all processes have exited
    monitor.stop()
    t_monitor.join()
