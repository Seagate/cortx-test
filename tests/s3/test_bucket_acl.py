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

import copy
import time
import logging
import pytest
from commons.helpers import node_helper
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils import assert_utils
from commons.constants import const
from libs.s3 import s3_test_lib, iam_test_lib, s3_acl_test_lib

S3_OBJ = s3_test_lib.S3TestLib()
IAM_OBJ = iam_test_lib.IamTestLib()
ACL_OBJ = s3_acl_test_lib.S3AclTestLib()
UTILS = node_helper.Node()

BKT_ACL_CONFIG = read_yaml("config/s3/test_bucket_acl.yaml")[1]
CMN_CONF = read_yaml("config/common_config.yaml")[1]
LOGGER = logging.getLogger(__name__)
ASRTOBJ = assert_utils


class TestBucketACL():
    """Bucket ACL Test suite."""

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
        LOGGER.info("STARTED: Setup Operations")
        self.random_id = str(time.time())
        self.account_name = "{}{}".format(
            BKT_ACL_CONFIG["bucket_acl"]["acc_name_prefix"],
            BKT_ACL_CONFIG["bucket_acl"]["acc_name"])
        self.email_id = "{}{}".format(
            self.account_name,
            BKT_ACL_CONFIG["bucket_acl"]["email_suffix"])
        self.ldap_user = const.S3_BUILD_VER[CMN_CONF["BUILD_VER_TYPE"]
                                            ]["ldap_creds"]["ldap_username"]
        self.ldap_pwd = const.S3_BUILD_VER[CMN_CONF["BUILD_VER_TYPE"]
                                           ]["ldap_creds"]["ldap_passwd"]
        LOGGER.info("ENDED: Setup Operations")

    def teardown_method(self):
        """Function to perform the clean up for each test."""
        LOGGER.info("STARTED: Teardown Operations")
        LOGGER.info("Deleting buckets in default account")
        resp = S3_OBJ.bucket_list()
        pref_list = [
            each_bucket for each_bucket in resp[1] if each_bucket.startswith(
                BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"])]
        for bucket in pref_list:
            ACL_OBJ.put_bucket_acl(
                bucket, acl=BKT_ACL_CONFIG["bucket_acl"]["bkt_permission"])
        S3_OBJ.delete_multiple_buckets(pref_list)
        LOGGER.info("Deleted buckets in default account")
        LOGGER.info(
            "Deleting IAM accounts with prefix: %s", self.account_name)
        acc_list = IAM_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)[1]
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        LOGGER.info(all_acc)
        for acc_name in all_acc:
            resp = IAM_OBJ.reset_account_access_key_s3iamcli(
                acc_name,
                self.ldap_user,
                self.ldap_pwd)
            access_key = resp[1]["AccessKeyId"]
            secret_key = resp[1]["SecretKey"]
            s3_obj_temp = s3_test_lib.S3TestLib(access_key, secret_key)
            LOGGER.info(
                "Deleting buckets in %s account if any", acc_name)
            bucket_list = s3_obj_temp.bucket_list()[1]
            LOGGER.info(bucket_list)
            s3_obj_acl = s3_acl_test_lib.S3AclTestLib(
                access_key, secret_key)
            for bucket in bucket_list:
                s3_obj_acl.put_bucket_acl(bucket, acl="private")
            s3_obj_temp.delete_all_buckets()
            IAM_OBJ.reset_access_key_and_delete_account_s3iamcli(acc_name)
        LOGGER.info("Deleted IAM accounts successfully")
        LOGGER.info("ENDED: Teardown Operations")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5717", "get_bucket_acl")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3012(self):
        """verify Get Bucket ACL of existing Bucket."""
        LOGGER.info("verify Get Bucket ACL of existing Bucket")
        bucket_name = "{}{}".format(
            BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"],
            BKT_ACL_CONFIG["test_10008"]["bucket_name"])
        bucket_permission = BKT_ACL_CONFIG["test_10008"]["bucket_permission"]
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp = ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(
            resp[1][1][0]["Permission"],
            bucket_permission,
            resp[1])
        LOGGER.info("verify Get Bucket ACL of existing Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5719", "get_bucket_acl")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3013(self):
        """verify Get Bucekt ACL of non existing Bucket."""
        LOGGER.info("verify Get Bucket ACL of non existing Bucket")
        bucket_name = BKT_ACL_CONFIG["test_10009"]["bucket_name"]
        try:
            ACL_OBJ.get_bucket_acl(bucket_name)
        except CTException as error:
            assert BKT_ACL_CONFIG["test_10009"]["err_message"] not in str(
                error.message), error.message
        LOGGER.info("verify Get Bucket ACL of non existing Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5712", "get_bucket_acl")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3014(self):
        """verify Get Bucket ACL of an empty Bucket."""
        LOGGER.info("verify Get Bucket ACL of an empty Bucket")
        bucket_name = "{}{}".format(
            BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"],
            BKT_ACL_CONFIG["test_10010"]["bucket_name"])
        bucket_permission = BKT_ACL_CONFIG["test_10010"]["bucket_permission"]
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp = ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(
            resp[1][1][0]["Permission"],
            bucket_permission,
            resp[1])
        LOGGER.info("verify Get Bucket ACL of an empty Bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5718", "get_bucket_acl")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3015(self):
        """verify Get Bucket ACL of an existing Bucket having objects."""
        LOGGER.info(
            "verify Get Bucket ACL of an existing Bucket having objects")
        bucket_name = "{}{}".format(
            BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"],
            BKT_ACL_CONFIG["test_10011"]["bucket_name"])
        bucket_permission = BKT_ACL_CONFIG["test_10011"]["bucket_permission"]
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        UTILS.create_file(BKT_ACL_CONFIG["test_10011"]["file_path"],
                          BKT_ACL_CONFIG["test_10011"]["file_size"])
        resp = S3_OBJ.object_upload(bucket_name,
                                    BKT_ACL_CONFIG["test_10011"]["obj_name"],
                                    BKT_ACL_CONFIG["test_10011"]["file_path"])
        assert resp[0], resp[1]
        assert resp[0], resp[1]
        resp = ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(
            resp[1][1][0]["Permission"],
            bucket_permission,
            resp[1])
        LOGGER.info(
            "verify Get Bucket ACL of an existing Bucket having objects")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5713", "get_bucket_acl")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3016(self):
        """Verify Get Bucket ACL without Bucket name."""
        LOGGER.info("Verify Get Bucket ACL without Bucket name")
        try:
            ACL_OBJ.get_bucket_acl(None)
        except CTException as error:
            assert BKT_ACL_CONFIG["test_10012"]["err_message"] in str(
                error.message), error.message
        LOGGER.info("Verify Get Bucket ACL without Bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5720", "get_bucket_acl")
    @CTFailOn(error_handler)
    def test_delete_and_verify_bucket_acl_3017(self):
        """Delete Bucket and verify Bucket ACL."""
        LOGGER.info("Delete Bucket and verify Bucket ACL")
        bucket_name = "{}{}".format(
            BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"],
            BKT_ACL_CONFIG["test_10013"]["bucket_name"])
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp = S3_OBJ.delete_bucket(bucket_name)
        assert resp[0], resp[1]
        try:
            ACL_OBJ.get_bucket_acl(bucket_name)
        except CTException as error:
            assert BKT_ACL_CONFIG["test_10013"]["err_message"] in str(
                error.message), error.message
        LOGGER.info("Delete Bucket and verify Bucket ACL")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5716", "get_bucket_acl")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3018(self):
        """verify Get Bucket ACL of existing Bucket with associated Account credentials."""
        LOGGER.info(
            "verify Get Bucket ACL of existing Bucket with associated Account credentials")
        acc_name = "{}{}".format(self.account_name, str(int(time.time())))
        email = "{}{}".format(str(int(time.time())), self.email_id,)
        resp = IAM_OBJ.create_account_s3iamcli(acc_name,
                                               email,
                                               self.ldap_user, self.ldap_pwd)
        assert resp[0], resp[1]
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        bucket_name = "{}{}{}".format(
            BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"],
            BKT_ACL_CONFIG["test_10014"]["bucket_name"],
            str(
                int(
                    time.time())))
        bucket_permission = BKT_ACL_CONFIG["test_10014"]["bucket_permission"]
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
        ASRTOBJ.assert_equals(
            resp[1][1][0]["Permission"],
            bucket_permission,
            resp[1])
        LOGGER.info(
            "verify Get Bucket ACL of existing Bucket with associated Account credentials")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5715", "get_bucket_acl")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3019(self):
        """verify Get Bucket ACL of existing Bucket with different Account credentials."""
        LOGGER.info(
            "verify Get Bucket ACL of existing Bucket with different Account credentials")
        accounts = BKT_ACL_CONFIG["test_10015"]["accounts"]
        emails = BKT_ACL_CONFIG["test_10015"]["emails"]
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
            BKT_ACL_CONFIG["test_10015"]["bucket_name"], str(int(time.time())))
        err_message = BKT_ACL_CONFIG["test_10015"]["err_message"]
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
        LOGGER.info(
            "verify Get Bucket ACL of existing Bucket with different Account credentials")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5714", "get_bucket_acl")
    @CTFailOn(error_handler)
    def test_verify_get_bucket_acl_3020(self):
        """verify Get Bucket ACL of existing Bucket with IAM User credentials."""
        LOGGER.info(
            "verify Get Bucket ACL of existing Bucket with IAM User credentials")
        accounts = BKT_ACL_CONFIG["test_10016"]["accounts"]
        emails = BKT_ACL_CONFIG["test_10016"]["emails"]
        user_name = BKT_ACL_CONFIG["test_10016"]["user_name"]
        access_keys = []
        secret_keys = []
        for account, email in zip(accounts, emails):
            account = "{}{}".format(account, str(int(time.time())))
            email = "{}{}".format(str(int(time.time())), email)
            resp = IAM_OBJ.create_account_s3iamcli(account, email,
                                                   self.ldap_user,
                                                   self.ldap_pwd)
            assert resp[0], resp[1]
            access_keys.append(resp[1]["access_key"])
            secret_keys.append(resp[1]["secret_key"])
        bucket_name = "{}{}".format(
            BKT_ACL_CONFIG["test_10016"]["bucket_name"], str(int(time.time())))
        err_message = BKT_ACL_CONFIG["test_10016"]["err_message"]
        s3_obj_acl = s3_test_lib.S3TestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        resp = s3_obj_acl.create_bucket(bucket_name)
        assert resp[0], resp[1]
        resp = s3_obj_acl.bucket_list()
        assert resp[0], resp[1]
        assert bucket_name in resp[1], resp[1]
        IAM_OBJ_acl = iam_test_lib.IamTestLib(
            access_key=access_keys[1],
            secret_key=secret_keys[1])
        resp = IAM_OBJ_acl.create_user(user_name)
        assert resp[0], resp[1]
        resp = IAM_OBJ_acl.create_access_key(user_name)
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
        LOGGER.info(
            "verify Get Bucket ACL of existing Bucket with IAM User credentials")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5728", "create_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_bucket_3527(self):
        """Add canned ACL bucket-owner-full-control along with READ ACL grant permission."""
        LOGGER.info(
            "Add canned ACL bucket-owner-full-control along with READ ACL grant permission")
        self.helper_method(BKT_ACL_CONFIG["test_10766"]["bucket_name"],
                           BKT_ACL_CONFIG["test_10766"]["acl"],
                           BKT_ACL_CONFIG["test_10766"]["error"])
        LOGGER.info(
            "Add canned ACL bucket-owner-full-control along with READ ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5727", "create_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_bucket_3528(self):
        """Add canned ACL bucket-owner-read along with READ ACL grant permission."""
        LOGGER.info(
            "Add canned ACL bucket-owner-read along with READ ACL grant permission")
        self.helper_method(BKT_ACL_CONFIG["test_10767"]["bucket_name"],
                           BKT_ACL_CONFIG["test_10767"]["acl"],
                           BKT_ACL_CONFIG["test_10767"]["error"])
        LOGGER.info(
            "Add canned ACL bucket-owner-read along with READ ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5736", "create_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3529(self):
        """Add canned ACL "private" along with "READ" ACL grant permission."""
        LOGGER.info(
            "Add canned ACL 'private' along with 'READ' ACL grant permission")
        self.helper_method(BKT_ACL_CONFIG["test_10768"]["bucket_name"],
                           BKT_ACL_CONFIG["test_10768"]["acl"],
                           BKT_ACL_CONFIG["test_10768"]["error"])
        LOGGER.info(
            "Add canned ACL 'private' along with 'READ' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5737", "create_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3530(self):
        """Add canned ACL "private" along with "FULL_CONTROL" ACL grant permission."""
        LOGGER.info(
            "Add canned ACL 'private' along with 'FULL_CONTROL' ACL grant permission")
        self.helper_method(BKT_ACL_CONFIG["test_10769"]["bucket_name"],
                           BKT_ACL_CONFIG["test_10769"]["acl"],
                           BKT_ACL_CONFIG["test_10769"]["error"])
        LOGGER.info(
            "Add canned ACL 'private' along with 'FULL_CONTROL' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5732", "create_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_3531(self):
        """Add canned ACL "public-read" along with "READ_ACP" ACL grant permission."""
        LOGGER.info(
            "Add canned ACL 'public-read' along with 'READ_ACP' ACL grant permission")
        self.helper_method(BKT_ACL_CONFIG["test_10770"]["bucket_name"],
                           BKT_ACL_CONFIG["test_10770"]["acl"],
                           BKT_ACL_CONFIG["test_10770"]["error"])
        LOGGER.info(
            "Add canned ACL 'public-read' along with 'READ_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5731", "create_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_3532(self):
        """Add canned ACL "public-read" along with "WRITE_ACP" ACL grant permission."""
        LOGGER.info(
            "Add canned ACL 'public-read' along with 'WRITE_ACP' ACL grant permission")
        self.helper_method(BKT_ACL_CONFIG["test_10771"]["bucket_name"],
                           BKT_ACL_CONFIG["test_10771"]["acl"],
                           BKT_ACL_CONFIG["test_10771"]["error"])
        LOGGER.info(
            "Add canned ACL 'public-read' along with 'WRITE_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5729", "create_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_write_3533(self):
        """Add canned ACL 'public-read-write' along with "WRITE_ACP" ACL grant permission."""
        LOGGER.info(
            "Add canned ACL 'public-read-write' along with 'WRITE_ACP' ACL grant permission")
        self.helper_method(BKT_ACL_CONFIG["test_10772"]["bucket_name"],
                           BKT_ACL_CONFIG["test_10772"]["acl"],
                           BKT_ACL_CONFIG["test_10772"]["error"])
        LOGGER.info(
            "Add canned ACL 'public-read-write' along with 'WRITE_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5730", "create_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_public_read_write_3534(self):
        """Add canned ACL 'public-read-write' along with "FULL_CONTROL" ACL grant permission."""
        LOGGER.info(
            "Add canned ACL 'public-read-write' along with 'FULL_CONTROL' ACL grant permission")
        self.helper_method(BKT_ACL_CONFIG["test_10773"]["bucket_name"],
                           BKT_ACL_CONFIG["test_10773"]["acl"],
                           BKT_ACL_CONFIG["test_10773"]["error"])
        LOGGER.info(
            "Add canned ACL 'public-read-write' along with 'FULL_CONTROL' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5739", "create_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_authenticate_read_3535(self):
        """Add canned ACL 'authenticate-read' along with "READ" ACL grant permission."""
        LOGGER.info(
            "Add canned ACL 'authenticate-read' along with 'READ' ACL grant permission")
        self.helper_method(BKT_ACL_CONFIG["test_10774"]["bucket_name"],
                           BKT_ACL_CONFIG["test_10774"]["acl"],
                           BKT_ACL_CONFIG["test_10774"]["error"])
        LOGGER.info(
            "Add canned ACL 'authenticate-read' along with 'READ' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5738", "create_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_authenticate_read_3536(self):
        """Add canned ACL 'authenticate-read' along with "READ_ACP" ACL grant permission."""
        LOGGER.info(
            "Add canned ACL 'authenticate-read' along with 'READ_ACP' ACL grant permission")
        self.helper_method(BKT_ACL_CONFIG["test_10775"]["bucket_name"],
                           BKT_ACL_CONFIG["test_10775"]["acl"],
                           BKT_ACL_CONFIG["test_10775"]["error"])
        LOGGER.info(
            "Add canned ACL 'authenticate-read' along with 'READ_ACP' ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5735", "put_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3537(self):
        """
        Add canned ACL "private" as a request header along with FULL_CONTROL
        ACL grant permission as request body
        """
        LOGGER.info(
            "Add canned ACL 'private' as a request header along with FULL_CONTROL"
            " ACL grant permission as request body")
        account_name = "{}{}".format(
            BKT_ACL_CONFIG["test_10776"]["account_name"], str(int(time.time())))
        email_id = "{}{}".format(str(int(time.time())),
                                 BKT_ACL_CONFIG["test_10776"]["email_id"])
        bucket_name = "{}{}".format(
            str(int(time.time())), BKT_ACL_CONFIG["test_10776"]["bucket_name"])
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
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        resp = s3_obj_acl.get_bucket_acl(bucket_name=bucket_name)
        newresp = {"Owner": resp[1][0], "Grants": resp[1][1]}
        LOGGER.info(
            "New dict to pass ACP with permission private:%s", newresp)
        newresp["Grants"][0]["Permission"] = BKT_ACL_CONFIG["test_10776"]["acl"]
        try:
            s3_obj_acl.put_bucket_acl(
                bucket_name=bucket_name,
                acl=BKT_ACL_CONFIG["test_10776"]["canned_acl"],
                access_control_policy=newresp)
        except CTException as error:
            LOGGER.debug(error.message)
            assert BKT_ACL_CONFIG["test_10776"]["error_message"] in error.message, error.message
        LOGGER.info("Cleanup activity")
        LOGGER.info("Deleting a bucket %s", bucket_name)
        resp = s3_test.delete_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Deleting an account %s", account_name)
        resp = IAM_OBJ.delete_account_s3iamcli(
            account_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info(
            "Add canned ACL 'private' as a request header along with FULL_CONTROL"
            " ACL grant permission as request body")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5733", "put_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3538(self):
        """
        Add canned ACL "private" in request body along with "FULL_CONTROL"
        ACL grant permission in request header
        """
        LOGGER.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request header")
        account_name = "{}{}".format(
            BKT_ACL_CONFIG["test_10777"]["account_name"], str(int(time.time())))
        email_id = "{}{}".format(str(int(time.time())),
                                 BKT_ACL_CONFIG["test_10777"]["email_id"])
        bucket_name = "{}{}".format(
            str(int(time.time())), BKT_ACL_CONFIG["test_10777"]["bucket_name"])
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
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])

        resp = s3_obj_acl.get_bucket_acl(bucket_name=bucket_name)
        newresp = {"Owner": resp[1][0], "Grants": resp[1][1]}
        LOGGER.info(
            "New dict to pass ACP with permission private:%s", newresp)
        newresp["Grants"][0]["Permission"] = BKT_ACL_CONFIG["test_10777"]["canned_acl"]
        try:
            s3_obj_acl.put_bucket_acl(
                bucket_name=bucket_name,
                acl=BKT_ACL_CONFIG["test_10777"]["acl"],
                access_control_policy=newresp)
        except CTException as error:
            LOGGER.debug(error.message)
            assert BKT_ACL_CONFIG["test_10777"]["error_message"] in error.message, error.message
        LOGGER.info("Cleanup activity")
        LOGGER.info("Deleting a bucket %s", bucket_name)
        resp = s3_test.delete_bucket(bucket_name, force=True)
        assert resp[0], resp[1]
        LOGGER.info("Deleting an account %s", account_name)
        resp = IAM_OBJ.delete_account_s3iamcli(
            account_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request header")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5734", "put_bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_private_3539(self):
        """
        Add canned ACL "private" in request body along with "FULL_CONTROL"
        ACL grant permission in request body
        """
        LOGGER.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request body")

        account_name = "{}{}".format(
            BKT_ACL_CONFIG["test_10778"]["account_name"], str(int(time.time())))
        email_id = "{}{}".format(str(int(time.time())),
                                 BKT_ACL_CONFIG["test_10778"]["email_id"])
        bucket_name = "{}{}".format(
            str(int(time.time())), BKT_ACL_CONFIG["test_10778"]["bucket_name"])
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
        canonical_id = resp[1]["canonical_id"]
        s3_test = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        s3_obj_acl = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key, secret_key=secret_key)
        resp = s3_test.create_bucket(bucket_name=bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        resp = s3_obj_acl.get_bucket_acl(bucket_name=bucket_name)
        newresp = {"Owner": resp[1][0], "Grants": resp[1][1]}
        LOGGER.info(
            "New dict to pass ACP with permission private:%s", newresp)
        newresp["Grants"][0]["Permission"] = BKT_ACL_CONFIG["test_10778"]["canned_acl"]
        new_grant = {
            "Grantee": {
                "ID": canonical_id,
                "Type": "CanonicalUser",
            },
            "Permission": BKT_ACL_CONFIG["test_10778"]["acl"],
        }
        # If we don"t want to modify the original ACL variable, then we
        # must do a deepcopy
        modified_acl = copy.deepcopy(newresp)
        modified_acl["Grants"].append(new_grant)
        LOGGER.info(
            "ACP with permission private and Full control:%s", modified_acl)
        try:
            s3_obj_acl.put_bucket_acl(
                bucket_name=bucket_name,
                access_control_policy=newresp)
        except CTException as error:
            LOGGER.debug(error.message)
            assert BKT_ACL_CONFIG["test_10778"]["error_message"] in error.message, error.message
        LOGGER.info("Cleanup activity")
        LOGGER.info("Deleting a bucket %s", bucket_name)
        resp = s3_test.delete_bucket(bucket_name)
        assert resp[0], resp[1]
        LOGGER.info("Deleting an account %s", account_name)
        resp = IAM_OBJ.delete_account_s3iamcli(
            account_name, access_key, secret_key)
        assert resp[0], resp[1]
        LOGGER.info(
            "Add canned ACL private in request body along with FULL_CONTROL"
            " ACL grant permission in request body")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5726", "bucket_acl")
    @CTFailOn(error_handler)
    def test_add_canned_acl_authenticated_read_3577(self):
        """
        Apply authenticated-read canned ACL to account2 and execute head-bucket from
        account2 on a bucket. Bucket belongs to account1
        """
        LOGGER.info(
            "Apply authenticated-read canned ACL to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")
        accounts = BKT_ACL_CONFIG["test_10837"]["accounts"]
        emails = BKT_ACL_CONFIG["test_10837"]["emails"]
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
            BKT_ACL_CONFIG["test_10837"]["bucket_name"], str(int(time.time())))

        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        acl_obj1 = s3_acl_test_lib.S3AclTestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=access_keys[1],
            secret_key=secret_keys[1])

        LOGGER.info("Creating new bucket from first account")
        resp = s3_obj1.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(bucket_name)
        ASRTOBJ.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        LOGGER.info("Performing authenticated read acl")
        resp = acl_obj1.put_bucket_acl(
            bucket_name, acl=BKT_ACL_CONFIG["test_10837"]["bucket_acl"])
        assert resp[0], resp[1]
        LOGGER.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(
            access_keys[0], secret_keys[0], bucket_name)
        assert resp[0], resp[1]
        print("aa {}".format(resp))
        assert BKT_ACL_CONFIG["test_10837"]["grant_permission"] in resp[1][1][1]["Permission"], \
            resp[1]
        LOGGER.info(
            "Performing head bucket with second account credentials")
        resp = s3_obj2.head_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        LOGGER.info("Deleting bucket")
        s3_obj1.delete_bucket(bucket_name, force=True)
        LOGGER.info("Deleting multiple accounts")
        IAM_OBJ.delete_multiple_accounts(account_name)
        LOGGER.info(
            "Apply authenticated-read canned ACL to account2 and execute "
            "head-bucket from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5724", "bucket_acl")
    @CTFailOn(error_handler)
    def test_apply_private_canned_acl_3578(self):
        """
        Summary: Apply private canned ACL to account2 and execute head-bucket

        Description: Apply private canned ACL to account2 and execute head-bucket
        from account2 on a bucket. Bucket belongs to account1
        """
        LOGGER.info(
            "Apply private canned ACL to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")
        accounts = BKT_ACL_CONFIG["test_10838"]["accounts"]
        emails = BKT_ACL_CONFIG["test_10838"]["emails"]
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
            BKT_ACL_CONFIG["test_10838"]["bucket_name"], str(int(time.time())))

        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        acl_obj1 = s3_acl_test_lib.S3AclTestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=access_keys[1],
            secret_key=secret_keys[1])

        LOGGER.info("Creating new bucket from first account")
        resp = s3_obj1.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(bucket_name)
        ASRTOBJ.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        LOGGER.info("Performing authenticated read acl")
        resp = acl_obj1.put_bucket_acl(
            bucket_name, acl=BKT_ACL_CONFIG["test_10838"]["bucket_acl"])
        assert resp[0], resp[1]
        LOGGER.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(
            access_keys[0], secret_keys[0], bucket_name)
        assert resp[0], resp[1]
        LOGGER.info(
            "Performing head bucket with second account credentials")
        try:
            s3_obj2.head_bucket(bucket_name)
        except CTException as error:
            LOGGER.debug(error.message)
            assert BKT_ACL_CONFIG["test_10838"]["error_message"] in error.message, error.message
        LOGGER.info("Deleting bucket")
        s3_obj1.delete_bucket(bucket_name, force=True)
        LOGGER.info("Deleting multiple accounts")
        IAM_OBJ.delete_multiple_accounts(account_name)
        LOGGER.info(
            "Apply private canned ACL to account2 and execute "
            "head-bucket from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5722", "bucket_acl")
    @CTFailOn(error_handler)
    def test_grant_read_permission_acl_3579(self):
        """
        Grant read permission to account2 and execute head-bucket
        from account2 on a bucket. Bucket belongs to account1
        """
        LOGGER.info(
            "Grant read permission to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")
        accounts = BKT_ACL_CONFIG["test_10839"]["accounts"]
        emails = BKT_ACL_CONFIG["test_10839"]["emails"]
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
            BKT_ACL_CONFIG["test_10839"]["bucket_name"], str(int(time.time())))
        s3_obj1 = s3_test_lib.S3TestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        acl_obj1 = s3_acl_test_lib.S3AclTestLib(
            access_key=access_keys[0],
            secret_key=secret_keys[0])
        s3_obj2 = s3_test_lib.S3TestLib(
            access_key=access_keys[1],
            secret_key=secret_keys[1])

        LOGGER.info("Creating new bucket from first account")
        resp = s3_obj1.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        LOGGER.info("Performing head bucket with first account credentials")
        resp = s3_obj1.head_bucket(bucket_name)
        ASRTOBJ.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        LOGGER.info("Performing grant read permission to second account")
        resp = acl_obj1.put_bucket_acl(
            bucket_name,
            grant_read="{}{}".format(
                BKT_ACL_CONFIG["test_10839"]["id_str"],
                canonical_ids[1]))
        assert resp[0], resp[1]
        LOGGER.info("Getting bucket acl")
        resp = acl_obj1.get_bucket_acl_using_iam_credentials(
            access_keys[0], secret_keys[0], bucket_name)
        ASRTOBJ.assert_equals(
            resp[1][1][0]["Grantee"]["DisplayName"],
            account_name[1],
            resp[1])
        ASRTOBJ.assert_equals(
            BKT_ACL_CONFIG["test_10839"]["grant_permission"],
            resp[1][1][0]["Permission"],
            resp[1])
        LOGGER.info(
            "Performing head bucket with second account credentials")
        resp = s3_obj2.head_bucket(bucket_name)
        ASRTOBJ.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        acl_obj1.put_bucket_acl(
            bucket_name,
            acl=BKT_ACL_CONFIG["test_10839"]["default_acl"])
        LOGGER.info("Deleting bucket")
        s3_obj1.delete_bucket(bucket_name, force=True)
        LOGGER.info("Deleting multiple accounts")
        IAM_OBJ.delete_multiple_accounts(account_name)
        LOGGER.info(
            "Grant read permission to account2 and execute head-bucket "
            "from account2 on a bucket. Bucket belongs to account1")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5721", "bucket_acl")
    @CTFailOn(error_handler)
    def test_perform_head_bucket_acl_3580(self):
        """Perform a head bucket on a bucket"""
        LOGGER.info("Perform a head bucket on a bucket")
        bucket_name = "{}{}".format(
            BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"],
            BKT_ACL_CONFIG["test_10840"]["bucket_name"])
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        resp = S3_OBJ.head_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1]["BucketName"], bucket_name, resp[1])
        LOGGER.info("Perform a head bucket on a bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5723", "bucket_acl")
    @CTFailOn(error_handler)
    def test_create_verify_default_acl_3581(self):
        """Create a bucket and verify default ACL"""
        LOGGER.info("Create a bucket and verify default ACL")
        bucket_name = "{}{}".format(
            BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"],
            BKT_ACL_CONFIG["test_10841"]["bucket_name"])
        bucket_permission = BKT_ACL_CONFIG["test_10841"]["bucket_permission"]
        resp = S3_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(resp[1], bucket_name, resp[1])
        resp = ACL_OBJ.get_bucket_acl(bucket_name)
        assert resp[0], resp[1]
        ASRTOBJ.assert_equals(
            resp[1][1][0]["Permission"],
            bucket_permission,
            resp[1])
        LOGGER.info("Create a bucket and verify default ACL")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8027", "bucket_acl")
    @CTFailOn(error_handler)
    def test_put_get_bucket_acl_312(self):
        """
        put bucket in account1 and get-bucket-acl for that bucket
        """
        LOGGER.info(
            "STARTED: put bucket in account1 and get-bucket-acl for that bucket")
        test_cfg = BKT_ACL_CONFIG["test_312"]
        bkt_name = "{}{}".format(
            BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"],
            test_cfg["bucket_name"].format(self.random_id))
        LOGGER.info("Step 1: Creating bucket: %s", bkt_name)
        resp = S3_OBJ.create_bucket(bkt_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Bucket: %s created", bkt_name)
        LOGGER.info("Step 2: Retrieving bucket acl attributes")
        resp = ACL_OBJ.get_bucket_acl(bkt_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 2: Bucket ACL was verified")
        LOGGER.info(
            "ENDED: put bucket in account1 and get-bucket-acl for that bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8029", "bucket_acl")
    @CTFailOn(error_handler)
    def test_put_get_bucket_acl_313(self):
        """acc1: put bucket, acc2: no permissions or canned acl, get-bucket-acl details"""
        LOGGER.info(
            "STARTED:acc1: put bucket, acc2: no permissions or canned acl, get-bucket-acl details")
        test_cfg = BKT_ACL_CONFIG["test_313"]
        bkt_name = "{}{}".format(
            BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"],
            test_cfg["bucket_name"].format(self.random_id))
        acc_name_2 = test_cfg["account_name"].format(self.random_id)
        emailid_2 = test_cfg["email_id"].format(self.random_id)
        LOGGER.info("Step 1: Creating bucket: %s", bkt_name)
        resp = S3_OBJ.create_bucket(bkt_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Bucket : %s created", bkt_name)
        create_acc = IAM_OBJ.create_s3iamcli_acc(acc_name_2, emailid_2)
        assert create_acc[0], create_acc[1]
        acl_test_2 = create_acc[1][2]
        LOGGER.info(
            "Step 2: Retrieving bucket acl attributes using account 2")
        try:
            acl_test_2.get_bucket_acl(bkt_name)
        except CTException as error:
            LOGGER.error(error.message)
            assert test_cfg["err_message"] in error.message, error.message
            LOGGER.info(
                "Step 2: retrieving bucket acl using account 2 failed with error %s",
                test_cfg["err_message"])
        LOGGER.info(
            "ENDED:acc1: put bucket, acc2: no permissions or canned acl, get-bucket-acl details")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8030", "bucket_acl")
    @CTFailOn(error_handler)
    def test_put_get_bucket_acl_431(self):
        """acc1 -put bucket, acc2- give read-acp permissions,acc1- get-bucket-acl"""
        LOGGER.info(
            "STARTED:acc1 -put bucket, acc2- give read-acp permissions,acc1-get-bucket-acl")
        test_cfg = BKT_ACL_CONFIG["test_431"]
        bkt_name = "{}{}".format(
            BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"],
            test_cfg["bucket_name"].format(self.random_id))
        acc_name_2 = test_cfg["account_name"].format(self.random_id)
        emailid_2 = test_cfg["email_id"].format(self.random_id)
        LOGGER.info("Step 1: Creating bucket: %s", bkt_name)
        resp = S3_OBJ.create_bucket(bkt_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Bucket : %s is created", bkt_name)
        create_acc = IAM_OBJ.create_s3iamcli_acc(acc_name_2, emailid_2)
        assert create_acc[0], create_acc[1]
        cannonical_id = create_acc[1][0]
        acl_test_2 = create_acc[1][2]
        LOGGER.info("Step 2: Performing authenticated read acp")
        resp = ACL_OBJ.put_bucket_acl(
            bkt_name, grant_read_acp=test_cfg["id_str"].format(cannonical_id))
        assert resp[0], resp[1]
        LOGGER.info("Step 2:Bucket with read ACP permission was set for acc2")
        LOGGER.info("Step 3: Retrieving bucket acl attributes")
        resp = acl_test_2.get_bucket_acl(bkt_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Bucket ACL was verified")
        LOGGER.info(
            "ENDED:acc1 -put bucket, acc2- give read-acp permissions,acc1- get-bucket-acl")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-8712", "bucket_acl")
    @CTFailOn(error_handler)
    def test_full_control_acl_6423(self):
        """Test full-control on bucket to cross account and test delete bucket from owner account"""
        LOGGER.info(
            "STARTED: Test full-control on bucket to cross account and test delete")
        test_cfg = BKT_ACL_CONFIG["test_6423"]
        bkt_name = "{0}{1}".format(
            BKT_ACL_CONFIG["bucket_acl"]["bkt_name_prefix"],
            test_cfg["bucket_name"].format(self.random_id))
        create_acc = IAM_OBJ.create_s3iamcli_acc(
            self.account_name, self.email_id)
        assert create_acc[0], create_acc[1]
        cannonical_id = create_acc[1][0]
        LOGGER.info("Step 1: Creating bucket with name %s", bkt_name)
        resp = S3_OBJ.create_bucket(bkt_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Created a bucket with name %s", bkt_name)
        LOGGER.info("Step 2: Verifying that bucket is created")
        resp = S3_OBJ.bucket_list()
        assert resp[0], resp[1]
        assert bkt_name in resp[1]
        LOGGER.info("Step 2: Verified that bucket is created")
        LOGGER.info(
            "Step 3:Performing put bucket acl for bucket %s for full control",
            bkt_name)
        resp = ACL_OBJ.put_bucket_acl(
            bkt_name, grant_full_control=test_cfg["id_str"].format(cannonical_id))
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3:Performed put bucket, bucket %s for account 2",
            bkt_name)
        LOGGER.info("Step 4: Retrieving acl of a bucket %s", bkt_name)
        resp = ACL_OBJ.get_bucket_acl(bkt_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Retrieved acl of a bucket %s", bkt_name)
        LOGGER.info("Step 5: Deleting a bucket %s", bkt_name)
        resp = S3_OBJ.delete_bucket(bkt_name)
        assert resp[0], resp[1]
        LOGGER.info("Step 5: Deleted a bucket %s", bkt_name)
        LOGGER.info("Step 6: Verifying that bucket is deleted")
        resp = S3_OBJ.bucket_list()
        assert resp[0], resp[1]
        assert bkt_name not in resp[1], resp[1]
        LOGGER.info("Step 6: Verified that bucket is deleted")
        LOGGER.info(
            "ENDED: Test full-control on bucket to cross account and test delete")
