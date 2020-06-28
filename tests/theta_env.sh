module swap PrgEnv-intel/6.0.5 PrgEnv-gnu/6.0.5
module load miniconda-3.6/conda-4.5.12

# This is specific to iyakushin account. 
# Test10 environment is created with "conda create -n Test10"
# Various packages like conda, pip, numpy, scipy, pandas, matplotlib is installed into the environment with "conda install ..."
# Cheetah/Savanna is downloaded from github using "git clone https://github.com/CODARcode/cheetah.git"
# Cheeta/Savanna is installed into the environment with "python setup.py install"

source activate Test10
