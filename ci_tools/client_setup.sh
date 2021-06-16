#!/bin/sh
#cp /$secrets_json_path $WORKSPACE/cortx-test/secrets.json
cp /$secrets_json_path $WORKSPACE/secrets.json
#cd cortx-test
yum install -y nfs-utils
yum install -y s3cmd
yum install -y s3fs-fuse
python3.7 -m venv virenv
source virenv/bin/activate
pip install --upgrade pip
if ${Need_pip_source}; then
pip3 install -r requirements.txt -i https://pypi.python.org/simple/
else
pip3 install -r requirements.txt
fi

mkdir -p /etc/ssl/stx-s3-clients/s3
export PYTHONPATH=$WORKSPACE:$PYTHONPATH
