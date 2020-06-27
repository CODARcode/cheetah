import pandas as pd
import sys

csv_file = sys.argv[1]

pf = pd.read_csv(csv_file)
pf_failed = pf[pf['exit_status'] != 'succeeded']
pf_succeeded = pf[pf['exit_status'] == 'succeeded']

print(f"According to cheetah generate-report: {len(pf_succeeded)} jobs succeeded, {len(pf_failed)} jobs failed")
 
if(len(pf_failed)>0):
    print("The following jobs failed:")
    print(pf_failed)
