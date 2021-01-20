import sys
import pytest
import logging
#from eos_test.csm.csm_setup import CSMConfigsCheck
from commons.utils import config_utils
from libs.csm.rest.csm_rest_iamuser import RestIamUser

class TestIamUser():
    """REST API Test cases for IAM users"""
    @classmethod
    def setup_class(self):
        """
        This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("Initializing test setups")
        self.csm_conf = config_utils.read_yaml(
            "config/csm/test_rest_iam_user.yaml")[1]
        self.log.info("Ended test module setups")
        #self.config = CSMConfigsCheck()
        #setup_ready = self.config.check_predefined_s3account_present()
        #if not setup_ready:
        #    setup_ready = self.config.setup_csm_s3
        #assert(setup_ready)
        self.rest_iam_user = RestIamUser()
        self.created_iam_users = set()
        self.log.info("Initiating Rest Client ...")

    @classmethod
    def teardown_class(self):
        self.log.info("Teardown started")
        for user in self.created_iam_users:
            self.rest_iam_user.delete_iam_user(
                login_as="s3account_user", user=user)
        self.log.info("Teardown ended")

    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-17495")
    def test_1133(self):
        """Test that IAM users are not permitted to login
         :avocado: tags=iam_user
         """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        status_code = self.csm_conf["test_1133"]
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        assert status, response
        user_name = response['user_name']
        self.created_iam_users.add(response['user_name'])
        assert(
            self.rest_iam_user.iam_user_login(user=user_name)== status_code["status_code"])
        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-17495")
    def test_1041(self):
        """Test that S3 account should have access to create IAM user from back end
        :avocado: tags=iam_user
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info("Creating IAM user")
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        print(status)
        self.log.info(
            "Verifying status code returned is 200 and response is not null")
        assert status, response

        for key, value in response.items():
            self.log.info("Verifying {} is not empty".format(key))
            assert value

        self.log.info("Verified that S3 account {} was successfully able to create IAM user: {}".format(
            self.rest_iam_user.config["s3account_user"]["username"], response))

        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-17495")
    def test_1022(self):
        """
        Test that IAM user is not able to execute and access the CSM REST APIs.	
        :avocado: tags=iam_user
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.debug(
            "Verifying that IAM user is not able to execute and access the CSM REST APIs")
        assert(
            self.rest_iam_user.verify_unauthorized_access_to_csm_user_api())
        self.log.debug(
            "Verified that IAM user is not able to execute and access the CSM REST APIs")

        self.log.info("##### Test ended -  {} #####".format(test_case_name))
