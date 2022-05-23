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
#

"""Python Library using boto3 module to perform account and user operations."""

import os
import logging
from typing import Union
import boto3
from botocore.exceptions import ClientError
from config.s3 import S3_CFG

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class IAMRest:
    """Library for creating BOTO3 IAM Rest Library."""

    def __init__(
            self,
            access_key: str = None,
            secret_key: str = None,
            endpoint_url: str = None,
            iam_cert_path: Union[str, bool] = None,
            **kwargs) -> None:
        """
        Method initializes members of IamLib.

        Different instances need to be create as per different parameter values like access_key,
        secret_key etc.
        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint url.
        :param iam_cert_path: iam certificate path.
        :param debug: debug mode.
        """
        init_iam_connection = kwargs.get("init_iam_connection", True)
        debug = kwargs.get("debug", S3_CFG["debug"])
        self.use_ssl = kwargs.get("use_ssl", S3_CFG["use_ssl"])
        val_cert = kwargs.get("validate_certs", S3_CFG["validate_certs"])
        self.iam_cert_path = iam_cert_path if val_cert else False
        if val_cert and not os.path.exists(S3_CFG['iam_cert_path']):
            raise IOError(f'Certificate path {S3_CFG["iam_cert_path"]} does not exists.')
        if debug:
            # Uncomment to enable debug
            boto3.set_stream_logger(name="botocore")

        try:
            if init_iam_connection:
                self.iam = boto3.client("iam",
                                        use_ssl=self.use_ssl,
                                        verify=self.iam_cert_path,
                                        aws_access_key_id=access_key,
                                        aws_secret_access_key=secret_key,
                                        endpoint_url=endpoint_url)
                self.iam_resource = boto3.resource("iam",
                                                   use_ssl=self.use_ssl,
                                                   verify=self.iam_cert_path,
                                                   aws_access_key_id=access_key,
                                                   aws_secret_access_key=secret_key,
                                                   endpoint_url=endpoint_url)
            else:
                LOGGER.info("Skipped: create iam client, resource object with boto3.")
        except (ClientError, Exception) as error:
            if "unreachable network" not in str(error):
                LOGGER.critical(error)

    def __del__(self):
        """Destroy all core objects."""
        try:
            del self.iam
            del self.iam_resource
        except NameError as error:
            LOGGER.warning(error)


