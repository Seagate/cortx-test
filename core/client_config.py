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
Utility Class for health status check and update to database
"""


import logging
import subprocess
import json
from urllib.parse import quote_plus
from pymongo import MongoClient
from commons.params import DB_HOSTNAME
from commons.params import DB_NAME
from commons.params import SYS_INFO_COLLECTION

LOGGER = logging.getLogger(__name__)


class ClientConfig:

    """
    Configure client for given target
    """

    def __init__(self, credentials):
        self.db_user, self.db_password = credentials

    def get_setup_details(self, target):
        """
            Fetch target details from database
            :return: setup_details
        """
        mongodburi = "mongodb://{0}:{1}@{2}"
        uri = mongodburi.format(quote_plus(self.db_user), quote_plus(self.db_password), DB_HOSTNAME)
        client = MongoClient(uri)
        setup_db = client[DB_NAME]
        collection_obj = setup_db[SYS_INFO_COLLECTION]
        setup_query = {"setupname": target}
        entry_exist = collection_obj.find(setup_query).count()
        setup_details = collection_obj.find_one(setup_query)
        return setup_details

    @staticmethod
    def run_cmd(cmd):
        """
        Execute bash commands on the host
        :param str cmd: command to be executed
        :return: command output
        :rtype: string
        """
        print("Executing command: {}".format(cmd))
        proc = subprocess.Popen(cmd, shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        result = str(proc.communicate())
        return result

    def set_s3_endpoints(self, public_data_ip):
        """
        Set s3 endpoints to cluster ip in /etc/hosts
        :param str public_data_ip: IP of the cluster
        :return: None
        """
        # Removing contents of /etc/hosts file and writing new contents
        self.run_cmd(cmd="rm -f /etc/hosts")
        with open("/etc/hosts", 'w') as file:
            file.write("127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4\n")
            file.write("::1         localhost localhost.localdomain localhost6 localhost6.localdomain6\n")
            file.write("{} s3.seagate.com sts.seagate.com iam.seagate.com sts.cloud.seagate.com\n"
                       .format(public_data_ip))

    def configure_s3_tools(self, target):
        """
        use makefile to configure s3 tools
        accept a target, pick access mey and secret key from file
        run make cmd
        """
        file = open("/root/{}_s3acc_secrets.json".format(target))
        data = json.load(file)
        access = data['AWS_ACCESS_KEY_ID']
        secret = data['AWS_SECRET_ACCESS_ID']
        self.run_cmd(cmd="make configure-tools --makefile=scripts/s3_tools/Makefile ACCESS={} SECRET={}".format(access, secret))
        file.close()

    def client_configure_for_given_target(self, acquired_target):
        """
        accept a acquired_target
        configure client according to acquired_target
        """
        target = self.get_setup_details(acquired_target)
        data_ip = target["lb"]
        if data_ip == "":
            nodes = target["nodes"]
            node = nodes[0]
            data_ip = node["public_data_ip"]
        self.set_s3_endpoints(data_ip)
        self.configure_s3_tools(acquired_target)
