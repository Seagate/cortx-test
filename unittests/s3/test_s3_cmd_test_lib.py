#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest for s3 cmd test library which contains aws s3 cli operations."""

import os
import shutil
import logging
import pytest

from commons.utils.system_utils import create_file, remove_file, create_multiple_size_files
from libs.s3 import iam_test_lib, s3_test_lib, s3_cmd_test_lib
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD

IAM_OBJ = iam_test_lib.IamTestLib()
S3_TEST_OBJ = s3_test_lib.S3TestLib()
S3_CMD_OBJ = s3_cmd_test_lib.S3CmdTestLib()


class TestS3CMDTestLib:
    """S3 CMD test lib unittest suite."""

    @classmethod
    def setup_class(cls):
        """test setup class."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup class operations.")
        cls.bkt_name_prefix = "ut-bkt"
        cls.acc_name_prefix = "ut-accnt"
        cls.dummy_bucket = "dummybucket"
        cls.file_size = 5
        cls.obj_name = "ut_obj"
        cls.test_folder_path = os.path.join(os.getcwd(), "test_folder")
        cls.test_file_path = os.path.join(cls.test_folder_path, "hello.txt")
        cls.ldap_user = LDAP_USERNAME
        cls.ldap_pwd = LDAP_PASSWD
        cls.d_user_name = "dummy_user"
        cls.status = "Inactive"
        cls.d_status = "dummy_Inactive"
        cls.d_nw_user_name = "dummy_user"
        cls.email = "{}@seagate.com"
        cls.log.info("STARTED: setup class operations completed.")

    @classmethod
    def teardown_class(cls):
        """Test teardown class."""
        cls.log.info("STARTED: teardown class operations.")
        cls.log.info("teardown class completed.")
        cls.log.info("STARTED: teardown class operations completed.")

    def setup_method(self):
        """
        Function will be invoked before test execution.

        It will perform prerequisite test steps if any
        Defined var for log, config, creating common dir
        """
        self.log.info("STARTED: Setup operations")
        self.log.info("deleting Common dir and files...")
        if not os.path.exists(self.test_folder_path):
            os.makedirs(self.test_folder_path)
        if os.path.exists(self.test_file_path):
            remove_file(self.test_file_path)
        # Delete account created with prefix.
        self.log.info(
            "Delete created account with prefix: %s",
            self.acc_name_prefix)
        acc_list = IAM_OBJ.list_accounts(
            self.ldap_user,
            self.ldap_pwd)[1]
        self.log.debug("Listing account %s", acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.acc_name_prefix in acc["AccountName"]]
        if all_acc:
            IAM_OBJ.delete_multiple_accounts(all_acc)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after test case.

        It will clean up resources which are getting created during test case execution.
        This function will reset accounts, delete buckets, accounts and files.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info("deleting Common dir and files...")
        if os.path.exists(self.test_folder_path):
            shutil.rmtree(self.test_folder_path)
        if os.path.exists(self.test_file_path):
            remove_file(self.test_file_path)
        # list buckets.
        bucket_list = S3_TEST_OBJ.bucket_list()[1]
        # Delete account created with prefix and all buckets.
        self.log.info(
            "Delete created account with prefix: %s",
            self.acc_name_prefix)
        acc_list = IAM_OBJ.list_accounts(
            self.ldap_user,
            self.ldap_pwd)[1]
        self.log.debug("Listing account %s", acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.acc_name_prefix in acc["AccountName"]]
        if all_acc:
            for acc in all_acc:
                resp = IAM_OBJ.reset_account_access_key(
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
                resp = IAM_OBJ.reset_access_key_and_delete_account(
                    acc)
                assert resp[0], resp[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                self.bkt_name_prefix)]
        self.log.info("bucket-list: %s", pref_list)
        if pref_list:
            S3_TEST_OBJ.delete_multiple_buckets(pref_list)
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.s3unittest
    def test_01_object_upload_cli(self):
        """Test object upload cli."""
        S3_TEST_OBJ.create_bucket("ut-bkt-01")
        create_file(
            self.test_file_path,
            self.file_size)
        resp = S3_CMD_OBJ.object_upload_cli(
            "ut-bkt-01",
            self.obj_name,
            self.test_file_path,
            self.file_size)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_02_upload_folder_cli(self):
        """Test upload folder cli."""
        S3_TEST_OBJ.create_bucket("ut-bkt-02")
        resp = S3_CMD_OBJ.upload_folder_cli(
            "ut-bkt-02",
            self.test_folder_path,
            3)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_03_download_bucket_cli(self):
        """"Test download bucket cli."""
        S3_TEST_OBJ.create_bucket("ut-bkt-03")
        create_multiple_size_files(
            0, 20,
            3, self.test_folder_path, "ut-file-03")
        S3_CMD_OBJ.upload_folder_cli(
            "ut-bkt-03", self.test_folder_path,
            3)
        op_val = S3_CMD_OBJ.download_bucket_cli(
            "ut-bkt-03", self.test_folder_path)
        assert op_val[0], op_val[1]
