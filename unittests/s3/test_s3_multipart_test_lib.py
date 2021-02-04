#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest for s3 multipart test helper library which contains multipart operations."""

import os
import shutil
import logging
import pytest

from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import create_file, remove_file
from libs.s3 import iam_test_lib, s3_test_lib, s3_multipart_test_lib

IAM_TEST_OBJ = iam_test_lib.IamTestLib()
S3_TEST_OBJ = s3_test_lib.S3TestLib()
S3_MP_OBJ = s3_multipart_test_lib.S3MultipartTestLib()

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
        cls.obj_name = "ut_obj"
        cls.file_size = 5
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

    def test_15_create_multipart_upload(self):
        """Test create multipart upload."""
        S3_TEST_OBJ.create_bucket("ut-bkt-15")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-15",
            self.obj_name)
        assert resp[0], resp[1]
        S3_TEST_OBJ.create_bucket("ut-bkt-15")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-15",
            self.obj_name,
            "test_key",
            "test_value")
        assert resp[0], resp[1]

    def test_16_upload_parts(self):
        """Test upload parts."""
        S3_TEST_OBJ.create_bucket("ut-bkt-16")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-16",
            self.obj_name)
        mpu_id = resp[1]["UploadId"]
        resp = S3_MP_OBJ.upload_parts(
            mpu_id,
            "ut-bkt-16",
            self.obj_name,
            50,
            5,
            self.test_file_path)
        assert resp[0], resp[1]

    def test_17_list_parts(self):
        """Test list parts."""
        S3_TEST_OBJ.create_bucket("ut-bkt-17")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-17",
            self.obj_name)
        mpu_id = resp[1]["UploadId"]
        S3_MP_OBJ.upload_parts(
            mpu_id,
            "ut-bkt-17",
            self.obj_name,
            50,
            5,
            self.test_file_path)
        resp = S3_MP_OBJ.list_parts(
            mpu_id,
            "ut-bkt-17",
            self.obj_name)
        assert resp[0], resp[1]

    def test_18_complete_multipart_upload(self):
        """Test complete multipart upload."""
        S3_TEST_OBJ.create_bucket("ut-bkt-18")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-18",
            self.obj_name)
        mpu_id = resp[1]["UploadId"]
        resp = S3_MP_OBJ.upload_parts(
            mpu_id,
            "ut-bkt-18",
            self.obj_name,
            50,
            5,
            self.test_file_path)
        parts = resp[1]
        resp = S3_MP_OBJ.complete_multipart_upload(
            mpu_id,
            parts,
            "ut-bkt-18",
            self.obj_name)
        assert resp[0], resp[1]

    def test_19_abort_multipart_all(self):
        """Test abort multipart all."""
        S3_TEST_OBJ.create_bucket("ut-bkt-19")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-19",
            self.obj_name)
        mpu_id = resp[1]["UploadId"]
        S3_MP_OBJ.upload_parts(
            mpu_id,
            "ut-bkt-19",
            self.obj_name,
            50,
            5,
            self.test_file_path)
        resp = S3_MP_OBJ.abort_multipart_all(
            "ut-bkt-19",
            self.obj_name)
        assert resp[0], resp[1]

    def test_55_list_multipart_uploads(self):
        """Test list multipart uploads."""
        bkt_name = "ut-bkt-55"
        obj_name = "ut-obj-55"
        S3_TEST_OBJ.create_bucket(bkt_name)
        op_val = S3_MP_OBJ.create_multipart_upload(bkt_name, obj_name)
        global MPID
        MPID = op_val[1]["UploadId"]
        op_val = S3_MP_OBJ.upload_parts(
            MPID, bkt_name, obj_name, 50,
            5, self.test_file_path)
        global parts
        parts = op_val[1]
        S3_MP_OBJ.complete_multipart_upload(MPID, parts, bkt_name, obj_name)
        op_val_ls = S3_MP_OBJ.list_multipart_uploads(bkt_name)
        assert op_val_ls[0], op_val[1]
        try:
            S3_MP_OBJ.list_multipart_uploads(self.dummy_bucket)
        except CTException as error:
            assert "NoSuchBucket" not in str(error.message), error.message

    def test_58_get_byte_range_of_object(self):
        """Test get byte range of object."""
        create_file(
            self.test_file_path,
            self.obj_size)
        S3_TEST_OBJ.create_bucket("ut-bkt-58")
        op_val = S3_TEST_OBJ.put_object(
            "ut-bkt-58",
            "ut-obj-58",
            self.test_file_path)
        assert op_val[0], op_val[1]
        op_val = S3_MP_OBJ.get_byte_range_of_object(
            "ut-bkt-58", "ut-obj-58",
            0, 5)
        assert op_val[0], op_val[1]
        try:
            S3_MP_OBJ.get_byte_range_of_object(
                self.dummy_bucket, "ut-obj-58",
                0, 5)
        except CTException as error:
            assert "NoSuchBucket" not in str(error.message), error.message
