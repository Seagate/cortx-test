#!/bin/sh
SERVER_IP=$(grep -v "^#" /etc/hosts | tail -1 | cut -d " " -f 1)
if [[ ! -x /usr/bin/sshpass ]]; then
    yum install -y sshpass
fi
sshpass -p "seagate" scp -r root@$SERVER_IP:/root/.aws /root/