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

"""S3 REST API operation Library."""

import logging
import time
import urllib
from http import HTTPStatus

from commons import errorcodes as err
from commons.constants import Rest
from commons.exceptions import CTException
from commons.utils.s3_utils import get_headers
from commons.utils.s3_utils import convert_xml_to_dict
from libs.csm.rest.csm_rest_s3user import RestS3user
from config.s3 import S3_CFG
from config import CSM_REST_CFG

LOGGER = logging.getLogger(__name__)


class S3AccountOperationsRestAPI(RestS3user):
    """S3 account operations using csm rest api."""

    def __init__(self):
        """s3 account operations constructor."""
        super().__init__()
        self.endpoint = CSM_REST_CFG["s3accounts_endpoint"]

    def create_s3_account(self, user_name, email_id, passwd) -> tuple:
        """
        Function will create new s3 account user.

        :param user_name: type of user required
        :param email_id: to store newly created user to config
        :param passwd: to store newly created user to config
        :return: bool, response of create user dict
        """
        try:
            LOGGER.debug("Create s3 accounts ...")
            data = {"account_name": user_name,
                    "account_email": email_id,
                    "password": passwd}
            LOGGER.debug("s3 account data %s", data)
            # Fetching api response
            response = self.create_custom_s3_user(data)
            if response.status_code != Rest.SUCCESS_STATUS_FOR_POST and response.ok is not True:
                return False, response.json()["message"]
            account_details = response.json()
            LOGGER.info("Account Details: %s", account_details)

            return True, account_details
        except BaseException as error:
            LOGGER.error(
                "%s %s: %s",
                Rest.EXCEPTION_ERROR,
                S3AccountOperationsRestAPI.create_s3_account.__name__,
                error)
            raise CTException(
                err.S3_REST_POST_REQUEST_FAILED, error) from error

    def list_s3_accounts(self) -> tuple:
        """
        Function will list down all created s3 accounts.

        :return: bool, account list.
        """
        try:
            LOGGER.debug("Fetch all s3 accounts ...")
            # Fetching api response
            response = self.list_all_created_s3account()
            if response.status_code != Rest.SUCCESS_STATUS and response.ok is not True:
                return False, response.json()["message"]
            accounts = [acc["account_name"]
                        for acc in response.json()["s3_accounts"]]
            LOGGER.debug("s3 accounts: %s", accounts)

            return True, accounts
        except BaseException as error:
            LOGGER.error(
                "%s %s: %s",
                Rest.EXCEPTION_ERROR,
                S3AccountOperationsRestAPI.list_s3_accounts.__name__,
                error)
            raise CTException(
                err.S3_REST_GET_REQUEST_FAILED, error) from error

    def delete_s3_account(self, user_name):
        """
        Function will delete the required user.

        :param user_name: user name of the account need to be deleted.
        :return: bool, response of deleted s3account.
        """
        try:
            LOGGER.debug("delete s3accounts user : %s", user_name)
            # Fetching api response
            response = self.delete_s3_account_user(user_name)
            if response.status_code == HTTPStatus.OK:
                return True, "Deleted user successfully"
            LOGGER.debug(response.json())
            return False, response.json()["message"]
        except BaseException as error:
            LOGGER.error(
                "%s %s: %s",
                Rest.EXCEPTION_ERROR,
                S3AccountOperationsRestAPI.delete_s3_account.__name__,
                error)
            raise CTException(
                err.S3_REST_DELETE_REQUEST_FAILED, error) from error

    def reset_s3account_password(self, user_name, new_password):
        """
        Function will update the s3 account password.

        :param user_name: Name of the s3 account user.
        :param new_password: New password of the s3 account user.
        :return: bool, response of reset s3account password.
        """
        try:
            LOGGER.debug("Update s3accounts user : %s", user_name)
            endpoint = f"{self.endpoint}/{user_name}"
            LOGGER.debug("Endpoint for s3 accounts is %s", endpoint)
            data = {"password": new_password,
                    "reset_access_key": "false"}
            LOGGER.debug("Payload for edit s3 accounts is %s", data)
            # Fetching api response
            response = self.edit_s3_account(user_name, data)
            if response.status_code != Rest.SUCCESS_STATUS and response.ok is not True:
                return False, f"Failed to reset password for '{user_name}' s3 account"
            LOGGER.debug(response.json())

            return True, response.json()["account_name"]
        except BaseException as error:
            LOGGER.error(
                "%s %s: %s",
                Rest.EXCEPTION_ERROR,
                S3AccountOperationsRestAPI.reset_s3account_password.__name__,
                error)
            raise CTException(
                err.S3_REST_PATCH_REQUEST_FAILED, error) from error


    def create_s3account_access_key(
            self,
            user_name,
            passwd,
            reset_access_key="true"):
        """
        Function will create/reset the access key for s3 account .

        :param user_name: Name of the s3 account user.
        :param passwd: New password of the s3 account user.
        :param reset_access_key: reset access key flag.
        :return: bool, response of reset access key for s3account.
        """
        try:
            LOGGER.debug("Update s3accounts user : %s", user_name)
            endpoint = f"{self.endpoint}/{user_name}"
            LOGGER.debug("Endpoint for s3 accounts is %s", endpoint)
            data = {"password": passwd,
                    "reset_access_key": reset_access_key}
            LOGGER.debug("Data to create/reset s3account access key: %s", data)
            # Fetching api response
            response = self.edit_s3_account(user_name, data)
            if response.status_code != Rest.SUCCESS_STATUS and response.ok is not True:
                return False, f"Failed to reset password for '{user_name}'"
            LOGGER.debug(response.json())

            return True, response.json()
        except BaseException as error:
            LOGGER.error(
                "%s %s: %s",
                Rest.EXCEPTION_ERROR,
                S3AccountOperationsRestAPI.create_s3account_access_key.__name__,
                error)
            raise CTException(
                err.S3_REST_PATCH_REQUEST_FAILED, error) from error


