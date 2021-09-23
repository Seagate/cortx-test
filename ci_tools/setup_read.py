#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
"""
Script can be used to read details from DB
Sample cmd: python setup_read.py --dbuser <username> --dbpassword <password> --target <setupname>
"""

import argparse
from urllib.parse import quote_plus
from pymongo import MongoClient

parser = argparse.ArgumentParser(description='Update the setup entry')
parser.add_argument('--dbuser',
                    help='Database user')
parser.add_argument('--dbpassword',
                    help='database password')
parser.add_argument('--target',
                    help='setupname')
args = parser.parse_args()

DB_HOSTNAME = """cftic1.pun.seagate.com:27017,
cftic2.pun.seagate.com:27017,
apollojenkins.pun.seagate.com:27017/
?authSource=cft_test_results&replicaSet=rs0"""
DB_NAME = "cft_test_results"
SYS_INFO_COLLECTION = "r2_systems"
DBUSER = args.dbuser
DBPSWD = args.dbpassword


def read_setup():
    """
    Function will create a string
    and temporary file
    """
    DOCKERCMD = ""
    setupname = args.target
    setup_query = {"setupname": setupname}
    mongodburi = "mongodb://{0}:{1}@{2}"
    uri = mongodburi.format(quote_plus(DBUSER), quote_plus(DBPSWD), DB_HOSTNAME)
    client = MongoClient(uri)
    setup_db = client[DB_NAME]
    collection_obj = setup_db[SYS_INFO_COLLECTION]
    entry_exist = collection_obj.find(setup_query).count()
    if entry_exist == 1:
        setup_details = collection_obj.find_one(setup_query)
        data_ip = setup_details["lb"]
        nodes = setup_details["nodes"]
        node = nodes[0]
        if data_ip in ('', 'FQDN without protocol(http/s)'):
            data_ip = node["public_data_ip"]
        DOCKERCMD += "--add-host=" + node['host'] + ":" + data_ip + " --add-host=s3.seagate.com:" \
                     + data_ip + " --add-host=iam.seagate.com:" + data_ip
    else:
        DOCKERCMD += "setup is not added"
    with open("docker_temp", "w") as f_file:
        print(DOCKERCMD, file=f_file)


if __name__ == '__main__':
    read_setup()
