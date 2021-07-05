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

"""S3 account REST API operation Library."""

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
    def create_s3_account(self, user_name, email_id, passwd):
        """
        Function will create new s3 account user.

        :param user_name: type of user required
        :param email_id: to store newly created user to config
        :param passwd: to store newly created user to config
        :return: response of create user
        """
        try:
            # Building request url
            LOGGER.debug("Create s3 accounts ...")
            # Collecting required payload to be added for request
            data = {"account_name": user_name,
                    "account_email": email_id,
                    "password": passwd}
            LOGGER.debug("s3 account details %s", data)
            # Fetching api response
            response = self.restapi.rest_call(
                "post",
                endpoint=self.endpoint,
                data=data,
                headers=self.headers)

            return response
        except BaseException as error:
            LOGGER.error(
                "%s %s: %s",
                Rest.EXCEPTION_ERROR,
                S3AccountOperationsRestAPI.create_s3_account.__name__,
                error)
            raise CTException(
                err.S3_REST_POST_REQUEST_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def list_all_created_s3account(self):
        """
        Function will list down all created accounts.

        :return: response of create user
        """
        try:
            # Building request url
            LOGGER.debug("Try to fetch all s3 accounts ...")
            # Fetching api response
            response = self.restapi.rest_call(
                "get", endpoint=self.endpoint, headers=self.headers)

            return response
        except BaseException as error:
            LOGGER.error(
                "%s %s: %s",
                Rest.EXCEPTION_ERROR,
                S3AccountOperationsRestAPI.list_all_created_s3account.__name__,
                error)
            raise CTException(
                err.S3_REST_GET_REQUEST_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def delete_s3_account(self, user_name):
        """
        Function will delete the required user.

        :param user_name: user name of the account need to be deleted
        :return: response delete s3account
        """
        try:
            # Building request url
            LOGGER.debug("delete s3accounts user : %s", user_name)
            endpoint = "{}/{}".format(self.endpoint, user_name)
            LOGGER.debug("Endpoint for s3 accounts is %s", endpoint)
            # Fetching api response
            response = self.restapi.rest_call(
                "delete", endpoint=endpoint, headers=self.headers)

            return response
        except BaseException as error:
            LOGGER.error(
                "%s %s: %s",
                Rest.EXCEPTION_ERROR,
                S3AccountOperationsRestAPI.delete_s3_account_user.__name__,
                error)
            raise CTException(
                err.S3_REST_DELETE_REQUEST_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def reset_s3account_password(self, user_name, new_password):
        """
        Function will update the required user.

        :param user_name: Name of the s3 account user.
        :param new_password: NEW password of the s3 account user.
        :return: response edit s3account
        """
        try:
            # Building request url
            LOGGER.debug("Try to edit s3accounts user : %s", user_name)
            endpoint = "{}/{}".format(self.endpoint, user_name)
            LOGGER.debug("Endpoint for s3 accounts is %s", endpoint)
            # Collecting payload
            data = {"password": new_password,
                    "reset_access_key": "false"}
            LOGGER.debug("Payload for edit s3 accounts is %s", data)
            # Fetching api response
            response = self.restapi.rest_call(
                "patch", data=data, endpoint=endpoint,
                headers=self.headers)

            return response
        except BaseException as error:
            LOGGER.error(
                "%s %s: %s",
                Rest.EXCEPTION_ERROR,
                S3AccountOperationsRestAPI.edit_s3_account_user.__name__,
                error)
            raise CTException(
                err.S3_REST_PATCH_REQUEST_FAILED, error) from error
