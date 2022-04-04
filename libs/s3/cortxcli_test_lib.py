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
import time

from config import CMN_CFG
from commons import errorcodes as err
from commons.exceptions import CTException
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cortx_cli_s3_buckets import CortxCliS3BucketOperations
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser
from libs.csm.cli.cortx_cli_s3access_keys import CortxCliS3AccessKeys
from libs.csm.cli.cli_csm_user import CortxCliCsmUser

LOGGER = logging.getLogger(__name__)


class CSMAccountOperations(CortxCliCsmUser, CortxCliS3AccountOperations):
    """Overriding class for csm user operations."""

    def __init__(self, session_obj: object = None):
        """Constructor for s3 account operations."""
        if CMN_CFG["product_type"] != "node":
            raise Exception("cortxcli command not supported in the k8s. Please, use rest api.")
        super().__init__(session_obj=session_obj)
        self.open_connection()

    def __del__(self):
        """closing established connection."""
        self.close_connection()

    def csm_user_create(self, username, email, password, role="manage"):
        """
        Creating new csm user using cortxcli.

        :param role: csm user role(manage, admin, monitor)
        :param password:  Password of the csm user.
        :param email: Email of the csm user.
        :param username: Name of the csm user.
        :return: create account cortxcli response.
        """
        try:
            start = time.perf_counter()
            self.login_cortx_cli()
            status, response = super().create_csm_user_cli(csm_user_name=username,
                                                           email_id=email,
                                                           password=password,
                                                           confirm_password=password,
                                                           role=role)
            self.log.info(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CSMAccountOperations.csm_user_create.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args)
        finally:
            self.logout_cortx_cli()
            end = time.perf_counter()
        self.log.info("Total Time in seconds for Creating csm account is: %s", str(end - start))

        return status, response

    def csm_user_update_role(self, user_name, password, role):
        """
        Function will update role of user.

        :param user_name: Name of a csm user whose role to be updated.
        :param role: Role to be updated.
        :param password: Current password.
        """
        try:
            self.login_cortx_cli()
            response = super().update_role(user_name=user_name, role=role,
                                           current_password=password, confirm="Y")
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CSMAccountOperations.csm_user_update_role.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args)
        finally:
            self.logout_cortx_cli()

        return response

    def csm_user_delete(self, user_name: str) -> tuple:
        """
        Deleting csm user using cortxcli.

        :param user_name: csm user name.
        :return: delete user response.
        """
        try:
            self.login_cortx_cli()
            response = super().delete_csm_user(user_name)
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CSMAccountOperations.csm_user_delete.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args)
        finally:
            self.logout_cortx_cli()

        return response

    def csm_user_list_s3accounts(self, csm_user=None, passwd=None):
        """
        Listing s3accounts using csm user(default with admin role).

        :param csm_user: Name of the csm user.
        :param passwd: password of the csm user.
        return True/False, Response s3 accounts dict.
        """
        try:
            accounts = {}
            if csm_user:
                self.login_cortx_cli(username=csm_user, password=passwd)
            else:
                self.login_cortx_cli()
            status, response = super().show_s3account_cortx_cli(output_format='json')
            if status:
                accounts = self.format_str_to_dict(input_str=response)["s3_accounts"]
            LOGGER.debug(accounts)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CSMAccountOperations.csm_user_list_s3accounts.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args)
        finally:
            self.logout_cortx_cli()

        return status, accounts

    def csm_user_show_s3accounts(self, csm_user=None, passwd=None):
        """
        Show s3accounts using csm user(default with admin role).

        :param csm_user: Name of the csm user.
        :param passwd: password of the csm user.
        return True/False, Response s3 accounts dict.
        """
        try:
            if csm_user:
                self.login_cortx_cli(username=csm_user, password=passwd)
            else:
                self.login_cortx_cli()
            status, response = super().show_s3account_cortx_cli(output_format='json')
            if status:
                accounts = self.format_str_to_dict(input_str=response)
            else:
                accounts = {}
            LOGGER.debug(accounts)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CSMAccountOperations.csm_user_show_s3accounts.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args)
        finally:
            self.logout_cortx_cli()

        return status, accounts

    def csm_user_create_s3account(self, s3_user, email, s3_passwd, **kwargs):
        """
        Create s3 account user using csm user(default with admin role).

        :param csm_user: Name of the csm user.
        :param passwd: password of the csm user.
        :param s3_user: Name of the s3 account user.
        :param email: Email id of the s3 account user.
        :param s3_passwd: Password of the s3 account user.
        return True/False, Response.
        """
        csm_user = kwargs.get("csm_user", None)
        passwd = kwargs.get("passwd", None)
        try:
            acc_details = {}
            if csm_user:
                self.login_cortx_cli(username=csm_user, password=passwd)
            else:
                self.login_cortx_cli()
            status, response = super().create_s3account_cortx_cli(
                account_name=s3_user, account_email=email, password=s3_passwd)
            if s3_user in response:
                response = self.split_table_response(response)[0]
                acc_details["account_name"] = response[0]
                acc_details["account_email"] = response[1]
                acc_details["account_id"] = response[2]
                acc_details["canonical_id"] = response[3]
                acc_details["access_key"] = response[4]
                acc_details["secret_key"] = response[5]
                LOGGER.info("Account Details: %s", acc_details)
                response = acc_details
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CSMAccountOperations.csm_user_create_s3account.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args)
        finally:
            self.logout_cortx_cli()

        return status, response

    def csm_user_delete_s3account(self, s3_user, csm_user=None, passwd=None):
        """
        Delete s3 account user using csm user(default with admin role).

        :param csm_user: Name of the csm user.
        :param passwd: password of the csm user.
        :param s3_user: Name of the s3 account user.
        return True/False, Response.
        """
        try:
            if csm_user:
                self.login_cortx_cli(username=csm_user, password=passwd)
            else:
                self.login_cortx_cli()
            status, response = super().delete_s3account_cortx_cli(account_name=s3_user)
            LOGGER.debug(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CSMAccountOperations.csm_user_delete_s3account.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args)
        finally:
            self.logout_cortx_cli()

        return status, response

    def csm_users_list(self) -> tuple:
        """
        Listing accounts using  cortxcli.

        :return: True/False and Response dict.
        """
        try:
            self.login_cortx_cli()
            status, response = super().list_csm_users(op_format='json')
            if status:
                accounts = response["users"]
            else:
                accounts = {}
            LOGGER.info(accounts)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CSMAccountOperations.csm_users_list.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args)
        finally:
            self.logout_cortx_cli()

        return status, accounts

    def reset_user_password(self, csm_user=None, passwd=None, new_password=None) -> tuple:
        """
        Reset csm user password.

        :param csm_user: Name of the csm user.
        :param passwd: password of the csm user.
        :param new_password: New password of the account.
        :return: True/False and Response.
        """
        try:
            if csm_user:
                self.login_cortx_cli(username=csm_user, password=passwd)
            else:
                self.login_cortx_cli()
            response = super().reset_root_user_password(csm_user, passwd, new_password)
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CSMAccountOperations.reset_s3acc_password.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args)
        finally:
            self.logout_cortx_cli()

        return response

    def reset_s3acc_password(self, csm_user=None, passwd=None, acc_name=None,
                             new_password=None) -> tuple:
        """
        Reset account password using csm user.

        :param csm_user: Name of the csm user.
        :param passwd: password of the csm user.
        :param acc_name: Name of the account.
        :param new_password: New password of the account.
        :return: True/False and Response.
        """
        try:
            if csm_user:
                self.login_cortx_cli(username=csm_user, password=passwd)
            else:
                self.login_cortx_cli()
            response = super().reset_s3account_password(account_name=acc_name,
                                                        new_password=new_password)
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CSMAccountOperations.reset_s3acc_password.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args)
        finally:
            self.logout_cortx_cli()

        return response

    def reset_s3acc_own_password(self, acc_name, old_password, new_password) -> tuple:
        """
        Reset account password with it's own password.

        :param acc_name: Name of the accounts.
        :param old_password: Old password of the account.
        :param new_password: New password of the account.
        :return: True/False and Response.
        """
        try:
            self.login_cortx_cli(username=acc_name, password=old_password)
            response = super().reset_s3account_password(account_name=acc_name,
                                                        new_password=new_password)
            LOGGER.info(response)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         CSMAccountOperations.reset_s3acc_own_password.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args)
        finally:
            self.logout_cortx_cli()

        return response


