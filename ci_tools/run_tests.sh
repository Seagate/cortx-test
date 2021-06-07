#!/bin/sh

source virenv/bin/activate
export PYTHONPATH=$WORKSPACE:$PYTHONPATH

if [ -z "${Clone_TEs_To_Exclude}" ] 
  then  
  	python3 -u tools/clone_test_plan/clone_test_plan.py -tp=${TestPlanNumber} -b=${Build} -br=${Build_Branch} -s=${Setup_Type}  -p=${Platform_Type} -n=${Nodes_In_Target} -sr=${Server_Type} -e=${Enclosure_Type} -c='TEST-19657'
  else
 	python3 -u tools/clone_test_plan/clone_test_plan.py -tp=${TestPlanNumber} -b=${Build} -br=${Build_Branch} -s=${Setup_Type}  -p=${Platform_Type} -n=${Nodes_In_Target} -sr=${Server_Type} -e=${Enclosure_Type} -c='TEST-19657' -st ${TEs_To_Exclude}
  fi

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