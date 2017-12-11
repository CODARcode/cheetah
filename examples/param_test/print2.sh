#!/bin/bash

echo PRINT2

echo NARGS=$#

for i in $(seq 1 $#); do
    echo $i:$1
    shift
done

echo "print2.ini:"
cat print2.ini
