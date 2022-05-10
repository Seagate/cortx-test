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

"""UnitTest for S3 ACL test library which contains ACL operations."""

import os
import shutil
import logging
import pytest

from commons import error_messages as errmsg
from commons.exceptions import CTException
from commons.utils.system_utils import create_file, remove_file
from libs.s3 import iam_test_lib, s3_test_lib, s3_acl_test_lib
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD

IAM_TEST_OBJ = iam_test_lib.IamTestLib()
S3_TEST_OBJ = s3_test_lib.S3TestLib()
S3_ACL_OBJ = s3_acl_test_lib.S3AclTestLib()
IAM_OBJ = iam_test_lib.IamTestLib()


class TestS3ACLTestLib:
    """S3 ACL test lib unittest suite."""

    @classmethod
    def setup_class(cls):
        """test setup class."""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup class operations.")
        cls.bkt_name_prefix = "ut-bkt"
        cls.acc_name_prefix = "ut-accnt"
        cls.obj_prefix = "ut-obj"
        cls.dummy_bucket = "dummybucket"
        cls.cid_key = "id={}"
        cls.mail = "{}@seagate.com"
        cls.file_size = 5
        cls.obj_name = "ut_obj"
        cls.test_folder_path = os.path.join(os.getcwd(), "test_folder")
        cls.test_file_path = os.path.join(cls.test_folder_path, "hello.txt")
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
        self.log.info("deleting common dir and files...")
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
                resp = IAM_TEST_OBJ.reset_account_access_key(
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
                resp = IAM_TEST_OBJ.reset_access_key_and_delete_account(
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
    def test_01_get_object_acl(self):
        """Test get object acl."""
        create_file(self.test_file_path, self.obj_size)
        S3_TEST_OBJ.create_bucket("ut-bkt-01")
        op_val = S3_TEST_OBJ.put_object(
            "ut-bkt-01",
            "ut-obj-01",
            self.test_file_path)
        assert op_val[0], op_val[1]
        op_val = S3_ACL_OBJ.get_object_acl(
            "ut-bkt-01", "ut-obj-01")
        assert op_val[0], op_val[1]
        try:
            S3_ACL_OBJ.get_object_acl(
                self.dummy_bucket, "ut-obj-01")
        except CTException as error:
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message

    @pytest.mark.s3unittest
    def test_02_get_bucket_acl(self):
        """Test get bucket acl."""
        S3_TEST_OBJ.create_bucket("ut-bkt-02")
        op_val = S3_ACL_OBJ.get_bucket_acl(
            "ut-bkt-02")
        assert op_val[0], op_val[1]
        try:
            S3_ACL_OBJ.get_bucket_acl(
                self.dummy_bucket)
        except CTException as error:
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message

    @pytest.mark.s3unittest
    def test_03_get_bucket_acl_using_iam_credentials(self):
        """Test get bucket acl using iam credentials."""
        op_val0 = IAM_OBJ.create_account(
            "ut-accnt-03",
            self.mail.format("ut-accnt-03"),
            self.ldap_user,
            self.ldap_pwd)
        assert op_val0[0], op_val0[1]
        temp_s3_obj = s3_test_lib.S3TestLib(
            access_key=op_val0[1]['access_key'],
            secret_key=op_val0[1]['secret_key'])
        temp_s3_obj.create_bucket("ut-bkt-03")
        op_val2 = S3_ACL_OBJ.get_bucket_acl_using_iam_credentials(
            op_val0[1]["access_key"], op_val0[1]["secret_key"], "ut-bkt-03")
        assert op_val2[0], op_val2[1]
        temp_s3_obj.delete_bucket("ut-bkt-03")
        try:
            S3_ACL_OBJ.get_bucket_acl_using_iam_credentials(
                "dummyAccKey", "dummySecKey", "ut-bkt-03")
        except CTException as error:
            assert errmsg.INVALID_ACCESSKEY_ERR_KEY in str(error.message), error.message

    @pytest.mark.s3unittest
    def test_04_put_object_acl(self):
        """Test put object acl."""
        create_file(
            self.test_file_path,
            self.obj_size)
        op_val = S3_TEST_OBJ.create_bucket("ut-bkt-04")
        assert op_val[0], op_val[1]
        op_val = S3_TEST_OBJ.put_object(
            "ut-bkt-04",
            "ut-obj-04",
            self.test_file_path)
        assert op_val[0], op_val[1]
        op_im = IAM_OBJ.create_account(
            "ut-accnt-04",
            self.mail.format("ut-accnt-04"),
            self.ldap_user,
            self.ldap_pwd)
        can_id = op_im[1]['canonical_id']
        op_val = S3_ACL_OBJ.add_grantee(
            "ut-bkt-04",
            "ut-obj-04",
            can_id,
            "READ")
        assert op_val[0], op_val[1]

    @pytest.mark.s3unittest
    def test_05_put_object_canned_acl(self):
        """Test put object canned acl."""
        create_file(
            self.test_file_path,
            self.obj_size)
        op_val = S3_TEST_OBJ.create_bucket("ut-bkt-05")
        assert op_val[0], op_val[1]
        op_val = S3_TEST_OBJ.put_object(
            "ut-bkt-05",
            "ut-obj-05",
            self.test_file_path)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.create_account(
            "ut-accnt-63",
            self.mail.format("ut-accnt-05"),
            self.ldap_user,
            self.ldap_pwd)
        can_id = op_val[1]['canonical_id']
        op_val = S3_ACL_OBJ.put_object_canned_acl(
            bucket_name="ut-bkt-05", key="ut-obj-05",
            acl="private")
        assert op_val[0], op_val[1]
        op_val = S3_ACL_OBJ.put_object_canned_acl(
            bucket_name="ut-bkt-05", key="ut-obj-05",
            grant_read_acp=self.cid_key.format(can_id))
        assert op_val[0], op_val[1]
        try:
            S3_ACL_OBJ.put_object_canned_acl(
                bucket_name="ut-bkt-05", key="ut-obj-05",
                acl="private",
                grant_read_acp=self.cid_key.format(can_id))
        except CTException as error:
            assert "InvalidRequest" in str(error.message), error.message

    @pytest.mark.s3unittest
    def test_06_put_object_with_acl(self):
        """Test put object with acl."""
        create_file(
            self.test_file_path,
            self.obj_size)
        op_val = S3_TEST_OBJ.create_bucket("ut-bkt-06")
        assert op_val[0], op_val[1]
        op_val = S3_TEST_OBJ.put_object(
            "ut-bkt-06",
            "ut-obj-06",
            self.test_file_path)
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.create_account(
            "ut-accnt-06",
            self.mail.format("ut-accnt-06"),
            self.ldap_user,
            self.ldap_pwd)
        can_id = op_val[1]['canonical_id']
        op_val = S3_ACL_OBJ.put_object_with_acl(
            bucket_name="ut-bkt-06", key="ut-obj-06",
            file_path=self.test_file_path,
            acl="bucket-owner-read")
        assert op_val[0], op_val[1]
        op_val = S3_ACL_OBJ.put_object_with_acl(
            bucket_name="ut-bkt-06", key="ut-obj-06",
            file_path=self.test_file_path,
            grant_read_acp=self.cid_key.format(can_id))
        assert op_val[0], op_val[1]
        try:
            S3_ACL_OBJ.put_object_with_acl(
                bucket_name="ut-bkt-06", key="ut-obj-06",
                file_path=self.test_file_path,
                acl="bucket-owner-read",
                grant_read_acp=self.cid_key.format(can_id))
        except CTException as error:
            assert "InvalidRequest" in str(error.message), error.message

    @pytest.mark.s3unittest
    def test_07_create_bucket_with_acl(self):
        """Test create bucket with acl."""
        op_val = IAM_OBJ.create_account(
            "ut-accnt-07",
            self.mail.format("ut-accnt-07"),
            self.ldap_user,
            self.ldap_pwd)
        can_id = op_val[1]['canonical_id']
        S3_ACL_OBJ.create_bucket_with_acl(
            bucket_name="ut-bkt-07",
            acl="private")
        try:
            S3_ACL_OBJ.create_bucket_with_acl(
                bucket_name="ut-bkt-07",
                acl="private",
                grant_read_acp=self.cid_key.format(can_id))
        except CTException as error:
            assert "InvalidRequest" in str(error.message), error.message

    @pytest.mark.s3unittest
    def test_08_put_bucket_acl(self):
        """Test put bucket acl."""
        op_val = S3_TEST_OBJ.create_bucket("ut-bkt-08")
        assert op_val[0], op_val[1]
        op_val = S3_ACL_OBJ.put_bucket_acl(
            "ut-bkt-08", acl="private")
        assert op_val[0], op_val[1]
        op_val = IAM_OBJ.create_account(
            "ut-accnt-08",
            self.mail.format("ut-accnt-08"),
            self.ldap_user,
            self.ldap_pwd)
        can_id = op_val[1]['canonical_id']
        try:
            S3_ACL_OBJ.put_bucket_acl(
                bucket_name=self.dummy_bucket,
                acl="private",
                grant_read_acp=self.cid_key.format(can_id))
        except CTException as error:
            assert errmsg.NO_BUCKET_OBJ_ERR_KEY in str(error.message), error.message
