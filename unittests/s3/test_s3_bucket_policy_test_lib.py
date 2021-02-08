#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest for s3 bucket policy test helper library which contains bucket policy operations."""

import os
import json
import shutil
import logging
import pytest

from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import create_file, remove_file
from libs.s3 import iam_test_lib, s3_test_lib, s3_bucket_policy_test_lib

IAM_TEST_OBJ = iam_test_lib.IamTestLib()
S3_TEST_OBJ = s3_test_lib.S3TestLib()
S3_BKT_POLICY_OBJ = s3_bucket_policy_test_lib.S3BucketPolicyTestLib()

CMN_CFG = read_yaml("config/common_config.yaml")[1]


class TestS3ACLTestLib:
    """S3 ACL test lib unittest suite."""

    @classmethod
    def setup_class(cls):
        """test setup class."""
        logging.basicConfig(
            filename="unittest.log",
            filemode="w",
            level=logging.DEBUG)
        cls.log = logging.getLogger(__name__)
        cls.bkt_name_prefix = "ut-bkt"
        cls.acc_name_prefix = "ut-accnt"
        cls.dummy_bucket = "dummybucket"
        cls.test_file_path = "/root/test_folder/hello.txt"
        cls.test_folder_path = "/root/test_folder"
        cls.ldap_user = CMN_CFG["ldap_username"]
        cls.ldap_pwd = CMN_CFG["ldap_passwd"]

    @classmethod
    def teardown_class(cls):
        """Test teardown class."""
        cls.log.info("Test teardown completed.")

    def setup_method(self):
        """
        Function will be invoked before test suit execution.

        It will perform prerequisite test steps if any
        Defined var for log, onfig, creating common dir
        """
        self.log.info("STARTED: Setup operations")
        if not os.path.exists(self.test_folder_path):
            os.mkdir(self.test_folder_path)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after test suit.

        It will clean up resources which are getting created during test case execution.
        This function will reset accounts, delete buckets, accounts and files.
        """
        self.log.info("STARTED: Teardown operations")
        bucket_list = S3_TEST_OBJ.bucket_list()[1]
        account_name = self.acc_name_prefix
        acc_list = IAM_TEST_OBJ.list_accounts_s3iamcli(
            self.ldap_user,
            self.ldap_pwd)[1]
        self.log.debug("Listing account %s", acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if account_name in acc["AccountName"]]
        if all_acc:
            for acc in all_acc:
                resp = IAM_TEST_OBJ.reset_account_access_key_s3iamcli(
                    acc, self.ldap_user, self.ldap_pwd)
                access_key = resp[1]["AccessKeyId"]
                secret_key = resp[1]["SecretKey"]
                s3_temp_obj = s3_test_lib.S3TestLib(
                    access_key=access_key, secret_key=secret_key)
                test_buckets = s3_temp_obj.bucket_list()[1]
                if test_buckets:
                    self.log.info("Deleting all buckets...")
                    bkt_list = s3_temp_obj.bucket_list()[1]
                    bk_list = [
                        each_bkt for each_bkt in bkt_list if each_bkt.startswith(
                            self.bkt_name_prefix)]
                    self.log.info("bucket-list: %s", bk_list)
                    resp = s3_temp_obj.delete_multiple_buckets(bk_list)
                    assert resp[0], resp[1]
                    self.log.info("Deleted all buckets")
                self.log.info("Deleting IAM accounts...")
                resp = IAM_TEST_OBJ.reset_access_key_and_delete_account_s3iamcli(
                    acc)
                assert resp[0], resp[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                self.bkt_name_prefix)]
        self.log.info("bucket-list: %s", pref_list)
        S3_TEST_OBJ.delete_multiple_buckets(pref_list)
        self.log.info("Deleting Common dir and files...")
        if os.path.exists(self.test_folder_path):
            shutil.rmtree(self.test_folder_path)
        if os.path.exists(self.test_file_path):
            remove_file(self.test_file_path)
        self.log.info("ENDED: Teardown operations")

    def test_01_get_bucket_policy(self):
        """Test get bucket policy."""
        bkt_name = "ut-bkt-01"
        op_val = S3_TEST_OBJ.create_bucket(bkt_name)
        assert op_val[0], op_val[1]
        try:
            S3_BKT_POLICY_OBJ.get_bucket_policy(bkt_name)
        except CTException as error:
            assert "NoSuchBucketPolicy" not in str(
                error.message), error.message
        bucket_policy = {
            'Version': '2019-12-04',
            'Statement': [{
                'Sid': 'AddPerm',
                'Effect': 'Allow',
                'Principal': '*',
                'Action': ['s3:GetObject'],
                'Resource': "arn:aws:s3:::%s/*" % bkt_name
            }]
        }
        bkt_policy = json.dumps(bucket_policy)
        op_val = S3_BKT_POLICY_OBJ.put_bucket_policy(bkt_name, bkt_policy)
        assert op_val[0], op_val[1]
        op_val = S3_BKT_POLICY_OBJ.get_bucket_policy(bkt_name)
        assert op_val[0], op_val[1]

    def test_01_put_bucket_policy(self):
        """Test bucket policy."""
        bkt_name = "ut-bkt-01"
        op_val = S3_TEST_OBJ.create_bucket(bkt_name)
        assert op_val[0], op_val[1]
        bucket_policy = {
            'Version': '2019-12-03',
            'Statement': [{
                'Sid': 'AddPerm',
                'Effect': 'Allow',
                'Principal': '*',
                'Action': ['s3:GetObject'],
                'Resource': "arn:aws:s3:::%s/*" % bkt_name
            }]
        }
        bkt_policy = json.dumps(bucket_policy)
        op_val = S3_BKT_POLICY_OBJ.put_bucket_policy(bkt_name, bkt_policy)
        assert op_val[0], op_val[1]
        try:
            S3_BKT_POLICY_OBJ.put_bucket_policy(
                self.dummy_bucket, bkt_policy)
        except CTException as error:
            assert "NoSuchBucket" not in str(error.message), error.message

    def test_02_delete_bucket_policy(self):
        """Test delete bucket policy."""
        create_resp = S3_TEST_OBJ.create_bucket("ut-bkt-02")
        assert create_resp[0], create_resp[1]
        resp = S3_BKT_POLICY_OBJ.put_bucket_policy(
            "ut-bkt-74", json.dumps({
                'Statement': [{
                    'Effect': 'Allow',
                    'Principal': '*',
                    'Action': 's3:GetObject',
                    'Resource': 'arn:aws:s3:::ut-bkt-02/*'
                },
                    {'Effect': 'Deny',
                     'Principal': '*',
                     'Action': 's3:DeleteObject',
                     'Resource': 'arn:aws:s3:::ut-bkt-02/*'
                     }]})
        )
        assert resp[0], resp[1]
        resp = S3_BKT_POLICY_OBJ.delete_bucket_policy("ut-bkt-02")
        assert resp[0], resp[1]
        try:
            S3_BKT_POLICY_OBJ.delete_bucket_policy("ut-bkt-02")
        except CTException as error:
            assert "NoSuchBucketPolicy" not in error.message, error.message
        S3_TEST_OBJ.delete_bucket("ut-bkt-02", force=True)
