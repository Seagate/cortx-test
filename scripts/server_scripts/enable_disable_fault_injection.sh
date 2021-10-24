#!/usr/bin/env bash

[ -z "$NODES" ] && { echo "Provide NODES"; exit 1; }
[ -z "$FIS" ] && { echo "Provide FIS"; exit 1; }
[ -z "$1" ] && { echo "Operation missed"; exit 1; }
inst_num=${NINST:-"45"}
start_port=28081
end_port=$(( $start_port + $inst_num - 1 ))
for f in $(echo $FIS | tr "," " ")
do
    sgtfi="x-seagate-faultinjection: $1,always,$f,0,0"
    for port in $(seq $start_port $end_port | tr "\n" " ")
    do
        pdsh -S -w  $NODES "curl -X PUT -H \"$sgtfi\" localhost:$port"
    done
done
