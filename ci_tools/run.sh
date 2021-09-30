#!/bin/sh

make all --makefile=scripts/s3_tools/Makefile ACCESS="$AWS_ACCESS_KEY_ID" SECRET="$AWS_SECRET_ACCESS_KEY"

export CORTX_TEST_ROOT=/cortx-test
export LIB=/usr/lib/python3.7
export SITE_PKGS=/usr/lib/python3.7/site-packages
export PYTHONPATH=$LIB:$SITE_PKGS:$CORTX_TEST_ROOT

"$PYTHON_VAR" ci_tools/aws_configure.py --access_key="$AWS_ACCESS_KEY_ID" --secret_key="$AWS_SECRET_ACCESS_KEY"

if [ "$SKIP_TE" != "None" ];
then
  cmd="$PYTHON_VAR -u tools/clone_test_plan/clone_test_plan.py -tp=$TEST_PLAN_NUMBER -b=$BUILD -s=$SETUP_TYPE -c=$COMMENT_JIRA -br=$BRANCH -n=$NODES -p=$PLATFORM -sr=$SERVER_TYPE -e=$ENCLOSURE_TYPE -st $SKIP_TE"
else
  cmd="$PYTHON_VAR -u tools/clone_test_plan/clone_test_plan.py -tp=$TEST_PLAN_NUMBER -b=$BUILD -s=$SETUP_TYPE -c=$COMMENT_JIRA -br=$BRANCH -n=$NODES -p=$PLATFORM -sr=$SERVER_TYPE -e=$ENCLOSURE_TYPE"
fi

$cmd

INPUT=cloned_tp_info.csv
OLDIFS=$IFS
IFS=','
[ ! -f $INPUT ] && { echo "$INPUT file not found"; exit 99; }
while read tp_id te_id old_te
do
    echo "tp_id : $tp_id"
    echo "te_id : $te_id"
    echo "old_te : $old_te"
    test_exe=$(echo $te_id | sed -e 's/\r//g')
    "$PYTHON_VAR" -u testrunner.py -te="$test_exe" -tp="$tp_id" -tg="$TARGET_NODE" -b="$BUILD" -t="$BUILD_TYPE" -d="$DB_UPDATE" --force_serial_run="$SEQUENTIAL_EXECUTION"
done < $INPUT
IFS=$OLDIFS


