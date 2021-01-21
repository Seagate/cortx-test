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

# IAM test helper library which contains admin_path operations.

import time
import logging
import boto3

from commons.constants import const
from commons import errorcodes as err
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.helpers.s3_helper import S3Helper
from commons.utils.system_utils import format_iam_resp
from libs.s3.s3_core_lib import S3Lib
from libs.s3.iam_core_lib import IamLib, S3IamCli
from libs.s3.s3_acl_test_lib import S3AclTestLib

try:
    s3hobj = S3Helper()
except ImportError as err:
    s3hobj = S3Helper.get_instance()

s3_conf = read_yaml("config/s3/s3_config.yaml")[1]
cmn_conf = read_yaml("config/common_config.yaml")[1]
logger = logging.getLogger(__name__)

ACC_ACCESS_KEY = ""
ACC_SECRET_KEY = ""
LDAP_USERNAME = const.S3_BUILD_VER[cmn_conf["BUILD_VER_TYPE"]]["ldap_creds"]["ldap_username"]
LDAP_PASSWD = const.S3_BUILD_VER[cmn_conf["BUILD_VER_TYPE"]]["ldap_creds"]["ldap_passwd"]


class IamTestLib(IamLib, S3IamCli):
    """
    Test Class for performing IAM related operations
    """

    def __init__(self,
                 access_key: str = s3hobj.get_local_keys()[0],
                 secret_key: str = s3hobj.get_local_keys()[1],
                 endpoint_url: str = s3_conf["iam_url"],
                 iam_cert_path: str = s3_conf["iam_cert_path"],
                 debug: bool = s3_conf["debug"]
                 ) -> None:
        """
        This method initializes members of IamTestLib and its parent class.
        :param access_key: access key.
        :param secret_key: secret key.
        :param endpoint_url: endpoint url.
        :param iam_cert_path: iam certificate path.
        :param debug: debug mode.
        """
        super(IamTestLib, self).__init__(access_key, secret_key, endpoint_url, iam_cert_path, debug)

    def create_user(self, user_name: str) -> tuple:
        """
        Creating new user.
        :param user_name: Name of the user.
        :return: (Boolean, response).
        """
        try:
            logger.info("Creating new user using boto3")
            response = super().create_user(user_name)
            # Adding sleep in sec due to ldap sync issue EOS-6783
            time.sleep(s3_conf["create_user_delay"])
            logger.info(response)
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_user.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def list_users(self) -> tuple:
        """
        List the users in current account
        :return: (Boolean, response)
        """
        try:
            logger.info("listing all users")
            response = super().list_users()["Users"]
            logger.info(response)
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.list_users.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def create_access_key(self, user_name: str) -> tuple:
        """
        Creating access key for given user.
        :param user_name: Name of the user.
        :return: (Boolean, response).
        """
        try:
            logger.info(f"Creating {user_name} user access key.")
            response = super().create_access_key(user_name)
            logger.info(response)
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_access_key.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def delete_access_key(self, user_name: str, access_key_id: str) -> tuple:
        """
        Deleting access key for given user.
        :param user_name: Name of the user.
        :param access_key_id: Access key of the associated user.
        :return: (Boolean, response).
        """
        try:
            logger.info(f"Deleting {user_name} user access key {access_key_id}.")
            response = super().delete_access_key(user_name, access_key_id)
            logger.info(response)
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.delete_access_key.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def delete_user(self, user_name: str) -> tuple:
        """
        Deleting given user.
        :param user_name: Name of the user.
        :return: (Boolean, response).
        """
        try:
            logger.info(f"Delete user {user_name}.")
            response = super().delete_user(user_name)
            logger.info(response)
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.delete_user.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def list_access_keys(self, user_name: str) -> tuple:
        """
        Listing access keys for given user.
        :param user_name: Name of the user.
        :return: (Boolean, response).
        """
        try:
            logger.info(f"list access keys.")
            response = super().list_access_keys(user_name)
            logger.info(response)
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.list_access_keys.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def update_access_key(self, access_key_id: str, status: str, user_name: str) -> tuple:
        """
        Updating access key for given user.
        :param user_name: Name of the user.
        :param access_key_id: Access key of the user.
        :param status: Status of the user Value Active/Inactive.
        :return: (Boolean, response).
        """
        try:
            logger.info(f"Update access key.")
            response = super().update_access_key(access_key_id, status, user_name)
            logger.info(response)
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.update_access_key.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def update_user(self, new_user_name: str, user_name: str) -> tuple:
        """
        Updating given user.
        :param new_user_name: New user name.
        :param user_name: Existing user name.
        :return: (Boolean, response).
        """
        try:
            logger.info(f"Update existing {user_name}user name to {new_user_name}.")
            response = super().update_user(new_user_name, user_name)
            logger.info(response)
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.update_user.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def create_user_login_profile(self, user_name: str, password: str, password_reset: bool = False) -> tuple:
        """
        Create user login profile.
        :param user_name: Name of the user.
        :param password: password for the user login profile.
        :param password_reset: with or without password reset value: True/False.
        :return: (Boolean, response).
        """
        try:
            logger.info(f"Create {user_name} user login profile and password reset is {password_reset}.")
            user_dict = {}
            login_profile = super().create_user_login_profile(user_name, password, password_reset)
            user_dict['user_name'] = login_profile.user_name
            user_dict['create_date'] = login_profile.create_date.strftime("%Y-%m-%d %H:%M:%S")
            user_dict['password_reset_required'] = login_profile.password_reset_required
            logger.debug(user_dict)
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_user_login_profile.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, user_dict

    def update_user_login_profile(self, user_name: str, password: str, password_reset: bool = False) -> tuple:
        """
        Update user login profile.
        :param user_name: Name of the user.
        :param password: password for the user login profile.
        :param password_reset: Password reset value True/False.
        :return: (Boolean, response)
        """
        try:
            logger.info(f"Update {user_name} user login profile with password reset {password_reset}.")
            response = super().update_user_login_profile(user_name, password, password_reset)
            logger.debug(f"{response}")
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.update_user_login_profile.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def update_user_login_profile_no_pwd_reset(self, user_name: str, password: str) -> tuple:
        """
        Update user login profile.
        :param user_name: Name of the user.
        :param password: Password for the user login profile.
        :return: (Boolean, response).
        """
        try:
            logger.info(f"Update {user_name} user login profile with no password reset.")
            response = super().update_user_login_profile_no_pwd_reset(user_name, password)
            logger.info(f"{response}")
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.update_user_login_profile_no_pwd_reset.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def get_user_login_profile(self, user_name: str) -> tuple:
        """
        Get user login profile if exists.
        :param user_name: Name of the user.
        :return: (Boolean, response).
        """
        try:
            logger.info(f"Get {user_name} user login profile details")
            user_dict = {}
            # login_profile = self.iam_resource.LoginProfile(user_name)
            login_profile = super().get_user_login_profile(user_name)
            user_dict['user_name'] = login_profile.user_name
            user_dict['create_date'] = login_profile.create_date.strftime(
                "%Y-%m-%d %H:%M:%S")
            user_dict['password_reset_required'] = login_profile.password_reset_required
            logger.info(user_dict)
        except Exception as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.get_user_login_profile.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, user_dict

    def s3_user_operation(self, user_name: str, bucket_name: str) -> tuple:
        """
        Performing CRUD operations using user access key and secret key.
        :param user_name: Name of the user.
        :param bucket_name: Bucket name.
        :return: (Boolean, response).
        """
        try:
            logger.info("Creating access key for the specified user")
            user_acc_key = super().create_access_key(user_name)
            response = user_acc_key
            acc_key = response["AccessKey"]["AccessKeyId"]
            sec_key = response["AccessKey"]["SecretAccessKey"]
            logger.info("Performing CRUD operations for s3 Data Path")
            # need to check this object
            s3 = S3Lib(acc_key, sec_key, s3_conf["s3_url"], s3_conf["s3_cert_path"], s3_conf["region"])
            op_cb = s3.create_bucket(bucket_name)
            logger.info(op_cb)
            op_bl = s3.bucket_list()
            logger.info(op_bl)
            op_db = s3.delete_bucket(bucket_name)
            logger.info(op_db)
            res = super().delete_access_key(user_name, acc_key)
            logger.info("Access Key deleted successfully: {}".format(res))
            response = {"AccountName": user_name, "BucketName": bucket_name}
        except BaseException as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.s3_user_operation.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def create_modify_delete_access_key(self, user_name: str, status: str) -> tuple:
        """
        Create access key, modify it and delete it.
        :param user_name: Name of the user.
        :param status: Status.
        :return: (Boolean, response).
        """
        try:
            logger.info("Creating access key for the specified user")
            user_acckey = super().create_access_key(user_name)
            response = user_acckey
            acc_key = response["AccessKey"]["AccessKeyId"]
            logger.info("Updating the access key")
            upd_acc_key = super().update_access_key(acc_key, status, user_name)
            logger.debug(upd_acc_key)
            logger.info("Deleting the access key")
            delete_acc_key = super().delete_access_key(user_name, acc_key)
            logger.debug(delete_acc_key)
            logger.info("Listing and Verifying the access key for particular user")
            verify_acc_key = super().list_access_keys(user_name)
            logger.debug(verify_acc_key)
        except BaseException as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_modify_delete_access_key.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, user_name

    @staticmethod
    def s3_ops_using_temp_auth_creds(access_key: str, secret_key: str, session_token: str, bucket_name: str) -> tuple:
        """
        Performing s3 operations such as create and delete bucket using temp auth creds and session token.
        :param access_key: Access key of account/user.
        :param secret_key: Secret key of account/user.
        :param session_token: Session token.
        :param bucket_name: Name of the bucket.
        :return: (Boolean, response)
        """
        logger.info("Performing s3 operations using temp auth credentials.")
        s3_resource = boto3.resource("s3",
                                     verify=s3_conf["s3_cert_path"],
                                     aws_access_key_id=access_key,
                                     aws_secret_access_key=secret_key,
                                     endpoint_url=s3_conf["s3_url"],
                                     region_name=s3_conf["region"],
                                     aws_session_token=session_token
                                     )
        try:
            logger.info("Creating a Bucket")
            bucket = s3_resource.create_bucket(Bucket=bucket_name)
            logger.info("Bucket is Created {0}".format(bucket))
            logger.info("Deleting a bucket")
            bucket = s3_resource.Bucket(bucket_name)
            response = bucket.delete()
            logger.debug(response)
            logger.info("Deleted bucket")
        except BaseException as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.s3_ops_using_temp_auth_creds.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, s3_resource

    def create_multiple_accounts_users(self, access_key: str, secret_key: str, acc_count: str,
                                       user_count: str) -> tuple:
        """
        Create given number of accounts and given number of users per account.
        :param access_key: Access key of account/user.
        :param secret_key: Secret key of account/user.
        :param acc_count: No. of Account to be created.
        :param user_count: No. of users to be created.
        :return: (Boolean, response).
        """
        logger.info(f"Create {acc_count} accounts and {user_count} users")
        acc_li = []
        user_li = []
        for acc in range(int(acc_count)):
            account_name = "testacc{}".format(str(time.time()))
            email = "testacc{}{}".format(str(time.time()), "@seagate.com")
            self.create_account_s3iamcli(account_name, email, LDAP_USERNAME, LDAP_PASSWD)
            acc_li.append(account_name)
            iam_obj = IamLib(access_key=access_key,
                             secret_key=secret_key,
                             endpoint_url=s3_conf["iam_url"],
                             iam_cert_path=s3_conf["iam_cert_path"])
            for user in range(int(user_count)):
                user_name = "testusr{}".format(str(time.time()))
                iam_obj.create_user(user_name)
                user_li.append(user_name)
        logger.debug(len(acc_li), len(user_li))
        if len(acc_li) == int(acc_count) or len(user_li) == int(user_count) * int(acc_count):
            return True, acc_li
        else:
            error = "Failed to create given accounts/users"
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_multiple_accounts_users.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error)

    def list_accounts_s3iamcli(self, ldap_user_id: str, ldap_password: str) -> tuple:
        """
        Listing accounts using aws s3iamcli.
        :param ldap_user_id: ldap server user id.
        :param ldap_password: ldap server user password.
        :return: (Boolean, response)
        """
        logger.info("Listing accounts using aws s3iamcli.")
        # Adding sleep in sec due to ldap sync issue EOS-8121
        time.sleep(s3_conf["list_account_delay"])
        response = super().list_accounts_s3iamcli(ldap_user_id, ldap_password)
        logger.info(response)
        if "error" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.list_accounts_s3iamcli.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, format_iam_resp(response)

    def list_users_s3iamcli(self, access_key: str, secret_key: str) -> tuple:
        """
        Listing users using aws s3iamcli.
        :param access_key: User access key.
        :param secret_key: User secret key.
        :return: (Boolean, response).
        """
        logger.info("Listing users using aws s3iamcli.")
        response = super().list_users_s3iamcli(access_key, secret_key)
        if "error" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.list_users_s3iamcli.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        users_list = list()
        res = response.split("b'")[1].replace("\\n", ",")
        user_name_list = filter(lambda x: "UserName" in x, res.split(','))
        users_list = [{"UserName": i.split('=')[-1].strip(' ')} for i in user_name_list]
        logger.info(users_list)

        return True, response

    def create_account_s3iamcli(self, account_name: str, email_id: str, ldap_user_id: str, ldap_password: str) -> tuple:
        """
        Creating new account using s3iamcli
        :param account_name: Account name
        :param email_id: Email id of the account
        :param ldap_user_id: Ldap user name/ID
        :param ldap_password: Ldap user password
        :return: (Boolean, response)
        """
        logger.info("Create new account using s3iamcli.")
        global ACC_ACCESS_KEY
        ACC_ACCESS_KEY = []
        global ACC_SECRET_KEY
        ACC_SECRET_KEY = []
        result = super().create_account_s3iamcli(account_name, email_id, ldap_user_id, ldap_password)
        # Adding sleep in sec due to ldap sync issue EOS-5924
        time.sleep(s3_conf["create_account_delay"])
        res = result.split("b'")[1].replace("\\n',", "")
        new_result = res.split(',')
        logger.debug(new_result)
        acc_dict = {}
        for i in new_result:
            if "AccessKeyId" in i:
                response = i.split('=')
                ACC_ACCESS_KEY.append(response[1].strip(' '))
                logger.info("Access Key Id : {}".format(ACC_ACCESS_KEY))
                acc_dict['access_key'] = response[1].strip(' ')
            elif "SecretKey" in i:
                response = i.split('=')
                ACC_SECRET_KEY.append(response[1].strip(' '))
                logger.info("Secret Key : {}".format(ACC_SECRET_KEY))
                acc_dict['secret_key'] = response[1].strip(' ')
            elif "CanonicalId" in i:
                response = i.split('=')
                canonical_id = response[1].strip(' ')
                logger.info("CanonicalId : {}".format(canonical_id))
                acc_dict['canonical_id'] = response[1].strip(' ')
            elif "AccountId" in i:
                response = i.split('=')
                canonical_id = response[1].strip(' ')
                logger.info("Account Id : {}".format(canonical_id))
                acc_dict['Account_Id'] = response[1].strip(' ')
        if "Account wasn't created" in result:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_account_s3iamcli.__name__,
                result))
            raise CTException(err.S3_CLIENT_ERROR, result)
        elif "s3iamcli: command not found" in result:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_account_s3iamcli.__name__,
                result))
            raise CTException(err.S3_CLIENT_ERROR, result)

        return True, acc_dict

    def delete_account_s3iamcli(self, account_name: str, access_key: str, secret_key: str, force: bool = True) -> tuple:
        """
        Deleting account using aws s3iamcli.
        :param account_name: Name of the account.
        :param access_key: Account access key.
        :param secret_key: Account secret key.
        :param force: Delete account forcefully value True/False.
        :return: (Boolean, response).
        """
        logger.info(f"Delete account with name {account_name} using s3iamcli")
        response = super().delete_account_s3iamcli(account_name, access_key, secret_key, force)
        # Adding sleep in sec due to ldap sync issue EOS-5924
        time.sleep(s3_conf["delete_account_delay"])
        logger.info(response)
        if "Account cannot be deleted" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.delete_account_s3iamcli.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, response

    def create_user_login_profile_s3iamcli(self, user_name: str, password: str, password_reset: str,
                                           access_key: str, secret_key: str) -> tuple:
        """
        Create user login profile using aws s3iamcli.
        :param user_name: Account user name.
        :param password: User password.
        :param password_reset: Password reset value True/False.
        :param access_key: User access key.
        :param secret_key: User secret key.
        :return: (Boolean, response)
        """
        logger.info("Create user login profile using s3iamcli")
        response = super().create_user_login_profile_s3iamcli(user_name, password, password_reset,
                                                              access_key, secret_key)
        logger.info(response)
        if "Failed" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_user_login_profile_s3iamcli.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, response

    def create_account_login_profile_s3iamcli(self, acc_name: str, password: str, access_key: str,
                                              secret_key: str, password_reset: bool = False) -> tuple:
        """
        Create account login profile using s3iamcli.
        :param acc_name: Account user name.
        :param password: Account password.
        :param access_key: Account access key.
        :param secret_key: Account secret key.
        :param password_reset: Password reset value True/False.
        :return: (Boolean, response).
        """
        logger.info("Create account login profile using s3iamcli")
        response = super().create_account_login_profile_s3iamcli(acc_name, password, access_key,
                                                                 secret_key, password_reset)
        if "Failed" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_account_login_profile_s3iamcli.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, response

    def update_account_login_profile_s3iamcli(self, acc_name: str, password: str, access_key: str,
                                              secret_key: str, password_reset: bool = False) -> tuple:
        """
        Update account login profile using s3iamcli.
        :param acc_name: Account user name.
        :param password: Account password.
        :param access_key: Account access key.
        :param secret_key: Account secret key.
        :param password_reset: Password reset value True/False.
        :return: (Boolean, response)
        """
        logger.info("Update account login profile using s3iamcli")
        response = super().update_account_login_profile_s3iamcli(acc_name, password, access_key,
                                                                 secret_key, password_reset)
        logger.info(response)
        if "Failed" in response or "error" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.update_account_login_profile_s3iamcli.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, response

    def get_account_login_profile_s3iamcli(self, acc_name: str, access_key: str, secret_key: str) -> tuple:
        """
        Get account login profile using s3iamcli.
        :param acc_name: Account user name.
        :param access_key: Account access key.
        :param secret_key: Account secret key.
        :return: (Boolean, response)
        """
        logger.info("Get account login profile using s3iamcli")
        response = super().get_account_login_profile_s3iamcli(acc_name, access_key, secret_key)
        logger.info(response)
        if "Failed" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.get_account_login_profile_s3iamcli.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, format_iam_resp(response)

    def update_user_login_profile_s3iamcli(self, user_name: str, password: str, password_reset: str,
                                           access_key: str, secret_key: str) -> tuple:
        """
        Update user login profile using s3iamcli.
        :param user_name: Account user name.
        :param password: User password.
        :param password_reset: Password reset value True/False.
        :param access_key: User access key.
        :param secret_key: User secret key.
        :return: (Boolean, response)
        """
        try:
            logger.info(f"Update {user_name} user login profile with password reset as {password_reset}")
            response = super().update_user_login_profile_s3iamcli(user_name, password, password_reset, access_key,
                                                                  secret_key)
            logger.info(response)
        except BaseException as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.update_user_login_profile_s3iamcli.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def get_user_login_profile_s3iamcli(self, user_name: str, access_key: str, secret_key: str) -> tuple:
        """
        Get user login profile using s3iamcli.
        :param user_name: Name of the user.
        :param access_key: Access key of the user.
        :param secret_key: Secret key of the user.
        :return: (Boolean, response)
        """
        logger.info(f"Get {user_name} user login profile details.")
        response = super().get_user_login_profile_s3iamcli(user_name, access_key, secret_key)
        if "Failed" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.get_user_login_profile_s3iamcli.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, response

    def create_user_login_profile_s3iamcli_with_both_reset_options(self, user_name: str, password: str,
                                                                   access_key: str, secret_key: str,
                                                                   both_reset_options: bool = False) -> tuple:
        """
        Create user login profile using s3iamcli with both reset options.
        :param user_name: Name of the user.
        :param password: Password for the user login.
        :param access_key: Access key of the user.
        :param secret_key: Secret key of the user.
        :param both_reset_options: both password reset option.
        :return: (Boolean, response)
        """
        logger.info(f"Create {user_name} user login profile with both reset options as {both_reset_options}.")
        response = super().create_user_login_profile_s3iamcli_with_both_reset_options(user_name, password,
                                                                                      access_key, secret_key,
                                                                                      both_reset_options)
        if "Failed" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_user_login_profile_s3iamcli_with_both_reset_options.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, response

    def reset_account_access_key_s3iamcli(self, account_name: str, ldap_user_id: str, ldap_password: str) -> tuple:
        """
        Resets account access key using aws s3iamcli.
        :param account_name: Name of the account.
        :param ldap_user_id: Ldap user name.
        :param ldap_password: Ldap user password.
        :return: (Boolean, response).
        """
        logger.info(f"Reset {account_name} access key using s3iamcli.")
        resp = super().reset_account_access_key_s3iamcli(account_name, ldap_user_id, ldap_password)
        time.sleep(s3_conf["reset_account_access_key_delay"])
        logger.info(resp)
        if "Account access key wasn't reset" in resp:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.reset_account_access_key_s3iamcli.__name__,
                resp))
            raise CTException(err.S3_CLIENT_ERROR, resp)

        result = resp.split("b'")[1].replace("\\n',", "")
        new_result = result.split(",")
        acc_dict = {}
        for item in new_result:
            response = item.split("=")
            acc_dict[response[0].strip(" ")] = response[1].strip(" ")
        logger.debug("output = {}".format(acc_dict))

        return True, acc_dict

    def create_user_using_s3iamcli(self, user_name: str, access_key: str, secret_key: str) -> tuple:
        """
        Creating user using s3iamcli.
        :param user_name: Name of the user.
        :param access_key: User access key.
        :param secret_key: User secret key.
        :return: (Boolean, Response)
        """
        logger.info(f"Create {user_name} user using s3iamcli")
        user_data = {}
        result = super().create_user_using_s3iamcli(user_name, access_key, secret_key)
        # Adding sleep in ms due to ldap sync issue EOS-6783
        time.sleep(s3_conf["create_user_delay"])
        if "Failed" in result:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_user_using_s3iamcli.__name__,
                result))
            raise CTException(err.S3_CLIENT_ERROR, result)

        res = result.split("b'")[1].replace("\\n',", "")
        new_result = res.split(",")
        logger.info(new_result)
        for i in new_result:
            if "UserId" in i:
                response = i.split("=")
                user_data["User Id"] = response[1].strip(" ")
                logger.debug("User Id : {}".format(user_data["User Id"]))
            elif "ARN" in i:
                response = i.split("=")
                user_data["ARN"] = response[1].strip(" ")
                logger.debug("ARN : {}".format(user_data["ARN"]))

        return True, user_data

    def create_account_login_profile_both_reset_options(self, acc_name: str, password: str,
                                                        access_key: str, secret_key: str) -> tuple:
        """
        Create account login profile using s3iamcli.
        :param acc_name: Name of the account.
        :param password: Password for the account login.
        :param access_key: Access key of the account.
        :param secret_key: Secret key of the account.
        :return: (Boolean, response)
        """
        logger.info("Create account login profile with both reset options")
        response = super().create_account_login_profile_both_reset_options(
            acc_name, password, access_key, secret_key)
        logger.info(response)
        if "Failed" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_account_login_profile_both_reset_options.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, response

    def create_account_login_profile_without_both_reset_options(self, acc_name: str, password: str,
                                                                access_key: str, secret_key: str) -> tuple:
        """
        Create account login profile using s3iamcli.
        :param acc_name: Name of the account.
        :param password: Password for the account login.
        :param access_key: Access key of the account.
        :param secret_key: Secret key of the account.
        :return: (Boolean, response)
        """
        logger.info("Create account login profile without reset options")
        response = super().create_acc_login_profile_without_both_reset_options(
            acc_name, password, access_key, secret_key)
        logger.info(response)
        if "Failed" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_account_login_profile_without_both_reset_options.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, response

    def update_account_login_profile_both_reset_options(self, acc_name: str, access_key: str,
                                                        secret_key: str, password: str = None) -> tuple:
        """
        Update account login profile using s3iamcli.
        :param acc_name: Name of the account.
        :param password: Password for the account login.
        :param access_key: Access key of the account.
        :param secret_key: Secret key of the account.
        :return: (Boolean, response)
        """
        logger.info("Create account login profile with both reset option")
        response = super().update_account_login_profile_both_reset_options(
            acc_name, access_key, secret_key, password)
        logger.info(response)
        if "Failed" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.update_account_login_profile_both_reset_options.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)
        return True, response

    def update_user_login_profile_without_passowrd_and_reset_option(self, user_name: str, access_key: str,
                                                                    secret_key: str) -> tuple:
        """
        Update user login profile using s3iamcli without password and reset options.
        :param user_name: Name of the user.
        :param access_key: Access key of the user.
        :param secret_key: Secret key of the user.
        :return: (Boolean, response)
        """
        logger.info(f"Update user login profile without password and reset options for user {user_name}")
        response = super().update_user_login_profile_without_password_and_reset_option(user_name, access_key,
                                                                                       secret_key)
        logger.info(response)
        if "Please provide password or password-reset" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.update_user_login_profile_without_passowrd_and_reset_option.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, response

    def get_temp_auth_credentials_account(self, account_name: str, account_password: str,
                                          duration: str = None) -> tuple:
        """
        Retrieving the temporary auth credentials for the given account.
        :param account_name: Name of the account.
        :param account_password: Password for the account.
        :param duration: Duration till account creds will be active.
        :return: (Boolean, response)
        """
        logger.info(f"Get temp auth credential for {account_name} account.")
        global ACC_ACCESS_KEY
        ACC_ACCESS_KEY = []
        global ACC_SECRET_KEY
        ACC_SECRET_KEY = []
        result = super().get_temp_auth_credentials_account(account_name, account_password, duration)
        logger.info("output = {}".format(result))
        if "error" in result:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.get_temp_auth_credentials_account.__name__,
                result))
            raise CTException(err.S3_CLIENT_ERROR, result)

        res = result.split("b'")[1].replace("\\n',", "")
        new_result = res.split(',')
        logger.debug(new_result)
        temp_auth_dict = {}
        for i in new_result:
            if "AccessKeyId" in i:
                response = i.split('=')
                ACC_ACCESS_KEY.append(response[1].strip(' '))
                logger.debug("Access Key Id : {}".format(ACC_ACCESS_KEY))
                temp_auth_dict['access_key'] = response[1].strip(' ')
            elif "SecretAccessKey" in i:
                response = i.split('=')
                ACC_SECRET_KEY.append(response[1].strip(' '))
                logger.debug("Secret Key : {}".format(ACC_SECRET_KEY))
                temp_auth_dict['secret_key'] = response[1].strip(' ')
            elif "SessionToken" in i:
                response = i.split('=')
                token = response[1].strip(' ')
                logger.debug("Session Token : {}".format(token))
                temp_auth_dict['session_token'] = token

        return True, temp_auth_dict

    def get_temp_auth_credentials_user(self, account_name: str, user_name: str, password: str,
                                       duration: str = None) -> tuple:
        """
        Retrieving the temporary auth credentials for the given user.
        :param account_name: Name of the account.
        :param user_name: Name of the user.
        :param password: Password for the user.
        :param duration: Duration till user creds will be active.
        :return: (Boolean, response)
        """
        logger.info(f"Get temp auth credential for {user_name} user.")
        global ACC_ACCESS_KEY
        ACC_ACCESS_KEY = []
        global ACC_SECRET_KEY
        ACC_SECRET_KEY = []
        result = super().get_temp_auth_credentials_user(account_name, user_name, password, duration)
        logger.info("output = {}".format(result))
        if "An error occurred" in result:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.get_temp_auth_credentials_user.__name__,
                result))
            raise CTException(err.S3_CLIENT_ERROR, result)

        res = result.split("b'")[1].replace("\\n',", "")
        new_result = res.split(',')
        logger.info(new_result)
        temp_auth_dict = {}
        for i in new_result:
            if "AccessKeyId" in i:
                response = i.split('=')
                ACC_ACCESS_KEY.append(response[1].strip(' '))
                logger.info("Access Key Id : {}".format(ACC_ACCESS_KEY))
                temp_auth_dict['access_key'] = response[1].strip(' ')
            elif "SecretAccessKey" in i:
                response = i.split('=')
                ACC_SECRET_KEY.append(response[1].strip(' '))
                logger.info("Secret Key : {}".format(ACC_SECRET_KEY))
                temp_auth_dict['secret_key'] = response[1].strip(' ')
            elif "SessionToken" in i:
                response = i.split('=')
                token = (response[1].strip(' '))
                logger.info("Session Token : {}".format(token))
                temp_auth_dict['session_token'] = token

        return True, temp_auth_dict

    def change_user_password(self, old_pwd: str, new_pwd: str, access_key: str, secret_key: str) -> tuple:
        """
        Change user password.
        :param old_pwd: Old password of user.
        :param new_pwd: New password of user.
        :param access_key: Access key of user.
        :param secret_key: Secret key of user.
        :return: (Boolean, response)
        """
        logger.info(f"Change user password")
        result = super().change_user_password(old_pwd, new_pwd, access_key, secret_key)
        logger.info("output = {}".format(result))
        if "failed" in result:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.change_user_password.__name__,
                result))
            raise CTException(err.S3_CLIENT_ERROR, result)

        return True, result

    def update_user_login_profile_s3iamcli_with_both_reset_options(self, user_name: str, password: str,
                                                                   access_key: str, secret_key: str) -> tuple:
        """
        Update user login profile using both password reset options.
        :param user_name: Name of user.
        :param password: User password.
        :param access_key: Access key of user.
        :param secret_key: Secret key of user.
        :return: (Boolean, response)
        """
        logger.info(f"Update {user_name} user login profile with both reset option.")
        result = super().update_user_login_profile_s3iamcli_with_both_reset_options(user_name, password,
                                                                                    access_key, secret_key)
        logger.info("output = {}".format(result))
        if "failed" in result:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.update_user_login_profile_s3iamcli_with_both_reset_options.__name__,
                result))
            raise CTException(err.S3_CLIENT_ERROR, result)

        return True, result

    def delete_multiple_accounts(self, acc_list: list) -> tuple:
        """
        Delete multiple accounts.
        :param acc_list: List of accounts.
        :return: (Boolean, response)
        """
        logger.debug(acc_list)
        logger.info("Deleting accounts in the given list....")
        deleted_acc_dict = dict()
        for acc in acc_list:
            logger.info("Deleting account : {}".format(acc))
            result = self.reset_access_key_and_delete_account_s3iamcli(acc)
            deleted_acc_dict[acc] = result[0]
        logger.info("List of deleted accounts: {0}".format(deleted_acc_dict))

        return True, deleted_acc_dict

    def create_and_delete_account_s3iamcli(self, account_name: str, email_id: str,
                                           secret_key: str, access_key: str) -> tuple:
        """
        Creating and Deleting Account.
        :param account_name: Name of the account.
        :param email_id: Email IF for the account.
        :param secret_key: Secret key.
        :param access_key: Access key.
        :return: (Boolean, response)
        """
        try:
            logger.info("Create and delete an account")
            acc = self.create_account_s3iamcli(account_name, email_id, LDAP_USERNAME, LDAP_PASSWD)
            logger.debug(acc)
            logger.info("Deleting Account")
            del_acc = self.delete_account_s3iamcli(account_name, access_key, secret_key)
            logger.debug(del_acc)

            return True, [acc, del_acc]
        except BaseException as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_and_delete_account_s3iamcli.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

    def reset_access_key_and_delete_account_s3iamcli(self, account_name: str) -> tuple:
        """
        Reset account access key and delete the account using aws s3iamcli.
        :param account_name: Name of the account.
        :return: (Boolean, response)
        """
        logger.info("Reset account access key and delete that account using s3iamcli")
        response = self.reset_account_access_key_s3iamcli(account_name, LDAP_USERNAME, LDAP_PASSWD)
        logger.debug(response)
        if not response[0]:
            return False, response
        access_key = response[1]["AccessKeyId"]
        secret_key = response[1]["SecretKey"]
        result = self.delete_account_s3iamcli(account_name=account_name, access_key=access_key,
                                              secret_key=secret_key, force=True)

        return result

    def create_user_access_key(self, user_name: str) -> tuple:
        """
        This function will create a user and access key in default account.
        :param str user_name: Name of the user to be created.
        :return: (Boolean, response)
        """
        logger.info("Creating a user and access key in default account")
        response = list()
        try:
            create_user = self.create_user(user_name)
            create_acc_key = self.create_access_key(user_name)
            # Adding sleep in sec due to ldap sync issue EOS-5924
            time.sleep(s3_conf["create_user_access_key_delay"])
            response.append({"User": create_user, "Keys": create_acc_key})
        except CTException as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in",
                    IamTestLib.create_user_access_key.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True, response

    def delete_users_with_access_key(self, iam_users_list: list) -> bool:
        """
        This function will delete the list of users from default account.
        :param list iam_users_list: List of users to be deleted.
        :return: (Boolean, response)
        """
        logger.info("Deleting iam users and access keys from default account.")
        try:
            for user in iam_users_list:
                resp = self.list_access_keys(user)
                if resp[0]:
                    logger.info("Deleting user access key")
                    for key in resp[1]["AccessKeyMetadata"]:
                        self.delete_access_key(
                            user, key["AccessKeyId"])
                    logger.info("Deleted user access key")
                logger.info("Deleting user from default account {0}".format(user))
                self.delete_user(user)
                logger.info("Deleted user from default account: {0}".format(user))
        except CTException as error:
            logger.error(
                "{0} {1}: {2}".format(
                    "Error in",
                    IamTestLib.delete_users_with_access_key.__name__,
                    error))
            raise CTException(err.S3_CLIENT_ERROR, error.args[0])

        return True

    def create_multiple_accounts(self, acc_count: str, name_prefix: str = "iamtestacc") -> tuple:
        """
        Create given no of accounts with specified prefix.
        :param int acc_count: No of accounts.
        :param str name_prefix: Account name prefix.
        :return: (Boolean, list of tuple with created account details).
        """
        logger.info(f"Create {acc_count} accounts starts with{name_prefix} name.")
        acc_li = []
        try:
            for acc in range(int(acc_count)):
                account_name = "{}{}".format(name_prefix, str(time.time()))
                email = "{}{}".format(account_name, s3_conf["email_suffix"])
                resp = self.create_account_s3iamcli(
                    account_name, email,
                    LDAP_USERNAME, LDAP_PASSWD)
                acc_li.append(resp)
        except CTException as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_multiple_accounts.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error)

        return True, acc_li

    def delete_account_s3iamcli_using_temp_creds(self, account_name: str, access_key: str, secret_key: str,
                                                 session_token: str, force: bool = False) -> tuple:
        """
        Deleting a specified account using it's temporary credentials.
        :param str account_name: Name of an account to be deleted.
        :param str access_key: Temporary access key of an account.
        :param str secret_key: Temporary secret key of an account.
        :param str session_token: Temporary session token of an account.
        :param bool force: --force option used while deleting an account.
        :return: Boolean and delete account response.
        """
        logger.info(f"Deleting {account_name} accounts using it's temporary credentials")
        response = super().delete_account_s3iamcli_using_temp_creds(account_name, access_key, secret_key, session_token,
                                                                    force)
        logger.info(response)
        if "An error occurred" in response:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.delete_account_s3iamcli_using_temp_creds.__name__,
                response))
            raise CTException(err.S3_CLIENT_ERROR, response)

        return True, response

    def create_s3iamcli_acc(self, account_name: str, email_id: str) -> tuple:
        """
        This function will create IAM accounts with specified account name and email-id.
        :param str account_name: Name of account to be created.
        :param str email_id: Email id for account creation.
        :return tuple: It returns multiple values such as canonical_id, access_key,
        secret_key and s3 objects which required to perform further operations.
        :return tuple
        """
        logger.info("Step : Creating account with name {} and email_id {}".format(account_name, email_id))
        try:
            create_account = self.create_account_s3iamcli(account_name, email_id, LDAP_USERNAME, LDAP_PASSWD)
            access_key = create_account[1]["access_key"]
            secret_key = create_account[1]["secret_key"]
            canonical_id = create_account[1]["canonical_id"]
            logger.info("Step Successfully created the s3iamcli account")
            s3_obj = S3Lib( access_key, secret_key, s3_conf["s3_url"], s3_conf["s3_cert_path"], s3_conf["region"])
            s3_acl_obj = S3AclTestLib(access_key=access_key, secret_key=secret_key)
            response = (canonical_id, s3_obj, s3_acl_obj, access_key, secret_key)
        except CTException as error:
            logger.error("{0} {1}: {2}".format(
                "Error in",
                IamTestLib.create_s3iamcli_acc.__name__,
                error))
            raise CTException(err.S3_CLIENT_ERROR, error)

        return True, response
