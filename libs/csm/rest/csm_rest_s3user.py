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
"""Test library for s3 account operations."""
import json
import time
from http import HTTPStatus
from requests.models import Response
import commons.errorcodes as err
from commons.constants import Rest as const
from commons.constants import S3_ENGINE_RGW
from commons.exceptions import CTException
from commons.utils import config_utils
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from config import CSM_REST_CFG, CMN_CFG

class RestS3user(RestTestLib):
    """RestS3user contains all the Rest Api calls for s3 account operations"""

    def __init__(self):
        super(RestS3user, self).__init__()
        self.recently_created_s3_account_user = None
        self.recent_patch_payload = None
        self.user_type = ("valid", "duplicate", "invalid", "missing")

    @RestTestLib.authenticate_and_login
    def create_s3_account(self, user_type="valid", save_new_user=False):
        """
        This function will create new s3 account user
        :param user_type: type of user required
        :param save_new_user: to store newly created user to config
        :return: response of create user
        """
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            return self.create_s3_basic()
        else:
            # Building request url
            self.log.debug("Create s3 accounts ...")
            endpoint = self.config["s3accounts_endpoint"]
            self.log.debug("Endpoint for s3 accounts is %s", endpoint)
            # Collecting required payload to be added for request
            user_data = self.create_payload_for_new_s3_account(user_type)
            self.log.debug("Payload for s3 accounts is %s", user_data)
            self.recently_created_s3_account_user = user_data
            if save_new_user:
                self.log.debug(
                    "Adding s3 accounts is to config with name : "
                    "new_s3_account_user")
                self.update_csm_config_for_user(
                    "new_s3_account_user",
                    user_data["account_name"],
                    user_data["password"])
            #user_data = json.dumps(user_data)
            # Fetching api response
            return self.restapi.rest_call(
                "post", endpoint=endpoint, json_dict=user_data, headers=self.headers)


    @RestTestLib.authenticate_and_login
    def list_all_created_s3account(self):
        """
            This function will list down all created accounts
            :return: response of create user
        """
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            response = Response()
            response.status_code = 200
            response._content = b'{"s3_accounts": [\
                {"account_name": "nightly_s3dk", "account_email": "nightly_s3dk@seagate.com"}]}'
        else:
            # Building request url
            self.log.debug("Try to fetch all s3 accounts ...")
            endpoint = self.config["s3accounts_endpoint"]
            self.log.debug("Endpoint for s3 accounts is %s", endpoint)

            # Fetching api response
            response = self.restapi.rest_call(
                "get", endpoint=endpoint, headers=self.headers)

        return response

    @RestTestLib.authenticate_and_login
    def edit_s3_account_user(self, username, payload="valid"):
        """
        This function will update the required user
        :param payload: payload for the type of user
        :param username: user name of the account need to be edited
        :return: response edit s3account
        """
        try:
            # Building request url
            self.log.debug("Try to edit s3accounts user : %s", username)
            endpoint = "{}/{}".format(
                self.config["s3accounts_endpoint"], username)
            self.log.debug("Endpoint for s3 accounts is %s", endpoint)

            # Collecting payload
            patch_payload = self.edit_user_payload(payload_type=payload)
            patch_payload = json.dumps(patch_payload)
            self.log.debug(
                "Payload for edit s3 accounts is %s", patch_payload)

            # Fetching api response
            response = self.restapi.rest_call(
                "patch", data=patch_payload, endpoint=endpoint,
                headers=self.headers)

            return response
        except BaseException as error:
            self.log.error("%s %s: %s",
                           const.EXCEPTION_ERROR,
                           RestS3user.edit_s3_account_user.__name__,
                           error)
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error) from error

    @RestTestLib.authenticate_and_login
    def delete_s3_account_user(self, username):
        """
        This function will delete the required user
        :param username: user name of the account need to be deleted
        :return: response delete s3account
        """
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            rest_iam_user = RestIamUser()
            response = rest_iam_user.delete_iam_user(user=username)
        else:
            # Building request url
            self.log.debug(
                "Try to delete s3accounts user : %s", username)
            endpoint = "{}/{}".format(
                self.config["s3accounts_endpoint"], username)
            self.log.debug("Endpoint for s3 accounts is %s", endpoint)
            # Fetching api response
            response = self.restapi.rest_call(
                "delete", endpoint=endpoint, headers=self.headers)
            # As per Pranay's suggestion, adding retry/polling of 25's to delete s3 account.
            end_time = time.time() + 25  # retry/polling for 25's
            status = response.status_code != const.SUCCESS_STATUS or response.ok is not True
            while status and time.time() <= end_time:
                response = self.restapi.rest_call("delete", endpoint=endpoint, headers=self.headers)
                status = response.status_code != const.SUCCESS_STATUS or response.ok is not True
                time.sleep(5)  # delay for next call.
        return response

    def verify_list_s3account_details(self, expect_no_user=False):
        """
        This function will verify the response details for list account
        :param expect_no_user: In case no user expected
        :return: Success(True)/Failure(False)
        """
        # Fetching all created accounts
        response = self.list_all_created_s3account()

        # Checking status code
        self.log.debug("Response to be verified : %s",
                        self.recently_created_s3_account_user)
        if (not response) or response.status_code != const.SUCCESS_STATUS:
            self.log.debug("Response is not 200")
            return False
        response = response.json()

        # Checking the response validity of response
        if const.S3_ACCOUNTS not in response:
            self.log.error("Error !!! No response fetched ...")
            return False

        # Checking for not "no user" scenario
        if len(response["s3_accounts"]) == 0 or expect_no_user:
            self.log.warning("No accounts present till now is : %s",
                                len(response["iam_users"]))
            return len(response["s3_accounts"]) == 0 and expect_no_user

        return all(const.ACC_NAME in key and const.ACC_EMAIL in key
                    for key in response["s3_accounts"])

    # pylint: disable-msg=too-many-return-statements
    def create_and_verify_s3account(self, user, expect_status_code):
        """
        This function will create and verify the response details for s3account
        :param user: type of s3 user need to create and verify
        :param expect_status_code : expected status code to be verify
        :return: Success(True)/Failure(False)
        """
        # Validating user
        if user not in self.user_type:
            self.log.error("Invalid user type ...")
            return False, None

        # Create s3account user
        response = self.create_s3_account(user_type=user)

        # Handling specific scenarios
        if user != "valid":
            self.log.debug("verify status code for user %s", user)
            return response.status_code == expect_status_code, response

        # Checking status code
        self.log.debug("Response to be verified : %s",
                        self.recently_created_s3_account_user)
        if (not response) or response.status_code != expect_status_code:
            self.log.debug("Response is not 200")
            return False, response

        # Checking presence of access key and secret key
        response = response.json()
        if const.ACCESS_KEY not in response and const.SECRET_KEY not in response:
            self.log.debug("secret key and/or access key is not present")
            return False, response

        # Checking account name
        self.log.debug("verifying Newly created account data ...")
        if response[const.ACC_NAME] != self.recently_created_s3_account_user[const.ACC_NAME]:
            self.log.debug("Miss match user name ...")
            return False, response

        # Checking account name
        if response[const.ACC_EMAIL] != self.recently_created_s3_account_user[const.ACC_EMAIL]:
            self.log.debug("Miss match email address ...")
            return False, response

        # Checking response in details
        self.log.debug(
            "verifying Newly created account data in created list...")
        list_acc = self.list_all_created_s3account().json()["s3_accounts"]
        expected_result = {const.ACC_EMAIL: response[const.ACC_EMAIL],
                            const.ACC_NAME: response[const.ACC_NAME]}

        return any(config_utils.verify_json_response(actual_result, expected_result)
                    for actual_result in list_acc), response


    def create_payload_for_new_s3_account(self, user_type):
        """
        This function will create payload according to the required type
        :param user_type: type of payload required
        :return: payload
        """
        # Creating payload for required user type
        # Creating s3accounts which are pre-defined in config
        if user_type == "pre-define":
            self.log.debug(
                "Creating s3accounts which are pre-defined in config")
            data = self.config["s3account_user"]
            return {"account_name": data["username"],
                    "account_email": data["email"],
                    "password": data["password"]}

        if user_type == "valid":
            user_name = "test%s" % int(time.time_ns())
            email_id = "test%s@seagate.com" % int(time.time_ns())
        if user_type == "duplicate":
            # creating new user to make it as duplicate
            self.create_s3_account()
            return self.recently_created_s3_account_user

        if user_type == "missing":
            return {"password": self.config["test_s3account_password"]}

        if user_type == "invalid":
            return {"user_name": "xys",
                    "mail": "abc@email.com",
                    "pass_word": "password"}

        if user_type == "invalid_for_ui":
            return {"account_name": "*ask%^*&",
                    "account_email": "seagate*mail-com",
                    "password": "password"}

        user_data = {"account_name": user_name,
                        "account_email": email_id,
                        "password": self.config["test_s3account_password"]}

        return user_data


    def edit_user_payload(self, payload_type):
        """
        This function will create payload for edit user type
        :param payload_type: type of payload required
        :return: payload
        """
        # Creating payload for edit user type
        payload_values = {
            "valid": {"password": self.config["test_s3account_password"],
                        "reset_access_key": "true"},
            "unchanged_access": {
                "password": self.config["test_s3account_password"],
                "reset_access_key": "false"},
            "only_reset_access_key": {"reset_access_key": "true"},
            "only_password": {
                "password": self.config["test_s3account_password"]},
            "no_payload": {}
        }

        # Check payload_type present or not
        if payload_type not in payload_values:
            self.log.error("Invalid payload type ...")
            return None

        return payload_values[payload_type]


    # pylint: disable-msg=too-many-return-statements
    def edit_and_verify_s3_account_user(self, user_payload):
        """
        This function will edit and verify s3 account users
        :param user_payload: payload for type of user need to be crated
        :return: Success(True)/Failure(False)
        """
        # Create new s3 account user
        self.log.debug("creating new s3 account user")
        self.create_s3_account(save_new_user=True)

        # Editing new s3 account user
        account_name = self.recently_created_s3_account_user["account_name"]
        self.log.debug("editing user %s", user_payload)
        response = self.edit_s3_account_user(
            username=account_name,
            payload=user_payload)

        # Handling Unchanged access scenario
        if user_payload in ("unchanged_access", "only_password"):
            self.log.debug(
                "verify status code for edit user without changing access")
            if (not response) or response.status_code != const.SUCCESS_STATUS:
                self.log.debug("Response is not 200")
                return False, account_name
            response = response.json()
            # For edit user without changing access secret key and access
            # key should not be visible
            return (response[const.ACC_NAME] == account_name) and (
                const.ACCESS_KEY not in response) and (
                const.SECRET_KEY not in response), account_name

        # Handling specific scenarios
        if user_payload != "valid":
            self.log.debug(
                "verify status code for user %s", user_payload)
            return (not response) and response.status_code == const.BAD_REQUEST, account_name

        # Checking status code
        self.log.debug("Response to be verified : %s",
                        self.recently_created_s3_account_user)
        if (not response) or response.status_code != const.SUCCESS_STATUS:
            self.log.debug("Response is not 200")
            return False, account_name

        # Checking presence of access key and secret key
        response = response.json()
        if const.ACCESS_KEY not in response and const.SECRET_KEY not in response:
            self.log.debug("secret key and/or access key is not present")
            return False, account_name

        # Checking account name
        self.log.debug("verifying Newly created account data ...")
        if const.ACC_NAME not in response:
            self.log.debug("username key is not present ...")
            return False, account_name

        return response[const.ACC_NAME] == account_name, account_name


    def delete_and_verify_s3_account_user(self):
        """
        This function will verify delete operation for s3 account
        :return: Success(True)/Failure(False)
        """
        # Create new s3 account user and adding it to fet it's IAM users
        self.log.debug("creating new s3 account user")
        self.create_s3_account(save_new_user=True)

        # Deleting account user
        account_name = self.recently_created_s3_account_user["account_name"]
        self.log.debug(
            "deleting new s3 account user name : %s", account_name)
        response = self.delete_s3_account_user(
            username=account_name)

        # Checking status code
        self.log.debug(f"Response to be verified for user: {account_name}")
        if (not response) or response.status_code != const.SUCCESS_STATUS:
            self.log.debug("Response is not 200")
            return False

        return response.json()["message"] == const.DELETE_SUCCESS_MSG


    @RestTestLib.authenticate_and_login
    def edit_s3_account(self, username, payload):
        """
        This function will provide invalid password in Patch request for the specified s3 account
        :param payload: payload for the type of user
        :type payload: json
        :param username: name of the s3 account that need to be edited
        :type username: str
        :return: response
        :rtype: json
        """
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            response = Response()
            response.status_code = 200
            response._content = b'{"message":"Delete bypassed"}'
            return response
        else:
            # Building request url
            self.log.debug("Try to edit s3accounts user : %s", username)
            endpoint = "{}/{}".format(
                self.config["s3accounts_endpoint"], username)
            self.log.debug("Endpoint for s3 accounts is %s", endpoint)

            self.log.debug(
                "Payload for edit s3 accounts is %s", payload)

            # Fetching api response
            self.log.debug("Fetching api response...")
            response = self.restapi.rest_call(
                "patch", data=payload, endpoint=endpoint, headers=self.headers)

            return response

    @RestTestLib.authenticate_and_login
    def update_s3_user_password(self, username, old_password, new_password):
        """
        This function will update s3 account user password
        :param username: Username
        :param old_password: Old Password
        :param new_password: New Password
        """
        self.log.debug(f"Changing password of s3 user {username} from {old_password} to "
                       f"{new_password}")
        # Prepare patch for s3 account user
        patch_payload = {"password": new_password, "reset_access_key": "true"}
        self.log.debug("editing user {}".format(patch_payload))
        endpoint = "{}/{}".format(self.config["s3accounts_endpoint"], username)
        self.log.debug("Endpoint for s3 accounts is {}".format(endpoint))
        self.headers["Content-Type"] = "application/json"
        try:
            # Fetching api response
            response = self.restapi.rest_call("patch", data=json.dumps(patch_payload),
                                              endpoint=endpoint, headers=self.headers)
        except Exception as error:
            self.log.error("{0} {1}: {2}".format(
                const.EXCEPTION_ERROR,
                RestS3user.update_s3_user_password.__name__,
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
    def create_an_account(self, user_name, password):
        """
        This function will create new s3 account user
        :param user_name: Account name
        :param password: account password
        :return: response of create user
        """
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            payload = {}
            payload.update({"uid":user_name})
            payload.update({"display_name":user_name})
            return self.create_s3_basic(payload)
        else:
            self.log.debug("Create s3 accounts ...")
            endpoint = self.config["s3accounts_endpoint"]
            self.log.debug("Endpoint for s3 accounts is %s", endpoint)
            # Collecting required payload to be added for request
            user_data = {
                "account_name": user_name,
                "account_email": f"{user_name}@seagate.com",
                "password": password
            }
            self.log.debug("Payload for s3 accounts is %s", user_data)
            #Fetching api response
            return self.restapi.rest_call(
                "post", endpoint=endpoint, data=user_data,
                headers=self.headers)

    @RestTestLib.authenticate_and_login
    def create_custom_s3_user(self, user_data: dict):
        """Function to create s3 user
        :param user_data: Payload for Create S3 user.
        """
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            payload = {}
            for key,value in user_data.items():
                if key == "account_name":
                    payload.update({"uid":value})
                if key == "account_email":
                    payload.update({"email":value})
                if key == "access_key":
                    payload.update({"access_key":value})
                if key == "secret_key":
                    payload.update({"secret_key":value})
            resp = self.create_s3_basic(payload)
        else:
            self.log.debug("Create s3 accounts ...")
            endpoint = self.config["s3accounts_endpoint"]
            self.log.debug("Endpoint for s3 accounts is %s", endpoint)
            user_data = json.dumps(user_data)
            resp = self.restapi.rest_call("post", endpoint=endpoint, data=user_data,
                                        headers=self.headers)

        if resp.status_code == HTTPStatus.CREATED.value:
            self.recently_created_s3_account_user = resp.json()
        return resp

    # pylint: disable=too-many-statements
    def create_custom_s3_payload(self, user_type: str):
        """
        Create the payload for the create S3
        :param user_type: value from "valid","duplicate_user",..
        """
        user_name = "test%s" % int(time.time_ns())
        email_id = "test%s@seagate.com" % int(time.time_ns())
        password = self.config["test_s3account_password"]
        access = user_name.ljust(const.S3_ACCESS_LL, "d")
        secret = config_utils.gen_rand_string(length=const.S3_SECRET_LL)

        if user_type == "valid":
            user_data = dict(zip(const.CUSTOM_S3_USER, [
                             user_name, email_id, password, access, secret]))

        if user_type == "duplicate":
            # creating new user to make it as duplicate
            self.log.info("Creating Valid S3 account...")
            user_data = dict(zip(const.CUSTOM_S3_USER, [
                             user_name, email_id, password, access, secret]))
            self.create_custom_s3_user(user_data)
            self.log.info("Valid S3 account created.")
            user_data = self.recently_created_s3_account_user["account_name"]
            del user_data["canonical_id"]

        if user_type == "duplicate_user":
            self.log.info("Creating Valid S3 account...")
            user_data = dict(zip(const.CUSTOM_S3_USER, [
                             user_name, email_id, password, access, secret]))
            self.create_custom_s3_user(user_data)
            self.log.info("Valid S3 account created.")
            email_id = "test%s@seagate.com" % int(time.time_ns())
            secret = config_utils.gen_rand_string(length=const.S3_SECRET_LL)
            tmp = "test%s" % int(time.time_ns())
            access = tmp.ljust(const.S3_ACCESS_LL, "d")
            user_name = self.recently_created_s3_account_user["account_name"]
            user_data = dict(zip(const.CUSTOM_S3_USER, [
                             user_name, email_id, password, access, secret]))

        if user_type == "duplicate_access":
            self.log.info("Creating Valid S3 account...")
            user_data = dict(zip(const.CUSTOM_S3_USER, [
                             user_name, email_id, password, access, secret]))
            self.create_custom_s3_user(user_data)
            self.log.info("Valid S3 account created.")
            user_name = "test%s" % int(time.time_ns())
            email_id = "test%s@seagate.com" % int(time.time_ns())
            secret = config_utils.gen_rand_string(length=const.S3_SECRET_LL)
            access = self.recently_created_s3_account_user["access_key"]
            user_data = dict(zip(const.CUSTOM_S3_USER, [
                             user_name, email_id, password, access, secret]))

        if user_type == "duplicate_email":
            self.log.info("Creating Valid S3 account...")
            user_data = dict(zip(const.CUSTOM_S3_USER, [
                             user_name, email_id, password, access, secret]))
            self.create_custom_s3_user(user_data)
            self.log.info("Valid S3 account created.")
            user_name = "test%s" % int(time.time_ns())
            access = user_name.ljust(const.S3_ACCESS_LL, "d")
            secret = config_utils.gen_rand_string(length=const.S3_SECRET_LL)
            email_id = self.recently_created_s3_account_user["account_email"]
            user_data = dict(zip(const.CUSTOM_S3_USER, [
                             user_name, email_id, password, access, secret]))

        if user_type == "duplicate_secret":
            self.log.info("Creating Valid S3 account...")
            user_data = dict(zip(const.CUSTOM_S3_USER, [
                             user_name, email_id, password, access, secret]))
            self.create_custom_s3_user(user_data)
            self.log.info("Valid S3 account created.")
            user_name = "test%s" % int(time.time_ns())
            email_id = "test%s@seagate.com" % int(time.time_ns())
            password = self.config["test_s3account_password"]
            access = user_name.ljust(const.S3_ACCESS_LL, "d")
            secret = self.recently_created_s3_account_user["secret_key"]
            user_data = dict(zip(const.CUSTOM_S3_USER, [
                             user_name, email_id, password, access, secret]))

        if user_type == "missing_access":
            template = const.CUSTOM_S3_USER.copy()
            template.remove("access_key")
            user_data = dict(zip(template, [user_name, email_id, password, secret]))

        if user_type == "missing_secret":
            template = const.CUSTOM_S3_USER.copy()
            template.remove("secret_key")
            user_data = dict(zip(template, [user_name, email_id, password, access]))
        if user_type == "pre-define":
            template = const.CUSTOM_S3_USER.copy()
            user_data = dict(zip(template, [CSM_REST_CFG["s3account_user"]["username"],
                                            CSM_REST_CFG["s3account_user"]["email"],
                                            CSM_REST_CFG["s3account_user"]["password"],
                                            CSM_REST_CFG["s3account_user"]["access_key"],
                                            CSM_REST_CFG["s3account_user"]["secret_key"]]))

        return user_data

    def create_verify_s3_custom(self, user_type: str,
                                expected_response: int = HTTPStatus.CREATED.value,
                                verify_err_args=None):
        """
        Create and verify custom S3 user.
        :verify_err_args: verify user name in error args
        """
        user_data = self.create_custom_s3_payload(user_type)
        resp = self.create_custom_s3_user(user_data)
        result = resp.status_code == expected_response
        if result:
            self.log.info("Status code check passed.")
            if verify_err_args:
                resp_args = resp.json()["error_format_args"]
                user_name = user_data["account_name"]
                if isinstance(resp_args, dict):
                    err_arg_check = user_name in resp_args.values() or \
                        user_name in resp_args.keys()
                else:
                    err_arg_check = user_name in resp_args.values()
                result = result and err_arg_check
        else:
            self.log.error("Status code check failed.")

        return result, resp

    def create_s3_basic(self, payload:dict=None):
        """All Create s3 account calls will be directed from this function only.
        """
        self.log.info("Simulating S3 account creation.")
        rest_iam_user = RestIamUser()
        payload_rgw = rest_iam_user.iam_user_payload_rgw(user_type="valid")
        if payload is not None:
            payload_rgw.update(payload)
        resp = rest_iam_user.create_iam_user_rgw(payload_rgw)
        s3_response = Response()
        if resp.status_code == HTTPStatus.CREATED:
            resp = resp.json()
            resp_dict = {"account_name": resp["keys"][0]["user"],
                        "account_email": resp["email"],
                        "account_id": resp["user_id"],
                        "canonical_id": resp["user_id"],
                        "access_key": resp["keys"][0]["access_key"],
                        "secret_key": resp["keys"][0]["secret_key"]}
            s3_response.status_code = 201
            s3_response._content = json.dumps(resp_dict).encode("utf-8")
        else:
            s3_response.status_code = resp.status_code
            resp = resp.json()
            resp_dict = {"error_code": resp["error_code"],
                        "message": resp["message"],
                        "message_id": resp["message_id"],
                        "error":"Failed to create S3 account."}
            s3_response._content = json.dumps(resp_dict).encode("utf-8")

        return s3_response
