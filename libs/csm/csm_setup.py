"""This Module will check the configurations of CSM"""
import logging
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from commons.constants import Rest as const
from commons.utils import config_utils

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
            self._log.info("Creating for setup ")
            response = self._s3account.create_s3_account(user_type="pre-define")
            result = response.status_code in (
                const.CONFLICT, const.SUCCESS_STATUS)
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
            self._log.info("Creating for setup ")
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
                "username": self._csm_user.config["csm_user_monitor"]["username"], "roles": ["monitor"]
            }
            result_monitor = any(config_utils.verify_json_response(
                    actual_result, expected_result) for actual_result in responses)
            expected_result = {
                "username": self._csm_user.config["csm_user_manage"]["username"], "roles": ["manage"]
            }
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
