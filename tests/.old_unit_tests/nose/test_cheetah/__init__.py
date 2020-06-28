import os.path

module_path = os.path.realpath(os.path.dirname(__file__))
source_path = os.path.realpath(os.path.join(module_path, '..', '..', '..'))

TEST_OUTPUT_DIR = os.path.join(source_path, 'test_output', 'nose',
                               'test_cheetah')
