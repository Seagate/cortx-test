"""This Module will check the configurations of CSM"""
import logging
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_test_lib import RestTestLib
from commons.constants import Rest as const
from commons.utils import config_utils
from commons import constants
from config import CMN_CFG

class CSMConfigsCheck:
    """This class will check the configurations of CSM"""

    def __init__(self):
        self._log = logging.getLogger(__name__)
        self._s3account = RestS3user()
        self._csm_user = RestCsmUser()

#    @property
    def setup_csm_s3(self):
        """
        This function will create predefined s3 account user
        :return: success/failure of presence of pre defined s3 account
        """
        result = False
        try:
            self._log.info("Creating S3 account for setup ")
            if CMN_CFG.get("product_family") == constants.PROD_FAMILY_LC:
                result, response = self._s3account.create_verify_s3_custom(user_type="pre-define")
            else:
                response = self._s3account.create_s3_account(user_type="pre-define")
            result = response.status_code in (
                const.CONFLICT, const.SUCCESS_STATUS_FOR_POST)
        except Exception as error:
            # CTP Exception handling not done here as this is being called in setup for every test suit
            # CTP Exception handling shall get complicated
            self._log.error("Error occurred during setup : %s", error)
        return result

#    @property
    def setup_csm_users(self):
        """
        This function will create predefined s3 csm users account
        :return: success/failure of presence of pre defined csm users account
        """
        result = False
        try:
            self._log.info("Creating CSM user for setup ")
            responses = (self._csm_user.create_csm_user(user_type="pre-define", user_role="manage"),
                         self._csm_user.create_csm_user(user_type="pre-define", user_role="monitor")
                         )
            result = all(
                response.status_code in (
                    const.CONFLICT,
                    const.SUCCESS_STATUS_FOR_POST) for response in responses)
        except Exception as error:
            # CTP Exception handling not done here as this is being called in setup for every test suit
            # CTP Exception handling shall get complicated
            self._log.error("Error occurred during setup : %s", error)
        return result

    def check_predefined_csm_user_present(self):
        """
        This function will Check the presence of pre defined csm users
        :return: boolean value for presence of pre defined csm users account
        """
        result = False
        try:
            self._log.info("Checking the presence of pre defined csm users")
            responses = self._csm_user.list_csm_users(
                const.SUCCESS_STATUS, return_actual_response=True).json()["users"]
            expected_result = {
                "username": self._csm_user.config["csm_user_monitor"]["username"], "role": "monitor"
            }
            result_monitor = any(config_utils.verify_json_response(
                actual_result, expected_result) for actual_result in responses)
            expected_result = {
                "username": self._csm_user.config["csm_user_manage"]["username"], "role": "manage"}
            result_manage = any(config_utils.verify_json_response(
                actual_result, expected_result) for actual_result in responses)
            result = result_manage and result_monitor
        except Exception as error:
            # CTP Exception handling not done here as this is being called in setup for every test suit
            # CTP Exception handling shall get complicated
            self._log.error("Error occurred during setup : %s", error)
        return result

    def check_predefined_s3account_present(self):
        """
        This function will Check the presence of pre defined s3 account
        :return: success/failure of presence of pre defined s3 account
        """
        result = False
        try:
            self._log.info("Checking the presence of pre defined s3 account")
            response = self._s3account.list_all_created_s3account().json()["s3_accounts"]
            expected_result = {const.ACC_NAME: self._s3account.config["s3account_user"]["username"]}
            result = any(config_utils.verify_json_response(
                actual_result, expected_result) for actual_result in response)
        except Exception as error:
            # CTP Exception handling not done here as this is being called in setup for every test suit
            # CTP Exception handling shall get complicated
            self._log.error("Error occurred during setup : %s", error)
        return result

    def delete_csm_users(self):
        """Function will delete all the stray csm user appart from predefined ones.
        """
        responses = self._csm_user.list_csm_users(
                const.SUCCESS_STATUS, return_actual_response=True).json()["users"]
        for resp in responses:
            if (resp["username"] != self._csm_user.config["csm_user_manage"]["username"] and
                resp["username"] != self._csm_user.config["csm_user_monitor"]["username"] and
                resp["username"] != self._csm_user.config["csm_admin_user"]["username"]):
                self._csm_user.delete_csm_user(resp["username"])

    def delete_s3_users(self):
        """Function will delete all the stray s3 user appart from predefined ones.
        """
        responses = self._s3account.list_all_created_s3account().json()["s3_accounts"]
        for resp in responses:
            if (resp["account_name"] != self._s3account.config["s3account_user"]["username"] and
                "nightly_s3acc" not in resp["account_name"]):
                self._s3account.delete_s3_account_user(resp["account_name"])

    def preboarding(self, username, old_password, new_password):
        """Perform preboarding

        :param username: admin user name
        :param old_password: Default password
        :param new_password: New password to be set
        :return [type]: True if preboarding is successful
        """
        self._log.info("Starting the preboarding for user : %s", username)
        rest_test_obj = RestTestLib()
        result = False
        payload = {"username": username, "password": old_password}
        response = rest_test_obj.rest_login(payload)
        if response.status_code == const.SUCCESS_STATUS:
            self._log.info("Successfully logged in from old password.")
            headers = {'Authorization': response.headers['Authorization']}
            patch_payload = {
                "confirmPassword": new_password,
                "password": new_password,
                "reset_password": True}
            endpoint = "{}/{}".format(rest_test_obj.config["csmuser_endpoint"], username)
            response = rest_test_obj.restapi.rest_call("patch", data=patch_payload,
                                                        endpoint=endpoint, headers=headers)
            if response.status_code == const.SUCCESS_STATUS:
                self._log.info("Successfully reset password of the admin user.")
                payload = {"username": username, "password": new_password}
                response = rest_test_obj.rest_login(payload)
                if response.status_code == const.SUCCESS_STATUS and response.json()[
                        "reset_password"]:
                    self._log.info("Preboarding completed.")
                    self._log.info("New admin credentials are : %s", payload)
                    result = True
                else:
                    self._log.error("Failed to login using new password: %s", new_password)
            else:
                self._log.error("Reset admin password failed.")
        else:
            self._log.error("Failed to login using old password: %s", old_password)
        return result
