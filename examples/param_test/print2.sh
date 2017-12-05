#!/bin/bash

echo PRINT2

echo NARGS=$#

for i in $(seq 1 $#); do
    echo $i:$1
    shift
done
