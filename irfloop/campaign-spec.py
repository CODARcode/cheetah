import math
from codar.cheetah import Campaign
from codar.cheetah import parameters as p
from codar.savanna.machines import SummitNode
from codar.cheetah.parameters import SymLink
import node_layouts as node_layouts
import sweeps as sweeps
import copy
import sys
import os

class IRF(Campaign):
	name = "IRF"
	# List of applications in your campaign
	codes = [ ("train", dict(exe="ranger")),
	("test", dict(exe="ranger")) ]

	# List of machines supported by this campaign
	supported_machines = ['summit']

	# If something in a run fails, abort that run (not the whole batch job)
	kill_on_partial_failure = True

	# Do you want to run some special setup script in each run directory at creation time? Usually no.
	run_dir_setup_script = None

	# Post processing to be performed after each experiment in the batch job completes
	#run_post_process_script = "bin/cleanup.sh"

	# Make your campaign directory readable to others in your group. Not required to be changed.
	umask = '027'

	# Job submission options. -- VERIFY YOUR PROJECT ID BELOW --
	scheduler_options = {'summit': {'project':'SYB105'}}

	# Setup script to be run before an experiment starts. Do your `module load`, `export PATH`, `export LD_LIBRARY_PATH` here.
	app_config_scripts = {'summit':'env-setup.sh'}

	sweepgroups = []
	for depvarname in [os.environ.get('DEPVARNAME')]:
		input_file_list = []
		for foldRepeat in range(10):
			for foldCount in range(5):
				input_file_list.append("/gpfs/alpine/syb105/proj-shared/Projects/iRF/cliffamDissertation/aThalNetworks/methylationLOOP/cheetahRun/Specifications/Data/input-files/foldRepeat_{}/fold_{}/fold{}_set{}_train_noSampleIDs.txt".format(foldRepeat, foldCount, foldRepeat, foldCount))

		sw = []
		for input_file in input_file_list:
			sw.append(sweeps.test_sweep(depvarname, input_file))

		sweepgroups.append(
			p.SweepGroup ("methLOOP_{}".format(depvarname),                     # give it a name
                  walltime=1200,               # total job walltime
                  per_run_timeout=3600,        # timeout for each experiment in the batch job
                  parameter_groups=copy.deepcopy(sw),     # list of sweeps in this SweepGroup
                  launch_mode='default',      # default or mpmd
                  tau_profiling=False,        # profiling using the TAU tool
                  tau_tracing=False,          # tracing using the TAU tool
                  nodes=50,                    # comment out to auto-calculate
                  component_inputs = {'train': [SymLink('input-files')] },   # Input files required by the app. Lets make it a symbolic link
                  run_repetitions=0) )         # No. of times each experiment/run must be repeated
	# Activate the SweepGroup
	sweeps = {'summit':sweepgroups}
