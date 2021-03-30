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

"""PUT Bucket test module."""

import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils import assert_utils
from libs.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_test_lib import S3LibNoAuth

S3T_OBJ = S3TestLib()
NO_AUTH_OBJ = S3LibNoAuth(s3_cert_path=S3_CFG["s3_cert_path"])
NO_AUTH_OBJ_WITHOUT_CERT = S3LibNoAuth(s3_cert_path=None)


class TestPutBucket:
    """PUT Bucket Test suite."""

    def setup_method(self):
        """
        This function will be invoked before each test case execution.

        It will perform prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Test setup operations.")
        self.bucket_name = "-".join(["putbk", str(time.time())])
        self.log.info("ENDED: Test setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after running each test case.

        It will clean all resources such as S3 buckets and the objects present into that bucket
        which are getting created during test execution .
        """
        self.log.info("STARTED: Test teardown operations.")
        status, bktlist = S3T_OBJ.bucket_list()
        if self.bucket_name in bktlist:
            resp = S3T_OBJ.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: Test teardown operations.")

    def create_and_list_buckets_without_auth(self, bucket_name, err_message):
        """
        This function creates a bucket with specified name and then list all buckets.

        :param str bucket_name: Name of the bucket to be created
        :param str err_message: Error that will occur while creating or listing bucket
        """
        self.log.info("Step 1: Creating bucket without authorization header.")
        self.log.info("Bucket name: %s", bucket_name)
        try:
            resp = NO_AUTH_OBJ.create_bucket(bucket_name)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
            assert_utils.assert_not_equal(
                bucket_name, resp[1], f"bucket created: {bucket_name}")
        except CTException as error:
            self.log.error(error.message)
            assert_utils.assert_in(
                err_message,
                error.message,
                error.message)
        self.log.info("Step 2: Listing buckets without authorization header")
        try:
            resp = NO_AUTH_OBJ.bucket_list()
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
            assert_utils.assert_not_in(bucket_name, resp[1], resp)
        except CTException as error:
            self.log.error(error.message)
            assert_utils.assert_in(
                err_message,
                error.message,
                error.message)

    @pytest.mark.s3
    @pytest.mark.tags('TEST-5838')
    @CTFailOn(error_handler)
    def test_verify_put_bucket_authorization_header_missing_412(self):
        """Verify put-bucket where authorization header is missing."""
        self.log.info(
            "STARTED: Verify put-bucket where authorization header is missing")
        self.create_and_list_buckets_without_auth(
            self.bucket_name, "AccessDenied")
        self.log.info(
            "ENDED: Verify put-bucket where authorization header is missing")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-5839')
    @CTFailOn(error_handler)
    def test_verify_put_bucket_ip_address_format_authorization_header_missing_415(
            self):
        """Verify put-bucket with ip address format where authorization header is missing."""
        self.log.info(
            "STARTED: Verify put-bucket with ip address format where authorization"
            " header is missing")
        self.create_and_list_buckets_without_auth(
            "192.168.10.20", "AccessDenied")
        self.log.info(
            "ENDED: Verify put-bucket with ip address format where authorization header is missing")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-5840')
    @CTFailOn(error_handler)
    def test_create_multiple_buckets_authorization_header_missing_416(self):
        """Create multiple buckets where authorization header is missing."""
        self.log.info(
            "STARTED: Create multiple buckets where authorization header is missing")
        for bucket in [f"{self.bucket_name}416_1", f"{self.bucket_name}416_2"]:
            self.create_and_list_buckets_without_auth(bucket, "AccessDenied")
        self.log.info(
            "ENDED: Create multiple buckets where authorization header is missing")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-5841')
    @CTFailOn(error_handler)
    def test_verify_put_bucket_without_giving_cacert_417(self):
        """
        Verify put-bucket without giving --cacert /etc/ssl/stx-s3-clients/s3/ca.crt using curl command
        and list that bucket
        """
        self.log.info(
            "STARTED: Verify put-bucket without giving --cacert /etc/ssl/stx-s3-clients/s3/ca.crt"
            " using curl command and list that bucket")
        self.log.info(
            "Step 1: Creating bucket without authorization header and without ca.cert")
        try:
            resp = NO_AUTH_OBJ_WITHOUT_CERT.create_bucket(self.bucket_name)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
            assert_utils.assert_not_equal(
                self.bucket_name, resp[1], f"bucket created: {self.bucket_name}")
        except CTException as error:
            self.log.error(error.message)
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info("Step 2: Listing buckets without authorization header")
        try:
            resp = NO_AUTH_OBJ_WITHOUT_CERT.bucket_list()
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
            assert_utils.assert_not_in(self.bucket_name, resp[1], resp)
        except CTException as error:
            self.log.error(error.message)
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "ENDED: Verify put-bucket without giving --cacert /etc/ssl/stx-s3-clients/s3/ca.crt"
            " using curl command and list that bucket")
