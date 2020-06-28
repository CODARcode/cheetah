# How to build the dependencies on Summit

* Our attempt to use spack on Summit to build all the dependencies so far failed and for now we are doing it manually.
* Load the following modules
  ```
  module load gcc/7.4.0	
  module load zeromq/4.2.5
  module load libfabric/1.7.0
  module load python/3.7.0-anaconda3-5.3.0
  ```
* Create conda environment
  ```
  conda create -n Test
  conda install conda pip numpy scipy pandas matplotlib
  source activae Test
  ```	
* Build mpi4py from source (using `conda install` is not a good idea since we want to make sure that system MPI is used)
  ```
  wget https://bitbucket.org/mpi4py/mpi4py/downloads/mpi4py-3.0.3.tar.gz
  tar xvf mpi4py-3.0.3.tar.gz
  cd mpi4py-3.0.3
  python setup.py install
  ```
* Install Cheetah/Savanna
  ```
  git clone git@github.com:CODARcode/cheetah.git
  cd cheetah
  python setup.py install
  ```
* Build simplest ADIOS installation with python support
  ```
  git clone https://github.com/ornladios/ADIOS2.git ADIOS2
  cd ADIOS2
  mkdir build
  cd build
  cmake -DCMAKE_CXX_COMPILER=`which g++` -DCMAKE_C_COMPILER=`which gcc` -DCMAKE_Fortran_COMPILER:FILEPATH=`which gfortran` \
  -DADIOS2_USE_MPI:STRING=True -DCMAKE_INSTALL_PREFIX=$HOME/SOFT_INSTALL/adios-2.5_simplest-gcc-7.4.0 -DADIOS2_USE_HDF5:STRING=False 
  -DADIOS2_USE_SZ:STRING=False  -DADIOS2_USE_ZFP:STRING=False -DADIOS2_USE_Blosc:STRING=False -DADIOS2_USE_BZip2:STRING=False 
  -DADIOS2_USE_PNG:STRING=False -DADIOS2_USE_DataMan:STRING=True  -DADIOS2_USE_Fortran:STRING=False ..
  make -j20
  make install
  ```
* Create a module (lua file) to use ADIOS, for example:
  ```
  dir = os.getenv("HOME") .. '/SOFT_INSTALL/adios-2.5_simplest-gcc-7.4.0/'
  prepend_path('PATH', dir .. 'bin')
  prepend_path('LD_LIBRARY_PATH', dir .. 'lib64')
  prepend_path('CPATH', dir .. 'include')
  prepend_path('PYTHONPATH', dir .. 'lib64/python3.6/site-packages')
  setenv('ADIOS2_DIR', dir)

  ```
* Use `module use ...` to make the corresponding directory with modules visible and load ADIOS, for example, as follows:
  ```
  module load Compiler/gcc/7.4.0/adios2/2.5_simplest-gcc-7.4.0
  ```
* Launch python interpreter and test that you can
  ```
  import adios2
  import cheetah
  import mpi4py
  import numpy
  import pandas
  ```
* If it worked, you are ready to run tests