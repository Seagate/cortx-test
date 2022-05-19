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
        response = self.execute_cli_commands(cmd=create_bucket_cmd, patterns=["Bucket created"])[1]
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
            show_bkts_cmd = f"{show_bkts_cmd} -f {op_format}"
        LOGGER.info("Listing buckets with cmd: %s", show_bkts_cmd)
        response = self.execute_cli_commands(cmd=show_bkts_cmd, patterns=["Bucket Name", "{", "<"])
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
        response = self.execute_cli_commands(cmd=delete_bucket_cmd, patterns=["Bucket deleted"])[1]
        LOGGER.info("Response returned: \n%s", response)
        if "Bucket deleted" in response:
            return True, response

        return False, response

    def delete_all_buckets_cortx_cli(self) -> dict:
        """
        This function deletes all buckets present under an s3 account
        :return: deleted and non-deleted buckets
        :rtype: (dict)
        """
        LOGGER.info("Listing all the buckets")
        resp_json = self.list_buckets_cortx_cli(op_format="json")
        bucket_list = self.format_str_to_dict(
            resp_json[1])["buckets"]
        response_dict = {"Deleted": [], "CouldNotDelete": []}
        for bucket in bucket_list:
            LOGGER.info("Deleting the bucket %s", bucket)
            resp = self.delete_bucket_cortx_cli(
                bucket["name"])
            if "Bucket deleted" in resp[1]:
                response_dict["Deleted"].append(bucket)
            else:
                response_dict["CouldNotDelete"].append(bucket)
        if response_dict["CouldNotDelete"]:
            LOGGER.error("Failed to delete all buckets")
            return response_dict
        return response_dict
