# !/usr/bin/python
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
This library contains methods for S3 Bucket Policy operations using CORTX CLI
"""

import logging
from commons import commands
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

        output = self.execute_cli_commands(cmd=command)[1]
        if "[Y/n]" in output:
            output = self.execute_cli_commands(cmd="Y")[1]
            if "Bucket Policy Updated Successfully" in output:
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

        output = self.execute_cli_commands(cmd=command)[1]
        if "[Y/n]" in output:
            output = self.execute_cli_commands(cmd="Y")[1]
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
            show_bkt_policy = "{} -f {}".format(
                show_bkt_policy, output_format)
        output = self.execute_cli_commands(cmd=show_bkt_policy)[1]
        if "error" in output.lower() or "exception" in output.lower():
            return False, output

        return True, output
