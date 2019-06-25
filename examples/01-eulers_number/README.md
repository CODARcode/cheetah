# Cheetah example: Calculating Euler's number

To demonstrate the usage of Cheetah, we will look at a simple Python3
script which calculates Euler's number (`e`) using two different methods.
It takes three positional arguments: the first is a string describing which
of the methods to use, the second is a parameter to the calculation method
that describes how many iterations or how precise to try to make the
calculation (meaning depends on the method), and the third is a precision
to use with the stdandard library Decimal module in python. If the third
argument is not specified, built in floating point is used instead.

For this examples, we suppose that the application writer wants to understand
which method is 'better' - gets more digits correct in a short amount of time.
To do this, we need to run the application many times with different values
to the arguments and examine the output.

## The application

The source code is contained in a single source file: [calc\_e.py](calc_e.py).
There are no dependencies other than python3.

## The Cheetah campaign specification

The `calc_e.py` application has three "parameters", which happen to be passed
to the program as positional arguments. In the spec file, we give a user
friendly unique name to the application code and specify the path to it's
executable. More complex applications may consist of multiple codes which
communicate with one another, which is why `codes` in the spec is a list.
The sweeps section describes what "runs" should be generated - what
combinations of parameters should be passed to the program in each of many
test runs.

friendly names to these arguments
[campaign\_calc\_e.py](campaign_calc_e.py)

## Generating the campaign directory

First we will test running the campaign on a local machine (using the
`-m local` option:

```
cheetah.py create-campaign -a . -o campaign -e campaign_calc_e.py -m local
```

This creates a directory `campaign/$USER`. The reason for the `$USER`
subdirectory is to facilitate multiple HPC users running a campaign without
interferring with one another, allowing them to combine results and make
better use of the available resources (since individual users often have a
job limit). Each sweep group (representing a scheduler job when running on
HPC resources) also gets a subdirectory - in this case we have only one.
Within the sweep group directory, there are many run directories. You can examine what parameters are used for each run by looking in `codar.run-params.*`. The JSON version uses the names specified in the spec, and the txt file shows the
command that will be executed.

## Run the campaign

This will run all sweep groups in the campaign. On a local machine, this
will just launch them in the background and execute each run serially.
```
campaign/$USER/run-all.sh
```

## Monitor progress

Show a summary of counts of runs in each state and return codes for each
run component within each run:
```
cheetah.py status campaign -s
```
Note that the status command only works once the job has started and the
initial status file is generated.

Detailed results, including per-run status, per-run component return codes,
and parameters used for each run component within each run:
```
cheetah.py status campaign -t -p
```

For more options, see `cheetah.py status -h`.

## Post processing

After the job is complete, the next step is to analyze the results. What type
of analysis needs to be done will vary a lot from application to application.
In this example, to figure out how well each method did, we would want to
parse out the stdout of each run (in
`campaign/bda/all-methods-small/run-*/codar.workflow.stdout.calc_e`, and
correlate with the parameters used for that run (in
`campaign/bda/all-methods-small/run-0.0/codar.cheetah.run-params.json`). This
could be dupped to a CSV and plotted in various ways.

In the future, Cheetah will support more tools to help solve common post
processing tasks. There is a hook to run a script on every run directory -
see `examples/PiExperiment.py` and `examples/pi-post-run-compare-digits.py`.
