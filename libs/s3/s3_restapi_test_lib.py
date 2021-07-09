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

"""S3 REST API operation Library."""

import logging

from commons import errorcodes as err
from commons.constants import Rest
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from config import CSM_REST_CFG

LOGGER = logging.getLogger(__name__)


class S3AccountOperationsRestAPI(RestS3user):
    """S3 account operations using csm rest api."""

    def __init__(self):
        """s3 account operations constructor."""
        super(S3AccountOperationsRestAPI, self).__init__()
        self.endpoint = CSM_REST_CFG["s3accounts_endpoint"]

    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
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
            response = self.restapi.rest_call(
                "post",
                endpoint=self.endpoint,
                data=data,
                headers=self.headers)
            if response.status_code != Rest.SUCCESS_STATUS and response.ok is not True:
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

    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def list_s3_accounts(self) -> tuple:
        """
        Function will list down all created s3 accounts.

        :return: bool, account list.
        """
        try:
            LOGGER.debug("Fetch all s3 accounts ...")
            # Fetching api response
            response = self.restapi.rest_call(
                "get", endpoint=self.endpoint, headers=self.headers)
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

    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def delete_s3_account(self, user_name):
        """
        Function will delete the required user.

        :param user_name: user name of the account need to be deleted.
        :return: bool, response of deleted s3account.
        """
        try:
            LOGGER.debug("delete s3accounts user : %s", user_name)
            endpoint = "{}/{}".format(self.endpoint, user_name)
            LOGGER.debug("Endpoint for s3 accounts is %s", endpoint)
            # Fetching api response
            response = self.restapi.rest_call(
                "delete", endpoint=endpoint, headers=self.headers)
            if response.status_code != Rest.SUCCESS_STATUS and response.ok is not True:
                return False, response.json()["message"]
            LOGGER.debug(response.json())

            return True, response.json()["message"]
        except BaseException as error:
            LOGGER.error(
                "%s %s: %s",
                Rest.EXCEPTION_ERROR,
                S3AccountOperationsRestAPI.delete_s3_account.__name__,
                error)
            raise CTException(
                err.S3_REST_DELETE_REQUEST_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
    def reset_s3account_password(self, user_name, new_password):
        """
        Function will update the s3 account password.

        :param user_name: Name of the s3 account user.
        :param new_password: New password of the s3 account user.
        :return: bool, response of reset s3account password.
        """
        try:
            LOGGER.debug("Update s3accounts user : %s", user_name)
            endpoint = "{}/{}".format(self.endpoint, user_name)
            LOGGER.debug("Endpoint for s3 accounts is %s", endpoint)
            data = {"password": new_password,
                    "reset_access_key": "false"}
            LOGGER.debug("Payload for edit s3 accounts is %s", data)
            # Fetching api response
            response = self.restapi.rest_call(
                "patch", data=data, endpoint=endpoint,
                headers=self.headers)
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

    @RestTestLib.authenticate_and_login
    @RestTestLib.rest_logout
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
            endpoint = "{}/{}".format(self.endpoint, user_name)
            LOGGER.debug("Endpoint for s3 accounts is %s", endpoint)
            data = {"password": passwd,
                    "reset_access_key": reset_access_key}
            LOGGER.debug("Data to create/reset s3account access key: %s", data)
            # Fetching api response
            response = self.restapi.rest_call(
                "patch", data=data, endpoint=endpoint,
                headers=self.headers)
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
