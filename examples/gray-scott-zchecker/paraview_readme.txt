To visualize with paraview, either save as hdf5 or convert bp to hdf5.

For example, convert the results of the simulation with compression and without:
adios_reorganize CompressionOutput.bp CompressionOutput.h5 BPFile '' HDF5 ''

Read it in ParaView with VisitPixierReader.

To visualize the results, one can run pavaview_h5.py script inside paraview.

Another alternative is to convert into VTK each (step,variable) pair:
h5tovtk -d '/Step9/U/original' CompressionOutput.h5 -o z.vtk

