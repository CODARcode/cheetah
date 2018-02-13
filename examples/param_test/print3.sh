#!/bin/bash

echo NARGS=$#

for i in $(seq 1 $#); do
    echo $i:$1
    shift
done

echo "print3.xml"
cat print3.xml
