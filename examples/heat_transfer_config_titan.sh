export LD_LIBRARY_PATH=/ccs/proj/csc143/CODAR_Demo/titan.gnu/adios/lib/:$LD_LIBRARY_PATH

# NOTE: this is needed for the sosflow version of the experiment,
# something idiosyncratic about the python2 install, which is used by
# sos analysis.
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/sw/xk6/python/2.7.9/sles11.3_gnu4.3.4/lib
