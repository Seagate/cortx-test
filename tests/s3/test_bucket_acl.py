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

from commons.params import TEST_DATA_PATH
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils import assert_utils
from commons.utils import system_utils
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD
from libs.s3 import s3_test_lib
from libs.s3 import iam_test_lib
from libs.s3 import s3_acl_test_lib

S3_OBJ = s3_test_lib.S3TestLib()
IAM_OBJ = iam_test_lib.IamTestLib()
ACL_OBJ = s3_acl_test_lib.S3AclTestLib()


class TestBucketACL:
    """Bucket ACL Test suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.random_id = str(time.time())
        cls.account_name = "{}{}".format("acl", "acltestaccn")
        cls.email_id = "{}{}".format(cls.account_name, "@seagate.com")
        cls.ldap_user = LDAP_USERNAME
        cls.ldap_pwd = LDAP_PASSWD
        cls.test_file = "testfile"
        cls.test_dir_path = os.path.join(TEST_DATA_PATH, "BucketACL")
        if not system_utils.path_exists(cls.test_dir_path):
            resp = system_utils.make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", resp)
        cls.test_file_path = os.path.join(cls.test_dir_path, cls.test_file)
        cls.log.info(
            "LDAP credentials: User: %s, pass: %s",
            cls.ldap_user,
            cls.ldap_pwd)
        cls.log.info("ENDED: setup test suite operations.")

    @staticmethod
    def teardown_class(cls):
        """
        Summary: This function will be invoked end of test suites.

        Description: It will remove test suite directory.
        """
        cls.log.info("STARTED: Teardown Operations")
        if not system_utils.path_exists(cls.test_dir_path):
            resp = system_utils.remove_dirs(cls.test_dir_path)
            cls.log.info("Remove path: %s", resp)
        cls.log.info("ENDED: Teardown Operations")

    def helper_method(self, bucket, acl, error_msg):
        """Helper method for creating bucket with acl."""
        account_name = "{}{}".format(self.account_name, str(int(time.time())))
        email_id = "{}{}".format(str(int(time.time())), self.email_id)
        resp = IAM_OBJ.create_account_s3iamcli(
            account_name, email_id, self.ldap_user, self.ldap_pwd)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        canonical_id = resp[1]["canonical_id"]
        bucket_name = "{}{}".format(
            bucket, str(int(time.time())))
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key, secret_key=secret_key)
        try:
            s3_obj_acl.create_bucket_with_acl(
                bucket_name=bucket_name,
                acl=acl,
                grant_read="id=" + canonical_id)
        except CTException as error:
            assert error_msg in str(error.message), error.message

    def setup_method(self):
        """
        Summary: This function will be invoked prior to each test case.

        Description: It will perform all prerequisite test steps if any.
        """
        self.log.info("STARTED: Setup Operations")
        if system_utils.path_exists(self.test_file_path):
            system_utils.remove_file(self.test_file_path)
        self.log.info("ENDED: Setup Operations")

    def teardown_method(self):
        """Function to perform the clean up for each test."""
        self.log.info("STARTED: Teardown Operations")
        self.log.info("Clean : %s", self.test_dir_path)
        if system_utils.path_exists(self.test_dir_path):
            resp = system_utils.cleanup_dir(self.test_dir_path)
            self.log.info(
                "cleaned path: %s, resp: %s",
                self.test_dir_path,
                resp)
        self.log.info("Deleting buckets in default account")
        resp = S3_OBJ.bucket_list()
        pref_list = [
            each_bucket for each_bucket in resp[1] if each_bucket.startswith(
                "acl")]
        for bucket in pref_list:
            ACL_OBJ.put_bucket_acl(
                bucket, acl="private")
        S3_OBJ.delete_multiple_buckets(pref_list)
        self.log.info("Deleted buckets in default account")
        self.log.info(
            "Deleting IAM accounts with prefix: %s", self.account_name)
        acc_list = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)[1]
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        self.log.info(all_acc)
        for acc_name in all_acc:
            resp = IAM_OBJ.reset_account_access_key_s3iamcli(
                acc_name,
                self.ldap_user,
                self.ldap_pwd)
            access_key = resp[1]["AccessKeyId"]
            secret_key = resp[1]["SecretKey"]
            s3_obj_temp = s3_test_lib.S3TestLib(access_key, secret_key)
            self.log.info(
                "Deleting buckets in %s account if any", acc_name)
            bucket_list = s3_obj_temp.bucket_list()[1]
            self.log.info(bucket_list)
            s3_obj_acl = s3_acl_test_lib.S3AclTestLib(
                access_key, secret_key)
            for bucket in bucket_list:
                s3_obj_acl.put_bucket_acl(bucket, acl="private")
            s3_obj_temp.delete_all_buckets()
            IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(acc_name)
        self.log.info("Deleted IAM accounts successfully")
        self.log.info("ENDED: Teardown Operations")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5717")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3012(self):
        """verify Get Bucket ACL of existing Bucket."""
        self.log.info("verify Get Bucket ACL of existing Bucket")
        bucket_name = "{}{}".format(
            "acl",
            "bucket-10008")
        bucket_permission = "FULL_CONTROL"
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp = ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            resp[1][1][0]["Permission"],
            bucket_permission,
            resp[1])
        self.log.info("verify Get Bucket ACL of existing Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5719")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3013(self):
        """verify Get Bucekt ACL of non existing Bucket."""
        self.log.info("verify Get Bucket ACL of non existing Bucket")
        bucket_name = "bucket-10009"
        try:
            ACL_OBJ.get_bucket_acl(bucket_name)
        except CTException as error:
            assert "NoSuchBucket" in str(
                error.message), error.message
        self.log.info("verify Get Bucket ACL of non existing Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5712")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3014(self):
        """verify Get Bucket ACL of an empty Bucket."""
        self.log.info("verify Get Bucket ACL of an empty Bucket")
        bucket_name = "{}{}".format(
            "acl",
            "bucket-10010")
        bucket_permission = "FULL_CONTROL"
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp = ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            resp[1][1][0]["Permission"],
            bucket_permission,
            resp[1])
        self.log.info("verify Get Bucket ACL of an empty Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5718")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3015(self):
        """verify Get Bucket ACL of an existing Bucket having objects."""
        self.log.info(
            "verify Get Bucket ACL of an existing Bucket having objects")
        bucket_name = "{}{}".format(
            "acl",
            "bucket-10011")
        bucket_permission = "FULL_CONTROL"
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        self.log.info(resp)
        assert_utils.assert_equals(resp[1], bucket_name, resp[1])
        system_utils.create_file(self.test_file_path,
                    1)
        resp = S3_OBJ.object_upload(bucket_name,
                                    self.test_file,
                                    self.test_file_path)
        assert resp[0], resp[1]
        resp = ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            resp[1][1][0]["Permission"],
            bucket_permission,
            resp[1])
        self.log.info(
            "verify Get Bucket ACL of an existing Bucket having objects")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5713")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3016(self):
        """Verify Get Bucket ACL without Bucket name."""
        self.log.info("Verify Get Bucket ACL without Bucket name")
        try:
            ACL_OBJ.get_bucket_acl(None)
        except CTException as error:
            assert "Required parameter bucket_name not set" in str(
                error.message), error.message
        self.log.info("Verify Get Bucket ACL without Bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5720")
    @CTFailOn(error_handler)
    def test_delete_and_verify_bucket_acl_3017(self):
        """Delete Bucket and verify Bucket ACL."""
        self.log.info("Delete Bucket and verify Bucket ACL")
        bucket_name = "{}{}".format(
            "acl",
            "bucket-10013")
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp = S3_OBJ.delete_bucket(bucket_name)
        assert resp[0], resp[1]
        try:
            ACL_OBJ.get_bucket_acl(bucket_name)
        except CTException as error:
            assert "NoSuchBucket" in str(
                error.message), error.message
        self.log.info("Delete Bucket and verify Bucket ACL")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5716")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3018(self):
        """verify Get Bucket ACL of existing Bucket with associated Account credentials."""
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with associated Account credentials")
        acc_name = "{}{}".format(self.account_name, str(int(time.time())))
        email = "{}{}".format(str(int(time.time())), self.email_id, )
        resp = IAM_OBJ.create_account_s3iamcli(acc_name,
                                               email,
                                               self.ldap_user, self.ldap_pwd)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        bucket_name = "{}{}{}".format(
            "acl",
            "bucket-10014",
            str(
                int(
                    time.time())))
        bucket_permission = "FULL_CONTROL"
        s3_obj_acl = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        resp = s3_obj_acl.create_bucket(bucket_name)
        assert resp[0], resp[1]

        resp = s3_obj_acl.bucket_list()
        assert resp[0], resp[1]
        assert bucket_name in str(resp[1]), resp[1]
        resp = ACL_OBJ.get_bucket_acl_using_iam_credentials(
            access_key, secret_key, bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            resp[1][1][0]["Permission"],
            bucket_permission,
            resp[1])
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with associated Account credentials")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5715")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3019(self):
        """verify Get Bucket ACL of existing Bucket with different Account credentials."""
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with different Account credentials")
        accounts = ["acltestaccnt100151", "acltestaccnt100152"]
        emails = ["acltestaccnt100151@seagate.com", "acltestaccnt100152@seagate.com"]
        access_keys = []
        secret_keys = []
        for account, email in zip(accounts, emails):
            account = "{}{}".format(account, str(int(time.time())))
            email = "{}{}".format(str(int(time.time())), email)
            resp = IAM_OBJ.create_account_s3iamcli(
                account, email, self.ldap_user, self.ldap_pwd)
            assert resp[0], resp[1]
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
        bucket_name = "{}{}".format(
            "aclbucket10015", str(int(time.time())))
        err_message = "AccessDenied"
        s3_obj_acl = s3_test_lib.S3TestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        resp = s3_obj_acl.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp = s3_obj_acl.bucket_list()
        assert resp[0], resp[1]
        assert bucket_name in resp[1], resp[1]
        try:
            ACL_OBJ.get_bucket_acl_using_iam_credentials(
                access_keys[1], secret_keys[1], bucket_name)
        except CTException as error:
            assert err_message in str(error.message), error.message
        resp = s3_obj_acl.delete_bucket(bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with different Account credentials")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5714")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3020(self):
        """verify Get Bucket ACL of existing Bucket with IAM User credentials."""
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with IAM User credentials")
        user_name = "user10016"
        access_keys = []
        secret_keys = []
        for account, email in zip(
                ["acltestaccnt100161", "acltestaccnt100162"],
                ["acltestaccnt100161@seagate.com", "acltestaccnt100162@seagate.com"]):
            resp = IAM_OBJ.create_account_s3iamcli(
                f"{account}{str(int(time.time()))}",
                f"{str(int(time.time()))}{email}",
                self.ldap_user,
                self.ldap_pwd)
            assert resp[0], resp[1]
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
        bucket_name = "{}{}".format(
            "aclbucket10016", str(int(time.time())))
        err_message = "AccessDenied"
        s3_obj_acl = s3_test_lib.S3TestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        resp = s3_obj_acl.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp = s3_obj_acl.bucket_list()
        assert resp[0], resp[1]
        assert bucket_name in resp[1], resp[1]
        iam_obj_acl = iam_test_lib.IamTestLib(
            access_key=access_keys[1],
            secret_key=secret_keys[1])
        resp = iam_obj_acl.create_user(user_name)
        assert resp[0], resp[1]
        resp = iam_obj_acl.create_access_key(user_name)
        assert resp[0], resp[1]
        access_key_user = resp[1]["AccessKey"]["AccessKeyId"]
        secret_key_user = resp[1]["AccessKey"]["SecretAccessKey"]
        try:
            ACL_OBJ.get_bucket_acl_using_iam_credentials(
                access_key_user, secret_key_user, bucket_name)
        except CTException as error:
            assert err_message in str(error.message), error.message
        resp = s3_obj_acl.delete_bucket(bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "verify Get Bucket ACL of existing Bucket with IAM User credentials")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5728")
    @CTFailOn(error_handler)
    def test_add_canned_acl_bucket_3527(self):
        """Add canned ACL bucket-owner-full-control along with READ ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with READ ACL grant permission")
        self.helper_method("aclbucket10766",
                           "bucket-owner-full-control",
                           "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with READ ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5727")
    @CTFailOn(error_handler)
    def test_add_canned_acl_bucket_3528(self):
        """Add canned ACL bucket-owner-read along with READ ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-read along with READ ACL grant permission")
        self.helper_method("aclbucket10767",
                           "bucket-owner-read",
                           "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL bucket-owner-read along with READ ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5736")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3529(self):
        """Add canned ACL "private" along with "READ" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'private' along with 'READ' ACL grant permission")
        self.helper_method("aclbucket10768",
                           "private",
                           "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'private' along with 'READ' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5737")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3530(self):
        """Add canned ACL "private" along with "FULL_CONTROL" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'private' along with 'FULL_CONTROL' ACL grant permission")
        self.helper_method("aclbucket10769",
                           "private",
                           "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'private' along with 'FULL_CONTROL' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5732")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_3531(self):
        """Add canned ACL "public-read" along with "READ_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'public-read' along with 'READ_ACP' ACL grant permission")
        self.helper_method("aclbucket10770",
                           "public-read",
                           "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'public-read' along with 'READ_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5731")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_3532(self):
        """Add canned ACL "public-read" along with "WRITE_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'public-read' along with 'WRITE_ACP' ACL grant permission")
        self.helper_method("aclbucket10771",
                           "public-read",
                           "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'public-read' along with 'WRITE_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5729")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_write_3533(self):
        """Add canned ACL 'public-read-write' along with "WRITE_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'public-read-write' along with 'WRITE_ACP' ACL grant permission")
        self.helper_method("aclbucket10772",
                            "public-read-write",
                           "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'public-read-write' along with 'WRITE_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5730")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_write_3534(self):
        """Add canned ACL 'public-read-write' along with "FULL_CONTROL" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'public-read-write' along with 'FULL_CONTROL' ACL grant permission")
        self.helper_method("aclbucket10773",
                           "public-read-write",
                           "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'public-read-write' along with 'FULL_CONTROL' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5739")
    @CTFailOn(error_handler)
    def test_add_canned_acl_authenticate_read_3535(self):
        """Add canned ACL 'authenticate-read' along with "READ" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'authenticate-read' along with 'READ' ACL grant permission")
        self.helper_method("aclbucket10774",
                           "authenticated-read",
                           "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'authenticate-read' along with 'READ' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5738")
    @CTFailOn(error_handler)
    def test_add_canned_acl_authenticate_read_3536(self):
        """Add canned ACL 'authenticate-read' along with "READ_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL 'authenticate-read' along with 'READ_ACP' ACL grant permission")
        self.helper_method("aclbucket10775",
                           "authenticated-read",
                           "Specifying both Canned ACLs and Header Grants is not allowed")
        self.log.info(
            "Add canned ACL 'authenticate-read' along with 'READ_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5735")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3537(self):
        """
        Add canned ACL "private" as a request header along with FULL_CONTROL
        ACL grant permission as request body
        """
        self.log.info(
            "Add canned ACL 'private' as a request header along with FULL_CONTROL"
            " ACL grant permission as request body")
        account_name = "{}{}".format(
            "acltestaccnt10776", str(int(time.time())))
        email_id = "{}{}".format(str(int(time.time())),
                                 "acltestaccnt10776@seagate.com")
        bucket_name = "{}{}".format(
            str(int(time.time())), "aclbucket10776")
        acc_str = "AccountName = {0}".format(account_name)
        acc_list = []
        resp = IAM_OBJ.list_accounts_s3iamcli(self.ldap_user, self.ldap_pwd)
        if acc_str in resp[1]:
            acc_list.append(account_name)
        if acc_list:
            IAM_OBJ.delete_multiple_accounts(acc_list)
        resp = IAM_OBJ.create_account_s3iamcli(
            account_name,
            email_id,
            self.ldap_user,
            self.ldap_pwd)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = s3_test.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], bucket_name, resp[1])
        resp = s3_obj_acl.get_bucket_acl(bucket_name=bucket_name)
        newresp = {"Owner": resp[1][0], "Grants": resp[1][1]}
        self.log.info(
            "New dict to pass ACP with permission private:%s", newresp)
        newresp["Grants"][0]["Permission"] = "FULL_CONTROL"
        try:
            s3_obj_acl.put_bucket_acl(
                bucket_name=bucket_name,
                acl="private",
                access_control_policy=newresp)
        except CTException as error:
            self.log.debug(error.message)
            assert "UnexpectedContent" in error.message, error.message
        self.log.info("Cleanup activity")
        self.log.info("Deleting a bucket %s", bucket_name)
        resp = s3_test.delete_bucket(bucket_name)
        assert resp[0], resp[1]
        self.log.info("Deleting an account %s", account_name)
        resp = IAM_OBJ.delete_account_s3iamcli(
            account_name, access_key, secret_key)
        assert resp[0], resp[1]
        self.log.info(
            "Add canned ACL 'private' as a request header along with FULL_CONTROL"
            " ACL grant permission as request body")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5733")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3538(self):
        """
        Add canned ACL "private" in request body along with "FULL_CONTROL"
        ACL grant permission in request header
        """
        self.log.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request header")
        account_name = "{}{}".format(
            "acltestaccnt10777", str(int(time.time())))
        email_id = "{}{}".format(str(int(time.time())),
                                 "acltestaccnt10777@seagate.com")
        bucket_name = "{}{}".format(
            str(int(time.time())), "aclbucket10777")
        acc_str = "AccountName = {0}".format(account_name)
        acc_list = []
        resp = IAM_OBJ.list_accounts_s3iamcli(self.ldap_user, self.ldap_pwd)
        if acc_str in resp[1]:
            acc_list.append(account_name)
        if acc_list:
            IAM_OBJ.delete_multiple_accounts(acc_list)
        resp = IAM_OBJ.create_account_s3iamcli(
            account_name,
            email_id,
            self.ldap_user,
            self.ldap_pwd)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key, secret_key=secret_key)

        resp = s3_test.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], bucket_name, resp[1])

        resp = s3_obj_acl.get_bucket_acl(bucket_name=bucket_name)
        newresp = {"Owner": resp[1][0], "Grants": resp[1][1]}
        self.log.info(
            "New dict to pass ACP with permission private:%s", newresp)
        newresp["Grants"][0]["Permission"] = "private"
        try:
            s3_obj_acl.put_bucket_acl(
                bucket_name=bucket_name,
                acl="FULL_CONTROL",
                access_control_policy=newresp)
        except CTException as error:
            self.log.debug(error.message)
            assert "BadRequest" in error.message, error.message
        self.log.info("Cleanup activity")
        self.log.info("Deleting a bucket %s", bucket_name)
        resp = s3_test.delete_bucket(bucket_name, force=True)
        assert resp[0], resp[1]
        self.log.info("Deleting an account %s", account_name)
        resp = IAM_OBJ.delete_account_s3iamcli(
            account_name, access_key, secret_key)
        assert resp[0], resp[1]
        self.log.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request header")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5734")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3539(self):
        """
        Add canned ACL "private" in request body along with "FULL_CONTROL"
        ACL grant permission in request body
        """
        self.log.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request body")

        account_name = "{}{}".format(
            "acltestaccnt10778", str(int(time.time())))
        email_id = "{}{}".format(str(int(time.time())),
                                 "acltestaccnt10778@seagate.com")
        bucket_name = "{}{}".format(
            str(int(time.time())), "aclbucket10778")
        acc_list = []
        resp = IAM_OBJ.list_accounts_s3iamcli(self.ldap_user, self.ldap_pwd)
        if f"AccountName = {account_name}" in resp[1]:
            acc_list.append(account_name)
        if acc_list:
            IAM_OBJ.delete_multiple_accounts(acc_list)
        resp = IAM_OBJ.create_account_s3iamcli(
            account_name,
            email_id,
            self.ldap_user,
            self.ldap_pwd)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        canonical_id = resp[1]["canonical_id"]
        s3_test = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = s3_test.create_bucket(bucket_name=bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], bucket_name, resp[1])
        resp = s3_obj_acl.get_bucket_acl(bucket_name=bucket_name)
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
            s3_obj_acl.put_bucket_acl(
                bucket_name=bucket_name,
                access_control_policy=newresp)
        except CTException as error:
            self.log.debug(error.message)
            assert "InvalidACL" in error.message, error.message
        self.log.info("Cleanup activity")
        self.log.info("Deleting a bucket %s", bucket_name)
        resp = s3_test.delete_bucket(bucket_name)
        assert resp[0], resp[1]
        self.log.info("Deleting an account %s", account_name)
        resp = IAM_OBJ.delete_account_s3iamcli(
            account_name, access_key, secret_key)
        assert resp[0], resp[1]
        self.log.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request body")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5726")
    @CTFailOn(error_handler)
    def test_add_canned_acl_authenticated_read_3577(self):
        """
        Apply authenticated-read canned ACL to account2 and execute head-bucket from
        account2 on a bucket. Bucket belongs to account1
        """
        self.log.info(
            "Apply authenticated-read canned ACL to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")
        accounts = ["acltestaccnt1", "acltestaccnt2"]
        emails = ["acltestaccnt1@seagate.com", "acltestaccnt2@seagate.com"]
        access_keys = []
        secret_keys = []
        canonical_ids = []
        account_name = []
        for account, email in zip(accounts, emails):
            account = "{}{}".format(account, str(int(time.time())))
            account_name.append(account)
            email = "{}{}".format(str(int(time.time())), email)
            resp = IAM_OBJ.create_account_s3iamcli(account, email,
                                                   self.ldap_user,
                                                   self.ldap_pwd)
            assert resp[0], resp[1]
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            canonical_ids.append(resp[1]["canonical_id"])
        bucket_name = "{}{}".format(
            "aclbucket-10837", str(int(time.time())))

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
        resp = s3_obj1.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], bucket_name, resp[1])
        self.log.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(bucket_name)
        assert_utils.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        self.log.info("Performing authenticated read acl")
        resp = acl_obj1.put_bucket_acl(
            bucket_name, acl="authenticated-read")
        assert resp[0], resp[1]
        self.log.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(
            access_keys[0], secret_keys[0], bucket_name)
        assert resp[0], resp[1]
        print("aa {}".format(resp))
        assert "READ" in resp[1][1][1]["Permission"], resp[1]
        self.log.info(
            "Performing head bucket with second account credentials")
        resp = s3_obj2.head_bucket(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        self.log.info("Deleting bucket")
        s3_obj1.delete_bucket(bucket_name, force=True)
        self.log.info("Deleting multiple accounts")
        IAM_OBJ.delete_multiple_accounts(account_name)
        self.log.info(
            "Apply authenticated-read canned ACL to account2 and execute "
            "head-bucket from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5724")
    @CTFailOn(error_handler)
    def test_apply_private_canned_acl_3578(self):
        """
        Summary: Apply private canned ACL to account2 and execute head-bucket

        Description: Apply private canned ACL to account2 and execute head-bucket
        from account2 on a bucket. Bucket belongs to account1
        """
        self.log.info(
            "Apply private canned ACL to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")
        accounts = ["acltestaccnt1", "acltestaccnt2"]
        emails = ["acltestaccnt1@seagate.com", "acltestaccnt2@seagate.com"]
        access_keys = []
        secret_keys = []
        canonical_ids = []
        account_name = []
        for account, email in zip(accounts, emails):
            account = "{}{}".format(account, str(int(time.time())))
            account_name.append(account)
            email = "{}{}".format(str(int(time.time())), email)
            resp = IAM_OBJ.create_account_s3iamcli(account, email,
                                                   self.ldap_user,
                                                   self.ldap_pwd)
            assert resp[0], resp[1]
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            canonical_ids.append(resp[1]["canonical_id"])
        bucket_name = "{}{}".format(
            "aclbucket-10838", str(int(time.time())))

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
        resp = s3_obj1.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], bucket_name, resp[1])
        self.log.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(bucket_name)
        assert_utils.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        self.log.info("Performing authenticated read acl")
        resp = acl_obj1.put_bucket_acl(
            bucket_name, acl="private")
        assert resp[0], resp[1]
        self.log.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(
            access_keys[0], secret_keys[0], bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Performing head bucket with second account credentials")
        try:
            s3_obj2.head_bucket(bucket_name)
        except CTException as error:
            self.log.debug(error.message)
            assert "Forbidden" in error.message, error.message
        self.log.info("Deleting bucket")
        s3_obj1.delete_bucket(bucket_name, force=True)
        self.log.info("Deleting multiple accounts")
        IAM_OBJ.delete_multiple_accounts(account_name)
        self.log.info(
            "Apply private canned ACL to account2 and execute "
            "head-bucket from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5722")
    @CTFailOn(error_handler)
    def test_grant_read_permission_acl_3579(self):
        """
        Grant read permission to account2 and execute head-bucket
        from account2 on a bucket. Bucket belongs to account1
        """
        self.log.info(
            "Grant read permission to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")
        accounts = ["acltestaccnt1", "acltestaccnt2"]
        emails = ["acltestaccnt1@seagate.com", "acltestaccnt2@seagate.com"]
        access_keys = []
        secret_keys = []
        canonical_ids = []
        account_name = []
        for account, email in zip(accounts, emails):
            account = "{}{}".format(account, str(int(time.time())))
            account_name.append(account)
            email = "{}{}".format(str(int(time.time())), email)
            resp = IAM_OBJ.create_account_s3iamcli(account, email,
                                                   self.ldap_user,
                                                   self.ldap_pwd)
            assert resp[0], resp[1]
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
            canonical_ids.append(resp[1]["canonical_id"])
        bucket_name = "{}{}".format(
            "aclbucket-10839", str(int(time.time())))
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
        resp = s3_obj1.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], bucket_name, resp[1])
        self.log.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(bucket_name)
        assert_utils.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        self.log.info("Performing grant read permission to second account")
        resp = acl_obj1.put_bucket_acl(
            bucket_name,
            grant_read="{}{}".format(
                "id=",
                canonical_ids[1]))
        assert resp[0], resp[1]
        self.log.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(
            access_keys[0], secret_keys[0], bucket_name)
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
        resp = s3_obj2.head_bucket(bucket_name)
        assert_utils.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        acl_obj1.put_bucket_acl(
            bucket_name,
            acl="private")
        self.log.info("Deleting bucket")
        s3_obj1.delete_bucket(bucket_name, force=True)
        self.log.info("Deleting multiple accounts")
        IAM_OBJ.delete_multiple_accounts(account_name)
        self.log.info(
            "Grant read permission to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5721")
    @CTFailOn(error_handler)
    def test_perform_head_bucket_acl_3580(self):
        """Perform a head bucket on a bucket"""
        self.log.info("Perform a head bucket on a bucket")
        bucket_name = "{}{}".format(
            "acl",
            "aclbucket-10840")
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], bucket_name, resp[1])
        resp = S3_OBJ.head_bucket(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        self.log.info("Perform a head bucket on a bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5723")
    @CTFailOn(error_handler)
    def test_create_verify_default_acl_3581(self):
        """Create a bucket and verify default ACL"""
        self.log.info("Create a bucket and verify default ACL")
        bucket_name = "{}{}".format(
            "acl",
            "aclbucket-10841")
        bucket_permission = "FULL_CONTROL"
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(resp[1], bucket_name, resp[1])
        resp = ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        assert_utils.assert_equals(
            resp[1][1][0]["Permission"],
            bucket_permission,
            resp[1])
        self.log.info("Create a bucket and verify default ACL")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8027")
    @CTFailOn(error_handler)
    def test_put_get_bucket_acl_312(self):
        """
        put bucket in account1 and get-bucket-acl for that bucket
        """
        self.log.info(
            "STARTED: put bucket in account1 and get-bucket-acl for that bucket")
        bkt_name = "{}{}".format("acl", "bucket-312-{}".format(self.random_id))
        self.log.info("Step 1: Creating bucket: %s", bkt_name)
        resp = S3_OBJ.create_bucket(bkt_name)
        assert resp[0], resp[1]
        self.log.info("Step 1: Bucket: %s created", bkt_name)
        self.log.info("Step 2: Retrieving bucket acl attributes")
        resp = ACL_OBJ.get_bucket_acl(bkt_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket ACL was verified")
        self.log.info(
            "ENDED: put bucket in account1 and get-bucket-acl for that bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8029")
    @CTFailOn(error_handler)
    def test_put_get_bucket_acl_313(self):
        """acc1: put bucket, acc2: no permissions or canned acl, get-bucket-acl details"""
        self.log.info(
            "STARTED:acc1: put bucket, acc2: no permissions or canned acl, get-bucket-acl details")
        bkt_name = "{}{}".format(
            "acl", "bucket-313-{}".format(self.random_id))
        acc_name_2 = "acltestaccnt313_{}".format(self.random_id)
        emailid_2 = "acltestaccnt313_{}@seagate.com".format(self.random_id)
        self.log.info("Step 1: Creating bucket: %s", bkt_name)
        resp = S3_OBJ.create_bucket(bkt_name)
        assert resp[0], resp[1]
        self.log.info("Step 1: Bucket : %s created", bkt_name)
        create_acc = IAM_OBJ.create_s3iamcli_acc(acc_name_2, emailid_2)
        assert create_acc[0], create_acc[1]
        acl_test_2 = create_acc[1][2]
        self.log.info(
            "Step 2: Retrieving bucket acl attributes using account 2")
        try:
            acl_test_2.get_bucket_acl(bkt_name)
        except CTException as error:
            self.log.error(error.message)
            assert "AccessDenied" in error.message, error.message
            self.log.info(
                "Step 2: retrieving bucket acl using account 2 failed with error %s",
                "AccessDenied")
        self.log.info(
            "ENDED:acc1: put bucket, acc2: no permissions or canned acl, get-bucket-acl details")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8030")
    @CTFailOn(error_handler)
    def test_put_get_bucket_acl_431(self):
        """acc1 -put bucket, acc2- give read-acp permissions,acc1- get-bucket-acl"""
        self.log.info(
            "STARTED:acc1 -put bucket, acc2- give read-acp permissions,acc1-get-bucket-acl")
        bkt_name = "{}{}".format("acl", "bucket-431-{}".format(self.random_id))
        acc_name_2 = "acltestaccnt431_{}".format(self.random_id)
        emailid_2 = "acltestaccnt431_{}@seagate.com".format(self.random_id)
        self.log.info("Step 1: Creating bucket: %s", bkt_name)
        resp = S3_OBJ.create_bucket(bkt_name)
        assert resp[0], resp[1]
        self.log.info("Step 1: Bucket : %s is created", bkt_name)
        create_acc = IAM_OBJ.create_s3iamcli_acc(acc_name_2, emailid_2)
        assert create_acc[0], create_acc[1]
        cannonical_id = create_acc[1][0]
        acl_test_2 = create_acc[1][2]
        self.log.info("Step 2: Performing authenticated read acp")
        resp = ACL_OBJ.put_bucket_acl(
            bkt_name, grant_read_acp="id={}".format(cannonical_id))
        assert resp[0], resp[1]
        self.log.info(
            "Step 2:Bucket with read ACP permission was set for acc2")
        self.log.info("Step 3: Retrieving bucket acl attributes")
        resp = acl_test_2.get_bucket_acl(bkt_name)
        assert resp[0], resp[1]
        self.log.info("Step 3: Bucket ACL was verified")
        self.log.info(
            "ENDED:acc1 -put bucket, acc2- give read-acp permissions,acc1- get-bucket-acl")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8712")
    @CTFailOn(error_handler)
    def test_full_control_acl_6423(self):
        """Test full-control on bucket to cross account and test delete bucket from owner account"""
        self.log.info(
            "STARTED: Test full-control on bucket to cross account and test delete")
        bkt_name = "{0}{1}".format(
            "acl", "bucket-6423-{}".format(self.random_id))
        create_acc = IAM_OBJ.create_s3iamcli_acc(
            self.account_name, self.email_id)
        assert create_acc[0], create_acc[1]
        cannonical_id = create_acc[1][0]
        self.log.info("Step 1: Creating bucket with name %s", bkt_name)
        resp = S3_OBJ.create_bucket(bkt_name)
        assert resp[0], resp[1]
        self.log.info("Step 1: Created a bucket with name %s", bkt_name)
        self.log.info("Step 2: Verifying that bucket is created")
        resp = S3_OBJ.bucket_list()
        assert resp[0], resp[1]
        assert bkt_name in resp[1]
        self.log.info("Step 2: Verified that bucket is created")
        self.log.info(
            "Step 3:Performing put bucket acl for bucket %s for full control",
            bkt_name)
        resp = ACL_OBJ.put_bucket_acl(
            bkt_name, grant_full_control="id={}".format(cannonical_id))
        assert resp[0], resp[1]
        self.log.info(
            "Step 3:Performed put bucket, bucket %s for account 2",
            bkt_name)
        self.log.info("Step 4: Retrieving acl of a bucket %s", bkt_name)
        resp = ACL_OBJ.get_bucket_acl(bkt_name)
        assert resp[0], resp[1]
        self.log.info("Step 4: Retrieved acl of a bucket %s", bkt_name)
        self.log.info("Step 5: Deleting a bucket %s", bkt_name)
        resp = S3_OBJ.delete_bucket(bkt_name)
        assert resp[0], resp[1]
        self.log.info("Step 5: Deleted a bucket %s", bkt_name)
        self.log.info("Step 6: Verifying that bucket is deleted")
        resp = S3_OBJ.bucket_list()
        assert resp[0], resp[1]
        assert bkt_name not in resp[1], resp[1]
        self.log.info("Step 6: Verified that bucket is deleted")
        self.log.info(
            "ENDED: Test full-control on bucket to cross account and test delete")
