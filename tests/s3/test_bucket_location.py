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

"""Bucket Location Test Module."""

import time
import logging
import pytest

from commons.constants import S3_ENGINE_RGW
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils import assert_utils
from libs.s3 import s3_test_lib
from libs.s3 import s3_acl_test_lib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from config.s3 import S3_CFG
from config import CMN_CFG


class TestBucketLocation:
    """Bucket Location Test suite."""

    # pylint: disable=attribute-defined-outside-init
    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Summary: Function will be invoked prior to each test case.

        Description: It will perform all prerequisite and cleanup test.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED : Setup test operations.")
        self.s3_test_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.account_name1 = "location-acc1{}".format(time.perf_counter_ns())
        self.email_id1 = "{}@seagate.com".format(time.perf_counter_ns())
        self.account_name2 = "location-acc2{}".format(time.perf_counter_ns())
        self.email_id2 = "{}@seagate.com".format(time.perf_counter_ns())
        self.bucket_name = "location-bkt{}".format(time.perf_counter_ns())
        self.s3acc_password = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.rest_obj = S3AccountOperations()
        self.account_list = []
        self.log.info("ENDED : Setup test operations.")
        yield
        self.log.info("STARTED: Teardown test operations.")
        self.log.info("Delete bucket: %s", self.bucket_name)
        resp = self.s3_test_obj.bucket_list()[1]
        self.log.info("Bucket list: %s", resp)
        for bucket_name in resp:
            resp = self.s3_test_obj.delete_bucket(bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Account list: %s", self.account_list)
        for acc in self.account_list:
            resp = self.rest_obj.delete_s3_account(acc)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: Teardown test operations.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_location
    @pytest.mark.sanity
    @pytest.mark.tags("TEST-5310")
    @CTFailOn(error_handler)
    def test_get_bkt_loc_valid_bkt_272(self):
        """Verify get bucket location for valid bucket which is present."""
        self.log.info(
            "Verify get bucket location for valid bucket which is present")
        self.log.info(
            "Step 1 : Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(
            self.bucket_name,
            resp[1],
            resp[1])
        self.log.info("Step 1 : Created a bucket with name %s",
                      self.bucket_name)
        self.log.info(
            "Step 2 : Retrieving bucket location on existing bucket %s",
            self.bucket_name)
        resp = self.s3_test_obj.bucket_location(
            self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            assert_utils.assert_equals(
                resp[1]["LocationConstraint"],
                "default",
                resp[1])
        else:
            assert_utils.assert_equals(
                resp[1]["LocationConstraint"],
                "us-west-2",
                resp[1])
        self.log.info(
            "Step 2 : Retrieved bucket location on existing bucket")
        self.log.info(
            "Verify get bucket location for valid bucket which is present")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_location
    @pytest.mark.tags("TEST-5311")
    @CTFailOn(error_handler)
    def test_get_bkt_loc_bkt_not_present_273(self):
        """verify get bucket location for the bucket which is not present."""
        self.log.info(
            "Verify get bucket location for the bucket which is not present")
        self.log.info(
            "Step 1 : Check the bucket location on non existing bucket %s ",
            self.bucket_name)
        try:
            resp = self.s3_test_obj.bucket_location(self.bucket_name)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert_utils.assert_in("NoSuchBucket", str(
                error.message), error.message)
        self.log.info(
            "Step 1 : Get bucket location on non existing bucket failed with error %s",
            "NoSuchBucket")
        self.log.info(
            "Verify get bucket location for the bucket which is not present")

    # @pytest.mark.parallel This test cause worker crash in bucket policy test suites.
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_location
    @pytest.mark.regression
    @pytest.mark.tags("TEST-7419")
    @CTFailOn(error_handler)
    def test_cross_account_get_bkt_loc_with_permission_274(self):
        """
        Cross account bucket loc.

        Verify for the bucket which is present in account1 and give read permissions
         to account2 and check get bucket location
        """
        self.log.info(
            "STARTED: Verify for the bucket which is present in account1 and give read"
            "permissions to account2 and check get bucket location")
        self.log.info(
            "Creating account1 with name prefix as %s",
            self.account_name1)
        acc1_resp = self.rest_obj.create_s3_account(
            acc_name=self.account_name1, email_id=self.email_id1,
            passwd=self.s3acc_password)
        assert_utils.assert_true(acc1_resp[0], acc1_resp[1])
        s3_acl_obj_1 = s3_acl_test_lib.S3AclTestLib(
            endpoint_url=S3_CFG['s3_url'],
            access_key=acc1_resp[1]["access_key"],
            secret_key=acc1_resp[1]["secret_key"])
        self.s3_test_obj = s3_test_lib.S3TestLib(
            access_key=acc1_resp[1]["access_key"],
            secret_key=acc1_resp[1]["secret_key"])
        self.account_list.append(self.account_name1)
        self.log.info("Created account1 with name %s", self.account_name1)
        self.log.info(
            "Creating account2 with name prefix as %s",
            self.account_name2)
        acc2_resp = self.rest_obj.create_s3_account(
            acc_name=self.account_name2, email_id=self.email_id2,
            passwd=self.s3acc_password)
        assert_utils.assert_true(acc2_resp[0], acc2_resp[1])
        self.account_list.append(self.account_name2)
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=acc2_resp[1]["access_key"],
            secret_key=acc2_resp[1]["secret_key"])
        self.log.info("Created account2 with name %s", self.account_name2)
        self.log.info("Step 1 : Creating bucket with name %s and setting read"
                      "permission to account2", self.bucket_name)
        resp = s3_acl_obj_1.create_bucket_with_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(acc1_resp[1]["canonical_id"]),
            grant_read="id={}".format(acc2_resp[1]["canonical_id"]))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1 : Created bucket with name %s and set read"
                      "permission to account2", self.bucket_name)
        self.log.info(
            "Step 2: Verifying get bucket location with account1")
        resp = self.s3_test_obj.bucket_location(self.bucket_name)
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            assert_utils.assert_equals(
                resp[1]["LocationConstraint"],
                "default",
                resp[1])
        else:
            assert_utils.assert_equals(
                resp[1]["LocationConstraint"],
                "us-west-2",
                resp[1])
        self.log.info(
            "Step 2: Verified get bucket location with account1")
        self.log.info(
            "Step 3 : Verifying get bucket location with account2 login")
        resp = s3_obj_2.bucket_location(self.bucket_name)
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            assert_utils.assert_equals(
                resp[1]["LocationConstraint"],
                "default",
                resp[1])
        else:
            assert_utils.assert_equals(
                resp[1]["LocationConstraint"],
                "us-west-2",
                resp[1])
        self.log.info(
            "Step 3 : Verified get bucket location with account2 login")
        self.log.info(
            "ENDED: Verify for the bucket which is present in account1 and give read"
            "permissions to account2 and check get bucket location")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_location
    @pytest.mark.tags("TEST-5312")
    @CTFailOn(error_handler)
    def test_cross_account_get_bkt_loc_275(self):
        """Verify the bucket which is present in account1 and get bucket location in account2."""
        self.log.info(
            "verify for the bucket which is present in account1 "
            "and get bucket location in account2")
        self.log.info(
            "Step 1 : Creating bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(
            self.bucket_name,
            resp[1],
            resp[1])
        self.log.info("Step 1 : Created bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2 : Creating second account to retrieve bucket location")
        resp = self.rest_obj.create_s3_account(
            acc_name=self.account_name1,
            email_id=self.email_id1,
            passwd=self.s3acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.account_list.append(self.account_name1)
        s3_obj_2 = s3_test_lib.S3TestLib(endpoint_url=S3_CFG['s3_url'],
                                         access_key=access_key, secret_key=secret_key)
        self.log.info(
            "Step 2 : Created second account to retrieve bucket location")
        self.log.info(
            "Step 3 : Verifying get bucket location with another account")
        try:
            s3_obj_2.bucket_location(
                self.bucket_name)
        except CTException as error:
            assert_utils.assert_in("AccessDenied", str(
                error.message), error.message)
        self.log.info(
            "Step 3 : Get bucket location with another account is failed"
            " with error %s", "AccessDenied")
        self.log.info(
            "Verify for the bucket which is present in account1 "
            "and get bucket location in account2")
