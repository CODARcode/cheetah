# Gray-Scott simulation with compression

The output from Gray-Scott simulation is passed through compression/decompression with SZ, ZFP or MGARD
and the results are compared with the original data using Z-Checker and FTK. The results are visualized with ParaView

## How to run

1. Modify `env.sh` to set the environment for your situation and source it
1. Build Gray-Scott simulation as described [here](https://github.com/pnorbert/adiosvm/tree/master/Tutorial/gray-scott)
   and create a symbolic link to the `gray-scott` binary from the current directory. 
2. In the `analysis` subdirectory, build `compression` executable and create a symbolic link to it from the current directory. 
   ```
   cd analysis
   make
   cd ..
   ln -s analysis/compression
   ```
4. You might need to modify `Makefile`
5. Review configuration file for Gray-Scott `settings.json` and ADIOS configuration file `adios2.xml`
4. The campaign is defined in `gs.py`
6. Z-Checker results are dumped into `compressionResults`
   directory for each experiment.
7. `sz.config` and `zc.config` are configuration files for SZ compressor and Z-Checker.
8. To create a campaign: `make create`, to run a campaign: `make run`, etc.


## References

* [Gray-Scott]( https://github.com/pnorbert/adiosvm/tree/master/Tutorial/gray-scott )
* [SZ]( https://www.mcs.anl.gov/~shdi/download/sz-download.html )
* [ZFP]( https://zfp.readthedocs.io/en/release0.5.5/index.html )
* [MGARD]( https://github.com/CODARcode/MGARD.git )
* [Z-Checker]( https://github.com/CODARcode/Z-checker )
* [FTK]( https://github.com/CODARcode/ftk )
* [ADIOS2]( https://adios2.readthedocs.io/en/latest/index.html )




