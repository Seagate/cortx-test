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
"""Tests operations on S3 Users using REST API"""

import json
import logging
import pytest
from commons.utils import config_utils
from commons.constants import Rest as const
from commons import cortxlogging
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_s3user import RestS3user

class TestS3user():
    """S3 user test class"""

    @classmethod
    def setup_class(cls):
        """This is method is for test suite set-up"""
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.config = CSMConfigsCheck()
        user_already_present = cls.config.check_predefined_s3account_present()
        if not user_already_present:
            user_already_present = cls.config.setup_csm_s3
        assert user_already_present
        cls.s3user = RestS3user()
        cls.csm_conf = config_utils.read_yaml(
            "config/csm/test_rest_s3_user.yaml")[1]
        cls.log.info("Initiating Rest Client for Alert ...")

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10744")
    def test_276(self):
        """Initiating the test case for the verifying success rest alert
        response.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.s3user.create_s3_account()
        assert self.s3user.verify_list_s3account_details()
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10746")
    def test_290(self):
        """Initiating the test case for the verifying success rest alert response

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3user.create_and_verify_s3account(
            user="valid", expect_status_code=self.s3user.success_response)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10747")
    def test_291(self):
        """Initiating the test case for the verifying success rest alert response

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3user.create_and_verify_s3account(
            user="invalid", expect_status_code=self.s3user.bad_request_response)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10749")
    def test_293(self):
        """Initiating the test case for the verifying success rest alert response

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.s3user.create_s3_account()
        assert self.s3user.create_and_verify_s3account(
            user="duplicate", expect_status_code=self.s3user.conflict_response)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10748")
    def test_292(self):
        """Initiating the test case for the verifying success rest alert response

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3user.create_and_verify_s3account(
            user="missing", expect_status_code=self.s3user.bad_request_response)
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10750")
    def test_294(self):
        """Initiating the test case for unauthorized user try to create
        s3account user.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3user.create_s3_account(
            login_as="s3account_user")
        assert response.status_code == self.s3user.forbidden
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10752")
    def test_586(self):
        """Initiating the test case for the verifying success rest alert response

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3user.edit_and_verify_s3_account_user(
            user_payload="valid")
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10753")
    def test_590(self):
        """
        Initiating the test case for REST API to update S3
        account/non_existing_user using PATCH request.

        :return:
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3user.edit_s3_account_user(
            "non_existing_user", login_as="s3account_user")
        assert response.status_code == self.s3user.forbidden
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10754")
    def test_587(self):
        """
        Initiating the test case for user Does not update secret/access key

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3user.edit_and_verify_s3_account_user(
            user_payload="unchanged_access")
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10755")
    def test_592(self):
        """
        Initiating the test case for Sender has no permission to update s3 account

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        # verifying No IAM user should present on first visit to s3 account
        response = self.s3user.edit_s3_account_user(
            username=self.s3user.default_s3user_name, login_as="csm_admin_user")
        assert response.status_code == self.s3user.forbidden
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10756")
    def test_615(self):
        """
        Initiating the test case for user Does not update secret/access key

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3user.edit_and_verify_s3_account_user(
            user_payload="no_payload")
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10757")
    def test_598(self):
        """
        Initiating the test case for user only reset access key value False

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3user.edit_and_verify_s3_account_user(
            user_payload="only_reset_access_key")
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10758")
    def test_595(self):
        """
        Initiating the test case for user only reset access key value

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3user.edit_and_verify_s3_account_user(
            user_payload="only_reset_access_key")
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10759")
    def test_606(self):
        """
        Initiating the test case for user only password field

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3user.edit_and_verify_s3_account_user(
            user_payload="only_password")
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10760")
    def test_488(self):
        """
        Initiating the test case for Successful delete account user

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3user.delete_and_verify_s3_account_user()
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10761")
    def test_491(self):
        """
        Initiating the test case for delete non existing s3account user

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3user.delete_s3_account_user("non_existing_user")
        assert response.status_code == self.s3user.forbidden
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10762")
    def test_492(self):
        """
        Initiating the test case for delete s3account user without permission

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3user.delete_s3_account_user(
            self.s3user.default_s3user_name, login_as="csm_admin_user")
        assert response.status_code == self.s3user.forbidden
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-10763")
    def test_493(self):
        """
        Initiating the test case for delete s3account without account name

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        # passing user name as blank
        response = self.s3user.delete_s3_account_user(
            username="", login_as="s3account_user")
        assert response.status_code == self.s3user.method_not_found
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-12842")
    def test_1914(self):
        """
        Initiating the test to test that error is returned when payload is incorrect

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Fetching the s3 account name")
        account_name = self.s3user.config["s3account_user"]["username"]

        self.log.info(
            "Creating payload with invalid password for the Patch request")
        payload = self.csm_conf["test_1914"]["payload"]

        self.log.info(
            "Providing invalid password for s3 account %s in Patch request", account_name)

        response = self.s3user.edit_s3_account_user_invalid_password(
            username=account_name,
            payload=json.dumps(payload),
            login_as="s3account_user")

        self.log.info(
            "Verifying response returned for s3 account %s", account_name)
        assert response.status_code == const.BAD_REQUEST

        self.log.info(
            "Verified that response returned for invalid password in Patch "
            "request for s3 account %s is %s", account_name, response)

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.tags("TEST-17188")
    def test_1915(self):
        """
        Test that error should be returned when s3 user enters some other s3 user's account name

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info(
            "Verifying that error should be returned when s3 user enters some"
            " other s3 user's account name")
        response_msg = self.csm_conf["test_1915"]["response_msg"]

        self.log.info("Creating new S3 account for test purpose")
        response = self.s3user.create_s3_account()

        self.log.debug("Verifying new S3 account got created successfully")
        assert response.status_code == const.SUCCESS_STATUS
        self.log.debug("Verified new S3 account %s got created successfully",
                        response.json()["account_name"])

        s3_acc = response.json()["account_name"]

        self.log.info(
            "Logging in with with existing s3 account %s and trying to change the "
            "password for new %s account", self.s3user.config["s3account_user"]["username"], s3_acc)
        response = self.s3user.edit_s3_account_user(
            username=s3_acc, payload="valid", login_as="s3account_user")

        self.log.debug("Verifying the response returned %s", response)
        assert response.status_code, self.s3user.forbidden
        assert response.json(), response_msg
        self.log.debug("Verified that expected status code %s and expected response "
                       "message %s was returned", response.status_code, response.json())

        self.log.info(
            "Verified that is returned when s3 user enters some other s3 user's account name")
        self.log.info(
            "##### Test completed -  %s #####", test_case_name)
