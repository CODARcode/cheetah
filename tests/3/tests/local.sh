cheetah generate-report -o local.csv local
echo "+++++++++++++ Test 1 +++++++++++++++"
python tests/sf.py local.csv
echo "+++++++++++++ Test 2 +++++++++++++++"
python tests/compare_results_with_reference.py local
echo "+++++++++++++ Test 3 +++++++++++++++"
python tests/non_empty_stderr.py local
