# !/usr/bin/python
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

"""All Users Object Acl Test Module."""
import logging
import os
from time import perf_counter_ns

import pytest

from commons import error_messages as err_msg
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils.s3_utils import poll
from commons.utils.system_utils import make_dirs
from commons.utils.system_utils import path_exists
from commons.utils.system_utils import remove_file
from config.s3 import S3_CFG
from libs.s3 import iam_test_lib
from libs.s3 import s3_acl_test_lib
from libs.s3 import s3_test_lib


# pylint: disable-msg=too-many-public-methods
class TestAllUsersObjectAcl:
    """All Users Object ACL Testsuite."""

    log = logging.getLogger(__name__)

    @classmethod
    def setup_class(cls):
        """
        Setup_class will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log.info("STARTED: setup test suite operations.")
        cls.s3_test_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.acl_obj = s3_acl_test_lib.S3AclTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.no_auth_obj = s3_test_lib.S3LibNoAuth(endpoint_url=S3_CFG["s3_url"])
        cls.iam_test_obj = iam_test_lib.IamTestLib(endpoint_url=S3_CFG["iam_url"])
        cls.group_uri = cls.test_dir_path = cls.test_file_path = None
        cls.bucket_name = cls.obj_name = None
        cls.log.info("ENDED: setup test suite operations.")

    def setup_method(self):
        """
        Setup_method will be invoked before running each test case.

        It will perform all prerequisite steps required for test execution.
        It will create a bucket and upload an object to that bucket.
        """
        self.log.info("STARTED: Setup operations")
        self.group_uri = "uri=http://acs.amazonaws.com/groups/global/AllUsers"
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestAllUsersObjectAcl")
        if not path_exists(self.test_dir_path):
            resp = make_dirs(self.test_dir_path)
            self.log.info("Created Directory path: %s", resp)
        self.test_file_path = os.path.join(
            self.test_dir_path, f"all_users_obj_acl{perf_counter_ns()}")
        self.log.info("Test file path: %s", self.test_file_path)
        self.bucket_name = f"allusersobjacl-bkt{perf_counter_ns()}"
        self.obj_name = f"allusersobj{perf_counter_ns()}"
        self.log.info("Creating a bucket and putting an object into bucket")
        resp = self.s3_test_obj.create_bucket_put_object(self.bucket_name, self.obj_name,
                                                         self.test_file_path, mb_count=5)
        assert resp[0], resp[1]
        self.log.info("Created a bucket and put an object into bucket successfully")
        self.log.info("Setting bucket ACL to FULL_CONTROL for all users")
        resp = self.acl_obj.put_bucket_acl(self.bucket_name, grant_full_control=self.group_uri)
        assert resp[0], resp[1]
        self.log.info("Set bucket ACL to FULL_CONTROL for all users")
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Teardown will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info("Clean : %s", self.test_dir_path)
        if path_exists(self.test_file_path):
            resp = remove_file(self.test_file_path)
            self.log.info("cleaned path: %s, resp: %s", self.test_file_path, resp)
        self.log.info("Deleting buckets...")
        status, response = self.s3_test_obj.delete_bucket(bucket_name=self.bucket_name, force=True)
        assert status, response
        self.log.info("ENDED: Teardown operations")

    def put_object_acl(self, acl):
        """Put object acl and verify it."""
        if acl == "grant_read":
            resp = self.acl_obj.put_object_canned_acl(
                self.bucket_name, self.obj_name, grant_read=self.group_uri)
            assert resp[0], resp[1]
        elif acl == "grant_write":
            resp = self.acl_obj.put_object_canned_acl(
                self.bucket_name, self.obj_name, grant_write=self.group_uri)
            assert resp[0], resp[1]
        elif acl == "grant_full_control":
            resp = self.acl_obj.put_object_canned_acl(
                self.bucket_name, self.obj_name, grant_full_control=self.group_uri)
            assert resp[0], resp[1]
        elif acl == "grant_read_acp":
            resp = self.acl_obj.put_object_canned_acl(
                self.bucket_name, self.obj_name, grant_read_acp=self.group_uri)
            assert resp[0], resp[1]
        elif acl == "grant_write_acp":
            resp = self.acl_obj.put_object_canned_acl(
                self.bucket_name, self.obj_name, grant_write_acp=self.group_uri)
            assert resp[0], resp[1]

    def verify_obj_acl_edit(self, permission):
        """Verify object's acl is changed."""
        self.log.info("Step 2: Verifying that object's acl is changed")
        resp = self.acl_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        assert permission == resp[1]["Grants"][0]["Permission"], resp[1]
        self.log.info("Step 2: Verified that object's acl is changed")

    def get_object_acl_using_unsigned_account(self):
        """Get object acl using unsigned account."""
        self.log.info("Step: Reading an object ACL from bucket using unsigned account")
        try:
            self.no_auth_obj.get_object_acl(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert err_msg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("Step: Reading an object ACL using unsigned account failed with %s",
                      err_msg.ACCESS_DENIED_ERR_KEY)

    def get_object_using_unsigned_account(self):
        """Get object using unsigned account."""
        self.log.info("Step: Reading an object from a bucket using unsigned account")
        try:
            self.no_auth_obj.get_object(self.bucket_name, self.obj_name)
        except CTException as error:
            self.log.error(error.message)
            assert err_msg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("Step: Reading object from a bucket using unsigned account failed with %s",
                      err_msg.ACCESS_DENIED_ERR_KEY)

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6019")
    def test_put_duplicate_object_without_auth_695(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have READ permission on object
        """
        self.log.info("STARTED: Put an object with same name in bucket without Autentication "
                      "when AllUsers have READ permission on object")
        self.log.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        self.log.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit("READ")
        self.log.info("Step 3: Uploading same object into bucket using unsigned account")
        resp = poll(self.no_auth_obj.put_object, self.bucket_name, self.obj_name,
                    self.test_file_path)
        assert resp[0], resp[1]
        self.log.info("Step 3: Uploaded same object into bucket successfully")
        self.log.info("ENDED: Put an object with same name in bucket without Autentication when "
                      "AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6016")
    def test_delete_object_without_authentication_697(self):
        """
        Delete an object from bucket without Authentication.

        Condition: AllUsers have READ permission on object
        """
        self.log.info("STARTED: Delete an object from bucket without Authentication when "
                      "AllUsers have READ permission on object")
        self.log.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        self.log.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit("READ")
        self.log.info("Step 3: Deleting an object from bucket using unsigned account")
        resp = poll(self.no_auth_obj.delete_object, self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info("Step 3: Deleted an object from bucket using unsigned account successfully")
        self.log.info("ENDED: Delete an object from bucket without Authentication "
                      "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-6014")
    def test_read_object_acl_without_auth_698(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have READ permission on object
        """
        self.log.info("STARTED: Read an object ACL from bucket without Authentication "
                      "when AllUsers have READ permission on object")
        self.log.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        self.log.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit("READ")
        self.get_object_acl_using_unsigned_account()
        self.log.info("ENDED: Read an object ACL from bucket without Authentication "
                      "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-6011")
    def test_update_object_acl_without_auth_699(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have READ permission on object
        """
        self.log.info("STARTED: Update an object ACL in bucket without Authentication "
                      "when AllUsers have READ permission on object")
        self.log.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        self.log.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit("READ")
        self.log.info("Step 3: Updating an object ACL from bucket using unsigned account")
        try:
            self.no_auth_obj.put_object_canned_acl(self.bucket_name, self.obj_name, acl="private")
        except CTException as error:
            self.log.error(error.message)
            assert err_msg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("Step 3: Updating an object ACL using unsigned account failed with %s",
                      err_msg.ACCESS_DENIED_ERR_KEY)
        self.log.info("ENDED: Update an object ACL in bucket without Authentication "
                      "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-6009")
    def test_put_duplicate_object_without_authentication_700(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        self.log.info("STARTED: Put an object with same name in bucket without Authentication "
                      "when AllUsers have WRITE permission on object")
        self.log.info("Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        self.log.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit("WRITE")
        self.log.info("Step 3: Putting an object with same name to bucket using unsigned account")
        resp = self.no_auth_obj.put_object(self.bucket_name, self.obj_name, self.test_file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Put an object with same name to bucket using unsigned account successfully")
        self.log.info("ENDED: Put an object with same name in bucket without Autentication "
                      "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-6006")
    def test_delete_obj_without_auth_701(self):
        """
        Delete an object from bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        self.log.info("STARTED: Delete an object from bucket without Authentication "
                      "when AllUsers have WRITE permission on object")
        self.log.info("Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        self.log.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit("WRITE")
        self.log.info("Step 3: Deleting an object from a bucket using unsigned account")
        resp = self.no_auth_obj.delete_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info("Step 3: Deleted an object from a bucket using unsigned account successfully")
        self.log.info("ENDED: Delete an object from bucket without Authentication "
                      "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-6004")
    def test_read_obj_acl_without_auth_702(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        self.log.info("STARTED: Read an object ACL from bucket without Authentication "
                      "when AllUsers have WRITE permission on object")
        self.log.info("Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        self.log.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit("WRITE")
        self.get_object_acl_using_unsigned_account()
        self.log.info("ENDED: Read an object ACL from bucket without Authentication "
                      "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-6002")
    def test_update_obj_write_permission_without_auth_703(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        self.log.info("STARTED: Update an object ACL in bucket without Authentication "
                      "when AllUsers have WRITE permission on object")
        self.log.info("Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        self.log.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit("WRITE")
        self.log.info("Step 3: Updating an object ACL using unsigned account")
        try:
            self.no_auth_obj.put_object_canned_acl(self.bucket_name, self.obj_name, acl="private")
        except CTException as error:
            self.log.error(error.message)
            assert err_msg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("ENDED: Update an object ACL in bucket without Authentication "
                      "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-6001")
    def test_put_duplicate_object_read_acp_704(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        self.log.info("STARTED: Put an object with same name in bucket without Autentication "
                      "when AllUsers have READ_ACP permission on object")
        self.log.info("Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        self.log.info("Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit("READ_ACP")
        self.log.info("Step 3: Putting an object with same name in bucket using unsigned account")
        resp = self.no_auth_obj.put_object(self.bucket_name, self.obj_name, self.test_file_path)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Put an object with same name in bucket using unsigned account successfully")
        self.log.info("ENDED: Put an object with same name in bucket without Autentication "
                      "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5970")
    def test_get_object_without_authentication_read_permission_757(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have READ permission on object
        """
        self.log.info("STARTED: GET an object from bucket without Autentication "
                      "when AllUsers have READ permission on object")
        self.log.info("Step 1: Changing object's acl to READ for all users")
        self.put_object_acl("grant_read")
        self.log.info("Step 1: Changed object's acl to READ for all users")
        self.verify_obj_acl_edit("READ")
        self.log.info(
            "Step 2: Reading an object which is uploaded to bucket using unsigned account")
        resp = self.no_auth_obj.get_object(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info("Step 2: Read an object which is uploaded to bucket successfully")
        self.log.info("ENDED: GET an object from bucket without Autentication "
                      "when AllUsers have READ permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5968")
    def test_get_allusers_object_without_auth_758(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have WRITE permission on object
        """
        self.log.info("STARTED: GET an object from bucket without Autentication "
                      "when AllUsers have WRITE permission on object")
        self.log.info("Step 1: Changing object's acl to WRITE for all users")
        self.put_object_acl("grant_write")
        self.log.info("Step 1: Changed object's acl to WRITE for all users")
        self.verify_obj_acl_edit("WRITE")
        self.get_object_using_unsigned_account()
        self.log.info("ENDED: GET an object from bucket without Autentication "
                      "when AllUsers have WRITE permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5999")
    def test_get_object_read_acp_705(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        self.log.info("Started : GET an object from bucket without Authentication "
                      "when AllUsers have READ_ACP permission on object")
        self.log.info("Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        self.log.info("Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit("READ_ACP")
        self.get_object_using_unsigned_account()
        self.log.info("ENDED: GET an object from bucket without Authentication "
                      "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5997")
    def test_read_obj_without_auth_read_acp_706(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        self.log.info("Started: Read an object ACL from bucket without Authentication "
                      "when AllUsers have READ_ACP permission on object")
        self.log.info("Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        self.log.info("Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit("READ_ACP")
        self.log.info("Step 3: Reading acl of object from a bucket using unsigned account")
        resp = self.no_auth_obj.get_object_acl(self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info("ENDED: Read an object ACL from bucket without Authentication "
                      "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5995")
    def test_update_obj_without_auth_read_acp_707(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have READ_ACP permission on object
        """
        self.log.info("Started: Update an object ACL in bucket without Authentication "
                      "when AllUsers have READ_ACP permission on object")
        self.log.info("Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_read_acp")
        self.log.info("Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit("READ_ACP")
        self.log.info("Step 3: Updating an object ACL using unsigned account")
        try:
            self.no_auth_obj.put_object_canned_acl(self.bucket_name, self.obj_name, acl="private")
        except CTException as error:
            self.log.error(error.message)
            assert err_msg.ACCESS_DENIED_ERR_KEY in error.message, error.message
        self.log.info("ENDED: Update an object ACL in bucket without Authentication "
                      "when AllUsers have READ_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5993")
    def test_put_object_without_auth_write_acp_708(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        self.log.info("Started: Put an object with same name in bucket without Autentication "
                      "when AllUsers have WRITE_ACP permission on object")
        self.log.info("Step 1: Changing object's acl to WRITE_ACP for all users")
        self.put_object_acl("grant_write_acp")
        self.log.info("Step 1: Changed object's acl to WRITE_ACP for all users")
        self.verify_obj_acl_edit("WRITE_ACP")
        self.log.info("Step 3: Upload same object to bucket using unsigned account")
        resp = self.no_auth_obj.put_object(self.bucket_name, self.obj_name, self.test_file_path)
        assert resp[0], resp[1]
        self.log.info("ENDED: Put an object with same name in bucket without Autentication "
                      "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5986")
    def test_get_object_without_auth_write_acp_709(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        self.log.info("Started:GET an object from bucket without Authentication "
                      "when AllUsers have WRITE_ACP permission on object")
        self.log.info("Step 1: Changing object's acl to WRITE_ACP for all users")
        self.put_object_acl("grant_write_acp")
        self.log.info("Step 1: Changed object's acl to WRITE_ACP for all users")
        self.verify_obj_acl_edit("WRITE_ACP")
        self.get_object_using_unsigned_account()
        self.log.info("ENDED:GET an object from bucket without Authentication "
                      "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5984")
    def test_read_object_without_auth_write_acp_710(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        self.log.info("Started: Read an object ACL from bucket without Authentication "
                      "when AllUsers have WRITE_ACP permission on object")
        self.log.info("Step 1: Changing object's acl to READ_ACP for all users")
        self.put_object_acl("grant_write_acp")
        self.log.info("Step 1: Changed object's acl to READ_ACP for all users")
        self.verify_obj_acl_edit("WRITE_ACP")
        self.get_object_acl_using_unsigned_account()
        self.log.info("ENDED: Read an object ACL from bucket without Authentication "
                      "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.tags("TEST-5982")
    def test_update_object_without_auth_write_acp_711(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have WRITE_ACP permission on object
        """
        self.log.info("Started:Update an object ACL in bucket without Authentication "
                      "when AllUsers have WRITE_ACP permission on object")
        self.log.info("Step 1: Changing object's acl to WRITE_ACP for all users")
        self.put_object_acl("grant_write_acp")
        self.log.info("Step 1: Changed object's acl to WRITE_ACP for all users")
        self.verify_obj_acl_edit("WRITE_ACP")
        self.log.info("Step 3: Update ACL of object using unsigned account")
        self.put_object_acl("grant_full_control")
        self.log.info("ENDED:Update an object ACL in bucket without Authentication "
                      "when AllUsers have WRITE_ACP permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5979")
    def test_put_duplicate_object_full_control_712(self):
        """
        Put an object with same name in bucket without Authentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        self.log.info("Started:Put an object with same name in bucket without Authentication"
                      "when AllUsers have FULL_CONTROL permission on object")
        self.log.info("Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        self.log.info("Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit("FULL_CONTROL")
        self.log.info("Step 3: upload same object in that bucket using unsigned account")
        resp = poll(self.no_auth_obj.put_object, self.bucket_name, self.obj_name,
                    self.test_file_path)
        assert resp[0], resp[1]
        self.log.info("ENDED:Put an object with same name in bucket without Autentication "
                      "when AllUsers have FULL_CONTROL permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5977")
    def test_get_object_without_auth_full_control_713(self):
        """
        GET an object from bucket without Authentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        self.log.info("Started:GET an object from bucket without Authentication "
                      "when AllUsers have FULL_CONTROL permission on object")
        self.log.info("Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        self.log.info("Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit("FULL_CONTROL")
        self.log.info("Step 3: Get object from that bucket using unsigned account")
        resp = poll(self.no_auth_obj.get_object, self.bucket_name, self.obj_name)
        assert resp[0], resp[1]
        self.log.info("ENDED:GET an object from bucket without Authentication "
                      "when AllUsers have FULL_CONTROL permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5975")
    def test_read_object_without_auth_full_control_714(self):
        """
        Read an object ACL from bucket without Authentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        self.log.info("Started:Read an object ACL from bucket without Authentication "
                      "when AllUsers have FULL_CONTROL permission on object")
        self.log.info("Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        self.log.info("Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit("FULL_CONTROL")
        self.log.info("Step 3: Get object acl from that bucket using unsigned account")
        resp = poll(self.acl_obj.get_object_acl, self.bucket_name, self.obj_name,
                    condition="{}[1]['Grants'][0]['Permission']=='FULL_CONTROL'")
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == "FULL_CONTROL", resp[1]
        self.log.info("ENDED:Read an object ACL from bucket without Authentication "
                      "when AllUsers have FULL_CONTROL permission on object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_acl
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5973")
    def test_update_object_without_auth_full_control_715(self):
        """
        Update an object ACL in bucket without Authentication.

        when AllUsers have FULL_CONTROL permission on object
        """
        self.log.info("Started:Update an object ACL in bucket without Authentication "
                      "when AllUsers have FULL_CONTROL permission on object")
        self.log.info("Step 1: Changing object's acl to FULL_CONTROL for all users")
        self.put_object_acl("grant_full_control")
        self.log.info("Step 1: Changed object's acl to FULL_CONTROL for all users")
        self.verify_obj_acl_edit("FULL_CONTROL")
        self.log.info("Step 3: Update object acl from that bucket using unsigned account")
        self.put_object_acl("grant_write_acp")
        self.log.info("Step 3: Changed object's acl to FULL_CONTROL for all users")
        self.log.info("Step 4: Verifying that object's acl is changed")
        resp = poll(self.acl_obj.get_object_acl, self.bucket_name, self.obj_name,
                    condition="{}[1]['Grants'][0]['Permission']=='WRITE_ACP'")
        assert resp[0], resp[1]
        assert resp[1]["Grants"][0]["Permission"] == "WRITE_ACP", resp[1]
        self.log.info("Step 4: Verified that object's acl is changed")
        self.log.info("ENDED:Update an object ACL in bucket without Authentication "
                      "when AllUsers have FULL_CONTROL permission on object")