class IamLib(IAMRest):
    """Class initialising s3 connection and including functions for account and user operations."""

    def create_user(self, user_name: str = None) -> dict:
        """
        Creating new user.

        :param user_name: user name.
        :return: user dict.
        """
        response = self.iam.create_user(UserName=user_name)
        LOGGER.debug(response)

        return response

    def list_users(self) -> dict:
        """
        List the users in current account.

        :return: s3 users dict.
        """
        response = self.iam.list_users()
        LOGGER.debug(response)

        return response

    def create_access_key(self, user_name: str = None) -> dict:
        """
        Creating access key for given s3 user.

        :param user_name: s3 user name.
        :return: user dict.
        """
        response = self.iam.create_access_key(UserName=user_name)
        LOGGER.debug(response)

        return response

    def delete_access_key(
            self,
            user_name: str = None,
            access_key_id: str = None) -> dict:
        """
        Deleting access key for given user.

        :param user_name:
        :param access_key_id:
        :return: delete access key response dict.
        """
        response = self.iam.delete_access_key(
            AccessKeyId=access_key_id, UserName=user_name)
        LOGGER.debug(response)

        return response

    def delete_user(self, user_name: str = None) -> dict:
        """
        Deleting given user.

        :param user_name: s3 user name.
        :return: delete user response dict.
        """
        response = self.iam.delete_user(UserName=user_name)
        LOGGER.debug(response)

        return response

    def list_access_keys(self, user_name: str = None) -> dict:
        """
        Listing access keys for given user.

        :param user_name:
        :return: list access key response dict.
        """
        response = self.iam.list_access_keys(UserName=user_name)
        LOGGER.debug(response)

        return response

    def update_access_key(
            self,
            access_key_id: str = None,
            status: str = None,
            user_name: str = None) -> dict:
        """
        Updating access key for given user.

        :param access_key_id: s3 user access key id.
        :param status: 'Active'|'Inactive'
        :param user_name: s3 user name.
        :return: update access key response dict.
        """
        response = self.iam.update_access_key(
            AccessKeyId=access_key_id, Status=status, UserName=user_name)
        LOGGER.debug(response)

        return response

    def update_user(self, new_user_name: str = None,
                    user_name: str = None) -> dict:
        """
        Updating given user.

        :param new_user_name: new s3 user name.
        :param user_name: old s3 user name.
        :return: update user response dict.
        """
        response = self.iam.update_user(
            NewUserName=new_user_name, UserName=user_name)
        LOGGER.debug(response)

        return response

    def get_user_login_profile(self, user_name: str = None) -> dict:
        """
        Get user login profile if exists.

        :param user_name: s3 user name.
        :return: get user login profile response dict.
        """
        response = self.iam_resource.LoginProfile(user_name)
        LOGGER.debug(response)

        return response

    def create_user_login_profile(
            self,
            user_name: str = None,
            password: str = None,
            password_reset: bool = False):
        """
        Create user login profile.

        :param user_name: s3 user name.
        :param password: s3 password.
        :param password_reset: True/False
        :return: create user login profile response dict.
        """
        login_profile = self.iam_resource.LoginProfile(user_name)
        response = login_profile.create(
            Password=password,
            PasswordResetRequired=password_reset)
        LOGGER.debug(response)

        return response

    def update_user_login_profile(
            self,
            user_name: str = None,
            password: str = None,
            password_reset: bool = False) -> dict:
        """
        Update user login profile.

        :param user_name: s3 user name.
        :param password: s3 password.
        :param password_reset: True/False
        :return: update user profile response dict.
        """
        login_profile = self.iam_resource.LoginProfile(user_name)
        response = login_profile.update(Password=password,
                                        PasswordResetRequired=password_reset)
        LOGGER.debug("output = %s", str(response))

        return response

    def update_user_login_profile_no_pwd_reset(
            self, user_name: str = None, password: str = None) -> dict:
        """
        Update user login profile.

        :param user_name: s3 user name.
        :param password: s3 password.
        :return: update user login profile no pwd reset response dict.
        """
        login_profile = self.iam_resource.LoginProfile(user_name)
        response = login_profile.update(Password=password)
        LOGGER.debug("output = %s", str(response))

        return response

    def delete_user_login_profile(self, user_name):
        """
        Delete the password for the specified IAM user.

        :param user_name: The name of the user whose password you want to delete.
        """
        response = self.iam.delete_login_profile(UserName=user_name)
        LOGGER.debug(response)

        return response

    def change_password(self, old_password: str = None, new_password: str = None):
        """
        Change the password of the IAM user with the IAM user.

        boto3.client object requesting for the password change. IAM object should be created with
        Access and Secret key of IAM user which is requesting for the password change.
        :param old_password: Old user password.
        :param new_password: New user password.
        :return: None
        """
        self.iam.change_password(OldPassword=old_password, NewPassword=new_password)