class _S3AccountOperations(CortxCliS3AccountOperations):
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
        acc_details = {}
        try:
            start = time.perf_counter()
            self.login_cortx_cli()
            kwargs.setdefault("sleep_time", 10)
            status, response = super().create_s3account_cortx_cli(
                account_name, account_email, password, **kwargs)
            if account_name in response:
                response = self.split_table_response(response)[0]
                acc_details["account_name"] = response[0]
                acc_details["account_email"] = response[1]
                acc_details["account_id"] = response[2]
                acc_details["canonical_id"] = response[3]
                acc_details["access_key"] = response[4]
                acc_details["secret_key"] = response[5]
                LOGGER.info("Account Details: %s", acc_details)
                response = acc_details
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         _S3AccountOperations.create_account_cortxcli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])
        finally:
            self.logout_cortx_cli()
            end = time.perf_counter()
        self.log.info("Total Time in seconds for Creating Account is: %s", str(end - start))
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
                accounts = {}
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         _S3AccountOperations.list_accounts_cortxcli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])
        finally:
            self.logout_cortx_cli()
        return accounts

    def delete_account_cortxcli(self,
                                account_name: str,
                                password: str = None) -> tuple:
        """
        Deleting account using cortxcli.

        :param password:
        :param account_name: s3 account name.
        :return:
        """
        try:
            if password:
                self.login_cortx_cli(username=account_name, password=password)
            else:
                self.login_cortx_cli()
            response = super().delete_s3account_cortx_cli(account_name)

        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         _S3AccountOperations.delete_account_cortxcli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])
        finally:
            self.logout_cortx_cli()
        return response

    def reset_s3_account_password(
            self,
            account_name: str = None,
            old_password: str = None,
            new_password: str = None,
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
            if old_password:
                self.login_cortx_cli(username=account_name, password=old_password)
            else:
                self.login_cortx_cli()
            response = super().reset_s3account_password(account_name,
                                                        new_password,
                                                        **kwargs)
        except Exception as error:
            LOGGER.error(
                "Error in %s:%s",
                _S3AccountOperations.reset_s3account_password.__name__,
                error)
            raise CTException(err.CLI_ERROR, error.args[0])
        finally:
            self.logout_cortx_cli()
        return response


class _IamUser(CortxCliIamUser):
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
        user_details = {}
        confirm_password = confirm_password if confirm_password else password
        try:
            kwargs.setdefault("sleep_time", 10)
            status, response = super().create_iam_user(
                user_name=user_name,
                password=password,
                confirm_password=confirm_password,
                **kwargs)
            if status and user_name in response:
                response = self.split_table_response(response)[0]
                user_details["user_name"] = response[0]
                user_details["user_id"] = response[1]
                user_details["arn"] = response[2]
                response = user_details
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         _IamUser.create_user_cortxcli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])

        return status, response

    def list_users_cortxcli(self) -> tuple:
        """
        Listing users using  cortxcli.

        :return: list users cortxcli response.
        """
        try:
            status, response = super().list_iam_user()
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         _IamUser.list_users_cortxcli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])

        return status, response

    def reset_iamuser_password_cortxcli(self,
                                        iamuser_name: str,
                                        new_password: str) -> tuple:
        """
        Update iam user password to new password using CORTX CLI.

        :param iamuser_name: IAM user name for which password should be updated
        :param new_password: New password for IAM user
        :return: True/False and Response returned by CORTX CLI
        """
        try:
            status, response = super().reset_iamuser_password(iamuser_name, new_password)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         _IamUser.reset_iamuser_password_cortxcli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])

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
                         _IamUser.delete_user_cortxcli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])

        return status, response


