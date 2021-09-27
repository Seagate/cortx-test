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

"""Python Library using boto3 module to perform account and user operations."""

import logging
from typing import Union
import boto3

LOGGER = logging.getLogger(__name__)


class IamLib:
    """Class initialising s3 connection and including functions for account and user operations."""

    def __init__(
            self,
            access_key: str = None,
            secret_key: str = None,
            endpoint_url: str = None,
            iam_cert_path: Union[str, bool] = None,
            **kwargs) -> None:
        """
        Method initializes members of IamLib.

        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint url.
        :param iam_cert_path: iam certificate path.
        :param debug: debug mode.
        """
        debug = kwargs.get("debug", False)
        use_ssl = kwargs.get("use_ssl", True)
        if debug:
            # Uncomment to enable debug
            boto3.set_stream_logger(name="botocore")

        try:
            self.iam = boto3.client("iam", use_ssl=use_ssl,
                                    verify=iam_cert_path,
                                    aws_access_key_id=access_key,
                                    aws_secret_access_key=secret_key,
                                    endpoint_url=endpoint_url)
            self.iam_resource = boto3.resource(
                "iam",
                use_ssl=use_ssl,
                verify=iam_cert_path,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                endpoint_url=endpoint_url)
        except Exception as err:
            if "unreachable network" not in str(err):
                LOGGER.critical(err)

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
