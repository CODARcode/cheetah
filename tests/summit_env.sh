module use $HOME/privatemodules
export MYSOFT=$HOME/SOFT_INSTALL
export MYSRC=$HOME/SOFT_SRC
export MYMOD=$HOME/privatemodules
export PATH=$HOME/bin:$PATH


shopt -s direxpand
module load python/3.7.0-anaconda3-5.3.0
module load gcc/7.4.0
module load Compiler/gcc/7.4.0/adios2/2.5_simplest-gcc-7.4.0
module load zeromq/4.2.5
module load libfabric/1.7.0

# This is specific to iyakushin account. 
# Test10 environment is created with "conda create -n Test10"
# Various packages like conda, pip, numpy, scipy, pandas, matplotlib is installed into the environment with "conda install ..."
# Cheetah/Savanna is downloaded from github using "git clone https://github.com/CODARcode/cheetah.git"
# Cheeta/Savanna is installed into the environment with "python setup.py install"


source activate Test11
