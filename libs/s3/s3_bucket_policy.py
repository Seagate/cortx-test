#!/usr/bin/python
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

"""Python Library using boto3 module to perform bucket policy Operations."""
import logging
from libs.s3.s3_core_lib import S3Lib

LOGGER = logging.getLogger(__name__)


class BucketPolicy(S3Lib):
    """Class containing methods to implement bucket policy functionality."""

    def get_bucket_policy(self, bucket_name: str = None) -> tuple:
        """
        Retrieve policy of the specified s3 bucket.

        :param bucket_name: Name of s3 bucket
        :return: Returns the policy of a specified s3 bucket
        and Success if successful, None and error message if failed.
        """
        response = self.s3_client.get_bucket_policy(Bucket=bucket_name)
        LOGGER.debug(response)

        return response

    def put_bucket_policy(
            self,
            bucket_name: str = None,
            bucket_policy: dict = None) -> dict:
        """
        Apply s3 bucket policy to specified s3 bucket.

        :param bucket_name: Name of s3 bucket
        :param bucket_policy: Bucket policy
        :return: Returns status and status message
        """
        self.s3_client.put_bucket_policy(
            Bucket=bucket_name, Policy=bucket_policy)

        return bucket_policy

    def delete_bucket_policy(self, bucket_name: str = None) -> dict:
        """
        Function will delete the policy applied to the specified S3 bucket.

        :param bucket_name: Name of s3 bucket.
        :return: Returns status and response of delete bucket policy operation.
        """
        LOGGER.debug("BucketName: %s", bucket_name)
        resp = self.s3_client.delete_bucket_policy(Bucket=bucket_name)
        LOGGER.debug("Bucket policy delete resp : %s", str(resp))
        resp["BucketName"] = bucket_name

        return resp
