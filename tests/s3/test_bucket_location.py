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

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils import assert_utils
from libs.s3 import s3_test_lib, iam_test_lib, s3_acl_test_lib

from libs.s3.cortxcli_test_lib import CortxCliTestLib
from config import S3_CFG

class TestBucketLocation:
    """Bucket Location Test suite."""
    cortx_obj = None
    bucket_name = None

    @classmethod
    def setup_class(cls):
        """Setup all the states required for execution of this test suit."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED : Setup operations at test suit level")
        cls.iam_obj = iam_test_lib.IamTestLib()
        cls.s3_obj = s3_test_lib.S3TestLib()
        cls.account_name = "location-acct"
        cls.bucket_prefix = "location-bkt"
        cls.email_id = "@seagate.com"
        cls.s3acc_password = S3_CFG["CliConfig"]["s3_account"]["password"]
        cls.log.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        teardown for cleanup
        """
        self.log.info("STARTED: Setup operations.")
        self.bucket_name = "{}{}".format(
            self.bucket_prefix, str(time.perf_counter()))
        self.cortx_obj = CortxCliTestLib()
        self.log.info("ENDED: Setup operations.")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will perform all cleanup operations.
        This function will delete buckets and accounts created for tests.
        """
        self.log.info("STARTED: Teardown operations.")
        self.log.info("Delete bucket: %s", self.bucket_name)
        resp = self.s3_obj.bucket_list()
        self.log.info("Bucket list: %s", resp)
        if resp:
            pref_list = [each_bucket for each_bucket in resp[1]
                         if self.bucket_prefix in each_bucket]
            if pref_list:
                resp = self.s3_obj.delete_multiple_buckets(pref_list)
                assert_utils.assert_true(resp[0], resp[1])
                self.log.info("Buckets deleted successfully: %s", pref_list)

        accounts = self.cortx_obj.list_accounts_cortxcli()
        accounts = [acc["account_name"]
                    for acc in accounts if self.account_name in acc["account_name"]]
        for acc in accounts:
            self.cortx_obj.delete_account_cortxcli(account_name=acc, password=self.s3acc_password)
        self.log.info("ENDED: Teardown operations.")


    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5310")
    @CTFailOn(error_handler)
    def test_get_bkt_loc_valid_bkt_272(self):
        """Verify get bucket location for valid bucket which is present."""
        self.log.info(
            "Verify get bucket location for valid bucket which is present")
        self.log.info(
            "Step 1 : Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_obj.create_bucket(
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
        resp = self.s3_obj.bucket_location(
            self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
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
            resp = self.s3_obj.bucket_location(
                self.bucket_name)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert "NoSuchBucket" in str(
                error.message), error.message
        self.log.info(
            "Step 1 : Get bucket location on non existing bucket failed with error %s",
            "NoSuchBucket")
        self.log.info(
            "Verify get bucket location for the bucket which is not present")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
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
        accounts_list = list()
        self.log.info(
            "Creating account1 with name prefix as %s",
            self.account_name)
        account1 = "{0}{1}".format(self.account_name, str(time.perf_counter())).replace('.', '_')
        email_id1 = "{0}{1}".format(account1, self.email_id)
        acc1_resp = self.cortx_obj.create_account_cortxcli(
            account_name=account1, account_email=email_id1, password=self.s3acc_password)
        assert_utils.assert_true(acc1_resp[0], acc1_resp[1])
        accounts_list.append(account1)

        s3_acl_obj_1 = s3_acl_test_lib.S3AclTestLib(
            access_key=acc1_resp[1]["access_key"],
            secret_key=acc1_resp[1]["secret_key"])

        s3_obj_1 = s3_test_lib.S3TestLib(
            access_key=acc1_resp[1]["access_key"],
            secret_key=acc1_resp[1]["secret_key"])
        self.log.info("Created account1 with name %s", account1)
        self.log.info(
            "Creating account2 with name prefix as %s",
            self.account_name)

        account2 = "{}{}".format(self.account_name, str(time.perf_counter())).replace('.', '_')
        email_id2 = "{}{}".format(account2, self.email_id)
        acc2_resp = self.cortx_obj.create_account_cortxcli(
            account_name=account2, account_email=email_id2, password=self.s3acc_password)
        assert_utils.assert_true(acc2_resp[0], acc2_resp[1])
        accounts_list.append(account2)

        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=acc2_resp[1]["access_key"],
            secret_key=acc2_resp[1]["secret_key"])
        self.log.info("Created account2 with name %s", account2)

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
        resp = s3_obj_1.bucket_location(self.bucket_name)
        assert_utils.assert_equals(
            "us-west-2",
            resp[1]["LocationConstraint"],
            resp[1])
        self.log.info(
            "Step 2: Verified get bucket location with account1")

        self.log.info(
            "Step 3 : Verifying get bucket location with account2 login")
        resp = s3_obj_2.bucket_location(self.bucket_name)
        assert_utils.assert_equals(
            "us-west-2",
            resp[1]["LocationConstraint"],
            resp[1])
        self.log.info(
            "Step 3 : Verified get bucket location with account2 login")
        # Cleanup activity
        self.log.info("Step 4: Performing cleanup.")
        if s3_obj_1:
            res_bkt = s3_obj_1.bucket_list()
            for bkt in res_bkt[1]:
                s3_obj_1.delete_bucket(bkt)

        for acc in accounts_list:
            self.cortx_obj.delete_account_cortxcli(
                account_name=acc, password=self.s3acc_password)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Verify for the bucket which is present in account1 and give read"
            "permissions to account2 and check get bucket location")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
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
        resp = self.s3_obj.create_bucket(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(
            self.bucket_name,
            resp[1],
            resp[1])
        self.log.info("Step 1 : Created bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2 : Creating second account to retrieve bucket location")
        account_name = "{}{}".format(
            self.account_name, str(time.perf_counter())).replace('.', '_')
        email_id = "{}{}".format(account_name,
                                 self.email_id)
        resp = self.cortx_obj.create_account_cortxcli(
            account_name=account_name,
            account_email=email_id,
            password=self.s3acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        self.log.info(
            "Step 2 : Created second account to retrieve bucket location")
        self.log.info(
            "Step 3 : Verifying get bucket location with another account")
        try:
            s3_obj_2.bucket_location(
                self.bucket_name)
        except CTException as error:
            assert "AccessDenied" in str(
                error.message), error.message
        self.log.info(
            "Step 3 : Get bucket location with another account is failed"
            " with error %s", "AccessDenied")
        # Cleanup activity
        self.log.info("Deleting account %s", account_name)
        self.cortx_obj.delete_account_cortxcli(
            account_name=account_name, password=self.s3acc_password)
        self.log.info(
            "Verify for the bucket which is present in account1 "
            "and get bucket location in account2")
