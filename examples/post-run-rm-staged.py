#!/usr/bin/env python3
"""
Example run post process script for cheetah, which deletes staged output files
to make room for future runs. Before deleting the files, the script saves the
directory contents.
"""

import sys
import json
import os
import shutil
import subprocess


OUTPUT_DIR_NAME = 'staged.bp0.dir'


def save_list_and_remove_staged(fob_path, output_dir_name):
    with open(fob_path) as f:
        fob = json.load(f)

    seen = set()

    default_working_dir = fob["working_dir"]

    for run in fob["runs"]:
        working_dir = run.get("working_dir") or default_working_dir
        if working_dir in seen:
            continue
        seen.add(working_dir)
        output_path = os.path.join(working_dir, output_dir_name)
        print("checking for", output_path)
        if not os.path.isdir(output_path):
            continue

        ls_out_file = os.path.join(working_dir, 'codar.post_run.ls.txt')
        with open(ls_out_file, 'w') as outf:
            subprocess.check_call(['ls', '-l', output_path], stdout=outf)
        shutil.rmtree(output_path)


def main():
    if len(sys.argv) != 2:
        print("Usage: %s fob_file_path" % sys.argv[0])
        sys.exit(1)
    save_list_and_remove_staged(sys.argv[1], OUTPUT_DIR_NAME)


if __name__ == "__main__":
    main()
