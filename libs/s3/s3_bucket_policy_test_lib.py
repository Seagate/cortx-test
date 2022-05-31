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
#
"""Python library contains methods for bucket policy."""

import logging
from botocore.exceptions import ClientError
from commons import errorcodes as err
from commons.utils.s3_utils import poll
from commons.exceptions import CTException
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_bucket_policy import BucketPolicy

LOGGER = logging.getLogger(__name__)


class S3BucketPolicyTestLib(BucketPolicy):
    """Class initialising s3 connection and including methods for bucket policy operations."""

    def __init__(
            self,
            access_key: str = ACCESS_KEY,
            secret_key: str = SECRET_KEY,
            endpoint_url: str = S3_CFG["s3_url"],
            s3_cert_path: str = S3_CFG["s3_cert_path"],
            **kwargs) -> None:
        """
        Method to initializes members of S3BucketPolicyTestLib and its parent class.

        :param access_key: access key
        :param secret_key: secret key
        :param endpoint_url: endpoint url
        :param s3_cert_path: s3 certificate path
        :param region: region
        :param aws_session_token: aws_session_token
        :param debug: debug mode
        """
        kwargs["region"] = kwargs.get("region", S3_CFG["region"])
        kwargs["aws_session_token"] = kwargs.get("aws_session_token", None)
        kwargs["debug"] = kwargs.get("debug", S3_CFG["debug"])
        self.sync_delay = S3_CFG["sync_delay"]
        super().__init__(
            access_key,
            secret_key,
            endpoint_url,
            s3_cert_path,
            **kwargs)

    def get_bucket_policy(self, bucket_name: str = None) -> tuple:
        """
        Retrieve policy of the specified s3 bucket.

        :param bucket_name: Name of s3 bucket
        :return: Returns the policy of a specified s3 bucket
        and Success if successful, None and error message if failed
        """
        try:
            LOGGER.info("getting bucket policy for the bucket")
            response = poll(super().get_bucket_policy, bucket_name, timeout=self.sync_delay)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in  %s: %s",
                         S3BucketPolicyTestLib.get_bucket_policy.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def put_bucket_policy(
            self,
            bucket_name: str = None,
            bucket_policy: str = None) -> tuple:
        """
        Apply s3 bucket policy to specified s3 bucket.

        :param bucket_name: Name of s3 bucket
        :param bucket_policy: Bucket policy
        :return: Returns status and status message
        """
        try:
            LOGGER.info("Applying bucket policy to specified bucket")
            response = super().put_bucket_policy(bucket_name, bucket_policy)
            LOGGER.info(response)
        except (ClientError, Exception) as error:
            LOGGER.error("Error in  %s: %s",
                         S3BucketPolicyTestLib.put_bucket_policy.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response

    def delete_bucket_policy(self, bucket_name: str = None) -> tuple:
        """
        Function will delete the policy applied to the specified S3 bucket.

        :param bucket_name: Name of s3 bucket
        :return: Returns status and response of delete bucket policy operation.
        """
        try:
            LOGGER.info("Deletes any policy applied to the bucket")
            response = poll(super().delete_bucket_policy, bucket_name, timeout=self.sync_delay)
            LOGGER.info(response["BucketName"])
        except (ClientError, Exception) as error:
            LOGGER.error("Error in  %s: %s",
                         S3BucketPolicyTestLib.delete_bucket_policy.__name__,
                         error)
            raise CTException(err.S3_CLIENT_ERROR, error.args[0]) from error

        return True, response["BucketName"]
