## Cheetah MPMD lite

`cheetah-mpmd` provides a less-featured, lite way to run MPMD applications using jsrun/srun/mpirun.

### How to run
Get an allocation, and run
[Summit]
`cheetah-mpmd jsrun -n1 -a4 -c4 --cheetah-app ./gray-scott settings-files.json : -n1 -a1 -c1 --cheetah-app ./pdf-calc gs.bp pdf.bp`

[Andes and other Slurm clusters]
`cheetah-mpmd srun -n4 -N1 --cheetah-app ./gray-scott settings-files.json : -n1 --cheetah-app ./pdf-calc gs.bp pdf.bp`

[local machines]
`cheetah-mpmd mpirun -np 4 --cheetah-app ./gray-scott settings-files.json : -np 1 --cheetah-app ./pdf-calc gs.bp pdf.bp`

You must mark your application executable using the `--cheetah-app` argument.

By default, the logging level is set to INFO. You can set the `LOG_LEVEL` environment variable to `DEBUG` for more information.

### Underlying Implementation
#### Summit
For Summit, runs each application on a separate node.
1. `cheetah-mpmd` extracts the jsrun arguments from each app and creates an intermediate erf file.
2. It reads the erf output files and creates an erf file for the MPMD run. The intermediate erf files are removed.
3. It submits the erf file for the mpmd run using `jsrun --erf_input=erf_file_name`.

#### Andes and other Slurm clusters
1. `cheetah-mpmd` extracts the slurm arguments and creates a configuration file that ends in .conf .
2. It submits the conf file using `srun --multi-prog conf_file`.

#### Local machines that use mpirun
`cheetah-mpmd` does not do anything special here. It is just to have a consistent interface.
The command is parsed and submitted as a regular mpirun mpmd command of the form 
`mpirun -np 2 ./app : -np 2 ./app2`

