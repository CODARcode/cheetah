* Animations are available in box:  https://anl.box.com/s/c7x29xf49mofmeftwqrlqe4nt6heulyh
* Notice: `U` at the beginning has some noise which compression does not handle well and one can see a difference between the original and lossy data.
* As the simulation goes, the pattern emerges and noise becomes negligible in comparison. Once this happen, the difference between original and lossy data becomes invisible.
* The movies are generated for 3 levels of SZ compression. Look into `compression.txt` file for details.
* For each compression level there are 2 directories: `withoutFTK` and `withFTK`.
* Compression/decompression of 3D volume is done at each time step.
* Correspondingly FTK computes local maxima in 3D volume at each time step.
* FTK shows some differences between original and lossy data that is not visible by simply looking at slices.
* Movies at fixed angles is not the best way to see that FTK seems to be doing a reasonable job finding the minima: it is more useful to use paraview interactively for that.
* Notice that at the beginning of simulation, there are thousands of local minima due to noise. As the simulation goes, noise smooths out and there are only a few tens of
  local maxima left.
