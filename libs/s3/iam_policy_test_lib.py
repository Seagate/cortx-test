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

"""Python library using boto3 module to perform AWS Identity & Access Management (IAM) policies."""

import logging
from botocore.exceptions import ClientError

from commons.utils.s3_utils import poll
from commons import errorcodes as err
from commons.exceptions import CTException
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.iam_core_lib import IamPolicy


LOGGER = logging.getLogger(__name__)


class IamPolicyTestLib(IamPolicy):
    """Class initialising s3 connection and including functions for iam policy operations."""

    def __init__(
            self,
            access_key: str = ACCESS_KEY,
            secret_key: str = SECRET_KEY,
            endpoint_url: str = S3_CFG["iam_url"],
            s3_cert_path: str = S3_CFG["s3_cert_path"],
            **kwargs) -> None:
        """
        Method to initializes members of IamPolicyTestLib and its parent class.

        :param access_key: access key
        :param secret_key: secret key
        :param endpoint_url: endpoint url
        :param s3_cert_path: s3 certificate path
        """
        self.sync_delay = S3_CFG["sync_delay"]
        super().__init__(
            access_key,
            secret_key,
            endpoint_url,
            s3_cert_path,
            **kwargs)

    def create_policy(self, policy_name: str = None,
                      policy_document: str = None, **kwargs) -> tuple:
        """
        Create a policy as per policy document.

        :param policy_name: The name of the policy to create.
        :param policy_document: The JSON policy document that you want to use as the content
        for the new policy.
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
        # :param tags: A list of tags that you want to attach to the new IAM customer managed policy
        #  Each tag consists of a key name and an associated value.
        :return: The newly created policy.
        """
        try:

            policy = super().create_policy(policy_name, policy_document, **kwargs)
            LOGGER.info("Created policy %s.", policy.arn)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.create_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args) from error

        return True, policy

    def delete_policy(self, policy_arn: str = None) -> tuple:
        """
        Delete a policy.

        :param policy_arn: The ARN of the policy to delete.
        """
        try:
            response = super().delete_policy(policy_arn)
            LOGGER.info("Deleted policy %s.", policy_arn)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.delete_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def get_policy(self, policy_arn: str = None) -> tuple:
        """
        Retrieve information about the specified managed policy.

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

    def list_policies(self, **kwargs) -> tuple:
        """
        List all the managed policies that are available in account.

        # :param scope: The scope to use for filtering the results.
        # :param only_attached: A flag to filter the results to only the attached policies.
        # :param path_prefix: The path prefix for filtering the results. This parameter is optional.
        #  If it is not included, it defaults to a slash (/), listing all policies.
        # :param policy_usage_filter: The policy usage method to use for filtering the results.
        # :param max_items:Use this only when paginating results to indicate the maximum number of
        #  items you want in the response.
        """
        try:
            response = super().list_policies(**kwargs)
            LOGGER.info("list policies %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.list_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def attach_group_policy(self, group_name: str = None, policy_arn: str = None) -> tuple:
        """
        Attache the specified managed policy to the specified IAM group.

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
        Remove the specified managed policy from the specified IAM group.

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

    def list_attached_group_policies(self, group_name: str = None, **kwargs) -> tuple:
        """
        List all managed policies that are attached to the specified IAM group.

        :param group_name: The name (friendly, not ARN) of the group to list attached policies for.
        # :param path_prefix: The path prefix for filtering the results. This parameter is optional.
        # If it is not included, it defaults to a slash (/), listing all policies.
        # :param marker: Use this parameter only when paginating results and only after you receive
        # a response indicating that the results are truncated.
        # :param max_items: Use this only when paginating results to indicate the maximum number of
        # items you want in the response.
        :Returns: A list of Policy resources.
        """
        try:
            response = super().list_attached_group_policies(group_name, **kwargs)
            LOGGER.info("list attached group policies %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.list_attached_group_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def attach_user_policy(self, user_name: str = None, policy_arn: str = None) -> tuple:
        """
        Attache the specified managed policy to the specified user.

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
        Remove the specified managed policy from the specified user.

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

    def list_attached_user_policies(self, user_name: str = None, **kwargs) -> tuple:
        """
        List all managed policies that are attached to the specified IAM user.

        :param user_name: The name (friendly, not ARN) of the user to list attached policies for.
        # :param path_prefix: The path prefix for filtering the results. This parameter is optional.
        #  If it is not included, it defaults to a slash (/), listing all policies.
        # :param marker: Use this parameter only when paginating results and only after you receive
        #  a response indicating that the results are truncated.
        # :param max_items: Use this only when paginating results to indicate the maximum number of
        # items you want in the response.
        """
        try:
            response = super().list_attached_user_policies(user_name, **kwargs)
            LOGGER.info("list attached user policies %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.list_attached_user_policies.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def validate_policy(self,
                        policy_document: str = None,
                        validate_policy_resource_type: str = None,
                        policy_type: str = None,
                        next_token: str = None,
                        **kwargs) -> tuple:
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
        try:
            response = super().validate_policy(policy_document, validate_policy_resource_type,
                                               policy_type, next_token, **kwargs)
            LOGGER.info("validate policy %s.", response)
        except ClientError as error:
            LOGGER.exception("Error in  %s: %s",
                             IamPolicyTestLib.validate_policy.__name__,
                             error)
            raise CTException(err.S3_CLIENT_ERROR, error.args)

        return True, response

    def check_policy_in_attached_policies(self, user: str, policy_arn: str, delay: int = None):
        """
        Check if policy with given Policy ARN is attached to a user

        :param user: User name
        :param policy_arn: Policy ARN
        :param delay: Time for list attached policy polling
        """
        if not delay:
            delay = self.sync_delay
        listed_policies = poll(super().list_attached_user_policies, user, timeout=delay)
        for policy in listed_policies["AttachedPolicies"]:
            if policy["PolicyArn"] == policy_arn:
                return True
        return False
