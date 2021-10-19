#!/usr/bin/env bash

[ -z "$NODES" ] && { echo "Provide NODES"; exit 1; }
s3cmdup=${S3STARTUP:-"/opt/seagate/cortx/s3/s3startsystem.sh"}
if [ "$1" = "enable" ]; then
    echo "Enabling"
    pdsh -S -w $NODES "sed -i \"s/s3server[[:space:]]*--/s3server --fault_injection true --/g\" $s3cmdup"
    echo "Done"
fi
if [ "$1" = "disable" ]; then
    echo "Disabling"
    pdsh -S -w $NODES "sed -i \"s/[[:space:]]*--fault_injection true//g\" $s3cmdup"
    echo "Done"
fi
