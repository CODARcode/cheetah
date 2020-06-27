cheetah generate-report -o summit.csv summit
echo "+++++++++++++ Test 1 +++++++++++++++"
python tests/sf.py summit.csv
echo "+++++++++++++ Test 2 +++++++++++++++"
python tests/compare_results_with_reference.py summit
echo "+++++++++++++ Test 3 +++++++++++++++"
python tests/non_empty_stderr.py summit

