#!/usr/bin/env python

import h5py
import csv
import subprocess

f = h5py.File('CompressionOutput.h5', 'r')

dataset_name = []
f.visit(dataset_name.append)
features = filter(lambda x: x.find("_features/") >= 0, dataset_name)

for feature in features:
    print(feature)
    dir = f'FEATURES/{feature}'
    com = f"mkdir -p {dir}"
    subprocess.getstatusoutput(com)
    d = f.get(feature)
    ff = open(f'{dir}/d.csv', 'w')
    writer = csv.writer(ff)
    writer.writerows(d)
    ff.close()

f.close()