class _S3AccessKeys(CortxCliS3AccessKeys):
    """This class has all s3 access key operations."""

    def __init__(self, session_obj: object = None):
        """
        Method initializes members of CortxCliS3AccessKeys.

        :param object session_obj: session object of host connection if already established
        """
        super().__init__(session_obj=session_obj)

    def create_s3_user_access_key(self, user_name: str, passwd: str, s3user: str) -> tuple:
        """
        Function will create a s3 account access key.

        :param user_name: Name of the user own s3 user.
        :param passwd: Password of the user own s3 user.
        :param s3user: For whom access key needs to be created.
        :return: True/False and response.
        """
        try:
            self.login_cortx_cli(username=user_name, password=passwd)
            status, response = self.create_s3user_access_key(s3user)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         _S3AccessKeys.create_s3_user_access_key.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])
        finally:
            self.logout_cortx_cli()

        return status, response

    def show_s3_user_access_key(self, user_name: str, passwd: str, s3user: str) -> tuple:
        """
        Function will show a s3 account access key.

        :param user_name: Name of the user own s3 user.
        :param passwd: Password of the user own s3 user.
        :param s3user: For whom access key needs to be created.
        :return: True/False and dictionary.
        """
        try:
            self.login_cortx_cli(username=user_name, password=passwd)
            status, response = self.show_s3user_access_key(s3user)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         _S3AccessKeys.show_s3_user_access_key.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])
        finally:
            self.logout_cortx_cli()

        return status, response

    def create_s3user_access_key_cortx_cli(
            self,
            user_name: str) -> tuple:
        """
        Function will create a bucket using CORTX CLI.

        :param user_name: for whom access key needs to be created.
        :return: True/False and response returned by CORTX CLI
        """
        try:
            status, response = super().create_s3_iam_access_key(user_name)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         _S3AccessKeys.create_s3user_access_key_cortx_cli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])

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
                         _S3AccessKeys.show_s3user_access_key_cortx_cli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])

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
                         _S3AccessKeys.update_s3user_access_key_cortx_cli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])

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
                         _S3AccessKeys.update_s3user_access_key_cortx_cli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])

        return status, response


