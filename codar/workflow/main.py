"""Main program for executing workflow script with different producers and
runners."""

import argparse
import threading
import logging

from codar.workflow.producer import JSONFilePipelineReader
from codar.workflow.consumer import PipelineRunner
from codar.workflow.model import mpiexec, aprun


def parse_args():
    parser = argparse.ArgumentParser(description='HPC Worflow script')
    parser.add_argument('--max-procs', type=int)
    parser.add_argument('--max-nodes', type=int)
    parser.add_argument('--processes-per-node', type=int)
    parser.add_argument('--runner', choices=['mpiexec', 'aprun', 'none'],
                        required=True)
    parser.add_argument('--producer', choices=['file'], default='file')
    parser.add_argument('--producer-input-file')
    parser.add_argument('--log-file')
    parser.add_argument('--log-level',
                        choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL'],
                        default='INFO')

    args = parser.parse_args()

    if not (bool(args.max_procs) ^ bool(args.max_nodes)):
        parser.error("specify one of --max-procs and --max-nodes")
    if args.max_nodes and not args.processes_per_node:
        parser.error("option --max-nodes requires --processes-per-node")

    return args


def main():
    args = parse_args()

    if args.runner == 'mpiexec':
        runner = mpiexec
    elif args.runner == 'aprun':
        runner = aprun
    else:
        runner = None

    if args.log_file:
        logger = logging.getLogger('codar.workflow')
        handler = logging.FileHandler(args.log_file)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(args.log_level)
    else:
        logger = None

    consumer = PipelineRunner(runner=runner, logger=logger,
                              max_procs=args.max_procs,
                              max_nodes=args.max_nodes,
                              processes_per_node=args.processes_per_node)
    producer = JSONFilePipelineReader(args.producer_input_file)

    t_consumer = threading.Thread(target=consumer.run_pipelines)
    t_consumer.start()

    # producer runs in this main thread
    for pipeline in producer.read_pipelines():
        consumer.add_pipeline(pipeline)

    # signal that there are no more pipelines and thread should exit
    # when reached
    consumer.stop()

    # wait for consumer to finish all the pipelines
    t_consumer.join()
