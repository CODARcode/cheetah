To visualize with paraview, either save as hdf5 or convert bp to hdf5.

For example, convert the results of the simulation:
adios_reorganize CompressionOutput.bp CompressionOutput.h5 BPFile '' HDF5 ''

You can read such an hdf5 file in ParaView with VisitPixierReader.

To visualize the results, go to the directory with CompressionOutput.h5, run pavaview_h5.py script inside ParaView - it will load a function myf(var='U', step=23).
In Python prompt you can now call this functions with 'U' or 'V' and any step from 0 to 23. It will run an animation that goes through all the X-slices for a particular
time step.

This was tested with ParaView 5.6.0 under Ubuntu 18.0.4



