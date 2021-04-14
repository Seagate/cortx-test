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

"""Cortxcli Test Library."""

import logging
from commons import errorcodes as err
from commons.exceptions import CTException

from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser
from libs.csm.cli.cli_csm_user import CortxCliCsmUser
from libs.csm.cli.cli_alerts_lib import CortxCliAlerts
from libs.s3.iam_test_lib import IamTestLib

# from libs.s3.iam_core_lib import IamLib
# from config import CMN_CFG

LOGGER = logging.getLogger(__name__)


class CortxcliS3AccountOperations(CortxCliS3AccountOperations):
    """Overriding class for S3 Account Operations."""

    def __init__(
            self, session_obj: object = None):
        """Constructor."""
        super().__init__(session_obj=session_obj)


class CortxcliS3BucketOperations(CortxCliS3BucketOperations):
    """Overriding class for cortxcli s3 bucket operations."""

    def __init__(
            self, session_obj: object = None):
        """Constructor."""
        super().__init__(session_obj=session_obj)


class CortxcliIamUser(CortxCliIamUser):
    """Overriding class for cortxcli Iam User."""

    def __init__(
            self, session_obj: object = None):
        """Constructor."""
        super().__init__(session_obj=session_obj)


class CortxcliCsmUser(CortxCliCsmUser):
    """Overriding class for CSM User."""

    def __init__(
            self, session_obj: object = None):
        """Constructor."""
        super().__init__(session_obj=session_obj)


class CortxcliAlerts(CortxCliAlerts):
    """Methods for performing operations on alerts using cortxcli."""

    def __init__(self, session_obj: object = None):
        """
        Method initializes members of CortxCliAlerts.

        :param object session_obj: session object of host connection if already established
        """
        super().__init__(session_obj=session_obj)


