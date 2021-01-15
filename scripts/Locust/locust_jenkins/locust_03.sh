#!/bin/sh
python3.6 -m venv venv
source venv/bin/activate
pip3.6 install -r requirements.txt
bash Locust/locust_jenkins/get_aws_creds.sh
TIMESTAMP=$(date +%F_%H:%M:%S | sed 's/\(:[0-9][0-9]\)[0-9]*$/\1/')
LOCUST_DIR="/root/locust_logs/locust_03_$TIMESTAMP"
mkdir -p $LOCUST_DIR
FILE_NAME="$LOCUST_DIR/locust_03_report.log"
venv/bin/python3.6 Locust/run_locust.py Locust/locust_03.py --t 40m --u 10 --l $FILE_NAME
cat $FILE_NAME
