#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""Object ACL Test Module."""

import os
import random
import time
import logging
import copy
import json
import pytest

from commons import error_messages as errmsg
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from commons.utils import assert_utils
from config.s3 import S3_OBJ_TST
from config.s3 import S3_CFG
from libs.s3 import s3_multipart_test_lib
from libs.s3 import s3_test_lib
from libs.s3 import s3_acl_test_lib
from libs.s3 import s3_tagging_test_lib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations


class TestObjectACL:
    """Object ACL Test suite."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.s3_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_acl_obj = s3_acl_test_lib.S3AclTestLib(
            endpoint_url=S3_CFG["s3_url"])
        self.s3_mp_obj = s3_multipart_test_lib.S3MultipartTestLib(
            endpoint_url=S3_CFG["s3_url"])
        self.tag_obj = s3_tagging_test_lib.S3TaggingTestLib(
            endpoint_url=S3_CFG["s3_url"])
        self.test_file = "testfile-{}.txt".format(time.perf_counter_ns())
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestObjectACL")
        self.mupart_obj_path = os.path.join(self.test_dir_path, "mp_obj")
        self.test_file_path = os.path.join(self.test_dir_path, self.test_file)
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.log.info("Test file path: %s", self.test_file_path)
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.log.info("STARTED: SetUp Operations")
        self.start_range = S3_OBJ_TST["s3_object"]["start_range"]
        self.end_range = S3_OBJ_TST["s3_object"]["end_range"]
        self.random_num = str(
            random.choice(
                range(
                    self.start_range,
                    self.end_range)))
        self.bucket_name = S3_OBJ_TST["s3_object"]["bucket_name"].format(
            time.perf_counter_ns())
        self.obj_name = S3_OBJ_TST["s3_object"]["object_name"].format(
            time.perf_counter_ns())
        self.account_name = "objaclacc{}".format(time.perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.account_name)
        self.account_name_1 = "objaclacc_one{}".format(time.perf_counter_ns())
        self.email_id_1 = "{}@seagate.com".format(self.account_name_1)
        self.account_name_2 = "objaclacc_two{}".format(time.perf_counter_ns())
        self.email_id_2 = "{}@seagate.com".format(self.account_name_2)
        self.rest_obj = S3AccountOperations()
        self.account_list = []
        self.log.info("ENDED: SetUp Operations")
        yield
        self.log.info("STARTED: Teardown operation.")
        if os.path.exists(self.test_file_path):
            system_utils.remove_file(self.test_file_path)
        bucket_list = self.s3_obj.bucket_list()[1]
        if self.bucket_name in bucket_list:
            resp = self.s3_obj.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.delete_accounts(self.account_list)
        self.log.info("ENDED: Teardown operation.")

    def delete_accounts(self, accounts):
        """It will clean up resources which are getting created during test suite setup."""
        self.log.debug(accounts)
        for acc in accounts:
            resp = self.rest_obj.delete_s3_account(acc)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Deleted %s account successfully", acc)

    def create_bucket_obj(self, bucket, obj_name, s3_test_obj=None):
        """
        Helper function to create bucket and object.

        :param str bucket: Name of the bucket.
        :param str obj_name: Name of the object
        :param object s3_test_obj: Custom s3 test object
        :return: None
        """
        s3_tobj = s3_test_obj if s3_test_obj else self.s3_obj
        self.log.info("Step : Creating a bucket: %s", bucket)
        res = s3_tobj.create_bucket(bucket)
        assert res[0], res[1]
        self.log.info("Step : Bucket is created: %s", bucket)
        self.log.info("Step : Creating a object:%s", obj_name)
        system_utils.create_file(self.test_file_path,
                                 S3_OBJ_TST["s3_object"]["file_size"])
        res = s3_tobj.put_object(bucket, obj_name, self.test_file_path)
        assert res[0], res[1]
        self.log.info("Step : Object is created:%s", obj_name)

    def create_s3_account(self, account_name, email_id, password):
        """
        Function to create s3 Account using cortxcli tool and return account details and objects.

        :param str account_name: Name for an account
        :param str email_id: Email id for an account
        :param str password: Password for the account
        :return: canonical_id, S3_OBJ, S3_ACL_OBJ, s3_tag_obj in tuple.
        """
        self.log.info(
            "Step : Creating account with name %s and email_id %s",
            account_name, email_id)
        create_account = self.rest_obj.create_s3_account(
            acc_name=account_name, email_id=email_id, passwd=password)
        assert create_account[0], create_account[1]
        self.log.debug("Successfully created s3 account %s", create_account[1])
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        canonical_id = create_account[1]["canonical_id"]
        # Creating the new s3 and ACL Object
        s3t_obj = s3_test_lib.S3TestLib(
            access_key=access_key, secret_key=secret_key)
        s3_acl_obj = s3_acl_test_lib.S3AclTestLib(
            access_key=access_key, secret_key=secret_key)
        s3_tag_obj = s3_tagging_test_lib.S3TaggingTestLib(
            access_key=access_key, secret_key=secret_key)
        self.account_list.append(account_name)

        return canonical_id, s3t_obj, s3_acl_obj, s3_tag_obj

    def create_acc_and_put_obj_acp(self, bkt_name, obj_name, test_cfg):
        """
        Function will create new account.

        and it will also set the access control policy of an existing s3 object
        This function returns the new s3 test object
        :param str bkt_name: Name of the bucket
        :param str obj_name: Name of the object
        :param dict test_cfg: test-case yaml config values
        :return object S3_OBJect: new account S3_OBJect
        """
        account_name = "objaclacc-{}".format(time.perf_counter_ns())
        email_id = "{}@seagate.com".format(self.account_name)
        self.log.info("Creating account with name %s and email_id %s",
                      account_name, email_id)
        result = self.create_s3_account(
            account_name, email_id, self.s3acc_passwd)
        json_policy = test_cfg["grantee_json"]
        json_policy["Grantee"]["ID"] = result[0]
        json_policy["Grantee"]["DisplayName"] = account_name
        s3_obj_2 = result[1]
        self.log.info("Step: Put canned ACL for the Existing Object")
        resp = self.s3_acl_obj.get_object_acl(bkt_name, obj_name)
        modified_acl = copy.deepcopy(resp[1])
        modified_acl["Grants"].append(json_policy)
        resp = self.s3_acl_obj.put_object_acp(bkt_name, obj_name, modified_acl)
        assert resp[0], resp[1]
        self.log.info(
            "Step: Put object canned acl for the object was successful")

        return s3_obj_2

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5856")
    @CTFailOn(error_handler)
    def test_get_existing_obj_acl_2874(self):
        """Verify that user able to get object ACL details for existing object."""
        self.log.info(
            "verify that user able to get object ACL details for existing object")
        self.log.info(
            "Bucket and Object : %s %s",
            self.bucket_name,
            self.obj_name)
        obj_acl = S3_OBJ_TST["s3_object"]["full_ctrl"]
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info("Step 3: Getting the object ACL: %s", self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        self.log.info("Step 3: Object ACL resp is : %s", res)
        assert obj_acl == res[1]["Grants"][0]["Permission"], res[0]
        self.log.info(
            "verify that user able to get object ACL details for existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5855")
    @CTFailOn(error_handler)
    def test_get_nonexising_obj_acl_2875(self):
        """verify that user able to get object ACL details for non existing object."""
        self.log.info(
            "verify that user able to get object ACL details for non existing object")
        self.log.info("Step 1: Creating a bucket: %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert res[0], res[1]
        self.log.info("Step 1: Bucket is created: %s", self.bucket_name)
        self.log.info(
            "Step 2: Getting the object ACL for object non-existing obj: %s",
            self.obj_name)
        try:
            self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["key_err"] in error.message, error.message
        self.log.info(
            "Step 2: Object ACL resp for non-existing object is: %s", res)
        self.log.info(
            "verify that user able to get object ACL details for non existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5854")
    @CTFailOn(error_handler)
    def test_download_with_empty_key_2876(self):
        """Verify that user able to download with empty key or not."""
        self.log.info(
            "verify that user able to download with empty key or not")
        self.log.info("Step 1: Creating a bucket: %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert res[0], res[1]
        self.log.info("Step 1: Bucket is created: %s", self.bucket_name)
        self.log.info(
            "Step 2: Getting the object ACL for object : %s", self.obj_name)
        try:
            self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["key_err"] in error.message, error.message
        self.log.info("Step 2: Object ACL resp is : %s", res)
        self.log.info(
            "verify that user able to download with empty key or not")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5857")
    @CTFailOn(error_handler)
    def test_reupload_get_obj_acl_2877(self):
        """User able to reupload object and get object acl."""
        self.log.info("User able to reupload object and get object acl")
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info("Step 1: Re-Uploading Object : %s", self.obj_name)
        res = self.s3_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.test_file_path)
        assert res[0], res[1]
        self.log.info("Step 2: Object is re-uploaded status: %s", res)
        self.log.info(
            "Step 2: Getting the object ACL after delete for object : %s",
            self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 3: Object ACL resp is : %s", res)
        self.log.info("User able to re-upload object and get object acl")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5858")
    @CTFailOn(error_handler)
    def test_verify_del_obj_acl_2878(self):
        """User should not get object acl when object was deleted."""
        self.log.info(
            "User should not get object acl when object was deleted")
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info("Step 3: Deleting object %s", self.obj_name)
        res = self.s3_obj.delete_object(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 3: Object Deleted %s", self.obj_name)
        self.log.info(
            "Step 4: Getting the object ACL for object : %s", self.obj_name)
        try:
            self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["key_err"] in error.message, error.message
        self.log.info("Step 4: Object ACL resp is : %s", res)
        self.log.info(
            "User should not get object acl when object was deleted")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-19885")
    @CTFailOn(error_handler)
    def test_get_obj_acl_mp(self):
        """user should able to get Object acl when multipart object is uploaded."""
        self.log.info(
            "user should able to get Object acl when multipart object is uploaded")
        obj_acl = S3_OBJ_TST["s3_object"]["full_ctrl"]
        file_size = S3_OBJ_TST["test_get_obj_acl_mp"]["file_size"]
        total_parts = S3_OBJ_TST["test_get_obj_acl_mp"]["total_parts"]
        self.log.info("Step 1: Creating a bucket: %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert res[0], res[1]
        self.log.info("Step 1: Bucket is created: %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating multipart for object upload: %s", self.obj_name)
        res = self.s3_mp_obj.create_multipart_upload(
            self.bucket_name, self.obj_name)
        assert res[0], res[1]
        res = self.s3_mp_obj.list_multipart_uploads(self.bucket_name)
        assert res[0], res[1]
        self.log.info(
            "Step 2: Listing of multipart object resp after multipart create: %s",
            res)
        self.log.info("Step 3: Uploading multi parts for object")
        upload_id = res[1]["Uploads"][0]["UploadId"]
        res = self.s3_mp_obj.upload_parts(
            upload_id,
            self.bucket_name,
            self.obj_name,
            file_size,
            total_parts=total_parts,
            multipart_obj_path=self.mupart_obj_path)
        assert res[1], res[1]
        self.log.info("Step 3: Uploading parts for object in progress")
        upload_parts_list = res[1]
        res = self.s3_mp_obj.list_parts(
            upload_id, self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 4: Complete the multipart upload process")
        res = self.s3_mp_obj.complete_multipart_upload(
            upload_id, upload_parts_list, self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 4: Multipart upload completed")
        self.log.info(
            "Step 5: Getting the object ACL for object :%s", self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 5: Object ACL resp is : %s", res)
        assert obj_acl == res[1]["Grants"][0]["Permission"], res[1]
        self.log.info("Clean Up Stage: Deleting all files created locally")
        self.log.info("Clean Up Stage: Done cleaning")
        self.log.info(
            "user should able to get Object acl when multipart object is uploaded")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5862")
    @CTFailOn(error_handler)
    def test_multipart_upload_verify_obj_acl_2879(self):
        """
        Perform Manual Multipart Object upload using create-multipart-upload.

        and complete-multipart-upload and verify Get object ACL
        """
        self.log.info(
            "Perform Manual Multipart Object upload using create-multipart-upload and "
            "complete-multipart-upload and verify Get object ACL")
        single_part_sz = S3_OBJ_TST["test_2879"]["single_part_sz"]
        total_parts = S3_OBJ_TST["test_2879"]["total_parts"]
        object_acl = S3_OBJ_TST["s3_object"]["full_ctrl"]
        self.log.info("Step 1: Creating a bucket: %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert res[0], res[1]
        self.log.info("Step 1: Bucket is created: %s", self.bucket_name)
        self.log.info(
            "Step 2: Creating multipart for object upload:%s", self.obj_name)
        res = self.s3_mp_obj.create_multipart_upload(
            self.bucket_name, self.obj_name)
        assert res[0], res[1]
        res = self.s3_mp_obj.list_multipart_uploads(self.bucket_name)
        self.log.info(
            "Step 2: Listing of multipart object resp after multipart create: %s",
            res)
        self.log.info("Step 3: Uploading multi parts for object")
        assert res[0], res[1]
        upload_id = res[1]["Uploads"][0]["UploadId"]
        res = self.s3_mp_obj.upload_parts(
            upload_id,
            self.bucket_name,
            self.obj_name,
            single_part_sz,
            total_parts=total_parts,
            multipart_obj_path=self.mupart_obj_path)
        assert res[0], res[1]
        upload_parts_list = res[1]
        res = self.s3_mp_obj.list_parts(
            upload_id, self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 3: Multipart upload list is : %s", res)
        self.log.info("Step 4: Complete the multipart upload")
        res = self.s3_mp_obj.complete_multipart_upload(
            upload_id, upload_parts_list, self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 4: Completed multipart upload")
        self.log.info(
            "Step 5: Getting the object ACL for object :%s", self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 5: Object ACL resp is : %s", res)
        assert object_acl == res[1]["Grants"][0]["Permission"], res[1]
        self.log.info("Clean Up Stage: Deleting all files created locally")
        self.log.info(
            "Perform Manual Multipart Object upload using create-multipart-upload and "
            "complete-multipart-upload and verify Get object ACL")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5787")
    @CTFailOn(error_handler)
    def test_default_multipart_upload_2910(self):
        """Perform Multipart Obj upload using default Multipart upload & verify Get object ACL."""
        self.log.info(
            "Perform Multipart Object upload "
            "using default Multipart upload and verify Get object ACL")
        object_acl = S3_OBJ_TST["s3_object"]["full_ctrl"]
        self.log.info("Step 1: Creating a bucket: %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert res[0], res[1]
        self.log.info("Step 1: Bucket is created: %s", self.bucket_name)
        self.log.info("Step 2: Creating file locally for upload")
        res = system_utils.create_file(
            self.test_file_path, S3_OBJ_TST["test_9897"]["f_size"])
        assert res[0], res[1]
        self.log.info("Step 2: Completed creating files locally")
        self.log.info("Step 3: Uploading Object : %s", self.obj_name)
        res = self.s3_obj.object_upload(
            self.bucket_name,
            self.obj_name,
            self.test_file_path)
        assert res[0], res[1]
        self.log.info("Step 3: Completed Uploading for Object")
        res = self.s3_obj.object_list(self.bucket_name)
        assert res[0], res[1]
        self.log.info(
            "Step 5: Getting the object ACL for object: %s", self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert object_acl == res[1]["Grants"][0]["Permission"], res[1]
        self.log.info("Step 5: Object ACL resp is : %s", res)
        self.log.info("Clean Up Stage: Deleting all files created locally")
        self.log.info("Clean Up Stage: Done cleaning")
        self.log.info(
            "Perform Multipart Object upload using default Multipart upload "
            "and verify Get object ACL")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5803")
    @CTFailOn(error_handler)
    def test_multipart_upload_chunksize_2911(self):
        """
        Perform Multipart Object upload using default upload.

        by specifically providing chunksize using aws s3 command set
        """
        self.log.info(
            "Perform Multipart Object upload using default upload by specifically providing "
            "chunksize using aws s3 command set")
        object_acl = S3_OBJ_TST["s3_object"]["full_ctrl"]
        system_utils.remove_file(S3_OBJ_TST["test_9898"]["run_cmd"])
        self.log.info("Step 1: Creating a bucket: %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert res[0], res[1]
        self.log.info("Step 1: Bucket is created: %s", self.bucket_name)
        self.log.info("Step 2: Creating file locally for upload")
        res = system_utils.create_file(
            self.test_file_path, S3_OBJ_TST["test_9898"]["f_size"])
        assert res[0], res[1]
        self.log.info("Step 2: Completed creating files locally")
        self.log.info("Step 3: Uploading Object : %s", self.obj_name)
        res = self.s3_obj.object_upload(
            self.bucket_name,
            self.obj_name,
            self.test_file_path)
        assert res[0], res[1]
        self.log.info("Step 3: Completed uploading for Object")
        res = self.s3_obj.object_list(self.bucket_name)
        assert res[0], res[1]
        self.log.info(
            "Step 4: Getting the object ACL for object :%s", self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 4: Object ACL resp is : %s", res)
        assert object_acl == res[1]["Grants"][0]["Permission"], res[1]
        self.log.info("Clean Up Stage: Deleting all files created locally")
        system_utils.remove_file(self.test_file_path)
        self.log.info("Clean Up Stage: Done cleaning")
        self.log.info(
            "Perform Multipart Object upload using default upload by specifically providing "
            "chunksize using aws s3 command set")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5804")
    @CTFailOn(error_handler)
    def test_upload_abort_multipart_upload_2912(self):
        """Perform Multipart Object upload & abort Multipart upload & verify Get Object ACL."""
        self.log.info(
            "Perform Manual Multipart Object upload and abort"
            " Multipart upload and verify Get Object ACL")
        single_part_sz = S3_OBJ_TST["test_9899"]["single_part_sz"]
        total_parts = S3_OBJ_TST["test_9899"]["single_part_sz"]
        self.log.info("Step 1: Creating a bucket: %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert res[0], res[1]
        self.log.info("Step 1: Bucket is created: %s", self.bucket_name)
        self.log.info("Step 2: Creating file locally for upload")
        res = self.s3_mp_obj.create_multipart_upload(
            self.bucket_name, self.obj_name)
        assert res[0], res[1]
        res = self.s3_mp_obj.list_multipart_uploads(self.bucket_name)
        self.log.info("Step 2: Completed creating files locally")
        assert res[0], res[1]
        upload_id = res[1]["Uploads"][0]["UploadId"]
        self.log.info("Step 3: Uploading Object :%s", self.obj_name)
        res = self.s3_mp_obj.upload_parts(
            upload_id,
            self.bucket_name,
            self.obj_name,
            single_part_sz,
            total_parts=total_parts,
            multipart_obj_path=self.mupart_obj_path)
        assert res[0], res[1]
        res = self.s3_mp_obj.list_parts(
            upload_id, self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 3: Uploading for Object in progress")
        self.log.info("Step 4: Aborting the multipart upload")
        res = self.s3_mp_obj.abort_multipart_all(
            self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 4: Aborted the multipart upload")
        self.log.info(
            "Step 5: Getting the object ACL for object :%s", self.obj_name)
        try:
            self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["key_err"] in error.message, error.message
        self.log.info("Step 5: Object ACL resp is : %s", res)
        self.log.info("Clean Up Stage: Deleting all files created locally")
        self.log.info("Clean Up Stage: Done cleaning")
        self.log.info(
            "Perform Manual Multipart Object upload and abort "
            "Multipart upload and verify Get Object ACL")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5760")
    @CTFailOn(error_handler)
    def test_vald_custom_acl_xml_3210(self):
        """put object acl with valid custom acl xml and check get object acl and compare."""
        self.log.info(
            "put object acl with valid custom acl xml and check get object acl and compare")
        permission = S3_OBJ_TST["s3_object"]["full_ctrl"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info("Step 4: Added grantee to the object%s", self.obj_name)
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name,
            self.obj_name,
            canonical_id,
            permission)
        assert res[0], res[1]
        self.log.info("Step 4: Grantee added for the object%s", self.obj_name)
        self.log.info(
            "Step 5: Get object acl of object %s after put object acl",
            self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert canonical_id in str(res[1]), res[0]
        self.log.info("Step 5: Object ACL resp is : %s", res)
        self.log.info(
            "put object acl with valid custom acl xml and check get object acl and compare")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5777")
    @CTFailOn(error_handler)
    def test_valid_canonical_id_3211(self):
        """put object acl with a valid canonical ID."""
        self.log.info("put object acl with a valid canonical ID")
        permission = S3_OBJ_TST["s3_object"]["full_ctrl"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info("Step 4: Added grantee to the object%s", self.obj_name)
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name,
            self.obj_name,
            canonical_id,
            permission)
        assert res[0], res[1]
        self.log.info("Step 4: Grantee added for the object%s", self.obj_name)
        self.log.info(
            "Step 5: Get object acl of object %s after put object acl",
            self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert canonical_id in str(res[1]), res[1]
        self.log.info("Step 5: Object ACL resp is : %s", res)
        self.log.info("Put object acl with a valid canonical ID")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5779")
    @CTFailOn(error_handler)
    def test_invalid_canonical_id_3212(self):
        """put object acl with a invalid canonical ID."""
        self.log.info("put object acl with a invalid canonical ID")
        permission = S3_OBJ_TST["s3_object"]["full_ctrl"]
        invalid_canonical_id = S3_OBJ_TST["test_3212"]["invalid_can_id"]
        assert_msg = S3_OBJ_TST["test_3212"]["assert_msg"]
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info(
            "Step 3: Put object acl of object %s with invalid canonical id",
            self.obj_name)
        try:
            self.s3_acl_obj.add_grantee(
                self.bucket_name,
                self.obj_name,
                invalid_canonical_id,
                permission)
        except CTException as error:
            assert assert_msg in error.message, error.message
        self.log.info(
            "Step 3: Grantee with Invalid canonical ID added for the object %s",
            self.obj_name)
        self.log.info("Put object acl with a invalid canonical ID")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5759")
    @CTFailOn(error_handler)
    def test_valid_read_permission_3213(self):
        """put object acl with valid permission ------------>> [Read]."""
        self.log.info(
            "put object acl with valid permission ------------>> [Read]")
        permission = S3_OBJ_TST["test_3213"]["obj_acl_rd"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        self.log.info("Step 1: Completed creating account")
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info("Step 2: Put read permission to object%s", self.obj_name)
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name,
            self.obj_name,
            canonical_id,
            permission)
        assert res[0], res[1]
        self.log.info("Step 2: Added read permission to object")
        self.log.info(
            "Step 3: Get object acl of object %s after put object acl",
            self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert canonical_id in str(res[1]), res[1]
        assert permission in str(res[1]), res[1]
        self.log.info("Step 3: Object ACL resp is : %s", res)
        self.log.info(
            "put object acl with valid permission ------------>> [Read]")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5756")
    @CTFailOn(error_handler)
    def test_valid_write_permission_3214(self):
        """put object acl with valid permission ------------>> [Write]."""
        self.log.info(
            "put object acl with valid permission ------------>> [Write]")
        permission = S3_OBJ_TST["test_3214"]["obj_acl_wr"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info(
            "Step 1: Set write permission to object%s",
            self.obj_name)
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name,
            self.obj_name,
            canonical_id,
            permission)
        assert res[0], res[1]
        self.log.info(
            "Step 1: Permission %s set for the object",
            self.obj_name)
        self.log.info(
            "Step 2: Get object acl of object %s after put object acl",
            self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert canonical_id in str(res[1]), res[1]
        assert permission in str(res[1]), res[1]
        self.log.info("Step 2: Object ACL resp is : %s", res)
        self.log.info(
            "Put object acl with valid permission ------------>> [Write]")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5757")
    @CTFailOn(error_handler)
    def test_valid_read_acp_permission_3215(self):
        """Put object acl with valid permission ------------>> [Read_acp]."""
        self.log.info(
            "put object acl with valid permission ------------>> [Read_acp]")
        permission = S3_OBJ_TST["test_3215"]["obj_acl_rdc"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info(
            "Step 1: Put read_acp permission to object%s", self.obj_name)
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name,
            self.obj_name,
            canonical_id,
            permission)
        assert res[0], res[1]
        self.log.info(
            "Step 4: Set write permission to object%s",
            self.obj_name)
        self.log.info(
            "Step 1: Get object acl of object %s after put object acl",
            self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert canonical_id in str(res[1]), res[1]
        assert permission in str(res[1]), res[1]
        self.log.info("Step 5: Object ACL resp is : %s", res)
        self.log.info(
            "put object acl with valid permission ------------>> [Read_acp]")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5742")
    @CTFailOn(error_handler)
    def test_valid_write_acp_permission_3216(self):
        """Put object acl with valid permission ------------>> [Write_acp]."""
        self.log.info(
            "put object acl with valid permission ------------>> [Write_acp]")
        permission = S3_OBJ_TST["test_3216"]["obj_acl_wrc"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info(
            "Step 2: Put write_acp permission to object%s", self.obj_name)
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name,
            self.obj_name,
            canonical_id,
            permission)
        assert res[0], res[1]
        self.log.info(
            "Step 2: Set write permission to object%s",
            self.obj_name)
        self.log.info(
            "Step 3: Get object acl of object %s after put object acl",
            self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert canonical_id in str(res[1]), res[1]
        assert permission in str(res[1]), res[1]
        self.log.info("Step 3: Object ACL resp is : %s", res)
        self.log.info(
            "put object acl with valid permission ------------>> [Write_acp]")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5763")
    @CTFailOn(error_handler)
    def test_invalid_permission_3217(self):
        """Put object acl with invalid permission."""
        self.log.info("put object acl with invalid permission")
        permission = S3_OBJ_TST["test_3217"]["obj_acl_rdwr"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        try:
            self.log.info(
                "Step 1: Put invalid permission to object%s", self.obj_name)
            self.s3_acl_obj.add_grantee(
                self.bucket_name,
                self.obj_name,
                canonical_id,
                permission)
        except CTException as error:
            assert errmsg.S3_INVALID_ACL_ERR in error.message, error.message
        self.log.info("Step 1: Invalid permission set for object%s", self.obj_name)
        self.log.info("Put object acl with invalid permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5762")
    @CTFailOn(error_handler)
    def test_invalid_xml_structure_3218(self):
        """Put object acl with invalid XML structure."""
        self.log.info("put object acl with invalid XML structure")
        permission = S3_OBJ_TST["test_3218"]["obj_acl_rdwr"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info("Step 1: Put permission with invalid XML structure")
        acl = {"Owner": {},
               "Grants": [{"Grantee": {"ID": canonical_id,
                                       "Type": S3_OBJ_TST["test_3218"]["Type"],
                                       "DisplayName": S3_OBJ_TST["test_3218"]["DisplayName"]},
                           "Permission": permission}]}
        try:
            self.s3_acl_obj.put_object_acp(
                self.bucket_name, self.obj_name, acl)
        except CTException as error:
            assert errmsg.S3_INVALID_ACL_ERR in error.message, error.message
        self.log.info(
            "Step 1: Done setting permission for the object using XML structure")
        self.log.info("put object acl with invalid XML structure")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5768")
    @CTFailOn(error_handler)
    def test_cross_account_grant_3226(self):
        """put object acl with cross account grant& run get-object-acl to get ACL XML & compare."""
        self.log.info(
            "put object acl with cross account grant and run "
            "get-object-acl to get ACL XML and compare")

        permission = S3_OBJ_TST["s3_object"]["full_ctrl"]
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_1 = result[0]
        self.log.info("Step 1: Completed creating account 1")
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_2 = result[0]
        self.log.info("Step 2: Completed creating account 2")
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info(
            "Step 4: Put object acl of object %s for account 1 %s",
            self.obj_name, self.account_name_1)
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name,
            self.obj_name,
            canonical_id_1,
            permission)
        assert res[0], res[1]
        self.log.info(
            "Step 4: Completed Setting permission to object acl by account 1 %s",
            self.obj_name)
        self.log.info(
            "Step 5: Put object acl of object %s with canonical id for account 2%s",
            self.obj_name,
            canonical_id_2)
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name,
            self.obj_name,
            canonical_id_2,
            permission)
        assert res[0], res[1]
        self.log.info(
            "Step 5: Completed setting permission to "
            "object with canonical id using account 2%s",
            self.obj_name)
        self.log.info(
            "Step 5: Get object acl of object %s after put object acl",
            self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert canonical_id_1 in str(res[1]), res[1]
        assert canonical_id_2 in str(res[1]), res[1]
        self.log.info(
            "Step 5: Object ACL resp is %s", res)
        self.log.info(
            "put object acl with cross account grant and "
            "run get-object-acl to get ACL XML and compare")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5765")
    @CTFailOn(error_handler)
    def test_put_objacl_invalid_obj_3227(self):
        """put object acl with invalid object [i.e object is not present]."""
        self.log.info(
            "put object acl with invalid object   [i.e object is not present]")
        permission = S3_OBJ_TST["s3_object"]["full_ctrl"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        self.log.info("Step 1: Completed creating account")
        self.log.info("Step 2: Creating bucket %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert res[0], res[1]
        self.log.info("Step 2: Bucket created")
        self.log.info("Step 3: Put object acl with invalid object")
        acl = {
            "Owner": {
                "DisplayName": S3_OBJ_TST["test_3227"]["DisplayName"],
                "ID": canonical_id},
            "Grants": [
                {
                    "Grantee": {
                        "ID": canonical_id,
                        "Type": S3_OBJ_TST["test_3227"]["Type"],
                        "DisplayName": S3_OBJ_TST["test_3227"]["DisplayName"]},
                    "Permission": permission}]}
        try:
            self.s3_acl_obj.put_object_acp(
                self.bucket_name, self.obj_name, acl)
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["key_err"] in error.message, error.message
        self.log.info(
            "Step 3: Put object acl with invalid object operation completed: %s",
            res)
        self.log.info(
            "Put object acl with invalid object [i.e object is not present]")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5780")
    @CTFailOn(error_handler)
    def test_put_obj_acl_100grants_3229(self):
        """put object acl with 100 grants."""
        self.log.info("put object acl with 100 grants")
        permission = S3_OBJ_TST["s3_object"]["full_ctrl"]
        name_initial = "100grants-{}{}"
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info(
            "Step 1: Creating n number of accounts to add grantee")
        for each in range(0, S3_OBJ_TST["test_3229"]["grant_count"]):
            account_name = name_initial.format(
                str(time.perf_counter_ns()), str(each))
            email_id = "{}{}".format(
                account_name, S3_OBJ_TST["test_3229"]["name_postfix"])
            result = self.create_s3_account(
                account_name, email_id, self.s3acc_passwd)
            can_id = result[0]
            op_val = self.s3_acl_obj.add_grantee(
                self.bucket_name, self.obj_name, can_id, permission)
            assert op_val[0], op_val[1]
            res = self.s3_acl_obj.get_object_acl(
                self.bucket_name, self.obj_name)
            assert res[0], res[1]
        self.log.info(
            "Step 1: Completed adding n number of grantee for object : %s",
            self.obj_name)
        self.log.info("Put object acl with 100 grants")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5761")
    @CTFailOn(error_handler)
    def test_put_objacl_morethan_100grants_3230(self):
        """Put object acl with more than 100 grants."""
        self.log.info("put object acl with more than 100 grants")
        permission = S3_OBJ_TST["s3_object"]["full_ctrl"]
        name_initial = "100grants-{}{}"
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info(
            "Step 1: Creating n number of accounts to add grantee")
        for each in range(0, S3_OBJ_TST["test_3230"]["grant_count"]):
            account_name = name_initial.format(
                str(time.perf_counter_ns()), str(each))
            email_id = "{}{}".format(
                account_name, S3_OBJ_TST["test_3230"]["name_postfix"])
            result = self.create_s3_account(
                account_name, email_id, self.s3acc_passwd)
            can_id = result[0]
            op_val = self.s3_acl_obj.add_grantee(
                self.bucket_name, self.obj_name, can_id, permission)
            assert op_val[0], op_val[1]
            res = self.s3_acl_obj.get_object_acl(
                self.bucket_name, self.obj_name)
            assert res[0], res[1]
        else:
            acc_name = name_initial.format(
                str(time.perf_counter_ns()), str(101))
            email = "{}{}".format(
                acc_name, S3_OBJ_TST["test_3230"]["name_postfix"])
            result = self.create_s3_account(
                acc_name, email, self.s3acc_passwd)
            canonical_id = result[0]
            try:
                self.s3_acl_obj.add_grantee(
                    self.bucket_name, self.obj_name, canonical_id, permission)
            except CTException as error:
                assert errmsg.S3_INVALID_ACL_ERR in error.message, error.message
                self.log.error(error.message)
        self.log.info("Put object acl with 100 grants")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5767")
    @CTFailOn(error_handler)
    def test_put_obj_invalid_partid_display_3231(self):
        """put object acl with invalid <owner> part id and Display name."""
        self.log.info(
            "put object acl with invalid <owner> part id and Display name")
        self.log.info("put object acl with more than 100 grants")
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        acl = self.s3_acl_obj.get_object_acl(
            self.bucket_name, self.obj_name)[1]
        modified_acl = copy.deepcopy(acl)
        modified_acl["Owner"]["ID"] = S3_OBJ_TST["test_3231"]["modified_acl_id"]
        modified_acl["Owner"]["DisplayName"] = S3_OBJ_TST["test_3231"]["modified_acl_name"]
        self.log.info(
            "Step 1: Put object acl with invalid display name and invalid id")
        try:
            self.s3_acl_obj.put_object_acp(
                self.bucket_name, self.obj_name, modified_acl)
        except CTException as error:
            assert errmsg.S3_INVALID_ACL_ERR in error.message, error.message
        self.log.info(
            "Step 1: Done setting put object acl with invalid display name and invalid id")
        self.log.info(
            "put object acl with invalid <owner> part id and Display name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5793")
    @CTFailOn(error_handler)
    def test_canned_acl_3682(self):
        """Add canned acl private for put object acl in account1 and get object from account2."""
        self.log.info(
            "Add canned acl private for put object acl in account1 and get object from account2")
        acl_permission = S3_OBJ_TST["test_3682"]["acl_permission"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        # User Account Variables
        # Creating User Account 1
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        # Creating the new s3 and ACL Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        self.log.info("Step 1: Creating Bucket and Object")
        # Create Bucket with Account 1st
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        # Creating Object inside the bucket
        obj_resp = s3_obj_1.put_object(
            self.bucket_name, self.obj_name, self.test_file_path)
        assert obj_resp[0], obj_resp[1]
        self.log.info("Step 1: Done Creating Bucket and Object")
        # Setting the Canned ACL for the Existing Object
        self.log.info(
            "Step 2: Setting the Canned ACL for the Existing Object")
        put_acl_res = s3_acl_obj_1.put_object_canned_acl(
            self.bucket_name, self.obj_name, acl=acl_permission)
        assert put_acl_res[0], True
        obj_acl = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 2: Response for the Existing Object %s", obj_acl)
        # Creating 2nd User Account
        # User Account Variables
        self.log.info("Step 3: Creating 2nd Account")
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_acl_obj_2 = result[2]
        self.log.info("Step 3: Created second account")
        # Creating the 2nd user s3 Object
        try:
            self.log.info("Step 5: Getting object from user 2")
            s3_acl_obj_2.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("Step 5: Object resp should fail with exception")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info("Add canned acl private for put object acl in \
                                                    account1 and get object from account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5791")
    @CTFailOn(error_handler)
    def test_put_get_canned_acl_3683(self):
        """Add canned acl private for put object in account1 and get object from account2."""
        self.log.info(
            "Add canned acl private for put object in account1 and get object from account2")
        acl_permission = S3_OBJ_TST["test_3683"]["acl_permission"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        # User Account Variables

        # Creating User Account 1
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        # Create Bucket with 1st User
        self.log.info(
            "Step 2: Creating Bucket and Object with ACL property")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        self.log.info(
            "Creating Object inside the bucket with canned ACL property")
        obj_resp = s3_acl_obj_1.put_object_with_acl(
            self.bucket_name, self.obj_name, self.test_file_path, acl=acl_permission)
        assert obj_resp[0], obj_resp[1]
        self.log.info(
            "Step 2: Done creating Object with canned ACL property")
        obj_acl = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        # Creating 2nd User Account
        # User Account Variables
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        # Creating the 2nd user s3-Object
        self.log.info("Getting object from user 2")
        s3_acl_obj_2 = result[2]
        # Performing the get ACL using the Account 2
        self.log.info("Getting the Object from user account 2")
        try:
            self.log.info("Step 5: Getting object from user 2")
            s3_acl_obj_2.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned acl private for put object in account1 and get object from account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5748")
    @CTFailOn(error_handler)
    def test_private_canned_write_acp_3684(self):
        """
        put object from account1 and give write-acp to account2.

        and apply private canned acl for put-object-acl and check for get-object-acl from account1
        """
        self.log.info(
            "put object in account1 and give write-acp to account2 and apply"
            " private canned acl for put-objecct-acl and check for get-object-acl from account1")
        write_acp = S3_OBJ_TST["test_3684"]["acl_permission"]
        self.log.info("Step 1: Creating account 2 ")
        result = self.create_s3_account(
            self.account_name, self.email_id_1, self.s3acc_passwd)
        canonical_id = result[0]
        self.log.info("Step 1: Completed Creating account 2 completed")
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        # Adding Write Permission for the 2nd User
        self.log.info(
            "Stpe 2 : Put write permission to object %s", self.obj_name)
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name, self.obj_name, canonical_id, write_acp)
        assert res[0], res[1]
        self.log.info(
            "Step 3 : Permission set for the object %s", self.obj_name)
        # Checking the get-object-acl  permission are granted correctly
        self.log.info(
            "Step 3: Get object acl of object %s after put object acl",
            self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert canonical_id in str(res[1]), res[1]
        self.log.info("Step 4: Get object acl response is %s", res)
        self.log.info("Creating s3 ACL object for user 2 account")
        s3_acl_user2 = result[2]
        # Logging to account2 and perform put-object acl with private canned
        # acl
        private_acp = S3_OBJ_TST["test_3684"]["private_acp"]
        self.log.info(
            "Step 4: Login to account2 and perform put-object acl with private canned acl")
        obj_resp = s3_acl_user2.put_object_canned_acl(
            self.bucket_name, self.obj_name, acl=private_acp)
        assert obj_resp[0]
        self.log.info(
            "Step 4: Done changing the permission of object from 2nd account")
        self.log.info(
            "Step 5: After login to account1 and check with get-object-acl")
        get_res = self.s3_acl_obj.get_object_acl(
            self.bucket_name, self.obj_name)
        self.log.info(
            "Step 5: Get object ACL resp from defaul account: %s", get_res)
        assert get_res[0], get_res[1]
        self.log.info(
            "put object in account1 and give write-acp to account2 and apply private"
            "canned acl for put-object-acl and check for get-object-acl from account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5794")
    @CTFailOn(error_handler)
    def test_canned_acl_authenticated_read_3685(self):
        """
        Add canned acl authenticated-read for put object in account1.

        and try to get object from account2
        """
        self.log.info(
            "Add canned acl authenticated-read for put object in account1 "
            "and try to get object from account2")
        auth_read = S3_OBJ_TST["test_3685"]["auth_read"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        # Creating User Account 1
        self.log.info("Step 1: Creating User Account 1")
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Successfully Created account 1")
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        # Create Bucket with 1st User
        self.log.info(
            "Step 2: Creating Bucket and Object with ACL property")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        # Creating Object inside the bucket with canned ACL property
        obj_resp = s3_acl_obj_1.put_object_with_acl(
            self.bucket_name, self.obj_name, self.test_file_path, acl=auth_read)
        assert obj_resp[0]
        # Get Object ACL validation
        self.log.info(
            "Step 2: Done creating Object with canned ACL property")
        self.log.info("Step 3: Getting Object ACL from the Parent Account")
        obj_acl = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 3: Get response of the get ACL is : %s", obj_acl)
        # Creating 2nd User Account and setting User Account Variables
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        # Creating the 2nd user s3-Object
        self.log.info("Getting object from user 2")
        s3_acl_obj_2 = result[2]
        # Performing the get ACL using the Account 2
        try:
            self.log.info("Getting the Object from user second")
            s3_acl_obj_2.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned acl authenticated-read for put object in account1 "
            "and try to get object from account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5797")
    @CTFailOn(error_handler)
    def test_put_get_canned_acl_authread_3686(self):
        """
        Add canned acl authenticated-read for put object acl in account1.

        and try to get object from account2
        """
        self.log.info(
            "Add canned acl authenticated-read for put object acl in account1 "
            "and try to get object from account2")
        auth_read = S3_OBJ_TST["test_3686"]["auth_read"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        # Creating User Account 1
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        self.log.info("Step 1: Done creating account 1")
        self.log.info("Step 2:Create Bucket and object with 1st User")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        # Creating Object inside the bucket
        put_obj_res = s3_obj_1.put_object(
            self.bucket_name, self.obj_name, self.test_file_path)
        self.log.info("Put object resp %s", put_obj_res)
        assert put_obj_res[0], put_obj_res[1]
        # Setting the Canned ACL for the new Object
        self.log.info(
            "Step 2:Done creating Bucket and object with 1st User")
        self.log.info("Step 3: Updating the acl property of the object")
        put_acl_res = s3_acl_obj_1.put_object_canned_acl(
            self.bucket_name, self.obj_name, acl=auth_read)
        assert put_acl_res[1]
        # Get Object ACL for user 1
        self.log.info(
            "Step 3: Successfully Updated the acl property of the object")
        self.log.info("Step 4: Verify the acl property of the object")
        obj_acl = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info("Step 4: Verified the acl property of the object")
        # Creating 2nd User Account
        # User Account Variables
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        # Creating the 2nd user s3 Object
        s3_acl_obj_2 = result[2]
        # Getting the Object from Account 2
        try:
            self.log.info("Step 6: Getting the Object from user second")
            s3_acl_obj_2.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 6: Get object ACL response using account 2 is AccessDenied")
        object_file_resp = s3_acl_obj_2.s3_client.get_object(
            Bucket=self.bucket_name, Key=self.obj_name)
        self.log.info("Object file resp : %s", object_file_resp)
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned acl authenticated-read for put object acl in account1 "
            "and try to get object from account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5749")
    @CTFailOn(error_handler)
    def test_authenticated_read_canned_acl_3687(self):
        """
        put object in account1 and give write-acp to account2.

        and apply authenticated-read canned acl for put-object-acl
        and check for get-object-acl from account1
        """
        self.log.info(
            "put object in account1 and give write-acp to account2 and apply "
            "authenticated-read canned acl for put-object-acl and "
            "check for get-object-acl from account1")
        write_acp = S3_OBJ_TST["test_3687"]["write_acp"]
        auth_read = S3_OBJ_TST["test_3687"]["auth_read"]
        error_msg = errmsg.ACCESS_DENIED_ERR_KEY
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        # Creating User Account 2
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info(
            "Step 2: Creating Bucket and putting object into it using Account 1")
        self.log.info("Creating bucket %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert res[0], res[1]
        self.log.info(
            "Putting object %s to existing bucket %s",
            self.obj_name, self.bucket_name)
        put_res = self.s3_obj.put_object(
            self.bucket_name, self.obj_name, self.test_file_path)
        assert put_res[0]
        self.log.info(
            "Step 2: Successfully Created Bucket and uploaded object using Account 1")
        self.log.info("Step 3: Get Object ACL property")
        get_obj_res = self.s3_acl_obj.get_object_acl(
            self.bucket_name, self.obj_name)
        assert get_obj_res[0], get_obj_res[1]
        self.log.info("Step 4: Get Object ACL resp : %s", get_obj_res)
        # Adding Write Permission for the 2nd User
        self.log.info(
            "Step 5: Put write-acp permission to object for account 2 %s",
            self.obj_name)
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name, self.obj_name, result[0], write_acp)
        assert res[0]
        self.log.info(
            "Step 5: Successfully updated the write-acp permission to object for account 2")
        # Checking the get-object-acl  permission are granted correctly
        self.log.info(
            "Step 6: Get object acl of object %s after put object acl",
            self.obj_name)
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert result[0] in str(res[1]), res[0]
        self.log.info(
            "Step 6: Get object acl resp of object %s : %s",
            self.obj_name, res)
        # Logging to second account
        self.log.info("Getting object from account 2")
        s3_acl_obj_2 = result[2]
        try:
            self.log.info(
                "Step 7: Login to account2 and perform put-object acl with private canned acl")
            s3_acl_obj_2.put_object_canned_acl(
                self.bucket_name, self.obj_name, acl=auth_read)
        except CTException as error:
            assert error_msg in error.message, error.message
        self.log.info(
            "Step 7: Done performing put-object acl with private canned acl using account 2")
        try:
            self.log.info("Get object with get-object-acl from account 2")
            s3_acl_obj_2.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert error_msg in error.message, error.message
        self.log.info(
            "put object in account1 and give write-acp to account2 and apply "
            "authenticated-read canned acl for put-object-acl and "
            "check for get-object-acl from account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5792")
    @CTFailOn(error_handler)
    def test_canned_acl_private_read_acp_3688(self):
        """
        Add canned acl private for put object in account1 and after give read-acp permissions.

        to account2 and check the operations.
        """
        self.log.info(
            "Add canned acl private for put object in account1 and after give "
            "read-acp permissions to account2 and check the operations")
        read_acp = S3_OBJ_TST["test_3688"]["read_acp"]
        private_acl = S3_OBJ_TST["test_3688"]["private_acl"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        # Creating User Account 1
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        # Create Bucket with 1st User
        self.log.info(
            "Creating Bucket and putting object into it using default user")
        self.log.info(
            "Step 2: Creating bucket and putting object%s", self.bucket_name)
        res = s3_obj_1.create_bucket(self.bucket_name)
        assert res[0], res[1]
        self.log.info("Putting object %s to existing bucket %s",
                      self.obj_name, self.bucket_name)
        res = s3_acl_obj_1.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            acl=private_acl)
        assert res[0], res[1]
        self.log.info("Step 2:  Completed creating object and bucket")
        self.log.info("Step 3: Verifying the Canned Object ACL property")
        obj_acl = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 3: Done Verifying the Canned Object ACL property")
        # Creating 2nd User Account
        # User Account Variables
        self.log.info("Creating account name %s and email_id %s",
                      self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        # Creating the 2nd user s3 Object
        self.log.info("Getting object from user 2")
        s3_acl_obj_2 = result[2]
        # Adding Read ACP Permission for the Account 2 User
        self.log.info(
            "Put write-acp permission to object for account 2 %s",
            self.obj_name)
        res = s3_acl_obj_1.add_grantee(
            self.bucket_name, self.obj_name, result[0], read_acp)
        assert res[0]
        # Validating the READ ACP permission for 2nd user
        self.log.info(
            "Step 4: Get object acl of object %s after put object acl",
            self.obj_name)
        res = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        self.log.info(
            "Step 4: Get object acl of object response is %s", res)
        assert res[0], res[1]
        assert result[0] in str(res[1]), res[0]
        assert read_acp in str(res[1]), res[0]
        # Get object ACL for 2nd Account User
        res = s3_acl_obj_2.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert result[0] in str(res[1]), res[0]
        assert read_acp in str(res[1]), res[0]
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned acl private for put object in account1 and after give "
            "read-acp permissions to account2 and check the operations")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5795")
    @CTFailOn(error_handler)
    def test_authenticated_read_acp_permissions_3689(self):
        """
        Add canned acl authenticated-read for put object in account1.

        and after give read-acp permissions to account2 and check the operations.
        """
        self.log.info(
            "Add canned acl authenticated-read for put object in account1 "
            "and after give read-acp permissions to account2 and check the operations")
        read_acp = S3_OBJ_TST["test_3689"]["read_acp"]
        auth_read = S3_OBJ_TST["test_3689"]["auth_read"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        # User Account Variables
        # Creating User Account 1
        self.log.info(
            "Step 1: Creating account 1 with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Successfully Created account 1")
        canonical_id_1 = result[0]
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        self.log.info("Step 2: Create Bucket with 1st User")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        self.log.info("Step 2: Create Bucket with 1st User")
        self.log.info(
            "Step 3: Creating Object inside the bucket with canned ACL property")
        obj_resp = s3_acl_obj_1.put_object_with_acl(
            self.bucket_name, self.obj_name, self.test_file_path, acl=auth_read)
        assert obj_resp[0]
        self.log.info(
            "Step 3: Successfully Object created with inside the bucket with canned ACL property")
        self.log.info("Step 4: Verifying the Canned Object ACL property")
        obj_acl_resp = s3_acl_obj_1.get_object_acl(
            self.bucket_name, self.obj_name)
        assert obj_acl_resp[0], obj_acl_resp[1]
        assert canonical_id_1 in str(obj_acl_resp[1]), obj_acl_resp[0]
        self.log.info(
            "Step 4: Successfully Verified the Canned Object ACL property")
        # Creating 2nd User Account User Account Variables
        self.log.info("Creating account with name %s and email_id %s",
                      self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_2 = result[0]
        # Creating the 2nd user s3 Object
        s3_acl_obj_2 = result[2]
        self.log.info("Step 5: Adding Read Permission for the 2nd User")
        self.log.info(
            "Put read-acp permission to object for account 2 %s",
            self.obj_name)
        res = s3_acl_obj_1.add_grantee(
            self.bucket_name, self.obj_name, canonical_id_2, read_acp)
        assert res[0]
        self.log.info(
            "Step 5: Successfully added Read Permission for the 2nd User")
        # Validating the READ ACP permission for 2nd user
        self.log.info(
            "Step 5: Get object acl of object %s after put object acl",
            self.obj_name)
        res = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        self.log.info("ACP Property : %s", res)
        assert res[0], res[1]
        assert canonical_id_2 in str(res[1]), res[0]
        assert read_acp in str(res[1]), res[0]
        self.log.info("Step 6: Get object ACL for 2nd User")
        try:
            get_acl_res = s3_acl_obj_2.get_object_acl(
                self.bucket_name, self.obj_name)
            self.log.info(
                "Step 6: Get ACL response for Account 2 %s", get_acl_res)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned acl authenticated-read for put object in account1"
            "and after give read-acp permissions to account2 and check the operations")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5789")
    @CTFailOn(error_handler)
    def test_overwrite_private_canned_acl_3693(self):
        """
        First add authenticated-read canned ACL to object.

        and overwrite private canned ACL to same object
        """
        self.log.info(
            "First add authenticated-read canned ACL to object and "
            "overwrite private canned ACL to same object")
        private_acl = S3_OBJ_TST["test_3693"]["private_acl"]
        auth_read = S3_OBJ_TST["test_3693"]["auth_read"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        # User Account Variables
        # Creating User Account 1
        self.log.info(
            "Step 1: Creating account 1 with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Successfully Created account 1")
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        self.log.info("Step 2: Create Bucket with 1st User")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        self.log.info("Step 2: Successfully Created Bucket with 1st User")
        self.log.info(
            "Step 3: Creating Object inside the bucket with canned ACL property")
        obj_resp = s3_acl_obj_1.put_object_with_acl(
            self.bucket_name, self.obj_name, self.test_file_path, acl=private_acl)
        assert obj_resp[0]
        self.log.info(
            "Step 3: Successfully created object with canned ACL property")
        self.log.info("Step 4: Get ACL Object ACL property ")
        obj_acl = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info("Step 4: Get ACL Object resp is %s", obj_acl)
        self.log.info(
            "Step 5 : Now override put-object-acl with canned acl authenticated-read")
        put_acl_res = s3_acl_obj_1.put_object_canned_acl(
            self.bucket_name, self.obj_name, auth_read)
        assert put_acl_res[0]
        self.log.info(
            "Step 5 : Done overriding put-object-acl with canned acl authenticated-read")
        # Creating 2nd User Account and setting User Account Variables
        self.log.info("Creating account name %s and email_id %s",
                      self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        # Creating the 2nd user s3 Object
        self.log.info("Getting object from user 2")
        s3_acl_obj_2 = result[2]
        try:
            self.log.info("Step 6: Getting the Object from user second")
            s3_acl_obj_2.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info("Step 6: Object from should return ACCESSIONED")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "First add private canned ACL to object "
            "and after that overwrite authenticated-read canned ACL to same object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5788")
    @CTFailOn(error_handler)
    def test_overwrite_authenticated_read_canned_acl_3692(self):
        """
        First add private canned ACL to object.

        and after that overwrite authenticated-read canned ACL to same object.
        """
        self.log.info(
            "First add private canned ACL to object "
            "and after that overwrite authenticated-read canned ACL to same object")
        auth_read = S3_OBJ_TST["test_3692"]["auth_read"]
        private_acl = S3_OBJ_TST["test_3692"]["private_acl"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        # Creating User Account 1
        # User Account Variables
        # Creating User Account 1
        self.log.info(
            "Step 1: Creating account 1 with name %s and email_id %s",
            self.account_name_1,
            self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Completed Creating account 1")
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        self.log.info("Step 2: Create Bucket with 1st User")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        self.log.info("Step 2: Successfully Created Bucket with 1st User")
        self.log.info(
            "Step 3: Creating Object inside the bucket with canned ACL property")
        obj_resp = s3_acl_obj_1.put_object_with_acl(
            self.bucket_name, self.obj_name, self.test_file_path, acl=auth_read)
        assert obj_resp[0]
        self.log.info(
            "Step 3: Successfully created object with canned ACL property")
        self.log.info("Step 4: Get ACL Object ACL property ")
        obj_acl = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info("Step 4: Get ACL Object resp is %s", obj_acl)
        self.log.info(
            "Step 5: Now apply put-object-acl with canned acl authenticated-read")
        put_acl_res = s3_acl_obj_1.put_object_canned_acl(
            self.bucket_name, self.obj_name, acl=private_acl)
        assert put_acl_res[0]
        self.log.info(
            "Step 5: Successfully applied put-object-acl with canned acl authenticated-read")
        # Creating 2nd User Account and set User Account Variables
        self.log.info("Creating account name %s and email_id %s",
                      self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        # Creating the 2nd user s3 Object
        s3_acl_obj_2 = result[2]
        self.log.info("Step 6: Getting object ACL from user 2")
        try:
            s3_acl_obj_2.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("Step 6: Done getting object ACL from user 2")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "First add private canned ACL to object "
            "and after that overwirte authenticated-read canned ACL to same object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5745")
    @CTFailOn(error_handler)
    def test_bucket_owner_read_canned_acl_3694(self):
        """
        Verify bucket-owner-read canned ACL when object does not belong to the bucket owner.

        and check for the results
        """
        self.log.info(
            "Verify bucket-owner-read canned ACL when object does not "
            "belong to the bucket owner.and check for the results")
        can_object_acl = S3_OBJ_TST["test_3694"]["can_object_acl"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        # Creating User Account 1
        # User Account Variables
        # Creating User Account 1
        self.log.info(
            "Step 1: Creating account 1 with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        # User Account Variables
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        can_id_usr_1 = result[0]
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        self.log.info(
            "Step 2: Creating account 2 with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        can_id_usr_2 = result[0]
        self.log.info("Step 2: Successfully Created account 2")
        s3obj_user2 = result[2]
        self.log.info("Step 3: Create Bucket with 1st User")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        self.log.info("Step 3: Successfully Created bucket")
        self.log.info("Step 4: Set the Permission for the existing bucket")
        resp = s3_acl_obj_1.put_bucket_acl(
            self.bucket_name, grant_full_control="{}{}".format(
                S3_OBJ_TST["test_3694"]["id_str"], can_id_usr_1))
        assert resp[0]
        resp = s3_acl_obj_1.put_bucket_acl(
            self.bucket_name, grant_write="{}{}".format(
                S3_OBJ_TST["test_3694"]["id_str"], can_id_usr_2))
        assert resp[0]
        self.log.info(
            "Step 4: Successfully updated the permissions for existing bucket")
        # Check bucket ACL permission
        resp = s3_acl_obj_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1][1][0]["Permission"] == S3_OBJ_TST["test_3694"]["write_acp"], resp[1]
        self.log.info(
            "Step 5: Put object in bucket from Account2 and "
            "specify the object acl with bucket-owner-read")
        put_acl_res = s3obj_user2.put_object_with_acl(
            self.bucket_name, self.obj_name, self.test_file_path, acl=can_object_acl)
        assert put_acl_res[1]
        self.log.info(
            "Step 5: Updated the following permission of object acl with bucket-owner-read")
        self.log.info(
            "Step 6: Get object acl of object %s after put object acl",
            self.obj_name)
        res = s3obj_user2.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert can_id_usr_1 in str(res[1]), res[0]
        self.log.info(
            "Step 6: Successfully updated the acl of object %s after put object acl",
            self.obj_name)
        # Verifying the object property created by the 2nd Account from account
        # 1
        self.log.info(
            "Step 7 :Get object acl of object %s after put object acl",
            self.obj_name)
        res = s3obj_user2.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info(
            "Step 7 :Verified the object property created by the 2nd Account from account")
        self.log.info("GET Object in the bucket using the Account 1")
        try:
            get_usr_obj = s3_acl_obj_1.get_object_acl(
                self.bucket_name, self.obj_name)
            assert not get_usr_obj[0]
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        s3_acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(can_id_usr_1))
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Verify bucket-owner-read canned ACL when object does not "
            "belong to the bucket owner.and check for the results")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5746")
    @CTFailOn(error_handler)
    def test_bucket_owner_full_control_3695(self):
        """
        put-object from account2 with the canned acl bucket-owner-full-control.

        from account1 where account2 has write permissions
        """
        self.log.info(
            "put-object from account2 with the canned acl bucket-owner-full-control "
            "from account1 where account2 has write permissions")
        can_object_acl = S3_OBJ_TST["test_3695"]["can_object_acl"]
        write_acp = S3_OBJ_TST["test_3695"]["write_acp"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        # Creating User Account 1
        # User Account Variables
        # Creating User Account 1
        self.log.info(
            "Step 1: Creating account 1 with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        # User Account Variables

        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        can_id_usr_1 = result[0]
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        # creating account 2
        self.log.info(
            "Step 2: Creating account 2 with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        can_id_usr_2 = result[0]
        self.log.info("Step 2: Successfully Created account 2")
        s3obj_user2 = result[2]
        self.log.info("Step 3:Create Bucket with 1st User")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        self.log.info("Step 3: Successfully Created Bucket with 1st User")
        self.log.info(
            "Step 4: Set the Permission for the existing bucket with grant full controll to user 1")
        resp = s3_acl_obj_1.put_bucket_acl(
            self.bucket_name, grant_full_control="{}{}".format(
                S3_OBJ_TST["test_3695"]["id_str"], can_id_usr_1))
        assert resp[0]
        self.log.info(
            "Step 4: Successfully Updated the the Permission for the existing bucket for user 1")
        self.log.info(
            "Step 5: Update the the Permission for the existing bucket for user 2 with grant write")
        resp = s3_acl_obj_1.put_bucket_acl(
            self.bucket_name, grant_write="{}{}".format(
                S3_OBJ_TST["test_3695"]["id_str"], can_id_usr_2))
        assert resp[1]
        self.log.info(
            "Step 5: Successfully Updated the acl for the existing bucket "
            "for user 2 with grant write")
        self.log.info("Step 6: Check bucket ACL permission")
        resp = s3_acl_obj_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1][1][0]["Permission"] == write_acp, resp[1]
        self.log.info("Step 6: bucket ACL permission resp is %s", resp)
        # Put object in bucket from Account2 and specify the object acl with
        # bucket-owner-read
        self.log.info(
            "Step 7 : Putting object %s to existing bucket %s by account 2 ",
            self.obj_name, self.bucket_name)
        put_acl_res = s3obj_user2.put_object_with_acl(
            self.bucket_name, self.obj_name, self.test_file_path, acl=can_object_acl)
        assert put_acl_res[0]
        self.log.info(
            "Step 7 : Successfully object uploaded to existing bucket")
        self.log.info(
            "Step 8 : Get object acl of object %s after put object acl using account 1",
            self.obj_name)
        res = s3obj_user2.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert can_id_usr_1 in str(res[1]), res[1]
        self.log.info(
            "Step 8 : Get object acl of object response using account using account 2 is %s",
            res)
        # Verifying the object property created by the 2nd Account from account
        self.log.info(
            "Get object acl of object %s after put object acl", self.obj_name)
        try:
            s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        s3_acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(can_id_usr_1))
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "put-object from account2 with the canned acl"
            "bucket-owner-full-control from account1 where account2 has write permissions")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5820")
    @CTFailOn(error_handler)
    def test_read_acl_permission_3504(self):
        """Add canned ACL bucket-owner-full-control along with READ ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with READ ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        bucket_permission = S3_OBJ_TST["test_3504"]["can_object_acl"]
        emailaddress = S3_OBJ_TST["s3_object"]["emailaddr"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1 : Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        s3_test_obj = result[1]
        s3_acl_obj_1 = result[2]
        resp = s3_test_obj.create_bucket(self.bucket_name)
        self.log.info("Step 2: Bucket was created")
        self.log.info(
            "Step 3: Put object with permission bucket-owner-full-control")
        assert resp[0], resp[1]
        try:
            s3_acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key,
                self.test_file_path,
                acl=bucket_permission,
                grant_read=emailaddress.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Putting object with acl and bucket permission uploaded successfully")
        resp = s3_test_obj.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with READ ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5813")
    @CTFailOn(error_handler)
    def test_canned_read_acl_permission_3509(self):
        """Add canned ACL bucket-owner-read along with READ ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-read along with READ ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        bucket_permission = S3_OBJ_TST["test_3509"]["can_object_acl"]
        emailaddress = S3_OBJ_TST["s3_object"]["emailaddr"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Successfully created the account")
        self.log.info(
            "Step 2 :Creating bucket using %s account credentials",
            self.account_name_1)
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        resp = s3_obj_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Successfully created the bucket")
        self.log.info("Step 3: Putting object with acl")
        try:
            s3_acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key,
                self.test_file_path,
                acl=bucket_permission,
                grant_read=emailaddress.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info("Step 3: Done putting object with acl and grants")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL bucket-owner-read along with READ ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5850")
    @CTFailOn(error_handler)
    def test_canned_private_read_acl_3543(self):
        """Add canned ACL "private" along with "READ" ACL grant permission."""
        self.log.info(
            "Add canned ACL private along with READ ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        bucket_permission = S3_OBJ_TST["test_3543"]["private_acp"]
        emailaddress = S3_OBJ_TST["s3_object"]["emailaddr"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Completed creating account")
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        resp = s3_obj_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Successfully Created bucket using account credentials")
        self.log.info("Step 3: Putting object with invalid acl permission")
        try:
            s3_acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key,
                self.test_file_path,
                acl=bucket_permission,
                grant_read=emailaddress.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Completed uploading object with invalid permissions")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL private along with READ ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5851")
    @CTFailOn(error_handler)
    def test_private_full_control_3544(self):
        """Add canned ACL "private" along with "FULL_CONTROL" ACL grant permission."""
        self.log.info(
            "Add canned ACL private along with FULL_CONTROL ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        bucket_permission = S3_OBJ_TST["test_3544"]["private_acp"]
        emailaddress = S3_OBJ_TST["s3_object"]["emailaddr"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Completed creating account")
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        resp = s3_obj_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Successfully Created bucket using account credentials")
        self.log.info("Step 3: Putting object with invalid acl permission")
        try:
            s3_acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key,
                self.test_file_path,
                acl=bucket_permission,
                grant_full_control=emailaddress.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Completed uploading object with invalid permissions")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL private along with FULL_CONTROL ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5847")
    @CTFailOn(error_handler)
    def test_public_read_acp_permission_3546(self):
        """Add canned ACL "public_read" along with "READ_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL public_read along with READ_ACP ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        bucket_permission = S3_OBJ_TST["test_3546"]["private_acp"]
        emailaddress = S3_OBJ_TST["s3_object"]["emailaddr"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Completed creating account")
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        resp = s3_obj_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Successfully Created bucket using account credentials")
        self.log.info("Step 3: Putting object with acl")
        try:
            s3_acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key,
                self.test_file_path,
                acl=bucket_permission,
                grant_read_acp=emailaddress.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Completed uploading object with invalid request permissions")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL public_read along with READ_ACP ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5845")
    @CTFailOn(error_handler)
    def test_public_read_write_acp_3547(self):
        """Add canned ACL "public_read" along with "WRITE_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL public_read along with WRITE_ACP ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        bucket_permission = S3_OBJ_TST["test_3547"]["private_acp"]
        emailaddress = S3_OBJ_TST["s3_object"]["emailaddr"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Completed creating account")
        self.log.info(
            "Step 2:Creating bucket using %s account credentials",
            self.account_name_1)
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        resp = s3_obj_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Successfully Created bucket using account credentials")
        self.log.info("Step 3: Putting object with acl")
        try:
            s3_acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key,
                self.test_file_path,
                acl=bucket_permission,
                grant_write_acp=emailaddress.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Completed uploading object with invalid request permissions")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL public_read along with WRITE_ACP ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5843")
    @CTFailOn(error_handler)
    def test_public_read_write_acp_acl_3548(self):
        """Add canned ACL "public_read-write" along with "WRITE_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL public_read-write along with WRITE_ACP ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        bucket_permission = S3_OBJ_TST["test_3548"]["private_acp"]
        emailaddress = S3_OBJ_TST["s3_object"]["emailaddr"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Completed creating account")
        self.log.info(
            "Step 2:Creating bucket using %s account credentials",
            self.account_name_1)
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        resp = s3_obj_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 3: Putting object with acl")
        try:
            s3_acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key,
                self.test_file_path,
                acl=bucket_permission,
                grant_write_acp=emailaddress.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Completed uploading object with invalid request permissions")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL public_read-write along with WRITE_ACP ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5844")
    @CTFailOn(error_handler)
    def test_public_read_write_full_control_3549(self):
        """Add canned ACL "public_read-write" along with "FULL_CONTROL" ACL grant permission."""
        self.log.info(
            "Add canned ACL public_read-write along with FULL_CONTROL ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        bucket_permission = S3_OBJ_TST["test_3549"]["private_acp"]
        emailaddress = S3_OBJ_TST["s3_object"]["emailaddr"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Completed creating account")
        self.log.info(
            "Step 2:Creating bucket using %s account credentials",
            self.account_name_1)
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        resp = s3_obj_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 3: Putting object with acl")
        try:
            s3_acl_obj_1.put_object_with_acl(
                self.bucket_name,
                key,
                self.test_file_path,
                acl=bucket_permission,
                grant_full_control=emailaddress.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Completed uploading object with invalid request permissions")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL public_read-write along with FULL_CONTROL ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5853")
    @CTFailOn(error_handler)
    def test_authenticate_read_acl_3550(self):
        """Add canned ACL "authenticate_read" along with "READ" ACL grant permission."""
        self.log.info(
            "Add canned ACL authenticate_read along with READ ACL grant permission")
        emailaddress = S3_OBJ_TST["s3_object"]["emailaddr"]
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        resp = s3_obj_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket was created")
        self.log.info(
            "Step 3: Upload object with authenticate_read permission and grant read permission")
        try:
            s3_acl_obj_1.put_object_with_acl(
                self.bucket_name,
                S3_OBJ_TST["s3_object"]["object_name"].format(
                    self.random_num),
                self.test_file_path,
                acl=S3_OBJ_TST["test_3550"]["auth_read"],
                grant_read=emailaddress.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Upload object with error failure message %s",
            S3_OBJ_TST["s3_object"]["inval_req"])
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL authenticate_read along with READ ACL grant permissionn")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5852")
    @CTFailOn(error_handler)
    def test_authenticate_read_acp_acl_3551(self):
        """Add canned ACL "authenticate_read" along with "READ_ACP" ACL grant permission."""
        self.log.info(
            "Add canned ACL authenticate_read along with READ_ACP ACL grant permission")
        emailaddress = S3_OBJ_TST["s3_object"]["emailaddr"]
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Account was Created Successfully")
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        resp = s3_obj_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket was created")
        self.log.info(
            "Step 3: Putting object with acl authenticate_read and READ_ACP permission")
        try:
            s3_acl_obj_1.put_object_with_acl(
                self.bucket_name,
                S3_OBJ_TST["s3_object"]["object_name"].format(
                    self.random_num),
                self.test_file_path,
                acl=S3_OBJ_TST["test_3551"]["private_acp"],
                grant_read_acp=emailaddress.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Putting object with invalid account/permission raised an "
            "exception was handled with error : %s",
            S3_OBJ_TST["s3_object"]["inval_req"])
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL authenticate_read along with READ_ACP ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5800")
    @CTFailOn(error_handler)
    def test_bucket_owner_read_canned_acl_3496(self):
        """Verify bucket-owner-read canned ACL when object belongs to the bucket owner."""
        self.log.info(
            "Verify bucket-owner-read canned ACL when object belongs to the bucket owner")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info("Step 1: Creating bucket")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 1: Successfully bucket was created")
        self.log.info("Step 2: Putting object with acl permission")
        resp = self.s3_acl_obj.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            acl=S3_OBJ_TST["test_3496"]["bucket_permission"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Object was successfully uploaded with bucket-owner-read permission")
        self.log.info("Step 3: Getting the object acl")
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert S3_OBJ_TST["s3_object"]["full_ctrl"] in str(
            res[1]), res[0]
        self.log.info("Step 3: Object was uploaded with ACL permission")
        self.log.info(
            "Verify bucket-owner-read canned ACL when object belongs to the bucket owner")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5802")
    @CTFailOn(error_handler)
    def test_bucket_owner_full_control_acl_3497(self):
        """Verify bucket-owner-full-control canned ACL when object belongs to the bucket owner."""
        self.log.info(
            "Verify bucket-owner-full-control canned ACL when object belongs to the bucket owner")

        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info("Step 1: Creating bucket")
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 1: Successfully bucket was created")
        self.log.info("Step 2: Putting object with acl permission")
        resp = self.s3_acl_obj.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            acl=S3_OBJ_TST["test_3496"]["bucket_permission"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Object was successfully uploaded with acl permission")
        self.log.info("Step 3: Getting the object acl")
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert S3_OBJ_TST["s3_object"]["full_ctrl"] in str(
            res[1]), res[0]
        self.log.info("Step 3: Object response was verified")
        self.log.info(
            "Verify bucket-owner-full-control canned ACL when object belongs to the bucket owner")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5799")
    @CTFailOn(error_handler)
    def test_bucket_owner_read_canned_3498(self):
        """Verify bucket-owner-read canned ACL when object does not belong to the bucket owner."""
        self.log.info(
            "Verify bucket-owner-read canned ACL when object does not belong to the bucket owner")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        account_name_list = []
        self.log.info("step 1: Creating User Account 1 and 2")

        account_name_list.append(self.account_name_1)
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result[0]
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_user_2 = result[0]
        s3obj_user2 = result[2]
        self.log.info("Step 1: Done creating account 1 and 2")
        self.log.info("Step 2 : Creating Bucket")
        resp = s3_obj_1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2 : Bucket was created")
        self.log.info("Step 3 : Put bucket with grant write permission")
        res = s3_acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_write="{}{}".format(
                S3_OBJ_TST["test_3498"]["id_str"],
                canonical_id_user_2))
        assert res[0], res[1]
        self.log.info(
            "Step 2: Successfully permission were given to the object")
        self.log.info("Step 3: Check bucket ACL permission")
        resp = s3_acl_obj_1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1][1][0]["Permission"] == S3_OBJ_TST["test_3498"]["write_assert"], resp[1]
        self.log.info("Step 3: Bucket ACL verified")
        self.log.info(
            "Step 4: Put Object with ACL permission and Verify it")
        resp = s3obj_user2.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            acl=S3_OBJ_TST["test_3498"]["bucket_read"])
        assert resp[0], resp[1]
        res = s3obj_user2.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert res[1]["Grants"][1]["Permission"] == \
            S3_OBJ_TST["test_3498"]["read_assert"], res[1]
        try:
            s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        try:
            s3_acl_obj_1.put_object_with_acl(
                self.bucket_name,
                self.obj_name,
                self.test_file_path,
                acl=S3_OBJ_TST["test_3498"]["auth_read"])
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Put Object ACL operation should fail with exception and"
            "error message was verified")
        s3_acl_obj_1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_1))
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Verify bucket-owner-read canned ACL when object does not belong to the bucket owner")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5801")
    @CTFailOn(error_handler)
    def test_bucket_owner_full_control_3499(self):
        """
        Verify bucket-owner-full-control canned ACL.

        when object does not belong to the bucket owner.
        """

        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info("Step 1: Creating User Account 1 and 2")

        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        canonical_id_user_1 = result[0]
        s3obj_user1 = result[1]
        s3acl_user1 = result[2]
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_user_2 = result[0]
        s3obj_user2 = result[2]
        self.log.info("Step 1: Completed Creating User Accounts 1 and 2")
        self.log.info("Step 2: Creating Bucket")
        resp = s3obj_user1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        res = s3acl_user1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_write="{}{}".format(
                S3_OBJ_TST["test_3499"]["id_str"],
                canonical_id_user_2))
        assert res[0], res[1]
        self.log.info(
            "Step 2: Bucket was successfully created by adding grantee 2")
        self.log.info("Step 3: Check bucket ACL permission")
        resp = s3acl_user1.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1][1][0]["Permission"] == S3_OBJ_TST["test_3499"]["write_assert"], resp[0]
        self.log.info("Step 3: Bucket permission was verified")
        self.log.info(
            "Step 4: Put object with bucket full control permission")
        resp = s3obj_user2.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            acl=S3_OBJ_TST["test_3499"]["bucket_full_control"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 4: Object with bucket full control permission uploaded successfully")
        self.log.info(
            "Step 5: Verify the object ACL permission using account 1 and 2")
        res = s3obj_user2.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        assert res[1]["Grants"][1]["Permission"] == \
            S3_OBJ_TST["s3_object"]["full_ctrl"], res[1]
        res = s3acl_user1.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info(
            "Step 5: Object ACL was verified using account 1 and 2")
        try:
            s3acl_user1.put_object_with_acl(
                self.bucket_name,
                self.obj_name,
                self.test_file_path,
                acl=S3_OBJ_TST["test_3499"]["auth_read"])
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        s3acl_user1.put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_full_control="id={}".format(canonical_id_user_1))
        resp = s3obj_user1.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Verify bucket-owner-full-control "
            "canned ACL when object does not belong to the bucket owner")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5805")
    @CTFailOn(error_handler)
    def test_bucket_owner_read_acl_full_control_3502(self):
        """
        First add bucket-owner-read canned ACL to object.

        and after that overwrite bucket-owner-full-control canned ACL to same object
        :avocado: tags=object_acl
        """
        self.log.info(
            "First add bucket-owner-read canned ACL to object and after that overwrite"
            "bucket-owner-full-control canned ACL to same object")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info("Step 1: Creating User Account 1")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3obj_user = result[1]
        s3acl_user = result[2]
        self.log.info("Step 1: Completed Creating User Accounts 1")
        self.log.info("Step 2: Create Bucket")
        resp = s3obj_user.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 3: Bucket was created")
        self.log.info("Step 4: Upload object")
        resp = s3acl_user.put_object_with_acl(
            self.bucket_name,
            key,
            self.test_file_path,
            acl=S3_OBJ_TST["test_3502"]["acl_bucket_read"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 4: Object was uploaded with acl permission")
        self.log.info("Step 5: Get object ACL")
        resp = s3acl_user.get_object_acl(self.bucket_name, key)
        assert resp[0], resp[1]
        self.log.info("Step 5: Get object ACL resp is verified")
        self.log.info(
            "Step 6:Overwrite canned acl bucket-owner-full-control")
        resp = s3acl_user.put_object_canned_acl(
            self.bucket_name, key, acl=S3_OBJ_TST["test_3502"]["bucket_full_control"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 6: Successfully Overwrite canned acl bucket-owner-full-control")
        self.log.info("Step 7: Get object ACL after overwrite")
        resp = s3acl_user.get_object_acl(self.bucket_name, key)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == \
            S3_OBJ_TST["s3_object"]["full_ctrl"], resp[1]
        self.log.info("Step 7: Get object ACL response is verified")
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "First add bucket-owner-read canned ACL to object and after that overwrite"
            "bucket-owner-full-control canned ACL to same object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5806")
    @CTFailOn(error_handler)
    def test_bucket_owner_full_control_read_canned_3503(self):
        """
        First add bucket-owner-full-control canned ACL to object and overwrite.

        bucket-owner-read canned ACL to same object
        """
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info("Step 1: Creating User Account 1")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1,
            self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3obj_user = result[1]
        s3acl_user = result[2]
        self.log.info("Step 1: Completed Creating User Accounts 1")
        self.log.info("Step 2: Creating Bucket")
        resp = s3obj_user.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket was created")
        self.log.info(
            "Step 2: Upload object with canned ACL bucket-owner-full-control")
        resp = s3acl_user.put_object_with_acl(
            self.bucket_name,
            key,
            self.test_file_path,
            acl=S3_OBJ_TST["test_3503"]["bucket_full_control"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Object was uploaded with acl permission")
        self.log.info("Step 3: Get object ACL")
        resp = s3acl_user.get_object_acl(self.bucket_name, key)
        assert resp[0], resp[1]
        self.log.info("Step 3: Get object ACL response is verified")
        self.log.info("Step 4: Put object and get ACL ")
        resp = s3acl_user.put_object_canned_acl(
            self.bucket_name, key, acl=S3_OBJ_TST["test_3503"]["acl_bucket_read"])
        assert resp[0], resp[1]
        resp = s3acl_user.get_object_acl(self.bucket_name, key)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == \
            S3_OBJ_TST["s3_object"]["full_ctrl"], resp[1]
        self.log.info(
            "Step 4: Put object was successful and get object ACL response was verified")
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "First add bucket-owner-full-control canned ACL to object and overwrite "
            "bucket-owner-read canned ACL to same object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5817")
    @CTFailOn(error_handler)
    def test_full_control_write_acl_3505(self):
        """Add canned ACL bucket-owner-full-control along with WRITE ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with WRITE ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Step 1: Account was created")
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info(
            "Step 2:Creating bucket using %s account credentials",
            self.account_name_1)
        resp = s3obj_user.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2:Bucket was created successfully")
        put_res = s3obj_user.put_object(
            self.bucket_name, key, self.test_file_path)
        assert put_res[0]
        self.log.info("Step 3: Putting object with acl")
        emailid = S3_OBJ_TST["s3_object"]["emailid_1"]
        try:
            acl_obj.put_object_canned_acl(
                self.bucket_name,
                key,
                acl=S3_OBJ_TST["test_3505"]["bucket_full_control"],
                grant_write=emailid.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Putting object with acl was handled with error message :%s",
            S3_OBJ_TST["s3_object"]["inval_req"])
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with WRITE ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5818")
    @CTFailOn(error_handler)
    def test_full_control_read_acp_acl_3506(self):
        """Add canned ACL bucket-owner-full-control along with READ_ACP ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with READ_ACP ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info("Step 1: Account was created successfully")
        self.log.info(
            "Step 2:Creating bucket using %s account credentials",
            self.account_name_1)
        resp = s3obj_user.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket was successfully created")
        self.log.info(
            "Step 3: Putting object with acl and grant permission")
        emailid = S3_OBJ_TST["s3_object"]["emailaddr"]
        try:
            acl_obj.put_object_with_acl(
                self.bucket_name,
                key,
                self.test_file_path,
                acl=S3_OBJ_TST["test_3506"]["bucket_full_control"],
                grant_read_acp=emailid.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Putting object with acl was handled with error message :%s",
            S3_OBJ_TST["s3_object"]["inval_req"])
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with READ_ACP ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5816")
    @CTFailOn(error_handler)
    def test_bucket_owner_full_control_write_acp_3507(self):
        """Add canned ACL bucket-owner-full-control along with WRITE_ACP ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with WRITE_ACP ACL grant permission")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info("Step 1: Account was created successfully")
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        resp = s3obj_user.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket was created successfully")
        self.log.info("Step 3: Putting object with acl permission")
        emailid = S3_OBJ_TST["s3_object"]["emailaddr"]
        try:
            acl_obj.put_object_with_acl(
                self.bucket_name,
                S3_OBJ_TST["s3_object"]["object_name"].format(
                    self.random_num),
                self.test_file_path,
                acl=S3_OBJ_TST["test_3507"]["bucket_full_control"],
                grant_write_acp=emailid.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Putting object with acl was handled with error message :%s",
            S3_OBJ_TST["s3_object"]["inval_req"])
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with WRITE_ACP ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5822")
    @CTFailOn(error_handler)
    def test_bucket_owner_full_control_acl_3508(self):
        """Add canned ACL bucket-owner-full-control along with FULL_CONTROL ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with FULL_CONTROL ACL grant permission")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info("Step 1: Successfully account was created")
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        resp = s3obj_user.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket was created")
        self.log.info(
            "Step 3: Putting object with acl and grant permission")
        emailid = S3_OBJ_TST["s3_object"]["emailaddr"]
        try:
            acl_obj.put_object_with_acl(
                self.bucket_name,
                S3_OBJ_TST["s3_object"]["object_name"].format(
                    self.random_num),
                self.test_file_path,
                acl=S3_OBJ_TST["test_3508"]["bucket_full_control"],
                grant_full_control=emailid.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Object was uploaded with invalid permission was handled with error message:%s",
            S3_OBJ_TST["s3_object"]["inval_req"])
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL bucket-owner-full-control along with FULL_CONTROL ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5809")
    @CTFailOn(error_handler)
    def test_bucket_owner_read_write_acl_permission_3510(self):
        """Add canned ACL bucket-owner-read along with WRITE ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-read along with WRITE ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info("Step 1: Account was created successfully")
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        resp = s3obj_user.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket was created")
        put_res = s3obj_user.put_object(
            self.bucket_name, key, self.test_file_path)
        assert put_res[0]
        self.log.info("Step 3: Putting object with canned acl")
        emailid = S3_OBJ_TST["s3_object"]["emailaddr"]
        try:
            acl_obj.put_object_canned_acl(
                self.bucket_name,
                key,
                acl=S3_OBJ_TST["test_3510"]["bucket_full_control"],
                grant_write=emailid.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Putting object with invalid permission was handled with error message : %s",
            S3_OBJ_TST["s3_object"]["inval_req"])
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL bucket-owner-read along with WRITE ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5811")
    @CTFailOn(error_handler)
    def test_bucket_owner_read_acp_acl_3511(self):
        """Add canned ACL bucket-owner-read along with READ_ACP ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-read along with READ_ACP ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info("Step 1: Account was created successfully")
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        resp = s3obj_user.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket was created")
        self.log.info(
            "Step 3: Putting object with acl and grant permission")
        emailid = S3_OBJ_TST["s3_object"]["emailaddr"]
        try:
            acl_obj.put_object_with_acl(
                self.bucket_name,
                key,
                self.test_file_path,
                acl=S3_OBJ_TST["test_3511"]["bucket_full_control"],
                grant_read_acp=emailid.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Putting object with invalid permission was handled with error message : %s",
            S3_OBJ_TST["s3_object"]["inval_req"])
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL bucket-owner-read along with READ_ACP ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5808")
    @CTFailOn(error_handler)
    def test_bucket_owner_read_write_acp_acl_3512(self):
        """Add canned ACL bucket-owner-read along with WRITE_ACP ACL grant permission."""
        self.log.info(
            "Add canned ACL bucket-owner-read along with WRITE_ACP ACL grant permission")
        key = S3_OBJ_TST["s3_object"]["object_name"].format(
            self.random_num)
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info("Step 1: Account was created successfully")
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        resp = s3obj_user.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket was created")
        self.log.info(
            "Step 3: Putting object with acl and grant permission")
        emailid = S3_OBJ_TST["s3_object"]["emailaddr"]
        try:
            acl_obj.put_object_with_acl(
                self.bucket_name,
                key,
                self.test_file_path,
                acl=S3_OBJ_TST["test_3512"]["bucket_full_control"],
                grant_write_acp=emailid.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Putting object with invalid permission was handled with error message : %s",
            S3_OBJ_TST["s3_object"]["inval_req"])
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL bucket-owner-read along with WRITE_ACP ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5815")
    @CTFailOn(error_handler)
    def test_bucket_owner_read_full_control_acl_3513(self):
        """
        Add canned ACL bucket-owner-read along with FULL_CONTROL ACL grant permission.
        """
        self.log.info(
            "Add canned ACL bucket-owner-read along with FULL_CONTROL ACL grant permission")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info("Step 1: Account was created successfully")
        self.log.info(
            "Step 2: Creating bucket using %s account credentials",
            self.account_name_1)
        resp = s3obj_user.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Bucket was created")
        self.log.info(
            "Step 3: Putting object with acl permission and grant permission")
        emailid = S3_OBJ_TST["s3_object"]["emailaddr"]
        try:
            acl_obj.put_object_with_acl(
                self.bucket_name,
                S3_OBJ_TST["s3_object"]["object_name"].format(
                    self.random_num),
                self.test_file_path,
                acl=S3_OBJ_TST["test_3513"]["bucket_full_control"],
                grant_full_control=emailid.format(self.email_id_1))
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 3: Putting object with invalid permission was handled with error message : %s",
            S3_OBJ_TST["s3_object"]["inval_req"])
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL bucket-owner-read along with FULL_CONTROL ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5861")
    @CTFailOn(error_handler)
    def test_private_acl_full_control_3552(self):
        """
        Add canned ACL "private" as a request header along with "FULL_CONTROL" ACL grant permission.

        as request body
        """
        self.log.info(
            "Add canned ACL private as a request header along with "
            "FULL_CONTROL ACL grant permission as request body")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        acl_obj = result[2]
        s3obj_user = result[1]
        resp = s3obj_user.create_bucket(bucket_name=self.bucket_name)
        assert resp[0], resp[1]
        resp = s3obj_user.put_object(
            self.bucket_name, self.obj_name, self.test_file_path)
        assert resp[0], resp[1]
        self.log.info("Step 1: Get object acl")
        resp = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        resp[1]["Grants"][0]["Permission"] = S3_OBJ_TST["test_3552"]["permission"]
        self.log.info("Step 2: Get object response is verified")
        self.log.info(
            "New dict to pass ACL with permission full control as request body")
        new_grant = {
            "Grantee": {
                "ID": canonical_id,
                "Type": S3_OBJ_TST["test_3552"]["can_str"],
            },
            "Permission": S3_OBJ_TST["s3_object"]["full_ctrl"],
        }
        modified_acl = copy.deepcopy(resp[1])
        modified_acl["Grants"].append(new_grant)
        self.log.info(
            "Step 3: Put object with ACP permission private and Full control:%s",
            modified_acl)
        try:
            acl_obj.put_object_acp(
                self.bucket_name, self.obj_name, modified_acl)
        except CTException as error:
            assert errmsg.S3_INVALID_ACL_ERR in error.message, error.message
        self.log.info(
            "Step 3: Exception was raised while adding invalid ACP with error message : %s",
            errmsg.S3_INVALID_ACL_ERR)
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Add canned ACL private as a request header along with"
            "FULL_CONTROL ACL grant permission as request body")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5848")
    @CTFailOn(error_handler)
    def test_private_request_body_full_contorl_header_3553(self):
        """
        Add canned ACL "private" in request body.

        along with "FULL_CONTROL" ACL grant permission in request header
        """
        self.log.info(
            "Add canned ACL private as a request header along "
            "with FULL_CONTROL ACL grant permission as request body")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        acl_obj = result[2]
        s3obj_user = result[1]
        resp = s3obj_user.create_bucket(bucket_name=self.bucket_name)
        assert resp[1], resp[0]
        self.log.info("Step 1: Put Object")
        resp = s3obj_user.put_object(
            self.bucket_name, self.obj_name, self.test_file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Object was uploaded to the bucket : %s", self.bucket_name)
        resp = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        new_grant = {
            "Grantee": {
                "ID": canonical_id,
                "Type": S3_OBJ_TST["test_3553"]["Type"],
                "DisplayName": self.account_name},
            "Permission": S3_OBJ_TST["test_3553"]["permission"]}
        modified_acp = copy.deepcopy(resp[1])
        modified_acp["Grants"][0] = new_grant
        self.log.info(
            "Step 2: Put ACL with private in request body and grant full control")
        emailid = S3_OBJ_TST["s3_object"]["emailaddr"].format(self.email_id)
        try:
            acl_obj.put_object_canned_acl(self.bucket_name, self.obj_name,
                                          access_control_policy=modified_acp,
                                          grant_full_control=emailid)
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 2: Put ACL with private was handled with error message : %s",
            S3_OBJ_TST["s3_object"]["inval_req"])
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info("Add canned ACL private in request body along with"
                      "FULL_CONTROL ACL grant permission in request heade")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5848")
    @CTFailOn(error_handler)
    def test_private_full_contorl_acl_permission_3554(self):
        """
        Add canned ACL "private" in request body along with "FULL_CONTROL" ACL grant permission.

        in request body
        """
        self.log.info(
            "Add canned ACL private in request body along "
            "with FULL_CONTROL ACL grant permission in request body")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email_id %s",
            self.account_name, self.email_id)
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        self.log.info("Step 1: Account was created")
        self.log.info("Step 2: Creating bucket %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert res[0], res[1]
        self.log.info("Step 2: Bucket was created")
        self.log.info(
            "Step 3: Putting object %s to existing bucket %s",
            self.obj_name, self.bucket_name)
        res = self.s3_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.test_file_path)
        assert res[0], res[1]
        self.log.info("Step 3: Object was uploaded")
        self.log.info("Step 4: Put full control and private ACL to object")
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name,
            self.obj_name,
            canonical_id,
            S3_OBJ_TST["s3_object"]["full_ctrl"])
        assert res[0], res[1]
        try:
            self.s3_acl_obj.add_grantee(
                self.bucket_name,
                self.obj_name,
                canonical_id,
                S3_OBJ_TST["test_3554"]["permission_2"])
        except CTException as error:
            assert errmsg.S3_INVALID_ACL_ERR in error.message, error.message
        self.log.info(
            "Step 4: Put full control and private ACL to object was handled with error message: %s",
            errmsg.S3_INVALID_ACL_ERR)
        self.log.info("Add canned ACL private in request body along with "
                      "FULL_CONTROL ACL grant permission in request body")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-19886")
    @CTFailOn(error_handler)
    def test_put_object_private_canned_acl_159(self):
        """Put-object-acl from cross account on the object with private canned-acl permission."""
        self.log.info(
            "put-object-acl from cross account on the object with private canned-acl permission")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info(
            "Step 1: Creating account 2 with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3obj_user2 = result[2]
        self.log.info("Step 1: Successfully created account 1 and 2")
        self.log.info("Step 2: Create Bucket with Account 1")
        buck_resp = s3obj_user.create_bucket(self.bucket_name)
        self.log.info("Create Bucket response is : %s", buck_resp)
        assert buck_resp[0], buck_resp[1]
        self.log.info("Step 2: Bucket was created successfully")
        self.log.info("Step 3: Put Object using Account 1")
        obj_resp = acl_obj.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            acl=S3_OBJ_TST["test_159"]["permission"])
        self.log.info(
            "Step 3: Put Object response with Private Canned ACL is verified successfully")
        assert obj_resp[0], obj_resp[1]
        obj_acl = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 4: Put Object into bucket create by account 1 by account 2 should fail")
        try:
            s3obj_user2.put_object_with_acl(
                self.bucket_name,
                self.obj_name,
                self.test_file_path,
                acl=S3_OBJ_TST["test_159"]["permission"])
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Put Object failure was handled with error message : %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "put-object-acl from cross account on the object with private canned-acl permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-19887")
    @CTFailOn(error_handler)
    def test_put_object_private_canned_acl_170(self):
        """Put-object-acl from cross account on the object with private canned-acl permission."""
        self.log.info(
            "put-object-acl from cross account on the object with private canned-acl permission")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info(
            "Step 1 : Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3obj_user2 = result[2]
        self.log.info("Step 1: Accounts was created successfully")
        buck_resp = s3obj_user.create_bucket(self.bucket_name)
        self.log.info(
            "Step 2: Create Bucket response is using account 1: %s", buck_resp)
        assert buck_resp[0], buck_resp[1]
        obj_resp = acl_obj.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            acl=S3_OBJ_TST["test_170"]["can_object_acl"])
        self.log.info(
            "Step 3: Put Object response with authenticated-read Canned ACL is : %s",
            obj_resp)
        assert obj_resp[0], obj_resp[1]
        obj_acl = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 3: Object was successfully uploaded with Canned ACL")
        self.log.info(
            "Step 4: Put Object into bucket created by account 1 by account 2")
        try:
            s3obj_user2.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                acl=S3_OBJ_TST["test_170"]["can_object_acl"])
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Put Object response was handled with error message : %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "put-object-acl from cross account on the object with private canned-acl permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-19888")
    @CTFailOn(error_handler)
    def test_put_object_owner_read_acl_172(self):
        """Test put-object-acl cross account on the object with bucket-owner-read canned-acl."""
        self.log.info(
            "Test put-object-acl from cross account on the object "
            "with bucket-owner-read canned-acl permission")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        can_object_acl = S3_OBJ_TST["test_172"]["can_object_acl"]
        usr2_acl = S3_OBJ_TST["s3_object"]["full_ctrl"]
        self.log.info(
            "Step 1: Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3obj_user2 = result[2]
        self.log.info("Step 1: Account were created successfully")
        self.log.info("Step 2: Create Bucket with Account 1")
        buck_resp = acl_obj.create_bucket_with_acl(
            self.bucket_name, grant_write="{}{}".format(
                S3_OBJ_TST["test_172"]["id_str"], result[0]))
        self.log.info("Bucket resp is %s", buck_resp)
        assert buck_resp[0], buck_resp[1]
        self.log.info("Step 2: Bucket was created")
        resp = acl_obj.get_bucket_acl(self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1][1][0]["Permission"] == \
            S3_OBJ_TST["test_172"]["permission_write"], resp[1]
        self.log.info(
            "Step 3: Putting object %s to existing bucket %s by account 2 ",
            self.obj_name, self.bucket_name)
        put_acl_res = s3obj_user2.put_object_with_acl(
            self.bucket_name, self.obj_name, self.test_file_path, acl=can_object_acl)
        assert put_acl_res[1]
        self.log.info(
            "Step 3: Put object ACL response is : %s", put_acl_res)
        self.log.info(
            "Step 4: Get object acl of object %s after put object acl",
            self.obj_name)
        resp = s3obj_user2.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[1]["Grants"][0]["Permission"] == usr2_acl, resp[1]
        self.log.info("Step 4: Get object acl resp was verified")
        self.log.info(
            "Step 5: Updating the current Object with same ACL property for object: %s",
            self.obj_name)
        put_acl_res = s3obj_user2.put_object_canned_acl(
            self.bucket_name, self.obj_name, acl=can_object_acl)
        assert put_acl_res[1]
        self.log.info(
            "Step 5: After updating the object ACL property was successfull")
        self.log.info(
            "Step 6: Get object acl of object %s after put object acl",
            self.obj_name)
        resp = s3obj_user2.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[1]["Grants"][0]["Permission"] == usr2_acl, resp[1]
        self.log.info("Step 6: Get object ACL resp was verified")
        self.log.info(
            "Step 6: Updating the current Object with same "
            "ACL property for object using account 1: %s", self.obj_name)
        put_acl_res = s3obj_user2.put_object_canned_acl(
            self.bucket_name, self.obj_name, acl=can_object_acl)
        assert put_acl_res[0]
        self.log.info("Step 6: ACL property was updated successfully")
        self.log.info("Step 7: Verifying the object acl using Account 1 "
                      "created by the 2nd Account from account 1")
        try:
            acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 7: Get object ACL was handled with error message : %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        # Cleanup
        resp = acl_obj.put_bucket_acl(self.bucket_name, acl="private")
        assert_utils.assert_true(resp[0], resp[1])
        acl_obj.delete_bucket(self.bucket_name, force=True)
        self.log.info("Test put-object-acl from cross account on the object"
                      "with bucket-owner-read canned-acl permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-19889")
    @CTFailOn(error_handler)
    def test_full_contorl_canned_acl_permission_175(self):
        """
        Test put-object-acl from cross account on the object with bucket-owner-full-control.

        canned-acl permission.
        """
        self.log.info(
            "Test put-object-acl from cross account on the object "
            "with bucket-owner-full-control canned-acl permission")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        can_object_acl = S3_OBJ_TST["test_175"]["can_object_acl"]
        self.log.info("Step 1 : Creating User Account 1 and 2")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        # Creating 2nd User Account and User Account Variables
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        can_id_2 = result[0]
        s3obj_user2 = result[2]
        self.log.info("Step 1 : Successfully accounts were created")
        self.log.info(
            "Step 2: Creating Bucket with Account 1 using acl permission")
        buck_resp = acl_obj.create_bucket_with_acl(
            self.bucket_name, grant_write="{}{}".format(
                S3_OBJ_TST["test_175"]["id_str"], can_id_2))
        assert buck_resp[0], buck_resp[1]
        self.log.info(
            "Step 2: Bucket was created with Bucket ACL permission")
        self.log.info(
            "Step 3: Putting object %s to existing bucket %s by account 2 ",
            self.obj_name, self.bucket_name)
        put_acl_res = s3obj_user2.put_object_with_acl(
            self.bucket_name, self.obj_name, self.test_file_path, acl=can_object_acl)
        assert put_acl_res[0]
        self.log.info("Step 3: Object was uploaded in the bucket")
        self.log.info(
            "Step 4: Get object acl of object %s after put object acl",
            self.obj_name)
        res = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 4: Get object acl resp was verified")
        self.log.info(
            "Step 5: Updating the current Object with same ACL property using Account 1")
        self.log.info(
            "Updating the current Object with same ACL property for object: %s",
            self.obj_name)
        put_acl_res = s3obj_user2.put_object_canned_acl(
            self.bucket_name, self.obj_name, acl=can_object_acl)
        assert put_acl_res[0]
        self.log.info(
            "Step 5: Get object acl of object %s after put object acl",
            self.obj_name)
        self.log.info(
            "Step 6: Verifying the object acl created by the 2nd Account from account")
        res = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 6: Object ACL was verified")
        self.log.info(
            "Step 7: Updating the current Object with same ACL property "
            "for object using account 1: %s", self.obj_name)
        put_acl_res = s3obj_user2.put_object_canned_acl(
            self.bucket_name, self.obj_name, acl=S3_OBJ_TST["test_175"]["bucket_read"])
        assert put_acl_res[0]
        time.sleep(S3_CFG["sync_delay"])
        self.log.info(
            "Step 7: Put object canned acl with bucket read permission was successfull")
        self.log.info(
            "Step 7: Get object acl of object after put object acl was verified")
        try:
            acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 7: Get Object ACL was handled with error message : %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        # Cleanup
        resp = acl_obj.put_bucket_acl(self.bucket_name, acl="private")
        assert_utils.assert_true(resp[0], resp[1])
        acl_obj.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "Test put-object-acl from cross account on the object "
            "with bucket-owner-full-control canned-acl permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-7566")
    @CTFailOn(error_handler)
    def test_public_read_get_obj_tagging_453(self):
        """
        Add public-read canned ACL to an existing object.

        and execute get-object-tagging from any other account
        """
        self.log.info(
            "STARTED : Add canned acl authenticated-read for put object in account1 "
            "and try to get object from account2")
        auth_read = S3_OBJ_TST["test_453"]["public_read"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Create tags on existing object using s3api put-object-tagging from account1")
        # Creating User Account 1
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Successfully Created account 1")
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        s3_tag_obj_1 = result[3]
        # Create Bucket with 1st User
        self.log.info("Creating Bucket with 1st Acc")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        system_utils.create_file(self.test_file_path,
                                 S3_OBJ_TST["s3_object"]["file_size"])
        self.log.info(
            "Uploading an object %s to bucket %s",
            self.obj_name, self.bucket_name)
        resp = s3_obj_1.put_object(self.bucket_name, self.obj_name,
                                   self.test_file_path)
        assert resp[0], resp[1]
        self.log.info("Setting tag to an object %s", self.obj_name)
        resp = s3_tag_obj_1.set_object_tag(
            self.bucket_name, self.obj_name, S3_OBJ_TST["test_453"]["key"],
            S3_OBJ_TST["test_453"]["value"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Done Create tags on existing object using s3api "
            "put-object-tagging from account1")
        self.log.info("Step 2: verify the object tags created")
        self.log.info("Retrieving tag of an object %s", self.obj_name)
        resp = s3_tag_obj_1.get_object_tags(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_453"]["key"] in resp[1][0]["Key"], resp[1]
        assert S3_OBJ_TST["test_453"]["value"] in resp[1][0]["Value"], resp[1]
        self.log.info("Step 2: Done verify the object tags created")
        self.log.info(
            "Step 3: Add public-read canned ACL to existing object")
        put_acl_res = s3_acl_obj_1.put_object_canned_acl(
            self.bucket_name, self.obj_name, acl=auth_read)
        assert put_acl_res[0], True
        self.log.info(
            "Step 3: Done Add public-read canned ACL to existing object")
        self.log.info(
            "Step 4: Get object-acl on above object and verify from account 1")
        obj_acl = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 4: Done Get object-acl on above object and verify from account 1")
        self.log.info("Step 5 : Switch to Account 2")
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_tag_obj_2 = result[3]
        self.log.info("Step 5 : Done Switch to Account 2")
        self.log.info(
            "Step 6: After switching to account2 perform get-object-tagging ")
        self.log.info("Retrieving tag of an object %s", self.obj_name)
        resp = s3_tag_obj_2.get_object_tags(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_453"]["key"] in resp[1][0]["Key"], resp[1]
        assert S3_OBJ_TST["test_453"]["value"] in resp[1][0]["Value"], resp[1]
        self.log.info(
            "Step 6: Done After switching to account2 perfrom get-object-tagging ")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED : Add canned acl authenticated-read for put object in account1 "
            "and try to get object from account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-7567")
    @CTFailOn(error_handler)
    def test_full_contorl_get_object_tagging_423(self):
        """
        Grant FULL_CONTROL permission to account2 and execute get-object-tagging.

        from account2 on a existing object
        """
        self.log.info(
            "STARTED : Grant FULL_CONTROL permission to account2 and "
            "execute get-object-tagging from account2 on a existing object")
        permission = S3_OBJ_TST["s3_object"]["full_ctrl"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Create tags on existing object using s3api put-object-tagging from account1")
        # Creating User Account 1
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Successfully Created account 1")
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        s3_tag_obj_1 = result[3]
        # Create Bucket with 1st User
        self.log.info("Creating Bucket with 1st Acc")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        system_utils.create_file(self.test_file_path,
                                 S3_OBJ_TST["s3_object"]["file_size"])
        self.log.info(
            "Uploading an object %s to bucket %s",
            self.obj_name, self.bucket_name)
        resp = s3_obj_1.put_object(self.bucket_name, self.obj_name,
                                   self.test_file_path)
        assert resp[0], resp[1]
        self.log.info("Setting tag to an object %s", self.obj_name)
        resp = s3_tag_obj_1.set_object_tag(
            self.bucket_name, self.obj_name, S3_OBJ_TST["test_423"]["key"],
            S3_OBJ_TST["test_423"]["value"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Done Create tags on existing object "
            "using s3api put-object-tagging from account1")
        self.log.info("Step 2: verify the object tags created")
        self.log.info("Retrieving tag of an object %s", self.obj_name)
        resp = s3_tag_obj_1.get_object_tags(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_423"]["key"] in resp[1][0]["Key"], resp[1]
        assert S3_OBJ_TST["test_423"]["value"] in resp[1][0]["Value"], resp[1]
        self.log.info("Step 2: Done verify the object tags created")
        self.log.info(
            "Step 3: Apply grant FULL_CONTROL permission to account2")
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_2 = result[0]
        s3_tag_obj_2 = result[3]
        res = s3_acl_obj_1.add_grantee(self.bucket_name, self.obj_name,
                                       canonical_id_2, permission)
        assert res[0], res[1]
        self.log.info(
            "Step 3: Done Apply grant FULL_CONTROL permission to account2")
        self.log.info(
            "Step 4: Get object-acl on above object and verify from account 1")
        obj_acl = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 4: Done Get object-acl on above object and verify from account 1")
        self.log.info("Step 5 : Switch to Account 2")
        self.log.info("Step 5 : Done in STEP 3 Switch to Account 2")
        self.log.info(
            "Step 6: After switching to account2 perform get-object-tagging ")
        self.log.info("Retrieving tag of an object %s", self.obj_name)
        resp = s3_tag_obj_2.get_object_tags(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_423"]["key"] in resp[1][0]["Key"], resp[1]
        assert S3_OBJ_TST["test_423"]["value"] in resp[1][0]["Value"], resp[1]
        self.log.info(
            "Step 6: Done After switching to account2 perfrom get-object-tagging ")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED : Grant FULL_CONTROL permission to account2 and "
            "execute get-object-tagging from account2 on a existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-7568")
    @CTFailOn(error_handler)
    def test_write_execute_get_object_tagging_421(self):
        """
        Grant WRITE permission to account2.

        and execute get-object-tagging from account2 on a existing object
        """
        self.log.info(
            "STARTED : Grant WRITE permission to account2 and "
            "execute get-object-tagging from account2 on a existing object")
        permission = S3_OBJ_TST["test_421"]["write"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Create tags on existing object using s3api put-object-tagging from account1")
        # Creating User Account 1
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Successfully Created account 1")
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        s3_tag_obj_1 = result[3]
        # Create Bucket with 1st User
        self.log.info("Creating Bucket with 1st Acc")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        system_utils.create_file(self.test_file_path,
                                 S3_OBJ_TST["s3_object"]["file_size"])
        self.log.info(
            "Uploading an object %s to bucket %s",
            self.obj_name, self.bucket_name)
        resp = s3_obj_1.put_object(self.bucket_name, self.obj_name,
                                   self.test_file_path)
        assert resp[0], resp[1]
        self.log.info("Setting tag to an object %s", self.obj_name)
        resp = s3_tag_obj_1.set_object_tag(
            self.bucket_name, self.obj_name, S3_OBJ_TST["test_421"]["key"],
            S3_OBJ_TST["test_421"]["value"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Done Create tags on existing object using "
            "s3api put-object-tagging from account1")
        self.log.info("Step 2: verify the object tags created")
        self.log.info("Retrieving tag of an object %s", self.obj_name)
        resp = s3_tag_obj_1.get_object_tags(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_421"]["key"] in resp[1][0]["Key"], resp[1]
        assert S3_OBJ_TST["test_421"]["value"] in resp[1][0]["Value"], resp[1]
        self.log.info("Step 2: Done verify the object tags created")
        self.log.info("Step 3: Apply grant WRITE permission to account2")
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_2 = result[0]
        s3_tag_obj_2 = result[3]
        res = s3_acl_obj_1.add_grantee(self.bucket_name, self.obj_name,
                                       canonical_id_2, permission)
        assert res[0], res[1]
        self.log.info(
            "Step 3: Done Apply grant WRITE permission to account2")
        self.log.info(
            "Step 4: Get object-acl on above object and verify from account 1")
        obj_acl = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 4: Done Get object-acl on above object and verify from account 1")
        self.log.info("Step 5 : Switch to Account 2")
        self.log.info("Step 5 : Done in STEP 3 Switch to Account 2")
        self.log.info(
            "Step 6: After switching to account2 perform get-object-tagging ")
        self.log.info("Retrieving tag of an object %s", self.obj_name)
        try:
            s3_tag_obj_2.get_object_tags(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 6: Done After switching to account2 perfrom get-object-tagging ")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED : Grant WRITE permission to account2 and "
            "execute get-object-tagging from account2 on a existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-7569")
    @CTFailOn(error_handler)
    def test_read_permission_get_object_tagging_419(self):
        """
        Grant READ permission to account2.

        and execute get-object-tagging from account2 on a existing object
        """
        self.log.info(
            "STARTED : Grant READ permission to account2 and "
            "execute get-object-tagging from account2 on a existing object")
        permission = S3_OBJ_TST["test_419"]["read"]
        resp = system_utils.create_file(self.test_file_path,
                                        S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Create tags on existing object using s3api put-object-tagging from account1")
        # Creating User Account 1
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        self.log.info("Successfully Created account 1")
        # Creating the new s3 Object
        s3_obj_1 = result[1]
        s3_acl_obj_1 = result[2]
        s3_tag_obj_1 = result[3]
        # Create Bucket with 1st User
        self.log.info("Creating Bucket with 1st Acc")
        buck_resp = s3_obj_1.create_bucket(self.bucket_name)
        assert buck_resp[0], buck_resp[1]
        system_utils.create_file(self.test_file_path,
                                 S3_OBJ_TST["s3_object"]["file_size"])
        self.log.info(
            "Uploading an object %s to bucket %s",
            self.obj_name, self.bucket_name)
        resp = s3_obj_1.put_object(self.bucket_name, self.obj_name,
                                   self.test_file_path)
        assert resp[0], resp[1]
        self.log.info("Setting tag to an object %s", self.obj_name)
        resp = s3_tag_obj_1.set_object_tag(
            self.bucket_name, self.obj_name, S3_OBJ_TST["test_419"]["key"],
            S3_OBJ_TST["test_419"]["value"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Done Create tags on existing object from account1")
        self.log.info("Step 2: verify the object tags created")
        self.log.info("Retrieving tag of an object %s", self.obj_name)
        resp = s3_tag_obj_1.get_object_tags(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_419"]["key"] in resp[1][0]["Key"], resp[1]
        assert S3_OBJ_TST["test_419"]["value"] in resp[1][0]["Value"], resp[1]
        self.log.info("Step 2: Done verify the object tags created")
        self.log.info("Step 3: Apply grant READ permission to account2")
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id_2 = result[0]
        s3_tag_obj_2 = result[3]
        res = s3_acl_obj_1.add_grantee(self.bucket_name, self.obj_name,
                                       canonical_id_2, permission)
        assert res[0], res[1]
        self.log.info(
            "Step 3: Done Apply grant READ permission to account2")
        self.log.info(
            "Step 4: Get object-acl on above object and verify from account 1")
        obj_acl = s3_acl_obj_1.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 4: Done Get object-acl on above object and verify from account 1")
        self.log.info("Step 5 : Switch to Account 2")
        self.log.info("Step 5 : Done in STEP 3 Switch to Account 2")
        self.log.info(
            "Step 6: After switching to account2 perform get-object-tagging ")
        self.log.info("Retrieving tag of an object %s", self.obj_name)
        resp = s3_tag_obj_2.get_object_tags(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_419"]["key"] in resp[1][0]["Key"], resp[1]
        assert S3_OBJ_TST["test_419"]["value"] in resp[1][0]["Value"], resp[1]
        self.log.info(
            "Step 6: Done After switching to account2 perfrom get-object-tagging ")
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED : Grant READ permission to account2 and "
            "execute get-object-tagging from account2 on a existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-7570")
    @CTFailOn(error_handler)
    def test_get_object_tagging_410(self):
        """Verify get-object-tagging for object owner."""
        self.log.info(
            "STARTED : Verify get-object-tagging for object owner")
        self.log.info("Step 1: Create tags on existing object")
        self.log.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.log.info("Creating a bucket %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        system_utils.create_file(self.test_file_path,
                                 S3_OBJ_TST["s3_object"]["file_size"])
        self.log.info(
            "Uploading an object %s to bucket %s",
            self.obj_name, self.bucket_name)
        resp = self.s3_obj.put_object(self.bucket_name, self.obj_name,
                                      self.test_file_path)
        assert resp[0], resp[1]
        self.log.info("Setting tag to an object %s", self.obj_name)
        resp = self.tag_obj.set_object_tag(
            self.bucket_name, self.obj_name, S3_OBJ_TST["test_410"]["key"],
            S3_OBJ_TST["test_410"]["value"])
        assert resp[0], resp[1]
        self.log.info("Step 1: Done Create tags on existing object")
        self.log.info("Step 2: verify the object tags created")
        self.log.info("Retrieving tag of an object %s", self.obj_name)
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.obj_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_410"]["key"] in resp[1][0]["Key"], resp[1]
        assert S3_OBJ_TST["test_410"]["value"] in resp[1][0]["Value"], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info("Step 2: Done verify the object tags created")
        self.log.info("ENDED : Verify get-object-tagging for object owner")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-7572")
    def test_put_object_acl_public_read_write_169(self):
        """Put-object-acl from cross account on obj with public-read-write canned-acl permission."""
        self.log.info(
            "STARTED:put-object-acl from cross account on the object with "
            "public-read-write canned-acl permission")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info(
            "Step 1 : Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3obj_user2 = result[2]
        self.log.info("Step 1: Accounts was created successfully")
        buck_resp = s3obj_user.create_bucket(self.bucket_name)
        self.log.info(
            "Step 2: Create Bucket response is using account 1: %s", buck_resp)
        assert buck_resp[0], buck_resp[1]
        obj_resp = acl_obj.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            acl=S3_OBJ_TST["test_169"]["can_object_acl"])
        self.log.info(
            "Step 3: Put Object response with public-read-write Canned ACL is : %s",
            obj_resp)
        assert obj_resp[0], obj_resp[1]
        obj_acl = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 4: Put Object into bucket created by account 1 by account 2")
        try:
            s3obj_user2.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                acl=S3_OBJ_TST["test_169"]["can_object_acl"])
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Put Object response was handled with error message : %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED:put-object-acl from cross account on the object "
            "with public-read-write canned-acl permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-7573")
    @CTFailOn(error_handler)
    def test_public_read_canned_acl_167(self):
        """put-object-acl from cross account on the obj with public-read canned-acl permission."""
        self.log.info(
            "STARTED:put-object-acl from cross account on the object "
            "with public-read canned-acl permission")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info(
            "Step 1 : Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3obj_user2 = result[2]
        self.log.info("Step 1: Accounts was created successfully")
        buck_resp = s3obj_user.create_bucket(self.bucket_name)
        self.log.info(
            "Step 2: Create Bucket response is using account 1: %s", buck_resp)
        assert buck_resp[0], buck_resp[1]
        obj_resp = acl_obj.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            acl=S3_OBJ_TST["test_167"]["can_object_acl"])
        self.log.info(
            "Step 3: Put Object response with public-read Canned ACL is : %s",
            obj_resp)
        assert obj_resp[0], obj_resp[1]
        obj_acl = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 4: Put Object into bucket created by account 1 by account 2")
        try:
            s3obj_user2.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                acl=S3_OBJ_TST["test_167"]["can_object_acl"])
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Put Object response was handled with error message : %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED:put-object-acl from cross account on the object with "
            "public-read canned-acl permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-7574")
    @CTFailOn(error_handler)
    def test_put_get_obj_acl_311(self):
        """
        put object in account1 Do not give any permissions or canned acl for account2.

        and get object acl from account2
        """
        self.log.info(
            "STARTED:put object in account1 Dont give any permissions or canned"
            " acl for account2 and get object acl from account2")
        resp = system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        acl_obj = result[2]
        s3obj_user = result[1]
        self.log.info(
            "Step 1 : Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3obj_user2 = result[2]
        self.log.info("Step 1: Accounts was created successfully")
        buck_resp = s3obj_user.create_bucket(self.bucket_name)
        self.log.info(
            "Step 2: Create Bucket response is using account 1: %s", buck_resp)
        assert buck_resp[0], buck_resp[1]
        obj_resp = s3obj_user.put_object(
            self.bucket_name,
            self.obj_name,
            self.test_file_path)
        self.log.info(
            "Step 3: Put Object response in Bucket")
        assert obj_resp[0], obj_resp[1]
        obj_acl = acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert obj_acl[0], obj_acl[1]
        self.log.info(
            "Step 4: Get Object ACL from bucket created by account 1")
        try:
            s3obj_user2.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Get object ACL response was handled with error message : %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        resp = s3obj_user.bucket_list()[1]
        if self.bucket_name in resp:
            s3obj_user.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED:put object in account1 Dont give any permissions or canned"
            " acl for account2 and get object acl from account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-7575")
    @CTFailOn(error_handler)
    def test_put_obj_read_acp_get_obj_acl_286(self):
        """
        put object in account1 and give read-acp permissions to account2.

        and get-object-acl details.
        """
        self.log.info(
            "STARTED:put object in account1 and give read-acp permissions "
            "to account2 and get-object-acl details")
        permission = S3_OBJ_TST["test_286"]["obj_acl_rdc"]
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        canonical_id = result[0]
        acl_obj_2 = result[2]
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info(
            "Step 1: Put read_acp permission to object%s", self.obj_name)
        res = self.s3_acl_obj.add_grantee(
            self.bucket_name,
            self.obj_name,
            canonical_id,
            permission)
        assert res[0], res[1]
        self.log.info("Step 2: Get object acl")
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info("Step 3: Get object acl from account 2")
        res = acl_obj_2.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info(
            "ENDED:put object in account1 and give read-acp permissions "
            "to account2 and get-object-acl details")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-7576")
    @CTFailOn(error_handler)
    def test_put_get_obj_acl_285(self):
        """put object in account1 and get-object-acl details for that object."""
        self.log.info(
            "STARTED:put object in account1 and get-object-acl details for that object")
        self.create_s3_account(
            self.account_name,
            self.email_id,
            self.s3acc_passwd)
        self.log.info(
            "Step 1: Put object%s", self.obj_name)
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        self.log.info("Step 2: Get object acl")
        res = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert res[0], res[1]
        self.log.info(
            "ENDED:put object in account1 and get-object-acl details for that object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5743")
    @CTFailOn(error_handler)
    def test_put_get_obj_acl_xml_3453(self):
        """
        put object acl in account1 and give read permissions to account2.

        and get object from account2 by using acl xml
        """
        self.log.info(
            "STARTED: put object acl in account1 and give read permissions to account2"
            " and get object from account2 by using acl xml")
        test_3453_cfg = S3_OBJ_TST["test_3453"]
        grantee_json = test_3453_cfg["new_grantee"]
        obj_permission = test_3453_cfg["grant_permission"]
        self.log.info("Step 1: Creating two accounts...")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3_acl_obj1 = result[2]
        s3_test_obj1 = result[1]
        email = S3_OBJ_TST["s3_object"]["emailaddr"].format(self.email_id_2)
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id, s3_test_obj2, s3_acl_obj2, _ = result
        self.log.info("Step 1: Created two accounts successfully")
        self.create_bucket_obj(self.bucket_name, self.obj_name, s3_test_obj1)
        self.log.info("Step 4: Creating a custom acl xml")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        grantee_json["Grantee"]["DisplayName"] = grantee_json["Grantee"]["DisplayName"].format(
            self.account_name_2)
        grantee_json["Grantee"]["ID"] = grantee_json["Grantee"]["ID"].format(
            canonical_id)
        new_grantee = json.dumps(grantee_json)
        modified_acp = copy.deepcopy(resp[1])
        modified_acp["Grants"][0] = new_grantee
        self.log.info(modified_acp)
        self.log.info("Step 4: Created a custom acl xml")
        self.log.info(
            "Step 5: Setting a %s permission to an object for second account",
            obj_permission)
        resp = s3_acl_obj1.put_object_canned_acl(
            self.bucket_name,
            self.obj_name,
            access_control_policy=modified_acp,
            grant_read=email)
        assert resp[0], resp[1]
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == obj_permission, resp[1]
        self.log.info(
            "Step 5: Set a %s permission to an object for second account",
            obj_permission)
        self.log.info("Step 6: Retrieving an object using second account")
        resp = s3_test_obj2.get_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 6: Retrieved an object using second account successfully")
        resp = s3_test_obj1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object acl in account1 and give read permissions to"
            " account2 and get object from account2 by using acl xml")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5786")
    @CTFailOn(error_handler)
    def test_put_check_invalid_canonical_id_3454(self):
        """put object acl in account1 and give invalid canonical id for account2 and check."""
        self.log.info(
            "STARTED: put object acl in account1 and "
            "give invalid canonical id for account2 and check")
        test_3454_cfg = S3_OBJ_TST["test_3454"]
        obj_permission = S3_OBJ_TST["s3_object"]["full_ctrl"]
        self.log.info("Step 1: Creating two accounts...")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3_acl_obj1 = result[2]
        s3_test_obj1 = result[1]
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id = result[0]
        self.log.info("Step 1: Created two accounts successfully")
        self.create_bucket_obj(self.bucket_name, self.obj_name, s3_test_obj1)
        can_id_len = len(canonical_id) - len(test_3454_cfg["sub_can_id"])
        new_canonical_id = f"{test_3454_cfg['sub_can_id']}{canonical_id[:can_id_len]}"
        self.log.info(
            "Step 4: Setting a %s permission to an object for second"
            " account with invalid canonical id", obj_permission)
        try:
            s3_acl_obj1.add_grantee(
                self.bucket_name,
                self.obj_name,
                new_canonical_id,
                obj_permission)
        except CTException as error:
            self.log.info(error.message)
            assert errmsg.S3_OBJ_ACL_INVALID_ARGUMENT_ERR in error.message, error.message
        self.log.info(
            "Step 4: Setting a %s permission to an object for second account"
            " with invalid canonical id failed with %s",
            obj_permission, errmsg.S3_OBJ_ACL_INVALID_ARGUMENT_ERR)
        resp = s3_test_obj1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object acl in account1 and "
            "give invalid canonical id for account2 and check")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5785")
    @CTFailOn(error_handler)
    def test_put_get_obj_control_permission_3455(self):
        """
        put object acl in account1 and give Full-control permissions to account2.

        and try to get object from account3 by using acl xml
        """
        self.log.info(
            "STARTED: put object acl in account1 and give Full-control permissions to"
            " account2 and try to get object from account3 by using acl xml")
        test_3455_cfg = S3_OBJ_TST["test_3455"]
        obj_permission = S3_OBJ_TST["s3_object"]["full_ctrl"]
        grantee_json = test_3455_cfg["new_grantee"]
        self.log.info("Step 1: Creating three accounts...")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3_acl_obj1 = result[2]
        s3_test_obj1 = result[1]
        email = S3_OBJ_TST["s3_object"]["emailaddr"].format(self.email_id_2)
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id, s3_test_obj2, s3_acl_obj2, _ = result
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_test_obj3 = result[1]
        self.log.info("Step 1: Created three accounts successfully")
        self.create_bucket_obj(self.bucket_name, self.obj_name, s3_test_obj1)
        self.log.info("Step 2: Creating a custom acl xml")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        grantee_json["Grantee"]["DisplayName"] = grantee_json["Grantee"]["DisplayName"].format(
            self.account_name_2)
        grantee_json["Grantee"]["ID"] = grantee_json["Grantee"]["ID"].format(
            canonical_id)
        new_grantee = json.dumps(grantee_json)
        modified_acp = copy.deepcopy(resp[1])
        modified_acp["Grants"][0] = new_grantee
        self.log.info(modified_acp)
        self.log.info("Step 2: Created a custom acl xml")
        self.log.info(
            "Step 3: Setting a %s permission to an object for second account",
            obj_permission)
        resp = s3_acl_obj1.put_object_canned_acl(
            self.bucket_name,
            self.obj_name,
            access_control_policy=modified_acp,
            grant_full_control=email)
        assert resp[0], resp[1]
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == obj_permission, resp[1]
        self.log.info(
            "Step 3: Set a %s permission to an object for second account",
            obj_permission)
        self.log.info("Step 4: Retrieving an object using third account")
        try:
            s3_test_obj3.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Retrieving an object using second account failed with %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        resp = s3_test_obj1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object acl in account1 and give Full-control permissions to"
            " account2 and try to get object from account3 by using acl xml")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5784")
    @CTFailOn(error_handler)
    def test_read_acp_permission_acl_xml_3456(self):
        """
        put object acl in account1 and give read-acp permissions to account2.

        and get object from account2 by using acl xml.
        """
        self.log.info(
            "STARTED: put object acl in account1 and give read-acp permissions to"
            " account2 and get object from account2 by using acl xml")
        test_3456_cfg = S3_OBJ_TST["test_3456"]
        obj_permission = test_3456_cfg["grant_permission"]
        grantee_json = test_3456_cfg["new_grantee"]
        self.log.info("Step 1: Creating two accounts...")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3_acl_obj1 = result[2]
        s3_test_obj1 = result[1]
        email = S3_OBJ_TST["s3_object"]["emailaddr"].format(self.email_id_2)
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id, s3_test_obj2, s3_acl_obj2, _ = result
        self.log.info("Step 1: Created two accounts successfully")
        self.create_bucket_obj(self.bucket_name, self.obj_name, s3_test_obj1)
        self.log.info("Step 2: Creating a custom acl xml")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        grantee_json["Grantee"]["DisplayName"] = grantee_json["Grantee"]["DisplayName"].format(
            self.account_name_2)
        grantee_json["Grantee"]["ID"] = grantee_json["Grantee"]["ID"].format(
            canonical_id)
        new_grantee = json.dumps(grantee_json)
        modified_acp = copy.deepcopy(resp[1])
        modified_acp["Grants"][0] = new_grantee
        self.log.info(modified_acp)
        self.log.info("Step 2: Created a custom acl xml")
        self.log.info(
            "Step 3: Setting a %s permission to an object for second account",
            obj_permission)
        resp = s3_acl_obj1.put_object_canned_acl(
            self.bucket_name,
            self.obj_name,
            access_control_policy=modified_acp,
            grant_read_acp=email)
        assert resp[0], resp[1]
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == obj_permission, resp[1]
        self.log.info(
            "Step 3: Set a %s permission to an object for second account",
            obj_permission)
        self.log.info("Step 4: Retrieving an object using second account")
        try:
            s3_test_obj2.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Retrieving an object using second account failed with %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        resp = s3_test_obj1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object acl in account1 and give read-acp permissions to account2"
            " and get object from account2 by using acl xml")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5782")
    @CTFailOn(error_handler)
    def test_write_acp_permission_get_acl_xml_3457(self):
        """
        put object acl in account1 and give write-acp permissions to account2.

        and get object from account2 by using acl xml
        """
        self.log.info(
            "STARTED: put object acl in account1 and give write-acp permissions to"
            " account2 and get object from account2 by using acl xml")
        test_3457_cfg = S3_OBJ_TST["test_3457"]
        obj_permission = test_3457_cfg["grant_permission"]
        grantee_json = test_3457_cfg["new_grantee"]
        self.log.info("Step 1: Creating two accounts...")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3_acl_obj1 = result[2]
        s3_test_obj1 = result[1]
        email = S3_OBJ_TST["s3_object"]["emailaddr"].format(self.email_id_2)
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id, s3_test_obj2, s3_acl_obj2, _ = result
        self.log.info("Step 1: Created two accounts successfully")
        self.create_bucket_obj(self.bucket_name, self.obj_name, s3_test_obj1)
        self.log.info("Step 2: Creating a custom acl xml")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        grantee_json["Grantee"]["DisplayName"] = grantee_json["Grantee"]["DisplayName"].format(
            self.account_name_2)
        grantee_json["Grantee"]["ID"] = grantee_json["Grantee"]["ID"].format(
            canonical_id)
        new_grantee = json.dumps(grantee_json)
        modified_acp = copy.deepcopy(resp[1])
        modified_acp["Grants"][0] = new_grantee
        self.log.info(modified_acp)
        self.log.info("Step 2: Created a custom acl xml")
        self.log.info(
            "Step 3: Setting a %s permission to an object for second account",
            obj_permission)
        resp = s3_acl_obj1.put_object_canned_acl(
            self.bucket_name,
            self.obj_name,
            access_control_policy=modified_acp,
            grant_write_acp=email)
        assert resp[0], resp[1]
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == obj_permission, resp[1]
        self.log.info(
            "Step 3: Set a %s permission to an object for second account",
            obj_permission)
        self.log.info("Step 4: Retrieving an object using second account")
        try:
            s3_test_obj2.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Retrieving an object using second account failed with %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        resp = s3_test_obj1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object acl in account1 and give write-acp permissions to account2"
            " and get object from account2 by using acl xml")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5755")
    @CTFailOn(error_handler)
    def test_write_permission_get_obj_acl_xml_3458(self):
        """
        put object acl in account1 and give write permissions to account2.

        get object from account2 by using acl xml
        """
        self.log.info(
            "STARTED: put object acl in account1 and give write permissions to"
            " account2 and get object from account2 by using acl xml")
        test_3458_cfg = S3_OBJ_TST["test_3458"]
        obj_permission = test_3458_cfg["grant_permission"]
        grantee_json = test_3458_cfg["new_grantee"]
        self.log.info("Step 1: Creating two accounts...")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3_acl_obj1 = result[2]
        s3_test_obj1 = result[1]
        email = S3_OBJ_TST["s3_object"]["emailaddr"].format(self.email_id_2)
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        canonical_id, s3_test_obj2, s3_acl_obj2, _ = result
        self.log.info("Step 1: Created two accounts successfully")
        self.create_bucket_obj(self.bucket_name, self.obj_name, s3_test_obj1)
        self.log.info("Step 2: Creating a custom acl xml")
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        grantee_json["Grantee"]["DisplayName"] = grantee_json["Grantee"]["DisplayName"].format(
            self.account_name_2)
        grantee_json["Grantee"]["ID"] = grantee_json["Grantee"]["ID"].format(
            canonical_id)
        new_grantee = json.dumps(grantee_json)
        modified_acp = copy.deepcopy(resp[1])
        modified_acp["Grants"][0] = new_grantee
        self.log.info(modified_acp)
        self.log.info("Step 2: Created a custom acl xml")
        self.log.info(
            "Step 3: Setting a %s permission to an object for second account",
            obj_permission)
        resp = s3_acl_obj1.put_object_canned_acl(
            self.bucket_name,
            self.obj_name,
            access_control_policy=modified_acp,
            grant_write=email)
        assert resp[0], resp[1]
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == obj_permission, resp[1]
        self.log.info(
            "Step 3: Set a %s permission to an object for second account",
            obj_permission)
        self.log.info("Step 4: Retrieving an object using second account")
        try:
            s3_test_obj2.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 4: Retrieving an object using second account failed with %s",
            errmsg.ACCESS_DENIED_ERR_KEY)
        resp = s3_test_obj1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object acl in account1 and give write permissions to"
            " account2 and get object from account2 by using acl xml")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-7560")
    @CTFailOn(error_handler)
    def test_full_control_permision_header_3459(self):
        """put object in acnt1 & give full control permissions to acnt2 using permission header."""
        self.log.info(
            "STARTED: put object in account1 and give full control permissions to account2 "
            "using permission header")
        obj_permission = S3_OBJ_TST["s3_object"]["full_ctrl"]
        system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        self.log.info("Step 1: Creating two accounts...")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3_acl_obj1 = result[2]
        s3_test_obj1 = result[1]
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_test_obj2 = result[1]
        s3_acl_obj2 = result[2]
        self.log.info("Step 1: Created two accounts successfully")
        self.log.info(
            "Step 2: Creating a bucket with name %s using first account",
            self.bucket_name)
        resp = s3_test_obj1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Created a bucket with name %s using first account",
            self.bucket_name)
        self.log.info(
            "Step 3: Uploading an object to bucket name with %s permission"
            " using first account", obj_permission)
        email = S3_OBJ_TST["s3_object"]["emailaddr"].format(self.email_id_2)
        resp = s3_acl_obj1.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            grant_full_control=email)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Uploaded an object to bucket name with %s permission"
            " using first account", obj_permission)
        self.log.info(
            "Step 4: Checking %s permissions are set for an object",
            obj_permission)
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == obj_permission, resp[1]
        self.log.info(
            "Step 4: Checked %s permissions are set for an object",
            obj_permission)
        self.log.info(
            "Step 5: Verifying %s permission is set for second account",
            obj_permission)
        resp = s3_test_obj2.get_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        resp = s3_acl_obj2.put_object_canned_acl(
            self.bucket_name, self.obj_name, grant_full_control=email)
        assert resp[0], resp[1]
        resp = s3_acl_obj2.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == obj_permission, resp[1]
        self.log.info(
            "Step 5: Verified that %s permission is set for second account",
            obj_permission)
        resp = s3_test_obj1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object in account1 and give full control permissions to account2 "
            "using permission header")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5754")
    @CTFailOn(error_handler)
    def test_put_obj_read_permission_permission_header_3460(self):
        """Put object in account1 and give read permissions to account2 using permission header."""
        self.log.info(
            "STARTED: put object in account1 and "
            "give read permissions to account2 using permission header")
        test_3460_cfg = S3_OBJ_TST["test_3460"]
        obj_permission = test_3460_cfg["grant_permission"]
        system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        self.log.info("Step 1: Creating two accounts...")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3_acl_obj1 = result[2]
        s3_test_obj1 = result[1]
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_test_obj2 = result[1]
        s3_acl_obj2 = result[2]
        self.log.info("Step 1: Created two accounts successfully")
        self.log.info(
            "Step 2: Creating a bucket with name %s using first account",
            self.bucket_name)
        resp = s3_test_obj1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Created a bucket with name %s using first account",
            self.bucket_name)
        self.log.info(
            "Step 3: Uploading an object to bucket name with %s permission "
            "using first account", obj_permission)
        email = S3_OBJ_TST["s3_object"]["emailaddr"].format(self.email_id_2)
        resp = s3_acl_obj1.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            grant_read=email)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Uploaded an object to bucket name with %s permission using first account",
            obj_permission)
        self.log.info(
            "Step 4: Checking %s permissions are set for an object",
            obj_permission)
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == obj_permission, resp[1]
        self.log.info(
            "Step 4: Checked %s permissions are set for an object",
            obj_permission)
        self.log.info(
            "Step 5: Verifying %s permission is set for second account",
            obj_permission)
        resp = s3_test_obj2.get_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        try:
            s3_acl_obj2.put_object_canned_acl(
                self.bucket_name, self.obj_name, grant_full_control=email)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        try:
            s3_acl_obj2.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 5: Verified that %s permission is set for second account",
            obj_permission)
        resp = s3_test_obj1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object in account1 and "
            "give read permissions to account2 using permission header")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5753")
    @CTFailOn(error_handler)
    def test_put_obj_read_acp_permission_header_3461(self):
        """Put object in account1 & give read-acp permission to account2 using permission header."""
        self.log.info(
            "STARTED: put object in account1 and give read-acp permissions "
            "to account2 using permission header")
        test_3461_cfg = S3_OBJ_TST["test_3461"]
        obj_permission = test_3461_cfg["grant_permission"]
        system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        self.log.info("Step 1: Creating two accounts...")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3_acl_obj1 = result[2]
        s3_test_obj1 = result[1]
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_test_obj2 = result[1]
        s3_acl_obj2 = result[2]
        self.log.info("Step 1: Created two accounts successfully")
        self.log.info(
            "Step 2: Creating a bucket with name %s using first account",
            self.bucket_name)
        resp = s3_test_obj1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Created a bucket with name %s using first account",
            self.bucket_name)
        self.log.info(
            "Step 3: Uploading an object to bucket name "
            "with %s permission using first account", obj_permission)
        email = S3_OBJ_TST["s3_object"]["emailaddr"].format(self.email_id_2)
        resp = s3_acl_obj1.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            grant_read_acp=email)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Uploaded an object to bucket name with %s permission "
            "using first account", obj_permission)
        self.log.info(
            "Step 4: Checking %s permissions are set for an object",
            obj_permission)
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == obj_permission, resp[1]
        self.log.info(
            "Step 4: Checked %s permissions are set for an object",
            obj_permission)
        self.log.info(
            "Step 5: Verifying %s permission is set for second account",
            obj_permission)
        try:
            s3_test_obj2.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        try:
            s3_acl_obj2.put_object_canned_acl(
                self.bucket_name, self.obj_name, grant_full_control=email)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        resp = s3_acl_obj2.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == obj_permission, resp[1]
        self.log.info(
            "Step 5: Verified that %s permission is set for second account",
            obj_permission)
        resp = s3_test_obj1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object in account1 and give read-acp permissions "
            "to account2 using permission header")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5750")
    @CTFailOn(error_handler)
    def test_write_permission_header_3462(self):
        """Put object in account1 and give write permissions to account2 using permission header."""
        self.log.info(
            "STARTED: put object in account1 and give write "
            "permissions to account2 using permission header")
        test_3462_cfg = S3_OBJ_TST["test_3462"]
        obj_permission = test_3462_cfg["grant_permission"]
        system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        self.log.info("Step 1: Creating two accounts...")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3_acl_obj1 = result[2]
        s3_test_obj1 = result[1]
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_test_obj2 = result[1]
        s3_acl_obj2 = result[2]
        self.log.info("Step 1: Created two accounts successfully")
        self.log.info(
            "Step 2: Creating a bucket with name %s using first account",
            self.bucket_name)
        resp = s3_test_obj1.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Created a bucket with name %s using first account",
            self.bucket_name)
        self.log.info(
            "Step 3: Uploading an object to bucket with %s permission "
            "using first account", obj_permission)
        email = S3_OBJ_TST["s3_object"]["emailaddr"].format(self.email_id_2)
        resp = s3_acl_obj1.put_object_with_acl(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            grant_write_acp=email)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Uploaded an object to bucket with %s "
            "permission using first account", obj_permission)
        self.log.info(
            "Step 4: Checking %s permissions are set for an object",
            obj_permission)
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == obj_permission, resp[1]
        self.log.info(
            "Step 4: Checking %s permissions are set for an object",
            obj_permission)
        self.log.info(
            "Step 5: Verifying that %s permission is set for second account",
            obj_permission)
        try:
            s3_test_obj2.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        resp = s3_acl_obj2.put_object_canned_acl(
            self.bucket_name, self.obj_name, grant_read=email)
        assert resp[0], resp[1]
        try:
            s3_acl_obj2.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info(
            "Step 5: Verified that %s permission is set for "
            "second account successfully", obj_permission)
        resp = s3_test_obj1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object in account1 and give write permissions "
            "to account2 using permission header")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5752")
    @CTFailOn(error_handler)
    def test_write_permission_header_3463(self):
        """Put object in account1 and give write permissions to account2 using permission header."""
        self.log.info(
            "STARTED: put object in account1 and give write permissions to "
            "account2 using permission header")
        test_3463_cfg = S3_OBJ_TST["test_3463"]
        obj_permission = test_3463_cfg["grant_permission"]
        self.log.info("Step 1: Creating two accounts...")
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_1, self.email_id_1)
        result = self.create_s3_account(
            self.account_name_1, self.email_id_1, self.s3acc_passwd)
        s3_acl_obj1 = result[2]
        s3_test_obj1 = result[1]
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2, self.email_id_2)
        self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        self.log.info("Step 1: Created two accounts successfully")
        self.create_bucket_obj(self.bucket_name, self.obj_name, s3_test_obj1)
        self.log.info(
            "Step 2: Setting an object permission to %s using first account",
            obj_permission)
        email = S3_OBJ_TST["s3_object"]["emailaddr"].format(self.email_id_2)
        resp = s3_acl_obj1.put_object_canned_acl(
            self.bucket_name, self.obj_name, grant_write=email)
        assert resp[0], resp[1]
        self.log.info(
            "Step 2: Set an object permission to %s using first account",
            obj_permission)
        self.log.info(
            "Step 3: Checking %s permissions are set for second account",
            obj_permission)
        resp = s3_acl_obj1.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] in obj_permission, resp[1]
        self.log.info(
            "Step 3: Checked %s permissions are set for second account",
            obj_permission)
        resp = s3_test_obj1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_test_obj1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object in account1 and give write "
            "permissions to account2 using permission header")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-7565")
    @CTFailOn(error_handler)
    def test_full_contorl_read_acl_permisisno_3541(self):
        """Add canned ACL bucket-owner-full-control along with READ ACL grant permission."""
        self.log.info(
            "STARTED:Add canned ACL bucket-owner-full-control along with READ ACL grant permission")
        test_3541_cfg = S3_OBJ_TST["test_3541"]
        self.log.info(
            "Step 1: Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_obj.create_bucket(self.bucket_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Created a bucket with name %s", self.bucket_name)
        self.log.info(
            "Step 2: Uploading an object to bucket %s with canned acl"
            " and READ ACL grant permission", self.bucket_name)
        system_utils.create_file(
            self.test_file_path,
            S3_OBJ_TST["s3_object"]["file_size"])
        try:
            self.s3_acl_obj.put_object_with_acl(
                self.bucket_name,
                self.obj_name,
                self.test_file_path,
                acl=test_3541_cfg["acl"],
                grant_read_acp=S3_OBJ_TST["s3_object"]["emailaddr"].format(
                    self.email_id_1))
        except CTException as error:
            self.log.error(error.message)
            assert S3_OBJ_TST["s3_object"]["inval_req"] in error.message, error.message
        self.log.info(
            "Step 2: Uploading an object to bucket %s with canned acl"
            " and READ ACL grant permission failed with %s",
            self.bucket_name, S3_OBJ_TST["s3_object"]["inval_req"])
        self.log.info(
            "ENDED: Add canned ACL bucket-owner-full-control along with READ ACL grant permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5766")
    @CTFailOn(error_handler)
    def test_invalid_custom_acl_xml_json_3228(self):
        """put object acl with invalid custom acl xml using json file."""
        self.log.info(
            "STARTED: put object acl with invalid custom acl xml using json file")
        self.log.info(
            "Bucket and Object : %s %s",
            self.bucket_name,
            self.obj_name)
        self.create_bucket_obj(self.bucket_name, self.obj_name)
        obj_acl_json = S3_OBJ_TST["test_3228"]["policy"]
        try:
            self.log.info("Step 1: Put invalid JSON")
            self.s3_acl_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                access_control_policy=obj_acl_json)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.S3_BKT_SPECIAL_CHARACTER_ERR in error.message, error.message
            self.log.info(
                "Step 1: Invalid JSON failed with "
                "error: %s",
                S3_OBJ_TST["test_3228"]["policy"])
        self.log.info(
            "ENDED: put object acl with invalid custom acl xml using json file")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5769")
    @CTFailOn(error_handler)
    def test_put_get_object_with_same_account_3248(self):
        """Put object acl with account1 and get object with same account1."""
        self.log.info(
            "STARTED: put object acl with account1 and get object with same account1")
        test_cfg = S3_OBJ_TST["test_3248"]
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name,
            self.email_id)
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        json_policy = test_cfg["json_policy"]
        json_policy["Owner"]["ID"] = result[0]
        json_policy["Owner"]["DisplayName"] = self.account_name
        json_policy["Grants"][0]["Grantee"]["ID"] = result[0]
        json_policy["Grants"][0]["Grantee"]["DisplayName"] = self.account_name
        s3_obj_1 = result[1]
        s3_obj_acl_1 = result[2]
        self.create_bucket_obj(
            self.bucket_name,
            self.obj_name,
            s3_test_obj=s3_obj_1)
        self.log.info("Step 1: Put canned ACL for the Existing Object")
        resp = s3_obj_acl_1.put_object_acp(
            self.bucket_name, self.obj_name, json_policy)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Put object canned acl for the object was successful")
        self.log.info("Step 2: Get object using account 1")
        resp = s3_obj_1.get_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Get object resp is : %s", resp)
        resp = s3_obj_1.bucket_list()[1]
        if self.bucket_name in resp:
            s3_obj_1.delete_bucket(self.bucket_name, force=True)
        self.log.info(
            "ENDED: put object acl with account1 and get object with same account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5747")
    @CTFailOn(error_handler)
    def test_put_get_object_3249(self):
        """Put object with account1 and get object with same account1."""
        self.log.info(
            "STARTED: put object with account1 and get object with same account1")
        self.create_bucket_obj(self.bucket_name, self.obj_name, self.s3_obj)
        self.log.info("Step 2: Get object using account 1")
        resp = self.s3_obj.get_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Get object resp is : %s", resp)
        self.log.info(
            "ENDED: put object with account1 and get object with same account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5790")
    @CTFailOn(error_handler)
    def test_get_object_by_changed_account_3250(self):
        """change account (to account2) and get object which is created by account1."""
        self.log.info(
            "STARTED: change account (to account2) and get object which is created by account1")
        self.log.info("Creating account with name %s and email_id %s",
                      self.account_name, self.email_id)
        result = self.create_s3_account(
            self.account_name, self.email_id, self.s3acc_passwd)
        s3_obj_2 = result[1]
        self.create_bucket_obj(self.bucket_name, self.obj_name, self.s3_obj)
        self.log.info("Step 2: Get object using account 2")
        try:
            s3_obj_2.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 2: get object using acc 2 failed with err message: %s",
                error.message)
        self.log.info(
            "ENDED: change account (to account2) and get object which is created by account1")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5775")
    @CTFailOn(error_handler)
    def test_put_obj_write_access_get_obj_3254(self):
        """Put object ACL with Account1, grant WRITE access to Account2 & Get obj with Account2."""
        self.log.info(
            "STARTED: Put object ACL with Account 1, grant WRITE access to"
            " Account 2 and Get object with Account 2")
        self.create_bucket_obj(self.bucket_name, self.obj_name, self.s3_obj)
        test_cfg = S3_OBJ_TST["test_3254"]
        s3_obj_2 = self.create_acc_and_put_obj_acp(
            self.bucket_name, self.obj_name, test_cfg)
        self.log.info("Step 2: Get object using account 2")
        try:
            s3_obj_2.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 2: get object using acc 2 failed with err message: %s",
                error.message)
        self.log.info("Step 2: Get object using account 2 was successful")
        self.log.info(
            "ENDED: Put object ACL with Account 1, grant WRITE access to"
            " Account 2 and Get object with Account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5772")
    @CTFailOn(error_handler)
    def test_put_obj_read_access_get_obj_3255(self):
        """Put object ACL with Account1, grant read access to Account2 & Get obj with Account2."""
        self.log.info(
            "STARTED: Put object ACL with Account 1, grant read access to"
            " Account 2 and Get object with Account 2")
        self.create_bucket_obj(self.bucket_name, self.obj_name, self.s3_obj)
        test_cfg = S3_OBJ_TST["test_3255"]
        s3_obj_2 = self.create_acc_and_put_obj_acp(
            self.bucket_name, self.obj_name, test_cfg)
        self.log.info("Step 1: Get object using account 2")
        resp = s3_obj_2.get_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info("Step 1: Get object using account 2 was successful")
        self.log.info(
            "ENDED: Put object ACL with Account 1, grant read access to"
            " Account 2 and Get object with Account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5774")
    def test_put_obj_acl_read_acp_3256(self):
        """Put obj ACL with Account1, grant read-acp access to Account2 & Get obj with Account2."""
        self.log.info(
            "STARTED: Put object ACL with Account 1, grant read-acp access to"
            " Account 2 and Get object with Account2")
        self.create_bucket_obj(self.bucket_name, self.obj_name, self.s3_obj)
        test_cfg = S3_OBJ_TST["test_3256"]
        s3_obj_2 = self.create_acc_and_put_obj_acp(
            self.bucket_name, self.obj_name, test_cfg)
        self.log.info("Step 1: Get object using account 2")
        try:
            s3_obj_2.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 1: get object using acc 2 failed with err message: %s",
                error.message)
        self.log.info(
            "ENDED: Put object ACL with Account 1, grant read-acp access to"
            " Account 2 and Get object with Account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5771")
    @CTFailOn(error_handler)
    def test_put_obj_write_acp_get_obj_3257(self):
        """Put obj ACL with Account1, grant write-acp access to Account2 get obj with Account2."""
        self.log.info(
            "STARTED: Put object ACL with Account 1, grant "
            "write-acp access to Account 2 and Get object with Account2")
        self.create_bucket_obj(self.bucket_name, self.obj_name, self.s3_obj)
        test_cfg = S3_OBJ_TST["test_3257"]
        s3_obj_2 = self.create_acc_and_put_obj_acp(
            self.bucket_name, self.obj_name, test_cfg)
        self.log.info("Step 1: Get object using account 2")
        try:
            s3_obj_2.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 1: get object using acc 2 failed with err message: %s",
                error.message)
        self.log.info(
            "ENDED: Put object ACL with Account 1, grant write-acp access to"
            " Account 2 and Get object with Account2")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5744")
    @CTFailOn(error_handler)
    def test_put_get_object_acl_xml_3451(self):
        """Put object acl in account1 and get object from account2 by using acl xml."""
        self.log.info(
            "STARTED: put object acl in account1 and get object from "
            "account2 by using acl xml")
        self.create_bucket_obj(self.bucket_name, self.obj_name, self.s3_obj)
        test_cfg = S3_OBJ_TST["test_3451"]
        self.log.info(test_cfg)
        self.log.info(
            "Creating account with name %s and email_id %s",
            self.account_name_2,
            self.email_id_2)
        result = self.create_s3_account(
            self.account_name_2, self.email_id_2, self.s3acc_passwd)
        s3_obj_2 = result[1]
        self.log.info("Step 1: Put canned ACL for the Existing Object")
        resp = self.s3_acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        modified_acl = copy.deepcopy(resp[1])
        resp = self.s3_acl_obj.put_object_acp(
            self.bucket_name, self.obj_name, modified_acl)
        assert resp[0], resp[1]
        self.log.info(
            "Step 1: Put object canned acl for the object was successful")
        self.log.info("Step 2: Get object using account 2")
        try:
            s3_obj_2.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert errmsg.ACCESS_DENIED_ERR_KEY in error.message, error.message
            self.log.info(
                "Step 2: get object using acc 2 failed with err message: %s",
                error.message)
        self.log.info("Step 2: Get object using account 2 was successful")
        self.log.info(
            "ENDED: put object acl in account1 and get object from account2 by using acl xml")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5741")
    @CTFailOn(error_handler)
    def test_put_obj_full_control_get_acl_xml_3452(self):
        """
        put object in account1 and give full control permissions to account2.

        get object from account2 by using acl xml.
        """
        self.log.info(
            "STARTED: put object in account1 and give full control permissions to "
            "account2 and get object from account2 by using acl xml")
        self.create_bucket_obj(self.bucket_name, self.obj_name, self.s3_obj)
        test_cfg = S3_OBJ_TST["test_3452"]
        s3_obj_2 = self.create_acc_and_put_obj_acp(
            self.bucket_name, self.obj_name, test_cfg)
        self.log.info("Step 1: Get object using account 2")
        resp = s3_obj_2.get_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info("Step 1: Get object using account 2 was successful")
        self.log.info(
            "ENDED: put object in account1 and give full control permissions to "
            "account2 and get object from account2 by using acl xml")
