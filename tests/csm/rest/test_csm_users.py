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
"""Tests various operation on CSM user using REST API
"""
import time
import json
import logging
import pytest
from commons import configmanager
from commons.constants import Rest as const
from commons.utils import assert_utils, config_utils
from commons import cortxlogging
from libs.csm.rest.csm_rest_csmuser import RestCsmUser
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.csm.rest.csm_rest_bucket import RestS3Bucket
from libs.csm.rest.csm_rest_bucket import RestS3BucketPolicy
from libs.csm.csm_setup import CSMConfigsCheck

class TestCsmUser():
    """REST API Test cases for CSM users
    """
    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_csm_user.yaml")
        cls.config = CSMConfigsCheck()
        user_already_present = cls.config.check_predefined_csm_user_present()
        if not user_already_present:
            user_already_present = cls.config.setup_csm_users()
            assert user_already_present
        s3acc_already_present = cls.config.check_predefined_s3account_present()
        if not s3acc_already_present:
            s3acc_already_present = cls.config.setup_csm_s3()
        assert s3acc_already_present
        cls.csm_user = RestCsmUser()
        cls.s3_accounts = RestS3user()
        cls.log.info("Initiating Rest Client ...")

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10720')
    def test_4947(self):
        """Initiating the test case to verify List CSM user.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_user.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10721')
    def test_4948(self):
        """Initiating the test case to verify List CSM user with offset=<int>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_user.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS, offset=2)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10722')
    def test_4949(self):
        """Initiating the test case to verify List CSM user with offset=<string>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_user.list_csm_users(
            expect_status_code=const.BAD_REQUEST, offset='abc',
            verify_negative_scenario=True)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10723')
    def test_4950(self):
        """Initiating the test case to verify List CSM user with offset=<empty>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert(self.csm_user.list_csm_users(expect_status_code=const.BAD_REQUEST, offset='',
                                            verify_negative_scenario=True))
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10724')
    def test_4951(self):
        """Initiating the test case to verify List CSM user with limit=<int>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_user.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS, limit=2)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10725')
    def test_4952(self):
        """Initiating the test case to verify List CSM user with limit=<int>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_user.list_csm_users(
            expect_status_code=const.BAD_REQUEST,
            limit='abc',
            verify_negative_scenario=True)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10711')
    def test_4954(self):
        """Initiating the test case to create csm users and List CSM user with
        limit > created csm users.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_user.list_actual_num_of_csm_users()
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10726')
    def test_4955(self):
        """Initiating the test case to verify List CSM user with limit=<int>.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_user.list_csm_users(
            expect_status_code=const.BAD_REQUEST,
            limit='',
            verify_negative_scenario=True)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10727')
    def test_5001(self):
        """
        Test that GET API with invalid value for sort_by param returns 400 response code
        and appropriate error json data

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        invalid_sortby = self.csm_conf["test_5001"]["invalid_sortby"]
        resp_msg = self.csm_conf["test_5001"]["response_msg"]
        response = self.csm_user.list_csm_users(
            expect_status_code=const.BAD_REQUEST,
            sort_by=invalid_sortby,
            verify_negative_scenario=True)
        self.log.info("Response : %s", response)
        self.log.info("Verifying the response for invalid value for sort_by")
        assert response, "Status code check has failed check has failed."
        self.log.info("Verified the response for invalid value for sort_by")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10728')
    def test_5002(self):
        """
        Test that GET API with no value for sort_by param returns 400 response code

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp_msg = self.csm_conf["test_5002"]["response_msg"]

        self.log.info("Fetching csm user with empty sort by string...")
        response = self.csm_user.list_csm_users(
            expect_status_code=const.BAD_REQUEST,
            sort_by="",
            return_actual_response=True)

        self.log.info("Verifying error response...")
        assert response.json(), resp_msg

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17864')
    def test_5003(self):
        """
        Test that GET API with valid value for sort_dir param returns 200
        response code and appropriate json data

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        valid_sortdir = self.csm_conf["test_5003"]["valid_sortdir"]
        for sortdir in valid_sortdir:
            self.log.info("Sorting dir by :%s", sortdir)
            response_text = self.csm_user.list_csm_users(
                expect_status_code=const.SUCCESS_STATUS,
                sort_dir=sortdir,
                return_actual_response=True)
            self.log.info("Verifying the actual response...")
            response = self.csm_user.verify_list_csm_users(
                response_text.json(), sort_dir=sortdir)
            assert response
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10715')
    def test_5011(self):
        """Initiating the test case for the verifying CSM user creating.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert (self.csm_user.create_and_verify_csm_user_creation(
            user_type="valid",
            user_role="manage",
            expect_status_code=const.SUCCESS_STATUS_FOR_POST))
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10716')
    def test_5012(self):
        """Initiating the test case for the verifying response for invalid CSM user creating.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_user.create_and_verify_csm_user_creation(
            user_type="invalid", user_role="manage",
            expect_status_code=const.BAD_REQUEST)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10717')
    def test_5013(self):
        """Initiating the test case for the verifying response with missing
        mandatory argument for CSM user creating.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_user.create_and_verify_csm_user_creation(
            user_type="missing",
            user_role="manage",
            expect_status_code=const.BAD_REQUEST)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10718')
    def test_5014(self):
        """Initiating the test case for the verifying response unauthorized user
        trying to create csm user.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.csm_user.create_csm_user(login_as="s3account_user")
        assert response.status_code == const.FORBIDDEN
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10719')
    def test_5015(self):
        """Initiating the test case for the verifying response for duplicate CSM user creation.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_user.create_and_verify_csm_user_creation(
            user_type="duplicate",
            user_role="manage",
            expect_status_code=const.CONFLICT)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags('TEST-18802')
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    def test_5000(self):
        """
        Test that GET API with valid value for sort_by param returns 200 response code
        and appropriate json data

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        valid_sortby = self.csm_conf["test_5000"]["valid_sortby"]
        for sortby in valid_sortby:
            self.log.info("Sorting by :%s", sortby)
            response = self.csm_user.list_csm_users(
                expect_status_code=const.SUCCESS_STATUS,
                sort_by=sortby, return_actual_response=True)
            self.log.info("Verifying the actual response...")
            message_check = self.csm_user.verify_list_csm_users(
                response.json(), sort_by=sortby)
            assert message_check
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10730')
    def test_5004(self):
        """
        Test that GET API with invalid value for sort_dir param returns 400
        response code and appropriate error json data

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        invalid_sortdir = self.csm_conf["test_5004"]["invalid_sortdir"]
        self.log.info("Checking the sort dir option...")
        response = self.csm_user.list_csm_users(
            expect_status_code=const.BAD_REQUEST,
            sort_dir=invalid_sortdir, return_actual_response=True)
        self.log.info("Checking the error message text...")
        message_check = const.SORT_DIR_ERROR in response.json()[
            'message_id']
        assert message_check, response.json()
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10713')
    def test_5006(self):
        """Initiating the test case to verify list CSM user with valid offset,
        limit,sort_by and sort_dir parameters provided.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.csm_user.verify_csm_user_list_valid_params()
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10714')
    def test_5008(self):
        """Initiating the test case to verify that 403 is returned by csm list
        users api for unauthorised access

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info(
            "Verifying csm list users api unauthorised access for s3 user")
        assert self.csm_user.verify_list_csm_users_unauthorised_access_failure(
            login_as="s3account_user")
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)
    
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10712')
    def test_5005(self):
        """
        Test that GET API with empty value for sort_dir param returns 400 response code
        and appropriate error json data

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        resp_msg = self.csm_conf["test_5005"]["response_msg"]

        self.log.info(
            "Fetching the response for empty sort_by parameter with the expected status code")
        response = self.csm_user.list_csm_users_empty_param(
            expect_status_code=const.BAD_REQUEST,
            csm_list_user_param="dir",
            return_actual_response=True)

        self.log.info("Verifying the error response returned status code: %s, response : %s",
                      response.status_code, response.json())
        assert response.json() == resp_msg
        self.log.info(
            "Verified that the returned error response is as expected: %s", response.json())
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-10795')
    def test_5009(self):
        """
        Test that GET API returns 200 response code and appropriate json data
        for valid username input.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info("Step 1: Creating a valid csm user")
        response = self.csm_user.create_csm_user(
            user_type="valid", user_role="manage")
        self.log.info("Verifying that user was successfully created")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST

        self.log.info("Reading the username")
        username = response.json()["username"]

        self.log.info(
            "Step 2: Sending the request to user %s", username)
        response = self.csm_user.list_csm_single_user(
            request_type="get",
            expect_status_code=const.SUCCESS_STATUS,
            user=username,
            return_actual_response=True)
        self.log.info("Verifying the status code returned")
        assert const.SUCCESS_STATUS == response.status_code
        actual_response = response.json()

        self.log.info(
            "Step 3: Fetching list of all users")
        response = self.csm_user.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS, return_actual_response=True)
        self.log.info(
            "Verifying that response to fetch all users was successful")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.info(
            "Step 4: Fetching the user %s information from the list", username)
        expected_response = []
        for item in response.json()["users"]:
            if item["username"] == username:
                expected_response = item
                break
        self.log.info("Verifying the actual response %s is matching the expected response %s",
                      actual_response, expected_response)
        assert config_utils.verify_json_response(
            actual_result=actual_response,
            expect_result=expected_response,
            match_exact=True)
        self.log.info(
            "Verified that the status code is 200 and response is as expected: %s", actual_response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10797')
    def test_5016(self):
        """
        Test that PATCH API returns 200 response code and appropriate json data
        for valid payload data.

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        # Test Purpose 1: Verifying root user can modify manage role user
        self.log.info("Test Purpose 1: Verifying that csm root user can "
                      "modify role and password of csm manage role user")

        user = self.csm_conf["test_5016"]["user"]
        self.log.info(
            "Test Purpose 1: Step 1: Creating csm manage user : %s", user)
        response = self.csm_user.create_csm_user(
            user_type=user[0], user_role=user[1])
        self.log.info(
            "Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info("User %s got created successfully", username)

        self.log.info("Test Purpose 1: Step 2: Login as csm root user and "
                      "change password and role of user %s", username)
        data = self.csm_conf["test_5016"]["payload_monitor"]
        self.log.info("Forming the payload")
        payload = {"role": data["role"], "password": data["password"]}
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info("Verifying if the password %s and role %s was updated "
                      "successfully for csm user %s",
                      data["password"], data["role"], username)
        self.log.info("Logging in as user %s", username)
        payload_login = {"username": username, "password": data["password"]}
        response = self.csm_user.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert response.status_code == const.SUCCESS_STATUS
        assert response.json()["role"] == user[2]

        self.log.info("Test Purpose 1: Verified status code %s was returned "
                      "along with response %s",
                      response.status_code, response.json())
        self.log.info("Test Purpose 2: Verified that the password %s "
                      "and role %s was updated successfully for csm user %s",
                      payload["password"], response.json()["role"], username)

        # Test Purpose 2: Verifying root user can modify monitor role user
        self.log.info(
            "Test Purpose 2: Verifying that csm root user can modify role and "
            "password of csm monitor role user")
        self.log.info("Test Purpose 2: Step 1: Creating csm monitor user")
        response = self.csm_user.create_csm_user(
            user_type=user[0], user_role=user[2])
        self.log.info(
            "Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info("User %s got created successfully", username)

        self.log.info(
            "Test Purpose 2 : Step 2: Login as csm root user and change "
            "password and role of user %s", username)
        data = self.csm_conf["test_5016"]["payload_manage"]
        payload = {"role": data["role"], "password": data["password"]}
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info("Verifying if the password %s and role %s was updated "
                      "successfully for csm user %s",
                      payload["password"], payload["role"], username)
        self.log.info("Logging in as user %s", username)
        payload_login = {"username": username, "password": payload["password"]}
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert response.status_code == const.SUCCESS_STATUS
        assert response.json()["role"] == user[1]

        self.log.info("Test Purpose 2: Verified status code %s was returned "
                      "along with response %s", response.status_code,
                      response.json())
        self.log.info("Test Purpose 2: Verified that the password %s and "
                      "role %s was updated successfully for csm user %s",
                      payload["password"], response.json()["role"], username)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12023')
    def test_1228(self):
        """
        Test that CSM user with role manager can perform GET and POST API request on S3 Accounts

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose 1: Verifying that csm manage user can perform "
            "POST api request on S3 account")

        self.log.info(
            "Test Purpose 1: Step 1: Logging in as csm user and creating s3 account")
        response = self.s3_accounts.create_s3_account(
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS

        s3_account_name = response.json()["account_name"]

        self.log.info("Verified status code %s was returned along with "
                      "response %s for s3 account %s creation",
                      response.status_code, response.json(), s3_account_name)
        self.log.info(
            "Test Purpose 1: Verified that csm manage user was able to create s3 account")

        self.log.info(
            "Test Purpose 1: Verified that csm manage user can perform POST "
            "api request on S3 account")

        self.log.info(
            "Test Purpose 2: Step 1: Logging in as csm user to get the "
            "details of the s3 account")
        response = self.s3_accounts.list_all_created_s3account(
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        s3_accounts = [item["account_name"]
                       for item in response.json()["s3_accounts"]]
        self.log.info(s3_accounts)
        assert s3_account_name in s3_accounts
        self.log.info("Verified status code %s was returned for getting "
                      "account %s details  along with response %s",
                      response.status_code, s3_account_name, response.json())
        self.log.info(
            "Test Purpose 2: Verified that csm manage user was able to "
            "get the details of s3 account")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12022')
    def test_1237(self):
        """
        Test that CSM user with monitor role can perform GET API request for CSM user

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose: Verifying that CSM user with monitor role can "
            "perform GET API request for CSM user")

        self.log.info("Step 1: Creating csm user")
        response = self.csm_user.create_csm_user()
        self.log.info(
            "Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info(
            "Step 2: Verified User %s got created successfully", username)

        self.log.info(
            "Step 3: Login as csm monitor user and perform get "
            "request on csm user %s", username)
        response = self.csm_user.list_csm_single_user(
            request_type="get",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            return_actual_response=True,
            login_as="csm_user_monitor")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.info(
            "Verifying that get request was successful for csm user %s", username)
        assert username in response.json()["username"]

        self.log.info("Verified that status code %s was returned along "
                      "with response: %s for the get request for csm "
                      "user %s", response.status_code,
                      response.json(), username)
        self.log.info(
            "Step 4: Verified that CSM user with monitor role successfully "
            "performed GET API request for CSM user")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12021')
    def test_1235(self):
        """
        Test that CSM user with role monitor can perform GET API request for S3 Accounts

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose: Verifying that csm monitor user can perform "
            "GET api request on S3 accounts")

        self.log.info(
            "Step 1: Creating s3 account")
        response = self.s3_accounts.create_s3_account()
        self.log.info("Verifying s3 account was successfully created")
        assert response.status_code == const.SUCCESS_STATUS
        s3_account_name = response.json()["account_name"]
        self.log.info(
            "Step 2: Verified s3 account %s was successfully created ", s3_account_name)

        self.log.info(
            "Step 3: Logging in as csm monitor user to get the details of the s3 accounts")
        response = self.s3_accounts.list_all_created_s3account(
            login_as="csm_user_monitor")
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS
        s3_accounts = [item["account_name"]
                       for item in response.json()["s3_accounts"]]
        self.log.info(s3_accounts)
        assert s3_account_name in s3_accounts
        self.log.info("Verified status code %s was returned for getting "
                      "account %s details  along with response %s",
                      response.status_code, s3_account_name, response.json())
        self.log.info(
            "Step 4: Verified that csm monitor user was able to get the details "
            "of s3 accounts using GET api")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)


    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-12018')
    def test_7421(self):
        """
        Test Non root user should able to change its password by specifying
        old_password and new password

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose: Verifying non root user should able to change its "
            "password by specifying old_password and new password ")

        data = self.csm_conf["test_7421"]["data"]
        username = self.csm_user.config["csm_user_manage"]["username"]
        self.log.info(
            "Step 1: Login as csm non root user and change password and role of"
            " user without providing old password %s", username)
        self.log.info(
            "Forming the payload specifying old password for csm manage user")
        old_password = self.csm_user.config["csm_user_manage"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username, data=True, payload=json.dumps(payload_user),
            return_actual_response=True, login_as="csm_user_manage")

        self.log.info("Verifying response code %s and response %s  returned",
                      response.status_code, response.json())
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info("Verifying if the password %s was updated successfully for csm user %s",
                      data[0], username)
        self.log.info(
            "Logging in as user %s with new password %s", username, data[0])
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_user.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info("Verified login with new password was successful with "
                      "status code %s and response %s",
                      response.status_code, response.json())
        self.log.info("Verified that the password %s was updated successfully"
                      " for %s csm user %s",
                      data[0], response.json()["role"], username)

        self.log.info("Reverting old password for user %s", username)
        payload_user = {"password": old_password}
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username,
            data=True,
            payload=json.dumps(payload_user),
            return_actual_response=True)

        self.log.info("Verifying response code %s and response returned %s",
                      response.status_code, response.json())
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-12024')
    def test_7411(self):
        """
        Test that root user should able to modify self password through CSM-REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose: Verifying Test that root user should able "
            "to modify self password using PATCH request ")

        data = self.csm_conf["test_7411"]["data"]
        username = self.csm_user.config["csm_admin_user"]["username"]

        self.log.info(
            "Step 1: Login as csm root user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm root user")
        old_password = self.csm_user.config["csm_admin_user"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username,
            data=True,
            payload=json.dumps(payload_user),
            return_actual_response=True,
            login_as="csm_admin_user")
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verifying if the password %s was updated "
                      "successfully for csm user %s",
                      data[0], username)

        self.log.info(
            "Step 2:Logging in as csm root user %s with new "
            "password %s", username, data[0])
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_user.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verified login with new password was successful with "
                      "status code %s and response %s",
                      response.status_code, response.json())
        self.log.info("Verified that the password %s was updated successfully"
                      " for csm root user %s",
                      data[0], username)

        self.log.info("Reverting the password...")
        response = self.csm_user.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info(
            "Verifying password was reverted and response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-12025')
    def test_1229(self):
        """
        Test that CSM user with manage role can perform GET, POST, PATCH and
        DELETE API request for CSM user

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_1229"]["data"]
        self.log.info("Test Purpose 1: Verifying that CSM user with manage role "
                      "can perform POST request and create a new csm user")
        self.log.info(
            "Test Purpose 1: Step 1: CSM manage user performing POST request")
        response = self.csm_user.create_csm_user(
            user_type=data[0], user_role=data[1], login_as="csm_user_manage")
        self.log.info(
            "Verifying if user was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS_FOR_POST)

        username = response.json()["username"]
        userid = response.json()["id"]
        actual_response = response.json()
        self.log.info(
            "Fetching list of all users")
        response1 = self.csm_user.list_csm_users(
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(response1.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info(
            "Fetching the user %s information from the list", username)
        expected_response = []
        for item in response1.json()["users"]:
            if item["username"] == username:
                expected_response = item
                break
        self.log.info("Verifying the actual response %s is matching the "
                      "expected response %s", actual_response, expected_response)
        assert (config_utils.verify_json_response(
            actual_result=actual_response,
            expect_result=expected_response,
            match_exact=True))
        self.log.info("User %s got created successfully", username)
        self.log.info("Status code %s was returned along with response: %s "
                      "for the POST request for csm user %s",
                      response.status_code,
                      response.json(), username)
        self.log.info(
            "Test Purpose 1: Verified that CSM user with manage role can "
            "perform POST request and create a new csm user")

        self.log.info(
            "Test Purpose 2: Verifying that that CSM user with manage role "
            "can perform GET request for CSM user")
        self.log.info(
            "Test Purpose 2: Step 1: CSM manage user performing GET request")
        response = self.csm_user.list_csm_single_user(
            request_type="get",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            return_actual_response=True,
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info(
            "Verifying that get request was successful for csm user %s", username)
        assert username in response.json()["username"]
        self.log.info("Status code %s was returned along with response: %s "
                      "for the GET request for csm user %s",
                      response.status_code, response.json(), username)
        self.log.info("Test Purpose 2: Verified that CSM user with manage role can "
                      "perform GET request for CSM user")

        self.log.info("Test Purpose 3: Verifying that that CSM user with manage "
                      " role can perform DELETE itself")
        response = self.csm_user.list_csm_single_user(
            request_type="delete",
            expect_status_code=const.SUCCESS_STATUS,
            user="csm_user_manage",
            return_actual_response=True,
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Status code %s was returned along with response %s for "
                      "Delete request", response.status_code, response.json())
        self.log.info("Test Purpose 3: Verified that CSM user with manage role can "
                      "perform DELETE request for CSM user")

        self.log.info(
            "Test Purpose 4: Verifying that that CSM user with manage role can"
            " perform PATCH request for itself")
        self.log.info(
            "Test Purpose 4: Step 1: Create csm manage user")
        response = self.csm_user.create_csm_user(
            user_type="pre-define", user_role="manage")
        self.log.info(
            "Verifying if user was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS_FOR_POST)
        self.log.info("User %s got created successfully", username)
        username = response.json()["username"]
        userid = response.json()["id"]

        self.log.info("Test Purpose 4: Step 2: Login as csm manage user and "
                      "modify its own password using Patch request")
        self.log.info("Forming the payload")
        old_password = self.csm_user.config["csm_user_manage"]["password"]
        payload = {"current_password": old_password, "password": data[3]}

        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user="csm_user_manage",
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_manage")
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verifying if the password %s was updated successfully for csm user %s",
                      data[3], username)
        self.log.info("Logging in as user %s", username)
        payload_login = {"username": username, "password": data[3]}
        response = self.csm_user.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Status code %s was returned along with response %s for "
                      "Patch request", response.status_code, response.json())
        self.log.info("Test Purpose 4: Verified that CSM user with manage role "
                      "can perform PATCH request for itself")

        self.log.info(
            "Reverting the password of pre-configured user csm_user_manage")

        payload = {"current_password": data[3], "password": old_password}
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user="csm_user_manage",
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_admin_user")
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info(
            "Verified that CSM user with manage role can perform GET, POST, "
            "PATCH and DELETE API request for CSM user")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-12026')
    def test_5019(self):
        """
        Test that PATCH API returns 200 response code and appropriate json data
        for partial payload.

        """

        # Test Purpose 1: Verifying root user can change the role of csm manage
        #  user partially without changing the password
        self.log.info("Test Purpose 1: Verifying that csm root user can partially "
                      "modify csm manage user by modifying only the user's role")

        user = self.csm_conf["test_5019"]["user"]
        payload_login = self.csm_conf["test_5019"]["payload_login"]
        self.log.info("Test Purpose 1: Step 1: Creating csm manage user")
        response = self.csm_user.create_csm_user(
            user_type=user[0], user_role=user[1])
        self.log.info(
            "Verifying if user was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS_FOR_POST)
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info("User %s got created successfully", username)

        self.log.info("Test Purpose 1: Step 2: Login as csm root user and change"
                      " only the role of user %s", username)
        self.log.info("Forming the payload")
        payload = {"role": user[2]}

        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verifying if the role %s was updated successfully for csm user %s",
                      user[2], username)

        userdata = json.loads(const.USER_DATA)
        self.log.info("Logging in as user %s", username)

        payload_login["username"] = username
        payload_login["password"] = userdata["password"]

        response = self.csm_user.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        assert_utils.assert_equals(response.json()["role"], user[2])

        self.log.info("Test Purpose 1: Verified status code %s was returned "
                      "along with response %s", response.status_code, response.json())

        self.log.info("Test Purpose 1: Verified that the role %s was updated successfully "
                      "for csm user %s", response.json()["role"], username)

        # Test Purpose 2: Verifying root user can change the password of csm manage
        # user partially without changing the role
        self.log.info("Test Purpose 2: Verifying that csm root user can partially modify "
                      "csm manage user by modifying only the user's password")

        self.log.info("Test Purpose 2: Step 1: Login as csm root user and change "
                      "only the password of user %s", username)

        self.log.info("Forming the payload")
        payload = {"password": user[3]}

        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verifying if the password %s was updated successfully "
                      "for csm user %s", user[3], username)

        self.log.info(
            "Logging in as user %s with the changed password %s", username, user[3])

        payload_login["username"] = username
        payload_login["password"] = user[3]
        response = self.csm_user.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Test Purpose 2: Verified status code %s was returned along "
                      "with response %s", response.status_code, response.json())

        self.log.info("Test Purpose 2: Verified that the password %s was updated "
                      "successfully for csm user %s", user[3], username)

        # Test Purpose 3: Verifying root user can change the role of csm monitor user
        # partially without changing the password
        self.log.info("Test Purpose 3: Verifying that csm root user can partially "
                      "modify csm monitor user by modifying only the user's role")

        self.log.info("Test Purpose 3: Step 1: Creating csm monitor user")
        response = self.csm_user.create_csm_user(
            user_type=user[0], user_role=user[2])
        self.log.info(
            "Verifying if user was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS_FOR_POST)
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info("User %s got created successfully", username)

        self.log.info("Test Purpose 3: Step 2: Login as csm root user and change "
                      "only the role of user %s", username)

        self.log.info("Forming the payload")
        payload = {"role": user[1]}

        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verifying if the role %s was updated successfully for csm user %s",
                      user[2], username)

        self.log.info("Logging in as user %s", username)

        payload_login["username"] = username
        payload_login["password"] = userdata["password"]
        response = self.csm_user.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        assert_utils.assert_equals(response.json()["role"], user[1])

        self.log.info("Test Purpose 3: Verified status code %s was returned along "
                      "with response %s", response.status_code, response.json())

        self.log.info("Test Purpose 3: Verified that the role %s was updated successfully"
                      " for csm user %s", response.json()["role"], username)

        # Test Purpose 4: Verifying root user can change the password of csm
        # monitor user partially without changing the role
        self.log.info("Test Purpose 4: Verifying that csm root user can partially "
                      "modify csm monitor user by modifying only the user's password")

        self.log.info("Test Purpose 4: Step 1: Login as csm root user and change "
                      "only the password of user %s", username)
        self.log.info("Forming the payload")
        payload = {"password": user[3], "confirmPassword": user[3]}

        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verifying if the password %s was updated successfully "
                      "for csm user %s", user[3], username)

        self.log.info("Logging in as user %s with the changed password %s",
                      username, user[3])

        payload_login["username"] = username
        payload_login["password"] = user[3]

        response = self.csm_user.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Test Purpose 4: Verified status code %s was returned "
                      "along with response %s", response.status_code, response.json())

        self.log.info("Test Purpose 4: Verified that the password %s was "
                      "updated successfully for csm user %s", user[3], username)

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12838')
    def test_7422(self):
        """
        Test that Non root user cannot change roles through CSM-REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Step 1: Verifying that csm manage user cannot modify its role")

        username = self.csm_user.config["csm_user_manage"]["username"]
        expected_response_manage = self.csm_conf["test_7422"]["response_manage"]
        expected_response_manage["error_format_args"] = username

        self.log.info(
            "Creating payload for the Patch request")
        payload = self.csm_conf["test_7422"]["payload_manage"]
        payload["current_password"] = self.csm_user.config["csm_user_manage"]["password"]
        self.log.info("Payload for the patch request is %s", payload)

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_manage")

        self.log.info(
            "Verifying response returned for user %s", username)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        assert_utils.assert_equals(response.json(), expected_response_manage)
        self.log.info("Step 1: Verified that csm manage user cannot modify its "
                      "role and response returned is %s", response)

        self.log.info(
            "Step 2: Verifying that csm monitor user cannot modify its role")

        username = self.csm_user.config["csm_user_monitor"]["username"]

        self.log.info("Creating payload for the Patch request")
        payload = self.csm_conf["test_7422"]["payload_monitor"]
        payload["current_password"] = self.csm_user.config["csm_user_monitor"]["password"]
        self.log.info("Payload for the patch request is %s", payload)

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_monitor")

        self.log.info(
            "Verifying response returned for user %s", username)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 2: Verified that csm monitor user cannot modify its role and "
            "response returned is %s", response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)
    
    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12839')
    def test_7412(self):
        """
        Test that user should not able to change roles for root user through
        CSM-REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        username = self.csm_user.config["csm_admin_user"]["username"]
        expected_response_admin = self.csm_conf["test_7412"]["response_admin"]
        expected_response_admin["error_format_args"] = username

        self.log.info(
            "Step 1: Verifying that csm admin user should not be able to modify"
            " its own role")

        self.log.info(
            "Creating payload with for the Patch request")
        payload = self.csm_conf["test_7412"]["payload_admin"]
        payload["current_password"] = self.csm_user.config["csm_admin_user"]["password"]
        self.log.info("Payload for the patch request is %s", payload)

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_admin_user")

        self.log.info("Verifying response returned")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        assert_utils.assert_equals(response.json(), expected_response_admin)

        self.log.info(
            "Step 1: Verified that csm admin user is not be able to modify its "
            "own role and response returned is %s", response)

        self.log.info(
            "Step 2: Verifying that csm manage user should not be able to modify "
            "csm admin user role")

        self.log.info(
            "Creating payload with for the Patch request")
        payload = self.csm_conf["test_7412"]["payload"]
        self.log.info("Payload for the patch request is %s", payload)

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_manage")

        self.log.info("Verifying response returned")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 2: Verified that csm manage user is not be able to modify "
            "csm admin user role and response returned is %s", response)

        self.log.info(
            "Step 3: Verifying that csm monitor user should not be able to"
            " modify csm admin user role")

        self.log.info(
            "Creating payload with for the Patch request")
        payload = self.csm_conf["test_7412"]["payload"]
        self.log.info("Payload for the patch request is %s", payload)

        self.log.info("Sending the Patch request to change the role")
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_monitor")

        self.log.info("Verifying response returned")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 3: Verified that csm monitor user is not be able to modify "
            "csm admin user role and response returned is %s", response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-12840')
    def test_7408(self):
        """
        Test that user should not be able to change its username through CSM-REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        payload = self.csm_conf["test_7408"]["payload"]
        resp_msg = self.csm_conf["test_7408"]["response_mesg"]

        self.log.info(
            "Step 1: Verifying that csm monitor user should not be able to "
            "modify its username")

        username = self.csm_user.config["csm_user_monitor"]["username"]

        self.log.info(
            "Creating payload for the Patch request")
        payload["current_password"] = self.csm_user.config["csm_user_monitor"]["password"]
        self.log.info("Payload for the patch request is: %s", payload)

        self.log.info("Sending the patch request for csm monitor user...")
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_monitor")
        self.log.info(
            "Verifying response returned for user %s", username)
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        assert_utils.assert_equals(response.json(),
                                   resp_msg)

        self.log.info(
            "Step 1: Verified that csm monitor user %s is not able to modify "
            "its username and response returned is %s", username, response)

        self.log.info(
            "Step 2: Verifying that csm manage user should not be able to "
            "modify its username")
        username = self.csm_user.config["csm_user_manage"]["username"]

        self.log.info(
            "Creating payload for the Patch request")
        payload["current_password"] = self.csm_user.config["csm_user_manage"]["password"]
        self.log.info("Payload for the patch request is: %s", payload)

        self.log.info("Sending the patch request for csm manage user...")
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_manage")
        self.log.info(
            "Verifying response returned for user %s", username)
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        assert_utils.assert_equals(response.json(), resp_msg)
        self.log.info(
            "Step 2: Verified that csm manage user %s is not be able to modify "
            "its username and response returned is %s", username, response)

        self.log.info(
            "Step 3: Verifying that csm admin user should not be able to modify"
            " its username")
        username = self.csm_user.config["csm_admin_user"]["username"]

        self.log.info(
            "Creating payload for the Patch request")
        payload["current_password"] = self.csm_user.config["csm_admin_user"]["password"]
        self.log.info("Payload for the patch request is: %s", payload)

        self.log.info("Sending the patch request for csm admin user...")
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user=username,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_admin_user")
        self.log.info(
            "Verifying response returned for user %s", username)
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        assert_utils.assert_equals(response.json(), resp_msg)

        self.log.info(
            "Step 3: Verified that csm admin user %s is not be able to modify "
            "its username and response returned is %s", username, response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-17865')
    def test_6220(self):
        """
        Test that duplicate users should not be created between csm users and
        s3 account users in CSM REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_6220"]
        self.log.info(
            "Step 1: Verifying that csm admin user should not be able to create"
            " duplicate csm user")

        username = self.csm_user.config["csm_user_manage"]["username"]
        mesg = data["response_duplicate_csm_manage_user"]["message"]
        data["response_duplicate_csm_manage_user"]["message"] = f"{mesg} {username}"

        self.log.info(
            "Logging in as csm admin user to create duplicate csm user %s",
            username)
        response = self.csm_user.create_csm_user(
            user_type="pre-define",
            user_role="manage",
            login_as="csm_admin_user")

        self.log.info("Verifying response code: %s and response returned: %s",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.status_code, const.CONFLICT)
        assert_utils.assert_equals(
            response.json(), data["response_duplicate_csm_manage_user"])
        self.log.info("Verified response returned")

        self.log.info(
            "Step 1: Verified that csm admin user is not able to create "
            "duplicate csm user")

        self.log.info(
            "Step 2: Verifying that csm manage user should not be able to "
            "create duplicate csm user")

        username = self.csm_user.config["csm_user_monitor"]["username"]
        mesg = data["response_duplicate_csm_monitor_user"]["message"]
        data["response_duplicate_csm_monitor_user"]["message"] = f"{mesg} {username}"

        self.log.info(
            "Logging in as csm manage user to create duplicate csm user %s", username)

        response = self.csm_user.create_csm_user(
            user_type="pre-define",
            user_role="monitor",
            login_as="csm_user_manage")

        self.log.info("Verifying response code: %s and response returned: %s",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.status_code, const.CONFLICT)
        assert_utils.assert_equals(
            response.json(), data["response_duplicate_csm_monitor_user"])

        self.log.info("Verified response returned")

        self.log.info(
            "Step 2: Verified that csm manage user is not able to create duplicate csm user")

        s3account = self.csm_user.config["s3account_user"]["username"]
        data["response_duplicate_s3_account"]["error_format_args"]["account_name"] = s3account

        self.log.info(
            "Step 3: Verifying that csm admin user should not be able to create"
            " duplicate s3 account")

        self.log.info(
            "Logging in as csm admin user to create duplicate s3 account %s", s3account)
        response = self.s3_accounts.create_s3_account(
            user_type="pre-define", login_as="csm_admin_user")

        self.log.info("Verifying response")
        assert_utils.assert_equals(response.status_code, const.CONFLICT)
        assert_utils.assert_equals(
            response.json(), data["response_duplicate_s3_account"])
        self.log.info("Verified response returned is: %s, %s",
                      response, response.json())

        self.log.info(
            "Step 3: Verified that csm admin user is not able to create "
            "duplicate s3 account")

        self.log.info(
            "Step 4: Verifying that csm manage user should not be able to "
            "create duplicate s3 account")

        self.log.info(
            "Logging in as csm manage user to create duplicate s3 account %s",
            s3account)
        response = self.s3_accounts.create_s3_account(
            user_type="pre-define", login_as="csm_user_manage")

        self.log.info("Verifying response")
        assert_utils.assert_equals(response.status_code, const.CONFLICT)
        assert_utils.assert_equals(
            response.json(), data["response_duplicate_s3_account"])
        self.log.info("Verified response returned is: %s, %s",
                      response, response.json())

        self.log.info(
            "Step 4: Verified that csm manage user is not able to create "
            "duplicate s3 account")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14657')
    def test_5021(self):
        """
        Test that DELETE API with default argument returns 200 response code
        and appropriate json data.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Step 1: Verifying that DELETE API with default argument returns 200 "
            "response code and appropriate json data")

        message = self.csm_conf["test_5021"]["response_message"]

        self.log.info("Creating csm user")
        response = self.csm_user.create_csm_user()

        self.log.info("Verifying that user was successfully created")
        assert (response.status_code ==
                const.SUCCESS_STATUS_FOR_POST)

        self.log.info("Reading the username")
        username = response.json()["username"]

        self.log.info(
            "Sending request to delete csm user %s", username)
        response = self.csm_user.list_csm_single_user(
            request_type="delete",
            expect_status_code=const.SUCCESS_STATUS,
            user=username, return_actual_response=True)

        self.log.info("Verifying response returned")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info("Verified success status %s is returned",
                      response.status_code)

        self.log.info("Verifying proper message is returned")
        assert_utils.assert_equals(response.json(),
                                   message)
        self.log.info(
            "Verified message returned is: %s", response.json())

        self.log.info(
            "Step 1: Verified that DELETE API with default argument returns 200"
            " response code and appropriate json data")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14658')
    def test_5023(self):
        """
        Test that DELETE API returns 403 response for unauthorized request.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Step 1: Verifying that DELETE API returns 403 response for "
            "unauthorized request")

        self.log.info(
            "Sending request to delete csm user with s3 authentication")
        response = self.csm_user.list_csm_single_user(
            request_type="delete",
            expect_status_code=const.FORBIDDEN,
            user="csm_user_manage",
            return_actual_response=True,
            login_as="s3account_user")

        self.log.info("Verifying response returned")

        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)

        self.log.info(
            "Step 1: Verified that DELETE API returns 403 response for "
            "unauthorized request : %s", response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14659')
    def test_5020(self):
        """
        Test that PATCH API returns 400 response code and appropriate json
        data for empty payload.

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_5020"]
        payload = {}
        self.log.info(
            "Step 1: Verifying that PATCH API returns 400 response code and "
            "appropriate json data for empty payload")

        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user="csm_user_manage",
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True)

        self.log.info("Verifying the status code returned : %s",
                      response.status_code)
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        self.log.info("Verified the status code returned")

        self.log.info(
            "Verifying the response message returned : %s", response.json())
        assert_utils.assert_equals(response.json(), data["response_msg"])
        self.log.info(
            "Verified the response message returned")

        self.log.info(
            "Step 1: Verified that PATCH API returns 400 response code and "
            "appropriate json data for empty payload")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14660')
    def test_5017(self):
        """
        Test that PATCH API returns 404 response code and appropriate json data
        for user that does not exist.

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_5017"]
        mesg = data["response_msg"]["message"]
        userid = data["invalid_user_id"]
        data["response_msg"]["message"] = f"{mesg} {userid}"

        self.log.info(
            "Step 1: Verifying that PATCH API returns 404 response code and "
            "appropriate json data for user that does not exist")

        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.METHOD_NOT_FOUND,
            user=userid,
            data=True,
            payload=json.dumps(data["payload"]),
            return_actual_response=True)

        self.log.info("Verifying the status code returned : %s",
                      response.status_code)
        assert_utils.assert_equals(response.status_code,
                                   const.METHOD_NOT_FOUND)
        self.log.info("Verified the status code returned")

        self.log.info(
            "Verifying the response message returned : %s", response.json())
        assert_utils.assert_equals(response.json(), data["response_msg"])
        self.log.info(
            "Verified the response message returned")

        self.log.info(
            "Step 1: Verified that PATCH API returns 404 response code and "
            "appropriate json data for user does not exist")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14661')
    def test_5010(self):
        """
        Test that GET API returns 404 response code and appropriate json data
        for non-existing username input.

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_5010"]
        mesg = data["response_msg"]["message"]
        userid = data["invalid_user_id"]
        data["response_msg"]["message"] = f"{mesg} {userid}"

        self.log.info(
            "Step 1: Verifying that GET API returns 404 response code and appropriate "
            "json data for non-existing username input")

        response = self.csm_user.list_csm_single_user(
            request_type="get",
            expect_status_code=const.METHOD_NOT_FOUND,
            user=userid,
            return_actual_response=True)

        self.log.info("Verifying the status code returned : %s",
                      response.status_code)
        assert_utils.assert_equals(response.status_code,
                                   const.METHOD_NOT_FOUND)
        self.log.info("Verified the status code returned")

        self.log.info(
            "Verifying the response message returned : %s", response.json())
        assert_utils.assert_equals(response.json(), data["response_msg"])
        self.log.info(
            "Verified the response message returned")

        self.log.info(
            "Step 1: Verified that GET API returns 404 response code and "
            "appropriate json data for non-existing(invalid) username input")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-14696')
    def test_5018(self):
        """
        Test that PATCH API returns 400 response code and appropriate error json
        data for invalid payload.

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_5018"]

        self.log.info(
            "Step 1: Verifying that PATCH API returns 400 response code and "
            "appropriate error json data for invalid password")

        for i in range(1, data["range"][0]):
            self.log.info("Verifying for invalid password: %s",
                          data[f'payload_invalid_password_{str(i)}'])
            response = self.csm_user.list_csm_single_user(
                request_type="patch",
                expect_status_code=const.BAD_REQUEST,
                user="csm_user_manage",
                data=True,
                payload=json.dumps(data[f'payload_invalid_password_{str(i)}']),
                return_actual_response=True)

            self.log.info("Verifying the returned status code: %s and response:"
                          " %s ", response.status_code, response.json())
            assert response.status_code == const.BAD_REQUEST, "Response code mismatch."
            print(i)
            assert_utils.assert_equals(
                response.json(), data[f'invalid_password_resp_{str(i)}'], "Error message mismatch.")

        self.log.info(
            "Step 1: Verified that PATCH API returns 400 response code and "
            "appropriate error json data for invalid password")

        self.log.info(
            "Step 2: Verifying that PATCH API returns 400 response code and "
            "appropriate error json data for invalid role")

        self.log.info("Verifying for invalid role: %s",
                      data["invalid_role_resp"])
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user="csm_user_manage", data=True,
            payload=json.dumps(data["payload_invalid_role"]),
            return_actual_response=True)

        self.log.info("Verifying the returned status code: %s and response: %s ",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        assert_utils.assert_equals(response.json(), data["invalid_role_resp"])

        self.log.info(
            "Step 2: Verified that PATCH API returns 400 response code and  "
            "appropriate error json data for invalid role")

        self.log.info(
            "Step 3: Verifying that PATCH API returns 400 response code and "
            "appropriate error json data for invalid password and role")

        self.log.info("Verifying for invalid role and invalid password: %s",
                      data["payload_invalid_password_role"])
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.BAD_REQUEST,
            user="csm_user_manage",
            data=True,
            payload=json.dumps(data["payload_invalid_password_role"]),
            return_actual_response=True)

        self.log.info("Verifying the returned status code: %s and response: %s",
                      response.status_code, response.json())
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)

        data_new1 = response.json()["message"].split(':')
        data_new2 = data_new1[1].split('{')
        if data_new2[1] == "'role'":
            role_passwd_resp = data["invalid_password_role_resp_1"]
        elif data_new2[1] == "'password'":
            role_passwd_resp = data["invalid_password_role_resp_2"]

        assert_utils.assert_equals(response.json(), role_passwd_resp)

        self.log.info(
            "Step 3: Verified that PATCH API returns 400 response code and "
            "appropriate error json data for invalid password and role")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-15862')
    def test_1173(self):
        """
        Test that in case the password is changed the user should not be able to
        login with the old password

        """

        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        data = self.csm_conf["test_1173"]["data"]
        status_code = self.csm_conf["test_1173"]["status_code"]

        # Verifying that CSM admin user should not be able to login with old password
        self.log.info(
            "Step 1: Verifying that CSM admin user should not be able to login"
            " with old password")

        username = self.csm_user.config["csm_admin_user"]["username"]

        self.log.info(
            "Step 1A: Login as csm root user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm root user")
        old_password = self.csm_user.config["csm_admin_user"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        self.log.info("Payload is: %s", payload_user)

        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username, data=True, payload=json.dumps(payload_user),
            return_actual_response=True, login_as="csm_admin_user")

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verified response code 200 was returned")

        self.log.info("Verifying if the password %s was updated successfully "
                      "for csm user %s", data[0], username)
        self.log.info(
            "Step 1B:Logging in as csm root user %s with new password %s",
            username, data[0])
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_user.verify_modify_csm_user(
            self.log.info(
                "Step 1C:Verifying by logging in as csm root user %s with "
                "old password %s", username,
                self.csm_user.config["csm_admin_user"]["password"]))
        payload_login = {"username": username, "password": old_password}

        response = self.csm_user.restapi.rest_call(
            request_type="post",
            endpoint=self.csm_user.config["rest_login_endpoint"],
            data=json.dumps(payload_login),
            headers=self.csm_user.config["Login_headers"])

        assert_utils.assert_equals(response.status_code, status_code)

        self.log.info("Verified login with old password was not successful!")

        self.log.info("Reverting old password")
        response = self.csm_user.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info(
            "Step 1: Verified that CSM admin user should not be able to login"
            " with old password")

        # Verifying that CSM manage user should not be able to login with old
        # password
        self.log.info(
            "Step 2: Verifying that CSM manage user should not be able to login"
            " with old password")

        username = self.csm_user.config["csm_user_manage"]["username"]

        self.log.info(
            "Step 2A: Login as csm manage user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm manage user")
        old_password = self.csm_user.config["csm_user_manage"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        self.log.info("Payload is: %s", payload_user)

        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username,
            data=True,
            payload=json.dumps(payload_user),
            return_actual_response=True,
            login_as="csm_user_manage")

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verifying response code 200 was returned")

        self.log.info("Verifying if the password %s was updated successfully "
                      "for csm manage user %s", data[0], username)
        self.log.info(
            "Step 2B:Logging in as csm manage user %s with new password %s",
            username, data[0])
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_user.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verified login with new password was successful with "
                      "status code %s and response %s", response.status_code, response.json())
        self.log.info("Verified that the password %s was updated successfully "
                      "for csm manage user %s", data[0], username)

        self.log.info(
            "Step 2C:Verifying by logging in as csm manage user %s with old "
            "password %s", username,
            self.csm_user.config["csm_user_manage"]["password"])
        payload_login = {"username": username, "password": old_password}

        response = self.csm_user.restapi.rest_call(
            request_type="post",
            endpoint=self.csm_user.config["rest_login_endpoint"],
            data=json.dumps(payload_login),
            headers=self.csm_user.config["Login_headers"])

        self.log.info("Verifying the status code %s returned",
                      response.status_code)
        assert_utils.assert_equals(response.status_code, status_code)
        self.log.info("Verified login with old password was not successful!")

        self.log.info("Reverting old password")
        response = self.csm_user.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verified response code 200 was returned")

        self.log.info(
            "Step 2: Verified that CSM manage user should not be able to login"
            " with old password")

        # Verifying that CSM monitor user should not be able to login with old
        # password
        self.log.info(
            "Step 3: Verifying that CSM monitor user should not be able to "
            "login with old password")

        username = self.csm_user.config["csm_user_monitor"]["username"]

        self.log.info(
            "Step 3A: Login as csm monitor user and change its password")
        self.log.info(
            "Forming the payload specifying old password for csm monitor user")
        old_password = self.csm_user.config["csm_user_monitor"]["password"]
        payload_user = {"current_password": old_password, "password": data[0]}
        self.log.info("Payload is: %s", payload_user)

        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=username,
            data=True,
            payload=json.dumps(payload_user),
            return_actual_response=True,
            login_as="csm_user_monitor")

        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verified response code 200 was returned")

        self.log.info("Verifying if the password %s was updated successfully "
                      "for csm monitor user %s", data[0], username)
        self.log.info(
            "Step 3B:Logging in as csm monitor user %s with new "
            "password %s", username, data[0])
        payload_login = {"username": username, "password": data[0]}
        response = self.csm_user.verify_modify_csm_user(
            user=username,
            payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)

        self.log.info("Verified login with new password was successful with "
                      "status code %s and response %s",
                      response.status_code, response.json())
        self.log.info("Verified that the password %s was updated successfully "
                      "for csm monitor user %s", data[0], username)

        self.log.info(
            "Step 3C:Verifying by logging in as csm monitor user %s "
            "with old password %s", username,
            self.csm_user.config["csm_user_monitor"]["password"])
        payload_login = {"username": username, "password": old_password}
        response = self.csm_user.restapi.rest_call(
            request_type="post",
            endpoint=self.csm_user.config["rest_login_endpoint"],
            data=json.dumps(payload_login),
            headers=self.csm_user.config["Login_headers"])

        self.log.info("Verifying the status code %s returned",
                      response.status_code)
        assert_utils.assert_equals(response.status_code, status_code)
        self.log.info("Verified login with old password was not successful!")

        self.log.info("Reverting old password")
        response = self.csm_user.revert_csm_user_password(
            username, data[0], old_password, return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert_utils.assert_equals(
            response.status_code, const.SUCCESS_STATUS)
        self.log.info("Verified response code 200 was returned")

        self.log.info(
            "Step 3: Verified that CSM monitor user should not be able to login"
            " with old password")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-16550')
    def test_1227(self):
        """
        Test that CSM user with role manager cannot perform any REST API request
        on IAM user

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying CSM user with role manager cannot perform any REST API "
            "request on IAM user")

        self.log.info("Creating IAM user for test verification purpose")
        rest_iam_user = RestIamUser()
        new_iam_user = "testiam" + str(int(time.time()))
        response = rest_iam_user.create_iam_user(
            user=new_iam_user, login_as="s3account_user")

        self.log.info(
            "Verifying IAM user %s creation was successful", new_iam_user)
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.info(
            "Verified IAM user %s creation was successful", new_iam_user)

        self.log.info(
            "Step 1: Verifying CSM admin user cannot perform GET request on "
            "IAM user")
        response = rest_iam_user.list_iam_users(login_as="csm_admin_user")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 1: Verified CSM admin user cannot perform GET request on "
            "IAM user")

        self.log.info(
            "Step 2: Verifying CSM manage user cannot perform GET request on "
            "IAM user")
        response = rest_iam_user.list_iam_users(
            login_as="csm_user_manage")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 2: Verified CSM manage user cannot perform GET request on "
            "IAM user")

        self.log.info(
            "Step 3: Verifying CSM admin user cannot perform POST request on "
            "IAM user")
        new_iam_user1 = "testiam" + str(int(time.time()))
        response = rest_iam_user.create_iam_user(
            user=new_iam_user1, login_as="csm_admin_user")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 3: Verified CSM admin user cannot perform POST request on "
            "IAM user")

        self.log.info(
            "Step 4: Verifying CSM manage user cannot perform POST request on "
            "IAM user")
        new_iam_user2 = "testiam" +  str(int(time.time()))
        response = rest_iam_user.create_iam_user(
            user=new_iam_user2, login_as="csm_user_manage")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 4: Verified CSM manage user cannot perform POST request on "
            "IAM user")

        self.log.info(
            "Step 5: Verifying CSM admin user cannot perform DELETE request on "
            "IAM user")
        response = rest_iam_user.delete_iam_user(
            user=new_iam_user, login_as="csm_admin_user")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 5: Verified CSM admin user cannot perform DELETE request on "
            "IAM user")

        self.log.info(
            "Step 6: Verifying CSM manage user cannot perform DELETE request on"
            " IAM user")
        response = rest_iam_user.delete_iam_user(
            user=new_iam_user, login_as="csm_user_manage")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Step 6: Verified CSM manage user cannot perform DELETE request on "
            "IAM user")

        self.log.info(
            "Verified CSM user with role manager cannot perform any REST API "
            "request on IAM user")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-16551')
    def test_1040(self):
        """
        Test that S3 account should not have access to create csm user from backend

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that S3 account does not have access to create csm user "
            "from backend")
        response = self.csm_user.create_csm_user(login_as="s3account_user")
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info(
            "Verified that S3 account does not have access to create csm user "
            "from backend")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-16552')
    def test_1172(self):
        """
        Test that the error messages related to the Log-in should not display
        any important information.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that the error messages related to the Log-in does not "
            "display any important information.")

        # self.rest_lib = RestTestLib()
        username = self.csm_conf["test_1172"]["username"]
        password = self.csm_conf["test_1172"]["password"]
        status_code = self.csm_conf["test_1172"]["status_code"]

        self.log.info("Step 1: Verifying with incorrect password")
        response = self.csm_user.custom_rest_login(
            username=self.csm_user.config["csm_admin_user"]["username"],
            password=password)
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert response.status_code == status_code, "Unexpected status code"
        self.log.info("Step 1: Verified with incorrect password")

        self.log.info("Step 2: Verifying with incorrect username")
        response = self.csm_user.custom_rest_login(
            username=username, password=self.csm_user.config[
                "csm_admin_user"]["password"])
        self.log.info("Expected Response: %s", status_code)
        self.log.info("Actual Response: %s", response.status_code)
        assert_utils.assert_equals(response.status_code, status_code)
        self.log.info("Step 2: Verified with incorrect username")

        self.log.info(
            "Verified that the error messages related to the Log-in does not "
            "display any important information.")

        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-16936')
    def test_7362(self):
        """
        Test that CSM user with monitor role cannot perform POST, PATCH and
        DELETE request on CSM user

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        password = self.csm_conf["test_7362"]["password"]

        self.log.info(
            "Step 1: Verifying that CSM user with monitor role cannot perform "
            "POST request to create new csm user")

        response = self.csm_user.create_csm_user(login_as="csm_user_monitor")
        self.log.debug("Verifying the response returned: %s", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 1: Verified that CSM user with monitor role cannot perform "
            "POST request to create new csm user")

        self.log.info(
            "Creating csm user for testing delete and patch requests")
        response = self.csm_user.create_csm_user()
        self.log.info(
            "Verifying if user was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS_FOR_POST)
        self.log.info(
            "Verified user was created successfully")
        userid = response.json()["id"]

        self.log.info(
            "Step 2: Verifying that CSM user with monitor role cannot perform "
            "DELETE request on a csm user")
        response = self.csm_user.list_csm_single_user(
            request_type="delete",
            expect_status_code=const.FORBIDDEN,
            user=userid,
            return_actual_response=True,
            login_as="csm_user_monitor")
        self.log.debug("Verifying the response returned: %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 2: Verified that CSM user with monitor role cannot perform"
            " DELETE request on a csm user")

        self.log.info(
            "Step 3: Verifying that CSM user with monitor role cannot perform"
            " PATCH request on a CSM user")

        self.log.info("Forming the payload")
        old_password = self.csm_user.config["csm_user_monitor"]["password"]
        payload = {"current_password": old_password, "password": password}

        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.FORBIDDEN,
            user=userid,
            data=True,
            payload=json.dumps(payload),
            return_actual_response=True,
            login_as="csm_user_monitor")
        self.log.debug("Verifying the response returned : %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 3: Verified that CSM user with monitor role cannot perform "
            "PATCH request on a CSM user")

        self.log.info(
            "Verified that CSM user with monitor role cannot perform POST,"
            " PATCH and DELETE API request for CSM user")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip("Test is invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-16935')
    def test_7361(self):
        """
        Test that CSM user with role manager cannot perform DELETE and PATCH
        API request on S3 Accounts

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that CSM user with role manager cannot perform PATCH and"
            " DELETE API request on S3 Account")

        username = self.csm_user.config["s3account_user"]["username"]

        self.log.info(
            "Step 1: Verifying that root csm user cannot perform PATCH API "
            "request on S3 Account")
        response = self.s3_accounts.edit_s3_account_user(
            username=username, login_as="csm_admin_user")

        self.log.debug("Verifying response returned: %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 1: Verified that root csm user cannot perform PATCH API "
            "request on S3 Account")

        self.log.info(
            "Step 2: Verifying that CSM user with role manager cannot perform "
            "PATCH API request on S3 Account")
        response = self.s3_accounts.edit_s3_account_user(
            username=username, login_as="csm_user_manage")

        self.log.debug("Verifying response returned: %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 2: Verified that CSM user with role manager cannot perform "
            "PATCH API request on S3 Account")

        self.log.info(
            "Step 3: Verifying that root csm user cannot perform DELETE API "
            "request on S3 Account")
        response = self.s3_accounts. delete_s3_account_user(
            username=username, login_as="csm_admin_user")

        self.log.debug("Verifying response returned: %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 3: Verified that root csm user cannot perform DELETE API "
            "request on S3 Account")

        self.log.info(
            "Step 4: Verifying that CSM user with role manager cannot perform "
            "DELETE API request on S3 Account")
        response = self.s3_accounts. delete_s3_account_user(
            username=username, login_as="csm_user_manage")

        self.log.debug("Verifying response returned : %s", response)
        assert_utils.assert_equals(
            response.status_code, const.FORBIDDEN)
        self.log.info("Verified the response: %s", response)

        self.log.info(
            "Step 4: Verified that CSM user with role manager cannot perform "
            "DELETE API request on S3 Account")

        self.log.info(
            "Verified that CSM user with role manager cannot perform PATCH and "
            "DELETE API request on S3 Account")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.parallel
    @pytest.mark.tags('TEST-17191')
    def test_7360(self):
        """
        Test that CSM user with role manager cannot perform REST API request on
        S3 Buckets
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that CSM user with role manager cannot perform REST "
            "API request on S3 Buckets")
        self.log.info(
            "Creating valid bucket and valid bucket policy for test purpose")
        s3_buckets = RestS3Bucket()
        self.log.info("Creating bucket for test")
        response = s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="s3account_user")

        self.log.debug("Verifying S3 bucket was created successfully")
        assert_utils.assert_equals(response.status_code,
                                   const.SUCCESS_STATUS)
        self.log.debug("Verified S3 bucket %s was created successfully",
                       response.json()['bucket_name'])
        bucket_name = response.json()['bucket_name']
        bucket_policy_obj = RestS3BucketPolicy(bucket_name)

        self.log.info(
            "Step 1: Verifying that CSM user with role manager cannot perform "
            "GET REST API request on S3 Buckets")
        response = s3_buckets.list_all_created_buckets(
            login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code,
                       const.FORBIDDEN)

        self.log.info(
            "Step 1: Verified that CSM user with role manager cannot perform "
            "GET REST API request on S3 Buckets")

        self.log.info(
            "Step 2: Verifying that CSM user with role manager cannot perform "
            "POST REST API request on S3 Buckets")
        response = s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code, const.FORBIDDEN)

        self.log.info(
            "Step 2: Verified that CSM user with role manager cannot perform "
            "POST REST API request on S3 Buckets")

        self.log.info(
            "Step 3: Verifying that CSM user with role manager cannot perform"
            "DELETE REST API request on S3 Buckets")
        response = s3_buckets.delete_s3_bucket(
            bucket_name=bucket_name, login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code,
                       const.FORBIDDEN)

        self.log.info(
            "Step 3: Verified that CSM user with role manager cannot "
            "perform DELETE REST API request on S3 Buckets")

        self.log.info(
            "Step 4: Verifying that CSM manage user cannot perform "
            "PATCH bucket policy request for a S3 bucket")
        operation = "default"
        custom_policy_params = {}
        response = bucket_policy_obj.create_bucket_policy(
            operation=operation, custom_policy_params=custom_policy_params,
            login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code, const.FORBIDDEN)

        self.log.info(
            "Step 5: Verifying that CSM user with role manager cannot perform "
            "GET bucket policy request for S3 Buckets")
        response = bucket_policy_obj.get_bucket_policy(
            bucket_name=bucket_name, login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code,
                       const.FORBIDDEN)

        self.log.info(
            "Step 5: Verifying that CSM user with role manager cannot perform"
            " GET bucket policy request for S3 Buckets")

        self.log.info(
            "Step 6: Verifying that CSM user with role manager cannot perform "
            "DELETE bucket policy request for S3 Buckets")
        response = bucket_policy_obj.delete_bucket_policy(
            login_as="csm_user_manage")

        self.log.debug("Verifying the response returned: %s ", response)
        assert_utils.assert_equals(response.status_code,
                                   const.FORBIDDEN)
        self.log.debug("Verified the actual response returned: %s with the "
                       "expected response %s", response.status_code,
                       const.FORBIDDEN)

        self.log.info(
            "Step 6: Verified that CSM user with role manager cannot "
            "perform DELETE bucket policy request for S3 Buckets")

        self.log.info(
            "Verified that CSM user with role manager cannot perform "
            "REST API request on S3 Buckets")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-12019')
    def test_7420(self):
        """
        Test that Root user should able to change other users password and roles
        without specifying old_password through CSM-REST

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Test Purpose: Verifying that csm root user should able to change "
            "other users password and roles without specifying old_password")

        data = self.csm_conf["test_7420"]["data"]
        self.log.info("Step 1: Creating csm manage user")
        response = self.csm_user.create_csm_user(
            user_type=data[0], user_role=data[1])

        self.log.info(
            "Verifying if user was created successfully")
        assert response.status_code == const.SUCCESS_STATUS_FOR_POST
        username = response.json()["username"]
        userid = response.json()["id"]
        self.log.info(
            "Verified User %s got created successfully", username)

        self.log.info(
            "Step 2: Login as csm root user and change password and role of "
            "user without providing old password %s", username)
        self.log.info("Forming the payload without specifying old password")
        payload_user = {"role": data[2], "password": data[3]}
        response = self.csm_user.list_csm_single_user(
            request_type="patch",
            expect_status_code=const.SUCCESS_STATUS,
            user=userid,
            data=True,
            payload=json.dumps(payload_user),
            return_actual_response=True)
        self.log.info("Verifying response code 200 was returned")
        assert response.status_code == const.SUCCESS_STATUS

        self.log.info("Verifying if the password %s and role %s was updated "
                      "successfully for csm user %s", data[3], data[2], username)
        self.log.info(
            "Logging in as user %s with new password %s", username, data[3])
        payload_login = {"username": username, "password": data[3]}
        response = self.csm_user.verify_modify_csm_user(
            user=username, payload_login=json.dumps(payload_login),
            expect_status_code=const.SUCCESS_STATUS,
            return_actual_response=True)
        assert response.status_code == const.SUCCESS_STATUS
        assert response.json()["role"] == data[2]

        self.log.info("Verified login with new password was successful with "
                      "status code %s and response %s", response.status_code, response.json())
        self.log.info("Verified that the password %s and role %s was updated"
                      " successfully for csm user %s", data[3], response.json()["role"], username)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-25278')
    def test_25278(self):
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        test_cfg = self.csm_conf["test_25278"]
        response = self.csm_user.edit_csm_user(login_as="csm_user_monitor", user="admin",
                                    role="manage")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(test_cfg["error_code"]) , "Error code check failed."
        assert response.json()["message"] == test_cfg["message"].format("csm_user_monitor","admin") , "Message check failed."
        assert response.json()["message_id"] == test_cfg["message_id"], "Message ID check failed."

        response = self.csm_user.edit_csm_user(login_as="csm_user_monitor", user="csm_user_manage",
                                    role="monitor")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(test_cfg["error_code"]) , "Error code check failed."
        assert response.json()["message"] == test_cfg["message"].format("csm_user_monitor","csm_user_manage") , "Message check failed."
        assert response.json()["message_id"] == test_cfg["message_id"], "Message ID check failed."
        self.log.info("##### Test completed -  %s #####", test_case_name)

        response = self.csm_user.edit_csm_user(login_as="csm_user_monitor", user="csm_user_monitor",
                                    role="manage")
        assert response.status_code == const.FORBIDDEN, "Status code check failed."
        assert response.json()["error_code"] == str(test_cfg["error_code"]) , "Error code check failed."
        assert response.json()["message"] == test_cfg["message"].format("csm_user_monitor","csm_user_monitor") , "Message check failed."
        assert response.json()["message_id"] == test_cfg["message_id"], "Message ID check failed."
        self.log.info("##### Test completed -  %s #####", test_case_name)
