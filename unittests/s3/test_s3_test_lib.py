#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest for IAM test helper library which contains admin_path operations."""

import os
import shutil
import logging
import pytest

from commons.exceptions import CTException
from commons.utils.system_utils import create_file, remove_file
from commons.utils.config_utils import read_yaml
from libs.s3 import iam_test_lib, s3_test_lib

IAM_TEST_OBJ = iam_test_lib.IamTestLib()
S3_TEST_OBJ = s3_test_lib.S3TestLib()

CMN_CFG = read_yaml("config/common_config.yaml")[1]


class TestS3TestLib:
    """S3 test lib unittest suite."""

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
        cls.obj_prefix = "ut-obj"
        cls.dummy_bucket = "dummybucket"
        cls.file_size = 5
        cls.obj_name = "ut_obj"
        cls.test_file_path = "/root/test_folder/hello.txt"
        cls.obj_size = 1
        cls.test_folder_path = "/root/test_folder"
        cls.ldap_user = CMN_CFG["ldap_username"]
        cls.ldap_pwd = CMN_CFG["ldap_passwd"]

    @classmethod
    def teardown_class(cls):
        """Test teardown class."""
        cls.log.info("Test teardown completed.")

    def setup_method(self):
        """
        This function will be invoked before test suit execution
        It will perform prerequisite test steps if any
        Defined var for log, onfig, creating common dir
        """
        self.log.info("STARTED: Setup operations")
        if not os.path.exists(self.test_folder_path):
            os.mkdir(self.test_folder_path)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        This function will be invoked after test suit.
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

    def test_01_create_bucket(self):
        """Test create bucket."""
        resp = S3_TEST_OBJ.create_bucket("ut-bkt-01")
        assert resp[0], resp[1]

    def test_02_bucket_list(self):
        """Test bucket list."""
        S3_TEST_OBJ.create_bucket("ut-bkt-02")
        resp = S3_TEST_OBJ.bucket_list()
        assert resp[0], resp[1]

    def test_03_put_object(self):
        """Test put object."""
        S3_TEST_OBJ.create_bucket("ut-bkt-03")
        create_file(
            self.test_file_path,
            self.file_size)
        resp = S3_TEST_OBJ.put_object(
            "ut-bkt-03",
            self.obj_name,
            self.test_file_path)
        assert resp[0], resp[1]
        resp = S3_TEST_OBJ.put_object(
            "ut-bkt-03",
            self.obj_name,
            self.test_file_path,
            "test_key",
            "test_value")
        assert resp[0], resp[1]

    def test_04_object_upload(self):
        """Test object upload."""
        S3_TEST_OBJ.create_bucket("ut-bkt-04")
        create_file(
            self.test_file_path,
            self.file_size)
        resp = S3_TEST_OBJ.object_upload(
            "ut-bkt-04",
            self.obj_name,
            self.test_file_path)
        assert resp[0], resp[1]

    def test_05_object_list(self):
        """Test object list."""
        S3_TEST_OBJ.create_bucket("ut-bkt-05")
        create_file(
            self.test_file_path,
            self.file_size)
        S3_TEST_OBJ.put_object(
            "ut-bkt-05",
            self.obj_name,
            self.test_file_path)
        resp = S3_TEST_OBJ.object_list(
            "ut-bkt-05")
        assert resp[0], resp[1]

    def test_06_head_bucket(self):
        """Test head bucket."""
        S3_TEST_OBJ.create_bucket("ut-bkt-06")
        resp = S3_TEST_OBJ.head_bucket(
            "ut-bkt-06")
        assert resp[0], resp[1]

    def test_07_delete_object(self):
        """Test delete object."""
        S3_TEST_OBJ.create_bucket("ut-bkt-07")
        create_file(
            self.test_file_path,
            self.file_size)
        S3_TEST_OBJ.put_object(
            "ut-bkt-07",
            self.obj_name,
            self.test_file_path)
        resp = S3_TEST_OBJ.delete_object(
            "ut-bkt-07",
            self.obj_name)
        assert resp[0], resp[1]

    def test_08_bucket_location(self):
        """Test bucket location."""
        S3_TEST_OBJ.create_bucket("ut-bkt-08")
        resp = S3_TEST_OBJ.bucket_location("ut-bkt-08")
        assert resp[0], resp[1]

    def test_09_object_info(self):
        """Test object info."""
        S3_TEST_OBJ.create_bucket("ut-bkt-09")
        create_file(
            self.test_file_path,
            self.file_size)
        S3_TEST_OBJ.put_object(
            "ut-bkt-09",
            self.obj_name,
            self.test_file_path)
        resp = S3_TEST_OBJ.object_info(
            "ut-bkt-09",
            self.obj_name)
        assert resp[0], resp[1]

    def test_10_object_download(self):
        """Test object download."""
        S3_TEST_OBJ.create_bucket("ut-bkt-10")
        create_file(
            self.test_file_path,
            self.file_size)
        S3_TEST_OBJ.put_object(
            "ut-bkt-10",
            self.obj_name,
            self.test_file_path)
        resp = S3_TEST_OBJ.object_download(
            "ut-bkt-10",
            self.obj_name,
            "/root/test_folder/test_outfile.txt")
        assert resp[0], resp[1]

    def test_11_delete_bucket(self):
        """Test delete bucket."""
        S3_TEST_OBJ.create_bucket("ut-bkt-11")
        resp = S3_TEST_OBJ.delete_bucket("ut-bkt-11")
        assert resp[0], resp[1]

    def test_14_delete_multiple_objects(self):
        """Test delete multiple objects."""
        S3_TEST_OBJ.create_bucket("ut-bkt-11")
        create_file(
            self.test_file_path,
            self.file_size)
        S3_TEST_OBJ.put_object(
            "ut-bkt-11",
            self.obj_name,
            self.test_file_path)
        S3_TEST_OBJ.put_object(
            "ut-bkt-11",
            "ut_obj_1",
            self.test_file_path)
        resp = S3_TEST_OBJ.delete_multiple_objects(
            "ut-bkt-11", [
                self.obj_name, "ut_obj_1"])
        assert resp[0], resp[1]

    def test_12_delete_multiple_buckets(self):
        """Test delete multiple buckets."""
        S3_TEST_OBJ.create_bucket("ut-bkt-12")
        S3_TEST_OBJ.create_bucket("ut-bkt-12-1")
        resp = S3_TEST_OBJ.delete_multiple_buckets(
            ["ut-bkt-12", "ut-bkt-12-1"])
        assert resp[0], resp[1]

    def test_13_delete_all_buckets(self):
        """Test delete all buckets."""
        S3_TEST_OBJ.create_bucket("ut-bkt-13")
        resp = S3_TEST_OBJ.delete_all_buckets()
        assert resp[0], resp[1]

    def test_14_create_multiple_buckets_with_objects(self):
        """"Test create multiple buckets with objects."""
        create_file(
            self.test_file_path,
            self.file_size)
        resp = S3_TEST_OBJ.create_multiple_buckets_with_objects(
            2,
            self.test_file_path,
            4)
        assert resp[0], resp[1]

    def test_15_bucket_count(self):
        """Test bucket count."""
        S3_TEST_OBJ.create_bucket("ut-bkt-15")
        resp = S3_TEST_OBJ.bucket_count()
        assert resp[0], resp[1]

    def test_16_get_bucket_size(self):
        """Test get bucket size."""
        S3_TEST_OBJ.create_bucket("ut-bkt-16")
        create_file(
            self.test_file_path,
            self.file_size)
        S3_TEST_OBJ.object_upload(
            "ut-bkt-16",
            self.obj_name,
            self.test_file_path)
        resp = S3_TEST_OBJ.get_bucket_size(
            "ut-bkt-16")
        assert resp[0], resp[1]

    def test_17_put_object(self):
        """Test put object."""
        create_file(
            self.test_file_path,
            self.obj_size)
        S3_TEST_OBJ.create_bucket("ut-bkt-17")
        op_val = S3_TEST_OBJ.put_object(
            "ut-bkt-17",
            "ut-obj-17",
            self.test_file_path)
        assert op_val[0], op_val[1]
        try:
            S3_TEST_OBJ.put_object(
                self.dummy_bucket,
                "ut-obj-17",
                self.test_file_path)
        except CTException as error:
            assert "NoSuchBucket" not in str(error.message), error.message

    def test_18_get_bucket_size(self):
        """Test get bucket size."""
        S3_TEST_OBJ.create_bucket("ut-bkt-18")
        op_val = S3_TEST_OBJ.get_bucket_size("ut-bkt-18")
        assert op_val[0], op_val[1]
        try:
            S3_TEST_OBJ.get_bucket_size(self.dummy_bucket)
        except CTException as error:
            assert "NoSuchBucket" not in str(error.message), error.message

    def test_19_list_objects_params(self):
        """Test list objects params."""
        create_file(self.test_file_path, 10)
        create_resp = S3_TEST_OBJ.create_bucket("ut-bkt-19")
        assert create_resp[0], create_resp[1]
        put_obj_resp = S3_TEST_OBJ.put_object(
            "ut-bkt-19",
            "ut-obj-19",
            self.test_file_path)
        assert put_obj_resp[0], put_obj_resp[1]
        # Listing objects with Valid prefix
        op_val = S3_TEST_OBJ.list_objects_with_prefix(
            "ut-bkt-19", self.obj_prefix)
        assert op_val[0], op_val[1]
        try:
            S3_TEST_OBJ.list_objects_with_prefix(
                self.dummy_bucket, self.obj_prefix)
        except CTException as error:
            assert "NoSuchBucket" not in str(error.message), error.message

    def test_20_put_object_with_storage_class(self):
        """Test put object with storage class."""
        create_resp = S3_TEST_OBJ.create_bucket("ut-bkt-20")
        assert create_resp[0], create_resp[1]
        create_file(
            self.test_file_path,
            self.file_size)
        resp = S3_TEST_OBJ.put_object_with_storage_class(
            "ut-bkt-20",
            self.obj_name,
            self.test_file_path,
            "STANDARD")
        assert resp[0], resp[1]
