#!/bin/bash

dir=$(dirname $0)
. $dir/../bin/activate
first="$1"
shift
time `which py.test` --cov-config .coveragerc --cov-report html --cov todo_tracker --weakref "$@"
coverage annotate -d "$first"
deactivate
