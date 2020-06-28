import sys
import glob
import os.path

run = sys.argv[1]

runs = glob.glob(f"{run}/*/*/run-*.iteration-*/codar.workflow.stderr.*")

counter = 0
for r in runs:
    if(os.path.getsize(r) > 0):
        print(f"Non-empty stderr: {r}")
        counter += 1
print(f"There are {counter} non-empty stderr files")
