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

"""
Cortxcli Test Library.

This module consists of following classes
CortxCliTestLib  is a Public class and can be used to create objects and using
functionality of Account, Bucket, User and AccessKey related operations.

Below classes are protected and private and need to be used for internal purpose
S3AccountOperations,
S3BucketOperations,
IamUser,
S3AccessKey
"""

import logging
from commons import errorcodes as err
from commons.exceptions import CTException

from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser
from libs.csm.cli.cortx_cli_s3access_keys import CortxCliS3AccessKeys

LOGGER = logging.getLogger(__name__)


class S3AccountOperations(CortxCliS3AccountOperations):
    """Overriding class for S3 Account Operations.

    This is a subclass to use functionality of S3 Account Operations.
    Class is open for extension.
    """

    def __init__(
            self, session_obj: object = None):
        """Constructor for s3 account operations."""
        super().__init__(session_obj=session_obj)

    def create_account_cortxcli(self,
                                account_name: str,
                                account_email: str,
                                password: str,
                                **kwargs) -> tuple:
        """
        Creating new account using  cortxcli.

        :param password:
        :param account_email:
        :param account_name: s3 account name.
        :return: create account cortxcli response.
        """
        acc_details = dict()
        try:
            self.login_cortx_cli()
            status, response = super().create_s3account_cortx_cli(
                account_name, account_email, password, **kwargs)
            if account_name in response:
                response = self.split_table_response(response)[0]
                acc_details["account_name"] = response[1]
                acc_details["account_email"] = response[2]
                acc_details["account_id"] = response[3]
                acc_details["canonical_id"] = response[4]
                acc_details["access_key"] = response[5]
                acc_details["secret_key"] = response[6]
                LOGGER.info("Account Details: %s", acc_details)
                response = acc_details
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3AccountOperations.create_account_cortxcli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])
        finally:
            self.logout_cortx_cli()

        return status, response

    def list_accounts_cortxcli(self, output_format='json') -> tuple:
        """
        Listing accounts using  cortxcli.

        :return: list account cortxcli response.
        """
        try:
            self.login_cortx_cli()
            status, response = super().show_s3account_cortx_cli(output_format=output_format)
            if status:
                accounts = self.format_str_to_dict(input_str=response)["s3_accounts"]
            else:
                accounts = dict()
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3AccountOperations.list_accounts_cortxcli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])
        finally:
            self.logout_cortx_cli()
        return accounts

    def delete_account_cortxcli(self,
                                account_name: str,
                                password: str) -> tuple:
        """
        Deleting account using cortxcli.

        :param password:
        :param account_name: s3 account name.
        :return:
        """
        try:
            self.login_cortx_cli(username=account_name, password=password)
            response = super().delete_s3account_cortx_cli(account_name)

        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3AccountOperations.delete_account_cortxcli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])
        finally:
            self.logout_cortx_cli()
        return response

    def reset_s3_account_password(
            self,
            account_name: str,
            old_password: str,
            new_password: str,
            **kwargs) -> tuple:
        """
        Function will update password for specified s3 account to new_password using CORTX CLI.

        :param account_name: Name of the s3 account whose password is to be update
        :param old_password: original password
        :param new_password: New password for s3 account
        :keyword reset_password: Y/n
        :return: True/False and Response returned by CORTX CLI
        """
        # inherit from csm cli
        try:
            self.login_cortx_cli(username=account_name, password=old_password)
            response = super().reset_s3account_password(account_name,
                                                        new_password,
                                                        **kwargs)
        except Exception as error:
            LOGGER.error(
                "Error in %s:%s",
                S3AccountOperations.reset_s3account_password.__name__,
                error)
            raise CTException(err.S3_ERROR, error.args[0])
        finally:
            self.logout_cortx_cli()
        return response


