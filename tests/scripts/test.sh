#!/bin/bash

echo ENV $(env)

echo PWD $(pwd)

echo NARGS=$#

for i in $(seq 1 $#); do
    echo $i:$1
    shift
done

echo 'start' $(date +%s)
sleep $(( RANDOM % 10 ))
echo 'end  ' $(date +%s)
