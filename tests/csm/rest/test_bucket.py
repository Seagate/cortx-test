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
"""Tests S3 buckets using REST API
"""
import logging
import pytest
from libs.csm.rest.csm_rest_bucket import RestS3Bucket
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.csm.csm_setup import CSMConfigsCheck
from commons import configmanager
from commons.utils import assert_utils
from commons import cortxlogging
from commons.constants import Rest as const
class TestS3Bucket():
    """ S3 bucket test cases"""
    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.config = CSMConfigsCheck()
        setup_ready = cls.config.check_predefined_s3account_present()
        if not setup_ready:
            setup_ready = cls.config.setup_csm_s3()
        assert setup_ready
        cls.s3_buckets = RestS3Bucket()
        cls.s3_account = RestS3user()
        cls.log.info("Initiating Rest Client for Alert ...")
        cls.csm_conf = configmanager.get_config_wrapper(fpath="config/csm/test_rest_s3_bucket.yaml")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10764')
    def test_573(self):
        """Initiating the test case for the verifying response of create bucket rest
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3_buckets.create_and_verify_new_bucket(
            const.SUCCESS_STATUS)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10765')
    def test_575(self):
        """Initiating the test case for the verifying response of create bucket
        rest with bucket name less than three
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3_buckets.create_and_verify_new_bucket(
            const.BAD_REQUEST, bucket_type="bucket_name_less_than_three_char")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10766')
    def test_576(self):
        """Initiating the test case for the verifying response of create bucket
        rest with bucket name more than 63
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3_buckets.create_and_verify_new_bucket(
            const.BAD_REQUEST, bucket_type="bucket_name_more_than_63_char")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10767')
    def test_577(self):
        """Initiating the test case for the verifying response of create bucket
        rest invalid initial letter of bucket
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("checking for bucket name start_with_underscore")
        start_with_underscore = self.s3_buckets.create_and_verify_new_bucket(
            const.BAD_REQUEST, bucket_type="start_with_underscore")
        self.log.info("The status for bucket name start_with_underscore is %s",
            start_with_underscore)
        start_with_uppercase = self.s3_buckets.create_and_verify_new_bucket(
            const.BAD_REQUEST, bucket_type="start_with_uppercase")
        self.log.info("The status for bucket name start_with_uppercase is %s",
            start_with_uppercase)
        assert start_with_uppercase and start_with_underscore

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-14750')
    def test_578(self):
        """Initiating the test to test RESP API to create bucket with bucketname
        having special or alphanumeric character
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        bucketname = self.csm_conf["test_578"]["bucket_name"]
        resp_msg = self.csm_conf["test_578"]["response_msg"]

        self.log.info(
            "Step 1: Verifying creating bucket with bucket name containing special characters")
        response = self.s3_buckets.create_invalid_s3_bucket(
            bucket_name=bucketname[0], login_as="s3account_user")

        self.log.info(response.json())

        self.log.info("Verifying the status code %s and response returned %s",
            response.status_code, response.json())
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        assert_utils.assert_equals(response.json(),
                                   resp_msg)

        self.log.info(
            "Step 1: Verified creating bucket with bucket name containing special characters")

        self.log.info(
            "Step 2: Verifying creating bucket with bucket name containing alphanumeric characters")
        response = self.s3_buckets.create_invalid_s3_bucket(
            bucket_name=bucketname[1], login_as="s3account_user")

        self.log.info("Verifying the status code %s and response returned %s",
            response.status_code, response.json())
        assert_utils.assert_equals(response.status_code,
                                   const.BAD_REQUEST)
        assert_utils.assert_equals(response.json(),
                                   resp_msg)

        self.log.info(
            "Step 1: Verified creating bucket with bucket name containing alphanumeric characters")

        self.log.info(
            "##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10768')
    def test_579(self):
        """Initiating the test case for the verifying response of create bucket
        rest for ip address as bucket name
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3_buckets.create_and_verify_new_bucket(
            const.BAD_REQUEST, bucket_type="ip_address")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10769')
    def test_580(self):
        """Initiating the test case for the verifying response of create bucket
        rest with unauthorized user login
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="csm_admin_user")
        assert const.FORBIDDEN == response.status_code

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10770')
    def test_581(self):
        """Initiating the test case for the verifying response of create bucket
        rest with duplicate user
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3_buckets.create_and_verify_new_bucket(
            const.CONFLICT, bucket_type="duplicate")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10771')
    def test_589(self):
        """Initiating the test case for the verifying response of create bucket
        rest with invalid data
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3_buckets.create_and_verify_new_bucket(
            const.BAD_REQUEST, bucket_type="invalid")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10772')
    def test_591(self):
        """Initiating the test case for the verifying response of list bucket rest
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.s3_buckets.create_s3_bucket(
            bucket_type="valid", login_as="s3account_user")
        assert self.s3_buckets.list_and_verify_bucket()

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10773')
    def test_593(self):
        """Initiating the test case for the verifying response of bucket rest
        for newly created s3 account
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.s3_account.create_s3_account(save_new_user=True)
        self.s3_buckets.list_and_verify_bucket(
            expect_no_user=True, login_as="s3account_user")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10774')
    def test_594(self):
        """Initiating the test case for the verifying response of list bucket
        rest with unauthorized user login
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3_buckets.list_all_created_buckets(
            login_as="csm_admin_user")
        assert const.FORBIDDEN == response.status_code

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10775')
    def test_596(self):
        """Initiating the test case for the verifying response of delete bucket rest
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3_buckets.delete_and_verify_new_bucket(
            const.SUCCESS_STATUS)

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10777')
    def test_597(self):
        """Initiating the test case for the verifying response of delete bucket that does not exist
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        assert self.s3_buckets.delete_and_verify_new_bucket(
            const.METHOD_NOT_FOUND, bucket_type="does-not-exist")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10776')
    def test_599(self):
        """Initiating the test case for the verifying response of list bucket
        rest with unauthorized user login
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3_buckets.delete_s3_bucket(
            bucket_name="any_name", login_as="csm_admin_user")
        assert const.FORBIDDEN == response.status_code

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.tags('TEST-10778')
    def test_601(self):
        """Initiating the test case for the verifying response of delete bucket
        rest with no bucket name
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        response = self.s3_buckets.delete_s3_bucket(
            bucket_name="", login_as="s3account_user")
        assert const.METHOD_NOT_FOUND == response.status_code
