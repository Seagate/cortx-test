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

"""This file contains test related to Bucket ACL (Access Control Lists)."""

import copy
import logging
import os
from time import perf_counter_ns

import pytest

from commons import error_messages as err_msg
from commons.exceptions import CTException
from commons.params import TEST_DATA_PATH
from commons.utils import assert_utils
from commons.utils import s3_utils
from commons.utils import system_utils
from config.s3 import S3_CFG
from libs.s3 import iam_test_lib
from libs.s3 import s3_acl_test_lib
from libs.s3 import s3_test_lib
from libs.s3.s3_acl_test_lib import S3AclTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations


# pylint: disable-msg=too-many-public-methods
class TestBucketACL:
    """Bucket ACL Test suite."""

    log = logging.getLogger(__name__)

    @classmethod
    def setup_class(cls):
        """
        Setup_class will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log.info("STARTED: setup test suite operations.")
        cls.s3_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.iam_obj = iam_test_lib.IamTestLib(endpoint_url=S3_CFG["iam_url"])
        cls.acl_obj = s3_acl_test_lib.S3AclTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.s3_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        cls.test_file = cls.test_file_path = cls.test_dir_path = None
        cls.account = cls.account1 = cls.rest_obj = None
        cls.account_list = []
        cls.account_prefix = "acltestaccn_{}"
        cls.bucket = "aclbucket-{}"
        cls.account_prefix = "acltestaccn{}"
        cls.email_prefix = "{}@seagate.com"
        cls.log.info("ENDED: setup test suite operations.")

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Summary: Function will be invoked prior to each test case.

        Description: It will perform all prerequisite and cleanup test.
        """
        self.log.info("STARTED: setup test operations.")
        self.test_file = f"testfile{perf_counter_ns()}.txt"
        self.test_dir_path = os.path.join(TEST_DATA_PATH, "TestBucketACL")
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
        self.log.info("Test data path: %s", self.test_dir_path)
        self.test_file_path = os.path.join(self.test_dir_path, self.test_file)
        self.bucket = f"aclbucket{perf_counter_ns()}"
        self.account = f"{self.account_prefix}1{perf_counter_ns()}"
        self.account1 = f"{self.account_prefix}2{perf_counter_ns()}"
        self.rest_obj = S3AccountOperations()
        self.log.info("ENDED: Setup test operations")
        yield
        self.log.info("STARTED: Teardown test operations")
        if system_utils.path_exists(self.test_file_path):
            resp = system_utils.remove_file(self.test_file_path)
            self.log.info("removed path: %s, resp: %s", self.test_file_path, resp)
        self.log.info("Deleting buckets in default account")
        resp = self.s3_obj.bucket_list()
        self.log.info(resp)
        pref_list = [each_bucket for each_bucket in resp[1] if each_bucket == self.bucket]
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
        for acc in list(accounts):
            self.log.debug("Deleting %s account", acc)
            resp = self.rest_obj.delete_s3_account(acc)
            assert_utils.assert_true(resp[0], resp[1])
            accounts.remove(acc)
            self.log.info("Deleted %s account successfully", acc)

    def create_bucket_with_acl_and_grant_permissions(
            self, bucket, acl, grant="grant-read", error_msg=None):
        """Helper method for Create bucket with given acl and grant permissions."""
        self.log.info("Create bucket with given acl and grant permissions.")
        self.log.info("Bucket name: %s, acl: %s, grant: %s, error_msg: %s",
                      bucket, acl, grant, error_msg)
        resp = self.rest_obj.create_s3_account(self.account, self.email_prefix.format(
            self.account), self.s3_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        access_key, secret_key = resp[1]["access_key"], resp[1]["secret_key"]
        canonical_id = resp[1]["canonical_id"]
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(access_key=access_key, secret_key=secret_key)
        self.account_list.append(self.account)
        try:
            if grant == "grant-read":
                resp = s3_obj_acl.create_bucket_with_acl(
                    bucket_name=bucket, acl=acl, grant_read=f"id={canonical_id}")
            elif grant == "grant-full-control":
                resp = s3_obj_acl.create_bucket_with_acl(
                    bucket_name=bucket, acl=acl, grant_full_control=f"id={canonical_id}")
            elif grant == "grant-write":
                resp = s3_obj_acl.create_bucket_with_acl(
                    bucket_name=bucket, acl=acl, grant_write=f"id={canonical_id}")
            elif grant == "grant-read-acp":
                resp = s3_obj_acl.create_bucket_with_acl(
                    bucket_name=bucket, acl=acl, grant_read_acp=f"id={canonical_id}")
            elif grant == "grant-write-acp":
                resp = s3_obj_acl.create_bucket_with_acl(
                    bucket_name=bucket, acl=acl, grant_write_acp=f"id={canonical_id}")
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
    @pytest.mark.tags("TEST-5717")
    def test_verify_get_bucket_acl_3012(self):
        """verify Get Bucket ACL of existing Bucket."""
        self.log.info("verify Get Bucket ACL of existing Bucket")
        resp = self.s3_obj.create_bucket(self.bucket)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_utils.poll(self.acl_obj.get_bucket_acl, self.bucket,
                             condition="{}[1][1][0]['Permission']=='FULL_CONTROL'")
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1][1][0]["Permission"], "FULL_CONTROL", resp[1])
        self.log.info("verify Get Bucket ACL of existing Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5719")
    def test_verify_get_bucket_acl_3013(self):
        """verify Get Bucket ACL of non existing Bucket."""
        self.log.info("verify Get Bucket ACL of non existing Bucket")
        try:
            resp = self.acl_obj.get_bucket_acl(self.bucket)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert err_msg.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message
        self.log.info("ENDED: verify Get Bucket ACL of non existing Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5712")
    def test_verify_get_bucket_acl_3014(self):
        """verify Get Bucket ACL of an empty Bucket."""
        self.log.info("verify Get Bucket ACL of an empty Bucket")
        resp = self.s3_obj.create_bucket(self.bucket)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.acl_obj.get_bucket_acl(self.bucket)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1][1][0]["Permission"], "FULL_CONTROL", resp[1])
        self.log.info("verify Get Bucket ACL of an empty Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5718")
    def test_verify_get_bucket_acl_3015(self):
        """verify Get Bucket ACL of an existing Bucket having objects."""
        self.log.info("verify Get Bucket ACL of an existing Bucket having objects")
        resp = self.s3_obj.create_bucket(self.bucket)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket, resp[1])
        system_utils.create_file(self.test_file_path, 1)
        resp = self.s3_obj.object_upload(self.bucket, self.test_file, self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.acl_obj.get_bucket_acl(self.bucket)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1][1][0]["Permission"], "FULL_CONTROL", resp[1])
        self.log.info("verify Get Bucket ACL of an existing Bucket having objects")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5713")
    def test_verify_get_bucket_acl_3016(self):
        """Verify Get Bucket ACL without Bucket name."""
        self.log.info("Verify Get Bucket ACL without Bucket name")
        try:
            resp = self.acl_obj.get_bucket_acl(None)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert err_msg.NO_BUCKET_NAME_ERR in str(error.message), error.message
        self.log.info("ENDED: Verify Get Bucket ACL without Bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5720")
    def test_delete_and_verify_bucket_acl_3017(self):
        """Delete Bucket and verify Bucket ACL."""
        self.log.info("Delete Bucket and verify Bucket ACL")
        resp = self.s3_obj.create_bucket(self.bucket)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_obj.delete_bucket(self.bucket)
        assert_utils.assert_true(resp[0], resp[1])
        try:
            resp = self.acl_obj.get_bucket_acl(self.bucket)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error)
            assert err_msg.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message
        self.log.info("ENDED: Delete Bucket and verify Bucket ACL")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5716")
    def test_verify_get_bucket_acl_3018(self):
        """verify Get Bucket ACL of existing Bucket with associated Account credentials."""
        self.log.info("verify Get Bucket ACL existing Bucket with associated Account credentials")
        resp = self.rest_obj.create_s3_account(self.account, self.email_prefix.format(
            self.account), self.s3_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.account_list.append(self.account)
        access_key, secret_key = resp[1]["access_key"], resp[1]["secret_key"]
        s3_obj_acl = s3_test_lib.S3TestLib(access_key=access_key, secret_key=secret_key)
        resp = s3_obj_acl.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj_acl.bucket_list()
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert self.bucket in str(resp[1]), resp[1]
        resp = self.acl_obj.get_bucket_acl_using_iam_credentials(access_key, secret_key,
                                                                 self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1][1][0]["Permission"], "FULL_CONTROL", resp[1])
        # Cleanup
        resp = s3_obj_acl.delete_bucket(self.bucket, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("verify Get Bucket ACL of existing Bucket with associated Account credential")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5715")
    def test_verify_get_bucket_acl_3019(self):
        """verify Get Bucket ACL of existing Bucket with different Account credentials."""
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with different Account credentials")
        access_keys, secret_keys = [], []
        for _ in range(2):
            account = self.account_prefix.format(perf_counter_ns())
            resp = self.rest_obj.create_s3_account(account, f"{account}@seagate.com",
                                                   self.s3_passwd)
            assert_utils.assert_true(resp[0], resp[1])
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            self.account_list.append(account)
        s3_obj_acl = s3_test_lib.S3TestLib(access_key=access_keys[0], secret_key=secret_keys[0])
        resp = s3_obj_acl.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj_acl.bucket_list()
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert self.bucket in resp[1], resp[1]
        try:
            resp = self.acl_obj.get_bucket_acl_using_iam_credentials(access_keys[1], secret_keys[1],
                                                                     self.bucket)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert err_msg.ACCESS_DENIED_ERR_KEY in str(error.message), error.message
        resp = s3_obj_acl.delete_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("verify Get Bucket ACL of existing Bucket with different Account credentials")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5714")
    def test_verify_get_bucket_acl_3020(self):
        """verify Get Bucket ACL of existing Bucket with IAM User credentials."""
        self.log.info("verify Get Bucket ACL of existing Bucket with IAM User credentials")
        user_name = "user10016"
        access_keys, secret_keys = [], []
        for _ in range(2):
            account = self.account_prefix.format(perf_counter_ns())
            resp = self.rest_obj.create_s3_account(account, f"{account}@seagate.com",
                                                   self.s3_passwd)
            assert_utils.assert_true(resp[0], resp[1])
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            self.account_list.append(account)
        s3_obj_acl = s3_test_lib.S3TestLib(access_key=access_keys[0], secret_key=secret_keys[0])
        resp = s3_obj_acl.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_obj_acl.bucket_list()
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert self.bucket in resp[1], resp[1]
        iam_obj_acl = iam_test_lib.IamTestLib(access_key=access_keys[1], secret_key=secret_keys[1])
        resp = iam_obj_acl.create_user(user_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = iam_obj_acl.create_access_key(user_name)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        access_key_user = resp[1]["AccessKey"]["AccessKeyId"]
        secret_key_user = resp[1]["AccessKey"]["SecretAccessKey"]
        try:
            resp = self.acl_obj.get_bucket_acl_using_iam_credentials(
                access_key_user, secret_key_user, self.bucket)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert err_msg.ACCESS_DENIED_ERR_KEY in str(error.message), error.message
        resp = s3_obj_acl.delete_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        resp = iam_obj_acl.delete_users_with_access_key([user_name])
        assert_utils.assert_true(resp, f"Failed to delete iam user: {user_name}")
        self.log.info("verify Get Bucket ACL of existing Bucket with IAM User credentials")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5728")
    def test_add_canned_acl_bucket_3527(self):
        """Add canned ACL bucket-owner-full-control along with READ ACL grant permission."""
        self.log.info(
            "STARTED: Add canned ACL bucket-owner-full-control along with READ "
            "ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket, "bucket-owner-full-control", error_msg=err_msg.CANNED_ACL_GRANT_ERR)
        self.log.info(
            "ENDED:Add canned ACL bucket-owner-full-control along with READ ACL "
            "grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5727")
    def test_add_canned_acl_bucket_3528(self):
        """Add canned ACL bucket-owner-read along with READ ACL grant permission."""
        self.log.info(
            "STARTED: Add canned ACL bucket-owner-read along with READ ACL "
            "grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket, "bucket-owner-read", error_msg=err_msg.CANNED_ACL_GRANT_ERR)
        self.log.info(
            "ENDED: Add canned ACL bucket-owner-read along with READ ACL "
            "grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5736")
    def test_add_canned_acl_private_3529(self):
        """Add canned ACL "private" along with "READ" ACL grant permission."""
        self.log.info(
            "STARTED: Add canned ACL 'private' along with 'READ' ACL "
            "grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket, "private", error_msg=err_msg.CANNED_ACL_GRANT_ERR)
        self.log.info(
            "ENDED: Add canned ACL 'private' along with 'READ' ACL "
            "grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5737")
    def test_add_canned_acl_private_3530(self):
        """Add canned ACL "private" along with "FULL_CONTROL" ACL grant permission."""
        self.log.info(
            "STARTED: Add canned ACL 'private' along with 'FULL_CONTROL' ACL "
            "grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket, "private", "grant-full-control", err_msg.CANNED_ACL_GRANT_ERR)
        self.log.info(
            "ENDED: Add canned ACL 'private' along with 'FULL_CONTROL' ACL "
            "grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5732")
    def test_add_canned_acl_public_read_3531(self):
        """Add canned ACL "public-read" along with "READ_ACP" ACL grant permission."""
        self.log.info(
            "STARTED: Add canned ACL 'public-read' along with 'READ_ACP' ACL "
            "grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket, "public-read", "grant-read-acp", err_msg.CANNED_ACL_GRANT_ERR)
        self.log.info(
            "ENDED: Add canned ACL 'public-read' along with 'READ_ACP' ACL grant "
            "permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5731")
    def test_add_canned_acl_public_read_3532(self):
        """Add canned ACL "public-read" along with "WRITE_ACP" ACL grant permission."""
        self.log.info(
            "STARTED: Add canned ACL 'public-read' along with 'WRITE_ACP' ACL "
            "grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket, "public-read", "grant-write-acp", err_msg.CANNED_ACL_GRANT_ERR)
        self.log.info(
            "ENDED: Add canned ACL 'public-read' along with 'WRITE_ACP' ACL "
            "grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5729")
    def test_add_canned_acl_public_read_write_3533(self):
        """Add canned ACL 'public-read-write' along with "WRITE_ACP" ACL grant permission."""
        self.log.info(
            "STARTED: Add canned ACL 'public-read-write' along with 'WRITE_ACP' "
            "ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket, "public-read-write", "grant-write-acp", err_msg.CANNED_ACL_GRANT_ERR)
        self.log.info(
            "ENDED: Add canned ACL 'public-read-write' along with 'WRITE_ACP' "
            "ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5730")
    def test_add_canned_acl_public_read_write_3534(self):
        """Add canned ACL 'public-read-write' along with "FULL_CONTROL" ACL grant permission."""
        self.log.info(
            "STARTED: Add canned ACL 'public-read-write' along with 'FULL_CONTROL' "
            "ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket, "public-read-write", "grant-full-control", err_msg.CANNED_ACL_GRANT_ERR)
        self.log.info(
            "ENDED: Add canned ACL 'public-read-write' along with 'FULL_CONTROL' "
            "ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5739")
    def test_add_canned_acl_authenticate_read_3535(self):
        """Add canned ACL 'authenticate-read' along with "READ" ACL grant permission."""
        self.log.info(
            "STARTED: Add canned ACL 'authenticate-read' along with 'READ' ACL "
            "grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket, "authenticated-read", error_msg=err_msg.CANNED_ACL_GRANT_ERR)
        self.log.info(
            "ENDED: Add canned ACL 'authenticate-read' along with 'READ' ACL "
            "grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5738")
    def test_add_canned_acl_authenticate_read_3536(self):
        """Add canned ACL 'authenticate-read' along with "READ_ACP" ACL grant permission."""
        self.log.info(
            "STARTED:Add canned ACL 'authenticate-read' along with 'READ_ACP' "
            "ACL grant permission")
        self.create_bucket_with_acl_and_grant_permissions(
            self.bucket, "authenticated-read", "grant-read-acp",
            error_msg=err_msg.CANNED_ACL_GRANT_ERR)
        self.log.info(
            "ENDED: Add canned ACL 'authenticate-read' along with 'READ_ACP' ACL "
            "grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5735")
    def test_add_canned_acl_private_3537(self):
        """Add canned ACL "private" as a request header along with FULL_CONTROL.
        ACL grant permission as request body
        """
        self.log.info("Add canned ACL 'private' as a request header along with FULL_CONTROL"
                      " ACL grant permission as request body")
        resp = self.rest_obj.create_s3_account(self.account, self.email_prefix.format(self.account),
                                               self.s3_passwd)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        access_key, secret_key = resp[1]["access_key"], resp[1]["secret_key"]
        self.account_list.append(self.account)
        s3_test = s3_test_lib.S3TestLib(access_key=access_key, secret_key=secret_key)
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(access_key=access_key, secret_key=secret_key)
        resp = s3_test.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket, resp[1])
        resp = s3_obj_acl.get_bucket_acl(bucket_name=self.bucket)
        self.log.info(resp)
        newresp = {"Owner": resp[1][0], "Grants": resp[1][1]}
        self.log.info("New dict to pass ACP with permission private:%s", newresp)
        newresp["Grants"][0]["Permission"] = "FULL_CONTROL"
        try:
            resp = s3_obj_acl.put_bucket_acl(bucket_name=self.bucket, acl="private",
                                             access_control_policy=newresp)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert "UnexpectedContent" in error.message, error.message
        self.log.info("Cleanup activity")
        self.log.info("Deleting a bucket %s", self.bucket)
        resp = s3_test.delete_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp)
        self.log.info("Add canned ACL 'private' as a request header along with FULL_CONTROL"
                      " ACL grant permission as request body")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5733")
    def test_add_canned_acl_private_3538(self):
        """Add canned ACL "private" in request body along with "FULL_CONTROL".
        ACL grant permission in request header.
        """
        self.log.info("Add canned ACL private in request body along with FULL_CONTROL"
                      " ACL grant permission in request header")
        resp = self.rest_obj.create_s3_account(self.account, self.email_prefix.format(self.account),
                                               self.s3_passwd)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        access_key, secret_key = resp[1]["access_key"], resp[1]["secret_key"]
        self.account_list.append(self.account)
        s3_test = s3_test_lib.S3TestLib(access_key=access_key, secret_key=secret_key)
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(access_key=access_key, secret_key=secret_key)
        resp = s3_test.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket, resp[1])
        resp = s3_obj_acl.get_bucket_acl(bucket_name=self.bucket)
        self.log.info(resp)
        newresp = {"Owner": resp[1][0], "Grants": resp[1][1]}
        self.log.info("New dict to pass ACP with permission private:%s", newresp)
        newresp["Grants"][0]["Permission"] = "private"
        try:
            resp = s3_obj_acl.put_bucket_acl(
                bucket_name=self.bucket,
                acl="FULL_CONTROL",
                access_control_policy=newresp)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert "BadRequest" in error.message, error.message
        self.log.info("Cleanup activity")
        self.log.info("Deleting a bucket %s", self.bucket)
        resp = s3_test.delete_bucket(self.bucket, force=True)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp)
        self.log.info("Add canned ACL private in request body along with FULL_CONTROL"
                      " ACL grant permission in request header")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5734")
    def test_add_canned_acl_private_3539(self):
        """Add canned ACL "private" in request body along with "FULL_CONTROL".
        ACL grant permission in request body.
        """
        self.log.info("Add canned ACL private in request body along with FULL_CONTROL"
                      " ACL grant permission in request body")
        resp = self.rest_obj.create_s3_account(self.account, self.email_prefix.format(self.account),
                                               self.s3_passwd)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        access_key, secret_key = resp[1]["access_key"], resp[1]["secret_key"]
        canonical_id = resp[1]["canonical_id"]
        self.account_list.append(self.account)
        s3_test = s3_test_lib.S3TestLib(access_key=access_key, secret_key=secret_key)
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(access_key=access_key, secret_key=secret_key)
        resp = s3_test.create_bucket(bucket_name=self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket, resp[1])
        resp = s3_obj_acl.get_bucket_acl(bucket_name=self.bucket)
        self.log.info(resp)
        newresp = {"Owner": resp[1][0], "Grants": resp[1][1]}
        self.log.info("New dict to pass ACP with permission private:%s", newresp)
        newresp["Grants"][0]["Permission"] = "private"
        new_grant = {"Grantee": {"ID": canonical_id, "Type": "CanonicalUser", },
                     "Permission": "FULL_CONTROL", }
        modified_acl = copy.deepcopy(newresp)
        modified_acl["Grants"].append(new_grant)
        self.log.info("ACP with permission private and Full control:%s", modified_acl)
        try:
            resp = s3_obj_acl.put_bucket_acl(bucket_name=self.bucket,
                                             access_control_policy=newresp)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert err_msg.S3_INVALID_ACL_ERR in error.message, error.message
        self.log.info("Cleanup activity")
        self.log.info("Deleting a bucket %s", self.bucket)
        resp = s3_test.delete_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp)
        self.log.info("Add canned ACL private in request body along with FULL_CONTROL"
                      " ACL grant permission in request body")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5726")
    def test_add_canned_acl_authenticated_read_3577(self):
        """Apply authenticated-read canned ACL to account2. Execute head-bucket from account2 on
         a bucket. Bucket belongs to account1.
        """
        self.log.info("Apply authenticated-read canned ACL to account2 and execute head-bucket "
                      "from account2 on a bucket. Bucket belongs to account1")
        access_keys = []
        secret_keys = []
        canonical_ids = []
        for _ in range(2):
            account = self.account_prefix.format(perf_counter_ns())
            resp = self.rest_obj.create_s3_account(account, f"{account}@seagate.com",
                                                   self.s3_passwd)
            assert_utils.assert_true(resp[0], resp[1])
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            canonical_ids.append(resp[1]["canonical_id"])
            self.account_list.append(account)
        s3_obj1 = s3_test_lib.S3TestLib(access_key=access_keys[0], secret_key=secret_keys[0])
        acl_obj1 = s3_acl_test_lib.S3AclTestLib(access_keys[0], secret_keys[0])
        s3_obj2 = s3_test_lib.S3TestLib(access_key=access_keys[1], secret_key=secret_keys[1])
        self.log.info("Creating new bucket from first account")
        resp = s3_obj1.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket, resp[1])
        self.log.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_equals(resp[1]["BucketName"], self.bucket, resp[1])
        self.log.info("Performing authenticated read acl")
        resp = acl_obj1.put_bucket_acl(self.bucket, acl="authenticated-read")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(access_keys[0], secret_keys[0],
                                                             self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert "READ" in resp[1][1][1]["Permission"], resp[1]
        self.log.info("Performing head bucket with second account credentials")
        resp = s3_obj2.head_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1]["BucketName"], self.bucket, resp[1])
        self.log.info("Deleting bucket")
        resp = s3_obj1.delete_bucket(self.bucket, force=True)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Apply authenticated-read canned ACL to account2 and execute "
                      "head-bucket from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5724")
    def test_apply_private_canned_acl_3578(self):
        """Apply private canned ACL to account2 and execute head-bucket."""
        self.log.info("Apply private canned ACL to account2 and execute head-bucket "
                      "from account2 on a bucket. Bucket belongs to account1")
        acc_ks = []
        secret_ks = []
        canonical_ids = []
        for _ in range(2):
            account = self.account_prefix.format(perf_counter_ns())
            resp = self.rest_obj.create_s3_account(account, f"{account}@seagate.com",
                                                   self.s3_passwd)
            assert_utils.assert_true(resp[0], resp[1])
            acc_ks.append(resp[1]["access_key"])
            secret_ks.append(resp[1]["secret_key"])
            canonical_ids.append(resp[1]["canonical_id"])
            self.account_list.append(account)
        s3_obj1 = s3_test_lib.S3TestLib(access_key=acc_ks[0], secret_key=secret_ks[0])
        acl_obj1 = s3_acl_test_lib.S3AclTestLib(access_key=acc_ks[0], secret_key=secret_ks[0])
        s3_obj2 = s3_test_lib.S3TestLib(access_key=acc_ks[1], secret_key=secret_ks[1])
        self.log.info("Creating new bucket from first account")
        resp = s3_obj1.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket, resp[1])
        self.log.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_equals(resp[1]["BucketName"], self.bucket, resp[1])
        self.log.info("Performing authenticated read acl")
        resp = acl_obj1.put_bucket_acl(self.bucket, acl="private")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(acc_ks[0], secret_ks[0], self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performing head bucket with second account credentials")
        try:
            resp = s3_obj2.head_bucket(self.bucket)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert "Forbidden" in error.message, error.message
        self.log.info("Deleting bucket")
        resp = s3_obj1.delete_bucket(self.bucket, force=True)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Apply private canned ACL to account2 and execute "
                      "head-bucket from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5722")
    def test_grant_read_permission_acl_3579(self):
        """
        Grant read permission to account2 and execute head-bucket.
        from account2 on a bucket. Bucket belongs to account1
        """
        self.log.info("Grant read permission to account2 and execute head-bucket "
                      "from account2 on a bucket. Bucket belongs to account1")
        acc_keys = []
        secret_keys = []
        canonical_ids = []
        accounts = []
        for _ in range(2):
            account = self.account_prefix.format(perf_counter_ns())
            resp = self.rest_obj.create_s3_account(account, f"{account}@seagate.com",
                                                   self.s3_passwd)
            assert_utils.assert_true(resp[0], resp[1])
            acc_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            canonical_ids.append(resp[1]["canonical_id"])
            self.account_list.append(account)
            accounts.append(account)
        s3_obj1 = s3_test_lib.S3TestLib(access_key=acc_keys[0], secret_key=secret_keys[0])
        acl_obj1 = s3_acl_test_lib.S3AclTestLib(access_key=acc_keys[0], secret_key=secret_keys[0])
        s3_obj2 = s3_test_lib.S3TestLib(access_key=acc_keys[1], secret_key=secret_keys[1])
        self.log.info("Creating new bucket from first account")
        resp = s3_obj1.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket, resp[1])
        self.log.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_equals(resp[1]["BucketName"], self.bucket, resp[1])
        self.log.info("Performing grant read permission to second account")
        resp = acl_obj1.put_bucket_acl(self.bucket, grant_read=f"id={canonical_ids[1]}")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(acc_keys[0], secret_keys[0],
                                                             self.bucket)
        self.log.info(resp)
        assert_utils.assert_equals(resp[1][1][0]["Grantee"]["DisplayName"], accounts[1], resp[1])
        assert_utils.assert_equals("READ", resp[1][1][0]["Permission"], resp[1])
        self.log.info("Performing head bucket with second account credentials")
        resp = s3_obj2.head_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_equals(resp[1]["BucketName"], self.bucket, resp[1])
        acl_obj1.put_bucket_acl(self.bucket, acl="private")
        self.log.info("Deleting bucket")
        resp = s3_obj1.delete_bucket(self.bucket, force=True)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Grant read permission to account2 and execute head-bucket "
                      "from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5721")
    def test_perform_head_bucket_acl_3580(self):
        """Perform a head bucket on a bucket."""
        self.log.info("Perform a head bucket on a bucket")
        resp = self.s3_obj.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket, resp[1])
        resp = self.s3_obj.head_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1]["BucketName"], self.bucket, resp[1])
        self.log.info("Perform a head bucket on a bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-5723")
    def test_create_verify_default_acl_3581(self):
        """Create a bucket and verify default ACL."""
        self.log.info("Create a bucket and verify default ACL")
        resp = self.s3_obj.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1], self.bucket, resp[1])
        resp = self.acl_obj.get_bucket_acl(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equals(resp[1][1][0]["Permission"], "FULL_CONTROL", resp[1])
        self.log.info("Create a bucket and verify default ACL")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-8027")
    def test_put_get_bucket_acl_312(self):
        """put bucket in account1 and get-bucket-acl for that bucket."""
        self.log.info("STARTED: put bucket in account1 and get-bucket-acl for that bucket")
        self.log.info("Step 1: Creating bucket: %s", self.bucket)
        resp = self.s3_obj.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Bucket: %s created", self.bucket)
        self.log.info("Step 2: Retrieving bucket acl attributes")
        resp = self.acl_obj.get_bucket_acl(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Bucket ACL was verified")
        self.log.info("ENDED: put bucket in account1 and get-bucket-acl for that bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-8029")
    def test_put_get_bucket_acl_313(self):
        """acc1: put bucket, acc2: no permissions or canned acl, get-bucket-acl details."""
        self.log.info(
            "STARTED:acc1: put bucket, acc2: no permissions or canned acl, get-bucket-acl details")
        self.log.info("Step 1: Creating bucket: %s", self.bucket)
        resp = self.s3_obj.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Bucket : %s created", self.bucket)
        create_acc = self.rest_obj.create_s3_account(self.account1, self.email_prefix.format(
            self.account1), self.s3_passwd)
        assert create_acc[0], create_acc[1]
        acl_test_2 = S3AclTestLib(create_acc[1]["access_key"], create_acc[1]["secret_key"])
        self.account_list.append(self.account1)
        self.log.info("Step 2: Retrieving bucket acl attributes using account 2")
        try:
            resp = acl_test_2.get_bucket_acl(self.bucket)
            self.log.info(resp)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.info(error.message)
            assert err_msg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 2: retrieving bucket acl using account 2 failed with error %s",
                "AccessDenied")
        self.log.info(
            "ENDED:acc1: put bucket, acc2: no permissions or canned acl, "
            "get-bucket-acl details")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags("TEST-8030")
    def test_put_get_bucket_acl_431(self):
        """acc1 -put bucket, acc2- give read-acp permissions,acc1- get-bucket-acl."""
        self.log.info("STARTED:acc1 put bucket, acc2 give read-acp permissions,acc1 get-bucket-acl")
        self.log.info("Step 1: Creating bucket: %s", self.bucket)
        resp = self.s3_obj.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Bucket : %s is created", self.bucket)
        s3_acc = self.rest_obj.create_s3_account(self.account1, self.email_prefix.format(
            self.account1), self.s3_passwd)
        assert s3_acc[0], s3_acc[1]
        canonical_id = s3_acc[1]["canonical_id"]
        acl_test_2 = S3AclTestLib(s3_acc[1]["access_key"], s3_acc[1]["secret_key"])
        self.account_list.append(self.account1)
        self.log.info("Step 2: Performing authenticated read acp")
        resp = self.acl_obj.put_bucket_acl(self.bucket, grant_read_acp=f"id={canonical_id}")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2:Bucket with read ACP permission was set for acc2")
        self.log.info("Step 3: Retrieving bucket acl attributes")
        resp = acl_test_2.get_bucket_acl(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Bucket ACL was verified")
        self.log.info("ENDED:acc1 put bucket, acc2 give read-acp permissions, acc1 get-bucket-acl")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-8712")
    def test_full_control_acl_6423(self):
        """Test full-control on bucket to cross accnt and test delete bucket from owner account."""
        self.log.info("STARTED: Test full-control on bucket to cross account and test delete")
        s3_acc = self.rest_obj.create_s3_account(self.account, self.email_prefix.format(
            self.account), self.s3_passwd)
        assert s3_acc[0], s3_acc[1]
        canonical_id = s3_acc[1]["canonical_id"]
        self.account_list.append(self.account)
        self.log.info("Step 1: Creating bucket with name %s", self.bucket)
        resp = self.s3_obj.create_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Created a bucket with name %s", self.bucket)
        self.log.info("Step 2: Verifying that bucket is created")
        resp = self.s3_obj.bucket_list()
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert self.bucket in resp[1]
        self.log.info("Step 2: Verified that bucket is created")
        self.log.info("Step 3: put bucket acl for bucket %s for full control", self.bucket)
        resp = self.acl_obj.put_bucket_acl(self.bucket, grant_full_control=f"id={canonical_id}")
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3:Performed put bucket, bucket %s for account 2", self.bucket)
        self.log.info("Step 4: Retrieving acl of a bucket %s", self.bucket)
        resp = self.acl_obj.get_bucket_acl(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Retrieved acl of a bucket %s", self.bucket)
        self.log.info("Step 5: Deleting a bucket %s", self.bucket)
        resp = self.s3_obj.delete_bucket(self.bucket)
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Deleted a bucket %s", self.bucket)
        self.log.info("Step 6: Verifying that bucket is deleted")
        resp = self.s3_obj.bucket_list()
        self.log.info(resp)
        assert_utils.assert_true(resp[0], resp[1])
        assert self.bucket not in resp[1], resp[1]
        self.log.info("Step 6: Verified that bucket is deleted")
        self.log.info("ENDED: Test full-control on bucket to cross account and test delete")
