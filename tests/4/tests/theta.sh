cheetah generate-report -o theta.csv theta
echo "+++++++++++++ Test 1 +++++++++++++++"
python tests/sf.py theta.csv
echo "+++++++++++++ Test 2 +++++++++++++++"
python tests/compare_results_with_reference.py theta
echo "+++++++++++++ Test 3 +++++++++++++++"
python tests/non_empty_stderr.py theta

