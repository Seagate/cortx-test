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

"""UnitTest for S3 core, test library which contains S3 operations."""

import os
import shutil
import logging
import pytest

from commons import errorconstants as errconst
from commons.exceptions import CTException
from commons.utils.system_utils import create_file
from commons.utils.system_utils import remove_file
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD
from libs.s3 import iam_test_lib, s3_test_lib

IAM_OBJ = iam_test_lib.IamTestLib()
S3_TEST_OBJ = s3_test_lib.S3TestLib()


class TestS3TestLib:
    """S3 test lib unittest suite."""

    @classmethod
    def setup_class(cls):
        """test setup class."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup class operations.")
        cls.bkt_name_prefix = "ut-bkt"
        cls.acc_name_prefix = "ut-accnt"
        cls.obj_prefix = "ut-obj"
        cls.dummy_bucket = "dummybucket"
        cls.file_size = 5
        cls.obj_name = "ut_obj"
        cls.test_folder_path = os.path.join(os.getcwd(), "test_folder")
        cls.test_file_path = os.path.join(cls.test_folder_path, "hello.txt")
        cls.test_down_path = os.path.join(cls.test_folder_path, "test_outfile.txt")
        cls.obj_size = 1
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
    def test_01_create_bucket(self):
        """Test create bucket."""
        resp = S3_TEST_OBJ.create_bucket("ut-bkt-01")
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_02_bucket_list(self):
        """Test bucket list."""
        S3_TEST_OBJ.create_bucket("ut-bkt-02")
        resp = S3_TEST_OBJ.bucket_list()
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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
            m_key="test_key",
            m_value="test_value")
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_06_head_bucket(self):
        """Test head bucket."""
        S3_TEST_OBJ.create_bucket("ut-bkt-06")
        resp = S3_TEST_OBJ.head_bucket(
            "ut-bkt-06")
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_08_bucket_location(self):
        """Test bucket location."""
        S3_TEST_OBJ.create_bucket("ut-bkt-08")
        resp = S3_TEST_OBJ.bucket_location("ut-bkt-08")
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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
            self.test_down_path)
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_11_delete_bucket(self):
        """Test delete bucket."""
        S3_TEST_OBJ.create_bucket("ut-bkt-11")
        resp = S3_TEST_OBJ.delete_bucket("ut-bkt-11")
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_12_delete_multiple_buckets(self):
        """Test delete multiple buckets."""
        S3_TEST_OBJ.create_bucket("ut-bkt-12")
        S3_TEST_OBJ.create_bucket("ut-bkt-12-1")
        resp = S3_TEST_OBJ.delete_multiple_buckets(
            ["ut-bkt-12", "ut-bkt-12-1"])
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_13_delete_all_buckets(self):
        """Test delete all buckets."""
        S3_TEST_OBJ.create_bucket("ut-bkt-13")
        resp = S3_TEST_OBJ.delete_all_buckets()
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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

    @pytest.mark.s3unittest
    def test_15_bucket_count(self):
        """Test bucket count."""
        resp = S3_TEST_OBJ.create_bucket("ut-bkt-15")
        self.log.info(resp)
        resp = S3_TEST_OBJ.bucket_count()
        self.log.info(resp)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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

    @pytest.mark.s3unittest
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
            assert errconst.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message

    @pytest.mark.s3unittest
    def test_18_get_bucket_size(self):
        """Test get bucket size."""
        S3_TEST_OBJ.create_bucket("ut-bkt-18")
        op_val = S3_TEST_OBJ.get_bucket_size("ut-bkt-18")
        assert op_val[0], op_val[1]
        try:
            S3_TEST_OBJ.get_bucket_size(self.dummy_bucket)
        except CTException as error:
            assert errconst.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message

    @pytest.mark.s3unittest
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
            assert errconst.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message

    @pytest.mark.s3unittest
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