class _S3BucketOperations(CortxCliS3BucketOperations):
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
                         _S3BucketOperations.create_bucket_cortx_cli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])

        return response

    def list_bucket_cortx_cli(
            self,
            op_format: str = "json") -> tuple:
        """
        Function will create a bucket using CORTX CLI.

        :param op_format:
        :return: True/False and response returned by CORTX CLI
        """
        try:
            response = super().list_buckets_cortx_cli(op_format=op_format)
        except Exception as error:
            LOGGER.error("Error in %s: %s",
                         _S3BucketOperations.list_bucket_cortx_cli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])

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
                         _S3BucketOperations.delete_bucket_cortx_cli.__name__,
                         error)
            raise CTException(err.CLI_ERROR, error.args[0])

        return response


class CortxCliTestLib(_S3AccountOperations,
                      _S3BucketOperations,
                      _IamUser,
                      _S3AccessKeys):
    """Class for performing cortxcli operations."""

    def __init__(
            self, session_obj: object = None):
        """Constructor for cortxcli test library.

        :param object session_obj: session object of host connection if already established.
        This class establish the session as soon as object is created.
        """
        if CMN_CFG["product_type"] != "node":
            raise Exception("cortxcli command not supported in the k8s. Please, use rest api.")
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
            raise CTException(err.CLI_ERROR, error.args[0])

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
            raise CTException(err.CLI_ERROR, error.args[0])

        return response
