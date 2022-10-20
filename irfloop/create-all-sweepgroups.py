"""
This program reads all depvarnames from a txt file which has one depvarname per line.
It then spawns multiple threads, each of which execute the Cheetah create-campaign command.

Each command is of the type DEPVARNAME=<depvarname> cheetah create-campaign -e campaign-spec.py .. 
In campaign-spec.py, the depvarname is set by reading the DEPVARNAME environment variable.
"""

import threading
from queue import Queue
import subprocess
import os


infname       = "depvarnamelist.txt"
app_root      = "/gpfs/alpine/world-shared/syb105/cliffam/methylationLOOP/cheetahRun/Specifications/Data"
campaign_out  = "./test-campaign"
cheetah_root  = "/ccs/proj/csc299/kmehta/cheetah"
num_threads   = 8


def read_depvarnames_from_file(q):
    """ Reads all 80k depvarnames from a txt file which has one depvarname
    per line.
    """


    # Open file and read all lines into a list
    try:
        with open(infname, "r") as f:
            lines = f.readlines()
    except:
        print("Aborting. Could not open {}".format(infname))
    
    # Remove trailing newline from each line in the list and add to queue
    for line in lines:
        depvarname = line.strip()
        q.put(depvarname)


def t_create_sweep_group():
    """ Function to be called by threads to create SweepGroups.
    """
    env = os.environ.copy()
    env['PATH'] = cheetah_root + "/bin" + os.pathsep + env['PATH']
    env['PYTHONPATH'] = cheetah_root + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = os.getcwd() + os.pathsep + env['PYTHONPATH']
    run_str = "cheetah create-campaign " \
              "-a {} -e campaign-spec.py -m summit " \
              "-o {}".format(app_root, campaign_out)
    args = run_str.split()

    while not q.empty():
        depvarname = q.get()
        env['DEPVARNAME'] = depvarname
        subp = subprocess.Popen(args, env=env)
        # print("Running DEPVARNAME={} {}".format(depvarname, subp.args))
        subp.wait()

        q.task_done()


# ---------------- MAIN FUNCTION ---------------- #
if __name__ == '__main__':
    q = Queue()
    read_depvarnames_from_file(q)

    # Now spawn threads to create SweepGroups
    for i in range(num_threads):
        worker = threading.Thread(target=t_create_sweep_group)
        worker.start()

    # Wait for all threads to finish
    q.join()

