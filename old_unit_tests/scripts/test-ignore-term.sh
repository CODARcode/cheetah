#!/bin/bash

trap 'echo ignoring TERM' TERM

echo 'start' $(date +%s)
echo Sleeping forever...
while true; do
    sleep 10 &
    wait
done
echo 'end  ' $(date +%s)
