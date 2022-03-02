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
"""Tests various operations on IAM users using REST API
NOTE: These tests are no longer valid as CSM will no longer support IAM user operations.
"""
import logging
import pytest
from commons import configmanager
from commons import cortxlogging
from libs.csm.csm_setup import CSMConfigsCheck
from libs.csm.rest.csm_rest_iamuser import RestIamUser

class TestIamUser():
    """REST API Test cases for IAM users"""

    @classmethod
    def setup_class(cls):
        """
        This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_iam_user.yaml")
        cls.log.info("Ended test module setups")
        cls.config = CSMConfigsCheck()
        setup_ready = cls.config.check_predefined_s3account_present()
        if not setup_ready:
            setup_ready = cls.config.setup_csm_s3()
        assert setup_ready
        cls.created_iam_users = set()
        cls.rest_iam_user = RestIamUser()
        cls.log.info("Initiating Rest Client ...")

    def teardown_method(self):
        """Teardown method which run after each function.
        """
        self.log.info("Teardown started")
        for user in self.created_iam_users:
            self.rest_iam_user.delete_iam_user(
                login_as="s3account_user", user=user)
        self.log.info("Teardown ended")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10732')
    def test_1133(self):
        """Test that IAM users are not permitted to login
          """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        status_code = self.csm_conf["test_1133"]
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        assert status, response
        user_name = response['user_name']
        self.created_iam_users.add(response['user_name'])
        assert(
            self.rest_iam_user.iam_user_login(user=user_name) == status_code["status_code"])
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-14749')
    def test_1041(self):
        """Test that S3 account should have access to create IAM user from back end
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.info("Creating IAM user")
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        print(status)
        self.log.info(
            "Verifying status code returned is 200 and response is not null")
        assert status, response

        for key, value in response.items():
            self.log.info("Verifying %s is not empty", key)
            assert value

        self.log.info("Verified that S3 account %s was successfully able to create IAM user: %s",
            self.rest_iam_user.config["s3account_user"]["username"], response)

        self.log.info("##### Test ended -  %s #####", test_case_name)


    @pytest.mark.skip("Test invalid for R2")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-17189')
    def test_1022(self):
        """
        Test that IAM user is not able to execute and access the CSM REST APIs.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        self.log.debug(
            "Verifying that IAM user is not able to execute and access the CSM REST APIs")
        assert self.rest_iam_user.verify_unauthorized_access_to_csm_user_api()
        self.log.debug(
            "Verified that IAM user is not able to execute and access the CSM REST APIs")
        self.log.info("##### Test ended -  %s #####", test_case_name)
