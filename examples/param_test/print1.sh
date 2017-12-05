#!/bin/bash

echo PRINT1
echo NARGS=$#

for i in $(seq 1 $#); do
    echo $i:$1
    shift
done

echo "print1.conf:"
cat print1.conf
