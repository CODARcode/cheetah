The output from Gray-Scott simulation is passed through Z-Checker

1. Modify `env.sh` to set the environment and source it
2. You might need to modify `Makefile` for your situation
3. Review configuration file for Gray-Scott `settingsA.json` and adios xml file `adios2.xml`
4. The campaign is defined in `gs.py`
5. From Gray-Scott `pdf_calc.py`, `analysis/zchecker.py` is created to read data via adios2 (we are using SST in `adios2.xml`)
   compress and decompress it and compare the results with the original. Compile it make a symbolic link to it from the current
   directory:
   ```
   cd analysis
   make
   cd ..
   ln -s analysis/zchecker
   ```
6. Z-Checker results are dumped into `compressionResults`
   directory.
7. `sz.config` and `zc.config` are configuration files for SZ compressor and Z-Checker.
8. To create a campaign: `make create`, to run a campaign: `make run`, etc.
9. Gray-Scott is taken from `https://github.com/pnorbert/adiosvm/tree/master/Tutorial/gray-scott`
10. SZ is taken from `https://www.mcs.anl.gov/~shdi/download/sz-download.html`
11. Z-Checker is taken from `https://github.com/CODARcode/Z-checker`


# TODO

1. Add second variable to `zchecker.cpp`
2. Test that Z-Checker reporting tool can deal with the resulting file organization.
3. Document how to install Gray-Scott