class IamPolicy(IAMRest):
    """Class initialising s3 connection and including functions for iam policy operations."""

    def create_policy(self, policy_name: str = None,
                      policy_document: str = None, **kwargs) -> object:
        """
        Create a policy as per policy document.

        :param policy_name: The name of the policy to create.
        :param policy_document: The policy document.
        """
        response = self.iam_resource.create_policy(PolicyName=policy_name,
                                                   PolicyDocument=policy_document, **kwargs)

        return response

    def delete_policy(self, policy_arn: str = None) -> dict:
        """
        Delete a policy.

        :param policy_arn: The ARN of the policy to delete.
        """
        response = self.iam_resource.Policy(policy_arn).delete()

        return response

    def get_policy(self, policy_arn: str = None) -> dict:
        """
        Retrieve information about the specified managed policy.

        :param policy_arn: The ARN of the policy to get.
        """
        response = self.iam.get_policy(PolicyArn=policy_arn)

        return response

    def list_policies(self, **kwargs) -> dict:
        """
        List all the managed policies that are available in account.

        # :param scope: The scope to use for filtering the results.
        # :param only_attached: A flag to filter the results to only the attached policies.
        # :param path_prefix: The path prefix for filtering the results. This parameter is optional.
        # If it is not included, it defaults to a slash (/), listing all policies.
        # :param policy_usage_filter: The policy usage method to use for filtering the results.
        # :param max_items:Use this only when paginating results to indicate the maximum number of
        # items you want in the response.
        """
        response = self.iam.list_policies(**kwargs)

        return response

    def attach_group_policy(self, group_name: str = None, policy_arn: str = None):
        """
        Attache the specified managed policy to the specified IAM group.

        :param group_name: The name(friendly name, not ARN) of the group to attach the policy to.
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to attach.
        """
        response = self.iam.attach_group_policy(GroupName=group_name, PolicyArn=policy_arn)

        return response

    def detach_group_policy(self, group_name: str = None, policy_arn: str = None):
        """
        Remove the specified managed policy from the specified IAM group.

        :param group_name: The name(friendly, not ARN) of the IAM group to detach the policy from.
        :param policy_arn: The Resource Name (ARN) of the IAM policy you want to detach.
        """
        response = self.iam.detach_group_policy(GroupName=group_name, PolicyArn=policy_arn)

        return response

    def list_attached_group_policies(self, group_name: str = None, **kwargs) -> list:
        """
        List all managed policies that are attached to the specified IAM group.

        :param group_name: The name(friendly, not ARN) of the group to list attached policies for.
        # :param path_prefix: The path prefix for filtering the results. This parameter is optional.
        # If it is not included, it defaults to a slash (/), listing all policies.
        # :param marker: Use this parameter only when paginating results and only after you receive
        # a response indicating that the results are truncated.
        # :param max_items: Use this only when paginating results to indicate the maximum number of
        # items you want in the response.
        :Returns: A list of Policy resources.
        """
        response = self.iam.list_attached_group_policies(GroupName=group_name, **kwargs)

        return response

    def attach_user_policy(self, user_name: str = None, policy_arn: str = None):
        """
        Attache the specified managed policy to the specified user.

        :param user_name: The name(friendly name, not ARN) of the IAM user to attach the policy to.
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to attach.
        """
        response = self.iam.attach_user_policy(UserName=user_name, PolicyArn=policy_arn)

        return response

    def detach_user_policy(self, user_name: str = None, policy_arn: str = None):
        """
        Remove the specified managed policy from the specified user.

        :param user_name: The name(friendly name, not ARN) of the IAM user to detach the policy from
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to detach.
        """
        response = self.iam.detach_user_policy(
            UserName=user_name,
            PolicyArn=policy_arn)

        return response

    def list_attached_user_policies(self, user_name: str = None, **kwargs) -> dict:
        """
        List all managed policies that are attached to the specified IAM user.

        :param user_name: The name(friendly name, not ARN) of the user to list attached policies for
        # :param path_prefix: The path prefix for filtering the results. This parameter is optional.
        #  If it is not included, it defaults to a slash (/), listing all policies.
        # :param marker: Use this parameter only when paginating results and only after you receive
        #  a response indicating that the results are truncated.
        # :param max_items: Use this only when paginating results to indicate the maximum number of
        # items you want in the response.
        """
        response = self.iam.list_attached_user_policies(UserName=user_name, **kwargs)

        return response

    def validate_policy(self,
                        policy_document: str = None,
                        validate_policy_resource_type: str = None,
                        policy_type: str = None,
                        next_token: str = None,
                        **kwargs) -> dict:
        """
        Request the validation of a policy and returns a list of findings.

        The findings help you identify issues and provide actionable recommendations to resolve the
        issue and enable you to author functional policies that meet security best practices.
        #:param locale: The locale to use for localizing the findings.
        #:param max_results: The maximum number of results to return in the response.
        :param next_token: A token used for pagination of results returned.
        :param policy_document: The JSON policy document to use as the content for the policy.
        :param policy_type: The type of policy to validate. Identity policies grant permissions to
         IAM principals.
        :param validate_policy_resource_type: The type of resource to attach to your resource policy
        """
        locale = kwargs.get("locale", "DE")
        max_result = kwargs.get("max_results", 123)
        response = self.iam.validate_policy(
            locale=locale, maxResults=max_result, nextToken=next_token,
            policyDocument=policy_document, policyType=policy_type,
            validatePolicyResourceType=validate_policy_resource_type)

        return response


