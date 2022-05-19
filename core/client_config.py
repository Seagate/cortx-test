# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
"""
Utility Class for health status check and update to database
"""

import json
import logging
import subprocess
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
        line1 = "127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4\n"
        line2 = "::1         localhost localhost.localdomain localhost6 localhost6.localdomain6\n"
        line3 = "{} s3.seagate.com sts.seagate.com iam.seagate.com " \
                "sts.cloud.seagate.com\n".format(public_data_ip)
        lines = [line1, line2, line3]

        self.run_cmd(cmd="rm -f /etc/hosts")
        with open("/etc/hosts", 'w') as file:
            file.writelines(lines)

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
        cmd = "make configure-tools --makefile=scripts/s3_tools/Makefile ACCESS={} SECRET={}"
        self.run_cmd(cmd=cmd.format(access, secret))
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
