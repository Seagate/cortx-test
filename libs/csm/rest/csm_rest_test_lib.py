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
""" REST API Alert operation Library. """
import logging
import time
from random import Random
from string import Template
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
import commons.errorcodes as err
from commons.constants import Rest as const
from commons.exceptions import CTException
from config import CSM_REST_CFG
from config import CMN_CFG
from libs.csm.rest.csm_rest_core_lib import RestClient


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
        self.seed = int(time.time())
        self.random_gen = Random(self.seed)
        self.log.info("Seed : %s", self.seed)
        self.worker_list = []
        self.workers = []
        for node in CMN_CFG["nodes"]:
            if node["node_type"] == "master":
                self.log.debug("Master node : %s", node["hostname"])
                self.master = LogicalNode(hostname=node["hostname"],
                                         username=node["username"],
                                         password=node["password"])
                self.hlth_master = Health(hostname=node["hostname"],
                                         username=node["username"],
                                         password=node["password"])
            else:
                self.log.debug("Worker node : %s", node["hostname"])
                self.workers.append(LogicalNode(hostname=node["hostname"],
                                                 username=node["username"],
                                                 password=node["password"]))
                host = node["hostname"]
                self.worker_list.append(host)

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
                err.CSM_REST_AUTHENTICATION_ERROR, error) from error

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    def custom_rest_login(self, username, password, username_key="username",
                          password_key="password", override_config=False, config_params=None):
        """
        This function tests the invalid login scenarios
        :param str username: username
        :param str password: password
        :param str username_key: key word for json load for username
        :param str password_key: key word for json load for password
        :param boolean override_config: to enable/disable param override
        :param dict config_params: params to be override
        :return [object]: response
        """
        try:
            if override_config and config_params is not None:
                config = CSM_REST_CFG
                for key, value in config_params.items():
                    config.update({key: value})
                restapi = RestClient(config)
                # Building response
                endpoint = config["rest_login_endpoint"]
                headers = config["Login_headers"]
                self.log.debug("endpoint %s", endpoint)
                payload = "{{\"{}\":\"{}\",\"{}\":\"{}\"}}".format(
                    username_key, username, password_key, password)

                # Fetch and verify response
                response = restapi.rest_call(
                    "post", endpoint, headers=headers, data=payload, save_json=False)
            else:
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
                err.CSM_REST_AUTHENTICATION_ERROR, error) from error
        return response

    def custom_rest_login_missing_param(self, param1, param1_key):
        """
        This function tests the invalid login scenarios
        :param str param1: can be username or password
        :param str param1_key: key word for json load for username or password
        :return [object]: response
        """
        try:
            # Building response
            endpoint = self.config["rest_login_endpoint"]
            headers = self.config["Login_headers"]
            self.log.debug("endpoint %s", endpoint)
            payload = "{{\"{}\":\"{}\"}}".format(
                param1_key, param1)

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
                err.CSM_REST_AUTHENTICATION_ERROR, error) from error
        return response

    @staticmethod
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
            self.log.debug("user is getting authorized for REST operations ...")
            # Checking the type of login user
            login_type = kwargs.pop("login_as") if "login_as" in kwargs else "csm_admin_user"
            # Checking the requirements to authorize
            authorized = kwargs.pop("authorized") if "authorized" in kwargs else True
            # Fetching the login response
            self.log.debug("user will be logged in as %s", login_type)
            response = self.rest_login(login_as=login_type)
            if authorized and response.status_code == const.SUCCESS_STATUS:
                self.headers = {'Authorization': response.headers['Authorization']}
            else:
                self.log.error("Authentication request failed in %s.\nResponse code : %s",
                               RestTestLib.authenticate_and_login.__name__, response.status_code)
                self.log.error("Response content: %s", response.content)
                self.log.error("Request headers : %s\nRequest body : %s",
                               response.request.headers, response.request.body)
                raise CTException(err.CSM_REST_AUTHENTICATION_ERROR)
            return func(self, *args, **kwargs)

        return create_authenticate_header

    @staticmethod
    def rest_logout(func):
        """
        :type: Decorator
        :functionality: logout the session after any rest calls.
        """

        def inner_func(self, *args, **kwargs):
            """
            This function will execute any rest call and logout the session.
            :param self: reference of class object.
            :param args: arguments of the executable function.
            :param kwargs: keyword arguments of the executable function.
            :return: function executables.
            """
            # Execute prior functions.
            response = func(self, *args, **kwargs)
            # logout session.
            resp = self.restapi.rest_call(
                "post", endpoint=self.config["rest_logout_endpoint"], headers=self.headers)
            if resp.status_code != const.SUCCESS_STATUS:
                raise CTException(err.CSM_REST_AUTHENTICATION_ERROR)
            return response

        return inner_func

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
                err.CSM_REST_VERIFICATION_FAILED, error) from error

    def get_headers(self, user_name, user_password):
        """
        This function will login with given user_name, user_password
        and gets the token. It creates and returns the required
        headers for user with token.
        :param user_name: user name for which we need headers
        :param user_password: user password for which we need headers
        :return: required headers
        """
        try:
            self.log.debug("Getting required headers for user %s", user_name)
            endpoint = self.config["rest_login_endpoint"]
            headers = self.config["Login_headers"]
            payload = "{{\"{}\":\"{}\",\"{}\":\"{}\"}}".format(
                "username", user_name, "password", user_password)
            self.log.debug("Payload for S3 account login is %s", payload)

            # Fetch user token from response
            response = self.restapi.rest_call(
                "post", endpoint, headers=headers, data=payload, save_json=False)
            if response.status_code != const.SUCCESS_STATUS:
                self.log.error("Authentication request failed.\nResponse code : %s",
                               response.status_code)
                self.log.error("Response content: %s", response.content)
                self.log.error("Request headers : %s\nRequest body : %s",
                               response.request.headers, response.request.body)
                raise CTException(err.CSM_REST_AUTHENTICATION_ERROR)
            token = response.headers['Authorization']
            headers = {'Authorization': token}
            conf_headers = self.config["Login_headers"]
            headers.update(conf_headers)
            return headers
        except Exception as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           RestTestLib.get_headers.__name__,
                           error)
            raise CTException(
                err.CSM_REST_VERIFICATION_FAILED, error.args[0]) from error

    def search_list_of_dict(self, search_key: str, search_val: str, search_in: list):
        """
        Search for {<search_key>:<search_val>} in [{<search_key>:<search_val>,..}, {}, {}...]
        """
        self.log.info("Search dict %s:%s in %s", search_key, search_val, search_in)
        return list(filter(lambda key: key[search_key] == search_val, search_in))
