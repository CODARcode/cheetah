* To visualize with paraview, either save as `hdf5` or convert `bp` to `hdf5` since at the moment paraview cannot read `bp` files.
* For example, to convert `bp` file into `h5` file:
  ```
  adios_reorganize CompressionOutput.bp CompressionOutput.h5 BPFile '' HDF5 ''
  ```
* You can read such an `hdf5` file in ParaView with `VisitPixierReader`. No other reader seems to be able to handle it.
* To visualize the results, run `paraview_compare.py` script inside ParaView python shell.
  It will load functions: `compareX(var='U', step=23, fn='CompressionOutput.h5', nx = 32)` and `compareT(var='U', X=16, fn='CompressionOutput.h5', steps=24)`.
* In ParaView Python shell you can now call these functions. `compareX()` shows 2D slice animation over `X` with fixed `T` for both original and lossy data.
  `compareT()` shows 2D slice animation over `T` with fixed `X` for both original and lossy data.
* By default, the camera is over `X` and only one side of the cube will be seen. If you want to change view in a predictable way, you can use `angle.py` macro, for example.
* The script was tested with ParaView 5.6.0 under Ubuntu 18.0.4
* One can find links to some animations in `movies` directory.
* `animations.py` script automates movie generation: first run `paraview_compare.py` in python shell, then run `animations.py`.



