#!/usr/bin/env python3
"""
Main script for calling cheetah subcommands.
"""

import os
import sys
import argparse

from codar.cheetah.loader import load_experiment_class
from codar.cheetah import report_generator, status


def main():
    top_parser = argparse.ArgumentParser(
                    description='Cheetah experiment harness',
                    usage='''cheetah.py <command> [<options>]
 Supported commands:
    create-campaign    Create a campaign directory from a spec file
    generate-report    Generate a report of results from a completed campaign
    status             Print information about a campaign
    help               Show this help message and exit

 For details on running each command, run 'cheetah.py <command> -h'.
''')
    commands = ['help', 'create-campaign', 'generate-report', 'status']
    top_parser.add_argument('command', help='Subcommand to run',
                            choices=commands)
    args = top_parser.parse_args(sys.argv[1:2])
    prog = 'cheetah.py ' + args.command
    command_args = sys.argv[2:]
    if args.command == 'create-campaign':
        create_campaign(prog, command_args)
    elif args.command == 'generate-report':
        generate_report(prog, command_args)
    elif args.command == 'status':
        status_command(prog, command_args)
    elif args.command == 'help':
        top_parser.print_help()
        sys.exit(os.EX_OK)
    else:
        assert False, 'unknown command: %s' % args.command


def create_campaign(prog, argv):
    parser = argparse.ArgumentParser(prog=prog,
                description='Create a campaign directory')
    parser.add_argument('-e', '--experiment-spec', required=True,
            help="Path to Python module containinig an experiment definition")
    parser.add_argument('-a', '--app-directory', required=True,
            help="Path to application directory containing executables")
    parser.add_argument('-m', '--machine', required=True,
            help="Name of machine to generate runner for")
    parser.add_argument('-o', '--output-directory', required=True,
            help="Output location where run scripts are saved")
    args = parser.parse_args(argv)

    eclass = load_experiment_class(args.experiment_spec)
    machine_name = args.machine
    # TODO: handle case where cheetah is run on local linux but target
    # different machine with different locations for app and output
    app_dir = os.path.abspath(args.app_directory)
    output_dir = os.path.abspath(args.output_directory)

    e = eclass(machine_name, app_dir)
    e.make_experiment_run_dir(output_dir)


def generate_report(prog, argv):
    parser = argparse.ArgumentParser(prog=prog,
                description="Generate a report for a completed campaign")
    parser.add_argument('-o', '--output-file', required=False,
                        default="./campaign_results.csv",
                        help="Redirect output to file, else write as "
                             "./campaign_results.csv")

    args = parser.parse_args(argv)
    report_generator.generate_report()


def status_command(prog, argv):
    parser = argparse.ArgumentParser(prog=prog,
                description="Get status of an existing campaign")
    parser.add_argument('-c', '--campaign-directory', required=False,
                        default='.',
                        help='Get status for top level campaign directory')
    parser.add_argument('-u', '--users', required=False,
                        default=None, nargs='*',
                        help='Get status for specific user(s) only')
    parser.add_argument('-g', '--groups', required=False,
                        default=None, nargs='*',
                        help='Get status for specific sweep group(s) only')
    parser.add_argument('-d', '--details', required=False, action='store_true',
                        help='Show detailed run counts for each group')

    args = parser.parse_args(argv)
    status.print_campaign_status(args.campaign_directory,
                                 filter_user=args.users,
                                 filter_group=args.groups,
                                 group_details=args.details)


if __name__ == '__main__':
    main()
