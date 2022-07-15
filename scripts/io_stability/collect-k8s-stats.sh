#!/bin/sh
# Script to start collecting stats of top cmd
#provide directory as argument
DIR=$1
mkdir -p "$DIR"

printf "\n\n############## Process Info. #############\n\n" >> "$DIR"/top_stats_log

while true
do
    printf "\n=====$(date +"%Y-%m-%dT%H:%M:%S")=========\n">> "$DIR"/top_stats_log
    kubectl top pods --containers --all-namespaces >> "$DIR"/top_stats_log
    printf "\n=====$(date +"%Y-%m-%dT%H:%M:%S")=========\n" >> "$DIR"/top_nodes_stats_log
    kubectl top nodes  >> "$DIR"/top_nodes_stats_log
    sleep 300 #wait for 5 mins
done

exit 0
