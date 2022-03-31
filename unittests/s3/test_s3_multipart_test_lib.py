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
#
#!/usr/bin/python
# -*- coding: utf-8 -*-

"""UnitTest for s3 multipart test library which contains multipart operations."""

import os
import shutil
import logging
import pytest

from commons import error_messages as errmsg
from commons.exceptions import CTException
from commons.utils.system_utils import create_file, remove_file
from libs.s3 import iam_test_lib, s3_test_lib, s3_multipart_test_lib
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD

IAM_OBJ = iam_test_lib.IamTestLib()
S3_TEST_OBJ = s3_test_lib.S3TestLib()
S3_MP_OBJ = s3_multipart_test_lib.S3MultipartTestLib()


class TestS3MultipartTestLib:
    """S3 Multipart upload test lib unittest suite."""

    @classmethod
    def setup_class(cls):
        """test setup class."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup class operations.")
        cls.bkt_name_prefix = "ut-bkt"
        cls.acc_name_prefix = "ut-accnt"
        cls.dummy_bucket = "dummybucket"
        cls.obj_name = "ut_obj"
        cls.file_size = 5
        cls.obj_size = 1
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
        self.log.info("Create file: %s", self.test_file_path)
        resp = create_file(self.test_file_path, self.obj_size)
        self.log.info(resp)
        if not os.path.exists(self.test_file_path):
            raise IOError(self.test_file_path)
        # list & delete buckets.
        bucket_list = S3_TEST_OBJ.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                self.bkt_name_prefix)]
        self.log.info("bucket-list: %s", pref_list)
        if pref_list:
            S3_TEST_OBJ.delete_multiple_buckets(pref_list)
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
    def test_01_create_multipart_upload(self):
        """Test create multipart upload."""
        S3_TEST_OBJ.create_bucket("ut-bkt-01")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-01",
            self.obj_name)
        assert resp[0], resp[1]
        S3_TEST_OBJ.create_bucket("ut-bkt-01-1")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-01-1",
            self.obj_name,
            "test_key",
            "test_value")
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_02_upload_parts(self):
        """Test upload parts."""
        S3_TEST_OBJ.create_bucket("ut-bkt-02")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-02",
            self.obj_name)
        mpu_id = resp[1]["UploadId"]
        resp = S3_MP_OBJ.upload_parts(
            mpu_id,
            "ut-bkt-02",
            self.obj_name,
            multipart_obj_size=50,
            total_parts=5,
            multipart_obj_path=self.test_file_path)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_03_list_parts(self):
        """Test list parts."""
        S3_TEST_OBJ.create_bucket("ut-bkt-03")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-03",
            self.obj_name)
        mpu_id = resp[1]["UploadId"]
        S3_MP_OBJ.upload_parts(
            mpu_id,
            "ut-bkt-03",
            self.obj_name,
            50,
            total_parts=5,
            multipart_obj_path=self.test_file_path)
        resp = S3_MP_OBJ.list_parts(
            mpu_id,
            "ut-bkt-03",
            self.obj_name)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_04_complete_multipart_upload(self):
        """Test complete multipart upload."""
        S3_TEST_OBJ.create_bucket("ut-bkt-04")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-04",
            self.obj_name)
        mpu_id = resp[1]["UploadId"]
        resp = S3_MP_OBJ.upload_parts(
            mpu_id,
            "ut-bkt-04",
            self.obj_name,
            50,
            total_parts=5,
            multipart_obj_path=self.test_file_path)
        parts = resp[1]
        resp = S3_MP_OBJ.complete_multipart_upload(
            mpu_id,
            parts,
            "ut-bkt-04",
            self.obj_name)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_05_abort_multipart_all(self):
        """Test abort multipart all."""
        S3_TEST_OBJ.create_bucket("ut-bkt-05")
        resp = S3_MP_OBJ.create_multipart_upload(
            "ut-bkt-05",
            self.obj_name)
        mpu_id = resp[1]["UploadId"]
        S3_MP_OBJ.upload_parts(
            mpu_id,
            "ut-bkt-05",
            self.obj_name,
            50,
            total_parts=5,
            multipart_obj_path=self.test_file_path)
        resp = S3_MP_OBJ.abort_multipart_all(
            "ut-bkt-05",
            self.obj_name)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_06_list_multipart_uploads(self):
        """Test list multipart uploads."""
        bkt_name = "ut-bkt-06"
        obj_name = "ut-obj-06"
        S3_TEST_OBJ.create_bucket(bkt_name)
        op_val = S3_MP_OBJ.create_multipart_upload(bkt_name, obj_name)
        mpid = op_val[1]["UploadId"]
        op_val = S3_MP_OBJ.upload_parts(
            mpid, bkt_name, obj_name, 50,
            total_parts=5, multipart_obj_path=self.test_file_path)
        parts = op_val[1]
        S3_MP_OBJ.complete_multipart_upload(mpid, parts, bkt_name, obj_name)
        op_val_ls = S3_MP_OBJ.list_multipart_uploads(bkt_name)
        assert op_val_ls[0], op_val[1]
        try:
            S3_MP_OBJ.list_multipart_uploads(self.dummy_bucket)
        except CTException as error:
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message

    @pytest.mark.s3unittest
    def test_07_get_byte_range_of_object(self):
        """Test get byte range of object."""
        S3_TEST_OBJ.create_bucket("ut-bkt-07")
        op_val = S3_TEST_OBJ.put_object(
            "ut-bkt-07",
            "ut-obj-07",
            self.test_file_path)
        assert op_val[0], op_val[1]
        op_val = S3_MP_OBJ.get_byte_range_of_object(
            "ut-bkt-07", "ut-obj-07",
            0, 5)
        assert op_val[0], op_val[1]
        try:
            S3_MP_OBJ.get_byte_range_of_object(
                self.dummy_bucket, "ut-obj-07",
                0, 5)
        except CTException as error:
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message
