#!/bin/sh

make all --makefile=scripts/s3_tools/Makefile ACCESS="$AWS_ACCESS_KEY_ID" SECRET="$AWS_SECRET_ACCESS_KEY"

export CORTX_TEST_ROOT=/cortx-test
export LIB=/usr/lib/python3.7
export SITE_PKGS=/usr/lib/python3.7/site-packages
export PYTHONPATH=$LIB:$SITE_PKGS:$CORTX_TEST_ROOT

"$PYTHON_VAR" ci_tools/aws_configure.py --access_key="$AWS_ACCESS_KEY_ID" --secret_key="$AWS_SECRET_ACCESS_KEY"

"$PYTHON_VAR" -u testrunner.py -te="$TEST_EXECUTION_NUMBER" -tp="$TEST_PLAN_NUMBER" -tg="$TARGET_NODE" -b="$BUILD" -t="$BUILD_TYPE" -d="$DB_UPDATE" --force_serial_run="$SEQUENTIAL_EXECUTION" -tt $TEST_TYPES

