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
from config import CMN_CFG
from libs.s3 import s3_test_lib, iam_test_lib, s3_acl_test_lib

LOGGER = logging.getLogger(__name__)

IAM_OBJ = iam_test_lib.IamTestLib()
S3_OBJ = s3_test_lib.S3TestLib()
S3_ACL_OBJ = s3_acl_test_lib.S3AclTestLib()


class TestBucketLocation:
    """Bucket Location Test suite"""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        LOGGER.info("STARTED: setup test suite operations.")
        cls.ldap_user = CMN_CFG["ldap_username"]
        cls.ldap_pwd = CMN_CFG["ldap_passwd"]
        cls.bucket_prefix = "location-bkt"
        cls.account_prefix = "location-acc"
        cls.email_id = "@seagate.com"
        cls.id_str = "id={}"
        cls.s3_obj_1 = None
        cls.bucket_name = None
        cls.account_name = None
        LOGGER.info("ENDED: setup test suite operations.")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        LOGGER.info("STARTED: teardown test suite operations.")
        LOGGER.info("Teardown completed.")
        LOGGER.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        teardown for cleanup
        """
        LOGGER.info("STARTED: Setup operations.")
        self.bucket_name = f"{self.bucket_prefix}{str(time.time())}"
        self.account_name = self.account_prefix
        if self.s3_obj_1:
            res_bkt = self.s3_obj_1.bucket_list()
            for bkt in res_bkt[1]:
                self.s3_obj_1.delete_bucket(bkt)
        resp = S3_OBJ.bucket_list()
        if resp:
            pref_list = [each_bucket for each_bucket in resp[1]
                         if each_bucket.startswith(self.bucket_prefix)]
            if pref_list:
                S3_OBJ.delete_multiple_buckets(pref_list)
        LOGGER.info("ENDED: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test case.
        It will perform all cleanup operations.
        This function will delete buckets and accounts created for tests.
        """
        LOGGER.info("STARTED: Teardown operations.")
        if self.s3_obj_1:
            res_bkt = self.s3_obj_1.bucket_list()
            for bkt in res_bkt[1]:
                self.s3_obj_1.delete_bucket(bkt)
        resp = S3_OBJ.bucket_list()
        if resp:
            pref_list = [each_bucket for each_bucket in resp[1]
                         if each_bucket.startswith(self.bucket_prefix)]
            S3_OBJ.delete_multiple_buckets(pref_list)
        acc_resp = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user,
            self.ldap_pwd)
        acc_list = [each_acc["AccountName"] for each_acc in acc_resp[1]
                    if each_acc[" Email"].startswith(self.account_prefix)]
        LOGGER.info("Deleting account %s", acc_list)
        IAM_OBJ.delete_multiple_accounts(acc_list)
        LOGGER.info("ENDED: Teardown operations.")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5310")
    @CTFailOn(error_handler)
    def test_get_bkt_loc_valid_bkt_272(self):
        """
        Verify get bucket location for valid bucket which is present
        """
        LOGGER.info(
            "Verify get bucket location for valid bucket which is present")
        LOGGER.info(
            "Step 1 : Creating a bucket with name %s",
            self.bucket_name)
        resp = S3_OBJ.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            self.bucket_name,
            resp[1],
            resp[1])
        LOGGER.info("Step 1 : Created a bucket with name %s",
                    self.bucket_name)
        LOGGER.info(
            "Step 2 : Retrieving bucket location on existing bucket %s",
            self.bucket_name)
        resp = S3_OBJ.bucket_location(
            self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            resp[1]["LocationConstraint"],
            "us-west-2",
            resp[1])
        LOGGER.info(
            "Step 2 : Retrieved bucket location on existing bucket")
        LOGGER.info(
            "Verify get bucket location for valid bucket which is present")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5311")
    def test_get_bkt_loc_bkt_not_present_273(self):
        """
        verify get bucket location for the bucket which is not present
        """
        LOGGER.info(
            "Verify get bucket location for the bucket which is not present")
        LOGGER.info(
            "Step 1 : Check the bucket location on non existing bucket %s ",
            self.bucket_name)
        try:
            S3_OBJ.bucket_location(
                self.bucket_name)
        except CTException as error:
            assert "NoSuchBucket" in str(
                error.message), error.message
        LOGGER.info(
            "Step 1 : Get bucket location on non existing bucket failed with error %s",
            "NoSuchBucket")
        LOGGER.info(
            "Verify get bucket location for the bucket which is not present")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7419")
    def test_cross_account_get_bkt_loc_with_permission_274(self):
        """
        Verify for the bucket which is present in account1 and give read permissions
         to account2 and check get bucket location
        """
        LOGGER.info(
            "STARTED: Verify for the bucket which is present in account1 and give read"
            "permissions to account2 and check get bucket location")
        LOGGER.info(
            "Creating account2 with name prefix as %s",
            self.account_name)
        resp = IAM_OBJ.create_multiple_accounts(
            2, self.account_name)
        assert resp[0], resp[1]
        canonical_id_user_1 = resp[1][0][1]["canonical_id"]
        access_key_u1 = resp[1][0][1]["access_key"]
        secret_key_u1 = resp[1][0][1]["secret_key"]
        canonical_id_user_2 = resp[1][1][1]["canonical_id"]
        access_key_u2 = resp[1][1][1]["access_key"]
        secret_key_u2 = resp[1][1][1]["secret_key"]
        s3_acl_obj_1 = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        self.s3_obj_1 = s3_test_lib.S3TestLib(
            access_key=access_key_u1, secret_key=secret_key_u1)
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=access_key_u2, secret_key=secret_key_u2)
        LOGGER.info(
            "Created account2 with name %s", self.account_name)
        LOGGER.info("Step 1 : Creating bucket with name %s and setting read"
                    "permission to account2", self.bucket_name)
        resp = s3_acl_obj_1.create_bucket_with_acl(
            bucket_name=self.bucket_name,
            grant_full_control=self.id_str.format(canonical_id_user_1),
            grant_read=self.id_str.format(canonical_id_user_2))
        assert resp[0], resp[1]
        LOGGER.info("Step 1 : Created bucket with name %s and set read"
                    "permission to account2", self.bucket_name)
        LOGGER.info(
            "Step 2: Verifying get bucket location with account1")
        resp = self.s3_obj_1.bucket_location(self.bucket_name)
        assert_utils.assert_equals(
            "us-west-2",
            resp[1]["LocationConstraint"],
            resp[1])
        LOGGER.info(
            "Step 2: Verified get bucket location with account1")
        LOGGER.info(
            "Step 3 : Verifying get bucket location with account2 login")
        resp = s3_obj_2.bucket_location(self.bucket_name)
        assert_utils.assert_equals(
            "us-west-2",
            resp[1]["LocationConstraint"],
            resp[1])
        LOGGER.info(
            "Step 3 : Verified get bucket location with account2 login")
        # # Performing cleanup using account1
        # self.s3_obj_1.delete_bucket(self.bucket_name)
        LOGGER.info(
            "ENDED: Verify for the bucket which is present in account1 and give read"
            "permissions to account2 and check get bucket location")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5312")
    def test_cross_account_get_bkt_loc_275(self):
        """
        Verify for the bucket which is present in account1 and get bucket location in account2
        """
        LOGGER.info(
            "verify for the bucket which is present in account1 "
            "and get bucket location in account2")
        LOGGER.info("Step 1 : Creating bucket with name %s", self.bucket_name)
        resp = S3_OBJ.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            self.bucket_name,
            resp[1],
            resp[1])
        LOGGER.info("Step 1 : Created bucket with name %s", self.bucket_name)
        LOGGER.info(
            "Step 2 : Creating second account to retrieve bucket location")
        account_name = "{}{}".format(
            self.account_name, str(time.time()))
        email_id = "{}{}".format(account_name,
                                 self.email_id)
        resp = IAM_OBJ.create_account_s3iamcli(
            account_name,
            email_id,
            self.ldap_user,
            self.ldap_pwd)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_obj_2 = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        LOGGER.info(
            "Step 2 : Created second account to retrieve bucket location")
        LOGGER.info(
            "Step 3 : Verifying get bucket location with another account")
        try:
            s3_obj_2.bucket_location(
                self.bucket_name)
        except CTException as error:
            assert "AccessDenied" in str(
                error.message), error.message
        LOGGER.info(
            "Step 3 : Get bucket location with another account is failed"
            " with error %s", "AccessDenied")
        # Cleanup activity
        LOGGER.info("Deleting account %s", account_name)
        resp = IAM_OBJ.delete_account_s3iamcli(
            account_name, access_key, secret_key, force=True)
        assert resp[0], resp[1]
        LOGGER.info(
            "Verify for the bucket which is present in account1 "
            "and get bucket location in account2")
