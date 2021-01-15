#!/bin/bash
declare -A MaxSize=( ["hare/consul-watch-service.log"]=100 \
["hare/consul-elect-rc-leader.log"]=100 \    
["hare/consul-proto-rc.log"]=100 \
["hare/consul-watch-handler.log"]=100 \
["hare"]=400 \
["elasticsearch/elasticsearch_cluster.log"]=20 \
["elasticsearch/elasticsearch_cluster_index_search_slowlog.log"]=-1 \
["elasticsearch/elasticsearch_cluster_index_indexing_slowlog.log"]=-1 \
["seagate/csm/csm_agent.log"]=50 \
["seagate/csm/csm_cli.log"]=100 \
["seagate/csm/csm_middleware.log"]=100 \
["seagate/cortx/ha/cortxha.log"]=300 \
["seagate/cortx/ha/resource_agent.log"]=300 \
["seagate/cortx/ha/ha_setup.log"]=300 \
["seagate/cortx/ha"]=300 \
["/var/mero"]=650 \
["/var/motr"]=4325 \
["seagate/provisioner"]=600 \
["seagate/s3/audit/audit.log"]=100 \
["seagate/s3"]=16896 \
["haproxy"]=200 \
["seagate/auth/server/app.log"]=20 \
["slapd.log"]=100 \
["rabbitmq"]=140 \
["cortx/sspl"]=200 \
)

ret=$(./bundle_checker.sh 2>&1; echo $BASHPID)
wait
rm -f bundle_checker_temp
echo "$ret" > bundle_checker_temp
while IFS=$'\n' read -r i
do 
   for j in "${!MaxSize[@]}";
   do
   	   if [[ "$i" =~ "$j" ]]; then
	       
	       sz=$(echo $i | cut -d' ' -f2)
	       if [ $sz -gt ${MaxSize[$j]} ]; then 
                  echo "Size violation by $i";
               else
                  echo "Size of $i within max limit"
               fi
	   	   
	   fi
   done 
done < bundle_checker_temp

exit 0