class S3AuthServerRestAPI(RestS3user):
    """S3 Auth service rest api operations."""

    def __init__(self, host=None):
        """S3AutheServer operations constructor."""
        super().__init__()
        self.endpoint = S3_CFG["s3auth_endpoint"].format(host) if host else S3_CFG["iam_url"]

    def execute_restapi_on_s3authserver(
            self, payload, access_key, secret_key, **kwargs) -> tuple:
        """
        Create header by calculate AuthV4 signature and execute rest api on s3 auth server.

        :param payload: payload data used in execution.
        :param access_key: access_key of s3 user.
        :param secret_key: secret_key of s3 user.
        :param request: s3auth restapi request.
        :param endpoint: s3auth restapi endpoint.
        """
        request = kwargs.get("request", "post")
        endpoint = kwargs.get("endpoint", None)
        # S3auth server endpoint.
        endpoint = endpoint if endpoint else self.endpoint
        # Create harder by calculate AuthV4 signature.
        headers = get_headers(
            request,
            self.endpoint,
            payload,
            service="s3",
            region="US",
            access_key=access_key,
            secret_key=secret_key)
        LOGGER.debug(headers)
        # Input data.
        payload = urllib.parse.urlencode(payload)
        LOGGER.debug(payload)
        # Fetching api response.
        response = self.restapi.s3auth_rest_call(
            "post", data=payload, endpoint=endpoint,
            headers=headers)
        response_data = convert_xml_to_dict(response)
        LOGGER.debug(response_data)
        if response.status_code != Rest.SUCCESS_STATUS and response.ok is not True:
            LOGGER.error("s3auth restapi request failed, reason: %s", response_data)
            return False, response_data["ErrorResponse"]["Error"]["Message"]
        time.sleep(S3_CFG["sync_step"])  # Added for direct rest call to sync.

        return True, response_data

    def update_account_login_profile(
            self, user_name=None, new_password=None, access_key=None, secret_key=None) -> tuple:
        """
        Reset s3 account password using s3authserver rest api.

        :param user_name: Name of the s3 account user.
        :param new_password: New password of the s3 account user.
        :param access_key: access_key of s3 user or ldap user of s3authserver.
        :param secret_key: secret_key of s3 user or ldap password of s3authserver.
        :return: bool, response of update account password for s3account.
        """
        payload = {"Action": "UpdateAccountLoginProfile"}
        if user_name:
            payload["AccountName"] = user_name
        if new_password:
            payload["Password"] = new_password
        status, response = self.execute_restapi_on_s3authserver(payload, access_key, secret_key)

        return status, response

    def create_iam_user(self, user_name, password, access_key, secret_key) -> tuple:
        """
        Create s3/iam account using s3authserver rest api.

        :param user_name: Name of iam user.
        :param password: Password of iam user.
        :param access_key: access_key of s3 user.
        :param secret_key: secret_key of s3 user.
        :return: bool, response of create iam user.
        """
        payload = {"Action": "CreateUser"}
        if user_name:
            payload["UserName"] = user_name
        if password:
            payload["Password"] = password
        status, response = self.execute_restapi_on_s3authserver(payload, access_key, secret_key)
        # Create account login profile.
        payload["Action"] = "CreateLoginProfile"
        self.execute_restapi_on_s3authserver(payload, access_key, secret_key)
        if status:
            response = response["CreateUserResponse"]["CreateUserResult"]["User"]
            LOGGER.debug("Create user response: %s", response)
            status = bool(user_name == response["UserName"])

        return status, response

    def list_iam_users(self, access_key, secret_key) -> tuple:
        """
        List iam users of s3 account using s3authserver rest api.

        :param access_key: access_key of s3 user.
        :param secret_key: secret_key of s3 user.
        :return: bool, response of list iam user for s3 account.
        """
        user_list = []
        payload = {"Action": "ListUsers"}
        status, response = self.execute_restapi_on_s3authserver(payload, access_key, secret_key)
        if status:
            member = response["ListUsersResponse"]["ListUsersResult"]["Users"]["member"]
            user_list = [
                member["UserName"]] if isinstance(
                    member, dict) else [
                        mem["UserName"] for mem in member] if isinstance(
                            member, list) else []

        return status, user_list

    def update_iam_user(
            self, user_name=None, new_password=None, access_key=None, secret_key=None) -> tuple:
        """
        Reset s3 iam user password using s3authserver rest api.

        :param user_name: Name of iam user.
        :param new_password: New password of iam user.
        :param access_key: access_key of s3 user.
        :param secret_key: secret_key of s3 user.
        :return: bool, response of update iam user for s3account.
        """
        payload = {"Action": "UpdateLoginProfile"}
        if user_name:
            payload["UserName"] = user_name
        if new_password:
            payload["Password"] = new_password
        status, response = self.execute_restapi_on_s3authserver(payload, access_key, secret_key)

        return status, response

    def delete_iam_user(self, user_name, access_key, secret_key) -> tuple:
        """
        Delete s3/iam account using s3authserver rest api.

        :param user_name: Name of the s3 account user.
        :param access_key: access_key of s3 user..
        :param secret_key: secret_key of s3 user.
        :return: bool, response of delete iam user.
        """
        payload = {"Action": "DeleteUser"}
        if user_name:
            payload["UserName"] = user_name
        status, response = self.execute_restapi_on_s3authserver(payload, access_key, secret_key)

        return status, response

    def create_iam_accesskey(self, user_name, access_key, secret_key) -> tuple:
        """
        Create s3/iam account user accesskey using s3authserver rest api.

        :param user_name: Name of s3 iam user.
        :param access_key: access_key of s3 user..
        :param secret_key: secret_key of s3 user.
        :return: bool, response of create accesskey of iam user.
        """
        payload = {"Action": "CreateAccessKey"}
        if user_name:
            payload["UserName"] = user_name
        status, response = self.execute_restapi_on_s3authserver(payload, access_key, secret_key)
        if status:
            response = response["CreateAccessKeyResponse"]["CreateAccessKeyResult"]["AccessKey"]
        LOGGER.debug("Create acesskey response: %s", response)

        return status, response

    # pylint: disable=too-many-arguments
    def create_custom_iam_accesskey(
            self, user_name, s3_access_key, s3_secret_key, iam_access_key=None,
            iam_secret_key=None) -> tuple:
        """
        Create s3/iam account user custom access & secret keys using s3authserver rest api.

        :param user_name: Name of s3 iam user.
        :param s3_access_key: access_key of s3 user.
        :param s3_secret_key: secret_key of s3 user.
        :param iam_access_key: access_key of IAM user.
        :param iam_secret_key: secret_key of IAM user.
        :return: bool, response of create accesskey of iam user.
        """
        payload = {"Action": "CreateAccessKey"}
        if user_name:
            payload["UserName"] = user_name
        if iam_access_key:
            payload["AccessKey"] = iam_access_key
        if iam_secret_key:
            payload["SecretKey"] = iam_secret_key
        status, response = self.execute_restapi_on_s3authserver(
            payload, s3_access_key, s3_secret_key)
        if status:
            response = response["CreateAccessKeyResponse"]["CreateAccessKeyResult"]["AccessKey"]
        LOGGER.debug("Create acesskey response: %s", response)

        return status, response

    def delete_iam_accesskey(self, user_name, access_key_id, access_key, secret_key) -> tuple:
        """
        Delete s3/iam account user accesskey using s3authserver rest api.

        :param user_name: Name of s3 iam user.
        :param access_key_id: Access key of the iam user.
        :param access_key: access_key of s3 user..
        :param secret_key: secret_key of s3 user.
        :return: bool, response of delete accesskey of iam account.
        """
        payload = {"Action": "DeleteAccessKey"}
        if user_name:
            payload["UserName"] = user_name
        if access_key_id:
            payload["AccessKeyId"] = access_key_id
        status, response = self.execute_restapi_on_s3authserver(payload, access_key, secret_key)

        return status, response

    def list_iam_accesskey(
            self, user_name, access_key, secret_key) -> tuple:
        """
        List iam user accesskey using s3authserver rest api.

        :param user_name: Name of s3 iam user.
        :param access_key: access_key of s3 user..
        :param secret_key: secret_key of s3 user.
        :return: bool, response of list accesskey of iam user.
        """
        payload = {"Action": "ListAccessKeys"}
        if user_name:
            payload["UserName"] = user_name
        status, response = self.execute_restapi_on_s3authserver(payload, access_key, secret_key)
        if status:
            response = response["ListAccessKeysResponse"]["ListAccessKeysResult"][
                "AccessKeyMetadata"]["member"]
        LOGGER.debug("List access key response: %s", response)

        return status, response

    def update_iam_accesskey(
            self, user_name, user_access_key, access_key, secret_key, **kwargs) -> tuple:
        """
        Update iam account user accesskey using s3authserver rest api.

        :param user_name: Name of s3 iam user.
        :param user_access_key: Access key of the iam user.
        :param access_key: access_key of s3 user..
        :param secret_key: secret_key of s3 user.
        :param status: accesskey status may be Active/Inactive.
        :return: bool, response of update accesskey of iam user.
        """
        status = kwargs.get("status", "Active")
        payload = {"Action": "UpdateAccessKey"}
        if user_name:
            payload["UserName"] = user_name
        payload["Status"] = status
        payload["AccessKeyId"] = user_access_key
        status, response = self.execute_restapi_on_s3authserver(payload, access_key, secret_key)

        return status, response
