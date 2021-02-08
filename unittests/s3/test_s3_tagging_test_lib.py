#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest for s3 tagging test helper library which contains s3 tagging operations."""

import os
import shutil
import logging
import pytest

from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import create_file, remove_file
from libs.s3 import iam_test_lib, s3_test_lib, s3_tagging_test_lib

IAM_TEST_OBJ = iam_test_lib.IamTestLib()
S3_TEST_OBJ = s3_test_lib.S3TestLib()
S3_TAG_OBJ = s3_tagging_test_lib.S3TaggingTestLib()

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
        cls.file_size = 5
        cls.obj_name = "ut_obj"
        cls.obj_size = 1
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

    def test_01_set_bucket_tag(self):
        """Test set bucket tag."""
        S3_TEST_OBJ.create_bucket("ut-bkt-01")
        resp = S3_TAG_OBJ.set_bucket_tag(
            "ut-bkt-01",
            "test_key",
            "test_value",
            10)
        assert resp[0], resp[1]

    def test_02_get_bucket_tags(self):
        """Test get bucket tag."""
        S3_TEST_OBJ.create_bucket("ut-bkt-02")
        S3_TAG_OBJ.set_bucket_tag(
            "ut-bkt-02",
            "test_key",
            "test_value",
            10)
        resp = S3_TAG_OBJ.get_bucket_tags(
            "ut-bkt-02")
        assert resp[0], resp[1]

    def test_03_delete_bucket_tagging(self):
        """Test delete bucket tagging."""
        S3_TEST_OBJ.create_bucket("ut-bkt-03")
        S3_TAG_OBJ.set_bucket_tag(
            "ut-bkt-03",
            "test_key",
            "test_value",
            10)
        resp = S3_TAG_OBJ.delete_bucket_tagging(
            "ut-bkt-03")
        assert resp[0], resp[1]

    def test_04_set_object_tag(self):
        """Test set object tag."""
        S3_TEST_OBJ.create_bucket("ut-bkt-04")
        create_file(
            self.test_file_path,
            self.file_size)
        S3_TEST_OBJ.put_object(
            "ut-bkt-04",
            self.obj_name,
            self.test_file_path)
        resp = S3_TAG_OBJ.set_object_tag(
            "ut-bkt-04",
            self.obj_name,
            "test_key",
            "test_value",
            10)
        assert resp[0], resp[1]

    def test_05_get_object_tags(self):
        """Test get object tags."""
        S3_TEST_OBJ.create_bucket("ut-bkt-05")
        create_file(
            self.test_file_path,
            self.file_size)
        S3_TEST_OBJ.put_object(
            "ut-bkt-05",
            self.obj_name,
            self.test_file_path)
        S3_TAG_OBJ.set_object_tag(
            "ut-bkt-05",
            self.obj_name,
            "test_key",
            "test_value",
            10)
        resp = S3_TAG_OBJ.get_object_tags(
            "ut-bkt-05",
            self.obj_name)
        assert resp[0], resp[1]

    def test_06_delete_object_tagging(self):
        """Test delete object tagging."""
        S3_TEST_OBJ.create_bucket("ut-bkt-06")
        create_file(
            self.test_file_path,
            self.file_size)
        S3_TEST_OBJ.put_object(
            "ut-bkt-06",
            self.obj_name,
            self.test_file_path)
        S3_TAG_OBJ.set_object_tag(
            "ut-bkt-06",
            self.obj_name,
            "test_key",
            "test_value")
        resp = S3_TAG_OBJ.delete_object_tagging(
            "ut-bkt-06",
            self.obj_name)
        assert resp[0], resp[1]

    def test_07_create_multipart_upload_with_tagging(self):
        """Test create multipart upload with tagging."""
        S3_TEST_OBJ.create_bucket("ut-bkt-07")
        resp = S3_TAG_OBJ.create_multipart_upload_with_tagging(
            "ut-bkt-07",
            self.obj_name,
            "test_key=test_value")
        assert resp[0], resp[1]

    def test_08_set_bucket_tag_duplicate_keys(self):
        """"Test set bucket tag duplicate keys."""
        S3_TEST_OBJ.create_bucket("ut-bkt-08")
        try:
            S3_TAG_OBJ.set_bucket_tag_duplicate_keys(
                "ut-bkt-08", "aaa1", "bbb2")
        except CTException as error:
            assert "MalformedXML" not in str(error.message), error.message

    def test_09_set_bucket_tag_base64_encode(self):
        """Test set bucket tag base64 encode."""
        S3_TEST_OBJ.create_bucket("ut-bkt-09")
        op_val = S3_TAG_OBJ.set_bucket_tag_invalid_char(
            "ut-bkt-09", "aaa", "aaa")
        assert op_val[0], op_val[1]
        try:
            S3_TAG_OBJ.set_bucket_tag_invalid_char(
                self.dummy_bucket, "aaa", "aaa")
        except CTException as error:
            assert "NoSuchBucket" not in str(error.message), error.message

    def test_10_set_duplicate_object_tag_key(self):
        """Test set duplicate object tag key."""
        create_file(
            self.test_file_path,
            self.obj_size)
        S3_TEST_OBJ.create_bucket("ut-bkt-10")
        S3_TEST_OBJ.put_object(
            "ut-bkt-10",
            "ut-obj-10",
            file_path=self.test_file_path)
        op_val = S3_TAG_OBJ.set_duplicate_object_tags(
            "ut-bkt-10",
            "ut-obj-10",
            "aaa",
            "bbb",
            False)
        assert op_val[0], op_val[1]
        try:
            S3_TAG_OBJ.set_duplicate_object_tags(
                "ut-bkt-10",
                "ut-obj-10",
                "aaa",
                "bbb")
        except CTException as error:
            assert "MalformedXML" not in str(error.message), error.message

    def test_11_put_object_tag_with_tagging(self):
        """Test put object tag with tagging."""
        create_file(
            self.test_file_path,
            self.obj_size)
        S3_TEST_OBJ.create_bucket("ut-bkt-11")
        op_val = S3_TAG_OBJ.put_object_with_tagging(
            "ut-bkt-11",
            "ut-obj-11",
            self.test_file_path,
            "aaa=bbb")
        assert op_val[0], op_val[1]
        op_val = S3_TAG_OBJ.put_object_with_tagging(
            "ut-bkt-11",
            "ut-obj-11",
            self.test_file_path,
            "aaa=bbb",
            "aaa",
            "bbb")
        assert op_val[0], op_val[1]
        try:
            S3_TAG_OBJ.put_object_with_tagging(
                self.dummy_bucket,
                "ut-obj-11",
                self.test_file_path,
                "aaa=bbb",
                "aaa",
                "bbb")
        except CTException as error:
            assert "NoSuchBucket" not in str(error.message), error.message

    def test_12_put_object_tag_base64_encode(self):
        """Test put object tag base64 encode."""
        create_file(
            self.test_file_path,
            self.obj_size)
        S3_TEST_OBJ.create_bucket("ut-bkt-12")
        S3_TEST_OBJ.put_object(
            "ut-bkt-12",
            "ut-obj-12",
            self.test_file_path)
        op_val = S3_TAG_OBJ.set_object_tag_invalid_char(
            "ut-bkt-12", "ut-obj-12",
            "aaa", "bbb")
        assert op_val[0], op_val[1]
        try:
            S3_TAG_OBJ.set_object_tag_invalid_char(
                self.dummy_bucket, "ut-obj-12",
                "aaa", "bbb")
        except CTException as error:
            assert "NoSuchBucket" not in str(error.message), error.message

    def test_13_get_object_tagging(self):
        """Test get object tagging."""
        create_file(
            self.test_file_path,
            self.obj_size)
        S3_TEST_OBJ.create_bucket("ut-bkt-13")
        S3_TAG_OBJ.put_object_with_tagging(
            "ut-bkt-13",
            "ut-obj-13",
            self.test_file_path,
            "aaa=bbb")
        op_val = S3_TAG_OBJ.get_object_with_tagging(
            "ut-bkt-13", "ut-obj-13")
        assert op_val[0], op_val[1]
        try:
            S3_TAG_OBJ.get_object_with_tagging(
                self.dummy_bucket, "ut-obj-13")
        except CTException as error:
            assert "NoSuchBucket" not in str(error.message), error.message
