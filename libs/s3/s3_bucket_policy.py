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
#

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