class IamRole(IAMRest):
    """Class initialising s3 connection and including functions for iam role operations."""

    def create_role(self, assume_role_policy_document: str = None,
                    role_name: str = None, **kwargs) -> dict:
        """
        create a role name and attaches a trust policy to it that is provided as a Policy Document.

        :param assume_role_policy_document: The trust relationship policy document that grants an
         entity permission to assume the role.
        :param role_name: The name of the role to create.
        # :param tags: A list of tags that you want to attach to the new role.
        """
        response = self.iam.create_role(AssumeRolePolicyDocument=assume_role_policy_document,
                                        RoleName=role_name, **kwargs)

        return response

    def delete_role(self, role_name: str = None):
        """
        Delete the specified role. The role must not have any policies attached.

        :param role_name: The name of the role to delete.
        """
        response = self.iam.delete_role(RoleName=role_name)

        return response

    def delete_role_policy(self, role_name: str = None, policy_name: str = None):
        """
        Delete the specified inline policy that is embedded in the specified IAM role.

        :param role_name: The name(friendly name, not ARN) identifying the role that the policy
        is embedded in.
        :param policy_name: The name of the inline policy to delete from the specified IAM role.
        """
        response = self.iam.delete_role_policy(RoleName=role_name, PolicyName=policy_name)

        return response

    def list_role_policies(self, **kwargs) -> dict:
        """
        List the names of the inline policies that are embedded in the specified IAM role.

        # :param role_name: The name of the role to list policies for.
        # :param marker: Use this parameter only when paginating results and only after you receive
        #  a response indicating that the results are truncated.
        # :param max_items: Use this only when paginating results to indicate the maximum number of
        # items you want in the response.
        """
        response = self.iam.list_role_policies(**kwargs)

        return response

    def list_roles(self, **kwargs):
        """
        List the IAM roles that have the specified path prefix.

        If there are none, the operation returns an empty list.
        # :param path_prefix: The path prefix for filtering the results.
        #  For example, the prefix /application_abc/component_xyz/ gets all roles whose path starts
        #  with /application_abc/component_xyz/. This parameter is optional.
        #  If it is not included, it defaults to a slash (/), listing all roles.
        # :param max_items: Use this only when paginating results to indicate the maximum number of
        #  items you want in the response.
        """
        response = self.iam.list_roles(**kwargs)

        return response

    def list_attached_role_policies(self, role_name: str = None, **kwargs) -> dict:
        """
        List all managed policies that are attached to the specified IAM role.

        :param role_name: The name(friendly name, not ARN) of the role to list attached policies for
        # :param path_prefix: The path prefix for filtering the results. This parameter is optional.
        # If it is not included, it defaults to a slash (/), listing all policies.
        # :param marker: Use this parameter only when paginating results and only after you receive
        # a response indicating that the results are truncated.
        # :param max_items: Use this only when paginating results to indicate the maximum number of
        # items you want in the response.
        """
        response = self.iam.list_attached_role_policies(RoleName=role_name, **kwargs)

        return response

    def attach_role_policy(self, role_name: str = None, policy_arn: str = None):
        """
        Attach the specified managed policy to the specified IAM role.

        :param role_name: The name(friendly name, not ARN) of the role to attach the policy to.
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to attach.
        """
        response = self.iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

        return response

    def detach_role_policy(self, role_name: str = None, policy_arn: str = None):
        """
        Remove the specified managed policy from the specified role.

        :param role_name: role_name: str = None, policy_arn: str = None):
        :param policy_arn: The Amazon Resource Name (ARN) of the IAM policy you want to detach.
        """
        response = self.iam.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)

        return response
