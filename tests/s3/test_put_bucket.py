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

"""PUT Bucket test module."""

import logging
import time

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.s3.s3_test_lib import S3LibNoAuth
from libs.s3.s3_test_lib import S3TestLib


class TestPutBucket:
    """PUT Bucket Test suite."""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.no_auth_obj = None
        cls.no_auth_obj_without_cert = None

    # pylint: disable=attribute-defined-outside-init
    def setup_method(self):
        """Function to perform the setup ops for each test."""
        self.log = logging.getLogger(__name__)
        self.s3t_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.no_auth_obj = S3LibNoAuth(endpoint_url=S3_CFG["s3_url"],
                                       s3_cert_path=S3_CFG["s3_cert_path"])
        self.no_auth_obj_without_cert = S3LibNoAuth(endpoint_url=S3_CFG["s3_url"],
                                                    s3_cert_path=None)
        self.log.info("STARTED: setup test operations.")
        self.bucket_name = "putbkt-{}".format(time.perf_counter_ns())
        self.log.info("ENDED: setup test operations.")

    def teardown_method(self):
        """Function to perform the clean up for each test."""
        self.log.info("STARTED: Test teardown operations.")
        status, bktlist = self.s3t_obj.bucket_list()
        assert_utils.assert_true(status, bktlist)
        if self.bucket_name in bktlist:
            resp = self.s3t_obj.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: Test teardown operations.")

    def create_and_list_buckets_without_auth(self, bucket_name, err_message):
        """
        Function creates a bucket with specified name and then list all buckets.

        :param str bucket_name: Name of the bucket to be created
        :param str err_message: Error that will occur while creating or listing bucket
        """
        self.log.info("Step 1: Creating bucket without authorization header.")
        self.log.info("Bucket name: %s", bucket_name)
        try:
            resp = self.no_auth_obj.create_bucket(bucket_name)
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
            resp = self.no_auth_obj.bucket_list()
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
            assert_utils.assert_not_in(bucket_name, resp[1], resp)
        except CTException as error:
            self.log.error(error.message)
            assert_utils.assert_in(
                err_message,
                error.message,
                error.message)

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_put
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

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_put
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

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_put
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

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_put
    @pytest.mark.tags('TEST-5841')
    @CTFailOn(error_handler)
    def test_verify_put_bucket_without_giving_cacert_417(self):
        """
        Verify put-bucket.

        Verify put-bucket without giving --cacert /etc/ssl/stx-s3-clients/s3/ca.crt using curl
         command and list that bucket.
        """
        self.log.info(
            "STARTED: Verify put-bucket without giving --cacert /etc/ssl/stx-s3-clients/s3/ca.crt"
            " using curl command and list that bucket")
        self.log.info(
            "Step 1: Creating bucket without authorization header and without ca.cert")
        try:
            resp = self.no_auth_obj_without_cert.create_bucket(
                self.bucket_name)
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
            resp = self.no_auth_obj_without_cert.bucket_list()
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
