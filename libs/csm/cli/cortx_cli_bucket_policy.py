# !/usr/bin/python
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
This library contains methods for S3 Bucket Policy operations using CORTX CLI
"""

import os
import time
import json
import logging
from commons import commands
from commons.helpers.node_helper import Node
from config import CMN_CFG
from libs.csm.cli.cortx_cli import CortxCli

LOGGER = logging.getLogger(__name__)


class CortxCliS3BktPolicyOperations(CortxCli):
    """
    This class has all s3 bucket policy operations
    """

    def __init__(self, session_obj: object = None):
        """
        This method initializes members of CortxCliS3BktPolicyOperations
        :param object session_obj: session object of host connection if already established
        """
        super().__init__(session_obj=session_obj)

    def create_bucket_policy(
            self,
            bucket_name: str = None,
            policy_id: str = None,
            file_path: str = None) -> tuple:
        """
        This function will create policy on a bucket
        :param bucket_name: Name of bucket on which policy will be applied
        :param policy_id: Policy ID
        :param file_path: File path of policy
        :return: (Boolean, response)
        """
        LOGGER.info("Applying policy on a bucket %s", bucket_name)
        command = " ".join(
            [commands.CMD_CREATE_BUCKET_POLICY, bucket_name, policy_id, file_path])

        output = self.execute_cli_commands(cmd=command, patterns=["[Y/n]"])[1]
        if "[Y/n]" in output:
            output = self.execute_cli_commands(cmd="Y",
                     patterns=["Bucket Policy Updated Successfully"])[1]
            if "Bucket Policy Updated Successfully" in output:
                time.sleep(15)
                return True, output

        return False, output

    def delete_bucket_policy(
            self,
            bucket_name: str = None) -> tuple:
        """
        This function will delete policy on a bucket
        :param bucket_name: Name of the bucket for which policy will be deleted
        :return: (Boolean, response)
        """
        LOGGER.info("Applying policy on a bucket %s", bucket_name)
        command = " ".join(
            [commands.CMD_DELETE_BUCKET_POLICY, bucket_name])

        output = self.execute_cli_commands(cmd=command, patterns=["[Y/n]"])[1]
        if "[Y/n]" in output:
            output = self.execute_cli_commands(cmd="Y", patterns=["Bucket policy deleted"])[1]
            if "Bucket policy deleted" in output:
                return True, output

        return False, output

    def show_bucket_policy(
            self,
            bucket_name: str,
            output_format: str = "json") -> tuple:
        """
        This function will return the bucket policy of given bucket
        :param bucket_name: Name of the bucket
        :param output_format: Format in which output will be returned.
                                 eg. 'json'|'xml'
        :return: (Boolean, Response)
        """
        LOGGER.info("Showing policy of a bucket %s", bucket_name)
        show_bkt_policy = " ".join(
            [commands.CMD_SHOW_BUCKET_POLICY, bucket_name])
        if output_format:
            show_bkt_policy = f"{show_bkt_policy} -f {output_format}"
        output = self.execute_cli_commands(cmd=show_bkt_policy, patterns=["Statement"])[1]
        if "error" in output.lower() or "exception" in output.lower():
            return False, output

        return True, output

    @classmethod
    def create_copy_json_file(
            self,
            bkt_policy: list = None,
            local_file_path: str = None,
            remote_file_path: str = None):
        """
        Function to create json file on server nodes with specified bucket policy
        :param bkt_policy: Policy which has to be added in json file
        :param local_file_path: Local file path
        :param remote_file_path: Remote file path
        :return: None
        """
        csm = CMN_CFG.get("csm")
        nodes = CMN_CFG.get("nodes")
        node1_helper_obj = Node(
            hostname=csm["mgmt_vip"],
            username=nodes[0]["username"],
            password=nodes[0]["password"])
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        with open(local_file_path, "w") as data:
            json.dump(bkt_policy, data, indent=4)
        node1_helper_obj.copy_file_to_remote(
            local_file_path, remote_file_path)
        time.sleep(2)
