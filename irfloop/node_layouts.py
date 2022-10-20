from codar.savanna.machines import SummitNode


def my_summit_layout():
	train_node = SummitNode()
	for i in range(40):
		train_node.cpu[i] = "train:0"

	test_node = SummitNode()
	for i in range(40):
		test_node.cpu[i] = "test:0"



	return [train_node, test_node]


