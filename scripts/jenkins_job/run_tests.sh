#!/bin/bash
TGT_NAME=`echo "$HOSTNAME" | sed  's/\..*//'`
echo "Target node entry name: $TGT_NAME"

pytest -m  release_regression --local True --target ${TGT_NAME} --junitxml log/latest/results.xml --html log/latest/results.html
