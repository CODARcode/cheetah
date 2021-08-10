import sys
import os
import glob
import pdb
import logging
import threading
import subprocess
from queue import Queue
import codar.savanna.main as savanna_main

logger = logging.getLogger('codar.savanna.multisg')

# Queue to hold all fobs as tasks
q = Queue()

# Queue to hold list of nodes
nq = Queue()


class SavannaArgs():
    def __init__(self, sg_path):
        self._sg_path            = sg_path
        self.codar_wf_script     = os.environ['CODAR_WORKFLOW_SCRIPT']
        self.runner              = "jsrun"
        self.log_file            = os.path.join(sg_path, "codar.FOBrun.log")
        self.log_level           = "DEBUG"
        self.max_nodes           = self._get_group_nodes()
        self.machine_name        = "summit"
        self.processes_per_node  = 42
        self.status_file         = os.path.join(sg_path, "codar.workflow.status.json")
        self.producer_input_file = os.path.join(sg_path, "fobs.json")
        self.stdout_path         = os.path.join(sg_path, "codar.workflow.stdout")
        self.stderr_path         = os.path.join(sg_path, "codar.workflow.stderr")


    def _get_group_nodes(self):
        """
        Get the nodes requested for this group. It won't be in env.
        """
        group_env = os.path.join(self._sg_path, "group-env.sh")
        key = 'CODAR_CHEETAH_GROUP_NODES'
        with open(group_env, "r") as f:
            lines = f.readlines()
        for line in lines:
            if key in line:
                return int(line.split(key)[1].split('"')[1])


def configure_logger():
    handler = logging.FileHandler('codar.FOBrun.log')
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel('DEBUG')
    logger.info("Starting Savanna multi SweepGroup runner")
    

def verify_pwd_campaign_root():
    """
    Verify current directory is the high-level campaign root/username directory.
    This prevents launches from other directories.
    """
    campaign_root = False
    if os.path.isfile("../.campaign"):
        campaign_root = True
    if not campaign_root:
        print("ERROR: Current directory must be campaign-root/username")
        sys.exit(1)


def populate_nq():
    """
    Get num nodes allocated to this job and add them to queue
    """
    # s = set()
    # nodes_str = os.environ['LSB_HOSTS'].split()
    # for n in nodes_str:
    #     if 'batch' not in n:
    #         s.add(n)

    # assert len(s) > 0, \
    #     "ERROR: Number of allocated nodes found to be zero. Aborting."
    # 
    # logger.info("{} nodes allocated to this job".format(len(s)))
    # for i in range(len(s)):
    #     nq.put(i+1)

    n = sg_nodes_reqd("./")
    logger.info("{} nodes allocated to this job".format(n))
    for i in range(n):
        nq.put(i+1)


def get_sg_list():
    """
    Get list of SG's in this campaign,
    and add them to the task queue.
    """
    dir_entries = os.listdir(".")
    for e in dir_entries:
        if os.path.isdir(os.path.join(".", e)):
            q.put(e)
    logger.info("Found {} sweepgroups".format(q.qsize()))


def sg_nodes_reqd(sg):
    """
    Get the no. of nodes requested by this sg.
    Return env var from group-env.sh
    """
    group_env = os.path.join(".", sg, "group-env.sh")
    key = 'CODAR_CHEETAH_GROUP_NODES'
    with open(group_env, "r") as f:
        lines = f.readlines()
    for line in lines:
        if key in line:
            return int(line.split(key)[1].split('"')[1])


def run_sg(sg_path, node_list):
    """
    Call the Savanna main.py for an SG.
    This is called by a separate thread.
    """
 
    # Set up inputs args for the savanna function
    sa = SavannaArgs(sg_path)
    run_str = "python3 {} " \
              "--runner={} " \
              "--producer-input-file={} " \
              "--max-nodes={} " \
              "--processes-per-node={} " \
              "--log-file={} " \
              "--machine-name={} " \
              "--status-file={} " \
              "--log-level={} ".format(             \
              sa.codar_wf_script,                   \
              sa.runner, sa.producer_input_file,    \
              sa.max_nodes, sa.processes_per_node,  \
              sa.log_file, sa.machine_name,         \
              sa.status_file, sa.log_level)

    # Open stdout and stderr path for Popen
    fdout = open(sa.stdout_path, "w")
    fderr = open(sa.stderr_path, "w")

    # Setup node list env var
    env = os.environ.copy()
    nodelist_str = ""
    for n in node_list:
        nodelist_str = nodelist_str + "{};".format(n)
    env['CODAR_CHEETAH_NODE_LIST'] = nodelist_str
    
    # Create fake jobid.txt file for status reporting to work
    with open(os.path.join(sg_path, "codar.cheetah.jobid.txt"), "w") as f:
        f.write("LSF:Job <000000> is submitted to default queue <batch>")

    logger.info("Starting SweepGroup {} with {} nodes: {}, args: {}".format(\
        sg_path, len(node_list), node_list, run_str))

    # Launch savanna main
    subp_args = run_str.split()
    subp = subprocess.Popen(subp_args, env=env, stdout=fdout, stderr=fderr)
    subp.wait()

    # Done. Close stdout and stderr files and release the nodes
    logger.info("{} done. Releasing nodes.".format(sg_path))
    fdout.close()
    fderr.close()
    for n in node_list:
        nq.put(n)

    # Signal task done
    q.task_done() 


#----------------------------------------------------------------------------#
if __name__=='__main__':
    
    # Setup
    configure_logger()
    verify_pwd_campaign_root()
    populate_nq()
    get_sg_list()

    # Start processing sweepgroups
    while not q.empty():
        sg = q.get()
        logger.info("Retrieved sg {}. Now fetching nodes".format(sg))
        fn = sg_nodes_reqd(sg)
        sg_nodes = []
        for i in range(fn):
            sg_nodes.append(nq.get())
        logger.info("Obtained {} nodes for {}".format(fn, sg))

        # Launch thread to run sweepgroup
        t = threading.Thread(target=run_sg, args=(sg, sg_nodes))
        t.start()
    
    # Wait for all tasks (sweepgroups) to be done
    logger.info("Done scheduling. Now waiting for all to complete.")
    q.join()

    # All done. Congratulations. 
    logger.info("All SweepGroups done. Congratulations")
     
