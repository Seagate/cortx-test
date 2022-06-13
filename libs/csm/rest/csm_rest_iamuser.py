#Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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
"""Test library for IAM user related operations."""
import json
import time
from http import HTTPStatus
from random import SystemRandom
from string import Template
import yaml
from requests.models import Response
import commons.errorcodes as err
from commons import commands as common_cmd
from commons.constants import Rest as const
from commons import constants as cons
from commons.constants import S3_ENGINE_RGW
from commons.exceptions import CTException
from commons.utils import config_utils
from config import CMN_CFG, CSM_REST_CFG
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_test_lib import RestTestLib

# pylint: disable-msg=too-many-public-methods
class RestIamUser(RestTestLib):
    """RestIamUser contains all the Rest API calls for iam user operations"""

    def __init__(self):
        super(RestIamUser, self).__init__()
        self.template_payload = Template(const.IAM_USER_DATA_PAYLOAD)
        self.iam_user = None
        self.csm_user = RestCsmUser()
        self.cryptogen = SystemRandom()

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
    def get_iam_user(self, user):
        """
        This function will get iam user details
        :param user: userid.
        :return: response
        """
        response = self.get_iam_user_rgw(user, self.headers)
        return response

    @RestTestLib.authenticate_and_login
    def delete_iam_user(self, user=None, purge_data=None):
        """
        This function will delete user
        :param user: userid of user
        :param purge_data: if True, deletes user created data.
        :return: response
        """
        if self.iam_user and (not user):
            user = self.iam_user
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            response = self.delete_iam_user_rgw(user, self.headers, purge_data)
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
    def list_iam_users(self, max_entries=None, marker=None):
        """
        This function will list all IAM users.
        :param max_entries: Number of users to be returned
        :param marker: Name of user from which specified number of users to be returned
        :return: response
        :rtype: response object
        """
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            response = self.list_iam_users_rgw(max_entries=max_entries, marker=marker)
        else:
            self.log.debug("Listing of iam users")
            endpoint = self.config["IAM_users_endpoint"]
            self.log.debug("Endpoint for iam user is %s", endpoint)

            self.headers.update(self.config["Login_headers"])

            # Fetching api response
            response = self.restapi.rest_call(
                "get", endpoint=endpoint, headers=self.headers)
        return response

    # pylint: disable-msg=too-many-branches
    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-return-statements
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

    @staticmethod
    def iam_user_optional_payload_rgw(payload):
        """
            Get optional parameters
        """
        user_id = payload["uid"]
        email = user_id + "@seagate.com"
        key_type = "s3"
        access_key = user_id.ljust(const.S3_ACCESS_LL, "d")
        secret_key = config_utils.gen_rand_string(length=const.S3_SECRET_LL)
        user_cap = "users=*"
        generate_key = True
        max_buckets = 1000
        suspended = False
        tenant = "abc"
        payload.update({"email": email})
        payload.update({"key_type": key_type})
        payload.update({"access_key": access_key})
        payload.update({"secret_key": secret_key})
        payload.update({"user_caps": user_cap})
        payload.update({"generate_key": generate_key})
        payload.update({"max_buckets": max_buckets})
        payload.update({"suspended": suspended})
        payload.update({"tenant": tenant})
        return payload

    def iam_user_payload_rgw(self, user_type="valid"):
        """
        Return payload for IAM user for RGW with Ceph
        """
        # Initialize all variables
        payload = {}
        user_id = const.IAM_USER + str(int(time.time_ns()))
        display_name = const.IAM_USER + str(int(time.time_ns()))
        payload.update({"uid": user_id})
        payload.update({"display_name": display_name})
        if user_type == "loaded":
            payload = self.iam_user_optional_payload_rgw(payload)
        elif user_type == "random":
            payload = self.iam_user_optional_payload_rgw(payload)
            del payload["uid"]
            del payload["display_name"]
            optional_payload = payload.copy()
            ran_sel = self.cryptogen.sample(list(range(0, len(optional_payload))),
                                    self.cryptogen.randrange(0, len(optional_payload)))
            for i, (k, _) in enumerate(payload.items()):
                if i not in ran_sel:
                    del optional_payload[k]
            optional_payload.update({"uid": user_id})
            optional_payload.update({"display_name": display_name})
            payload = optional_payload.copy()
        self.log.info("Payload : %s", payload)
        return payload

    @staticmethod
    def compare_iam_payload_response(rest_response, payload):
        """
            Compare rest response with expected response
        """
        payload["user_id"] = payload.pop("uid")
        if "user_caps" in payload:
            payload["caps"] = payload.pop("user_caps")
        for key, value in payload.items():
            if key in rest_response:
                if key == 'caps':
                    continue
                if key == "suspended":
                    expected_val = 0
                    if value:
                        expected_val = 1
                    if rest_response[key] != expected_val:
                        return False, key, expected_val, rest_response[key]
                if key == "access_key":
                    if value != rest_response["keys"][0]["access_key"]:
                        return False, key, value, rest_response["keys"][0]["access_key"]
                elif key == "secret_key":
                    if value != rest_response["keys"][0]["secret_key"]:
                        return False, key, value, rest_response["keys"][0]["secret_key"]
                elif rest_response[key] != value:
                    return False, key, value, rest_response[key]
        return True, None

    @RestTestLib.authenticate_and_login
    def create_iam_user_rgw(self, payload: dict):
        """
        Creates IAM user for given payload.
        :param payload: payload for user creation
        :return: response
        """
        self.log.info("Creating IAM user request....")
        endpoint = self.config["s3_iam_user_endpoint"]
        response = self.restapi.rest_call("post", endpoint=endpoint, json_dict=payload,
                                          headers=self.headers)
        self.log.info("IAM user request successfully sent...")
        return response

    @RestTestLib.authenticate_and_login
    def add_user_caps_rgw(self, uid, payload: dict):
        """
        Add capabilities to user
        :param uid: uid of user
        :param payload: payload for adding capabilities
        :return: response
        """
        self.log.info("Adding user capabilities to user....")
        endpoint = CSM_REST_CFG["s3_iam_caps_endpoint"] + "/" + uid
        response = self.restapi.rest_call("put", endpoint=endpoint, json_dict=payload,
                                          headers=self.headers)
        self.log.info("Adding user capabilities to user request successfully sent...")
        return response

    @RestTestLib.authenticate_and_login
    def remove_user_caps_rgw(self, uid, payload: dict):
        """
        Remove capabilities from user
        :param uid: uid of user
        :param payload: payload for removing capabilities
        :return: response
        """
        self.log.info("Removing user capabilities from user....")
        endpoint = CSM_REST_CFG["s3_iam_caps_endpoint"] + "/" + uid
        response = self.restapi.rest_call("delete", endpoint=endpoint, json_dict=payload,
                                          headers=self.headers)
        self.log.info("Removing user capabilities from user request successfully sent...")
        return response

    @RestTestLib.authenticate_and_login
    def delete_iam_user_rgw(self, uid, header, purge_data=None):
        """
        Delete IAM user
        :param uid: userid
        :param header: header for api authentication
        :param purge_data: If true, delete users data
        :return: response
        """
        self.log.info("Delete IAM user request....")
        endpoint = CSM_REST_CFG["s3_iam_user_endpoint"] + "/" + uid
        if purge_data is not None:
            payload = {"purge_data": purge_data}
        else:
            payload = None
        response = self.restapi.rest_call("delete", endpoint=endpoint, json_dict=payload,
                                          headers=header)
        self.log.info("Delete IAM user request successfully sent...")
        return response

    @RestTestLib.authenticate_and_login
    def get_iam_user_rgw(self, uid, header):
        """
        Get IAM user
        :param uid: userid
        :param header: header for api authentication
        :return: response
        """
        self.log.info("Get IAM user request....")
        endpoint = CSM_REST_CFG["s3_iam_user_endpoint"] + "/" + uid
        response = self.restapi.rest_call("get", endpoint=endpoint,
                                          headers=header)
        self.log.info("Get IAM user request successfully sent...")
        return response

    @RestTestLib.authenticate_and_login
    def add_key_to_iam_user(self, **kwargs):
        """
        Add keys to the user
        :keyword access_key: access key which needs to be added to user
        :keyword secret_key: secret_key key which needs to be added to user
        :keyword uid : uid of user for which keys need to be added
        :keyword key_type : type of key to be added
        :keyword generate_key : whether to generate keys for user
        :return response of add key rest call
        """
        self.log.info("Adding key to IAM user request....")
        access_key = kwargs.get("access_key", None)
        secret_key = kwargs.get("secret_key", None)
        endpoint = CSM_REST_CFG["s3_iam_keys_endpoint"]
        payload = {"uid": kwargs.get("uid", None)}
        payload.update({"key_type": kwargs.get("key_type", 's3')})
        payload.update({"generate_key": kwargs.get("generate_key", True)})
        if access_key is not None:
            payload.update({"access_key": access_key})
        if secret_key is not None:
            payload.update({"secret_key": secret_key})
        response = self.restapi.rest_call("put", endpoint=endpoint, json_dict=payload,
                                          headers=self.headers)
        self.log.info("Adding key to IAM user request successfully sent...")
        return response

    def validate_added_deleted_keys(self, existing_keys, new_keys, added=True):
        """
        To validate if new keys are added or deleted properly
        :keyword existing_keys: List of existing keys
        :keyword new_keys : List of new keys for comparison with existing keys
        :keyword added : whether keys were added in new keys
        :return difference of existing and new keys
        """
        self.log.info("Validating keys")
        self.log.debug("Existing keys %s", existing_keys)
        self.log.debug("New keys %s", new_keys)
        if added:
            keys_list1 = existing_keys
            keys_list2 = new_keys
        else:
            keys_list2 = existing_keys
            keys_list1 = new_keys
        key_match_cnt = 0
        existing_keys_matching = False
        diff_key = []
        for key in keys_list2:
            found = False
            for key1 in keys_list1:
                if key1["access_key"] == key["access_key"]:
                    found = True
                    break
            if not found:
                diff_key.append(key)
            else:
                key_match_cnt = key_match_cnt + 1
        if len(diff_key) == 1 and key_match_cnt == len(keys_list1):
            existing_keys_matching = True
        return existing_keys_matching, diff_key

    @RestTestLib.authenticate_and_login
    def remove_key_from_iam_user(self, **kwargs):
        """
        Remove keys from the user
        :keyword access_key: access key which needs to be removed from user
        :keyword uid : uid of user for which keys need to be removed
        :keyword key_type : type of key to be removed
        :return response of remove key rest call
        """
        self.log.info("Remove key from IAM user request....")
        endpoint = CSM_REST_CFG["s3_iam_keys_endpoint"]
        payload = {"uid": kwargs.get("uid", None)}
        payload.update({"key_type": kwargs.get("key_type", 's3')})
        payload = {"access_key": kwargs.get("access_key", None)}
        response = self.restapi.rest_call("delete", endpoint=endpoint, json_dict=payload,
                                          headers=self.headers)
        self.log.info("Remove key from IAM user request successfully sent...")
        return response

    def verify_create_iam_user_rgw(self, user_type="valid", expected_response=HTTPStatus.CREATED,
                                   verify_response=False, login_as="csm_admin_user"):
        """
        creates and verify status code and response for iam user request.
        :param user_type: user type
        :param expected_response: expected response from test
        :param verify_response: if response needs to be verified
        :param login_as: login user as admin, manage or monitor
        :return: boolean, response
        """
        payload = self.iam_user_payload_rgw(user_type=user_type)
        response = self.create_iam_user_rgw(payload, login_as=login_as)
        resp = response.json()
        if response.status_code == expected_response:
            self.log.info("Status code check passed.")
            result = True
            if verify_response:
                self.log.info("Checking response...")
                for key, value in payload.items():
                    self.log.info("Expected response for %s: %s", key, value)
                    if key == "uid":
                        key = "user_id"
                    if key in ('key_type', 'access_key', 'secret_key', 'user_caps', 'generate_key'):
                        continue

                    self.log.info("Actual response for %s: %s", key, resp[key])
                    if value != resp[key]:
                        self.log.error("Actual and expected response for %s didnt match", key)
                        result = False
        else:
            self.log.error("Status code check failed.")
            result = False
        return result, resp

    @RestTestLib.authenticate_and_login
    def modify_iam_user_rgw(self, uid, payload: dict, auth_header=True):
        """
        Modify IAM User parameters.
        :param uid: userid
        :param payload: payload for user creation
        :return: response
        """
        self.log.info("Modifying IAM user request....")
        endpoint = CSM_REST_CFG["s3_iam_user_endpoint"] + "/" + uid
        if auth_header:
            headers = self.headers
        else:
            headers = None
        response = self.restapi.rest_call("patch", endpoint=endpoint, json_dict=payload,
                                          headers=headers)
        self.log.info("IAM user request successfully sent...")
        return response

    def iam_user_patch_random_payload(self):
        """
        Return random patch payload for IAM user for RGW with Ceph
        """
        # Initialize all variables
        payload = {}
        user_id = const.IAM_USER + str(int(time.time_ns()))
        payload.update({"uid": user_id})
        display_name = const.IAM_USER + str(int(time.time_ns()))
        payload.update({"display_name": display_name})
        payload = self.iam_user_optional_payload_rgw(payload)
        del payload["uid"]
        del payload["tenant"]
        del payload["user_caps"]
        optional_payload = payload.copy()
        ran_sel = self.cryptogen.sample(list(range(0, len(optional_payload))),
                                    self.cryptogen.randrange(0, len(optional_payload)))
        for i, (k, _) in enumerate(payload.items()):
            if i not in ran_sel:
                del optional_payload[k]
        payload = optional_payload.copy()
        self.log.info("Payload : %s", payload)
        return payload

    @staticmethod
    def verify_caps(updated_caps, get_resp_caps):
        """
        Verify if updated capabilities are available in get resp capabilities
        :param updated_caps: capabilities used for update request
        :param get_resp_caps: capabilities received in get iam call
        :return list of difference in updated and get iam call capabilities
        """
        existing_caps = []
        random_cap_list = updated_caps.split(";")
        for item in random_cap_list:
            caps = item.split("=")
            list_item = {}
            list_item.update({"type": caps[0]})
            if caps[1] == "read,write":
                list_item.update({"perm": '*'})
            else:
                list_item.update({"perm": caps[1]})
            existing_caps.append(list_item)
        diff_items = []
        for i in get_resp_caps:
            if i not in existing_caps:
                diff_items.append(i)
        return diff_items

    def get_random_caps(self):
        """
        Get random capabilities
        """
        cap_keys = ['usage', 'users', 'buckets', 'info', 'metadata', 'zone']
        cap_values = ['read', 'write', 'read,write', '*']
        random_index = self.cryptogen.sample(list(range(1, len(cap_keys))),
                                     SystemRandom().randrange(1, len(cap_keys)))
        random_cap = ""
        for index in random_index:
            value_index = SystemRandom().randrange(0, len(cap_values))
            value = cap_values[value_index]
            random_cap = random_cap + cap_keys[index] + "=" + value + ";"
        return random_cap[:-1]

    @RestTestLib.authenticate_and_login
    def list_iam_users_rgw(self, max_entries=None, marker=None, auth_header=None):
        """
        This function will list all IAM users.
        :param max_entries: Number of users to be returned
        :param marker: Name of user from which specified number of users to be returned
        :return: response
        :rtype: response object
        """

        self.log.debug("Listing of iam users")
        endpoint = self.config["iam_users_endpoint"]
        self.log.debug("Endpoint for iam user is %s", endpoint)
        if auth_header is not None:
            header = {'Authorization': auth_header}
        else:
            header = self.headers
        # Fetching api response
        response = self.restapi.rest_call("get", endpoint=endpoint, headers=header,
                                          params={"max_entries": max_entries, "marker": marker})
        return response

    def fetch_internal_iamuser(self, node_obj):
        """
        Function to fetch internal IAM user
        """
        self.log.info("Fetching internal IAM User")
        pod_name = node_obj.get_pod_name(pod_prefix=cons.CONTROL_POD_NAME_PREFIX)
        self.log.info(pod_name[1])
        node_obj.execute_cmd(
            cmd=common_cmd.K8S_CP_TO_LOCAL_CMD.format(
                pod_name[1], cons.CLUSTER_CONF_PATH, cons.CLUSTER_COPY_PATH, cons.CORTX_CSM_POD),
            read_lines=False,
            exc=False)
        node_obj.copy_file_to_local(
            remote_path=cons.CLUSTER_COPY_PATH, local_path=cons.CSM_COPY_PATH)
        stream = open(cons.CSM_COPY_PATH, 'r', encoding="utf-8")
        data = yaml.safe_load(stream)
        internal_user = data["cortx"]["rgw"]["auth_user"]
        return internal_user

    @staticmethod
    def get_iam_user_payload(param=None):
        """
        Creates selected parameters IAM user payload.
        """
        time.sleep(1)
        res, temp = [], []
        user_id = const.IAM_USER + str(int(time.time()))
        display_name = const.IAM_USER + str(int(time.time()))
        temp.append(user_id)
        temp.append(display_name)
        if param == "email":
            email = user_id + "@seagate.com"
            temp.append(email)
            res = temp
        elif param == "a_key":
            access_key = user_id.ljust(const.S3_ACCESS_LL, "d")
            temp.append(access_key)
            res = temp
        elif param == "s_key":
            secret_key = config_utils.gen_rand_string(length=const.S3_SECRET_LL)
            temp.append(secret_key)
            res = temp
        elif param == "keys":
            acc_key = user_id.ljust(const.S3_ACCESS_LL, "d")
            sec_key = config_utils.gen_rand_string(length=const.S3_SECRET_LL)
            temp.append(acc_key)
            temp.append(sec_key)
            res = temp
        else:
            res = temp
        return res
