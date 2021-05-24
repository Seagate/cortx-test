#!/bin/sh

python3 -u tools/clone_test_plan/clone_test_plan.py -tp=$TEST_PLAN_NUMBER -b=$BUILD -bt=$BUILD_TYPE -s=$SETUP_TYPE -c='TEST-19657'

INPUT=cloned_tp_info.csv
OLDIFS=$IFS
IFS=','
[ ! -f $INPUT ] && { echo "$INPUT file not found"; exit 99; }
while read tp_id te_id
do
	echo "tp_id : $tp_id"
	echo "te_id : $te_id"
    test_exe=$(echo $te_id | sed -e 's/\r//g')
    python3 -u testrunner.py -te=$test_exe -tp=$tp_id -tg=$Target_Node -b=$BUILD -t=$BUILD_TYPE -d=${DB_Update} --force_serial_run ${Sequential_Execution}
done < $INPUT
IFS=$OLDIFS