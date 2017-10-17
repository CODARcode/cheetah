#!/bin/bash

cd $(dirname $0)

nosetests -v tests/nose
nosetests --with-doctest -v codar

tests/test-examples.sh

