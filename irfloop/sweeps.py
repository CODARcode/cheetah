from codar.cheetah import parameters as p
from node_layouts import my_summit_layout
def test_sweep(depvarname, input_file_train):
	input_file_test = input_file_train.replace("train","test")

	test_out_prefix = input_file_train.split("/")[-1].split("_train_")[0]


	sweep_parameters = [

		p.ParamRunner('train', 'nprocs', [1]),

		p.ParamCmdLineOption('train', 'input_file', '--file', [input_file_train]),
		p.ParamCmdLineOption('train', 'treetype', '--treetype', [3]),
		p.ParamCmdLineOption('train', 'mtrytype', '--mtryType', [1]),
		p.ParamCmdLineOption('train', 'depvarname', '--depvarname', [depvarname]),
		p.ParamCmdLineOption('train', 'ntree', '--ntree', [1000]),
		p.ParamCmdLineOption('train', 'numIterations', '--numIterations', [5]),
		p.ParamCmdLineOption('train', 'targetpartitionsize', '--targetpartitionsize', [5]),
		p.ParamCmdLineOption('train', 'write-enabled', '--write', [None]),
		p.ParamCmdLineOption ('train', 'impmeasure', '--impmeasure', [1]),
		p.ParamCmdLineOption ('train', 'nthreads', '--nthreads', [160]),
		p.ParamCmdLineOption ('train', 'usempi', '--useMPI', [1]),
		p.ParamCmdLineOption ('train', 'outprefix', '--outprefix', ['methLOOP_{}'.format(depvarname)]),
		p.ParamCmdLineOption ('train', 'printpathfile', '--printPathfile', [0]),
		p.ParamCmdLineOption ('train', 'outputdirectory', '--outputDirectory', ["./"]),


		p.ParamRunner('test', 'nprocs', [1]),

		p.ParamCmdLineOption('test', 'input_file', '--file', [input_file_test]),
		p.ParamCmdLineOption('test', 'predict', '--predict', ['methLOOP_{}.forest'.format(depvarname)]),
		p.ParamCmdLineOption('test', 'treetype', '--treetype', [3]),
		p.ParamCmdLineOption('test', 'depvarname', '--depvarname', [depvarname]),
		p.ParamCmdLineOption('test', 'impmeasure', '--impmeasure', [1]),
		p.ParamCmdLineOption('test', 'nthreads', '--nthreads', [160]),
		p.ParamCmdLineOption('test', 'usempi', '--useMPI', [0]),
		p.ParamCmdLineOption('test', 'outprefix', '--outprefix', ['methLOOP_{}_test'.format(test_out_prefix)]),
		p.ParamCmdLineOption('test', 'outputdirectory', '--outputDirectory', ["./"]),

	]

	sweep = p.Sweep ( parameters = sweep_parameters, node_layout = {'summit': my_summit_layout()},
			rc_dependency = {'test':'train'} )


	return sweep
