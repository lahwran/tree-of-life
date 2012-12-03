#!/bin/bash

dir=$(dirname $0)
. $dir/../bin/activate
time `which py.test` --cov-config .coveragerc --cov-report html --cov todo_tracker "$@"
res=$?
deactivate

if [ "$res" = "0" ]
then
    . $dir/../pypy_venv/bin/activate
    time `which py.test` "$@"
    deactivate
fi
