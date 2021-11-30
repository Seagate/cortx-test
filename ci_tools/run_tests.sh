#!/bin/sh

source virenv/bin/activate
export PYTHONPATH=$WORKSPACE:$PYTHONPATH

INPUT=cloned_tp_info.csv
OLDIFS=$IFS
IFS=','
[ ! -f $INPUT ] && { echo "$INPUT file not found"; exit 99; }
while read tp_id te_id
do
	echo "tp_id : $tp_id"
	echo "te_id : $te_id"
    test_exe=$(echo $te_id | sed -e 's/\r//g')
	python3 -u testrunner.py -te=$test_exe -tp=$tp_id -tg=${Target_Node} -b=${Build} -t=${Build_Branch} -d=${DB_Update} -p=${Process_Cnt_Parallel_Exe} --force_serial_run ${Sequential_Execution}
done < $INPUT
IFS=$OLDIFS


deactivate