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
"""Test library for CSM user related operations."""
import time
import json
import random
from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from commons.utils import config_utils
from libs.csm.rest.csm_rest_test_lib import RestTestLib

class RestCsmUser(RestTestLib):
    """RestCsmUser contains all the Rest API calls for csm user operations"""

    def __init__(self):
        super(RestCsmUser, self).__init__()
        self.recently_created_csm_user = None
        self.recent_patch_payload = None
        self.user_type = ("valid", "duplicate", "invalid", "missing")
        self.user_roles = ["manage", "monitor"]
        self.random_user = False
        self.random_num = 0
        self.csm_user_list_params = ("offset", "limit", "sortby", "dir")

    def create_payload_for_new_csm_user(self, user_type, user_defined_role):
        """
        This function will create payload according to the required type for creating CSM user.
        :param user_type: type of user to create payload.
        :param user_defined_role : type of user role to create payload.
        :return: payload
        """
        try:
            # Creating payload for required user type

            # Creating users which are pre-defined in config
            if user_type == "pre-define":
                self.log.debug(
                    "Creating users which are pre-defined in config")
                user = "csm_user_manage" if user_defined_role == "manage" else "csm_user_monitor"
                data = self.config[user]
                return {"username": data["username"],
                        "password": data["password"],
                        "role": user_defined_role,
                        "email": data["username"]+"@seagate.com",
                        "alert_notification": "true"}

            if user_type == "valid":
                if self.random_user:
                    user_name = "test{}{}".format(
                        int(self.random_num), int(time.time()))
                    user_role = user_defined_role
                else:
                    user_name = "test{}".format(int(time.time()))
                    user_role = user_defined_role

            if user_type == "duplicate":
                # creating new user to make it as duplicate
                self.create_csm_user()
                return self.recently_created_csm_user

            if user_type == "missing":
                return {"username": "tests3user", "role": user_defined_role}

            if user_type == "invalid":
                return {"username": "xys",  "password": "password", "role": "xyz"}

            if user_type == "invalid_for_ui":
                return {"username": "*ask%^*&", "password": "password", "role": "xyz"}

            user = "csm_user_manage" if user_defined_role == "manage" else "csm_user_monitor"
            data = self.config[user]
            user_data = {"username": user_name,
                         "password": self.config["test_csmuser_password"],
                         "role": user_role,
                         "email": user_name + "@seagate.com",
                         "alert_notification": "true"
                         }
            return user_data
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.create_payload_for_new_csm_user.__name__,
                error)
            raise CTException(
        err.CSM_REST_VERIFICATION_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def create_csm_user(self, user_type="valid", user_role="manage",
                        save_new_user=False):
        """
        This function will create new CSM user
        :param user_type: type of user required
        :param user_role: User role type.
        :param save_new_user: to store newly created user to config
        :return: response of create user
        """
        try:
            # Building request url
            self.log.debug("Creating CSM user")
            endpoint = self.config["csmuser_endpoint"]
            self.log.debug(
                "Endpoint for CSM user creation is  %s", endpoint)

            # Creating required payload to be added for request
            data = self.create_payload_for_new_csm_user(user_type, user_role)
            user_data = const.USER_DATA
            user_data = user_data.replace("testusername", data["username"]).replace(
                "user_role", data["role"])
            if user_type == "missing":
                user_data = const.MISSING_USER_DATA
                user_data = user_data.replace("testusername", data["username"]).replace(
                    "user_role", data["role"])
            self.log.debug("Payload for CSM user is %s", user_data)
            self.recently_created_csm_user = json.loads(user_data)
            self.log.debug("Recently created CSM user is %s",
                self.recently_created_csm_user)
            if save_new_user:
                self.log.debug(
                    "Adding new CSM user in csm config : new_csm_user")
                self.update_csm_config_for_user(
                    "new_csm_user", user_data["username"], user_data["password"])
            # Fetching api response
            self.headers.update(const.CONTENT_TYPE)
            return self.restapi.rest_call("post", endpoint=endpoint,
                                          data=user_data, headers=self.headers)
        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.create_csm_user.__name__,
                error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error) from error

    def create_and_verify_csm_user_creation(self, user_type, user_role,
                                            expect_status_code):
        """
        This function will create and verify new CSM user.
        :param user_type: type of user required
        :param user_role: User role type.
        :param expect_status_code: Expected status code for verification.
        :return: boolean value for Success(True)/Failure(False)
        """
        try:
            # Validating user
            if user_type not in self.user_type or user_role not in self.user_roles:
                self.log.error("Invalid user type or role")
                return False

            # Create CSM user
            response = self.create_csm_user(
                user_type=user_type, user_role=user_role)
            self.log.debug(
                "response of the create csm user is  %s", response)

            # Handling specific scenarios
            if not response.status_code:
                self.log.debug("Response is not as expected")
                return False

            if user_type != "valid":
                self.log.debug(
                    "verify status code for user %s", user_type)
                self.log.debug("Expected status code %s and Actual status code %s",
                                expect_status_code,
                                response.status_code)
                return expect_status_code == response.status_code
            # Checking status code
            self.log.debug("Response to be verified :%s",
                self.recently_created_csm_user)
            if expect_status_code != response.status_code:
                self.log.debug("Expected status code %s and Actual status code %s",
                                expect_status_code,
                                response.status_code)
                self.log.debug("Response is not as expected")
                return False

            # Checking response in details
            self.log.debug(
                "verifying Newly created CSM user data in created list")
            list_acc = self.list_csm_users(expect_status_code=const.SUCCESS_STATUS,
                                           return_actual_response=True).json()["users"]
            expected_result = self.recently_created_csm_user.copy()
            expected_result.pop("password")
            expected_result.pop("alert_notification")
            return any(config_utils.verify_json_response(actual_result,
                expected_result) for actual_result in list_acc)
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.create_and_verify_csm_user_creation.__name__,
                error)
            raise CTException(
        err.CSM_REST_VERIFICATION_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def list_csm_users(self, expect_status_code, offset=None, limit=None,
        sort_by=None, sort_dir=None, return_actual_response=False,
        verify_negative_scenario=False):
        """
        This function will list all existing csm users
        :param expect_status_code: expected status code
        :param offset: value for offset parameter <int>
        :param limit: value for limit parameter <int>
        :param sort_by: value for 'sort_by' parameter criteria used to sort csm users list
                        possible values: <username/created_time/updated_time>
        :param sort_dir: order/direction in which list should be sorted
                         possible values: <asc/desc>
        :param return_actual_response: returns actual response object <True/False>
        :param verify_negative_scenario: to verify negative scenarios <True/False>
        :return: boolean result as per the verification <True/False>
                 returns actual response if return_actual_response=True
        """
        try:
            # Building request url
            self.log.debug("Fetching csm users ...")
            endpoint = self.config["csmuser_endpoint"]

            # Adding parameters(if any) to endpoint
            parameters = {"offset": [offset, "offset="],
                          "limit": [limit, "limit="],
                          "sort_by": [sort_by, "sortby="],
                          "sort_dir": [sort_dir, "dir="]}
            params_selected = [
                value for key, value in parameters.items() if value[0] is not None]
            if len(params_selected):
                # Adding first parameter
                endpoint += '?' + \
                    params_selected[0][1] + str(params_selected[0][0])
                if len(params_selected) > 1:
                    # Adding other parameters(if any)
                    for i in range(1, len(params_selected)):
                        endpoint += '&' + \
                            params_selected[i][1] + str(params_selected[i][0])

            self.log.debug("Endpoint to list csm users is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(
                request_type="get", endpoint=endpoint, headers=self.headers)
            self.log.debug(
                "response returned is:\n %s", response.json())

            # Checking status code
            if expect_status_code == response.status_code:
                self.log.debug("Status code successfully verified\n Value:%s",
                    response.status_code)
            else:
                self.log.debug("Status code is not as expected")
                self.log.debug("Expected Value:%s   Actual Value:%s",
                    expect_status_code, response.status_code)
                return False

            # Verifying status code in case of negative scenario
            if verify_negative_scenario:
                self.log.debug("verifying response for negative scenario")
                return response.status_code == expect_status_code

            # Returning actual response object
            if return_actual_response:
                self.log.debug("Returning actual response")
                return response

            return self.verify_list_csm_users(response.json(), offset, limit, sort_by, sort_dir)
        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.list_csm_users.__name__,
                error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error) from error

    def verify_list_csm_users(self, actual_response, offset=None, limit=None,
                              sort_by=None, sort_dir=None):
        """
        This function will verify the response details for list csm users
        :param actual_response: response to be verified
        :param offset: offset value <int>
        :param limit: value for limit parameter <int>
        :param sort_by: value for 'sort_by' parameter criteria used to sort csm users list
                        possible values: <username/created_time/updated_time>
        :param sort_dir: order/direction in which list should be sorted
                         possible values: <asc/desc>
        :return: boolean verification result <True/False>
        """""
        try:
            # Fetching all created csm users
            self.log.debug(
                "fetching complete csm users list for verification purpose...")
            if sort_by is not None:
                response = self.list_csm_users(expect_status_code=200,
                                                return_actual_response=True,
                                                sort_by=sort_by)
            elif sort_dir is not None:
                response = self.list_csm_users(
                    expect_status_code=200, return_actual_response=True, sort_dir=sort_dir)
            else:
                response = self.list_csm_users(
                    expect_status_code=200, return_actual_response=True)

            # Checking status code
            if (not response) or response.status_code != const.SUCCESS_STATUS:
                self.log.debug("Response is not 200")
                return False
            expected_response = response.json()

            # Checking for verification and returning result
            if offset:
                self.log.debug("verifying response for offset parameter...")
                expected_response["users"] = expected_response["users"][offset:]
                return config_utils.verify_json_response(actual_result=actual_response,
                    expect_result=expected_response, match_exact=True)
            if limit:
                self.log.debug("verifying response for limit parameter...")
                expected_response["users"] = expected_response["users"][:limit]
                return config_utils.verify_json_response(actual_result=actual_response,
                expect_result=expected_response, match_exact=True)
            return config_utils.verify_json_response(actual_result=actual_response,
                expect_result=expected_response, match_exact=True)
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.verify_list_csm_users.__name__,
                error)
            raise CTException(
        err.CSM_REST_VERIFICATION_FAILED, error) from error

    def list_actual_num_of_csm_users(self):
        """
        Function to verify that even if the limit is greater
        than the actual users present,only the list with actual number of users
        present will be returned
        :return: boolean verification result <True/False>
        """
        try:
            # Get the count of the number of csm users present
            self.log.debug("Getting the initial list of csm users present")
            response = self.list_csm_users(
                expect_status_code=const.SUCCESS_STATUS, return_actual_response=True)
            # Checking status code
            if (not response) or response.status_code != const.SUCCESS_STATUS:
                self.log.debug("Response is not 200")
                return False

            # Checking the number of users returned
            expected_response = response.json()
            self.log.debug("Checking the number of users returned")
            existing_user_count = len(expected_response['users'])

            # Creating more csm users
            self.log.debug("Creating more csm users")
            for num_users in range(1, const.CSM_NUM_OF_USERS_TO_CREATE+1):
                response = self.create_csm_user(
                    user_type="valid", user_role="monitor")
                self.log.debug(
                    "response of the create csm user is  %s", response)
                self.log.debug("Users created %s", num_users)

            # List CSM users
            self.log.debug(
                "Setting the limit to be larger than the number of users present ")
            limit = existing_user_count + \
                const.CSM_NUM_OF_USERS_TO_CREATE + const.CSM_USER_LIST_LIMIT

            # Fetching all users for verification purpose based on tha limit provided
            self.log.debug(
                "fetching csm users list for verification purpose...")
            response = self.list_csm_users(
                limit=limit, expect_status_code=const.SUCCESS_STATUS, return_actual_response=True)
            # Checking status code
            if (not response) or response.status_code != const.SUCCESS_STATUS:
                self.log.debug("Response is not 200")
                return False

            # Verifying if the response contains the actual number of csm users
            # present, even if the limit provided was bigger
            expected_response = response.json()
            actual_num_of_users = existing_user_count + const.CSM_NUM_OF_USERS_TO_CREATE
            self.log.debug("Reading the actual number of users expected")
            expected_response["users"] = expected_response["users"][:actual_num_of_users]
            self.log.debug(
                "Verifying that even if limit is greater than the users present"
                ", only the actual number of users list is returned")
            return config_utils.verify_json_response(actual_result=response.json(),
                expect_result=expected_response, match_exact=True)
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.list_actual_num_of_csm_users.__name__,
                error)
            raise CTException(
        err.CSM_REST_VERIFICATION_FAILED, error) from error

    def verify_csm_user_list_valid_params(self):
        """
        Function to test that when all valid params such as
        offset, limit, sort and sort_dir, correct user list is returned
        :return: Verification response
        :rtype: bool
        """
        try:
            self.log.debug("Creating csm users with random count")
            self.random_user = True
            for num_users in range(1, const.CSM_NUM_OF_USERS_TO_CREATE+1):
                self.random_num = random.randint(
                    const.RANDOM_NUM_START, const.RANDOM_NUM_END)
                response = self.create_csm_user()
                # Checking status code
                if not response.status_code:
                    self.log.debug("Response is not as expected")
                    return False
                self.log.debug("Users created %s", num_users)

            # Fetching all csm users
            self.log.debug(
                "fetching all csm users without parameters specified")
            response = self.list_csm_users(
                expect_status_code=const.SUCCESS_STATUS, return_actual_response=True)
            # Checking status code
            if (not response) or response.status_code != const.SUCCESS_STATUS:
                self.log.debug("Failure in status code, returned code is %s "
                "instead of 200", response.status_code)
                return False
            self.log.debug("Storing the usernames in a list")
            user_list = [item["username"] for item in response.json()["users"]]
            user_list_before = sorted(user_list)

            # Fetching csm user list with offset, limit,sort and sort_dir specified
            self.log.debug(
                "Fetching user list with parameters offset,limit,sort_by and "
                "sort_dir specified")
            response = self.list_csm_users(limit=const.CSM_USER_LIST_LIMIT,
                                        offset=const.CSM_USER_LIST_OFFSET,
                                        sort_by=const.CSM_USER_LIST_SORT_BY,
                                        sort_dir=const.CSM_USER_LIST_SORT_DIR,
                                        expect_status_code=const.SUCCESS_STATUS,
                                        return_actual_response=True)
            # Checking status code
            if (not response) or response.status_code != const.SUCCESS_STATUS:
                self.log.debug("Failure in status code,returned code is %s "
                "instead of 200", response.status_code)
                return False
            self.log.debug("Storing the usernames in a list")
            user_list_after = [item["username"]
                               for item in response.json()["users"]]

            # Verifying that user list is returned as per the parameters specified
            self.log.debug(
                "Verifying if the user list returned is as per the offset,limit"
                ", sort_by and sort_dir parameters specified")
            if not user_list_before[
                const.CSM_USER_LIST_OFFSET:const.CSM_USER_LIST_LIMIT+const.CSM_USER_LIST_OFFSET
                ] == user_list_after:
                self.log.debug(
                    "CSM user list is not as per the parameters specified")
                self.log.debug(user_list_before)
                self.log.debug(user_list_after)
                return False
            self.log.debug(
                "User list returned is as per the parameters specified")
            return True
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.verify_csm_user_list_valid_params.__name__,
                error)
            raise CTException(
        err.CSM_REST_VERIFICATION_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def verify_list_csm_users_unauthorised_access_failure(self):
        """
        This function verifies that unauthorized access to csm api gives 403(forbidden) error
        :return: boolean verification result <True/False>
        """
        try:
            self.log.debug(
                "Checking access to csm api with s3 account authentication")
            endpoint = self.config["csmuser_endpoint"]
            self.log.debug("Endpoint to list csm users is %s", endpoint)
            # Fetching api response
            self.log.debug("Fetching the api response...")
            response = self.restapi.rest_call(
                request_type="get", endpoint=endpoint, headers=self.headers)
            self.log.debug("Response returned is %s", response)
            # Checking status code
            self.log.debug("Verifying if the status code returned is 403")
            if response.status_code == const.FORBIDDEN:
                self.log.debug("Response code returned is %s",
                    response.status_code)
                result = True
            else:
                self.log.debug("Response is not 403")
                result = False
            return result
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.verify_list_csm_users_unauthorised_access_failure.__name__,
                error)
            raise CTException(
        err.CSM_REST_VERIFICATION_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def list_csm_users_empty_param(self, expect_status_code,
        csm_list_user_param, return_actual_response=False):
        """
        This function returns response for the empty parameter provided
        :param csm_list_user_param: csm list user api parameter name
        (offset,limit,sort_by or sort_dir)
        :return: boolean result as per the verification <True/False>
                 returns actual response if return_actual_response=True
        :rtype: bool
        """
        try:
            self.log.debug(
                "Checking response when empty parameter is provided to list csm user api")

            # Validating parameter provided
            if csm_list_user_param not in self.csm_user_list_params:
                self.log.error("Invalid parameter provided!")
                return False

            endpoint = self.config["csmuser_endpoint"]
            # Forming the endpoint
            self.log.debug(
                "Forming the endpoint with empty value for the specified parameter")
            #endpoint += '?' + csm_list_user_param + '=None'
            endpoint += "{}{}{}".format("?", csm_list_user_param, "=None")
            self.log.debug("Endpoint to list csm users is %s", endpoint)

            # Fetching api response
            self.log.debug("Fetching the api response with empty parameter %s",
                csm_list_user_param)
            response = self.restapi.rest_call(
                request_type="get", endpoint=endpoint, headers=self.headers)
            self.log.debug("Response returned is %s", response)

            # Checking status code
            if expect_status_code == response.status_code:
                self.log.debug("Status code successfully verified\n Value:%s",
                    response.status_code)
            else:
                self.log.debug("Status code is not as expected")
                self.log.debug("Expected Value:%s   Actual Value:%s",
                    expect_status_code, response.status_code)
                return False

            # Returning actual response object
            if return_actual_response:
                self.log.debug("Returning actual response")
                return response

            return True
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.list_csm_users_empty_param.__name__,
                error)
            raise CTException(
        err.CSM_REST_VERIFICATION_FAILED, error) from error

    @RestTestLib.authenticate_and_login
    def list_csm_single_user(self, request_type, expect_status_code, user,
        payload=None, data=False, params=False, return_actual_response=False):
        """
        This function returns trues/false verification response or json
        response for single csm user
        :param request_type: request type of the request
        :param expect_status_code:Expected status code for verification
        :param user: csm user info
        :param payload: payload for the request
        :param data: data to be provided in the request if true
        :param params: parameters to be provided in the request if true
        :param return_actual_response: actual response to return
        :return: boolean result as per the verification <True/False>
                 returns actual response if return_actual_response=True
        :rtype: bool/response
        """
        try:
            headers = {}
            headers.update(self.headers)
            endpoint = self.config["csmuser_endpoint"]
            # Forming the endpoint
            self.log.debug(
                "Forming the endpoint for the csm user")
            endpoint += "{}{}".format("/", user)
            self.log.debug("Endpoint to list csm user is %s", endpoint)

            if params:
                # Fetching api response with parameters in the request
                self.log.debug(
                    "Fetching api response for the csm user %s with parameters"
                    " in the request", user)
                response = self.restapi.rest_call(
                    request_type=request_type, endpoint=endpoint, params=payload, headers=headers)
            if data:
                # Fetching api response with data in the request
                self.log.debug(
                    "Fetching api response for the csm user %s with data in the request", user)
                headers.update(const.CONTENT_TYPE)
                response = self.restapi.rest_call(
                    request_type=request_type, endpoint=endpoint, data=payload,
                    headers=headers)
            else:
                # Fetching api response for the request
                self.log.debug(
                    "Fetching api response for the csm user %s", user)
                response = self.restapi.rest_call(
                    request_type=request_type, endpoint=endpoint, headers=headers)

            # Checking status code
            if expect_status_code == response.status_code:
                self.log.debug("Status code successfully verified\n Value:%s",
                    response.status_code)
            else:
                self.log.debug("Status code is not as expected")
                self.log.debug("Expected Value:%s\n   Actual Value:%s",
                    expect_status_code, response.status_code)
                return False

            # Returning actual response object
            if return_actual_response:
                self.log.debug("Returning actual response")
                return response

            return True
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.list_csm_single_user.__name__,
                error)
            raise CTException(
        err.CSM_REST_VERIFICATION_FAILED, error) from error

    def verify_modify_csm_user(self, user, payload_login, expect_status_code,
        return_actual_response=False):
        """
        This function verifies the modified csm user
        :param user: csm user info
        :type user: string
        :param payload_login: payload for the login request
        :type payload_login: json
        :param expect_status_code:Expected status code for verification
        :type expect_status_code: int
        :param request_type: request type of the request
        :type request_type: string
        :param return_actual_response: actual response to return
        :type return_actual_response: bool
        :return: boolean result as per the verification <True/False>
                 returns actual response if return_actual_response=True
        :rtype: bool/response
        """
        try:
            headers = {}
            self.log.debug("Logging in as csm user %s", user)
            response = self.restapi.rest_call(
                request_type="post",
                endpoint=self.config["rest_login_endpoint"],
                data=payload_login,
                headers=self.config["Login_headers"])
            self.log.debug("response :  %s",response)
            if response.status_code == const.SUCCESS_STATUS:
                headers.update(
                    {'Authorization': response.headers['Authorization']})

            endpoint = self.config["csmuser_endpoint"]
            # Forming the endpoint
            self.log.debug(
                "Forming the csm endpoint")
            endpoint += "{}{}".format("/", user)
            self.log.debug("Endpoint to list csm user is %s", endpoint)
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint, headers=headers)

            # Checking status code
            if expect_status_code == response.status_code:
                self.log.debug("Status code successfully verified\n Value:%s",
                    response.status_code)
            else:
                self.log.debug("Status code is not as expected")
                self.log.debug("Expected Value:%s   Actual Value:%s",
                    expect_status_code, response.status_code)
                return False

            # Returning actual response object
            if return_actual_response:
                self.log.debug("Returning actual response")
                return response

            return True
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.verify_modify_csm_user.__name__,
                error)
            raise CTException(
        err.CSM_REST_VERIFICATION_FAILED, error) from error

    def revert_csm_user_password(self, username, current_password, old_password,
    return_actual_response=False):
        """
        This function reverts the csm root password if it is updated
        :param current_password: updated csm root password
        :type user: string
        :param return_actual_response: actual response to return
        :type return_actual_response: bool
        :return: boolean result as per the verification <True/False>
                 returns actual response if return_actual_response=True
        :rtype: bool/response
        """
        try:
            headers = {}
            headers.update(const.CONTENT_TYPE)

            self.log.debug(
                "Reverting old password %s for csm user %s", old_password, username)

            self.log.debug(
                "Logging in with current password %s", current_password)
            payload_login = {"username": username,
                             "password": current_password}
            self.log.debug(
                "Payload for the login is : %s", payload_login)
            response = self.restapi.rest_call(request_type="post",
                                              endpoint=self.config["rest_login_endpoint"],
                                              data=json.dumps(payload_login), headers=headers)
            self.log.debug("response is : %s", response)

            if response.status_code == const.SUCCESS_STATUS:
                headers.update({
                    'Authorization': response.headers['Authorization']})

            endpoint = self.config["csmuser_endpoint"]
            # Forming the endpoint
            self.log.debug(
                "Forming the csm endpoint")
            endpoint = f"{endpoint}/{username}"
            self.log.debug("Endpoint to list csm user is %s", endpoint)

            payload = {"current_password": current_password,
                       "password": old_password}
            self.log.debug(
                "Payload for reverting password is: %s", payload)

            self.log.debug("Fetching the response...")
            response = self.restapi.rest_call(
                request_type="patch", endpoint=endpoint, data=json.dumps(payload), headers=headers)

            # Returning actual response object
            if return_actual_response:
                self.log.debug("Returning actual response")
                return response
            return True
        except Exception as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.revert_csm_user_password.__name__,
                error)
            raise CTException(
        err.CSM_REST_VERIFICATION_FAILED, error) from error

    def verify_user_exits(self, user: str) -> bool:
        """
        verify if the user exists on the csm.
        :param user: csm user name.
        :type user: str.
        :return: True if user found else False.
        :rtype: bool.
        """
        users = self.list_csm_users(const.SUCCESS_STATUS,
                                    return_actual_response=True)
        self.log.debug(f"List csm users response: {users.json()}")
        found = False
        for usr in users.json()['users']:
            if user == usr['username']:
                self.log.debug(
                    f"Inside loop: user: {user}, username: {usr['username']}")
                found = True
                break

        return found

    @RestTestLib.authenticate_and_login
    def delete_csm_user(self, user_id):
        """
        This function will create new CSM user
        :param user_type: type of user required
        :param user_role: User role type.
        :param save_new_user: to store newly created user to config
        :return obj: response of delete user operation
        """
        try:
            # Building request url
            self.log.debug("Deleting CSM user")
            endpoint = self.config["csmuser_endpoint"]
            endpoint = f"{endpoint}/{user_id}"
            self.log.debug(
                "Endpoint for CSM user creation is  %s", endpoint)

            # Fetching api response
            self.headers.update(const.CONTENT_TYPE)
            return self.restapi.rest_call("delete", endpoint=endpoint, headers=self.headers)

        except BaseException as error:
            self.log.error("%s %s: %s",
                const.EXCEPTION_ERROR,
                RestCsmUser.delete_csm_user.__name__,
                error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error) from error

    @RestTestLib.authenticate_and_login
    def update_csm_account_password(self, username, old_password, new_password):
        """
        This function will update csm account user password
        :param username: Username
        :param old_password: Old Password
        :param new_password: New Password
        :return: Success(True)/Failure(False)
        """
        try:
            self.log.debug(
                f"Changing password of csm user {username} from {old_password} to "
                f"{new_password}")
            # Prepare patch for s3 account user
            patch_payload = {
                "password": new_password,
                "current_password": old_password
            }
            self.log.debug("editing user {}".format(patch_payload))
            endpoint = "{}/{}".format(self.config["csmuser_endpoint"], username)
            self.log.debug("Endpoint for s3 accounts is {}".format(endpoint))

            # Log in using old password and get headers
            headers = self.get_headers(username, old_password)
            patch_payload = json.dumps(patch_payload)

            # Fetching api response
            response = self.restapi.rest_call("patch", data=patch_payload, endpoint=endpoint,
                                              headers=headers)
        except Exception as error:
            self.log.error("{0} {1}: {2}".format(
                const.EXCEPTION_ERROR,
                RestCsmUser.update_csm_account_password.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

        if response.status_code != const.SUCCESS_STATUS:
            self.log.error(f"Response code : {response.status_code}")
            self.log.error(f"Response content: {response.content}")
            self.log.error(f"Request headers : {response.request.headers}\n"
                           f"Request body : {response.request.body}")
            raise CTException(err.CSM_REST_GET_REQUEST_FAILED,
                              msg="CSM user password change request failed.")

    @RestTestLib.authenticate_and_login
    def edit_csm_user(self, user:str=None, role:str=None, email:str=None, password:str=None, current_password:str=None):
        endpoint = self.config["csmuser_endpoint"] + "/" + user
        patch_payload = {}
        if role is not None:
            patch_payload.update({"role":role})
        if email is not None:
            patch_payload.update({"email":email})
        if password is not None:
            patch_payload.update({"password":password})
        if current_password is not None:
            patch_payload.update({"current_password":current_password})
        self.log.info(patch_payload)
        response = self.restapi.rest_call("patch", data=patch_payload, endpoint=endpoint,
                                              headers=self.headers)
        return response

