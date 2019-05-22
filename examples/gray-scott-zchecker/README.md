The output from Gray-Scott simulation is passed through Z-Checker

1. Modify `env.sh` to set the environment and source it
2. You might need to modify `Makefile` for your situation
3. Review configuration file for Gray-Scott `settingsA.json` and adios xml file `adios2.xml`
4. The campaign is defined in `gs.py`
5. From Gray-Scott `pdf_calc.py`, `analysis/zchecker.py` is created to read data via adios2 (we are using SST in `adios2.xml`)
   compress and decompress it and compare the results with the original. Z-Checker results are dumped into `compressionResults`
   directory.
6. `sz.config` and `zc.config` are configuration files for SZ compressor and Z-Checker.


