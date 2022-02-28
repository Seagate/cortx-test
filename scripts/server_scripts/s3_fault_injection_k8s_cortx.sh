#!/usr/bin/bash
echo "---------------------------------------------------------"
echo "Fault injection Control Script"
fi_inject=$1
echo "Fault injection: $fi_inject"

cortx_data_pod_array=()
IFS=$'\n' read -r -d '' -a cortx_data_pod_array < <(kubectl get pods | grep cortx-data-pod | awk '{print $1}')
for i in ${cortx_data_pod_array[@]}
do
  s3_containers=()
  IFS=$'\n' read -r -d '' -a s3_containers < <(kubectl get pods $i -o jsonpath='{.spec.containers[*].name}' | grep -o cortx-s3-[0-9]*[0-9])
  for j in ${s3_containers[@]}; do
    echo "---------------------------------------------------------"
    echo "POD: $i"
    echo "CONTAINER: $j"
    echo "$fi_inject fault injection parameter"
    if [ "$fi_inject" == "enable" ]; then
        echo "Enable"
        kubectl exec -it $i -c $j -- sed -i s/s3server\ \-\-s3pidfile/s3server\ \-\-fault_injection\ true\ \-\-s3pidfile/g /opt/seagate/cortx/s3/s3startsystem.sh
    else
        echo "Disable"
        kubectl exec -it $i -c $j -- sed -i s/s3server\ \-\-fault_injection\ true\ \-\-s3pidfile/s3server\ \-\-s3pidfile/g /opt/seagate/cortx/s3/s3startsystem.sh
    fi
    echo "Killing stale s3 process"
    kubectl exec -it $i -c $j -- pkill -9 s3server
  done
done
echo "---------------------------------------------------------"
echo -n "Waiting for new s3 processes to start"
for i in ${cortx_data_pod_array[@]}
do
  s3_containers=()
  IFS=$'\n' read -r -d '' -a s3_containers < <(kubectl get pods $i -o jsonpath='{.spec.containers[*].name}' | grep -o cortx-s3-[0-9]*[0-9])
  for j in ${s3_containers[@]}; do
    for k in $(seq 1 30)
    do
      echo -n "."
      if [ ! -z $(kubectl exec -it $i -c $j -- pgrep s3server 2> /dev/null) ]; then break;fi
    done
  done
done
echo -e "\nS3server started with required option!!!"
