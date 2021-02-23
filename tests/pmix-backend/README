This is a stripped-down version of the Savanna workflow tool for running on Summit. It runs a pipeline of applications concurrently.

`savanna.py` contains the main Savanna code. 
A workflow can be created using the `Pipeline` object, which is a collection of `Run` objects that represent independent applications.

Depending on the backend being used, Savanna will invoke an executor to run the Pipeline. We currently use the jsrun backend, with an empty skeleton provided for the PMIx backend.

The jsrun executor creates ERF files for each application in the workflow, and submits them using the `jsrun --erf_input=<erf_file_name>` command.

To Run
======

Get an allocation on Summit, and run `python example.py` to run the example.

