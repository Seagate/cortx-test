# !/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

"""All Users Object Acl Test Module."""
import os
import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import make_dirs, cleanup_dir, path_exists
from config import S3_CFG
from libs.s3 import s3_test_lib, iam_test_lib, s3_acl_test_lib

ALL_USERS_CONF = read_yaml("config/s3/test_all_users_object_acl.yaml")[1]


class TestAllUsers:
    """All Users Object ACL Testsuite."""

    all_user_cfg = ALL_USERS_CONF["all_users_obj_acl"]

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.bucket_name = "{0}{1}".format(
            cls.all_user_cfg["bucket_name"], str(int(time.time())))
        cls.obj_name = "{0}{1}".format(
            cls.all_user_cfg["obj_name"], str(int(time.time())))
        cls.test_file = "all_users_obj_acl.txt"
        cls.test_dir_path = os.path.join(os.getcwd(), "testdata")
        cls.test_file_path = os.path.join(cls.test_dir_path, cls.test_file)
        cls.log.info("Test file path: %s", cls.test_file_path)
        cls.log.info("ENDED: setup test suite operations.")

    def put_object_acl(self, acl):
        """helper method to put object acl and verify it."""
        if acl == "grant_read":
            resp = self.acl_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                grant_read=self.all_user_cfg["group_uri"])
            assert resp[0], resp[1]
        elif acl == "grant_write":
            resp = self.acl_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                grant_write=self.all_user_cfg["group_uri"])
            assert resp[0], resp[1]
        elif acl == "grant_full_control":
            resp = self.acl_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                grant_full_control=self.all_user_cfg["group_uri"])
            assert resp[0], resp[1]
        elif acl == "grant_read_acp":
            resp = self.acl_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                grant_read_acp=self.all_user_cfg["group_uri"])
            assert resp[0], resp[1]
        elif acl == "grant_write_acp":
            resp = self.acl_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                grant_write_acp=self.all_user_cfg["group_uri"])
            assert resp[0], resp[1]

    def verify_obj_acl_edit(self, permission):
        """helper method to verify object's acl is changed."""
        self.log.info("Step 2: Verifying that object's acl is changed")
        resp = self.acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert permission == resp[1]["Grants"][0]["Permission"], resp[1]
        self.log.info("Step 2: Verified that object's acl is changed")

    def setup_method(self):
        """
        Function will be invoked before running each test case.

        It will perform all prerequisite steps required for test execution.
        It will create a bucket and upload an object to that bucket.
        """
        self.log.info("STARTED: Setup operations")
        self.s3_test_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.acl_obj = s3_acl_test_lib.S3AclTestLib(endpoint_url=S3_CFG["s3_url"])
        self.no_auth_obj = s3_test_lib.S3LibNoAuth(endpoint_url=S3_CFG["s3_url"])
        self.iam_test_obj = iam_test_lib.IamTestLib(endpoint_url=S3_CFG["iam_url"])
        if not path_exists(self.test_dir_path):
            resp = make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", resp)
        self.bucket_name = "{0}{1}".format(
            self.all_user_cfg["bucket_name"], str(int(time.time())))
        self.obj_name = "{0}{1}".format(
            self.all_user_cfg["obj_name"], str(int(time.time())))
        self.log.info("Creating a bucket and putting an object into bucket")
        try:
            self.s3_test_obj.delete_bucket(bucket_name=self.bucket_name, force=True)
        except Exception as berr:
            self.log.warning(berr)
        resp = self.s3_test_obj.create_bucket_put_object(
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.all_user_cfg["mb_count"])
        assert resp[0], resp[1]
        self.log.info(
            "Created a bucket and put an object into bucket successfully")
        self.log.info("Setting bucket ACL to FULL_CONTROL for all users")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_full_control=self.all_user_cfg["group_uri"])
        assert resp[0], resp[1]
        self.log.info("Set bucket ACL to FULL_CONTROL for all users")
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info("Clean : %s", self.test_dir_path)
        if path_exists(self.test_dir_path):
            resp = cleanup_dir(self.test_dir_path)
            self.log.info(
                "cleaned path: %s, resp: %s",
                self.test_dir_path,
                resp)
        bucket_list = self.s3_test_obj.bucket_list()[1]
        all_users_buckets = [
            bucket for bucket in bucket_list if ALL_USERS_CONF["all_users_obj_acl"]["bucket_name"]
            in bucket]
        self.log.info("Deleting buckets...")
        for bucket in all_users_buckets:
            self.acl_obj.put_bucket_acl(
                bucket, grant_full_control=ALL_USERS_CONF["all_users_obj_acl"]["group_uri"])
        if all_users_buckets:
            self.s3_test_obj.delete_multiple_buckets(all_users_buckets)
        self.log.info("Deleted buckets.")
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-6019")
    @CTFailOn(error_handler)
    def test_put_duplicate_object_without_auth_695(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have READ permission on object
        """
        test_695_cfg = ALL_USERS_CONF["test_695"]
        self.log.info(
            "STARTED: Put an object with same name in bucket without Autentication "
            "when AllUsers have READ permission on object")
        self.log.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        self.log.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit(test_695_cfg["permission"])
        self.log.info(
            "Step 3: Uploading same object into bucket using unsigned account")
        resp = self.no_auth_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.test_file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Uploaded same object into bucket successfully")
        self.log.info(
            "ENDED: Put an object with same name in bucket without Autentication when "
            "AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-6016")
    @CTFailOn(error_handler)
    def test_delete_object_without_authentication_697(self):
        """
        Delete an object from bucket without Authentication.

        Condition: AllUsers have READ permission on object
        """
        test_697_cfg = ALL_USERS_CONF["test_697"]
        self.log.info(
            "STARTED: Delete an object from bucket without Authentication when "
            "AllUsers have READ permission on object")
        self.log.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        self.log.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit(test_697_cfg["permission"])
        self.log.info(
            "Step 3: Deleting an object from bucket using unsigned account")
        resp = self.no_auth_obj.delete_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Deleted an object from bucket using unsigned account successfully")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication "
            "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-6014")
    @CTFailOn(error_handler)
    def test_read_object_acl_without_auth_698(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have READ permission on object
        """
        test_698_cfg = ALL_USERS_CONF["test_698"]
        self.log.info(
            "STARTED: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ permission on object")
        self.log.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        self.log.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit(test_698_cfg["permission"])
        self.log.info(
            "Step 3: Reading an object ACL from bucket using unsigned account")
        try:
            self.no_auth_obj.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert test_698_cfg["err_message"] in error.message, error.message
        self.log.info(
            "Step 3: Reading an object ACL using unsigned account failed with %s",
            test_698_cfg["err_message"])
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-6011")
    @CTFailOn(error_handler)
    def test_update_object_acl_without_auth_699(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have READ permission on object
        """
        test_699_cfg = ALL_USERS_CONF["test_699"]
        self.log.info(
            "STARTED: Update an object ACL in bucket without Authentication "
            "when AllUsers have READ permission on object")
        self.log.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        self.log.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit(test_699_cfg["permission"])
        self.log.info(
            "Step 3: Updating an object ACL from bucket using unsigned account")
        try:
            self.no_auth_obj.put_object_canned_acl(
                self.bucket_name, self.obj_name, acl=test_699_cfg["acl"])
        except CTException as error:
            self.log.error(error.message)
            assert test_699_cfg["err_message"] in error.message, error.message
        self.log.info(
            "Step 3: Updating an object ACL using unsigned account failed with %s",
            test_699_cfg["err_message"])
        self.log.info(
            "ENDED: Update an object ACL in bucket without Authentication "
            "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-6009")
    @CTFailOn(error_handler)
    def test_put_duplicate_object_without_authentication_700(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        test_700_cfg = ALL_USERS_CONF["test_700"]
        self.log.info(
            "STARTED: Put an object with same name in bucket without Authentication "
            "when AllUsers have WRITE permission on object")
        self.log.info(
            "Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        self.log.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit(test_700_cfg["permission"])
        self.log.info(
            "Step 3: Putting an object with same name to bucket using unsigned account")
        resp = self.no_auth_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.test_file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Put an object with same name to bucket using unsigned account successfully")
        self.log.info(
            "ENDED: Put an object with same name in bucket without Autentication "
            "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-6006")
    @CTFailOn(error_handler)
    def test_delete_obj_without_auth_701(self):
        """
        Delete an object from bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        test_701_cfg = ALL_USERS_CONF["test_701"]
        self.log.info(
            "STARTED: Delete an object from bucket without Authentication "
            "when AllUsers have WRITE permission on object")
        self.log.info(
            "Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        self.log.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit(test_701_cfg["permission"])
        self.log.info(
            "Step 3: Deleting an object from a bucket using unsigned account")
        resp = self.no_auth_obj.delete_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Deleted an object from a bucket using unsigned account successfully")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication "
            "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-6004")
    @CTFailOn(error_handler)
    def test_read_obj_acl_without_auth_702(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        test_702_cfg = ALL_USERS_CONF["test_702"]
        self.log.info(
            "STARTED: Read an object ACL from bucket without Authentication "
            "when AllUsers have WRITE permission on object")
        self.log.info(
            "Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        self.log.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit(test_702_cfg["permission"])
        self.log.info(
            "Step 3: Reading an object acl from a bucket using unsigned account")
        try:
            self.no_auth_obj.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert test_702_cfg["err_message"] in error.message, error.message
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-6002")
    @CTFailOn(error_handler)
    def test_update_obj_write_permission_without_auth_703(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        test_703_cfg = ALL_USERS_CONF["test_703"]
        self.log.info(
            "STARTED: Update an object ACL in bucket without Authentication "
            "when AllUsers have WRITE permission on object")
        self.log.info(
            "Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        self.log.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit(test_703_cfg["permission"])
        self.log.info(
            "Step 3: Updating an object ACL using unsigned account")
        try:
            self.no_auth_obj.put_object_canned_acl(
                self.bucket_name, self.obj_name, acl=test_703_cfg["acl"])
        except CTException as error:
            self.log.error(error.message)
            assert test_703_cfg["err_message"] in error.message, error.message
        self.log.info(
            "ENDED: Update an object ACL in bucket without Authentication "
            "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-6001")
    @CTFailOn(error_handler)
    def test_put_duplicate_object_read_acp_704(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        test_704_cfg = ALL_USERS_CONF["test_704"]
        self.log.info(
            "STARTED: Put an object with same name in bucket without Autentication "
            "when AllUsers have READ_ACP permission on object")
        self.log.info(
            "Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        self.log.info(
            "Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit(test_704_cfg["permission"])
        self.log.info(
            "Step 3: Putting an object with same name in bucket using unsigned account")
        resp = self.no_auth_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.test_file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Put an object with same name in bucket using unsigned account successfully")
        self.log.info(
            "ENDED: Put an object with same name in bucket without Autentication "
            "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5970")
    @CTFailOn(error_handler)
    def test_get_object_without_authentication_read_permission_757(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have READ permission on object
        """
        test_757_cfg = ALL_USERS_CONF["test_757"]
        self.log.info(
            "STARTED: GET an object from bucket without Autentication "
            "when AllUsers have READ permission on object")
        self.log.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        self.log.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit(test_757_cfg["permission"])
        self.log.info(
            "Step 3: Reading an object which is uploaded to bucket using unsigned account")
        resp = self.no_auth_obj.get_object(
            self.bucket_name,
            self.obj_name)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Read an object which is uploaded to bucket successfully")
        self.log.info(
            "ENDED: GET an object from bucket without Autentication "
            "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5968")
    @CTFailOn(error_handler)
    def test_get_allusers_object_without_auth_758(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        test_758_cfg = ALL_USERS_CONF["test_758"]
        self.log.info(
            "STARTED: GET an object from bucket without Autentication "
            "when AllUsers have WRITE permission on object")
        self.log.info(
            "Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        self.log.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit(test_758_cfg["permission"])
        self.log.info(
            "Step 3: Reading an object from a bucket using unsigned account")
        try:
            self.no_auth_obj.get_object(
                self.bucket_name,
                self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert test_758_cfg["err_message"] in error.message, error.message
        self.log.info(
            "Step 3: Reading object from a bucket using unsigned account failed with %s",
            test_758_cfg["err_message"])
        self.log.info(
            "ENDED: GET an object from bucket without Autentication "
            "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5999")
    @CTFailOn(error_handler)
    def test_get_object_read_acp_705(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        test_705_cfg = ALL_USERS_CONF["test_705"]
        self.log.info(
            "Started : GET an object from bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")
        self.log.info(
            "Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        self.log.info(
            "Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit(test_705_cfg["permission"])
        self.log.info(
            "Step 3: Reading an object from a bucket using unsigned account")
        try:
            self.no_auth_obj.get_object(
                self.bucket_name,
                self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert test_705_cfg["err_message"] in error.message, error.message
        self.log.info(
            "Step 3: Reading object from a bucket using unsigned account failed with %s",
            test_705_cfg["err_message"])
        self.log.info(
            "ENDED: GET an object from bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5997")
    @CTFailOn(error_handler)
    def test_read_obj_without_auth_read_acp_706(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        test_706_cfg = ALL_USERS_CONF["test_706"]
        self.log.info(
            "Started: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")
        self.log.info(
            "Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        self.log.info(
            "Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit(test_706_cfg["permission"])
        self.log.info(
            "Step 3: Reading acl of object from a bucket using unsigned account")
        resp = self.no_auth_obj.get_object_acl(
            self.bucket_name,
            self.obj_name)
        assert resp[0], resp[1]
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5995")
    @CTFailOn(error_handler)
    def test_update_obj_without_auth_read_acp_707(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        test_707_cfg = ALL_USERS_CONF["test_707"]
        self.log.info(
            "Started: Update an object ACL in bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")
        self.log.info(
            "Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        self.log.info(
            "Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit(test_707_cfg["permission"])
        self.log.info(
            "Step 3: Updating an object ACL using unsigned account")
        try:
            self.no_auth_obj.put_object_canned_acl(
                self.bucket_name, self.obj_name, acl=test_707_cfg["acl"])
        except CTException as error:
            self.log.error(error.message)
            assert test_707_cfg["err_message"] in error.message, error.message
        self.log.info(
            "ENDED: Update an object ACL in bucket without Authentication "
            "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5993")
    @CTFailOn(error_handler)
    def test_put_object_without_auth_write_acp_708(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        test_708_cfg = ALL_USERS_CONF["test_708"]
        self.log.info(
            "Started: Put an object with same name in bucket without Autentication "
            "when AllUsers have WRITE_ACP permission on object")
        self.log.info(
            "Step 1: Changing object's acl to WRITE_ACP for all users")
        self.put_object_acl("grant_write_acp")
        self.log.info(
            "Step 1: Changed object's acl to WRITE_ACP for all users")
        self.verify_obj_acl_edit(test_708_cfg["permission"])
        self.log.info(
            "Step 3: Upload same object to bucket using unsigned account")
        resp = self.no_auth_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.test_file_path)
        assert resp[0], resp[1]
        self.log.info(
            "ENDED: Put an object with same name in bucket without Autentication "
            "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5986")
    @CTFailOn(error_handler)
    def test_get_object_without_auth_write_acp_709(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        test_709_cfg = ALL_USERS_CONF["test_709"]
        self.log.info(
            "Started:GET an object from bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")
        self.log.info(
            "Step 1: Changing object's acl to WRITE_ACP for all users")
        self.put_object_acl("grant_write_acp")
        self.log.info(
            "Step 1: Changed object's acl to WRITE_ACP for all users")
        self.verify_obj_acl_edit(test_709_cfg["permission"])
        self.log.info(
            "Step 3: Get object using unsigned account")
        try:
            self.no_auth_obj.get_object(
                self.bucket_name,
                self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert test_709_cfg["err_message"] in error.message, error.message
        self.log.info(
            "ENDED:GET an object from bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5984")
    @CTFailOn(error_handler)
    def test_read_object_without_auth_write_acp_710(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        test_710_cfg = ALL_USERS_CONF["test_710"]
        self.log.info(
            "Started: Read an object ACL from bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")
        self.log.info(
            "Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_write_acp")
        self.log.info(
            "Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit(test_710_cfg["permission"])
        self.log.info(
            "Step 3: Reading acl of object from a bucket using unsigned account")
        try:
            self.no_auth_obj.get_object_acl(
                self.bucket_name,
                self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert test_710_cfg["err_message"] in error.message, error.message
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5982")
    @CTFailOn(error_handler)
    def test_update_object_without_auth_write_acp_711(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        test_711_cfg = ALL_USERS_CONF["test_711"]
        self.log.info(
            "Started:Update an object ACL in bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")
        self.log.info(
            "Step 1: Changing object's acl to WRITE_ACP for all users")
        self.put_object_acl("grant_write_acp")
        self.log.info(
            "Step 1: Changed object's acl to WRITE_ACP for all users")
        self.verify_obj_acl_edit(test_711_cfg["permission"])
        self.log.info(
            "Step 3: Update ACL of object using unsigned account")
        self.put_object_acl("grant_full_control")
        self.log.info(
            "ENDED:Update an object ACL in bucket without Authentication "
            "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5979")
    @CTFailOn(error_handler)
    def test_put_duplicate_object_full_control_712(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        test_712_cfg = ALL_USERS_CONF["test_712"]
        self.log.info(
            "Started:Put an object with same name in bucket without Authentication"
            "when AllUsers have FULL_CONTROL permission on object")
        self.log.info(
            "Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        self.log.info(
            "Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit(test_712_cfg["permission"])
        self.log.info(
            "Step 3: upload same object in that bucket using unsigned account")
        resp = self.no_auth_obj.put_object(
            self.bucket_name,
            self.obj_name,
            self.test_file_path)
        assert resp[0], resp[1]
        self.log.info(
            "ENDED:Put an object with same name in bucket without Autentication "
            "when AllUsers have FULL_CONTROL permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5977")
    @CTFailOn(error_handler)
    def test_get_object_without_auth_full_control_713(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        test_713_cfg = ALL_USERS_CONF["test_713"]
        self.log.info(
            "Started:GET an object from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")
        self.log.info(
            "Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        self.log.info(
            "Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit(test_713_cfg["permission"])
        self.log.info(
            "Step 3: Get object from that bucket using unsigned account")
        resp = self.no_auth_obj.get_object(
            self.bucket_name,
            self.obj_name)
        assert resp[0], resp[1]
        self.log.info(
            "ENDED:GET an object from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5975")
    @CTFailOn(error_handler)
    def test_read_object_without_auth_full_control_714(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        test_714_cfg = ALL_USERS_CONF["test_714"]
        self.log.info(
            "Started:Read an object ACL from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")
        self.log.info(
            "Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        self.log.info(
            "Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit(test_714_cfg["permission"])
        self.log.info(
            "Step 3: Get object acl from that bucket using unsigned account")
        resp = self.acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert test_714_cfg["permission"] == resp[1]["Grants"][0]["Permission"], resp[1]
        self.log.info(
            "ENDED:Read an object ACL from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5973")
    @CTFailOn(error_handler)
    def test_update_object_without_auth_full_control_715(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        test_715_cfg = ALL_USERS_CONF["test_715"]
        self.log.info(
            "Started:Update an object ACL in bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")
        self.log.info(
            "Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        self.log.info(
            "Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit(test_715_cfg["permission"])
        self.log.info(
            "Step 3: Update object acl from that bucket using unsigned account")
        self.put_object_acl("grant_write_acp")
        self.log.info(
            "Step 3: Changed object's acl to FULL_CONTROL for all users")
        self.log.info("Step 4: Verifying that object's acl is changed")
        resp = self.acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert test_715_cfg["new_permission"] == resp[1]["Grants"][0]["Permission"], resp[1]
        self.log.info("Step 4: Verified that object's acl is changed")
        self.log.info(
            "ENDED:Update an object ACL in bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission on object")
