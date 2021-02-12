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

import boto3

from commons import commands
from commons.utils.system_utils import run_local_cmd
from libs.s3 import LOGGER


class IamLib:
    """Class initialising s3 connection and including functions for account and user operations."""

    def __init__(
            self,
            access_key: str = None,
            secret_key: str = None,
            endpoint_url: str = None,
            iam_cert_path: str = None,
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

        if debug:
            # Uncomment to enable debug
            boto3.set_stream_logger(name="botocore")

        self.iam = boto3.client("iam", verify=iam_cert_path,
                                aws_access_key_id=access_key,
                                aws_secret_access_key=secret_key,
                                endpoint_url=endpoint_url)
        self.iam_resource = boto3.resource(
            "iam",
            verify=iam_cert_path,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url)

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


class S3IamCli:
    """Class for performing S3iamcli operations."""

    @staticmethod
    def list_accounts_s3iamcli(
            ldap_user_id: str = None,
            ldap_password: str = None) -> tuple:
        """
        Listing accounts using aws s3iamcli.

        :param ldap_user_id: ldap user id.
        :param ldap_password: ldap password.
        :return: list account s3iamcli response.
        """
        cmd = commands.CMD_LIST_ACC.format(ldap_user_id, ldap_password)
        LOGGER.info("List accounts s3iamcli = %s", str(cmd))
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def list_users_s3iamcli(
            access_key: str = None,
            secret_key: str = None) -> tuple:
        """
        Listing users using aws s3iamcli.

        :param access_key: s3 user access key.
        :param secret_key: s3 user secret key.
        :return: list users s3iamcli response.
        """
        cmd = commands.CMD_LST_USR.format(access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.info("output = %s", str(result))

        return result

    @staticmethod
    def create_account_s3iamcli(
            account_name: str = None,
            email_id: str = None,
            ldap_user_id: str = None,
            ldap_password: str = None) -> tuple:
        """
        Creating new account using aws s3iamcli.

        :param account_name: s3 account name.
        :param email_id: s3 user mail id.
        :param ldap_user_id: ldap user id.
        :param ldap_password: ldap password.
        :return: create account s3iamcli response.
        """
        cmd = commands.CMD_CREATE_ACC.format(
            account_name, email_id, ldap_user_id, ldap_password)
        LOGGER.info(cmd)
        response = run_local_cmd(cmd)
        LOGGER.debug(response)

        return response

    @staticmethod
    def delete_account_s3iamcli(
            account_name: str = None,
            access_key: str = None,
            secret_key: str = None,
            force: bool = True) -> tuple:
        """
        Deleting account using aws s3iamcli.

        :param account_name: s3 account name.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :param force: forceful delete s3 account True/False.
        :return:
        """
        if force:
            cmd = commands.CMD_DEL_ACC_FORCE.format(
                account_name, access_key, secret_key)
        else:
            cmd = commands.CMD_DEL_ACC.format(
                account_name, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def create_user_login_profile_s3iamcli(
            user_name: str = None,
            password: str = None,
            password_reset: bool = False,
            access_key: str = None,
            secret_key: str = None) -> tuple:
        """
        Create user login profile using aws s3iamcli.

        :param user_name: s3 user name.
        :param password: s3 password.
        :param password_reset:
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :return: create user login profile s3iamcli response.
        """
        if password_reset:
            cmd = commands.CREATE_USR_PROFILE_PWD_RESET.format(
                user_name, password, access_key, secret_key)
        else:
            cmd = commands.CREATE_USR_PROFILE_NO_PWD_RESET.format(
                user_name, password, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def create_account_login_profile_s3iamcli(
            acc_name: str = None,
            password: str = None,
            access_key: str = None,
            secret_key: str = None,
            password_reset: bool = False) -> tuple:
        """
        Create account login profile using s3iamcli.

        :param acc_name: s3 account name.
        :param password: s3 password.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :param password_reset: password reset True/False.
        :return: create account login profile s3iamcli response.
        """
        if password_reset:
            cmd = commands.CREATE_ACC_PROFILE_PWD_RESET.format(
                acc_name, password, access_key, secret_key)
        else:
            cmd = commands.CREATE_ACC_RROFILE_NO_PWD_RESET.format(
                acc_name, password, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def update_account_login_profile_s3iamcli(
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
        :return: update account login profile s3iamcli response.
        """
        if password_reset:
            cmd = commands.UPDATE_ACC_PROFILE_RESET.format(
                acc_name, password, access_key, secret_key)
        else:
            cmd = commands.UPDATE_ACC_PROFILE_NO_RESET.format(
                acc_name, password, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def get_account_login_profile_s3iamcli(
            acc_name: str = None,
            access_key: str = None,
            secret_key: str = None) -> tuple:
        """
        Get account login profile using s3iamcli.

        :param acc_name: s3 account name.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :return: get account login profile s3iamcli response.
        """
        cmd = commands.GET_ACC_PROFILE.format(acc_name, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def update_user_login_profile_s3iamcli(
            user_name: str = None,
            password: str = None,
            password_reset: bool = False,
            access_key: str = None,
            secret_key: str = None) -> tuple:
        """
        Update user login profile using s3iamcli.

        :param user_name: s3 user name.
        :param password: s3 password.
        :param password_reset: password reset.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :return: update user login profile s3iamcli response.
        """
        if password_reset:
            cmd = commands.UPDATE_USR_PROFILE_RESET.format(
                user_name, password, access_key, secret_key)
        else:
            cmd = commands.UPDATE_ACC_PROFILE.format(
                user_name, password, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def get_user_login_profile_s3iamcli(
            user_name: str = None,
            access_key: str = None,
            secret_key: str = None) -> tuple:
        """
        Get user login profile using s3iamcli.

        :param user_name: s3 user name.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :return: get user login profile s3iamcli response.
        """
        cmd = commands.GET_USRLOGING_PROFILE.format(
            user_name, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def create_user_login_profile_s3iamcli_with_both_reset_options(
            user_name: str = None,
            password: str = None,
            access_key: str = None,
            secret_key: str = None,
            both_reset_options: bool = False) -> tuple:
        """
        Create user login profile using s3iamcli with both reset options.

        :param user_name: s3 user name.
        :param password: s3 password.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :param both_reset_options: reset both options.
        :return: create user login profile s3iamcli with both reset options response.
        """
        LOGGER.info(both_reset_options)
        if both_reset_options:
            cmd = commands.CREATE_USR_LOGIN_PROFILE_NO_RESET.format(
                user_name, password, access_key, secret_key)
        else:
            cmd = commands.CREATE_USR_LOGIN_PROFILE.format(
                user_name, password, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def reset_account_access_key_s3iamcli(
            account_name: str = None,
            ldap_user_id: str = None,
            ldap_password: str = None) -> tuple:
        """
        Reset account access key using aws s3iamcli.

        :param account_name: s3 account name.
        :param ldap_user_id: s3 ldap user id.
        :param ldap_password: s3 ldap password.
        :return: reset account access key s3iamcli response.
        """
        cmd = commands.RESET_ACCESS_ACC.format(
            account_name, ldap_user_id, ldap_password)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug(result)

        return result

    @staticmethod
    def create_user_using_s3iamcli(
            user_name: str = None,
            access_key: str = None,
            secret_key: str = None) -> tuple:
        """
        Creating user using s3iamcli.

        :param user_name: s3 user name.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :return: create user using s3iamcli response.
        """
        cmd = commands.CREATE_ACC_USR_S3IAMCLI.format(
            user_name, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def create_account_login_profile_both_reset_options(
            acc_name: str = None, password: str = None, access_key: str = None,
            secret_key: str = None) -> tuple:
        """
        Create account login profile using s3iamcli.

        :param acc_name: s3 account name.
        :param password: s3 password.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :return: create account login profile both reset options.
        """
        cmd = commands.CREATE_ACC_RROFILE_WITH_BOTH_RESET.format(
            acc_name, password, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def create_acc_login_profile_without_both_reset_options(
            acc_name: str = None, password: str = None,
            access_key: str = None, secret_key: str = None) -> tuple:
        """
        Create account login profile using s3iamcli.

        :param acc_name: s3 account name.
        :param password: s3 password.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :return: create acc login profile without both reset options response.
        """
        cmd = commands.CREATE_ACC_PROFILE_WITHOUT_BOTH_RESET.format(
            acc_name, password, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def update_account_login_profile_both_reset_options(
            acc_name: str = None,
            access_key: str = None,
            secret_key: str = None,
            password: str = None) -> tuple:
        """
        Update account login profile using s3iamcli.

        :param acc_name: s3 account name.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :param password: s3 password.
        :return: update account login profile both reset options response.
        """
        if password:
            cmd = commands.UPDATE_ACC_PROFILE_BOTH_RESET.format(
                acc_name, password, access_key, secret_key)
        else:
            cmd = commands.UPDATE_ACC_LOGIN_PROFILE.format(
                acc_name, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def update_user_login_profile_without_password_and_reset_option(
            user_name: str = None, access_key: str = None, secret_key: str = None) -> tuple:
        """
        Update user login profile using s3iamcli without password and reset options.

        :param user_name: s3 user name.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :return: update user login profile without password and reset option response.
        """
        cmd = commands.UPDATE_USR_LOGIN_PROFILE.format(
            user_name, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def get_temp_auth_credentials_account(
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
        if duration is not None:
            cmd = commands.GET_TEMP_ACC_DURATION.format(
                account_name, account_password, duration)
        else:
            cmd = commands.GET_TEMP_ACC.format(account_name, account_password)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def get_temp_auth_credentials_user(
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
        if duration is not None:
            cmd = commands.GET_TEMP_USR_DURATION.format(
                account_name, user_name, password, duration)
        else:
            cmd = commands.GET_TEMP_USR.format(
                account_name, user_name, password)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def change_user_password(
            old_pwd: str = None,
            new_pwd: str = None,
            access_key: str = None,
            secret_key: str = None) -> tuple:
        """
        Change password for IAM user.

        :param old_pwd: old password.
        :param new_pwd: new password.
        :param access_key: s3 access key.
        :param secret_key: s3 secret key.
        :return: change user password response.
        """
        cmd = commands.CMD_CHANGE_PWD.format(
            old_pwd, new_pwd, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def update_user_login_profile_s3iamcli_with_both_reset_options(
            user_name: str = None, password: str = None, access_key: str = None,
            secret_key: str = None) -> tuple:
        """
        Update user login profile using both password reset options.

        :param user_name: Name of user.
        :param password: User password.
        :param access_key: Access key of user.
        :param secret_key: Secret key of user.
        :return: update user login profile s3iamcli with both reset options response.
        """
        cmd = commands.UPDATE_USR_PROFILE_BOTH_RESET.format(
            user_name, password, access_key, secret_key)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result

    @staticmethod
    def delete_account_s3iamcli_using_temp_creds(account_name: str = None,
                                                 access_key: str = None,
                                                 secret_key: str = None,
                                                 session_token: str = None,
                                                 force: bool = False) -> tuple:
        """
        Deleting a specified account using it's temporary credentials.

        :param account_name: Name of an account to be deleted.
        :param access_key: Temporary access key of an account.
        :param secret_key: Temporary secret key of an account.
        :param session_token: Temporary session token of an account.
        :param force: --force option used while deleting an account.
        :return: Delete account response.
        """
        if force:
            cmd = commands.DEL_ACNT_USING_TEMP_CREDS_FORCE.format(
                account_name, access_key, secret_key, session_token)
        else:
            cmd = commands.DEL_ACNT_USING_TEMP_CREDS.format(
                account_name, access_key, secret_key, session_token)
        LOGGER.info(cmd)
        result = run_local_cmd(cmd)
        LOGGER.debug("output = %s", str(result))

        return result
