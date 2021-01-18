import sys
import time
import json
from ctp.utils import ctpyaml

from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_s3account import RestS3account

#from commons.eos_errors import error_handler

#from eos_test.csm.csm_setup import CSMConfigsCheck
#from eos_test.csm.rest.csm_rest_iamuser import RestIamUser
#from eos_test.csm.rest.csm_rest_test_lib import RestTestLib
#from eos_test.csm.rest.csm_rest_bucket import RestS3Bucket
#from eos_test.csm.rest.csm_rest_bucket import RestS3BucketPolicy

 
class CsmUserTests(Test):
    """REST API Test cases for CSM users"""

    def setUp(self):
        """ This is method is for test suite set-up """
        self.log.info("Initializing test setups ......")
        self.config = CSMConfigsCheck()
        user_already_present = self.config.check_predefined_csm_user_present()
        if not user_already_present:
            user_already_present = self.config.setup_csm_users
        self.assertTrue(user_already_present)
        s3acc_already_present = self.config.check_predefined_s3account_present()
        if not s3acc_already_present:
            s3acc_already_present = self.config.setup_csm_s3
        self.assertTrue(s3acc_already_present)
        self.csm_user = RestCsmUser()
        self.s3_accounts = RestS3account()
        self.log.info("Initiating Rest Client for Alert ...")
        self.csm_conf = ctpyaml.read_yaml("config/csm/test_rest_csm_user.yaml")

    @ctp_fail_on(error_handler)
    def test_5011(self):
        """Initiating the test case for the verifying CSM user creating.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(self.csm_user.create_and_verify_csm_user_creation(
            user_type="valid", user_role="manage", expect_status_code=self.csm_user.success_response_post))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5012(self):
        """Initiating the test case for the verifying response for invalid CSM user creating.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(self.csm_user.create_and_verify_csm_user_creation(
            user_type="invalid", user_role="manage", expect_status_code=self.csm_user.bad_request_response))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5013(self):
        """Initiating the test case for the verifying response with missing mandatory argument for CSM user creating.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(self.csm_user.create_and_verify_csm_user_creation(
            user_type="missing", user_role="manage", expect_status_code=self.csm_user.bad_request_response))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5014(self):
        """Initiating the test case for the verifying response unauthorized user trying to create csm user.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        response = self.csm_user.create_csm_user(login_as="s3account_user")
        self.assertTrue(response.status_code == self.csm_user.forbidden)
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5015(self):
        """Initiating the test case for the verifying response for duplicate CSM user creation.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(self.csm_user.create_and_verify_csm_user_creation(
            user_type="duplicate", user_role="manage", expect_status_code=self.csm_user.conflict_response))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_4947(self):
        """Initiating the test case to verify List CSM user.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(self.csm_user.list_csm_users(
            expect_status_code=self.csm_user.const.SUCCESS_STATUS))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_4948(self):
        """Initiating the test case to verify List CSM user with offset=<int>.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(self.csm_user.list_csm_users(
            expect_status_code=self.csm_user.const.SUCCESS_STATUS, offset=2))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_4949(self):
        """Initiating the test case to verify List CSM user with offset=<string>.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(self.csm_user.list_csm_users(expect_status_code=self.csm_user.const.BAD_REQUEST, offset='abc',
                                                     verify_negative_scenario=True))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_4950(self):
        """Initiating the test case to verify List CSM user with offset=<empty>.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(self.csm_user.list_csm_users(expect_status_code=self.csm_user.const.BAD_REQUEST, offset='',
                                                     verify_negative_scenario=True))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_4951(self):
        """Initiating the test case to verify List CSM user with limit=<int>.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(self.csm_user.list_csm_users(
            expect_status_code=self.csm_user.const.SUCCESS_STATUS, limit=2))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_4952(self):
        """Initiating the test case to verify List CSM user with limit=<int>.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(self.csm_user.list_csm_users(expect_status_code=self.csm_user.const.BAD_REQUEST, limit='abc',
                                                     verify_negative_scenario=True))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_4955(self):
        """Initiating the test case to verify List CSM user with limit=<int>.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(
            self.csm_user.list_csm_users(expect_status_code=self.csm_user.const.BAD_REQUEST, limit='',
                                         verify_negative_scenario=True))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5001(self):
        """
        Test that GET API with invalid value for sort_by param returns 400 response code
        and appropriate error json data
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        invalid_sortby = self.csm_conf["test_5001"]["invalid_sortby"]
        resp_msg = self.csm_conf["test_5001"]["response_msg"]
        response = self.csm_user.list_csm_users(expect_status_code=self.csm_user.bad_request_response,
                                                sort_by=invalid_sortby, return_actual_response=True)

        self.log.info("Verifying the response for invalid value for sort_by")
        self.assertTrue(response.json(), resp_msg)
        self.log.info("Verified the response for invalid value for sort_by")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5000(self):
        """
        Test that GET API with valid value for sort_by param returns 200 response code
        and appropriate json data
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        valid_sortby = self.csm_conf["test_5000"]["valid_sortby"]
        for sortby in valid_sortby:
            self.log.info("Sorting by :{}".format(sortby))
            response = self.csm_user.list_csm_users(
                expect_status_code=self.csm_user.success_response, sort_by=sortby, return_actual_response=True)
            self.log.info("Verifying the actual response...")
            message_check = self.csm_user.verify_list_csm_users(
                response.json(), sort_by=sortby)
            self.assertTrue(message_check)
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5004(self):
        """
        Test that GET API with invalid value for sort_dir param returns 400 response code and appropriate error json data
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        invalid_sortdir = self.csm_conf["test_5004"]["invalid_sortdir"]
        self.log.info("Checking the sort dir option...")
        response = self.csm_user.list_csm_users(expect_status_code=self.csm_user.bad_request_response,
                                                sort_dir=invalid_sortdir, return_actual_response=True)
        self.log.info("Checking the error message text...")
        message_check = self.csm_user.const.SORT_DIR_ERROR in response.json()[
            'message_id']
        self.assertTrue(message_check, response)
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_4954(self):
        """Initiating the test case to create csm users and List CSM user with limit > created csm users.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(
            self.csm_user.list_actual_num_of_csm_users())
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5006(self):
        """Initiating the test case to verify list CSM user with valid offset,limit,sort_by and sort_dir parameters provided.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.assertTrue(
            self.csm_user.verify_csm_user_list_valid_params())
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5008(self):
        """Initiating the test case to verify that 403 is returned by csm list users api for unauthorised access
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        self.log.info(
            "Verifying csm list users api unauthorised access for s3 user")
        self.assertTrue(
            self.csm_user.verify_list_csm_users_unauthorised_access_failure(login_as="s3account_user"))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5005(self):
        """
        Test that GET API with empty value for sort_dir param returns 400 response code
        and appropriate error json data
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        resp_msg = self.csm_conf["test_5005"]["response_msg"]

        self.log.info(
            "Fetching the response for empty sort_by parameter with the expected status code")
        response = self.csm_user.list_csm_users_empty_param(expect_status_code=self.csm_user.bad_request_response,
                                                            csm_list_user_param="sort_dir", return_actual_response=True)

        self.log.info("Verifying the error response returned status code: {}, response : {}".format(
            response.status_code, response.json()))
        self.assertEqual(
            response.json(), resp_msg)
        self.log.info(
            "Verified that the returned error response is as expected: {}".format(response.json()))
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5009(self):
        """
        Test that GET API returns 200 response code and appropriate json data for valid username input.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info("Step 1: Creating a valid csm user")
        response = self.csm_user.create_csm_user(
            user_type="valid", user_role="manage")
        self.log.info("Verifying that user was successfully created")
        self.assertTrue(response.status_code ==
                        self.csm_user.success_response_post)

        self.log.info("Reading the username")
        username = response.json()["username"]

        self.log.info(
            "Step 2: Sending the request to user {}".format(username))
        response = self.csm_user.list_csm_single_user(request_type="get",
                                                      expect_status_code=self.csm_user.success_response, user=username, return_actual_response=True)
        self.log.info("Verifying the status code returned")
        self.assertEqual(self.csm_user.success_response, response.status_code)
        actual_response = response.json()

        self.log.info(
            "Step 3: Fetching list of all users")
        response = self.csm_user.list_csm_users(
            expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.log.info(
            "Verifying that response to fetch all users was successful")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response)
        self.log.info(
            "Step 4: Fetching the user {} information from the list".format(username))
        expected_response = []
        for item in response.json()["users"]:
            if item["username"] == username:
                expected_response = item
                break
        self.log.info("Verifying the actual response {} is matching the expected response {}".format(
            actual_response, expected_response))
        self.assertTrue(self.csm_user.verify_json_response(actual_result=actual_response, expect_result=expected_response,
                                                           match_exact=True))
        self.log.info(
            "Verified that the status code is 200 and response is as expected: {}".format(actual_response))

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5002(self):
        """
        Test that GET API with no value for sort_by param returns 400 response code
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        resp_msg = self.csm_conf["test_5002"]["response_msg"]

        self.log.info("Fetching csm user with empty sort by string...")
        response = self.csm_user.list_csm_users(expect_status_code=self.csm_user.bad_request_response,
                                                sort_by="", return_actual_response=True)

        self.log.info("Verifying error response...")
        self.assertTrue(response.json(), resp_msg)

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5003(self):
        """
        Test that GET API with valid value for sort_dir param returns 200 response code and appropriate json data
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))
        valid_sortdir = self.csm_conf["test_5003"]["valid_sortdir"]
        for sortdir in valid_sortdir:
            self.log.info("Sorting dir by :{}".format(sortdir))
            response_text = self.csm_user.list_csm_users(
                expect_status_code=self.csm_user.success_response, sort_dir=sortdir, return_actual_response=True)
            self.log.info("Verifying the actual response...")
            response = self.csm_user.verify_list_csm_users(
                response_text.json(), sort_dir=sortdir)
            self.assertTrue(response)
        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5016(self):
        """
        Test that PATCH API returns 200 response code and appropriate json data for valid payload data.
        :avocado: tags=rest_csm_user_test
        """

        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        # Test Purpose 1: Verifying root user can modify manage role user
        self.log.info(
            "Test Purpose 1: Verifying that csm root user can modify role and password of csm manage role user")

        user = self.csm_conf["test_5016"]["user"]
        self.log.info("Test Purpose 1: Step 1: Creating csm manage user")
        response = self.csm_user.create_csm_user(
            user_type=user[0], user_role=user[1])
        self.log.info(
            "Verifying if user was created successfully")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response_post)
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info("User {} got created successfully".format(username))

        self.log.info(
            "Test Purpose 1: Step 2: Login as csm root user and change password and role of user {}".format(username))
        data = self.csm_conf["test_5016"]["payload_monitor"]
        self.log.info("Forming the payload")
        payload = {"roles": [data["role"]], "password": data["password"]}
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=userid, data=True, payload=json.dumps(payload), return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verifying if the password {} and role {} was updated successfully for csm user {}".format(
            data["password"], data["role"], username))
        self.log.info("Logging in as user {}".format(username))
        payload_login = {"username": username, "password": data["password"]}
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.assertEqual(response.json()["roles"][0], user[2])

        self.log.info("Test Purpose 1: Verified status code {} was returned along with response {}".format(
            response.status_code, response.json()))
        self.log.info("Test Purpose 2: Verified that the password {} and role {} was updated successfully for csm user {}".format(
            payload["password"], response.json()["roles"][0], username))

        # Test Purpose 2: Verifying root user can modify monitor role user
        self.log.info(
            "Test Purpose 2: Verifying that csm root user can modify role and password of csm monitor role user")
        self.log.info("Test Purpose 2: Step 1: Creating csm monitor user")
        response = self.csm_user.create_csm_user(
            user_type=user[0], user_role=user[2])
        self.log.info(
            "Verifying if user was created successfully")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response_post)
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info("User {} got created successfully".format(username))

        self.log.info(
            "Test Purpose 2 : Step 2: Login as csm root user and change password and role of user {}".format(username))
        data = self.csm_conf["test_5016"]["payload_manage"]
        payload = {"roles": [data["role"]], "password": data["password"]}
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=userid, data=True, payload=json.dumps(payload), return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verifying if the password {} and role {} was updated successfully for csm user {}".format(
            payload["password"], payload["roles"], username))
        self.log.info("Logging in as user {}".format(username))
        payload_login = {"username": username, "password": payload["password"]}
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.assertEqual(response.json()["roles"][0], user[1])

        self.log.info("Test Purpose 2: Verified status code {} was returned along with response {}".format(
            response.status_code, response.json()))
        self.log.info("Test Purpose 2: Verified that the password {} and role {} was updated successfully for csm user {}".format(
            payload["password"], response.json()["roles"][0], username))

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_1228(self):
        """
        Test that CSM user with role manager can perform GET and POST API request on S3 Accounts
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Test Purpose 1: Verifying that csm manage user can perform POST api request on S3 account")

        self.log.info(
            "Test Purpose 1: Step 1: Logging in as csm user and creating s3 account")
        response = self.s3_accounts.create_s3_account(
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code,
                         self.csm_user.const.SUCCESS_STATUS)

        s3_account_name = response.json()["account_name"]

        self.log.info("Verified status code {} was returned along with response {} for s3 account {} creation".format(
            response.status_code, response.json(), s3_account_name))
        self.log.info(
            "Test Purpose 1: Verified that csm manage user was able to create s3 account")

        self.log.info(
            "Test Purpose 1: Verified that csm manage user can perform POST api request on S3 account")

        self.log.info(
            "Test Purpose 2: Step 1: Logging in as csm user to get the details of the s3 account")
        response = self.s3_accounts.list_all_created_s3account(
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code,
                         self.csm_user.const.SUCCESS_STATUS)
        s3_accounts = [item["account_name"]
                       for item in response.json()["s3_accounts"]]
        self.log.info(s3_accounts)
        self.assertIn(s3_account_name, s3_accounts)
        self.log.info("Verified status code {} was returned for getting account {} details  along with response {}".format(
            response.status_code, s3_account_name, response.json()))
        self.log.info(
            "Test Purpose 2: Verified that csm manage user was able to get the details of s3 account")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_1237(self):
        """
        Test that CSM user with monitor role can perform GET API request for CSM user
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Test Purpose: Verifying that CSM user with monitor role can perform GET API request for CSM user")

        self.log.info("Step 1: Creating csm user")
        response = self.csm_user.create_csm_user()
        self.log.info(
            "Verifying if user was created successfully")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response_post)
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info(
            "Step 2: Verified User {} got created successfully".format(username))

        self.log.info(
            "Step 3: Login as csm monitor user and perform get request on csm user {}".format(username))
        response = self.csm_user.list_csm_single_user(request_type="get",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=userid, return_actual_response=True, login_as="csm_user_monitor")
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.log.info(
            "Verifying that get request was successful for csm user {}".format(username))
        self.assertIn(username, response.json()["username"])

        self.log.info("Verified that status code {} was returned along with response: {} for the get request for csm user {}".format(response.status_code,
                                                                                                                                     response.json(), username))
        self.log.info(
            "Step 4: Verified that CSM user with monitor role successfully performed GET API request for CSM user")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_1235(self):
        """
        Test that CSM user with role monitor can perform GET API request for S3 Accounts
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Test Purpose: Verifying that csm monitor user can perform GET api request on S3 accounts")

        self.log.info(
            "Step 1: Creating s3 account")
        response = self.s3_accounts.create_s3_account()
        self.log.info("Verifying s3 account was successfully created")
        self.assertEqual(response.status_code,
                         self.csm_user.const.SUCCESS_STATUS)
        s3_account_name = response.json()["account_name"]
        self.log.info(
            "Step 2: Verified s3 account {} was successfully created ".format(s3_account_name))

        self.log.info(
            "Step 3: Logging in as csm monitor user to get the details of the s3 accounts")
        response = self.s3_accounts.list_all_created_s3account(
            login_as="csm_user_monitor")
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code,
                         self.csm_user.const.SUCCESS_STATUS)
        s3_accounts = [item["account_name"]
                       for item in response.json()["s3_accounts"]]
        self.log.info(s3_accounts)
        self.assertIn(s3_account_name, s3_accounts)
        self.log.info("Verified status code {} was returned for getting account {} details  along with response {}".format(
            response.status_code, s3_account_name, response.json()))
        self.log.info(
            "Step 4: Verified that csm monitor user was able to get the details of s3 accounts using GET api")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_7421(self):
        """
        Test Non root user should able to change its password by specifying old_password and new password
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Test Purpose: Verifying non root user should able to change its password by specifying old_password and new password ")

        data = self.csm_conf["test_7421"]["data"]
        username = self.csm_user.config["csm_user_manage"]["username"]
        self.log.info(
            "Step 1: Login as csm non root user and change password and role of user without providing old password {}".format(username))
        self.log.info(
            "Forming the payload specifying old password for csm manage user")
        old_password = self.csm_user.config["csm_user_manage"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=username, data=True, payload=json.dumps(payload_user),
                                                      return_actual_response=True, login_as="csm_user_manage")

        self.log.info("Verifying response code {} and response {}  returned".format(
            response.status_code, response.json()))
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verifying if the password {} was updated successfully for csm user {}".format(
            data[0], username))
        self.log.info(
            "Logging in as user {} with new password {}".format(username, data[0]))
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verified login with new password was successful with status code {} and response {}".format(
            response.status_code, response.json()))
        self.log.info("Verified that the password {} was updated successfully for csm user {}".format(
            data[0], response.json()["roles"][0], username))

        self.log.info("Reverting old password for user {}".format(username))
        payload_user = {"password": old_password}
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=username, data=True, payload=json.dumps(payload_user),
                                                      return_actual_response=True)

        self.log.info("Verifying response code and response returned".format(
            response.status_code, response.json()))
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_7420(self):
        """
        Test that Root user should able to change other users password and roles without specifying old_password through CSM-REST
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Test Purpose: Verifying that csm root user should able to change other users password and roles without specifying old_password")

        data = self.csm_conf["test_7420"]["data"]
        self.log.info("Step 1: Creating csm manage user")
        response = self.csm_user.create_csm_user(
            user_type=data[0], user_role=data[1])

        self.log.info(
            "Verifying if user was created successfully")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response_post)
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info(
            "Verified User {} got created successfully".format(username))

        self.log.info(
            "Step 2: Login as csm root user and change password and role of user without providing old password {}".format(username))
        self.log.info("Forming the payload without specifying old password")
        payload_user = {"roles": [data[2]], "password": data[3]}
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=userid, data=True, payload=json.dumps(payload_user), return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verifying if the password {} and role {} was updated successfully for csm user {}".format(
            data[3], data[2], username))
        self.log.info(
            "Logging in as user {} with new password {}".format(username, data[3]))
        payload_login = {"username": username, "password": data[3]}
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.assertEqual(response.json()["roles"][0], data[2])

        self.log.info("Verified login with new password was successful with status code {} and response {}".format(
            response.status_code, response.json()))
        self.log.info("Verified that the password {} and role {} was updated successfully for csm user {}".format(
            data[3], response.json()["roles"][0], username))

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_7411(self):
        """
        Test that root user should able to modify self password through CSM-REST
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Test Purpose: Verifying Test that root user should able to modify self password using PATCH request ")

        data = self.csm_conf["test_7411"]["data"]
        username = self.csm_user.config["csm_admin_user"]["username"]

        self.log.info(
            "Step 1: Login as csm root user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm root user")
        old_password = self.csm_user.config["csm_admin_user"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=username, data=True, payload=json.dumps(payload_user),
                                                      return_actual_response=True, login_as="csm_admin_user")
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.log.info("Verifying if the password {} was updated successfully for csm user {}".format(
            data[0], username))

        self.log.info(
            "Step 2:Logging in as csm root user {} with new password {}".format(username, data[0]))
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verified login with new password was successful with status code {} and response {}".format(
            response.status_code, response.json()))
        self.log.info("Verified that the password {} was updated successfully for csm root user {}".format(
            data[0], username))

        self.log.info("Reverting the password...")
        response = self.csm_user.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info(
            "Verifying password was reverted and response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_1229(self):
        """
        Test that CSM user with manage role can perform GET, POST, PATCH and DELETE API request for CSM user
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        data = self.csm_conf["test_1229"]["data"]
        # -------------------------------------------------------------------------------------------
        self.log.info(
            "Test Purpose 1: Verifying that CSM user with manage role can perform POST request and create a new csm user")
        self.log.info(
            "Test Purpose 1: Step 1: CSM manage user performing POST request")
        response = self.csm_user.create_csm_user(
            user_type=data[0], user_role=data[1], login_as="csm_user_manage")
        self.log.info(
            "Verifying if user was created successfully")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response_post)

        username = response.json()["username"]
        userid = response.json()["id"]
        actual_response = response.json()
        self.log.info(
            "Fetching list of all users")
        response1 = self.csm_user.list_csm_users(
            expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response1.status_code,
                         self.csm_user.success_response)
        self.log.info(
            "Fetching the user {} information from the list".format(username))
        expected_response = []
        for item in response1.json()["users"]:
            if item["username"] == username:
                expected_response = item
                break
        self.log.info("Verifying the actual response {} is matching the expected response {}".format(
            actual_response, expected_response))
        self.assertTrue(self.csm_user.verify_json_response(actual_result=actual_response, expect_result=expected_response,
                                                           match_exact=True))
        self.log.info("User {} got created successfully".format(username))
        self.log.info("Status code {} was returned along with response: {} for the POST request for csm user {}".format(response.status_code,
                                                                                                                        response.json(), username))
        self.log.info(
            "Test Purpose 1: Verified that CSM user with manage role can perform POST request and create a new csm user")

        # --------------------------------------------------------------------------------------------------------
        self.log.info(
            "Test Purpose 2: Verifying that that CSM user with manage role can perform GET request for CSM user")
        self.log.info(
            "Test Purpose 2: Step 1: CSM manage user performing GET request")
        response = self.csm_user.list_csm_single_user(request_type="get",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=userid, return_actual_response=True, login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.log.info(
            "Verifying that get request was successful for csm user {}".format(username))
        self.assertIn(username, response.json()["username"])
        self.log.info("Status code {} was returned along with response: {} for the GET request for csm user {}".format(response.status_code,
                                                                                                                       response.json(), username))
        self.log.info(
            "Test Purpose 2: Verified that CSM user with manage role can perform GET request for CSM user")

        # ----------------------------------------------------------------------------------------------------------
        self.log.info(
            "Test Purpose 3: Verifying that that CSM user with manage role can perform DELETE itself")
        response = self.csm_user.list_csm_single_user(request_type="delete",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user="csm_user_manage", return_actual_response=True, login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.log.info("Status code {} was returned along with response {} for Delete request".format(
            response.status_code, response.json()))
        self.log.info(
            "Test Purpose 3: Verified that CSM user with manage role can perform DELETE request for CSM user")

        # -------------------------------------------------------------------------------------------------
        self.log.info(
            "Test Purpose 4: Verifying that that CSM user with manage role can perform PATCH request for itself")
        self.log.info(
            "Test Purpose 4: Step 1: Create csm manage user")
        response = self.csm_user.create_csm_user(
            user_type="pre-define", user_role="manage")
        self.log.info(
            "Verifying if user was created successfully")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response_post)
        self.log.info("User {} got created successfully".format(username))
        username = response.json()["username"]
        userid = response.json()["id"]

        self.log.info(
            "Test Purpose 4: Step 2: Login as csm manage user and modify its own password using Patch request")
        self.log.info("Forming the payload")
        old_password = self.csm_user.config["csm_user_manage"]["password"]
        payload = {"current_password": old_password, "password": data[3]}

        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user="csm_user_manage", data=True, payload=json.dumps(payload), return_actual_response=True, login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verifying if the password {} was updated successfully for csm user {}".format(
            data[3], username))
        self.log.info("Logging in as user {}".format(username))
        payload_login = {"username": username, "password": data[3]}
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Status code {} was returned along with response {} for Patch request".format(
            response.status_code, response.json()))
        self.log.info(
            "Test Purpose 4: Verified that CSM user with manage role can perform PATCH request for itself")

        self.log.info(
            "Reverting the password of pre-configured user csm_user_manage")

        payload = {"current_password": data[3], "password": old_password}
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user="csm_user_manage", data=True, payload=json.dumps(payload), return_actual_response=True, login_as="csm_admin_user")
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)
        # ------------------------------------------------------------------------------------------------------
        self.log.info(
            "Verified that CSM user with manage role can perform GET, POST, PATCH and DELETE API request for CSM user")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5019(self):
        """
        Test that PATCH API returns 200 response code and appropriate json data for partial payload.
        :avocado: tags=rest_csm_user_test
        """

        # Test Purpose 1: Verifying root user can change the role of csm manage user partially without changing the password
        self.log.info(
            "Test Purpose 1: Verifying that csm root user can partially modify csm manage user by modifying only the user's role")

        user = self.csm_conf["test_5019"]["user"]
        payload_login = self.csm_conf["test_5019"]["payload_login"]
        self.log.info("Test Purpose 1: Step 1: Creating csm manage user")
        response = self.csm_user.create_csm_user(
            user_type=user[0], user_role=user[1])
        self.log.info(
            "Verifying if user was created successfully")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response_post)
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info("User {} got created successfully".format(username))

        self.log.info(
            "Test Purpose 1: Step 2: Login as csm root user and change only the role of user {}".format(username))
        self.log.info("Forming the payload")
        payload = {"roles": [user[2]]}

        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=userid, data=True, payload=json.dumps(payload), return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verifying if the role {} was updated successfully for csm user {}".format(
            user[2], username))

        userdata = json.loads(self.csm_user.const.USER_DATA)
        self.log.info("Logging in as user {}".format(username))

        payload_login["username"] = username
        payload_login["password"] = userdata["password"]

        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.assertEqual(response.json()["roles"][0], user[2])

        self.log.info("Test Purpose 1: Verified status code {} was returned along with response {}".format(
            response.status_code, response.json()))

        self.log.info("Test Purpose 1: Verified that the role {} was updated successfully for csm user {}".format(
            response.json()["roles"][0], username))

        # Test Purpose 2: Verifying root user can change the password of csm manage user partially without changing the role
        self.log.info(
            "Test Purpose 2: Verifying that csm root user can partially modify csm manage user by modifying only the user's password")

        self.log.info(
            "Test Purpose 2: Step 1: Login as csm root user and change only the password of user {}".format(username))

        self.log.info("Forming the payload")
        payload = {"password": user[3]}

        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=userid, data=True, payload=json.dumps(payload), return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verifying if the password {} was updated successfully for csm user {}".format(
            user[3], username))

        self.log.info(
            "Logging in as user {} with the changed password {}".format(username, user[3]))

        payload_login["username"] = username
        payload_login["password"] = user[3]
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Test Purpose 2: Verified status code {} was returned along with response {}".format(
            response.status_code, response.json()))

        self.log.info("Test Purpose 2: Verified that the password {} was updated successfully for csm user {}".format(
            user[3], username))

        # Test Purpose 3: Verifying root user can change the role of csm monitor user partially without changing the password
        self.log.info(
            "Test Purpose 3: Verifying that csm root user can partially modify csm monitor user by modifying only the user's role")

        self.log.info("Test Purpose 3: Step 1: Creating csm monitor user")
        response = self.csm_user.create_csm_user(
            user_type=user[0], user_role=user[2])
        self.log.info(
            "Verifying if user was created successfully")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response_post)
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info("User {} got created successfully".format(username))

        self.log.info(
            "Test Purpose 3: Step 2: Login as csm root user and change only the role of user {}".format(username))

        self.log.info("Forming the payload")
        payload = {"roles": [user[1]]}

        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=userid, data=True, payload=json.dumps(payload), return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verifying if the role {} was updated successfully for csm user {}".format(
            user[2], username))

        self.log.info("Logging in as user {}".format(username))

        payload_login["username"] = username
        payload_login["password"] = userdata["password"]
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.assertEqual(response.json()["roles"][0], user[1])

        self.log.info("Test Purpose 3: Verified status code {} was returned along with response {}".format(
            response.status_code, response.json()))

        self.log.info("Test Purpose 3: Verified that the role {} was updated successfully for csm user {}".format(
            response.json()["roles"][0], username))

        # Test Purpose 4: Verifying root user can change the password of csm monitor user partially without changing the role
        self.log.info(
            "Test Purpose 4: Verifying that csm root user can partially modify csm monitor user by modifying only the user's password")

        self.log.info(
            "Test Purpose 4: Step 1: Login as csm root user and change only the password of user {}".format(username))
        self.log.info("Forming the payload")
        payload = {"password": user[3], "confirmPassword": user[3]}

        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=userid, data=True, payload=json.dumps(payload), return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verifying if the password {} was updated successfully for csm user {}".format(
            user[3], username))

        self.log.info(
            "Logging in as user {} with the changed password {}".format(username, user[3]))

        payload_login["username"] = username
        payload_login["password"] = user[3]

        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Test Purpose 4: Verified status code {} was returned along with response {}".format(
            response.status_code, response.json()))

        self.log.info("Test Purpose 4: Verified that the password {} was updated successfully for csm user {}".format(
            user[3], username))

    @ctp_fail_on(error_handler)
    def test_7422(self):
        """
        Test that Non root user cannot change roles through CSM-REST
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Step 1: Verifying that csm manage user cannot modify its role")

        username = self.csm_user.config["csm_user_manage"]["username"]
        expected_response_manage = self.csm_conf["test_7422"]["response_manage"]
        expected_response_manage["error_format_args"] = username

        self.log.info(
            "Creating payload for the Patch request")
        payload = self.csm_conf["test_7422"]["payload_manage"]
        payload["current_password"] = self.csm_user.config["csm_user_manage"]["password"]
        self.log.info("Payload for the patch request is {}".format(payload))

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.const.FORBIDDEN,
                                                      user=username, data=True, payload=json.dumps(payload),
                                                      return_actual_response=True, login_as="csm_user_manage")

        self.log.info(
            "Verifying response returned for user {}".format(username))
        self.assertEqual(response.status_code,
                         self.csm_user.const.FORBIDDEN)
        self.assertEqual(response.json(), expected_response_manage)
        self.log.info(
            "Step 1: Verified that csm manage user cannot modify its role and response returned is {}".format(response))

        self.log.info(
            "Step 2: Verifying that csm monitor user cannot modify its role")

        username = self.csm_user.config["csm_user_monitor"]["username"]

        self.log.info(
            "Creating payload for the Patch request")
        payload = self.csm_conf["test_7422"]["payload_monitor"]
        payload["current_password"] = self.csm_user.config["csm_user_monitor"]["password"]
        self.log.info("Payload for the patch request is {}".format(payload))

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.const.FORBIDDEN,
                                                      user=username, data=True, payload=json.dumps(payload),
                                                      return_actual_response=True, login_as="csm_user_monitor")

        self.log.info(
            "Verifying response returned for user {}".format(username))
        self.assertEqual(response.status_code,
                         self.csm_user.const.FORBIDDEN)
        self.log.info(
            "Step 2: Verified that csm monitor user cannot modify its role and response returned is {}".format(response))

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_7412(self):
        """
        Test that user should not able to change roles for root user through CSM-REST
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        username = self.csm_user.config["csm_admin_user"]["username"]
        expected_response_admin = self.csm_conf["test_7412"]["response_admin"]
        expected_response_admin["error_format_args"] = username

        self.log.info(
            "Step 1: Verifying that csm admin user should not be able to modify its own role")

        self.log.info(
            "Creating payload with for the Patch request")
        payload = self.csm_conf["test_7412"]["payload_admin"]
        payload["current_password"] = self.csm_user.config["csm_admin_user"]["password"]
        self.log.info("Payload for the patch request is {}".format(payload))

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.const.FORBIDDEN,
                                                      user=username, data=True, payload=json.dumps(payload),
                                                      return_actual_response=True, login_as="csm_admin_user")

        self.log.info("Verifying response returned")
        self.assertEqual(response.status_code,
                         self.csm_user.const.FORBIDDEN)
        self.assertEqual(response.json(), expected_response_admin)

        self.log.info(
            "Step 1: Verified that csm admin user is not be able to modify its own role and response returned is {}".format(response))

        self.log.info(
            "Step 2: Verifying that csm manage user should not be able to modify csm admin user role")

        self.log.info(
            "Creating payload with for the Patch request")
        payload = self.csm_conf["test_7412"]["payload"]
        self.log.info("Payload for the patch request is {}".format(payload))

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.const.FORBIDDEN,
                                                      user=username, data=True, payload=json.dumps(payload),
                                                      return_actual_response=True, login_as="csm_user_manage")

        self.log.info("Verifying response returned")
        self.assertEqual(response.status_code,
                         self.csm_user.const.FORBIDDEN)
        self.log.info(
            "Step 2: Verified that csm manage user is not be able to modify csm admin user role and response returned is {}".format(response))

        self.log.info(
            "Step 3: Verifying that csm monitor user should not be able to modify csm admin user role")

        self.log.info(
            "Creating payload with for the Patch request")
        payload = self.csm_conf["test_7412"]["payload"]
        self.log.info("Payload for the patch request is {}".format(payload))

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.const.FORBIDDEN,
                                                      user=username, data=True, payload=json.dumps(payload),
                                                      return_actual_response=True, login_as="csm_user_monitor")

        self.log.info("Verifying response returned")
        self.assertEqual(response.status_code,
                         self.csm_user.const.FORBIDDEN)
        self.log.info(
            "Step 3: Verified that csm monitor user is not be able to modify csm admin user role and response returned is {}".format(response))

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_7408(self):
        """
        Test that user should not be able to change its username through CSM-REST
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        payload = self.csm_conf["test_7408"]["payload"]
        resp_msg = self.csm_conf["test_7408"]["response_mesg"]

        self.log.info(
            "Step 1: Verifying that csm monitor user should not be able to modify its username")

        username = self.csm_user.config["csm_user_monitor"]["username"]

        self.log.info(
            "Creating payload for the Patch request")
        payload["current_password"] = self.csm_user.config["csm_user_monitor"]["password"]
        self.log.info("Payload for the patch request is: {}".format(payload))

        self.log.info("Sending the patch request for csm monitor user...")
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.bad_request_response,
                                                      user=username, data=True, payload=json.dumps(payload),
                                                      return_actual_response=True, login_as="csm_user_monitor")
        self.log.info(
            "Verifying response returned for user {}".format(username))
        self.assertEqual(response.status_code,
                         self.csm_user.bad_request_response)
        self.assertEqual(response.json(),
                         resp_msg)

        self.log.info(
            "Step 1: Verified that csm monitor user {} is not able to modify its username and response returned is {}".format(username, response))

        self.log.info(
            "Step 2: Verifying that csm manage user should not be able to modify its username")
        username = self.csm_user.config["csm_user_manage"]["username"]

        self.log.info(
            "Creating payload for the Patch request")
        payload["current_password"] = self.csm_user.config["csm_user_manage"]["password"]
        self.log.info("Payload for the patch request is: {}".format(payload))

        self.log.info("Sending the patch request for csm manage user...")
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.bad_request_response,
                                                      user=username, data=True, payload=json.dumps(payload),
                                                      return_actual_response=True, login_as="csm_user_manage")
        self.log.info(
            "Verifying response returned for user {}".format(username))
        self.assertEqual(response.status_code,
                         self.csm_user.bad_request_response)
        self.assertEqual(response.json(), resp_msg)
        self.log.info(
            "Step 2: Verified that csm manage user {} is not be able to modify its username and response returned is {}".format(username, response))

        self.log.info(
            "Step 3: Verifying that csm admin user should not be able to modify its username")
        username = self.csm_user.config["csm_admin_user"]["username"]

        self.log.info(
            "Creating payload for the Patch request")
        payload["current_password"] = self.csm_user.config["csm_admin_user"]["password"]
        self.log.info("Payload for the patch request is: {}".format(payload))

        self.log.info("Sending the patch request for csm admin user...")
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.bad_request_response,
                                                      user=username, data=True, payload=json.dumps(payload),
                                                      return_actual_response=True, login_as="csm_admin_user")
        self.log.info(
            "Verifying response returned for user {}".format(username))
        self.assertEqual(response.status_code,
                         self.csm_user.bad_request_response)
        self.assertEqual(response.json(), resp_msg)

        self.log.info(
            "Step 3: Verified that csm admin user {} is not be able to modify its username and response returned is {}".format(username, response))

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_6220(self):
        """
        Test that duplicate users should not be created between csm users and s3 account users in CSM REST
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        data = self.csm_conf["test_6220"]
        self.log.info(
            "Step 1: Verifying that csm admin user should not be able to create duplicate csm user")

        username = self.csm_user.config["csm_user_manage"]["username"]
        mesg = data["response_duplicate_csm_manage_user"]["message"]
        data["response_duplicate_csm_manage_user"]["message"] = f"{mesg} {username}"

        self.log.info(
            "Logging in as csm admin user to create duplicate csm user {}".format(username))
        response = self.csm_user.create_csm_user(
            user_type="pre-define", user_role="manage", login_as="csm_admin_user")

        self.log.info("Verifying response code: {} and response returned: {}".format(
            response.status_code, response.json()))
        self.assertEqual(response.status_code, self.csm_user.const.CONFLICT)
        self.assertEqual(
            response.json(), data["response_duplicate_csm_manage_user"])
        self.log.info("Verified response returned")

        self.log.info(
            "Step 1: Verified that csm admin user is not able to create duplicate csm user")

        self.log.info(
            "Step 2: Verifying that csm manage user should not be able to create duplicate csm user")

        username = self.csm_user.config["csm_user_monitor"]["username"]
        mesg = data["response_duplicate_csm_monitor_user"]["message"]
        data["response_duplicate_csm_monitor_user"]["message"] = f"{mesg} {username}"

        self.log.info(
            "Logging in as csm manage user to create duplicate csm user {}".format(username))

        response = self.csm_user.create_csm_user(
            user_type="pre-define", user_role="monitor", login_as="csm_user_manage")

        self.log.info("Verifying response code: {} and response returned: {}".format(
            response.status_code, response.json()))
        self.assertEqual(response.status_code, self.csm_user.const.CONFLICT)
        self.assertEqual(
            response.json(), data["response_duplicate_csm_monitor_user"])

        self.log.info("Verified response returned")

        self.log.info(
            "Step 2: Verified that csm manage user is not able to create duplicate csm user")

        s3account = self.csm_user.config["s3account_user"]["username"]
        data["response_duplicate_s3_account"]["error_format_args"]["account_name"] = s3account

        self.log.info(
            "Step 3: Verifying that csm admin user should not be able to create duplicate s3 account")

        self.log.info(
            "Logging in as csm admin user to create duplicate s3 account {}".format(s3account))
        response = self.s3_accounts.create_s3_account(
            user_type="pre-define", login_as="csm_admin_user")

        self.log.info("Verifying response")
        self.assertEqual(response.status_code, self.csm_user.const.CONFLICT)
        self.assertEqual(
            response.json(), data["response_duplicate_s3_account"])
        self.log.info("Verified response returned is: {}, {}".format(
            response, response.json()))

        self.log.info(
            "Step 3: Verified that csm admin user is not able to create duplicate s3 account")

        self.log.info(
            "Step 4: Verifying that csm manage user should not be able to create duplicate s3 account")

        self.log.info(
            "Logging in as csm manage user to create duplicate s3 account {}".format(s3account))
        response = self.s3_accounts.create_s3_account(
            user_type="pre-define", login_as="csm_user_manage")

        self.log.info("Verifying response")
        self.assertEqual(response.status_code, self.csm_user.const.CONFLICT)
        self.assertEqual(
            response.json(), data["response_duplicate_s3_account"])
        self.log.info("Verified response returned is: {}, {}".format(
            response, response.json()))

        self.log.info(
            "Step 4: Verified that csm manage user is not able to create duplicate s3 account")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5021(self):
        """
        Test that DELETE API with default argument returns 200 response code and appropriate json data.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Step 1: Verifying that DELETE API with default argument returns 200 response code and appropriate json data")

        message = self.csm_conf["test_5021"]["response_message"]

        self.log.info("Creating csm user")
        response = self.csm_user.create_csm_user()

        self.log.info("Verifying that user was successfully created")
        self.assertTrue(response.status_code ==
                        self.csm_user.success_response_post)

        self.log.info("Reading the username")
        username = response.json()["username"]

        self.log.info(
            "Sending request to delete csm user {}".format(username))
        response = self.csm_user.list_csm_single_user(request_type="delete",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=username, return_actual_response=True)

        self.log.info("Verifying response returned")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response)
        self.log.info("Verified success status {} is returned".format(
            response.status_code))

        self.log.info("Verifying proper message is returned")
        self.assertEqual(response.json(),
                         message)
        self.log.info(
            "Verified message returned is: {}".format(response.json()))

        self.log.info(
            "Step 1: Verified that DELETE API with default argument returns 200 response code and appropriate json data")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5023(self):
        """
        Test that DELETE API returns 403 response for unauthorized request.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Step 1: Verifying that DELETE API returns 403 response for unauthorized request")

        self.log.info("Checking if s3 account is present")
        self.config = CSMConfigsCheck()
        user_already_present = self.config.check_predefined_s3account_present()
        if not user_already_present:
            user_already_present = self.config.setup_csm_s3
        self.assertTrue(user_already_present)

        self.log.info(
            "Sending request to delete csm user with s3 authentication")
        response = self.csm_user.list_csm_single_user(request_type="delete",
                                                      expect_status_code=self.csm_user.forbidden,
                                                      user="csm_user_manage", return_actual_response=True, login_as="s3account_user")

        self.log.info("Verifying response returned")

        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)

        self.log.info(
            "Step 1: Verified that DELETE API returns 403 response for unauthorized request : {}".format(response))

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5020(self):
        """
        Test that PATCH API returns 400 response code and appropriate json data for empty payload.
        :avocado: tags=rest_csm_user_test
        """

        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        data = self.csm_conf["test_5020"]
        payload = {}
        self.log.info(
            "Step 1: Verifying that PATCH API returns 400 response code and appropriate json data for empty payload")

        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.bad_request_response,
                                                      user="csm_user_manage", data=True, payload=json.dumps(payload), return_actual_response=True)

        self.log.info("Verifying the status code returned : {}".format(
            response.status_code))
        self.assertEqual(response.status_code,
                         self.csm_user.bad_request_response)
        self.log.info("Verified the status code returned")

        self.log.info(
            "Verifying the response message returned : {}".format(response.json()))
        self.assertEqual(response.json(), data["response_msg"])
        self.log.info(
            "Verified the response message returned")

        self.log.info(
            "Step 1: Verified that PATCH API returns 400 response code and appropriate json data for empty payload")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5017(self):
        """
        Test that PATCH API returns 404 response code and appropriate json data for user that does not exist.
        :avocado: tags=rest_csm_user_test
        """

        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        data = self.csm_conf["test_5017"]
        mesg = data["response_msg"]["message"]
        userid = data["invalid_user_id"]
        data["response_msg"]["message"] = f"{mesg} {userid}"

        self.log.info(
            "Step 1: Verifying that PATCH API returns 404 response code and appropriate json data for user that does not exist")

        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.method_not_found,
                                                      user=userid, data=True, payload=json.dumps(data["payload"]), return_actual_response=True)

        self.log.info("Verifying the status code returned : {}".format(
            response.status_code))
        self.assertEqual(response.status_code,
                         self.csm_user.method_not_found)
        self.log.info("Verified the status code returned")

        self.log.info(
            "Verifying the response message returned : {}".format(response.json()))
        self.assertEqual(response.json(), data["response_msg"])
        self.log.info(
            "Verified the response message returned")

        self.log.info(
            "Step 1: Verified that PATCH API returns 404 response code and appropriate json data for user does not exist")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5010(self):
        """
        Test that GET API returns 404 response code and appropriate json data for non-existing username input.
        :avocado: tags=rest_csm_user_test
        """

        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        data = self.csm_conf["test_5010"]
        mesg = data["response_msg"]["message"]
        userid = data["invalid_user_id"]
        data["response_msg"]["message"] = f"{mesg} {userid}"

        self.log.info(
            "Step 1: Verifying that GET API returns 404 response code and appropriate json data for non-existing username input")

        response = self.csm_user.list_csm_single_user(request_type="get",
                                                      expect_status_code=self.csm_user.method_not_found,
                                                      user=userid, return_actual_response=True)

        self.log.info("Verifying the status code returned : {}".format(
            response.status_code))
        self.assertEqual(response.status_code,
                         self.csm_user.method_not_found)
        self.log.info("Verified the status code returned")

        self.log.info(
            "Verifying the response message returned : {}".format(response.json()))
        self.assertEqual(response.json(), data["response_msg"])
        self.log.info(
            "Verified the response message returned")

        self.log.info(
            "Step 1: Verified that GET API returns 404 response code and appropriate json data for non-existing(invalid) username input")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_5018(self):
        """
        Test that PATCH API returns 400 response code and appropriate error json data for invalid payload.
        :avocado: tags=rest_csm_user_test
        """

        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        data = self.csm_conf["test_5018"]

        self.log.info(
            "Step 1: Verifying that PATCH API returns 400 response code and appropriate error json data for invalid password")

        for i in range(1, data["range"][0]):
            self.log.info("Verifying for invalid password: {}".format(
                data[f'payload_invalid_password_{str(i)}']))
            response = self.csm_user.list_csm_single_user(request_type="patch",
                                                          expect_status_code=self.csm_user.bad_request_response,
                                                          user="csm_user_manage", data=True, payload=json.dumps(data[f'payload_invalid_password_{str(i)}']), return_actual_response=True)

            self.log.info("Verifying the returned status code: {} and response: {} ".format(
                response.status_code, response.json()))
            self.assertEqual(response.status_code,
                             self.csm_user.bad_request_response)
            self.assertEqual(
                response.json(), data[f'invalid_password_resp_{str(i)}'])

        self.log.info(
            "Step 1: Verified that PATCH API returns 400 response code and appropriate error json data for invalid password")

        self.log.info(
            "Step 2: Verifying that PATCH API returns 400 response code and appropriate error json data for invalid role")

        self.log.info("Verifying for invalid role: {}".format(
            data["invalid_role_resp"]))
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.bad_request_response,
                                                      user="csm_user_manage", data=True, payload=json.dumps(data["payload_invalid_role"]), return_actual_response=True)

        self.log.info("Verifying the returned status code: {} and response: {} ".format(
            response.status_code, response.json()))
        self.assertEqual(response.status_code,
                         self.csm_user.bad_request_response)
        self.assertEqual(response.json(), data["invalid_role_resp"])

        self.log.info(
            "Step 2: Verified that PATCH API returns 400 response code and appropriate error json data for invalid role")

        self.log.info(
            "Step 3: Verifying that PATCH API returns 400 response code and appropriate error json data for invalid password and role")

        self.log.info("Verifying for invalid role and invalid password: {}".format(
            data["payload_invalid_password_role"]))
        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.bad_request_response,
                                                      user="csm_user_manage", data=True, payload=json.dumps(data["payload_invalid_password_role"]), return_actual_response=True)

        self.log.info("Verifying the returned status code: {} and response: {} ".format(
            response.status_code, response.json()))
        self.assertEqual(response.status_code,
                         self.csm_user.bad_request_response)

        data_new1 = response.json()["message"].split(':')
        data_new2 = data_new1[1].split('{')
        if data_new2[1] == "'roles'":
            role_passwd_resp = data["invalid_password_role_resp_1"]
        elif data_new2[1] == "'password'":
            role_passwd_resp = data["invalid_password_role_resp_2"]

        self.assertEqual(response.json(), role_passwd_resp)

        self.log.info(
            "Step 3: Verified that PATCH API returns 400 response code and appropriate error json data for invalid password and role")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_1173(self):
        """
        Test that in case the password is changed the user should not be able to login with the old password
        :avocado: tags=rest_csm_user_test
        """

        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        data = self.csm_conf["test_1173"]["data"]
        status_code = self.csm_conf["test_1173"]["status_code"]

        # Verifying that CSM admin user should not be able to login with old password
        self.log.info(
            "Step 1: Verifying that CSM admin user should not be able to login with old password")

        username = self.csm_user.config["csm_admin_user"]["username"]

        self.log.info(
            "Step 1A: Login as csm root user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm root user")
        old_password = self.csm_user.config["csm_admin_user"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        self.log.info("Payload is: {}".format(payload_user))

        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=username, data=True, payload=json.dumps(payload_user),
                                                      return_actual_response=True, login_as="csm_admin_user")

        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.log.info("Verified response code 200 was returned")

        self.log.info("Verifying if the password {} was updated successfully for csm user {}".format(
            data[0], username))
        self.log.info(
            "Step 1B:Logging in as csm root user {} with new password {}".format(username, data[0]))
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verified login with new password was successful with status code {} and response {}".format(
            response.status_code, response.json()))

        self.log.info(
            "Step 1C:Verifying by logging in as csm root user {} with old password {}".format(username, self.csm_user.config["csm_admin_user"]["password"]))
        payload_login = {"username": username, "password": old_password}

        response = self.csm_user.restapi.rest_call(request_type="post",
                                                   endpoint=self.csm_user.config["rest_login_endpoint"],
                                                   data=json.dumps(payload_login), headers=self.csm_user.config["Login_headers"])

        self.log.info("Verifying the status code {} returned".format(
            response.status_code))
        self.assertEqual(response.status_code, status_code)

        self.log.info("Verified login with old password was not successful!")

        self.log.info("Reverting old password")
        response = self.csm_user.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info(
            "Step 1: Verified that CSM admin user should not be able to login with old password")

        # Verifying that CSM manage user should not be able to login with old password
        self.log.info(
            "Step 2: Verifying that CSM manage user should not be able to login with old password")

        username = self.csm_user.config["csm_user_manage"]["username"]

        self.log.info(
            "Step 2A: Login as csm manage user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm manage user")
        old_password = self.csm_user.config["csm_user_manage"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        self.log.info("Payload is: {}".format(payload_user))

        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=username, data=True, payload=json.dumps(payload_user),
                                                      return_actual_response=True, login_as="csm_user_manage")

        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.log.info("Verifying response code 200 was returned")

        self.log.info("Verifying if the password {} was updated successfully for csm manage user {}".format(
            data[0], username))
        self.log.info(
            "Step 2B:Logging in as csm manage user {} with new password {}".format(username, data[0]))
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verified login with new password was successful with status code {} and response {}".format(
            response.status_code, response.json()))
        self.log.info("Verified that the password {} was updated successfully for csm manage user {}".format(
            data[0], username))

        self.log.info(
            "Step 2C:Verifying by logging in as csm manage user {} with old password {}".format(username, self.csm_user.config["csm_user_manage"]["password"]))
        payload_login = {"username": username, "password": old_password}

        response = self.csm_user.restapi.rest_call(request_type="post",
                                                   endpoint=self.csm_user.config["rest_login_endpoint"],
                                                   data=json.dumps(payload_login), headers=self.csm_user.config["Login_headers"])

        self.log.info("Verifying the status code {} returned".format(
            response.status_code))
        self.assertEqual(response.status_code, status_code)
        self.log.info("Verified login with old password was not successful!")

        self.log.info("Reverting old password")
        response = self.csm_user.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.log.info("Verified response code 200 was returned")

        self.log.info(
            "Step 2: Verified that CSM manage user should not be able to login with old password")

        # Verifying that CSM monitor user should not be able to login with old password
        self.log.info(
            "Step 3: Verifying that CSM monitor user should not be able to login with old password")

        username = self.csm_user.config["csm_user_monitor"]["username"]

        self.log.info(
            "Step 3A: Login as csm monitor user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm monitor user")
        old_password = self.csm_user.config["csm_user_monitor"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        self.log.info("Payload is: {}".format(payload_user))

        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.success_response,
                                                      user=username, data=True, payload=json.dumps(payload_user),
                                                      return_actual_response=True, login_as="csm_user_monitor")

        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.log.info("Verified response code 200 was returned")

        self.log.info("Verifying if the password {} was updated successfully for csm monitor user {}".format(
            data[0], username))
        self.log.info(
            "Step 3B:Logging in as csm monitor user {} with new password {}".format(username, data[0]))
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login), expect_status_code=self.csm_user.success_response, return_actual_response=True)
        self.assertEqual(response.status_code, self.csm_user.success_response)

        self.log.info("Verified login with new password was successful with status code {} and response {}".format(
            response.status_code, response.json()))
        self.log.info("Verified that the password {} was updated successfully for csm monitor user {}".format(
            data[0], username))

        self.log.info(
            "Step 3C:Verifying by logging in as csm monitor user {} with old password {}".format(username, self.csm_user.config["csm_user_monitor"]["password"]))
        payload_login = {"username": username, "password": old_password}
        response = self.csm_user.restapi.rest_call(request_type="post",
                                                   endpoint=self.csm_user.config["rest_login_endpoint"],
                                                   data=json.dumps(payload_login), headers=self.csm_user.config["Login_headers"])

        self.log.info("Verifying the status code {} returned".format(
            response.status_code))
        self.assertEqual(response.status_code, status_code)
        self.log.info("Verified login with old password was not successful!")

        self.log.info("Reverting old password")
        response = self.csm_user.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        self.assertEqual(response.status_code, self.csm_user.success_response)
        self.log.info("Verified response code 200 was returned")

        self.log.info(
            "Step 3: Verified that CSM monitor user should not be able to login with old password")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_1227(self):
        """
        Test that CSM user with role manager cannot perform any REST API request on IAM user
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Verifying CSM user with role manager cannot perform any REST API request on IAM user")

        self.log.info("Creating IAM user for test verification purpose")
        self.rest_iam_user = RestIamUser()
        new_iam_user = "testiam{}".format(int(time.time()))
        response = self.rest_iam_user.create_iam_user(
            user=new_iam_user, login_as="s3account_user")

        self.log.info(
            "Verifying IAM user {} creation was successful".format(new_iam_user))
        self.assertEqual(response.status_code,
                         self.csm_user.success_response)
        self.log.info(
            "Verified IAM user {} creation was successful".format(new_iam_user))

        self.log.info(
            "Step 1: Verifying CSM admin user cannot perform GET request on IAM user")
        response = self.rest_iam_user.list_iam_users(login_as="csm_admin_user")
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.info(
            "Step 1: Verified CSM admin user cannot perform GET request on IAM user")

        self.log.info(
            "Step 2: Verifying CSM manage user cannot perform GET request on IAM user")
        response = self.rest_iam_user.list_iam_users(
            login_as="csm_user_manage")
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.info(
            "Step 2: Verified CSM manage user cannot perform GET request on IAM user")

        self.log.info(
            "Step 3: Verifying CSM admin user cannot perform POST request on IAM user")
        new_iam_user1 = "testiam{}".format(int(time.time()))
        response = self.rest_iam_user.create_iam_user(
            user=new_iam_user1, login_as="csm_admin_user")
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.info(
            "Step 3: Verified CSM admin user cannot perform POST request on IAM user")

        self.log.info(
            "Step 4: Verifying CSM manage user cannot perform POST request on IAM user")
        new_iam_user2 = "testiam{}".format(int(time.time()))
        response = self.rest_iam_user.create_iam_user(
            user=new_iam_user2, login_as="csm_user_manage")
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.info(
            "Step 4: Verified CSM manage user cannot perform POST request on IAM user")

        self.log.info(
            "Step 5: Verifying CSM admin user cannot perform DELETE request on IAM user")
        response = self.rest_iam_user.delete_iam_user(
            user=new_iam_user, login_as="csm_admin_user")
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.info(
            "Step 5: Verified CSM admin user cannot perform DELETE request on IAM user")

        self.log.info(
            "Step 6: Verifying CSM manage user cannot perform DELETE request on IAM user")
        response = self.rest_iam_user.delete_iam_user(
            user=new_iam_user, login_as="csm_user_manage")
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.info(
            "Step 6: Verified CSM manage user cannot perform DELETE request on IAM user")

        self.log.info(
            "Verified CSM user with role manager cannot perform any REST API request on IAM user")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_1040(self):
        """
        Test that S3 account should not have access to create csm user from backend
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Verifying that S3 account does not have access to create csm user from backend")
        response = self.csm_user.create_csm_user(login_as="s3account_user")
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.info(
            "Verified that S3 account does not have access to create csm user from backend")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    def test_1172(self):
        """
        Test that the error messages related to the Log-in should not display any important information.
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Verifying that the error messages related to the Log-in does not display any important information.")

        self.rest_lib = RestTestLib()
        username = self.csm_conf["test_1172"]["username"]
        password = self.csm_conf["test_1172"]["password"]
        status_code = self.csm_conf["test_1172"]["status_code"]

        self.log.info("Step 1: Verifying with incorrect password")
        response = self.rest_lib.invalid_rest_login(
            username=self.csm_user.config["csm_admin_user"]["username"], password=password)
        self.log.info("Expected Response: {}".format(status_code))
        self.log.info("Actual Response: {}".format(response.status_code))
        self.assertEqual(response.status_code,
                         status_code, "Unexpected status code")
        self.log.info("Step 1: Verified with incorrect password")

        self.log.info("Step 2: Verifying with incorrect username")
        response = self.rest_lib.invalid_rest_login(
            username=username, password=self.csm_user.config["csm_admin_user"]["password"])
        self.log.info("Expected Response: {}".format(status_code))
        self.log.info("Actual Response: {}".format(response.status_code))
        self.assertEqual(response.status_code,
                         status_code, "Unexpected status code")
        self.log.info("Step 2: Verified with incorrect username")

        self.log.info(
            "Verified that the error messages related to the Log-in does not display any important information.")

        self.log.info("##### Test ended -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_7362(self):
        """
        Test that CSM user with monitor role cannot perform POST, PATCH and DELTE request on CSM user
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        password = self.csm_conf["test_7362"]["password"]

        self.log.info(
            "Step 1: Verifying that CSM user with monitor role cannot perform POST request to create new csm user")

        response = self.csm_user.create_csm_user(login_as="csm_user_monitor")
        self.log.debug("Verifying the response returned: {}".format(response))
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.info("Verified the response: {}".format(response))

        self.log.info(
            "Step 1: Verified that CSM user with monitor role cannot perform POST request to create new csm user")

        self.log.info(
            "Creating csm user for testing delete and patch requests")
        response = self.csm_user.create_csm_user()
        self.log.info(
            "Verifying if user was created successfully")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response_post)
        self.log.info(
            "Verified user was created successfully")
        userid = response.json()["id"]

        self.log.info(
            "Step 2: Verifying that CSM user with monitor role cannot perform DELETE request on a csm user")
        response = self.csm_user.list_csm_single_user(request_type="delete",
                                                      expect_status_code=self.csm_user.forbidden,
                                                      user=userid, return_actual_response=True, login_as="csm_user_monitor")
        self.log.debug("Verifying the response returned: {}".format(response))
        self.assertEqual(response.status_code, self.csm_user.forbidden)
        self.log.info("Verified the response: {}".format(response))

        self.log.info(
            "Step 2: Verified that CSM user with monitor role cannot perform DELETE request on a csm user")

        self.log.info(
            "Step 3: Verifying that CSM user with monitor role cannot perform PATCH request on a CSM user")

        self.log.info("Forming the payload")
        old_password = self.csm_user.config["csm_user_monitor"]["password"]
        payload = {"current_password": old_password, "password": password}

        response = self.csm_user.list_csm_single_user(request_type="patch",
                                                      expect_status_code=self.csm_user.forbidden,
                                                      user=userid, data=True, payload=json.dumps(payload), return_actual_response=True, login_as="csm_user_manage")
        self.log.debug("Verifying the response returned : {}".format(response))
        self.assertEqual(response.status_code, self.csm_user.forbidden)
        self.log.info("Verified the response: {}".format(response))

        self.log.info(
            "Step 3: Verified that CSM user with monitor role cannot perform PATCH request on a CSM user")

        self.log.info(
            "Verified that CSM user with monitor role cannot perform POST, PATCH and DELETE API request for CSM user")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_7361(self):
        """
        Test that CSM user with role manager cannot perform DELETE and PATCH API request on S3 Accounts
        :avocado: tags=rest_csm_user_test
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Verifying that CSM user with role manager cannot perform PATCH and DELETE API request on S3 Account")

        username = self.csm_user.config["s3account_user"]["username"]

        self.log.info(
            "Step 1: Verifying that root csm user cannot perform PATCH API request on S3 Account")
        response = self.s3_accounts.edit_s3_account_user(
            username=username, login_as="csm_admin_user")

        self.log.debug("Verifying response returned: {}".format(response))
        self.assertEqual(response.status_code, self.csm_user.forbidden)
        self.log.info("Verified the response: {}".format(response))

        self.log.info(
            "Step 1: Verified that root csm user cannot perform PATCH API request on S3 Account")

        self.log.info(
            "Step 2: Verifying that CSM user with role manager cannot perform PATCH API request on S3 Account")
        response = self.s3_accounts.edit_s3_account_user(
            username=username, login_as="csm_user_manage")

        self.log.debug("Verifying response returned: {}".format(response))
        self.assertEqual(response.status_code, self.csm_user.forbidden)
        self.log.info("Verified the response: {}".format(response))

        self.log.info(
            "Step 2: Verified that CSM user with role manager cannot perform PATCH API request on S3 Account")

        self.log.info(
            "Step 3: Verifying that root csm user cannot perform DELETE API request on S3 Account")
        response = self.s3_accounts. delete_s3_account_user(
            username=username, login_as="csm_admin_user")

        self.log.debug("Verifying response returned: {}".format(response))
        self.assertEqual(response.status_code, self.csm_user.forbidden)
        self.log.info("Verified the response: {}".format(response))

        self.log.info(
            "Step 3: Verified that root csm user cannot perform DELETE API request on S3 Account")

        self.log.info(
            "Step 4: Verifying that CSM user with role manager cannot perform DELETE API request on S3 Account")
        response = self.s3_accounts. delete_s3_account_user(
            username=username, login_as="csm_user_manage")

        self.log.debug("Verifying response returned : {}".format(response))
        self.assertEqual(response.status_code, self.csm_user.forbidden)
        self.log.info("Verified the response: {}".format(response))

        self.log.info(
            "Step 4: Verified that CSM user with role manager cannot perform DELETE API request on S3 Account")

        self.log.info(
            "Verified that CSM user with role manager cannot perform PATCH and DELETE API request on S3 Account")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))

    @ctp_fail_on(error_handler)
    def test_7360(self):
        """
        Test that CSM user with role manager cannot perform REST API request on S3 Buckets
        :avocado: tags=rest_csm_user_test_s3_bucket
        """
        test_case_name = sys._getframe().f_code.co_name
        self.log.info("##### Test started -  {} #####".format(test_case_name))

        self.log.info(
            "Verifying that CSM user with role manager cannot perform REST API request on S3 Buckets")
        self.log.info(
            "Creating valid bucket and valid bucket policy for test purpose")
        self.s3_buckets = RestS3Bucket()
        self.log.info("Creating bucket for test")
        response = self.s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="s3account_user")

        self.log.debug("Verifying S3 bucket was created successfully")
        self.assertEqual(response.status_code,
                         self.csm_user.success_response)
        self.log.debug("Verified S3 bucket {} was created successfully".format(
            response.json()['bucket_name']))
        bucket_name = response.json()['bucket_name']
        self.bucket_policy = RestS3BucketPolicy(bucket_name)

        self.log.info(
            "Step 1: Verifying that CSM user with role manager cannot perform GET REST API request on S3 Buckets")
        response = self.s3_buckets.list_all_created_buckets(
            login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: {} ".format(response))
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.debug("Verified the actual response returned: {} with the expected response".format(
            response.status_code, self.csm_user.forbidden))

        self.log.info(
            "Step 1: Verified that CSM user with role manager cannot perform GET REST API request on S3 Buckets")

        self.log.info(
            "Step 2: Verifying that CSM user with role manager cannot perform POST REST API request on S3 Buckets")
        response = self.s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: {} ".format(response))
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.debug("Verified the actual response returned: {} with the expected response".format(
            response.status_code, self.csm_user.forbidden))

        self.log.info(
            "Step 2: Verified that CSM user with role manager cannot perform POST REST API request on S3 Buckets")

        self.log.info(
            "Step 3: Verifying that CSM user with role manager cannot perform DELETE REST API request on S3 Buckets")
        response = self.s3_buckets.delete_s3_bucket(
            bucket_name=bucket_name, login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: {} ".format(response))
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.debug("Verified the actual response returned: {} with the expected response".format(
            response.status_code, self.csm_user.forbidden))

        self.log.info(
            "Step 3: Verified that CSM user with role manager cannot perform DELETE REST API request on S3 Buckets")

        self.log.info(
            "Step 4: Verifying that CSM manage user cannot perform PATCH bucket policy request for a S3 bucket")
        operation = "default"
        custom_policy_params = {}
        response = self.bucket_policy.create_bucket_policy(
            operation=operation, custom_policy_params=custom_policy_params, login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: {} ".format(response))
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.debug("Verified the actual response returned: {} with the expected response".format(
            response.status_code, self.csm_user.forbidden))

        self.log.info(
            "Step 5: Verifying that CSM user with role manager cannot perform GET bucket policy request for S3 Buckets")
        response = self.bucket_policy.get_bucket_policy(
            bucket_name=bucket_name, login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: {} ".format(response))
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.debug("Verified the actual response returned: {} with the expected response".format(
            response.status_code, self.csm_user.forbidden))

        self.log.info(
            "Step 5: Verifying that CSM user with role manager cannot perform GET bucket policy request for S3 Buckets")

        self.log.info(
            "Step 6: Verifying that CSM user with role manager cannot perform DELETE bucket policy request for S3 Buckets")
        response = self.bucket_policy.delete_bucket_policy(
            login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: {} ".format(response))
        self.assertEqual(response.status_code,
                         self.csm_user.forbidden)
        self.log.debug("Verified the actual response returned: {} with the expected response".format(
            response.status_code, self.csm_user.forbidden))

        self.log.info(
            "Step 6: Verified that CSM user with role manager cannot perform DELETE bucket policy request for S3 Buckets")

        self.log.info(
            "Verified that CSM user with role manager cannot perform REST API request on S3 Buckets")

        self.log.info(
            "##### Test completed -  {} #####".format(test_case_name))
