#!/bin/sh
python3.6 -m venv venv
source venv/bin/activate
pip3.6 install -r requirements.txt
bash scripts/Locust/locust_jenkins/get_aws_creds.sh
TIMESTAMP=$(date +%F_%H:%M:%S | sed 's/\(:[0-9][0-9]\)[0-9]*$/\1/')
LOCUST_DIR="/root/locust_logs/locust_08_$TIMESTAMP"
mkdir -p $LOCUST_DIR
FILE_NAME="$LOCUST_DIR/locust_08_report.log"
venv/bin/python3.6 scripts/Locust/run_locust.py scripts/Locust/locust_08.py --t $1 --u $2 --r $3 --l $FILE_NAME
cat $FILE_NAME