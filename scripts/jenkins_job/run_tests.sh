#!/bin/bash
TGT_NAME=$1
echo "Target node entry name: $TGT_NAME"

pytest scripts/jenkins_job/aws_configure.py::test_create_acc_aws_conf --local True --target ${TGT_NAME}
pytest -m "release_regression" --local True --target ${TGT_NAME} --junitxml "log/latest/results.xml" --html "log/latest/results.html"
