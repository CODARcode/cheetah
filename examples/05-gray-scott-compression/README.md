The output from Gray-Scott simulation is passed through compression/decompression with SZ, ZFP or MGARD
and the results are compared with the original data using Z-Checker and FTK. The results are visualized with ParaView

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
9. Gray-Scott is taken from https://github.com/pnorbert/adiosvm/tree/master/Tutorial/gray-scott
10. SZ is taken from https://www.mcs.anl.gov/~shdi/download/sz-download.html
11. Z-Checker is taken from https://github.com/CODARcode/Z-checker
12. MGARD is taken from https://github.com/CODARcode/MGARD.git
13. FTK is taken from https://github.com/CODARcode/ftk




