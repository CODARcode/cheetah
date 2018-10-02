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

if [ $(( RANDOM % 2 )) = 1 ]; then
    echo 'end failure  ' $(date +%s)
    exit 1
else
    echo 'end  ' $(date +%s)
fi
