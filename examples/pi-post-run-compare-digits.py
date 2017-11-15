#!/usr/bin/env python3

import sys
import json
import os.path


def compare_pi_digits(ref_path, result_path):
    with open(ref_path) as ref_file, open(result_path) as result_file:
        ref = ref_file.read()
        result = result_file.read()
        if ref[0] != result[0]:
            return 0
        if result[1] != '.':
            return 1
        for i in range(2, min(len(ref), len(result))):
            if ref[i] != result[i]:
                break
        # don't count decimal
        return i-1


def main(fob_path):
    ref_path = os.path.join(os.path.dirname(__file__), 'pi1M.txt')
    with open(fob_path) as f:
        fob_data = json.load(f)
    out_dir = fob_data['working_dir']
    run_output = os.path.join(out_dir, 'codar.workflow.stdout.pi')
    digits = compare_pi_digits(ref_path, run_output)
    digits_file_path = os.path.join(out_dir, 'post-digits.txt')
    with open(digits_file_path, 'w') as f:
        f.write(str(digits))
        f.write('\n')


if __name__ == '__main__':
    fob_path = 'codar.cheetah.fob.json'
    main(fob_path)

    # uncomment to test forcing workflow exit when this has nonzero exit
    #sys.exit(1)
