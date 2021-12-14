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
from botocore.exceptions import ClientError

from config.s3 import S3_CFG
from commons import errorcodes as err
from commons.exceptions import CTException
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.iam_core_lib import IamPolicy


LOGGER = logging.getLogger(__name__)


class IamRoleTestLib(IamPolicy):
    """Class initialising s3 connection and including functions for iam role operations."""

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

    def create_role(self, assume_role_policy_document: str = None,
                    role_name: str = None, **kwargs) -> tuple:
        """
        create a role name and attaches a trust policy to it that is provided as a Policy Document.

        :param assume_role_policy_document: The trust relationship policy document that grants an
         entity permission to assume the role.
        :param role_name: The name of the role to create.
        # :param tags: A list of tags that you want to attach to the new role.
        """
        try:
            response = super().create_role(assume_role_policy_document, role_name, **kwargs)
            LOGGER.info("create role %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamRoleTestLib.create_role.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def delete_role(self, role_name: str = None):
        """
        Delete the specified role. The role must not have any policies attached.

        :param role_name: The name of the role to delete.
        """
        try:
            response = super().delete_role(role_name)
            LOGGER.info("delete role %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamRoleTestLib.delete_role.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def delete_role_policy(self, role_name: str = None, policy_name: str = None) -> tuple:
        """
        Delete the specified inline policy that is embedded in the specified IAM role.

        :param role_name: The name (friendly name, not ARN) identifying the role that the policy
        is embedded in.
        :param policy_name: The name of the inline policy to delete from the specified IAM role.
        """
        try:
            response = super().delete_role_policy(role_name, policy_name)
            LOGGER.info("delete policy for role %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamRoleTestLib.delete_role_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def list_role_policies(self, role_name: str = None, marker: str = None, max_items: int = 123):
        """
        List the names of the inline policies that are embedded in the specified IAM role.

        :param role_name: The name of the role to list policies for.
        :param marker: Use this parameter only when paginating results and only after you receive
         a response indicating that the results are truncated.
        :param max_items: Use this only when paginating results to indicate the maximum number of
        items you want in the response.
        """
        try:
            response = super().list_role_policies(role_name, marker, max_items)
            LOGGER.info("List role policies %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamRoleTestLib.list_role_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def list_roles(self, path_prefix: str = "/", max_items: int = 123, **kwargs) -> tuple:
        """
        List the IAM roles that have the specified path prefix.

        :param path_prefix: The path prefix for filtering the results. For example, the prefix
        /application_abc/component_xyz/ gets all roles whose path starts with
        /application_abc/component_xyz/. This parameter is optional. If it is not included,
        it defaults to a slash (/), listing all roles.
        :param max_items: Use this only when paginating results to indicate the maximum number of
        items you want in the response.
        """
        try:
            response = super().list_roles(path_prefix, max_items, **kwargs)
            LOGGER.info("List roles %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamRoleTestLib.list_roles.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def attach_role_policy(self, role_name: str = None, policy_arn: str = None) -> tuple:
        """
        Attache the specified managed policy to the specified IAM role.

        :param role_name: The name (friendly name, not ARN) of the role to attach the policy to.
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to attach.
        """
        try:
            response = super().attach_role_policy(role_name, policy_arn)
            LOGGER.info("attach role policy %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamRoleTestLib.attach_role_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def detach_role_policy(self, role_name: str = None, policy_arn: str = None) -> tuple:
        """
        Remove the specified managed policy from the specified role.

        :param role_name: role_name: str = None, policy_arn: str = None):
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to detach.
        """
        try:
            response = super().detach_role_policy(role_name, policy_arn)
            LOGGER.info("detach role policy %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamRoleTestLib.detach_role_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def list_attached_role_policies(self,
                                    role_name: str = None,
                                    path_prefix: str = "/",
                                    marker: str = None,
                                    max_items: int = 123) -> tuple:
        """
        List all managed policies that are attached to the specified IAM role.

        :param role_name: The name (friendly, not ARN) of the role to list attached policies for.
        :param path_prefix: The path prefix for filtering the results. This parameter is optional.
        If it is not included, it defaults to a slash (/), listing all policies.
        :param marker: Use this parameter only when paginating results and only after you receive
        a response indicating that the results are truncated.
        :param max_items: Use this only when paginating results to indicate the maximum number of
        items you want in the response.
        """
        try:
            response = super().list_attached_role_policies(role_name, path_prefix, marker,
                                                           max_items)
            LOGGER.info("list attached role policies %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamRoleTestLib.list_attached_role_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response
