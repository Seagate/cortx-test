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

"""This file contains test related to Bucket ACL (Access Control Lists)."""

import os
import copy
import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_PATH
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils import s3_utils
from config.s3 import S3_CFG
from libs.s3 import s3_test_lib
from libs.s3 import iam_test_lib
from libs.s3 import s3_acl_test_lib
from libs.s3.s3_acl_test_lib import S3AclTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations


class TestBucketACL:
    """Bucket ACL Test suite."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Summary: Function will be invoked prior to each test case.

        Description: It will perform all prerequisite and cleanup test.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: setup test operations.")
        self.s3_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.iam_obj = iam_test_lib.IamTestLib(endpoint_url=S3_CFG["iam_url"])
        self.acl_obj = s3_acl_test_lib.S3AclTestLib(
            endpoint_url=S3_CFG["s3_url"])
        self.test_file = "testfile{}.txt"
        self.s3acc_password = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.test_dir_path = os.path.join(TEST_DATA_PATH, "TestBucketACL")
        if not system_utils.path_exists(self.test_dir_path):
            resp = system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", resp)
        self.log.info("Test data path: %s", self.test_dir_path)
        self.test_file_path = os.path.join(
            self.test_dir_path, self.test_file.format(time.perf_counter()))
        self.bucket_name = "{}-{}".format("aclbucket", time.perf_counter_ns())
        self.account_prefix = "acltestaccn_{}"
        self.account_name = "{}{}".format(
            "acltestaccn1", time.perf_counter_ns())
        self.email_id = "{}{}".format(self.account_name, "@seagate.com")
        self.account_name1 = "{}{}".format(
            "acltestaccn2", time.perf_counter_ns())
        self.email_id1 = "{}{}".format(self.account_name, "@seagate.com")
        self.rest_obj = S3AccountOperations()
        self.log.info("Bucket name: %s", self.bucket_name)
        self.account_list = []
        self.log.info("ENDED: Setup test operations")
        yield
        self.log.info("STARTED: Teardown test operations")
        if system_utils.path_exists(self.test_file_path):
            resp = system_utils.remove_file(self.test_file_path)
            self.log.info(
                "removed path: %s, resp: %s",
                self.test_file_path,
                resp)
        self.log.info("Deleting buckets in default account")
        resp = self.s3_obj.bucket_list()
        self.log.info(resp)
        pref_list = [each_bucket for each_bucket in resp[1]
                     if each_bucket == self.bucket_name]
        if pref_list:
            for bucket in pref_list:
                self.acl_obj.put_bucket_acl(bucket, acl="private")
            resp = self.s3_obj.delete_multiple_buckets(pref_list)
            self.log.info(resp)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Deleted buckets in default account")
        self.log.info("Account list: %s", self.account_list)
        self.delete_accounts(self.account_list)
        del self.rest_obj
        self.log.info("ENDED: Teardown test operations")

    def delete_accounts(self, accounts):
        """It will clean up resources which are getting created during test suite setup."""
        self.log.debug(accounts)
        for acc in accounts:
            self.log.debug("Deleting %s account", acc)
            resp = self.rest_obj.delete_s3_account(acc)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Deleted %s account successfully", acc)

    def create_bucket_with_acl_and_grant_permissions(
            self, bucket_name, acl, grant="grant-read", error_msg=None):
        """Helper method for Create bucket with given acl and grant permissions."""
        self.log.info("Create bucket with given acl and grant permissions.")
        self.log.info("Bucket name: %s, acl: %s, grant: %s, error_msg: %s",
                      bucket_name, acl, grant, error_msg)
        resp = self.rest_obj.create_s3_account(
            self.account_name, self.email_id, self.s3acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        canonical_id = resp[1]["canonical_id"]
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(access_key=access_key, secret_key=secret_key)
        self.account_list.append(self.account_name)
        try:
            if grant == "grant-read":
                resp = s3_obj_acl.create_bucket_with_acl(
                    bucket_name=bucket_name, acl=acl, grant_read="id={}".format(canonical_id))
            elif grant == "grant-full-control":
                resp = s3_obj_acl.create_bucket_with_acl(
                    bucket_name=bucket_name, acl=acl, grant_full_control="id={}".format(
                        canonical_id))
            elif grant == "grant-write":
                resp = s3_obj_acl.create_bucket_with_acl(
                    bucket_name=bucket_name, acl=acl, grant_write="id={}".format(canonical_id))
            elif grant == "grant-read-acp":
                resp = s3_obj_acl.create_bucket_with_acl(
                    bucket_name=bucket_name, acl=acl, grant_read_acp="id={}".format(canonical_id))
            elif grant == "grant-write-acp":
                resp = s3_obj_acl.create_bucket_with_acl(
                    bucket_name=bucket_name, acl=acl, grant_write_acp="id={}".format(canonical_id))
            else:
                assert_utils.assert_true(False, f"Incorrect options grant: {grant}")
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert error_msg in str(error.message), error.message

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.sanity
    @pytest.mark.tags("TEST-5717")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3012(self):
        """verify Get Bucket ACL of existing Bucket."""
        self.log.info("verify Get Bucket ACL of existing Bucket")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_utils.poll(self.acl_obj.get_bucket_acl,
                             self.bucket_name,
                             condition="{}[1][1][0]['Permission']=='FULL_CONTROL'")
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1][1][0]["Permission"], "FULL_CONTROL", resp[1])
        self.log.info("verify Get Bucket ACL of existing Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5719")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3013(self):
        """verify Get Bucket ACL of non existing Bucket."""
        self.log.info("verify Get Bucket ACL of non existing Bucket")
        try:
            resp = self.acl_obj.get_bucket_acl(self.bucket_name)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert "NoSuchBucket" in str(
                error.message), error.message
        self.log.info("verify Get Bucket ACL of non existing Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5712")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3014(self):
        """verify Get Bucket ACL of an empty Bucket."""
        self.log.info("verify Get Bucket ACL of an empty Bucket")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info("verify Get Bucket ACL of an empty Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5718")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3015(self):
        """verify Get Bucket ACL of an existing Bucket having objects."""
        self.log.info(
            "verify Get Bucket ACL of an existing Bucket having objects")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp)
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        system_utils.create_file(self.test_file_path,
                                 1)
        resp = self.s3_obj.object_upload(self.bucket_name,
                                         self.test_file,
                                         self.test_file_path)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info(
            "verify Get Bucket ACL of an existing Bucket having objects")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5713")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3016(self):
        """Verify Get Bucket ACL without Bucket name."""
        self.log.info("Verify Get Bucket ACL without Bucket name")
        try:
            resp = self.acl_obj.get_bucket_acl(None)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert "Required parameter bucket_name not set" in str(
                error.message), error.message
        self.log.info("Verify Get Bucket ACL without Bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5720")
    @CTFailOn(error_handler)
    def test_delete_and_verify_bucket_acl_3017(self):
        """Delete Bucket and verify Bucket ACL."""
        self.log.info("Delete Bucket and verify Bucket ACL")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.delete_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        try:
            resp = self.acl_obj.get_bucket_acl(self.bucket_name)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert "NoSuchBucket" in str(
                error.message), error.message
        self.log.info("Delete Bucket and verify Bucket ACL")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5716")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3018(self):
        """verify Get Bucket ACL of existing Bucket with associated Account credentials."""
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with associated Account credentials")
        resp = self.rest_obj.create_s3_account(
            self.account_name, self.email_id, self.s3acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.account_list.append(self.account_name)
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_obj_acl = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        resp = s3_obj_acl.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj_acl.bucket_list()
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert self.bucket_name in str(resp[1]), resp[1]
        resp = self.acl_obj.get_bucket_acl_using_iam_credentials(
            access_key, secret_key, self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        # Cleanup
        resp = s3_obj_acl.delete_bucket(self.bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with associated Account credentials")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5715")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3019(self):
        """verify Get Bucket ACL of existing Bucket with different Account credentials."""
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with different Account credentials")
        access_keys = []
        secret_keys = []
        for _ in range(2):
            account = self.account_prefix.format(time.perf_counter_ns())
            email = "{}@seagate.com".format(account)
            resp = self.rest_obj.create_s3_account(
                account, email, self.s3acc_password)
            assert_utils.assert_true(resp[0], resp[1])
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            self.account_list.append(account)
        s3_obj_acl = s3_test_lib.S3TestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        resp = s3_obj_acl.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj_acl.bucket_list()
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert self.bucket_name in resp[1], resp[1]
        try:
            resp = self.acl_obj.get_bucket_acl_using_iam_credentials(
                access_keys[1], secret_keys[1], self.bucket_name)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert "AccessDenied" in str(error.message), error.message
        resp = s3_obj_acl.delete_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with different Account credentials")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5714")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3020(self):
        """verify Get Bucket ACL of existing Bucket with IAM User credentials."""
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with IAM User credentials")
        user_name = "user10016"
        access_keys = []
        secret_keys = []
        for _ in range(2):
            account = self.account_prefix.format(time.perf_counter_ns())
            email = "{}@seagate.com".format(account)
            resp = self.rest_obj.create_s3_account(
                account, email, self.s3acc_password)
            assert_utils.assert_true(resp[0], resp[1])
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            self.account_list.append(account)
        err_message = "AccessDenied"
        s3_obj_acl = s3_test_lib.S3TestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        resp = s3_obj_acl.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj_acl.bucket_list()
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert self.bucket_name in resp[1], resp[1]
        iam_obj_acl = iam_test_lib.IamTestLib(
            access_key=access_keys[1],
            secret_key=secret_keys[1])
        resp = iam_obj_acl.create_user(user_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = iam_obj_acl.create_access_key(user_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        access_key_user = resp[1]["AccessKey"]["AccessKeyId"]
        secret_key_user = resp[1]["AccessKey"]["SecretAccessKey"]
        try:
            resp = self.acl_obj.get_bucket_acl_using_iam_credentials(
                access_key_user, secret_key_user, self.bucket_name)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert err_message in str(error.message), error.message
        resp = s3_obj_acl.delete_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = iam_obj_acl.delete_users_with_access_key([user_name])
        assert_utils.assert_true(resp, f"Failed to delete iam user: {user_name}")
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with IAM User credentials")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.sanity
    @pytest.mark.tags("TEST-5728")
    @CTFailOn(error_handler)
    def test_add_canned_acl_bucket_3527(self):
        """Add canned ACL bucket-owner-full-control along with READ ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with READ ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket_name,
            "bucket-owner-full-control",
            error_msg="Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with READ ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5727")
    @CTFailOn(error_handler)
    def test_add_canned_acl_bucket_3528(self):
        """Add canned ACL bucket-owner-read along with READ ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-read along with READ ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket_name,
            "bucket-owner-read",
            error_msg="Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL bucket-owner-read along with READ ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5736")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3529(self):
        """Add canned ACL "private" along with "READ" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'private' along with 'READ' ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket_name,
            "private",
            error_msg="Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'private' along with 'READ' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5737")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3530(self):
        """Add canned ACL "private" along with "FULL_CONTROL" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'private' along with 'FULL_CONTROL' ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket_name,
            "private",
            "grant-full-control",
            "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'private' along with 'FULL_CONTROL' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5732")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_3531(self):
        """Add canned ACL "public-read" along with "READ_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'public-read' along with 'READ_ACP' ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket_name,
            "public-read",
            "grant-read-acp",
            "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'public-read' along with 'READ_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5731")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_3532(self):
        """Add canned ACL "public-read" along with "WRITE_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'public-read' along with 'WRITE_ACP' ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket_name,
            "public-read",
            "grant-write-acp",
            "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'public-read' along with 'WRITE_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5729")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_write_3533(self):
        """Add canned ACL 'public-read-write' along with "WRITE_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'public-read-write' along with 'WRITE_ACP' ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket_name,
            "public-read-write",
            "grant-write-acp",
            "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'public-read-write' along with 'WRITE_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5730")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_write_3534(self):
        """Add canned ACL 'public-read-write' along with "FULL_CONTROL" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'public-read-write' along with 'FULL_CONTROL' ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket_name,
            "public-read-write",
            "grant-full-control",
            "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'public-read-write' along with 'FULL_CONTROL' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5739")
    @CTFailOn(error_handler)
    def test_add_canned_acl_authenticate_read_3535(self):
        """Add canned ACL 'authenticate-read' along with "READ" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'authenticate-read' along with 'READ' ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket_name,
            "authenticated-read",
            error_msg="Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'authenticate-read' along with 'READ' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5738")
    @CTFailOn(error_handler)
    def test_add_canned_acl_authenticate_read_3536(self):
        """Add canned ACL 'authenticate-read' along with "READ_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'authenticate-read' along with 'READ_ACP' ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket_name,
            "authenticated-read",
            "grant-read-acp",
            error_msg="Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'authenticate-read' along with 'READ_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5735")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3537(self):
        """
        Add canned ACL "private" as a request header along with FULL_CONTROL.

        ACL grant permission as request body
        """
        self.log.info(
            "Add canned ACL 'private' as a request header along with FULL_CONTROL"
            " ACL grant permission as request body")
        resp = self.rest_obj.create_s3_account(
            self.account_name, self.email_id, self.s3acc_password)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.account_list.append(self.account_name)
        s3_test = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = s3_test.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        resp = s3_obj_acl.get_bucket_acl(bucket_name=self.bucket_name)
        self.log.info(resp)
        newresp = {"Owner": resp[1][0], "Grants": resp[1][1]}
        self.log.info(
            "New dict to pass ACP with permission private:%s", newresp)
        newresp["Grants"][0]["Permission"] = "FULL_CONTROL"
        try:
            resp = s3_obj_acl.put_bucket_acl(
                bucket_name=self.bucket_name,
                acl="private",
                access_control_policy=newresp)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert "UnexpectedContent" in error.message, error.message
        self.log.info("Cleanup activity")
        self.log.info("Deleting a bucket %s", self.bucket_name)
        resp = s3_test.delete_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp)
        self.log.info(
            "Add canned ACL 'private' as a request header along with FULL_CONTROL"
            " ACL grant permission as request body")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5733")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3538(self):
        """
        Add canned ACL "private" in request body along with "FULL_CONTROL".

        ACL grant permission in request header.
        """
        self.log.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request header")
        resp = self.rest_obj.create_s3_account(
            self.account_name, self.email_id, self.s3acc_password)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.account_list.append(self.account_name)
        s3_test = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = s3_test.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        resp = s3_obj_acl.get_bucket_acl(bucket_name=self.bucket_name)
        self.log.info(resp)
        newresp = {"Owner": resp[1][0], "Grants": resp[1][1]}
        self.log.info(
            "New dict to pass ACP with permission private:%s", newresp)
        newresp["Grants"][0]["Permission"] = "private"
        try:
            resp = s3_obj_acl.put_bucket_acl(
                bucket_name=self.bucket_name,
                acl="FULL_CONTROL",
                access_control_policy=newresp)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert "BadRequest" in error.message, error.message
        self.log.info("Cleanup activity")
        self.log.info("Deleting a bucket %s", self.bucket_name)
        resp = s3_test.delete_bucket(self.bucket_name, force=True)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp)
        self.log.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request header")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5734")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3539(self):
        """
        Add canned ACL "private" in request body along with "FULL_CONTROL".

        ACL grant permission in request body.
        """
        self.log.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request body")
        resp = self.rest_obj.create_s3_account(self.account_name,
                                               self.email_id,
                                               self.s3acc_password)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        canonical_id = resp[1]["canonical_id"]
        self.account_list.append(self.account_name)
        s3_test = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = s3_test.create_bucket(bucket_name=self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        resp = s3_obj_acl.get_bucket_acl(bucket_name=self.bucket_name)
        self.log.info(resp)
        newresp = {"Owner": resp[1][0], "Grants": resp[1][1]}
        self.log.info(
            "New dict to pass ACP with permission private:%s", newresp)
        newresp["Grants"][0]["Permission"] = "private"
        new_grant = {
            "Grantee": {
                "ID": canonical_id,
                "Type": "CanonicalUser",
            },
            "Permission": "FULL_CONTROL",
        }
        # If we don"t want to modify the original ACL variable, then we
        # must do a deepcopy
        modified_acl = copy.deepcopy(newresp)
        modified_acl["Grants"].append(new_grant)
        self.log.info(
            "ACP with permission private and Full control:%s", modified_acl)
        try:
            resp = s3_obj_acl.put_bucket_acl(
                bucket_name=self.bucket_name,
                access_control_policy=newresp)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert "InvalidACL" in error.message, error.message
        self.log.info("Cleanup activity")
        self.log.info("Deleting a bucket %s", self.bucket_name)
        resp = s3_test.delete_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp)
        self.log.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request body")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5726")
    @CTFailOn(error_handler)
    def test_add_canned_acl_authenticated_read_3577(self):
        """
        Apply authenticated-read canned ACL to account2.

        Execute head-bucket from account2 on a bucket. Bucket belongs to account1.
        """
        self.log.info(
            "Apply authenticated-read canned ACL to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")
        access_keys = []
        secret_keys = []
        canonical_ids = []
        for _ in range(2):
            account = self.account_prefix.format(time.perf_counter_ns())
            email = "{}@seagate.com".format(account)
            resp = self.rest_obj.create_s3_account(account,
                                                   email,
                                                   self.s3acc_password)
            assert_utils.assert_true(resp[0], resp[1])
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            canonical_ids.append(resp[1]["canonical_id"])
            self.account_list.append(account)
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        acl_obj1 = s3_acl_test_lib.S3AclTestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=access_keys[1],
            secret_key=secret_keys[1])
        self.log.info("Creating new bucket from first account")
        resp = s3_obj1.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_equals(
            resp[1]["BucketName"],
            self.bucket_name,
            resp[1])
        self.log.info("Performing authenticated read acl")
        resp = acl_obj1.put_bucket_acl(
            self.bucket_name, acl="authenticated-read")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(
            access_keys[0], secret_keys[0], self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        print("aa {}".format(resp))
        assert "READ" in resp[1][1][1]["Permission"], resp[1]
        self.log.info(
            "Performing head bucket with second account credentials")
        resp = s3_obj2.head_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(
            resp[1]["BucketName"],
            self.bucket_name,
            resp[1])
        self.log.info("Deleting bucket")
        resp = s3_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Apply authenticated-read canned ACL to account2 and execute "
            "head-bucket from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5724")
    @CTFailOn(error_handler)
    def test_apply_private_canned_acl_3578(self):
        """
        Summary: Apply private canned ACL to account2 and execute head-bucket.

        Description: Apply private canned ACL to account2 and execute head-bucket
        from account2 on a bucket. Bucket belongs to account1
        """
        self.log.info(
            "Apply private canned ACL to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")
        access_keys = []
        secret_keys = []
        canonical_ids = []
        for _ in range(2):
            account = self.account_prefix.format(time.perf_counter_ns())
            email = "{}@seagate.com".format(account)
            resp = self.rest_obj.create_s3_account(
                account, email, self.s3acc_password)
            assert_utils.assert_true(resp[0], resp[1])
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            canonical_ids.append(resp[1]["canonical_id"])
            self.account_list.append(account)
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        acl_obj1 = s3_acl_test_lib.S3AclTestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=access_keys[1],
            secret_key=secret_keys[1])
        self.log.info("Creating new bucket from first account")
        resp = s3_obj1.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_equals(
            resp[1]["BucketName"],
            self.bucket_name,
            resp[1])
        self.log.info("Performing authenticated read acl")
        resp = acl_obj1.put_bucket_acl(
            self.bucket_name, acl="private")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(
            access_keys[0], secret_keys[0], self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Performing head bucket with second account credentials")
        try:
            resp = s3_obj2.head_bucket(self.bucket_name)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert "Forbidden" in error.message, error.message
        self.log.info("Deleting bucket")
        resp = s3_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Apply private canned ACL to account2 and execute "
            "head-bucket from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5722")
    @CTFailOn(error_handler)
    def test_grant_read_permission_acl_3579(self):
        """
        Grant read permission to account2 and execute head-bucket.

        from account2 on a bucket. Bucket belongs to account1
        """
        self.log.info(
            "Grant read permission to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")
        access_keys = []
        secret_keys = []
        canonical_ids = []
        account_name = []
        for _ in range(2):
            account = self.account_prefix.format(time.perf_counter_ns())
            email = "{}@seagate.com".format(account)
            resp = self.rest_obj.create_s3_account(
                account, email, self.s3acc_password)
            assert_utils.assert_true(resp[0], resp[1])
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            canonical_ids.append(resp[1]["canonical_id"])
            self.account_list.append(account)
            account_name.append(account)
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        acl_obj1 = s3_acl_test_lib.S3AclTestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=access_keys[1],
            secret_key=secret_keys[1])
        self.log.info("Creating new bucket from first account")
        resp = s3_obj1.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        self.log.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_equals(
            resp[1]["BucketName"],
            self.bucket_name,
            resp[1])
        self.log.info("Performing grant read permission to second account")
        resp = acl_obj1.put_bucket_acl(
            self.bucket_name,
            grant_read="{}{}".format(
                "id=",
                canonical_ids[1]))
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(
            access_keys[0], secret_keys[0], self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_equals(
            resp[1][1][0]["Grantee"]["DisplayName"],
            account_name[1],
            resp[1])
        assert_utils.assert_equals(
            "READ",
            resp[1][1][0]["Permission"],
            resp[1])
        self.log.info(
            "Performing head bucket with second account credentials")
        resp = s3_obj2.head_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_equals(
            resp[1]["BucketName"],
            self.bucket_name,
            resp[1])
        acl_obj1.put_bucket_acl(
            self.bucket_name,
            acl="private")
        self.log.info("Deleting bucket")
        resp = s3_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Grant read permission to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.sanity
    @pytest.mark.tags("TEST-5721")
    @CTFailOn(error_handler)
    def test_perform_head_bucket_acl_3580(self):
        """Perform a head bucket on a bucket."""
        self.log.info("Perform a head bucket on a bucket")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        resp = self.s3_obj.head_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(
            resp[1]["BucketName"],
            self.bucket_name,
            resp[1])
        self.log.info("Perform a head bucket on a bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5723")
    @CTFailOn(error_handler)
    def test_create_verify_default_acl_3581(self):
        """Create a bucket and verify default ACL."""
        self.log.info("Create a bucket and verify default ACL")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket_name, resp[1])
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info("Create a bucket and verify default ACL")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-8027")
    @CTFailOn(error_handler)
    def test_put_get_bucket_acl_312(self):
        """put bucket in account1 and get-bucket-acl for that bucket."""
        self.log.info(
            "STARTED: put bucket in account1 and get-bucket-acl for that bucket")
        self.log.info("Step 1: Creating bucket: %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Bucket: %s created", self.bucket_name)
        self.log.info("Step 2: Retrieving bucket acl attributes")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Bucket ACL was verified")
        self.log.info(
            "ENDED: put bucket in account1 and get-bucket-acl for that bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-8029")
    @CTFailOn(error_handler)
    def test_put_get_bucket_acl_313(self):
        """acc1: put bucket, acc2: no permissions or canned acl, get-bucket-acl details."""
        self.log.info(
            "STARTED:acc1: put bucket, acc2: no permissions or canned acl, get-bucket-acl details")
        self.log.info("Step 1: Creating bucket: %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Bucket : %s created", self.bucket_name)
        create_acc = self.rest_obj.create_s3_account(
            self.account_name1, self.email_id1, self.s3acc_password)
        assert create_acc[0], create_acc[1]
        acl_test_2 = S3AclTestLib(
            access_key=create_acc[1]["access_key"],
            secret_key=create_acc[1]["secret_key"])
        self.account_list.append(self.account_name1)
        self.log.info(
            "Step 2: Retrieving bucket acl attributes using account 2")
        try:
            resp = acl_test_2.get_bucket_acl(self.bucket_name)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert "AccessDenied" in error.message, error.message
            self.log.info(
                "Step 2: retrieving bucket acl using account 2 failed with error %s",
                "AccessDenied")
        self.log.info(
            "ENDED:acc1: put bucket, acc2: no permissions or canned acl, get-bucket-acl details")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-8030")
    @CTFailOn(error_handler)
    def test_put_get_bucket_acl_431(self):
        """acc1 -put bucket, acc2- give read-acp permissions,acc1- get-bucket-acl."""
        self.log.info(
            "STARTED:acc1 -put bucket, acc2- give read-acp permissions,acc1-get-bucket-acl")
        self.log.info("Step 1: Creating bucket: %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Bucket : %s is created", self.bucket_name)
        create_acc = self.rest_obj.create_s3_account(
            self.account_name1, self.email_id1, self.s3acc_password)
        assert create_acc[0], create_acc[1]
        cannonical_id = create_acc[1]["canonical_id"]
        acl_test_2 = S3AclTestLib(
            access_key=create_acc[1]["access_key"],
            secret_key=create_acc[1]["secret_key"])
        self.account_list.append(self.account_name1)
        self.log.info("Step 2: Performing authenticated read acp")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name, grant_read_acp="id={}".format(cannonical_id))
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2:Bucket with read ACP permission was set for acc2")
        self.log.info("Step 3: Retrieving bucket acl attributes")
        resp = acl_test_2.get_bucket_acl(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Bucket ACL was verified")
        self.log.info(
            "ENDED:acc1 -put bucket, acc2- give read-acp permissions,acc1- get-bucket-acl")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-8712")
    @CTFailOn(error_handler)
    def test_full_control_acl_6423(self):
        """Test full-control on bucket to cross accnt and test delete bucket from owner account."""
        self.log.info(
            "STARTED: Test full-control on bucket to cross account and test delete")
        create_acc = self.rest_obj.create_s3_account(
            self.account_name, self.email_id, self.s3acc_password)
        assert create_acc[0], create_acc[1]
        cannonical_id = create_acc[1]["canonical_id"]
        self.account_list.append(self.account_name)
        self.log.info("Step 1: Creating bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created a bucket with name %s",
            self.bucket_name)
        self.log.info("Step 2: Verifying that bucket is created")
        resp = self.s3_obj.bucket_list()
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert self.bucket_name in resp[1]
        self.log.info("Step 2: Verified that bucket is created")
        self.log.info(
            "Step 3:Performing put bucket acl for bucket %s for full control",
            self.bucket_name)
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name, grant_full_control="id={}".format(cannonical_id))
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3:Performed put bucket, bucket %s for account 2",
            self.bucket_name)
        self.log.info(
            "Step 4: Retrieving acl of a bucket %s",
            self.bucket_name)
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Retrieved acl of a bucket %s", self.bucket_name)
        self.log.info("Step 5: Deleting a bucket %s", self.bucket_name)
        resp = self.s3_obj.delete_bucket(self.bucket_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Deleted a bucket %s", self.bucket_name)
        self.log.info("Step 6: Verifying that bucket is deleted")
        resp = self.s3_obj.bucket_list()
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert self.bucket_name not in resp[1], resp[1]
        self.log.info("Step 6: Verified that bucket is deleted")
        self.log.info(
            "ENDED: Test full-control on bucket to cross account and test delete")
