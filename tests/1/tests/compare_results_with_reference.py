import glob
import sys

def diff_lines(one, two, ref):
    diff = 0
    for pair in zip(one, two):
        if(pair[0] != pair[1] and pair[0].find("time(s)") < 0 ):
            print(f"Difference: in {ref}: {pair}")
            diff += 1
    return diff

run = sys.argv[1]

references = glob.glob("reference/*/run-*.iteration-*/codar.workflow.stdout.*")
references.sort()

runs = glob.glob(f"{run}/*/*/run-*.iteration-*/codar.workflow.stdout.*")
runs.sort()

diff = 0

for pair in zip(references, runs):
    ref_f = open(pair[0])
    ref_lines = ref_f.readlines()
    ref_f.close()

    run_f = open(pair[1])
    run_lines = run_f.readlines()
    run_f.close()

    diff += diff_lines(ref_lines, run_lines, pair[0])

print(f"There are {diff} differences in comparison with the reference")
