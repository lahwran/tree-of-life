#!/bin/bash
dir=$(dirname $0)

if [ "$1" == "--pypy-only" ]; then
    shift
    res="0"
else
    . $dir/../bin/activate
    time `which py.test` --cov-config .coveragerc --cov-report html --cov todo_tracker --weakref "$@"
    res=$?
    deactivate
fi

if [ "$res" = "0" ]
then
    . $dir/../pypy*venv/bin/activate
    time `which py.test` "$@"
    deactivate
fi
