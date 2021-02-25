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
This library contains methods for S3 Bucket operations using CORTX CLI
"""

import logging
from commons import commands
from libs.csm.cli.cortx_cli import CortxCli

LOGGER = logging.getLogger(__name__)


class CortxCliS3BucketOperations(CortxCli):
    """
    This class has all s3 bucket operations
    """

    def __init__(self, session_obj: object = None):
        """
        This method initializes members of CortxCliS3BucketOperations
        :param object session_obj: session object of host connection if already established
        """
        super().__init__(session_obj=session_obj)

    def create_bucket_cortx_cli(
            self,
            bucket_name: str) -> tuple:
        """
        This function will create a bucket using CORTX CLI
        :param bucket_name: New bucket's name
        :return: True/False and response returned by CORTX CLI
        """
        create_bucket_cmd = commands.CMD_CREATE_BUCKET.format(bucket_name)
        LOGGER.info("Creating bucket with name %s", bucket_name)
        response = self.execute_cli_commands(cmd=create_bucket_cmd)[1]
        LOGGER.info("Response returned: \n%s", response)
        if "Bucket created" in response:
            return True, response

        return False, response

    def list_buckets_cortx_cli(self, op_format: str = None) -> tuple:
        """
        This function will list s3buckets using CORTX CLI
        :param op_format: Format for bucket list (optional) (default value: table)
                       (possible values: table/xml/json)
        :return: response returned by CORTX CLI
        """
        show_bkts_cmd = commands.CMD_SHOW_BUCKETS
        if op_format:
            show_bkts_cmd = "{} -f {}".format(show_bkts_cmd, op_format)
        LOGGER.info("Listing buckets with cmd: %s", show_bkts_cmd)
        response = self.execute_cli_commands(cmd=show_bkts_cmd)
        LOGGER.info("Response returned: \n%s", response)

        return response

    def delete_bucket_cortx_cli(
            self,
            bucket_name: str) -> tuple:
        """
        This function will delete given bucket using CORTX CLI
        :param bucket_name: name of the bucket to be deleted
        :return: True/False and response returned by CORTX CLI
        """
        delete_bucket_cmd = commands.CMD_DELETE_BUCKET.format(bucket_name)
        LOGGER.info("Deleting bucket %s", bucket_name)
        response = self.execute_cli_commands(cmd=delete_bucket_cmd)[1]
        LOGGER.info("Response returned: \n%s", response)
        if "Bucket deleted" in response:
            return True, response

        return False, response
