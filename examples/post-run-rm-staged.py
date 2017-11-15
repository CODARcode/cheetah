#!/usr/bin/env python3
"""
Example run post process script for cheetah, which deletes staged output files
to make room for future runs. Before deleting the files, the script saves the
directory contents.
"""

import json
import os
import shutil
import subprocess


OUTPUT_DIR_NAME = 'staged.bp0.dir'


def save_list_and_remove_staged(fob_path, output_dir_name):
    with open(fob_path) as f:
        fob = json.load(f)

    seen = set()

    # If the group has component subdirs set, then each code component
    # within the workflow run will have a different working directroy,
    # so we need to check the fob file and make sure we find output
    # files in all working directories.
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
    # Note: working directory will be the run directory, containing both
    # codar.cheetah.fob.json and codar.cheetah.run-params.json
    save_list_and_remove_staged('codar.cheetah.fob.json', OUTPUT_DIR_NAME)


if __name__ == "__main__":
    main()
