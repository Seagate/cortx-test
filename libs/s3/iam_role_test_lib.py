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

"""Python library using boto3 module to perform AWS Identity & Access Management (IAM) role."""

import logging

from botocore.exceptions import ClientError

from commons import errorcodes as err
from commons.exceptions import CTException
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.iam_core_lib import IamRole

LOGGER = logging.getLogger(__name__)


class IamRoleTestLib(IamRole):
    """Class initialising s3 connection and including functions for iam role operations."""

    def __init__(self,
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
        super().__init__(access_key=access_key, secret_key=secret_key, endpoint_url=endpoint_url,
                         iam_cert_path=s3_cert_path, **kwargs)

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
            raise CTException(err.S3_CLIENT_ERROR, error.args) from error

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

    def list_role_policies(self, **kwargs) -> tuple:
        """
        List the names of the inline policies that are embedded in the specified IAM role.

        # :param role_name: The name of the role to list policies for.
        # :param marker: Use this parameter only when paginating results and only after you receive
        #  a response indicating that the results are truncated.
        # :param max_items: Use this only when paginating results to indicate the maximum number of
        # items you want in the response.
        """
        try:
            response = super().list_role_policies(**kwargs)
            LOGGER.info("List role policies %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamRoleTestLib.list_role_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def list_roles(self, **kwargs) -> tuple:
        """
        List the IAM roles that have the specified path prefix.

        # :param path_prefix: The path prefix for filtering the results. For example, the prefix
        # /application_abc/component_xyz/ gets all roles whose path starts with
        # /application_abc/component_xyz/. This parameter is optional. If it is not included,
        # it defaults to a slash (/), listing all roles.
        # :param max_items: Use this only when paginating results to indicate the maximum number of
        # items you want in the response.
        """
        try:
            response = super().list_roles(**kwargs)
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

    def list_attached_role_policies(self, role_name: str = None, **kwargs) -> tuple:
        """
        List all managed policies that are attached to the specified IAM role.

        :param role_name: The name (friendly, not ARN) of the role to list attached policies for.
        # :param path_prefix: The path prefix for filtering the results. This parameter is optional.
        # If it is not included, it defaults to a slash (/), listing all policies.
        # :param marker: Use this parameter only when paginating results and only after you receive
        # a response indicating that the results are truncated.
        # :param max_items: Use this only when paginating results to indicate the maximum number of
        # items you want in the response.
        """
        try:
            response = super().list_attached_role_policies(role_name, **kwargs)
            LOGGER.info("list attached role policies %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamRoleTestLib.list_attached_role_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response