class CortxCliTestLib(CortxcliS3AccountOperations,
                    CortxcliS3BucketOperations,
                    CortxcliIamUser,
                    CortxcliCsmUser,
                    IamTestLib):
    """Class for performing cortxcli operations."""

    def __init__(
            self, session_obj: object = None):
        """Constructor."""
        super().__init__(session_obj=session_obj)

    def login_cortx_cli(
            self,
            username: str = None,
            password: str = None,
            **kwargs) -> tuple:
        """
        Method to login to cortxcli.

        :param username: username to be passed
        :param password:
        :param kwargs:
        :keyword login_cortxcli: command for login to CLI
        :return: tuple
        """
        try:
            if None in {username, password}:
                response = super().login_cortx_cli()
            else:
                response = super().login_cortx_cli(username, password, **kwargs)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CortxCliTestLib.login_cortx_cli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return response

    def logout_cortx_cli(self) -> tuple:
        """
        Function will be used to logout of CORTX CLI.

        :return: True/False and output
        """
        try:
            response = super().logout_cortx_cli()
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CortxCliTestLib.logout_cortx_cli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return response

    def list_accounts_cortxcli(self) -> tuple:
        """
        Listing accounts using aws s3iamcli.

        :return: list account cortxcli response.
        """
        try:
            response = super().show_s3account_cortx_cli()
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CortxCliTestLib.list_accounts_cortxcli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return response

    def list_users_cortxcli(self) -> tuple:
        """
        Listing users using aws cortxcli.

        :return: list users cortxcli response.
        """
        try:
            status, response = super().list_iam_user()
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CortxCliTestLib.list_users_cortxcli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return status, response

    def create_account_cortxcli(self,
                                account_name: str,
                                account_email: str,
                                password: str,
                                **kwargs) -> tuple:
        """
        Creating new account using aws s3iamcli.

        :param password:
        :param account_email:
        :param account_name: s3 account name.
        :return: create account cortxcli response.
        """
        try:
            status, response = super().create_s3account_cortx_cli(
                account_name, account_email, password, **kwargs)
            if status:
                status, response = self.get_s3account_details_cortxcli(
                    response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CortxCliTestLib.create_account_cortxcli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return status, response

    def create_user_using_cortxcli(self,
                                   user_name: str = None,
                                   password: str = None,
                                   confirm_password: str = None,
                                   **kwargs) -> tuple:
        """
        Creating user using cortxcli.

        This function will create new IAM user
        :param user_name: Name of IAM user to be created
        :param password: Password to create s3 IAM user.
        :param confirm_password: Confirm password to create s3 IAM user.
        :keyword confirm: Confirm option for creating a IAM user
        :keyword help_param: True for displaying help/usage
        :return: (Boolean/Response)
        :return: create user using cortxcli response.
        """
        try:
            response = super().create_iam_user(
                user_name=user_name,
                password=password,
                confirm_password=confirm_password,
                **kwargs)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CortxCliTestLib.create_user_using_cortxcli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return response

    def reset_s3account_password(
            self,
            account_name: str,
            new_password: str,
            **kwargs) -> tuple:
        """
        Function will update password for specified s3 account to new_password using CORTX CLI.

        :param account_name: Name of the s3 account whose password is to be update
        :param new_password: New password for s3 account
        :keyword reset_password: Y/n
        :return: True/False and Response returned by CORTX CLI
        """
        # inhirit from csm cli
        try:
            response = super(
                CortxCliTestLib,
                self).reset_s3account_password(account_name,
                                               new_password,
                                               **kwargs)

        except Exception as error:
            LOGGER.error(
                "Error in %s:%s",
                CortxCliTestLib.reset_s3account_password.__name__,
                error)
            raise CTException(err.S3_ERROR, error.args[0])

        return response

    def get_s3account_details_cortxcli(
            self,
            account_name=None,
            account_email=None,
            password=None,
            response=None):
        """
        Method will create s3 account using cortxcli and returns access and secret key.

        :param response:
        :param str account_name: Name of s3 account user to be created.
        :param str account_email: Account email for account creation.
        :param str password: Password to create s3 account user.
        :return: (True/False, Response)
        :rtype: tuple
        """
        acc_details = dict()
        if response is None:
            response = self.create_s3account_cortx_cli(
                account_name=account_name,
                account_email=account_email,
                password=password)[1]

        if account_name in response:
            response = self.split_table_response(response)[0]
            acc_details["account_name"] = response[1]
            acc_details["account_email"] = response[2]
            acc_details["account_id"] = response[3]
            acc_details["canonical_id"] = response[4]
            acc_details["access_key"] = response[5]
            acc_details["secret_key"] = response[6]
            LOGGER.info("Account Details: %s", acc_details)
            self.logout_cortx_cli()
            return True, acc_details

        return False, response

    def create_get_s3account_details_cortxcli(
            self,
            account_name,
            account_email,
            password):
        """
        Method will create s3 account using cortxcli and returns access and secret key.

        :param str account_name: Name of s3 account user to be created.
        :param str account_email: Account email for account creation.
        :param str password: Password to create s3 account user.
        :return: (True/False, Response)
        :rtype: tuple
        """
        acc_details = dict()
        login = self.login_cortx_cli()
        if login:
            response = self.create_s3account_cortx_cli(
                account_name=account_name,
                account_email=account_email,
                password=password)[1]
            if account_name in response:
                response = self.split_table_response(response)[0]
                acc_details["account_name"] = response[1]
                acc_details["account_email"] = response[2]
                acc_details["account_id"] = response[3]
                acc_details["canonical_id"] = response[4]
                acc_details["access_key"] = response[5]
                acc_details["secret_key"] = response[6]
                LOGGER.info("Account Details: %s", acc_details)
                self.logout_cortx_cli()
                return True, acc_details

            return False, response

        return False, login

    @staticmethod
    def delete_account_cortxcli(account_name: str = None) -> tuple:
        """
        Deleting account using cortxcli.

        :param account_name: s3 account name.
        :return:
        """
        try:
            response = super().delete_s3account_cortx_cli(account_name)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CortxCliTestLib.delete_account_cortxcli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return response

    def create_user_login_profile_boto3(self,
                                        user_name=None,
                                        password=None,
                                        password_reset=False) -> tuple:
        """
        Create user login profile using aws cortxcli.

        :param user_name: s3 user name.
        :param password: s3 password.
        :param password_reset:
        :return: create user login profile boto3 response.
        """
        # use boto3

        return self.create_user_login_profile(user_name=user_name,
                                              password=password,
                                              password_reset=password_reset)

    def get_user_login_profile_boto3(self, user_name: str = None) -> tuple:
        """
        Get user login profile if exists.

        :param user_name: Name of the user.
        :return: (Boolean, response).
        """
        return self.get_user_login_profile(user_name)

    @staticmethod
    def create_account_login_profile_cortxcli(
            acc_name: str = None,
            password: str = None,
            access_key: str = None,
            secret_key: str = None,
            password_reset: bool = False) -> tuple:
        """
        Create account login profile using cortxcli.

        :param acc_name: s3 account name.
        :param password: s3 password.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :param password_reset: password reset True/False.
        :return: create account login profile s3iamcli response.
        """
        # Not Supported in cortxcli, check boto3

    @staticmethod
    def update_account_login_profile_cortxcli(
            acc_name: str = None,
            password: str = None,
            access_key: str = None,
            secret_key: str = None,
            password_reset: bool = False) -> tuple:
        """
        Update account login profile using s3iamcli.

        :param acc_name: s3 account name.
        :param password: s3 password.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :param password_reset: password reset True/False.
        :return: update account login profile cortxcli response.
        """
        # Not Supported in cortxcli, check boto3

    @staticmethod
    def get_account_login_profile_cortxcli(
            acc_name: str = None,
            access_key: str = None,
            secret_key: str = None) -> tuple:
        """
        Get account login profile using cortxcli.

        :param acc_name: s3 account name.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :return: get account login profile s3iamcli response.
        """
        # Not Supported in cortxcli, check boto3

    def update_user_login_profile_boto3(
            self,
            user_name: str = None,
            password: str = None,
            password_reset: bool = False,
    ) -> tuple:
        """
        Update user login profile using cortxcli.

        :param user_name: s3 user name.
        :param password: s3 password.
        :param password_reset: password reset.
        :return: update user login profile boto3 response.
        """
        return super().update_user_login_profile(user_name, password, password_reset)

    def update_user_login_profile_no_pwd_reset(
            self,
            user_name: str = None,
            password: str = None,
            password_reset: bool = False) -> dict:
        """
        Update user login profile.

        :param password_reset:
        :param user_name: s3 user name.
        :param password: s3 password.
        :return: update user login profile no pwd reset response dict.
        """
        # using boto3
        return self.update_user_login_profile(
            user_name=user_name,
            password=password,
            password_reset=password_reset)[1]

    def reset_account_access_key_cortxcli(
            self, account_name: str = None, ) -> tuple:
        """
        Method to reset account access key.

        :param account_name: s3 account name.
        :return: reset account access key cortxcli response.

        """

    def get_temp_auth_credentials_account(self,
                                          account_name: str = None,
                                          account_password: str = None,
                                          duration: int = None) -> tuple:
        """
        Retrieving the temporary auth credentials for the given account.

        :param account_name: s3 account name.
        :param account_password: s3 account password.
        :param duration:
        :return: get temp auth credentials account response.
        """
        # Not Supported

    def get_temp_auth_credentials_user(self,
                                       account_name: str = None,
                                       user_name: str = None,
                                       password: str = None,
                                       duration: int = None) -> tuple:
        """
        Retrieving the temporary auth credentials for the given user.

        :param account_name: s3 account name.
        :param user_name: s3 user name.
        :param password: s3 password.
        :param duration:
        :return: get temp auth credentials user response.
        """
        # Not supported

    def reset_access_key_and_delete_account_cortxcli(
            self, account_name: str = None) -> tuple:
        """
        Reset account access key and delete the account using aws cortxcli.

        :param account_name: Name of the account.
        :return: (Boolean, response)
        """
        # LOGGER.info(
        #     "Reset account access key and delete that account")
        # response = self.reset_account_access_key_cortxcli(account_name)
        # LOGGER.debug(response)
        # if not response[0]:
        #     return False, response
        # access_key = response[1]["AccessKeyId"]
        # secret_key = response[1]["SecretKey"]
        # LOGGER.debug(access_key, secret_key)
        result = self.delete_account_cortxcli(
            account_name=account_name)

        return result

    def change_user_password(self,
                             user_name: str = None,
                             password: str = None,
                             password_reset: bool = False) -> tuple:
        """
        Change password for IAM user.

        :return: change user password response.
        """
        # Checking, cortxcli reset password
        # s3iamusers reset_password
        # Check boto3, update_user_login_profile

        return self.update_user_login_profile_boto3(user_name,
                                                    password,
                                                    password_reset=password_reset)

    def reset_iamuser_password(
            self,
            iamuser_name: str,
            new_password: str,
            **kwargs) -> tuple:
        """
        This function will update password for specified s3 account to new_password using CORTX CLI.
        :param account_name: Name of the s3 account whose password is to be update
        :param new_password: New password for s3 account
        :keyword reset_password: Y/n
        :return: True/False and Response returned by CORTX CLI
        """
        reset_password = kwargs.get("reset_password", "Y")
        cmd = "s3iamusers reset_password {}"
        reset_pwd_cmd = cmd.format(iamuser_name)
        LOGGER.info("Resetting s3 account password to %s", new_password)
        response = self.execute_cli_commands(cmd=reset_pwd_cmd)[1]
        if "Password:" in response:
            response = self.execute_cli_commands(cmd=new_password)[1]
            if "Confirm Password:" in response:
                response = self.execute_cli_commands(cmd=new_password)[1]
                if "[Y/n]" in response:
                    response = self.execute_cli_commands(cmd=reset_password)[1]
                    if iamuser_name in response:
                        LOGGER.info("Response returned: \n%s", response)
                        return True, response
                return False, response


    def create_iamuser_access_key(self, user_name: str = None) -> tuple:
        """
        Creating access key for given user.

        :param user_name: Name of the user.
        :return: (Boolean, response).
        """
        LOGGER.info("Creating %s user access key.", user_name)
        status, response = IamTestLib.create_access_key(user_name)
        LOGGER.info(response)
        return status, response


    def create_bucket_cortx_cli(
            self,
            bucket_name: str) -> tuple:
        """
        This function will create a bucket using CORTX CLI
        :param bucket_name: New bucket's name
        :return: True/False and response returned by CORTX CLI
        """
        try:
            response = super().create_bucket_cortx_cli()
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CortxCliTestLib.create_bucket_cortx_cli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return response