class IamUser(CortxCliIamUser):
    """Overriding class for cortxcli Iam User.

    class is open for future Implementation and Extension.
    """

    def __init__(
            self, session_obj: object = None):
        """Constructor for Iam user operations.

        :param object session_obj: session object of host connection if already established
        """
        super().__init__(session_obj=session_obj)

    def create_user_cortxcli(self,
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
                         IamUser.create_user_cortxcli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return response

    def list_users_cortxcli(self) -> tuple:
        """
        Listing users using  cortxcli.

        :return: list users cortxcli response.
        """
        try:
            status, response = super().list_iam_user()
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         IamUser.list_users_cortxcli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return status, response

    def delete_user_cortxcli(self, user_name) -> tuple:
        """
        Listing users using  cortxcli.

        :return: list users cortxcli response.
        """
        try:
            status, response = super().delete_iam_user(user_name)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         IamUser.delete_user_cortxcli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return status, response


class S3AccessKeys(CortxCliS3AccessKeys):
    """This class has all s3 access key operations."""

    def __init__(self, session_obj: object = None):
        """
        Method initializes members of CortxCliS3AccessKeys.

        :param object session_obj: session object of host connection if already established
        """
        super().__init__(session_obj=session_obj)

    def create_s3user_access_key_cortx_cli(
            self,
            user_name: str) -> tuple:
        """
        Function will create a bucket using CORTX CLI.

        :param user_name: for whon access key needs to be created.
        :return: True/False and response returned by CORTX CLI
        """
        try:
            status, response = super().create_s3_iam_access_key(user_name)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3AccessKeys.create_s3user_access_key_cortx_cli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return status, response

    def show_s3user_access_key_cortx_cli(
            self,
            user_name: str) -> tuple:
        """
        Function will show s3 user access keys using CORTX CLI.

        :param user_name: for whom the access key needs to be listed
        :return: True/False and response returned by CORTX CLI
        """
        try:
            status, response = super().show_s3access_key(user_name)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3AccessKeys.show_s3user_access_key_cortx_cli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return status, response

    def update_s3user_access_key_cortx_cli(
            self,
            user_name: str,
            access_key: str,
            status: str) -> tuple:
        """
        Function will update a access key using CORTX CLI.

        :param status: Status for update access key
                        (possible values: Active/Inactive)
        :param access_key: which need to be updated
        :param user_name: for whom access key needs to be updated.
        :return: True/False and response returned by CORTX CLI
        """
        try:
            status, response = super().update_s3access_key(user_name, access_key, status)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3AccessKeys.update_s3user_access_key_cortx_cli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return status, response

    def delete_s3user_access_key_cortx_cli(
            self,
            user_name: str) -> tuple:
        """
        Function will delete a user access key using CORTX CLI.

        :param user_name: user name for whom access key will be created.
        :return: True/False and response returned by CORTX CLI
        """
        try:
            status, response = super().delete_s3access_key(user_name)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3AccessKeys.update_s3user_access_key_cortx_cli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return status, response


class S3BucketOperations(CortxCliS3BucketOperations):
    """Overriding class for cortxcli s3 bucket operations.

    This class is used to have s3 Bucket Operations.
    """

    def __init__(
            self, session_obj: object = None):
        """Constructor for s3 bucket operations.

        :param object session_obj: session object of host connection if already established.
        """
        super().__init__(session_obj=session_obj)

    def create_bucket_cortx_cli(
            self,
            bucket_name: str) -> tuple:
        """
        Function will create a bucket using CORTX CLI.

        :param bucket_name: New bucket's name
        :return: True/False and response returned by CORTX CLI
        """
        try:
            response = super().create_bucket_cortx_cli(bucket_name)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3BucketOperations.create_bucket_cortx_cli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return response

    def list_bucket_cortx_cli(
            self,
            op_format: str = "sjon") -> tuple:
        """
        Function will create a bucket using CORTX CLI.

        :param op_format:
        :return: True/False and response returned by CORTX CLI
        """
        try:
            response = super().list_buckets_cortx_cli(op_format=op_format)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3BucketOperations.list_bucket_cortx_cli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return response

    def delete_bucket_cortx_cli(
            self,
            bucket_name: str) -> tuple:
        """
        Function will delete a bucket using CORTX CLI.

        :param bucket_name: New bucket's name
        :return: True/False and response returned by CORTX CLI
        """
        try:
            response = super().delete_bucket_cortx_cli(bucket_name)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         S3BucketOperations.delete_bucket_cortx_cli.__name__,
                         error)
            raise CTException(err.S3_ERROR, error.args[0])

        return response


class CortxCliTestLib(S3AccountOperations,
                      S3BucketOperations,
                      IamUser,
                      S3AccessKeys):
    """Class for performing cortxcli operations."""

    def __init__(
            self, session_obj: object = None):
        """Constructor for cortxcli test library.

        :param object session_obj: session object of host connection if already established.
        This class establish the session as soon as object is created.
        """
        super().__init__(session_obj=session_obj)
        self.open_connection()

    def __del__(self):
        """closing established connection."""
        self.close_connection()

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
