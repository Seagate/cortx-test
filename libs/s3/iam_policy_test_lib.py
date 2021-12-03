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
"""Python library using boto3 module to perform AWS Identity & Access Management (IAM) policies."""

import logging

from config.s3 import S3_CFG
from commons import errorcodes as err
from commons.exceptions import CTException
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.iam_core_lib import IamPolicy
from botocore.exceptions import ClientError

LOGGER = logging.getLogger(__name__)


class IamPolicyTestLib(IamPolicy):
    """Class initialising s3 connection and including functions for iam policy operations."""

    def __init__(
            self,
            access_key: str = ACCESS_KEY,
            secret_key: str = SECRET_KEY,
            endpoint_url: str = S3_CFG["s3_url"],
            s3_cert_path: str = S3_CFG["s3_cert_path"],
            **kwargs) -> None:
        """
        Method to initializes members of IamPolicyTestLib and its parent class.

        :param access_key: access key
        :param secret_key: secret key
        :param endpoint_url: endpoint url
        :param s3_cert_path: s3 certificate path
        """
        super().__init__(
            access_key,
            secret_key,
            endpoint_url,
            s3_cert_path,
            **kwargs)

    def create_policy(self, policy_name: str = None, policy_document: str = None) -> tuple:
        """
        Creates a policy as per policy document.

        :param policy_name: The name of the policy to create.
        :param policy_document: The document of the policy.
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": actions,
                    "Resource": resource_arn
                }
            ]
        }
        :return: The newly created policy.
        """
        try:

            policy = super().create_policy(policy_name, policy_document)
            LOGGER.info("Created policy %s.", policy.arn)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.create_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, policy

    def delete_policy(self, policy_arn: str = None) -> tuple:
        """
        Deletes a policy.

        :param policy_arn: The ARN of the policy to delete.
        """
        try:
            response = super().delete_policy(policy_arn)
            LOGGER.info("Deleted policy %s.", policy_arn)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.create_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response
