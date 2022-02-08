#!/bin/bash
TGT_NAME=$1
WORK_SPACE=$2
echo "Target node entry name: $TGT_NAME"
echo -e "Workspace: $WORK_SPACE"
echo -e "\n\n---------------------------------------[ Pytest running aws_configure ]--------------------------------------\n\n"
pytest scripts/jenkins_job/aws_configure.py::test_create_acc_aws_conf --local True --target ${TGT_NAME}
echo -e "\n\n---------------------------------------[ Pytest running prov_sanity ]--------------------------------------\n\n"
cd $WORK_SPACE && pytest -m "prov_sanity" --local True --target ${TGT_NAME} comptests/prov --validate_certs False --junitxml "log/latest/results.xml" --html "log/latest/results.html"

