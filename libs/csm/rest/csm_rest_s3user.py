"""Test library for s3 account operations."""
import time
import commons.errorcodes as err
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_test_lib import RestTestLib as Base
import logging
from commons.constants import Rest as const

class RestS3user(Base):
    """RestS3user contains all the Rest Api calls for s3 account operations"""

    def __init__(self):
        super(RestS3user, self).__init__()
        self.recently_created_s3_account_user = None
        self.recent_patch_payload = None
        self.user_type = ("valid", "duplicate", "invalid", "missing")

    @Base.authenticate_and_login
    def create_s3_account(self, user_type="valid", save_new_user=False):
        """
        This function will create new s3 account user
        :param user_type: type of user required
        :param save_new_user: to store newly created user to config
        :return: response of create user
        """
        try:
            # Building request url
            self._log.debug("Create s3 accounts ...")
            endpoint = self.config["s3accounts_endpoint"]
            self._log.debug("Endpoint for s3 accounts is {}". format(endpoint))

            # Collecting required payload to be added for request
            user_data = self.create_payload_for_new_s3_account(user_type)
            self._log.debug("Payload for s3 accounts is {}".format(user_data))
            self.recently_created_s3_account_user = user_data
            if save_new_user:
                self._log.debug(
                    "Adding s3 accounts is to config with name : new_s3_account_user")
                self.update_csm_config_for_user(
                    "new_s3_account_user", user_data["account_name"], user_data["password"])

            # Fetching api response
            return self.restapi.rest_call(
                "post", endpoint=endpoint, data=user_data, headers=self.headers)

        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestS3user.create_s3_account.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0])

    @Base.authenticate_and_login
    def list_all_created_s3account(self):
        """
            This function will list down all created accounts
            :return: response of create user
        """
        try:
            # Building request url
            self._log.debug("Try to fetch all s3 accounts ...")
            endpoint = self.config["s3accounts_endpoint"]
            self._log.debug("Endpoint for s3 accounts is {}".format(endpoint))

            # Fetching api response
            response = self.restapi.rest_call(
                "get", endpoint=endpoint, headers=self.headers)

            return response
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestS3user.list_all_created_s3account.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0])

    @Base.authenticate_and_login
    def edit_s3_account_user(self, username, payload="valid"):
        """
        This function will update the required user
        :param payload: payload for the type of user
        :param username: user name of the account need to be edited
        :return: response edit s3account
        """
        try:
            # Building request url
            self._log.debug("Try to edit s3accounts user : {}".format(username))
            endpoint = "{}/{}".format(
                self.config["s3accounts_endpoint"], username)
            self._log.debug("Endpoint for s3 accounts is {}".format(endpoint))

            # Collecting payload
            patch_payload = self.edit_user_payload(payload_type=payload)
            self._log.debug(
                "Payload for edit s3 accounts is {}".format(patch_payload))

            # Fetching api response
            response = self.restapi.rest_call(
                "patch", data=patch_payload, endpoint=endpoint, headers=self.headers)

            return response
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestS3user.edit_s3_account_user.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0])

    @Base.authenticate_and_login
    def delete_s3_account_user(self, username):
        """
        This function will delete the required user
        :param username: user name of the account need to be deleted
        :return: response delete s3account
        """
        try:
            # Building request url
            self._log.debug(
                "Try to delete s3accounts user : {}".format(username))
            endpoint = "{}/{}".format(
                self.config["s3accounts_endpoint"], username)
            self._log.debug("Endpoint for s3 accounts is {}".format(endpoint))

            # Fetching api response
            response = self.restapi.rest_call(
                "delete", endpoint=endpoint, headers=self.headers)

            return response
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestS3user.delete_s3_account_user.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0])

    def verify_list_s3account_details(self, expect_no_user=False):
        """
        This function will verify the response details for list account
        :param expect_no_user: In case no user expected
        :return: Success(True)/Failure(False)
        """
        try:
            # Fetching all created accounts
            response = self.list_all_created_s3account()

            # Checking status code
            self._log.debug("Response to be verified : ",
                           self.recently_created_s3_account_user)
            if (not response) or response.status_code != const.SUCCESS_STATUS:
                self._log.debug("Response is not 200")
                return False
            response = response.json()

            # Checking the response validity of response
            if const.S3_ACCOUNTS not in response:
                self._log.error("Error !!! No response fetched ...")
                return False

            # Checking for not "no user" scenario
            if len(response["s3_accounts"]) == 0 or expect_no_user:
                self._log.warning("No accounts present till now is : {}".format(
                    len(response["iam_users"])))
                return len(response["s3_accounts"]) == 0 and expect_no_user

            return all(const.ACC_NAME in key and const.ACC_EMAIL in key for key in response["s3_accounts"])
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestS3user.verify_list_s3account_details.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def create_and_verify_s3account(self, user, expect_status_code):
        """
        This function will create and verify the response details for s3account
        :param user: type of s3 user need to create and verify
        :param expect_status_code : expected status code to be verify
        :return: Success(True)/Failure(False)
        """
        try:
            # Validating user
            if user not in self.user_type:
                self._log.error("Invalid user type ...")
                return False

            # Create s3account user
            response = self.create_s3_account(user_type=user)

            # Handling specific scenarios
            if user != "valid":
                self._log.debug("verify status code for user {}".format(user))
                return response.status_code == expect_status_code

            # Checking status code
            self._log.debug("Response to be verified : ",
                           self.recently_created_s3_account_user)
            if (not response) or response.status_code != expect_status_code:
                self._log.debug("Response is not 200")
                return False

            # Checking presence of access key and secret key
            response = response.json()
            if const.ACCESS_KEY not in response and const.SECRET_KEY not in response:
                self._log.debug("secret key and/or access key is not present")
                return False

            # Checking account name
            self._log.debug("verifying Newly created account data ...")
            if response[const.ACC_NAME] != self.recently_created_s3_account_user[const.ACC_NAME]:
                self._log.debug("Miss match user name ...")
                return False

            # Checking account name
            if response[const.ACC_EMAIL] != self.recently_created_s3_account_user[const.ACC_EMAIL]:
                self._log.debug("Miss match email address ...")
                return False

            # Checking response in details
            self._log.debug(
                "verifying Newly created account data in created list...")
            list_acc = self.list_all_created_s3account().json()["s3_accounts"]
            expected_result = {const.ACC_EMAIL: response[const.ACC_EMAIL],
                               const.ACC_NAME: response[const.ACC_NAME]}

            return any(self.verify_json_response(actual_result, expected_result) for actual_result in list_acc)
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestS3user.create_and_verify_s3account.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def create_payload_for_new_s3_account(self, user_type):
        """
        This function will create payload according to the required type
        :param user_type: type of payload required
        :return: payload
        """
        try:
            # Creating payload for required user type

            # Creating s3accounts which are pre-defined in config
            if user_type == "pre-define":
                self._log.debug(
                    "Creating s3accounts which are pre-defined in config")
                data = self.config["s3account_user"]
                return {"account_name": data["username"],
                        "account_email": data["email"],
                        "password": data["password"]}

            if user_type == "valid":
                user_name, email_id = "test{}".format(
                    int(time.time())), "test{}@seagate.com".format(int(time.time()))

            if user_type == "duplicate":
                # creating new user to make it as duplicate
                self.create_s3_account()
                return self.recently_created_s3_account_user

            if user_type == "missing":
                return {"password": self.config["test_s3account_password"]}

            if user_type == "invalid":
                return {"user_name": "xys", "mail": "abc@email.com", "pass_word": "password"}

            if user_type == "invalid_for_ui":
                return {"account_name": "*ask%^*&", "account_email": "seagate*mail-com", "password": "password"}

            user_data = {"account_name": user_name,
                         "account_email": email_id,
                         "password": self.config["test_s3account_password"]}

            return user_data
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestS3user.create_payload_for_new_s3_account.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def edit_user_payload(self, payload_type):
        """
        This function will create payload for edit user type
        :param payload_type: type of payload required
        :return: payload
        """
        try:
            # Creating payload for edit user type
            payload_values = {
                "valid": {"password": self.config["test_s3account_password"], "reset_access_key": "true"},
                "unchanged_access": {"password": self.config["test_s3account_password"], "reset_access_key": "false"},
                "only_reset_access_key": {"reset_access_key": "true"},
                "only_password": {"password": self.config["test_s3account_password"]},
                "no_payload": {}
            }

            # Check payload_type present or not
            if payload_type not in payload_values:
                self._log.error("Invalid payload type ...")
                return None

            return payload_values[payload_type]
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestS3user.edit_user_payload.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def edit_and_verify_s3_account_user(self, user_payload):
        """
        This function will edit and verify s3 account users
        :param user_payload: payload for type of user need to be crated
        :return: Success(True)/Failure(False)
        """
        try:
            # Create new s3 account user
            self._log.debug("creating new s3 account user")
            self.create_s3_account(save_new_user=True)

            # Editing new s3 account user
            account_name = self.recently_created_s3_account_user["account_name"]
            self._log.debug("editing user {}".format(user_payload))
            response = self.edit_s3_account_user(
                username=account_name, payload=user_payload, login_as="new_s3_account_user")

            # Handling Unchanged access scenario
            if user_payload in ("unchanged_access", "only_password"):
                self._log.debug(
                    "verify status code for edit user without changing access")
                if (not response) or response.status_code != const.SUCCESS_STATUS:
                    self._log.debug("Response is not 200")
                    return False
                response = response.json()
                # For edit user without changing access secret key and access key should not be visible
                return (response[const.ACC_NAME] == account_name) and (
                    const.ACCESS_KEY not in response) and (
                    const.SECRET_KEY not in response)

            # Handling specific scenarios
            if user_payload != "valid":
                self._log.debug(
                    "verify status code for user {}".format(user_payload))
                return (not response) and response.status_code == const.BAD_REQUEST

            # Checking status code
            self._log.debug("Response to be verified : ",
                           self.recently_created_s3_account_user)
            if (not response) or response.status_code != const.SUCCESS_STATUS:
                self._log.debug("Response is not 200")
                return False

            # Checking presence of access key and secret key
            response = response.json()
            if const.ACCESS_KEY not in response and const.SECRET_KEY not in response:
                self._log.debug("secret key and/or access key is not present")
                return False

            # Checking account name
            self._log.debug("verifying Newly created account data ...")
            if const.ACC_NAME not in response:
                self._log.debug("username key is not present ...")
                return False

            return response[const.ACC_NAME] == account_name
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestS3user.edit_and_verify_s3_account_user.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    def delete_and_verify_s3_account_user(self):
        """
        This function will verify delete operation for s3 account
        :return: Success(True)/Failure(False)
        """
        try:
            # Create new s3 account user and adding it to fet it's IAM users
            self._log.debug("creating new s3 account user")
            self.create_s3_account(save_new_user=True)

            # Deleting account user
            account_name = self.recently_created_s3_account_user["account_name"]
            self._log.debug(
                "deleting new s3 account user name : {}".format(account_name))
            response = self.delete_s3_account_user(
                username=account_name, login_as="new_s3_account_user")

            # Checking status code
            self._log.debug("Response to be verified for user: ", account_name)
            if (not response) or response.status_code != const.SUCCESS_STATUS:
                self._log.debug("Response is not 200")
                return False

            return response.json()["message"] == const.DELETE_SUCCESS_MSG
        except Exception as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestS3user.delete_and_verify_s3_account_user.__name__,
                error))
            raise CTException(err.CSM_REST_VERIFICATION_FAILED, error.args[0])

    @Base.authenticate_and_login
    def edit_s3_account_user_invalid_password(self, username, payload):
        """
        This function will provide invalid password in Patch request for the specified s3 account
        :param payload: payload for the type of user
        :type payload: json
        :param username: name of the s3 account that need to be edited
        :type username: str
        :return: response
        :rtype: json 
        """
        try:
            # Building request url
            self._log.debug("Try to edit s3accounts user : {}".format(username))
            endpoint = "{}/{}".format(
                self.config["s3accounts_endpoint"], username)
            self._log.debug("Endpoint for s3 accounts is {}".format(endpoint))

            self._log.debug(
                "Payload for edit s3 accounts is {}".format(payload))

            # Fetching api response
            self._log.debug("Fetching api response...")
            response = self.restapi.rest_call(
                "patch", data=payload, endpoint=endpoint, headers=self.headers)

            return response
        except BaseException as error:
            self._log.error("{0} {1}: {2}".format(
                self.exception_error,
                RestS3user.edit_s3_account_user_invalid_password.__name__,
                error))
            raise CTException(
                err.CSM_REST_AUTHENTICATION_ERROR, error.args[0])
