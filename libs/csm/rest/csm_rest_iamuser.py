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
from http import HTTPStatus
from requests.models import Response
from commons.constants import S3_ENGINE_RGW
from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from commons.utils import config_utils
from config import CMN_CFG, CSM_REST_CFG
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
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            payload = self.iam_user_payload_rgw(user_type="valid")
            response = self.create_iam_user_rgw(payload)
        else:
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
            response = self.restapi.rest_call(
                "post", endpoint=endpoint, data=iam_user_payload,
                headers=self.headers)
        return response

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
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            response = Response()
            response.status_code = 200
            response._content = b'{"message":"bypassed"}'
        else:
            self.log.debug("iam user")
            endpoint = '/'.join((self.config["IAM_users_endpoint"], user))
            self.log.debug(
                "Endpoint for delete iam user is %s", endpoint)

            self.headers.update(self.config["Login_headers"])

            # Fetching api response
            response = self.restapi.rest_call(
                "delete", endpoint=endpoint, headers=self.headers)
        return response

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
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            return self.verify_create_iam_user_rgw(user_type="valid")
        else:
            response = self.create_iam_user(
                user=user, password=password, login_as="s3account_user")
            if response.status_code != expected_status_code:
                self.log.error(
                    "Response is not 200, Response=%s",
                    response.status_code)
                return False, response.json()
        return True, response.json()

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
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            response = Response()
            response.status_code = 200
            response._content = b'{"message":"bypassed"}'
        else:
            # Building response
            endpoint = self.config["rest_login_endpoint"]
            headers = self.config["Login_headers"]
            self.log.debug("endpoint  : %s ", endpoint)
            payload = Template(const.IAM_USER_LOGIN_PAYLOAD).substitute(
                username=user,
                password=password)

            # Fetch and verify response
            response = self.restapi.rest_call(
                "post", endpoint, headers=headers,
                data=payload, save_json=False)
            self.log.debug("response :  %s", response)

        return response.status_code

    @RestTestLib.authenticate_and_login
    def list_iam_users(self):
        """
        This function will list all IAM users.
        :return: response
        :rtype: response object
        """
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            response = Response()
            response.status_code = 200
            response._content = b'{"message":"bypassed"}'
        else:
            self.log.debug("Listing of iam users")
            endpoint = self.config["IAM_users_endpoint"]
            self.log.debug("Endpoint for iam user is %s", endpoint)

            self.headers.update(self.config["Login_headers"])

            # Fetching api response
            response = self.restapi.rest_call(
                "get", endpoint=endpoint, headers=self.headers)
        return response

    def verify_unauthorized_access_to_csm_user_api(self):
        """
        Verifying that IAM login to CSM fails and unauthorised access to CSM
        REST API fails.
        :return: True/False
        :rtype: bool
        """
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            response = Response()
            response.status_code = 200
            response._content = b'{"message":"bypassed"}'
        else:
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
                "user_role", data["role"])
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

    @RestTestLib.authenticate_and_login
    def create_iam_user_under_given_account(self, iam_user, iam_password, account_name):
        """
        This function will create iam user under given account_name.
        :param iam_user: username for new iam user
        :param iam_password: password of new iam user
        :param account_name: username of S3 account under which new iam user will be created
        :return: new iam user details
        """
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            response = Response()
            response.status_code = 200
            response._content = b'{"message":"bypassed"}'
        else:
            self.log.debug("Creating new iam user %s under %s", iam_user, account_name)
            iam_user_payload = {
                "user_name": iam_user,
                "password": iam_password,
                "require_reset": False
            }
            endpoint = self.config["IAM_users_endpoint"]
            self.log.debug("Endpoint for iam user creation is %s", endpoint)
            self.log.info("self.headers = %s", self.headers)
            self.headers["Content-Type"] = "application/json"
            response = self.restapi.rest_call("post", endpoint=endpoint,
                                              data=json.dumps(iam_user_payload),
                                              headers=self.headers)

            if response.status_code != const.SUCCESS_STATUS:
                self.log.error("Response = %s", response.text)
                self.log.error("Request header = %s", response.request.headers)
                self.log.error("Request Body= %s ", response.request.body)
                raise CTException(err.CSM_REST_POST_REQUEST_FAILED,
                                  msg="Create IAM user request failed")

        return response

    @RestTestLib.authenticate_and_login
    def list_iam_users_for_given_s3_user(self, user):
        """
        This function will list all iam users from given s3 user.
        :param user: username of S3 account under which new iam user will be created
        :return: response of delete iam user
        """
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            response = Response()
            response.status_code = 200
            response._content = b'{"message":"bypassed"}'
        else:
            self.log.debug("Listing all iam users under S3 account %s", user)
            endpoint = self.config["IAM_users_endpoint"]
            self.log.debug("Endpoint for iam user listing is %s", endpoint)
            self.headers.update(self.config["Login_headers"])
            # Fetching api response
            response = self.restapi.rest_call("get", endpoint=endpoint, headers=self.headers)
            if response.status_code != const.SUCCESS_STATUS:
                self.log.error("Response = %s", response.text)
                self.log.error("Request header = %s", response.request.headers)
                self.log.error("Request Body= %s ", response.request.body)
                raise CTException(err.CSM_REST_GET_REQUEST_FAILED, msg="List IAM users failed.")
        return response

    @RestTestLib.authenticate_and_login
    def delete_iam_user_under_given_account(self, iam_user, account_name):
        """
        This function will delete iam user from given account_name.
        :param iam_user: iam user name which needs to be deleted
        :param account_name: username of S3 account under which new iam user will be created
        """
        self.log.debug("Deleting %s under S3 account %s", iam_user, account_name)
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            response = Response()
            response.status_code = 200
            response._content = b'{"message":"bypassed"}'
        else:

            endpoint = '/'.join((self.config["IAM_users_endpoint"], iam_user))
            self.log.debug("Endpoint for iam user deletion is %s", endpoint)
            response = self.restapi.rest_call("delete", endpoint=endpoint, headers=self.headers)
            if response.status_code != const.SUCCESS_STATUS:
                self.log.error("Response = %s", response.text)
                self.log.error("Request header = %s", response.request.headers)
                self.log.error("Request Body= %s ", response.request.body)
                raise CTException(err.CSM_REST_DELETE_REQUEST_FAILED,
                                  msg="Delete IAM users request failed.")
        return response

    def iam_user_payload_rgw(self, user_type="valid"):
        """
        Return payload for IAM user for RGW with Ceph
        """
        # Initialize all variables
        payload = {}
        user_id = const.IAM_USER + str(int(time.time()))
        display_name = const.IAM_USER + str(int(time.time()))
        email = user_id + "@seagate.com"
        key_type = "s3"
        access_key = user_id.ljust(const.S3_ACCESS_LL, "d")
        secret_key = config_utils.gen_rand_string(length=const.S3_SECRET_LL)
        user_cap = "users=*"
        generate_key = True
        max_buckets = 1000
        suspended = False
        tenant = "abc"
        if user_type == "valid":
            payload.update({"uid": user_id})
            payload.update({"display_name": display_name})
        if user_type == "loaded":
            payload.update({"uid": user_id})
            payload.update({"display_name": display_name})
            payload.update({"email": email})
            payload.update({"key_type": key_type})
            payload.update({"access_key": access_key})
            payload.update({"secret_key": secret_key})
            payload.update({"user_caps": user_cap})
            payload.update({"generate_key": generate_key})
            payload.update({"max_buckets": max_buckets})
            payload.update({"suspended": suspended})
            payload.update({"tenant": tenant})
        self.log.info("Payload : %s", payload)
        return payload

    @RestTestLib.authenticate_and_login
    def create_iam_user_rgw(self, payload: dict):
        """
        Creates IAM user for given payload.
        """
        self.log.info("Creating IAM user request....")
        endpoint = CSM_REST_CFG["s3_iam_user_endpoint"]
        response = self.restapi.rest_call("post", endpoint=endpoint, json_dict=payload,
                                          headers=self.headers)
        self.log.info("IAM user request successfully sent...")
        return response

    def verify_create_iam_user_rgw(
            self, user_type="valid", expected_response=HTTPStatus.OK, verify_response=False):
        """
        creates and verify status code and response for iam user request.
        """
        payload = self.iam_user_payload_rgw(user_type=user_type)
        response = self.create_iam_user_rgw(payload)
        resp = response.json()
        if response.status_code == expected_response:
            self.log.info("Status code check passed.")
            result = True
            if verify_response:
                self.log.info("Checking response...")
                for key,value in payload.items():
                    self.log.info("Expected response for %s: %s", key,value)
                    if key == "uid":
                        key = "user_id"
                    self.log.info("Actual response for %s: %s", key, resp[key])
                    if value != resp[key]:
                        self.log.error("Actual and expected response for %s didnt match", key)
                        result = False
        else:
            self.log.error("Status code check failed.")
            result = False
        return result, resp
