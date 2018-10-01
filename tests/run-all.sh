#!/bin/bash

set -e

cd $(dirname $0)

nosetests -v nose
nosetests --with-doctest -v ../codar

./test-examples.sh
