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

"""UnitTest for s3 tagging test library which contains s3 tagging operations."""

import os
import shutil
import logging
import pytest

from commons import error_messages as errmsg
from commons.exceptions import CTException
from commons.utils.system_utils import create_file, remove_file
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD
from libs.s3 import iam_test_lib, s3_test_lib, s3_tagging_test_lib

IAM_OBJ = iam_test_lib.IamTestLib()
S3_TEST_OBJ = s3_test_lib.S3TestLib()
S3_TAG_OBJ = s3_tagging_test_lib.S3TaggingTestLib()


class TestS3TaggingTestLib:
    """S3 Tagging test lib unittest suite."""

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
    def test_01_set_bucket_tag(self):
        """Test set bucket tag."""
        resp = S3_TEST_OBJ.create_bucket("ut-bkt-01")
        self.log.info(resp)
        assert resp[0], resp[1]
        resp = S3_TAG_OBJ.set_bucket_tag(
            "ut-bkt-01",
            "test_key",
            "test_value",
            10)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_02_get_bucket_tags(self):
        """Test get bucket tag."""
        resp = S3_TEST_OBJ.create_bucket("ut-bkt-02")
        self.log.info(resp)
        assert resp[0], resp[1]
        S3_TAG_OBJ.set_bucket_tag(
            "ut-bkt-02",
            "test_key",
            "test_value",
            10)
        resp = S3_TAG_OBJ.get_bucket_tags(
            "ut-bkt-02")
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_03_delete_bucket_tagging(self):
        """Test delete bucket tagging."""
        resp = S3_TEST_OBJ.create_bucket("ut-bkt-03")
        self.log.info(resp)
        assert resp[0], resp[1]
        S3_TAG_OBJ.set_bucket_tag(
            "ut-bkt-03",
            "test_key",
            "test_value",
            10)
        resp = S3_TAG_OBJ.delete_bucket_tagging(
            "ut-bkt-03")
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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
            tag_count=10)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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
            tag_count=10)
        resp = S3_TAG_OBJ.get_object_tags(
            "ut-bkt-05",
            self.obj_name)
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
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

    @pytest.mark.s3unittest
    def test_07_create_multipart_upload_with_tagging(self):
        """Test create multipart upload with tagging."""
        resp = S3_TEST_OBJ.create_bucket("ut-bkt-07")
        self.log.info(resp)
        assert resp[0], resp[1]
        resp = S3_TAG_OBJ.create_multipart_upload_with_tagging(
            "ut-bkt-07",
            self.obj_name,
            "test_key=test_value")
        assert resp[0], resp[1]

    @pytest.mark.s3unittest
    def test_08_set_bucket_tag_duplicate_keys(self):
        """"Test set bucket tag duplicate keys."""
        resp = S3_TEST_OBJ.create_bucket("ut-bkt-08")
        self.log.info(resp)
        assert resp[0], resp[1]
        try:
            S3_TAG_OBJ.set_bucket_tag_duplicate_keys(
                "ut-bkt-08", "aaa1", "bbb2")
        except CTException as error:
            assert errmsg.MALFORMED_XML_ERR in str(error.message), error.message

    @pytest.mark.s3unittest
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
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message

    @pytest.mark.s3unittest
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
            duplicate_key=False)
        assert op_val[0], op_val[1]
        try:
            S3_TAG_OBJ.set_duplicate_object_tags(
                "ut-bkt-10",
                "ut-obj-10",
                "aaa",
                "bbb")
        except CTException as error:
            assert errmsg.MALFORMED_XML_ERR in str(error.message), error.message

    @pytest.mark.s3unittest
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
            key="aaa",
            value="bbb")
        assert op_val[0], op_val[1]
        try:
            S3_TAG_OBJ.put_object_with_tagging(
                self.dummy_bucket,
                "ut-obj-11",
                self.test_file_path,
                "aaa=bbb",
                key="aaa",
                value="bbb")
        except CTException as error:
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message

    @pytest.mark.s3unittest
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
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message

    @pytest.mark.s3unittest
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
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message
