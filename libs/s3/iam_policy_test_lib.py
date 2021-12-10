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

    def create_policy_with_tags(self, policy_name: str = None, policy_document: str = None,
                                tags: list = None, **kwargs) -> tuple:
        """
        Creates a policy as per policy document with tags.

        :param policy_name: The name of the policy to create.
        :param policy_document: TThe JSON policy document that you want to use as the content
        for the new policy.
        :param tags: A list of tags that you want to attach to the new IAM customer managed policy.
         Each tag consists of a key name and an associated value.
        """
        try:

            policy = super().create_policy_with_tags(policy_name, policy_document, tags, **kwargs)
            LOGGER.info("Created policy %s.", policy.arn)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.create_policy_with_tags.__name__,
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

    def get_policy(self, policy_arn: str = None) -> tuple:
        """
        Retrieves information about the specified managed policy.

        :param policy_arn: The ARN of the policy to get.
        """
        try:
            response = super().get_policy(policy_arn)
            LOGGER.info("policy %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.get_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def list_policies(self,
                      scope: str = 'All',
                      only_attached: bool = True,
                      path_prefix: str = "/",
                      policy_usage_filter: str = "PermissionsPolicy",
                      max_items: int = 123,
                      **kwargs) -> tuple:
        """
        Lists all the managed policies that are available in account.

        :param scope: The scope to use for filtering the results.
        :param only_attached: A flag to filter the results to only the attached policies.
        :param path_prefix: The path prefix for filtering the results. This parameter is optional.
         If it is not included, it defaults to a slash (/), listing all policies.
        :param policy_usage_filter: The policy usage method to use for filtering the results.
        :param max_items:Use this only when paginating results to indicate the maximum number of
         items you want in the response.
        """
        try:
            response = super().list_policies(
                scope, only_attached, path_prefix, policy_usage_filter, max_items, **kwargs)
            LOGGER.info("list policies %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.list_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def create_role(self, assume_role_policy_document: str = None, role_name: str = None) -> tuple:
        """
        creates a role name and attaches a trust policy to it that is provided as a Policy Document.

        :param assume_role_policy_document: The trust relationship policy document that grants an
         entity permission to assume the role.
         :param role_name: The name of the role to create.
        """
        try:
            response = super().create_role(assume_role_policy_document, role_name)
            LOGGER.info("create role %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.create_role.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def create_role_with_tags(self,
                              assume_role_policy_document: str = None,
                              role_name: str = None,
                              tags: list = None,
                              **kwargs) -> tuple:
        """
        creates a role name and attaches a trust policy to it that is provided as a Policy Document.

        :param assume_role_policy_document: The trust relationship policy document that grants an
         entity permission to assume the role.
        :param role_name: The name of the role to create.
        :param tags: A list of tags that you want to attach to the new role.
        """
        try:
            response = super().create_role_with_tags(assume_role_policy_document, role_name)
            LOGGER.info("create role with tags %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.create_role.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def delete_role(self, role_name: str = None):
        """
        Deletes the specified role. The role must not have any policies attached.

        :param role_name: The name of the role to delete.
        """
        try:
            response = super().delete_role(role_name)
            LOGGER.info("delete role %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.delete_role.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def delete_role_policy(self, role_name: str = None, policy_name: str = None) -> tuple:
        """
        Deletes the specified inline policy that is embedded in the specified IAM role.

        :param role_name: The name (friendly name, not ARN) identifying the role that the policy
        is embedded in.
        :param policy_name: The name of the inline policy to delete from the specified IAM role.
        """
        try:
            response = super().delete_role_policy(role_name, policy_name)
            LOGGER.info("delete policy for role %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.delete_role_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def list_role_policies(self, role_name: str = None, marker: str = None, max_items: int = 123):
        """
        Lists the names of the inline policies that are embedded in the specified IAM role.

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
                             IamPolicyTestLib.list_role_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def list_roles(self, path_prefix: str = "/", max_items: int = 123, **kwargs) -> tuple:
        """
        Lists the IAM roles that have the specified path prefix. If there are none,
         the operation returns an empty list.

        :param path_prefix: The path prefix for filtering the results.
         For example, the prefix /application_abc/component_xyz/ gets all roles whose path starts
         with /application_abc/component_xyz/. This parameter is optional.
         If it is not included, it defaults to a slash (/), listing all roles.
        :param max_items: Use this only when paginating results to indicate the maximum number of
         items you want in the response.
        """
        try:
            response = super().list_roles(path_prefix, max_items, **kwargs)
            LOGGER.info("List roles %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.list_roles.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def attach_group_policy(self, group_name: str = None, policy_arn: str = None) -> tuple:
        """
        Attaches the specified managed policy to the specified IAM group.

        :param group_name: The name (friendly name, not ARN) of the group to attach the policy to.
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to attach.
        """
        try:
            response = super().attach_group_policy(group_name, policy_arn)
            LOGGER.info("attach group policy %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.attach_group_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def detach_group_policy(self, group_name: str = None, policy_arn: str = None) -> tuple:
        """
        Removes the specified managed policy from the specified IAM group.

        :param group_name: The name (friendly, not ARN) of the IAM group to detach the policy from.
        :param policy_arn: The Resource Name (ARN) of the IAM policy you want to detach.
        """
        try:
            response = super().detach_group_policy(group_name, policy_arn)
            LOGGER.info("detach group policy %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.detach_group_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def list_attached_group_policies(self,
                                     group_name: str = None,
                                     path_prefix: str = "/",
                                     marker: str = None,
                                     max_items: int = 123) -> tuple:
        """
        Lists all managed policies that are attached to the specified IAM group.

        :param group_name: The name (friendly, not ARN) of the group to list attached policies for.
        :param path_prefix: The path prefix for filtering the results. This parameter is optional.
        If it is not included, it defaults to a slash (/), listing all policies.
        :param marker: Use this parameter only when paginating results and only after you receive
        a response indicating that the results are truncated.
        :param max_items: Use this only when paginating results to indicate the maximum number of
        items you want in the response.
        :Returns: A list of Policy resources.
        """
        try:
            response = super().list_attached_group_policies(
                group_name, path_prefix, marker, max_items)
            LOGGER.info("list attached group policies %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.list_attached_group_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def attach_user_policy(self, user_name: str = None, policy_arn: str = None) -> tuple:
        """
        Attaches the specified managed policy to the specified user.

        :param user_name: The name (friendly name, not ARN) of the IAM user to attach the policy to.
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to attach.
        """
        try:
            response = super().attach_user_policy(user_name, policy_arn)
            LOGGER.info("attached user policy %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.attach_user_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def detach_user_policy(self, user_name: str = None, policy_arn: str = None) -> tuple:
        """
        Removes the specified managed policy from the specified user.

        :param user_name: The name (friendly, not ARN) of the IAM user to detach the policy from.
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to detach.
        """
        try:
            response = super().detach_user_policy(user_name, policy_arn)
            LOGGER.info("detach user policy %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.detach_user_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def list_attached_role_policies(self,
                                    role_name: str = None,
                                    path_prefix: str = "/",
                                    marker: str = None,
                                    max_items: int = 123) -> tuple:
        """
        Lists all managed policies that are attached to the specified IAM role.

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
                             IamPolicyTestLib.list_attached_role_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def attach_role_policy(self, role_name: str = None, policy_arn: str = None) -> tuple:
        """
        Attaches the specified managed policy to the specified IAM role

        :param role_name: The name (friendly name, not ARN) of the role to attach the policy to.
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to attach.
        """
        try:
            response = super().attach_role_policy(role_name, policy_arn)
            LOGGER.info("attach role policy %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.attach_role_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def detach_role_policy(self, role_name: str = None, policy_arn: str = None) -> tuple:
        """
        Removes the specified managed policy from the specified role.

        :param role_name: role_name: str = None, policy_arn: str = None):
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to detach.
        """
        try:
            response = super().detach_role_policy(role_name, policy_arn)
            LOGGER.info("detach role policy %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.detach_role_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def list_attached_user_policies(self,
                                    user_name: str = None,
                                    path_prefix: str = "/",
                                    marker: str = None,
                                    max_items: int = 123) -> tuple:
        """
        Lists all managed policies that are attached to the specified IAM user.

        :param user_name: The name (friendly, not ARN) of the user to list attached policies for.
        :param path_prefix: The path prefix for filtering the results. This parameter is optional.
         If it is not included, it defaults to a slash (/), listing all policies.
        :param marker: Use this parameter only when paginating results and only after you receive
         a response indicating that the results are truncated.
        :param max_items: Use this only when paginating results to indicate the maximum number of
        items you want in the response.
        """
        try:
            response = super().list_attached_user_policies(user_name, path_prefix, marker,
                                                           max_items)
            LOGGER.info("list attached user policies %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.list_attached_user_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response
