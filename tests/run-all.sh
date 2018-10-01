#!/bin/bash

set -e

cd $(dirname $0)

nosetests -v nose
nosetests --with-doctest -v ../codar

./test-examples.sh

# Ideally this should be run outside any other virtualenv, but this is
# better than nothing and without including it in run-all it may be
# forgotten.
./test-setup-py.sh
