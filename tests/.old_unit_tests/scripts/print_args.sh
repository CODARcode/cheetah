#!/bin/bash

echo NARGS=$#

for i in $(seq 1 $#); do
    echo $i:$1
    shift
done
