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
""" REST API Alert operation Library. """
import logging
from string import Template

import commons.errorcodes as err
from commons.constants import Rest as const
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_core_lib import RestClient
from config import CSM_REST_CFG

class RestTestLib:
    """
        This is the class for common test library
    """

    def __init__(self):
        self.config = CSM_REST_CFG
        self.log = logging.getLogger(__name__)
        self.restapi = RestClient(CSM_REST_CFG)
        self.user_type = ("valid", "duplicate", "invalid", "missing")
        self.headers = {}

    def rest_login(self, login_as):
        """
        This function will request for login
        login_as str/dict: The type of user you desire to login
        object : In case complete response is required
        """
        try:
            # Building response
            endpoint = self.config["rest_login_endpoint"]
            headers = self.config["Login_headers"]
            self.log.debug("endpoint: %s", endpoint)
            if isinstance(login_as, dict):
                payload = Template(const.LOGIN_PAYLOAD).substitute(login_as)
            else:
                payload = Template(const.LOGIN_PAYLOAD).substitute(
                    **self.config[login_as])

            # Fetch and verify response
            response = self.restapi.rest_call(
                "post", endpoint, headers=headers, data=payload, save_json=False)
            self.log.debug("response : %s", response)
            return response

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            RestTestLib.rest_login.__name__,
                            error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0]) from error

    def custom_rest_login(self, username, password,
                          username_key="username", password_key="password"):
        """
        This function tests the invalid login scenarios
        :param str username: username
        :param str password: password
        :param str username_key: key word for json load for username
        :param str password_key: key word for json load for password
        :return [object]: response
        """
        try:
            # Building response
            endpoint = self.config["rest_login_endpoint"]
            headers = self.config["Login_headers"]
            self.log.debug("endpoint %s", endpoint)
            payload = "{{\"{}\":\"{}\",\"{}\":\"{}\"}}".format(
                username_key, username, password_key, password)

            # Fetch and verify response
            response = self.restapi.rest_call(
                "post", endpoint, headers=headers, data=payload, save_json=False)
            self.log.debug("response : %s", response)

        except BaseException as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            RestTestLib.custom_rest_login.__name__,
                            error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0]) from error
        return response

    def authenticate_and_login(func):
        """
        :type: Decorator
        :functionality: Authorize the user before any rest calls
        """

        def create_authenticate_header(self, *args, **kwargs):
            """
            This function will fetch the login token and create the authentication header
            :param self: reference of class object
            :param args: arguments of the executable function
            :param kwargs: keyword arguments of the executable function
            :keyword login_as : type of user making the REST call (string)
            :keyword authorized : to verify unauthorized scenarios (boolean)
            :return: function executables
            """
            self.headers = {}  # Initiate headers
            self.log.debug(
                "user is getting authorized for REST operations ...")

            # Checking the type of login user
            login_type = kwargs.pop(
                "login_as") if "login_as" in kwargs else "csm_admin_user"

            # Checking the requirements to authorize
            authorized = kwargs.pop(
                "authorized") if "authorized" in kwargs else True

            # Fetching the login response
            self.log.debug("user will be logged in as %s", login_type)
            response = self.rest_login(login_as=login_type)

            if authorized and response.status_code == const.SUCCESS_STATUS:
                self.headers = {
                    'Authorization': response.headers['Authorization']}

            return func(self, *args, **kwargs)
        return create_authenticate_header

    def update_csm_config_for_user(self, user_type, username, password):
        """
         This function will update user config in run time
        :param user_type: new user type
        :param username: user name of new user
        :param password: password of new user
        :return: Boolean value for successful creation
        """
        try:
            # Updating configurations
            self.config.update({
                user_type: {"username": username, "password": password}
            })

            # Verify successfully added
            return user_type in self.config
        except Exception as error:
            self.log.error("%s %s: %s",
                            const.EXCEPTION_ERROR,
                            RestTestLib.update_csm_config_for_user.__name__,
                            error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error
