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
"""Tests Bucket policy using REST API
"""
import logging
import pytest
from libs.csm.rest.csm_rest_bucket import RestS3Bucket
from libs.csm.rest.csm_rest_bucket import RestS3BucketPolicy
from libs.csm.rest.csm_rest_iamuser import RestIamUser
from libs.csm.csm_setup import CSMConfigsCheck
from commons import cortxlogging

class TestBucketPolicy():
    """S3 Bucket Policy Testsuite
    """
    @classmethod
    def setup_class(cls):
        """
        This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.a
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups")
        cls.config = CSMConfigsCheck()
        setup_ready = cls.config.check_predefined_s3account_present()
        if not setup_ready:
            setup_ready = cls.config.setup_csm_s3()
        assert setup_ready

    def setup_method(self):
        """Setup for each tests
        """
        self.s3_buckets = RestS3Bucket()
        self.log.info("Creating bucket for test")
        response = self.s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="s3account_user")
        self.bucket_name = response.json()['bucket_name']
        self.log.info("##### bucket name %s #####", self.bucket_name)
        self.bucket_policy = RestS3BucketPolicy(self.bucket_name)
        self.rest_iam_user = RestIamUser()
        self.created_iam_users = set()
        self.log.info("Ended test setups")

    def teardown_method(self):
        """teardown for each tests
        """
        self.log.info("Teardown started")
        self.s3_buckets.delete_s3_bucket(
            bucket_name=self.bucket_name,
            login_as="s3account_user")
        for user in self.created_iam_users:
            self.rest_iam_user.delete_iam_user(
                login_as="s3account_user", user=user)
        self.log.info("Teardown ended")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10783')
    def test_4212(self):
        """Test that s3 user can add bucket policy
         """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.bucket_policy.create_and_verify_bucket_policy()
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10784')
    def test_4213(self):
        """Test that s3 user can update bucket policy
         """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.bucket_policy.create_and_verify_bucket_policy()
        assert self.bucket_policy.create_and_verify_bucket_policy(
            operation='update_policy')
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10785')
    def test_4214(self):
        """Test that error is retuned when s3 user sends PUT request with invalid json
         """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.bucket_policy.create_and_verify_bucket_policy(expected_status_code=400,
                                                                  operation="invalid_payload",
                                                                  validate_expected_response=False)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10779')
    def test_4215(self):
        """test that s3 user can GET current bucket policy
         """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.bucket_policy.create_and_verify_bucket_policy(
            login_as="s3account_user")
        assert self.bucket_policy.get_and_verify_bucket_policy()
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10788')
    def test_4216(self):
        """Test that error code is returned when s3 user send GET request on
        bucket when no bucket policy exist on it
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.bucket_policy.get_and_verify_bucket_policy(
            expected_status_code=404,
            validate_expected_response=False)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10781')
    def test_4217(self):
        """Test that error is returned when s3 user send GET request on incorrect/invalid bucket
         """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.bucket_policy.create_and_verify_bucket_policy()
        assert self.bucket_policy.get_and_verify_bucket_policy(
            validate_expected_response=False,
            expected_status_code=404,
            invalid_bucket=True)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10780')
    def test_4218(self):
        """Test that s3 user can delete bucket policy
         """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.bucket_policy.create_and_verify_bucket_policy()
        assert self.bucket_policy.delete_and_verify_bucket_policy()
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10786')
    def test_4219(self):
        """Test that error is returned when s3 user try delete bucket policy which doesn't exist
         """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.bucket_policy.delete_and_verify_bucket_policy(
            expected_status_code=404)
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10792')
    def test_4220(self):
        """test that s3 user can add bucket policy to allow some bucket related
        actions to specific user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        assert status, response
        user_id = response['user_id']
        self.created_iam_users.add(response['user_name'])
        policy_params = {'s3operation': 'GetObject',
                         'effect': 'Allow',
                         'principal': user_id}
        assert self.bucket_policy.create_and_verify_bucket_policy(
            operation='custom', custom_policy_params=policy_params,
            validate_expected_response=False)
        assert self.bucket_policy.get_and_verify_bucket_policy()
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10794')
    def test_4221(self):
        """test that s3 user can add bucket policy to allow many(more than one)
        bucket related actions to many(more than one) users
         """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        assert status, response
        user_id = response['user_id']
        self.created_iam_users.add(response['user_name'])
        policy_params = {'s3operation1': 'GetObject',
                         's3operation2': 'DeleteObject',
                         'effect': 'Allow',
                         'principal': user_id
                         }
        assert self.bucket_policy.create_and_verify_bucket_policy(
            operation='multi_policy', custom_policy_params=policy_params)
        assert self.bucket_policy.get_and_verify_bucket_policy()
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10793')
    def test_4222(self):
        """test that s3 user can add bucket policy to deny all bucket related
        actions to specific user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        status, response = self.rest_iam_user.create_and_verify_iam_user_response_code()
        assert status, response
        user_id = response['user_id']
        self.created_iam_users.add(response['user_name'])
        policy_params = {'s3operation': 'GetObject',
                         'effect': 'Deny',
                         'principal': user_id}
        assert self.bucket_policy.create_and_verify_bucket_policy(
            operation='custom', custom_policy_params=policy_params)
        assert self.bucket_policy.get_and_verify_bucket_policy()
        self.log.info("##### Test ended -  %s #####", test_case_name)
