"""Test library for CSM user related operations."""
import time
import json
import random
from commons.constants import Rest as const
import commons.errorcodes as err
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_test_lib import RestTestLib as Base

class RestCsmUser(Base):
    """RestCsmUser contains all the Rest API calls for csm user operations"""

    def __init__(self):
        super(RestCsmUser, self).__init__()
        self.recently_created_csm_user = None
        self.recent_patch_payload = None
        self.user_type = ("valid", "duplicate", "invalid", "missing")
        self.user_roles = ["manage", "monitor"]
        self.random_user = False
        self.random_num = 0
        self.csm_user_list_params = ("offset", "limit", "sort_by", "sort_dir")

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
                self._log.info(
                    "Creating users which are pre-defined in config")
                user = "csm_user_manage" if user_defined_role == "manage" else "csm_user_monitor"
                data = self.config[user]
                return {"username": data["username"],
                        "password": data["password"],
                        "roles": [user_defined_role],
                        "email": data["username"]+"@seagate.com",
                        "alert_notification": "true"}

            if user_type == "valid":
                if self.random_user:
                    user_name, user_role = "test{}{}".format(
                        int(self.random_num), int(time.time())), [user_defined_role]
                else:
                    user_name, user_role = "test{}".format(int(time.time())), [
                        user_defined_role]

            if user_type == "duplicate":
                # creating new user to make it as duplicate
                self.create_csm_user()
                return self.recently_created_csm_user

            if user_type == "missing":
                return {"username": "tests3user", "roles": [user_defined_role]}

            if user_type == "invalid":
                return {"username": "xys",  "password": "password", "roles": ["xyz"]}

            if user_type == "invalid_for_ui":
                return {"username": "*ask%^*&", "password": "password", "roles": ["xyz"]}

            user = "csm_user_manage" if user_defined_role == "manage" else "csm_user_monitor"
            data = self.config[user]
            user_data = {"username": user_name,
                         "password": self.config["test_csmuser_password"],
                         "roles": user_role,
                         "email": user_name + "@seagate.com",
                         "alert_notification": "true"
                         }
            return user_data
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.create_payload_for_new_csm_user.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    @Base.authenticate_and_login
    def create_csm_user(self, user_type="valid", user_role="manage", save_new_user=False):
        """
        This function will create new CSM user
        :param user_type: type of user required
        :param user_role: User role type.
        :param save_new_user: to store newly created user to config
        :return: response of create user
        """
        try:
            # Building request url
            self._log.info("Creating CSM user")
            endpoint = self.config["csmuser_endpoint"]
            self._log.info(
                "Endpoint for CSM user creation is  {}".format(endpoint))

            # Creating required payload to be added for request
            data = self.create_payload_for_new_csm_user(user_type, user_role)
            user_data = const.USER_DATA
            user_data = user_data.replace("testusername", data["username"]).replace(
                "user_role", data["roles"][0])
            if user_type == "missing":
                user_data = const.MISSING_USER_DATA
                user_data = user_data.replace("testusername", data["username"]).replace(
                    "user_role", data["roles"][0])
            self._log.info("Payload for CSM user is {}".format(user_data))
            self.recently_created_csm_user = json.loads(user_data)
            self._log.info("Recently created CSM user is {}".format(
                self.recently_created_csm_user))
            if save_new_user:
                self._log.info(
                    "Adding new CSM user in csm config : new_csm_user")
                self.update_csm_config_for_user(
                    "new_csm_user", user_data["username"], user_data["password"])
            # Fetching api response
            self.headers.update(const.CONTENT_TYPE)
            return self.restapi.rest_call("post", endpoint=endpoint, data=user_data, headers=self.headers)
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.create_csm_user.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0])

    def create_and_verify_csm_user_creation(self, user_type, user_role, expect_status_code):
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
                self._log.error("Invalid user type or role")
                return False

            # Create CSM user
            response = self.create_csm_user(
                user_type=user_type, user_role=user_role)
            self._log.info(
                "response of the create csm user is  {}".format(response))

            # Handling specific scenarios
            if not response.status_code:
                self._log.info("Response is not as expected")
                return False

            if user_type != "valid":
                self._log.info(
                    "verify status code for user {}".format(user_type))
                self._log.info("Expected status code {} and Actual status code {}".format(expect_status_code,
                                                                                          response.status_code))
                return expect_status_code == response.status_code

            # Checking status code
            self._log.info("Response to be verified :{}".format(
                self.recently_created_csm_user))
            if expect_status_code != response.status_code:
                self._log.info("Expected status code {} and Actual status code {}".format(expect_status_code,
                                                                                          response.status_code))
                self._log.info("Response is not as expected")
                return False

            # Checking response in details
            self._log.info(
                "verifying Newly created CSM user data in created list")
            list_acc = self.list_csm_users(expect_status_code=self.const.SUCCESS_STATUS,
                                           return_actual_response=True).json()["users"]
            expected_result = self.recently_created_csm_user.copy()
            expected_result.pop("password")
            expected_result.pop("alert_notification")
            return any(self.verify_json_response(actual_result, expected_result) for actual_result in list_acc)
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.create_and_verify_csm_user_creation.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    @Base.authenticate_and_login
    def list_csm_users(self, expect_status_code, offset=None, limit=None, sort_by=None, sort_dir=None,
                       return_actual_response=False, verify_negative_scenario=False):
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
            self._log.info("Fetching csm users ...")
            endpoint = self.config["csmuser_endpoint"]

            # Adding parameters(if any) to endpoint
            parameters = {"offset": [offset, "offset="], "limit": [limit, "limit="], "sort_by": [sort_by, "sort_by="],
                          "sort_dir": [sort_dir, "sort_dir="]}
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

            self._log.info("Endpoint to list csm users is {}".format(endpoint))

            # Fetching api response
            response = self.restapi.rest_call(
                request_type="get", endpoint=endpoint, headers=self.headers)
            self._log.info(
                "response returned is:\n {}".format(response.json()))

            # Checking status code
            if expect_status_code == response.status_code:
                self._log.info("Status code successfully verified\n Value:{}".format(
                    response.status_code))
            else:
                self._log.info("Status code is not as expected")
                self._log.info("Expected Value:{}   Actual Value:{}".format(
                    expect_status_code, response.status_code))
                return False

            # Verifying status code in case of negative scenario
            if verify_negative_scenario:
                self._log.info("verifying response for negative scenario")
                return response.status_code == expect_status_code

            # Returning actual response object
            if return_actual_response:
                self._log.info("Returning actual response")
                return response

            return self.verify_list_csm_users(response.json(), offset, limit, sort_by, sort_dir)
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.list_csm_users.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0])

    def verify_list_csm_users(self, actual_response, offset=None, limit=None, sort_by=None, sort_dir=None):
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
            self._log.info(
                "fetching complete csm users list for verification purpose...")
            if sort_by is not None:
                response = self.list_csm_users(
                    expect_status_code=200, return_actual_response=True, sort_by=sort_by)
            elif sort_dir is not None:
                response = self.list_csm_users(
                    expect_status_code=200, return_actual_response=True, sort_dir=sort_dir)
            else:
                response = self.list_csm_users(
                    expect_status_code=200, return_actual_response=True)

            # Checking status code
            if (not response) or response.status_code != self.const.SUCCESS_STATUS:
                self._log.info("Response is not 200")
                return False
            expected_response = response.json()

            # Checking for verification and returning result
            if offset:
                self._log.info("verifying response for offset parameter...")
                expected_response["users"] = expected_response["users"][offset:]
                return self.verify_json_response(actual_result=actual_response, expect_result=expected_response,
                                                 match_exact=True)
            if limit:
                self._log.info("verifying response for limit parameter...")
                expected_response["users"] = expected_response["users"][:limit]
                return self.verify_json_response(actual_result=actual_response, expect_result=expected_response,
                                                 match_exact=True)
            return self.verify_json_response(actual_result=actual_response, expect_result=expected_response,
                                             match_exact=True)
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.verify_list_csm_users.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def list_actual_num_of_csm_users(self):
        """
        Function to verify that even if the limit is greater 
        than the actual users present,only the list with actual number of users present will be returned 
        :return: boolean verification result <True/False>     
        """

        try:
            # Get the count of the number of csm users present
            self._log.info("Getting the initial list of csm users present")
            response = self.list_csm_users(
                expect_status_code=self.const.SUCCESS_STATUS, return_actual_response=True)
            # Checking status code
            if (not response) or response.status_code != self.const.SUCCESS_STATUS:
                self._log.info("Response is not 200")
                return False

            # Checking the number of users returned
            expected_response = response.json()
            self._log.info("Checking the number of users returned")
            existing_user_count = len(expected_response['users'])

            # Creating more csm users
            self._log.info("Creating more csm users")
            for num_users in range(1, const.CSM_NUM_OF_USERS_TO_CREATE+1):
                response = self.create_csm_user(
                    user_type="valid", user_role="monitor")
                self._log.info(
                    "response of the create csm user is  {}".format(response))
                self._log.info("Users created {}".format(num_users))

            # List CSM users
            self._log.info(
                "Setting the limit to be larger than the number of users present ")
            limit = existing_user_count + \
                const.CSM_NUM_OF_USERS_TO_CREATE + const.CSM_USER_LIST_LIMIT

            # Fetching all users for verification purpose based on tha limit provided
            self._log.info(
                "fetching csm users list for verification purpose...")
            response = self.list_csm_users(
                limit=limit, expect_status_code=self.const.SUCCESS_STATUS, return_actual_response=True)
            # Checking status code
            if (not response) or response.status_code != self.const.SUCCESS_STATUS:
                self._log.info("Response is not 200")
                return False

            # Verifying if the response contains the actual number of csm users present, even if the limit provided was bigger
            expected_response = response.json()
            actual_num_of_users = existing_user_count + const.CSM_NUM_OF_USERS_TO_CREATE
            self._log.info("Reading the actual number of users expected")
            expected_response["users"] = expected_response["users"][:actual_num_of_users]
            self._log.info(
                "Verifying that even if limit is greater than the users present, only the actual number of users list is returned")
            return self.verify_json_response(actual_result=response.json(), expect_result=expected_response,
                                             match_exact=True)
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.list_actual_num_of_csm_users.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def verify_csm_user_list_valid_params(self):
        """
        Function to test that when all valid params such as 
        offset, limit, sort and sort_dir, correct user list is returned
        :return: Verification response
        :rtype: bool
        """
        try:
            self._log.info("Creating csm users with random count")
            self.random_user = True
            for num_users in range(1, const.CSM_NUM_OF_USERS_TO_CREATE+1):
                self.random_num = random.randint(
                    const.RANDOM_NUM_START, const.RANDOM_NUM_END)
                response = self.create_csm_user()
                # Checking status code
                if not response.status_code:
                    self._log.info("Response is not as expected")
                    return False
                self._log.info("Users created {}".format(num_users))

            # Fetching all csm users
            self._log.info(
                "fetching all csm users without parameters specified")
            response = self.list_csm_users(
                expect_status_code=self.const.SUCCESS_STATUS, return_actual_response=True)
            # Checking status code
            if (not response) or response.status_code != self.const.SUCCESS_STATUS:
                self._log.info("Failure in status code, returned code is {} instead of 200".format(
                    response.status_code))
                return False
            self._log.info("Storing the usernames in a list")
            user_list = [item["username"] for item in response.json()["users"]]
            user_list_before = sorted(user_list)

            # Fetching csm user list with offset, limit,sort and sort_dir specified
            self._log.info(
                "Fetching user list with parameters offset,limit,sort_by and sort_dir specified")
            response = self.list_csm_users(limit=const.CSM_USER_LIST_LIMIT, offset=const.CSM_USER_LIST_OFFSET, sort_by=const.CSM_USER_LIST_SORT_BY,
                                           sort_dir=const.CSM_USER_LIST_SORT_DIR, expect_status_code=self.const.SUCCESS_STATUS, return_actual_response=True)
            # Checking status code
            if (not response) or response.status_code != self.const.SUCCESS_STATUS:
                self._log.info("Failure in status code,returned code is {} instead of 200".format(
                    response.status_code))
                return False
            self._log.info("Storing the usernames in a list")
            user_list_after = [item["username"]
                               for item in response.json()["users"]]

            # Verifying that user list is returned as per the parameters specified
            self._log.info(
                "Verifying if the user list returned is as per the offset,limit, sort_by and sort_dir parameters specified")
            if not user_list_before[const.CSM_USER_LIST_OFFSET:const.CSM_USER_LIST_LIMIT+const.CSM_USER_LIST_OFFSET] == user_list_after:
                self._log.info(
                    "CSM user list is not as per the parameters specified")
                self._log.info(user_list_before)
                self._log.info(user_list_after)
                return False
            self._log.info(
                "User list returned is as per the parameters specified")
            return True
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.verify_csm_user_list_valid_params.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    @Base.authenticate_and_login
    def verify_list_csm_users_unauthorised_access_failure(self):
        """
        This function verifies that unauthorized access to csm api gives 403(forbidden) error
        :return: boolean verification result <True/False>
        """
        try:
            self._log.info(
                "Checking access to csm api with s3 account authentication")
            endpoint = self.config["csmuser_endpoint"]
            self._log.info("Endpoint to list csm users is {}".format(endpoint))
            # Fetching api response
            self._log.info("Fetching the api response...")
            response = self.restapi.rest_call(
                request_type="get", endpoint=endpoint, headers=self.headers)
            self._log.info("Response returned is {}".format(response))
            # Checking status code
            self._log.info("Verifying if the status code returned is 403")
            if response.status_code == const.FORBIDDEN:
                self._log.info("Response code returned is {}".format(
                    response.status_code))
                result = True
            else:
                self._log.info("Response is not 403")
                result = False
            return result
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.verify_list_csm_users_unauthorised_access_failure.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    @Base.authenticate_and_login
    def list_csm_users_empty_param(self, expect_status_code, csm_list_user_param, return_actual_response=False):
        """
        This function returns response for the empty parameter provided 
        :param csm_list_user_param: csm list user api parameter name(offset,limit,sort_by or sort_dir)
        :return: boolean result as per the verification <True/False>
                 returns actual response if return_actual_response=True
        :rtype: bool
        """
        try:
            self._log.info(
                "Checking response when empty parameter is provided to list csm user api")

            # Validating parameter provided
            if csm_list_user_param not in self.csm_user_list_params:
                self._log.error("Invalid parameter provided!")
                return False

            endpoint = self.config["csmuser_endpoint"]
            # Forming the endpoint
            self._log.info(
                "Forming the endpoint with empty value for the specified parameter")
            #endpoint += '?' + csm_list_user_param + '=None'
            endpoint += "{}{}{}".format("?", csm_list_user_param, "=None")
            self._log.info("Endpoint to list csm users is {}".format(endpoint))

            # Fetching api response
            self._log.info("Fetching the api response with empty parameter {}". format(
                csm_list_user_param))
            response = self.restapi.rest_call(
                request_type="get", endpoint=endpoint, headers=self.headers)
            self._log.info("Response returned is {}".format(response))

            # Checking status code
            if expect_status_code == response.status_code:
                self._log.info("Status code successfully verified\n Value:{}".format(
                    response.status_code))
            else:
                self._log.info("Status code is not as expected")
                self._log.info("Expected Value:{}   Actual Value:{}".format(
                    expect_status_code, response.status_code))
                return False

            # Returning actual response object
            if return_actual_response:
                self._log.info("Returning actual response")
                return response

            return True
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.list_csm_users_empty_param.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    @Base.authenticate_and_login
    def list_csm_single_user(self, request_type, expect_status_code, user, payload=None, data=False, params=False, return_actual_response=False):
        """
        This function returns trues/false verification response or json response for single csm user
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
            self._log.info(
                "Forming the endpoint for the csm user")
            endpoint += "{}{}".format("/", user)
            self._log.info("Endpoint to list csm user is {}".format(endpoint))

            if params:
                # Fetching api response with parameters in the request
                self._log.info(
                    "Fetching api response for the csm user {} with parameters in the request".format(user))
                response = self.restapi.rest_call(
                    request_type=request_type, endpoint=endpoint, params=payload, headers=headers)
            if data:
                # Fetching api response with data in the request
                self._log.info(
                    "Fetching api response for the csm user {} with data in the request".format(user))
                headers.update(const.CONTENT_TYPE)
                response = self.restapi.rest_call(
                    request_type=request_type, endpoint=endpoint, data=payload, headers=headers)
            else:
                # Fetching api response for the request
                self._log.info(
                    "Fetching api response for the csm user {}".format(user))
                response = self.restapi.rest_call(
                    request_type=request_type, endpoint=endpoint, headers=headers)

            # Checking status code
            if expect_status_code == response.status_code:
                self._log.info("Status code successfully verified\n Value:{}".format(
                    response.status_code))
            else:
                self._log.info("Status code is not as expected")
                self._log.info("Expected Value:{}   Actual Value:{}".format(
                    expect_status_code, response.status_code))
                return False

            # Returning actual response object
            if return_actual_response:
                self._log.info("Returning actual response")
                return response

            return True
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.list_csm_single_user.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def verify_modify_csm_user(self, user, payload_login, expect_status_code, return_actual_response=False):
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
            self._log.info("Logging in as csm user {}".format(user))
            response = self.restapi.rest_call(request_type="post",
                                              endpoint=self.config["rest_login_endpoint"],
                                              data=payload_login, headers=self.config["Login_headers"])
            self._log.info("response : ", response)
            if response.status_code == self.const.SUCCESS_STATUS:
                headers.update(
                    {'Authorization': response.headers['Authorization']})

            endpoint = self.config["csmuser_endpoint"]
            # Forming the endpoint
            self._log.info(
                "Forming the csm endpoint")
            endpoint += "{}{}".format("/", user)
            self._log.info("Endpoint to list csm user is {}".format(endpoint))
            response = self.restapi.rest_call(request_type="get",
                                              endpoint=endpoint, headers=headers)

            # Checking status code
            if expect_status_code == response.status_code:
                self._log.info("Status code successfully verified\n Value:{}".format(
                    response.status_code))
            else:
                self._log.info("Status code is not as expected")
                self._log.info("Expected Value:{}   Actual Value:{}".format(
                    expect_status_code, response.status_code))
                return False

            # Returning actual response object
            if return_actual_response:
                self._log.info("Returning actual response")
                return response

            return True
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.verify_modify_csm_user.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def revert_csm_user_password(self, username, current_password, old_password, return_actual_response=False):
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

            self._log.info(
                "Reverting old password {} for csm user {}".format(old_password, username))

            self._log.info(
                "Logging in with current password {}".format(current_password))
            payload_login = {"username": username,
                             "password": current_password}
            self._log.info(
                "Payload for the login is : {}".format(payload_login))
            response = self.restapi.rest_call(request_type="post",
                                              endpoint=self.config["rest_login_endpoint"],
                                              data=json.dumps(payload_login), headers=headers)
            self._log.info("response is : {}".format(response))

            if response.status_code == const.SUCCESS_STATUS:
                headers.update({
                    'Authorization': response.headers['Authorization']})

            endpoint = self.config["csmuser_endpoint"]
            # Forming the endpoint
            self._log.info(
                "Forming the csm endpoint")
            endpoint = f"{endpoint}/{username}"
            self._log.info("Endpoint to list csm user is {}".format(endpoint))

            payload = {"current_password": current_password,
                       "password": old_password}
            self._log.info(
                "Payload for reverting password is: {}".format(payload))

            self._log.info("Fetching the response...")
            response = self.restapi.rest_call(
                request_type="patch", endpoint=endpoint, data=json.dumps(payload), headers=headers)

            # Returning actual response object
            if return_actual_response:
                self._log.info("Returning actual response")
                return response
            return True
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.revert_csm_user_password.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def verify_user_exits(self, user: str) -> bool:
        """
        verify if the user exists on the csm.
        :param user: csm user name.
        :type user: str.
        :return: True if user found else False.
        :rtype: bool.
        """
        users = self.list_csm_users(self.const.SUCCESS_STATUS,
                                    return_actual_response=True)
        self._log.info(f"List csm users response: {users.json()}")
        found = False
        for usr in users.json()['users']:
            if user == usr['username']:
                self._log.info(f"Inside loop: user: {user}, username: {usr['username']}")
                found = True
                break

        return found

    @Base.authenticate_and_login
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
            self._log.info("Deleting CSM user")
            endpoint = self.config["csmuser_endpoint"]
            endpoint = f"{endpoint}/{user_id}"
            self._log.info(
                "Endpoint for CSM user creation is  {}".format(endpoint))

            # Fetching api response
            self.headers.update(const.CONTENT_TYPE)
            return self.restapi.rest_call("delete", endpoint=endpoint, headers=self.headers)

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestCsmUser.delete_csm_user.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0])
