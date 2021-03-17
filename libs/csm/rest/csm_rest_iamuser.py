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
"""Test library for IAM user related operations."""
import time
from string import Template
import json

from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from libs.csm.rest.csm_rest_csmuser import RestCsmUser


class RestIamUser(RestTestLib):
    """RestIamUser contains all the Rest API calls for iam user operations"""

    def __init__(self):
        super(RestIamUser, self).__init__()
        self.template_payload = Template(const.IAM_USER_DATA_PAYLOAD)
        self.iam_user = None
        self.csm_user = RestCsmUser()

    @RestTestLib.authenticate_and_login
    def create_iam_user(self, user=const.IAM_USER,
                        password=const.IAM_PASSWORD,
                        require_reset_val="true"):
        """
        This function will create payload according to the required type for
        creating Iam user.
        :param user: type of user to create payload.
        :param password: password of new user
        :param require_reset_val: set reset value to true or false
        :return: payload
        """
        try:
            self.log.debug("iam user")
            payload = self.template_payload.substitute(
                iamuser=user,
                iampassword=password,
                requireresetval=require_reset_val)
            iam_user_payload = payload
            endpoint = self.config["IAM_users_endpoint"]
            self.log.debug("Endpoint for iam user is %s", endpoint)

            self.headers.update(self.config["Login_headers"])

            # Fetching api response
            return self.restapi.rest_call(
                "post", endpoint=endpoint, data=iam_user_payload,
                headers=self.headers)

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            RestIamUser.create_iam_user.__name__,
                            error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0]) from error

    @RestTestLib.authenticate_and_login
    def delete_iam_user(self, user=None):
        """
        This function will delete payload according to the required type for
        deleting Iam user.
        :param user: type of user to create payload.
        :return: payload
        """
        if self.iam_user and (not user):
            user = self.iam_user
        try:
            self.log.debug("iam user")
            endpoint = '/'.join((self.config["IAM_users_endpoint"], user))
            self.log.debug(
                "Endpoint for delete iam user is %s", endpoint)

            self.headers.update(self.config["Login_headers"])

            # Fetching api response
            return self.restapi.rest_call(
                "delete", endpoint=endpoint, headers=self.headers)

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            RestIamUser.delete_iam_user.__name__,
                            error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0]) from error

    def create_and_verify_iam_user_response_code(self,
                                                 user=const.IAM_USER +
                                                 str(int(time.time())),
                                                 password=const.IAM_PASSWORD,
                                                 expected_status_code=200):
        """
        This function will create and verify new iam user.
        :param user: type of user required
        :param expect_status_code: Expected status code for verification.
        :return: boolean value for Success(True)/Failure(False)
        """
        self.iam_user = user
        try:
            response = self.create_iam_user(
                user=user, password=password, login_as="s3account_user")
            if response.status_code != expected_status_code:
                self.log.error(
                    "Response is not 200, Response=%s",
                    response.status_code)
                return False, response.json()
            return True, response.json()
        except Exception as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            RestIamUser.create_and_verify_iam_user_response_code.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

    @RestTestLib.authenticate_and_login
    def iam_user_login(self, user=None,
                       password=const.IAM_PASSWORD):
        """
        This function will request for  IAM user login
        :param user: name of user required
        :param password: password of user login
        :return: response of status code
        """
        if self.iam_user and not user:
            user = self.iam_user
        try:
            # Building response
            endpoint = self.config["rest_login_endpoint"]
            headers = self.config["Login_headers"]
            self.log.debug(f"endpoint  {endpoint}")
            payload = Template(const.IAM_USER_LOGIN_PAYLOAD).substitute(
                username=user,
                password=password)

            # Fetch and verify response
            response = self.restapi.rest_call(
                "post", endpoint, headers=headers,
                data=payload, save_json=False)
            self.log.debug("response :  %s", response)

            return response.status_code
        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            RestIamUser.iam_user_login.__name__,
                            error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0]) from error

    @RestTestLib.authenticate_and_login
    def list_iam_users(self):
        """
        This function will list all IAM users.
        :return: response
        :rtype: response object
        """
        try:
            self.log.debug("Listing of iam users")
            endpoint = self.config["IAM_users_endpoint"]
            self.log.debug("Endpoint for iam user is %s", endpoint)

            self.headers.update(self.config["Login_headers"])

            # Fetching api response
            return self.restapi.rest_call(
                "get", endpoint=endpoint, headers=self.headers)

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            RestIamUser.list_iam_users.__name__,
                            error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0]) from error

    def verify_unauthorized_access_to_csm_user_api(self):
        """
        Verifying that IAM login to CSM fails and unauthorised access to CSM
        REST API fails.
        :return: True/False
        :rtype: bool
        """
        try:

            self.log.debug("Creating IAM user")
            user = f"{const.IAM_USER}{str(int(time.time()))}"
            response = self.create_iam_user(
                user=user, login_as="s3account_user")

            self.log.debug(
                "Verifying IAM user was created")
            if response.status_code == const.SUCCESS_STATUS:
                self.log.debug(
                    "Verified IAM user was created")
            else:
                self.log.error("Error in IAM user creation")
                return False

            self.log.debug("Verifying IAM login to CSM fails")
            headers = {}
            self.log.debug("Logging in as iam user %s", user)
            payload_login = {"username": user, "password": const.IAM_PASSWORD}
            response = self.restapi.rest_call(
                request_type="post",
                endpoint=self.config["rest_login_endpoint"],
                data=json.dumps(payload_login),
                headers=self.config["Login_headers"])
            if response.status_code != const.UNAUTHORIZED:
                self.log.error(
                    "IAM user log in to CSM should fail!But got response %s", response)
                return False
            else:
                self.log.debug(
                    "IAM user log in to CSM failed with expected response %s", response)

            endpoint = self.config["csmuser_endpoint"]

            self.log.debug(
                "Verifying unauthorised access to GET CSM user list API request")
            # Fetching api response
            response = self.restapi.rest_call(
                request_type="get", endpoint=endpoint, headers=headers)
            self.log.debug(
                "response returned is:\n %s", response)
            if response.status_code != const.UNAUTHORIZED:
                self.log.error(
                    "GET CSM users request should fail without valid "
                    "authorization token!But got response %s", response)
                return False
            else:
                self.log.debug(
                    "Unauthorised GET CSM users request failed with expected response %s", response)

            self.log.debug(
                "Verifying unauthorised access to CREATE CSM user API request")
            # Creating required payload to be added for request
            data = self.csm_user.create_payload_for_new_csm_user(
                user_type="valid", user_defined_role="manage")
            user_data = const.USER_DATA
            user_data = user_data.replace("testusername", data["username"]).replace(
                "user_role", data["roles"][0])
            self.log.debug("Payload for CSM user is %s", user_data)
            response = self.restapi.rest_call(
                "post", endpoint=endpoint, data=user_data, headers=headers)
            if response.status_code != const.UNAUTHORIZED:
                self.log.error(
                    "POST CSM user request should fail without valid "
                    "authorization token!But got response %s", response)
                return False
            else:
                self.log.debug(
                    "Unauthorised POST CSM user request failed with expected "
                    "response %s", response)

            self.log.debug(
                "Verifying unauthorised access to GET CSM user API request")
            endpoint_single_user = f"{endpoint}/csm_user_manage"
            response = self.restapi.rest_call(
                request_type="get", endpoint=endpoint_single_user, headers=headers)
            if response.status_code != const.UNAUTHORIZED:
                self.log.error(
                    "GET CSM user request should fail without valid "
                    "authorization token!But got response %s", response)
                return False
            else:
                self.log.debug(
                    "Unauthorised GET CSM user request failed with expected "
                    "response %s", response)

            self.log.debug(
                "Verifying unauthorised access to update(PATCH) CSM user API request")
            old_password = self.csm_user.config["csm_user_manage"]["password"]
            payload = {"current_password": old_password,
                       "password": "Testuser@12345"}

            response = self.restapi.rest_call(
                request_type="patch", endpoint=endpoint_single_user, data=payload, headers=headers)
            if response.status_code != const.UNAUTHORIZED:
                self.log.error(
                    "PATCH CSM user request should fail without valid "
                    "authorization token!But got response %s", response)
                return False
            else:
                self.log.debug(
                    "Unauthorised PATCH CSM users request failed with expected "
                    "response %s", response)

            self.log.debug(
                "Verifying unauthorised access to DELETE CSM user API request")
            response = self.restapi.rest_call(
                request_type="delete", endpoint=endpoint_single_user,
                headers=headers)
            if response.status_code != const.UNAUTHORIZED:
                self.log.error(
                    "DELETE CSM user request should fail without valid "
                    "authorization token!But got response %s", response)
                return False
            else:
                self.log.debug(
                    "Unauthorised DELETE CSM users request failed with expected"
                    " response %s", response)

            self.log.debug(
                "Verifying unauthorised access to GET permission API request")

            endpoint_permission = self.config["csmuser_permission_endpoint"]
            self.log.debug(
                "Permission endpoint is : %s", endpoint_permission)
            response = self.restapi.rest_call(
                request_type="get", endpoint=endpoint_permission,
                headers=headers)
            if response.status_code != const.UNAUTHORIZED:
                self.log.error(
                    "GET Permission request should fail without valid "
                    "authorization token!But got response %s", response)
                return False
            else:
                self.log.debug(
                    "Unauthorised GET permission request failed with expected"
                    "response %s", response)

            return True
        except BaseException as error:
            self.log.error(
                "%s %s: %s",
                const.EXCEPTION_ERROR,
                RestIamUser.verify_unauthorized_access_to_csm_user_api.__name__,
                error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR,
                error.args[0]) from error
