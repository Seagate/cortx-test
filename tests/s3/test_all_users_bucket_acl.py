#!/usr/bin/python
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
"""All User Bucket ACL test module."""
import os
import logging
import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils.assert_utils import assert_true
from commons.utils.assert_utils import assert_in
from commons.utils.assert_utils import assert_false
from commons.utils.assert_utils import assert_equal
from commons.utils.assert_utils import assert_not_in
from commons.utils import system_utils
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_test_lib import S3LibNoAuth
from libs.s3.s3_acl_test_lib import S3AclTestLib

S3_TEST_OBJ = S3TestLib()
ACL_OBJ = S3AclTestLib()
NO_AUTH_OBJ = S3LibNoAuth()
ALL_USERS_CFG = read_yaml("config/s3/test_all_users_bucket_acl.yaml")[1]


class TestAllUsers:
    """All Users Testsuite"""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.test_file = "all_users.txt"
        cls.test_dir_path = os.path.join(
            os.getcwd(), "testdata", "TestAllUsers")
        cls.test_file_path = os.path.join(cls.test_dir_path, cls.test_file)
        if not os.path.exists(cls.test_dir_path):
            os.makedirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.log.info("Test file path: %s", cls.test_file_path)
        cls.log.info("ENDED: setup test suite operations.")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        cls.log.info("STARTED: teardown test suite operations.")
        if system_utils.path_exists(cls.test_dir_path):
            system_utils.remove_dirs(cls.test_dir_path)
        cls.log.info("Cleanup test directory: %s", cls.test_dir_path)
        cls.log.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        This function will be invoked before running each test case.

        It will perform all prerequisite steps required for test execution.
        """
        self.log.info("STARTED: Setup operations")
        if system_utils.path_exists(self.test_file_path):
            system_utils.remove_file(self.test_file_path)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        This function will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        self.log.info("STARTED: Teardown operations")
        bucket_list = S3_TEST_OBJ.bucket_list()[1]
        all_users_buckets = [
            bucket for bucket in bucket_list if ALL_USERS_CFG["all_users"]["bkt_name_prefix"] in bucket]
        for bucket in all_users_buckets:
            ACL_OBJ.put_bucket_acl(
                bucket,
                grant_full_control=ALL_USERS_CFG["all_users"]["group_uri"])
        if all_users_buckets:
            resp = S3_TEST_OBJ.delete_multiple_buckets(all_users_buckets)
            assert_true(resp[0], resp[1])
        self.log.info("ENDED: Teardown operations")

    def create_bucket_put_object(
            self,
            bucket_name,
            obj_name,
            file_path,
            mb_count):
        """
        This function creates a bucket and uploads an object to the bucket.
        :param bucket_name: Name of bucket to be created
        :param obj_name: Name of an object to be put to the bucket
        :param file_path: Path of the file to be created and uploaded to bucket
        :param mb_count: Size of file in MBs
        """
        self.log.info("Creating a bucket %s", bucket_name)
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        self.log.info("Created a bucket %s", bucket_name)
        system_utils.create_file(file_path, mb_count)
        self.log.info(
            "Uploading an object %s to bucket %s", obj_name, bucket_name)
        resp = S3_TEST_OBJ.put_object(bucket_name, obj_name, file_path)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Uploaded an object %s to bucket %s", obj_name, bucket_name)

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6094')
    @CTFailOn(error_handler)
    def test_375(self):
        """Check listing of objects in bucket without Authentication
        when AllUsers have READ permission."""
        self.log.info(
            "STARTED: Check listing of objects in bucket without "
            "Authentication when AllUsers have READ permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_375"]["bucket_name"],
            ALL_USERS_CFG["test_375"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_375"]["bucket_name"],
            grant_read=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_375"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_375"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to list objects of a bucket from "
            "other unsigned user")
        resp = NO_AUTH_OBJ.object_list(
            ALL_USERS_CFG["test_375"]["bucket_name"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 4: Listed objects of a bucket from other "
            "unsigned user successfully")
        self.log.info(
            "ENDED: Check listing of objects in bucket without Authentication"
            " when AllUsers have READ permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6092')
    @CTFailOn(error_handler)
    def test_376(self):
        """Put an object in bucket without Authentication when AllUsers have READ permission."""
        self.log.info(
            "STARTED: Put an object in bucket without Authentication"
            " when AllUsers have READ permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_376"]["bucket_name"],
            ALL_USERS_CFG["test_376"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_376"]["bucket_name"],
            grant_read=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_376"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_376"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to put an object to a bucket "
            "from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.put_object(
                ALL_USERS_CFG["test_376"]["bucket_name"],
                ALL_USERS_CFG["test_376"]["new_obj_name"],
                self.test_file_path)
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_376"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Putting an object to bucket from other unsigned"
            " user is failed")
        self.log.info(
            "ENDED: Put an object in bucket without Authentication when"
            " AllUsers have READ permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6090')
    @CTFailOn(error_handler)
    def test_377(self):
        """Delete an object from bucket without Authentication
        when AllUsers have READ permission."""
        self.log.info(
            "STARTED: Delete an object from bucket without Authentication "
            "when AllUsers have READ permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_377"]["bucket_name"],
            ALL_USERS_CFG["test_377"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_377"]["bucket_name"],
            grant_read=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_377"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_377"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to delete an object from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.delete_object(
                ALL_USERS_CFG["test_377"]["bucket_name"],
                ALL_USERS_CFG["test_377"]["obj_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_377"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Deleting object from other unsigned user failed")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication "
            "when AllUsers have READ permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6088')
    @CTFailOn(error_handler)
    def test_378(self):
        """Read an object ACL from bucket without Authentication
        when AllUsers have READ permission."""
        self.log.info(
            "STARTED: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_378"]["bucket_name"],
            ALL_USERS_CFG["test_378"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_378"]["bucket_name"],
            grant_read=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_378"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_378"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to read an object's ACL from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.get_object_acl(
                ALL_USERS_CFG["test_378"]["bucket_name"],
                ALL_USERS_CFG["test_378"]["obj_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_378"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading object's ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6086')
    @CTFailOn(error_handler)
    def test_379(self):
        """Read a bucket ACL of a bucket without Authentication
        when AllUsers have READ permission."""
        self.log.info(
            "STARTED: Read a bucket ACL of a bucket without Authentication "
            "when AllUsers have READ permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_379"]["bucket_name"],
            ALL_USERS_CFG["test_379"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_379"]["bucket_name"],
            grant_read=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_379"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_379"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Reading bucket's ACL from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.get_bucket_acl(
                ALL_USERS_CFG["test_379"]["bucket_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_379"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading bucket's ACL from other unsigned user failed")
        self.log.info(
            "ENDED: Read a bucket ACL of a bucket without Authentication "
            "when AllUsers have READ permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6084')
    @CTFailOn(error_handler)
    def test_380(self):
        """Update a bucket ACL for a bucket without Authentication
        when AllUsers have READ permission."""
        self.log.info(
            "STARTED: Update a bucket ACL for a bucket without Authentication "
            "when AllUsers have READ permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_380"]["bucket_name"],
            ALL_USERS_CFG["test_380"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_380"]["bucket_name"],
            grant_read=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_380"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_380"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Updating bucket ACL from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.put_bucket_acl(
                ALL_USERS_CFG["test_380"]["bucket_name"],
                acl=ALL_USERS_CFG["test_380"]["acl"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_380"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Updating bucket ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Update a bucket ACL for a bucket without Authentication "
            "when AllUsers have READ permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6082')
    @CTFailOn(error_handler)
    def test_381(self):
        """Update an object ACL from bucket without Authentication
                when AllUsers have READ permission."""
        self.log.info(
            "STARTED: Update an object ACL from bucket without Authentication "
            "when AllUsers have READ permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_381"]["bucket_name"],
            ALL_USERS_CFG["test_381"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_381"]["bucket_name"],
            grant_read=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_381"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_381"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Updating object's ACL from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.put_object_canned_acl(
                ALL_USERS_CFG["test_381"]["bucket_name"],
                ALL_USERS_CFG["test_381"]["obj_name"],
                acl=ALL_USERS_CFG["test_381"]["acl"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_381"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Updating object's ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Update an object ACL from bucket without Authentication"
            " when AllUsers have READ permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6080')
    @CTFailOn(error_handler)
    def test_382(self):
        """Listing of objects in bucket without Authentication
        when AllUsers have WRITE permission."""
        self.log.info(
            "STARTED: Listing of objects in bucket without Authentication "
            "when AllUsers have WRITE permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_382"]["bucket_name"],
            ALL_USERS_CFG["test_382"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_382"]["bucket_name"],
            grant_write=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_382"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_382"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Listing objects in bucket from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.object_list(
                ALL_USERS_CFG["test_382"]["bucket_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_382"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Listing objects in bucket from other unsigned user is failed")
        self.log.info(
            "ENDED: Listing of objects in bucket without Authentication when"
            " AllUsers have WRITE permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6078')
    @CTFailOn(error_handler)
    def test_383(self):
        """Create an object in bucket without Authentication
        when AllUsers have WRITE permission."""
        self.log.info(
            "STARTED: Create an object in bucket without Authentication when "
            "AllUsers have WRITE permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_383"]["bucket_name"],
            ALL_USERS_CFG["test_383"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_383"]["bucket_name"],
            grant_write=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_383"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_383"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Putting an object in the bucket from other unsigned user")
        resp = NO_AUTH_OBJ.put_object(
            ALL_USERS_CFG["test_383"]["bucket_name"],
            ALL_USERS_CFG["test_383"]["new_obj_name"],
            self.test_file_path)
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 4: An object %s is put to bucket %s successfully",
            ALL_USERS_CFG["test_383"]["new_obj_name"],
            ALL_USERS_CFG["test_383"]["bucket_name"])
        self.log.info("Step 5: Setting the bucket ACL to 'private'")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_383"]["bucket_name"],
            acl=ALL_USERS_CFG["test_383"]["acl"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 5: Bucket ACL is set to 'private' successfully")
        self.log.info(
            "Step 6: Reading objects of bucket %s",
            ALL_USERS_CFG["test_383"]["bucket_name"])
        resp = S3_TEST_OBJ.object_list(
            ALL_USERS_CFG["test_383"]["bucket_name"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 6: Read objects of bucket %s successfully",
            ALL_USERS_CFG["test_383"]["bucket_name"])
        self.log.info(
            "ENDED: Create an object in bucket without Authentication when "
            "AllUsers have WRITE permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6076')
    @CTFailOn(error_handler)
    def test_384(self):
        """Delete an object from bucket without Authentication
        when AllUsers have WRITE permission."""
        self.log.info(
            "STARTED: Delete an object from bucket without Authentication when"
            " AllUsers have WRITE permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_384"]["bucket_name"],
            ALL_USERS_CFG["test_384"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_384"]["bucket_name"],
            grant_write=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_384"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_384"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Deleting an object of a bucket from other unsigned user")
        resp = NO_AUTH_OBJ.delete_object(
            ALL_USERS_CFG["test_384"]["bucket_name"],
            ALL_USERS_CFG["test_384"]["obj_name"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 4: Deleted an object of a bucket from other"
            "unsigned user successfully")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication when "
            "AllUsers have WRITE permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6074')
    @CTFailOn(error_handler)
    def test_385(self):
        """Read an object ACL from bucket without Authentication
        when AllUsers have WRITE permission."""
        self.log.info(
            "STARTED: Read an object ACL from bucket without Authentication"
            " when AllUsers have WRITE permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_385"]["bucket_name"],
            ALL_USERS_CFG["test_385"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_385"]["bucket_name"],
            grant_write=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_385"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_385"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Reading an object ACL from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.get_object_acl(
                ALL_USERS_CFG["test_385"]["bucket_name"],
                ALL_USERS_CFG["test_385"]["obj_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_385"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading an object ACL from other unsigned user failed")
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have WRITE permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6072')
    @CTFailOn(error_handler)
    def test_386(self):
        """Read a bucket ACL from bucket without Authentication
        when AllUsers have WRITE permission."""
        self.log.info(
            "STARTED: Read a bucket ACL from bucket without Authentication"
            " when AllUsers have WRITE permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_386"]["bucket_name"],
            ALL_USERS_CFG["test_386"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_386"]["bucket_name"],
            grant_write=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_386"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_386"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Reading bucket ACL from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.get_bucket_acl(
                ALL_USERS_CFG["test_386"]["bucket_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_386"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 3: Reading bucket ACL from other unsigned user failed")
        self.log.info(
            "ENDED: Read a bucket ACL from bucket without Authentication"
            " when AllUsers have WRITE permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6070')
    @CTFailOn(error_handler)
    def test_387(self):
        """Update a bucket ACL from bucket without Authentication
        when AllUsers have WRITE permission."""
        self.log.info(
            "STARTED: Update a bucket ACL from bucket without Authentication"
            " when AllUsers have WRITE permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_387"]["bucket_name"],
            ALL_USERS_CFG["test_387"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_387"]["bucket_name"],
            grant_write=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_387"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_387"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to change bucket ACL to private from "
            "other unsigned user")
        try:
            resp = NO_AUTH_OBJ.put_bucket_acl(
                ALL_USERS_CFG["test_387"]["bucket_name"],
                acl=ALL_USERS_CFG["test_387"]["acl"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_387"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Changing bucket ACL to private from "
            "other unsigned user is failed")
        self.log.info(
            "ENDED: Update a bucket ACL from bucket without Authentication "
            "when AllUsers have WRITE permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6068')
    @CTFailOn(error_handler)
    def test_388(self):
        """Update an object ACL from bucket without Authentication
        when AllUsers have WRITE permission."""
        self.log.info(
            "STARTED: Update an object ACL from bucket without Authentication "
            "when AllUsers have WRITE permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_388"]["bucket_name"],
            ALL_USERS_CFG["test_388"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_388"]["bucket_name"],
            grant_write=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_388"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_388"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to change object ACL from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.put_object_canned_acl(
                ALL_USERS_CFG["test_388"]["bucket_name"],
                ALL_USERS_CFG["test_388"]["obj_name"],
                acl=ALL_USERS_CFG["test_388"]["acl"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_388"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Changing object ACL to private from "
            "other unsigned user is failed")
        self.log.info(
            "ENDED: Update an object ACL from bucket without Authentication"
            " when AllUsers have WRITE permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6066')
    @CTFailOn(error_handler)
    def test_389(self):
        """Check listing of objects in bucket without Authentication
        when AllUsers have READ_ACP permission."""
        self.log.info(
            "STARTED: Check listing of objects in bucket without Authentication"
            " when AllUsers have READ_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_389"]["bucket_name"],
            ALL_USERS_CFG["test_389"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_389"]["bucket_name"],
            grant_read_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_389"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_389"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Get list of objects from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.object_list(
                ALL_USERS_CFG["test_389"]["bucket_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_389"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Get list of objects from other unsigned user failed")
        self.log.info(
            "ENDED: Check listing of objects in bucket without Authentication"
            " when AllUsers have READ_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6064')
    @CTFailOn(error_handler)
    def test_390(self):
        """Create an object in bucket without Authentication
        when AllUsers have READ_ACP permission."""
        self.log.info(
            "STARTED: Create an object in bucket without Authentication"
            " when AllUsers have READ_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_390"]["bucket_name"],
            ALL_USERS_CFG["test_390"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_390"]["bucket_name"],
            grant_read_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_390"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_390"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to upload an object from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.put_object(
                ALL_USERS_CFG["test_390"]["bucket_name"],
                ALL_USERS_CFG["test_390"]["new_obj_name"],
                self.test_file_path)
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_390"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Uploading object from other unsigned user failed")
        self.log.info(
            "ENDED: Create an object in bucket without Authentication "
            "when AllUsers have READ_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6062')
    @CTFailOn(error_handler)
    def test_391(self):
        """Delete an object from bucket without Authentication
        when AllUsers have READ_ACP permission."""
        self.log.info(
            "STARTED: Delete an object from bucket without Authentication "
            "when AllUsers have READ_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_391"]["bucket_name"],
            ALL_USERS_CFG["test_391"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_391"]["bucket_name"],
            grant_read_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_391"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_391"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4:Trying to delete existing object from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.delete_object(
                ALL_USERS_CFG["test_391"]["bucket_name"],
                ALL_USERS_CFG["test_391"]["obj_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_391"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Deleting existing object from other unsigned user failed")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication "
            "when AllUsers have READ_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6060')
    @CTFailOn(error_handler)
    def test_392(self):
        """Read an object ACL from bucket without Authentication
        when AllUsers have READ_ACP permission."""
        self.log.info(
            "STARTED: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_392"]["bucket_name"],
            ALL_USERS_CFG["test_392"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_392"]["bucket_name"],
            grant_read_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_392"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_392"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to read existing object's ACL from"
            " other unsigned user")
        try:
            resp = NO_AUTH_OBJ.get_object_acl(
                ALL_USERS_CFG["test_392"]["bucket_name"],
                ALL_USERS_CFG["test_392"]["obj_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_392"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading object's ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication"
            " when AllUsers have READ_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6058')
    @CTFailOn(error_handler)
    def test_393(self):
        """Read a bucket ACL from bucket without Authentication
        when AllUsers have READ_ACP permission."""
        self.log.info(
            "STARTED: Read a bucket ACL from bucket without Authentication"
            " when AllUsers have READ_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_393"]["bucket_name"],
            ALL_USERS_CFG["test_393"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_393"]["bucket_name"],
            grant_read_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_393"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_393"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to read bucket's ACL from other unsigned user")
        resp = NO_AUTH_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_393"]["bucket_name"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 4: Read bucket's ACL from other unsigned user successfully")
        self.log.info(
            "ENDED: Read a bucket ACL from bucket without Authentication when"
            " AllUsers have READ_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6056')
    @CTFailOn(error_handler)
    def test_394(self):
        """Update a bucket ACL from bucket without Authentication
        when AllUsers have READ_ACP permission."""
        self.log.info(
            "STARTED: Update a bucket ACL from bucket without Authentication"
            " when AllUsers have READ_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_394"]["bucket_name"],
            ALL_USERS_CFG["test_394"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_394"]["bucket_name"],
            grant_read_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_394"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_394"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to update bucket's ACL from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.put_bucket_acl(
                ALL_USERS_CFG["test_394"]["bucket_name"],
                acl=ALL_USERS_CFG["test_394"]["acl"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_394"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Updating bucket's ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Update a bucket ACL from bucket without Authentication"
            " when AllUsers have READ_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6054')
    @CTFailOn(error_handler)
    def test_395(self):
        """Update an object ACL from bucket without Authentication
        when AllUsers have READ_ACP permission."""
        self.log.info(
            "STARTED: Update an object ACL from bucket without Authentication "
            "when AllUsers have READ_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_395"]["bucket_name"],
            ALL_USERS_CFG["test_395"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_395"]["bucket_name"],
            grant_read_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_395"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_395"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to update object's ACL from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.put_object_canned_acl(
                ALL_USERS_CFG["test_395"]["bucket_name"],
                ALL_USERS_CFG["test_395"]["obj_name"],
                acl=ALL_USERS_CFG["test_395"]["acl"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_395"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Updating object's ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Update an object ACL from bucket without Authentication "
            "when AllUsers have READ_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6052')
    @CTFailOn(error_handler)
    def test_396(self):
        """Check listing of objects in bucket without Authentication
         when AllUsers have WRITE_ACP permission."""
        self.log.info(
            "STARTED: Check listing of objects in bucket without Authentication"
            " when AllUsers have WRITE_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_396"]["bucket_name"],
            ALL_USERS_CFG["test_396"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_396"]["bucket_name"],
            grant_write_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_396"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_396"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Getting list of objects in bucket from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.object_list(
                ALL_USERS_CFG["test_396"]["bucket_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_396"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Getting list of objects in bucket from other unsigned user failed")
        self.log.info(
            "ENDED: Check listing of objects in bucket without Authentication "
            "when AllUsers have WRITE_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6050')
    @CTFailOn(error_handler)
    def test_397(self):
        """Create an object in bucket without Authentication
        when AllUsers have WRITE_ACP permission."""
        self.log.info(
            "STARTED: Create an object in bucket without Authentication "
            "when AllUsers have WRITE_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_397"]["bucket_name"],
            ALL_USERS_CFG["test_397"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_397"]["bucket_name"],
            grant_write_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_397"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_397"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Uploading an object to a bucket from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.put_object(
                ALL_USERS_CFG["test_397"]["bucket_name"],
                ALL_USERS_CFG["test_397"]["new_obj_name"],
                self.test_file_path)
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_397"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Uploading an object to a bucket from other unsigned user is failed")
        self.log.info(
            "ENDED: Create an object in bucket without Authentication when "
            "AllUsers have WRITE_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6048')
    @CTFailOn(error_handler)
    def test_398(self):
        """Delete an object from bucket without Authentication
        when AllUsers have WRITE_ACP permission."""
        self.log.info(
            "STARTED: Delete an object from bucket without Authentication when "
            "AllUsers have WRITE_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_398"]["bucket_name"],
            ALL_USERS_CFG["test_398"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_398"]["bucket_name"],
            grant_write_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_398"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_398"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Deleting an object to a bucket from other unsigned user")
        try:
            resp = NO_AUTH_OBJ.delete_object(
                ALL_USERS_CFG["test_398"]["bucket_name"],
                ALL_USERS_CFG["test_398"]["obj_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_398"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Deleting an object from other unsigned user is failed")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication when "
            "AllUsers have WRITE_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6044')
    @CTFailOn(error_handler)
    def test_399(self):
        """Read an object ACL from bucket without Authentication
        when AllUsers have WRITE_ACP permission."""
        self.log.info(
            "STARTED: Read an object ACL from bucket without Authentication when "
            "AllUsers have WRITE_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_399"]["bucket_name"],
            ALL_USERS_CFG["test_399"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_399"]["bucket_name"],
            grant_write_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_399"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_399"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Reading object ACL through other unsigned account")
        try:
            resp = NO_AUTH_OBJ.get_object_acl(
                ALL_USERS_CFG["test_399"]["bucket_name"],
                ALL_USERS_CFG["test_399"]["obj_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_399"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading object ACL through other unsigned account failed")
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication when "
            "AllUsers have WRITE_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6042')
    @CTFailOn(error_handler)
    def test_400(self):
        """Read a bucket ACL from bucket without Authentication when AllUsers
         have WRITE_ACP permission."""
        self.log.info(
            "STARTED: Read a bucket ACL from bucket without Authentication "
            "when AllUsers have WRITE_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_400"]["bucket_name"],
            ALL_USERS_CFG["test_400"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_400"]["bucket_name"],
            grant_write_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_400"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_400"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Reading bucket ACL through other unsigned account")
        try:
            resp = NO_AUTH_OBJ.get_bucket_acl(
                ALL_USERS_CFG["test_400"]["bucket_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_400"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading bucket ACL through other unsigned account failed")
        self.log.info(
            "ENDED: Read a bucket ACL from bucket without Authentication "
            "when AllUsers have WRITE_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6040')
    @CTFailOn(error_handler)
    def test_401(self):
        """Update a bucket ACL from bucket without Authentication when
        AllUsers have WRITE_ACP permission."""
        self.log.info(
            "STARTED: Update a bucket ACL from bucket without Authentication"
            " when AllUsers have WRITE_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_401"]["bucket_name"],
            ALL_USERS_CFG["test_401"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_401"]["bucket_name"],
            grant_write_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_401"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_401"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Updating bucket ACL through other unsigned account")
        resp = NO_AUTH_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_401"]["bucket_name"],
            grant_full_control=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        resp = NO_AUTH_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_401"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_401"]["new_permission"],
            resp[1])
        self.log.info(
            "Step 4: Updated bucket ACL through from other unsigned"
            " user successfully")
        self.log.info(
            "ENDED: Update a bucket ACL from bucket without Authentication"
            " when AllUsers have WRITE_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6038')
    @CTFailOn(error_handler)
    def test_402(self):
        """Update an object ACL from bucket without Authentication when
        AllUsers have WRITE_ACP permission."""
        self.log.info(
            "STARTED: Update an object ACL from bucket without Authentication"
            " when AllUsers have WRITE_ACP permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_402"]["bucket_name"],
            ALL_USERS_CFG["test_402"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_402"]["bucket_name"],
            grant_write_acp=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_402"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_402"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Updating object ACL through other unsigned account")
        try:
            resp = NO_AUTH_OBJ.put_object_canned_acl(
                ALL_USERS_CFG["test_402"]["bucket_name"],
                ALL_USERS_CFG["test_402"]["obj_name"],
                acl=ALL_USERS_CFG["test_402"]["acl"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_402"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4:Updating object ACL through other unsigned account failed")
        self.log.info(
            "ENDED: Update an object ACL from bucket without Authentication"
            " when AllUsers have WRITE_ACP permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6036')
    @CTFailOn(error_handler)
    def test_403(self):
        """Listing of objects in bucket without Authentication when
         AllUsers have FULL_CONTROL permission."""
        self.log.info(
            "STARTED: Listing of objects in bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_403"]["bucket_name"],
            ALL_USERS_CFG["test_403"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_403"]["bucket_name"],
            grant_full_control=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_403"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_403"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Listing objects in bucket through other unsigned account")
        resp = NO_AUTH_OBJ.object_list(
            ALL_USERS_CFG["test_403"]["bucket_name"])
        assert_true(resp[0], resp[1])
        assert_in(
            ALL_USERS_CFG["test_403"]["obj_name"], str(
                resp[1]), resp[1])
        self.log.info(
            "Step 4: Listed objects in bucket through other "
            "unsigned account successfully")
        self.log.info(
            "ENDED: Listing of objects in bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6033')
    @CTFailOn(error_handler)
    def test_404(self):
        """Put an object in bucket without Authentication when AllUsers
        have FULL_CONTROL permission."""
        self.log.info(
            "STARTED: Put an object in bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_404"]["bucket_name"],
            ALL_USERS_CFG["test_404"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_404"]["bucket_name"],
            grant_full_control=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_404"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_404"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4:Uploading object in bucket through other unsigned account")
        resp = NO_AUTH_OBJ.put_object(
            ALL_USERS_CFG["test_404"]["bucket_name"],
            ALL_USERS_CFG["test_404"]["new_obj_name"],
            self.test_file_path)
        assert_true(resp[0], resp[1])
        resp = NO_AUTH_OBJ.object_list(
            ALL_USERS_CFG["test_404"]["bucket_name"])
        assert_in(
            ALL_USERS_CFG["test_404"]["new_obj_name"], str(
                resp[1]), resp[1])
        self.log.info(
            "Step 4: Uploaded object in bucket through other "
            "unsigned account successfully")
        self.log.info(
            "ENDED: Put an object in bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6031')
    @CTFailOn(error_handler)
    def test_405(self):
        """Delete an object from bucket without Authentication when AllUsers
         have FULL_CONTROL permission."""
        self.log.info(
            "STARTED: Delete an object from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_405"]["bucket_name"],
            ALL_USERS_CFG["test_405"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_405"]["bucket_name"],
            grant_full_control=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_405"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_405"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4:Deleting obj from bucket through other unsigned account")
        resp = NO_AUTH_OBJ.delete_object(
            ALL_USERS_CFG["test_405"]["bucket_name"],
            ALL_USERS_CFG["test_405"]["obj_name"])
        assert_true(resp[0], resp[1])
        resp = NO_AUTH_OBJ.object_list(
            ALL_USERS_CFG["test_405"]["bucket_name"])
        assert_not_in(
            ALL_USERS_CFG["test_405"]["obj_name"],
            str(resp[1]), resp[1])
        self.log.info(
            "Step 4:Deleted object from bucket through other unsigned account")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication when"
            " AllUsers have FULL_CONTROL permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6029')
    @CTFailOn(error_handler)
    def test_406(self):
        """Read an object ACL from bucket without Authentication when
        AllUsers have FULL_CONTROL permission."""
        self.log.info(
            "STARTED: Read an object ACL from bucket without Authentication"
            " when AllUsers have FULL_CONTROL permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_406"]["bucket_name"],
            ALL_USERS_CFG["test_406"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_406"]["bucket_name"],
            grant_full_control=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_406"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_406"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Reading object ACL through other unsigned account")
        try:
            resp = NO_AUTH_OBJ.get_object_acl(
                ALL_USERS_CFG["test_406"]["bucket_name"],
                ALL_USERS_CFG["test_406"]["obj_name"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_406"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading object ACL through other unsigned account failed")
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication when"
            " AllUsers have FULL_CONTROL permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6026')
    @CTFailOn(error_handler)
    def test_407(self):
        """Read a bucket ACL from bucket without Authentication when AllUsers
         have FULL_CONTROL permission"""
        self.log.info(
            "STARTED: Read a bucket ACL from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_407"]["bucket_name"],
            ALL_USERS_CFG["test_407"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_407"]["bucket_name"],
            grant_full_control=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_407"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_407"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Reading bucket ACL through other unsigned account")
        resp = NO_AUTH_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_407"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_407"]["permission"],
            resp[1])
        self.log.info(
            "Step 4: Read bucket ACL through other unsigned "
            "account successfully")
        self.log.info(
            "ENDED: Read a bucket ACL from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6024')
    @CTFailOn(error_handler)
    def test_408(self):
        """Update a bucket ACL from bucket without Authentication
        when AllUsers have FULL_CONTROL permission."""
        self.log.info(
            "STARTED: Update a bucket ACL from bucket without Authentication"
            " when AllUsers have FULL_CONTROL permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_408"]["bucket_name"],
            ALL_USERS_CFG["test_408"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_408"]["bucket_name"],
            grant_full_control=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_408"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_408"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Updating bucket ACL through other unsigned account")
        resp = NO_AUTH_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_408"]["bucket_name"],
            acl=ALL_USERS_CFG["test_408"]["acl"])
        assert_true(resp[0], resp[1])
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_408"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_408"]["permission"],
            resp[1])
        self.log.info(
            "Step 4: Updated bucket ACL through other unsigned"
            " account successfully")
        self.log.info(
            "ENDED: Update a bucket ACL from bucket without Authentication"
            " when AllUsers have FULL_CONTROL permission")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-6021')
    @CTFailOn(error_handler)
    def test_409(self):
        """Update an object ACL from bucket without Authentication
        when AllUsers have FULL_CONTROL permission."""
        self.log.info(
            "STARTED: Update an object ACL from bucket without Authentication"
            " when AllUsers have FULL_CONTROL permission")
        self.log.info(
            "Step 1: Creating a bucket and uploading an object to bucket")
        self.create_bucket_put_object(
            ALL_USERS_CFG["test_409"]["bucket_name"],
            ALL_USERS_CFG["test_409"]["obj_name"],
            self.test_file_path,
            ALL_USERS_CFG["all_users"]["mb_count"])
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = ACL_OBJ.put_bucket_acl(
            ALL_USERS_CFG["test_409"]["bucket_name"],
            grant_full_control=ALL_USERS_CFG["all_users"]["group_uri"])
        assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = ACL_OBJ.get_bucket_acl(
            ALL_USERS_CFG["test_409"]["bucket_name"])
        assert_equal(
            resp[1][1][0]["Permission"],
            ALL_USERS_CFG["test_409"]["permission"],
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Updating object ACL through other unsigned account")
        try:
            resp = NO_AUTH_OBJ.put_object_canned_acl(
                ALL_USERS_CFG["test_409"]["bucket_name"],
                ALL_USERS_CFG["test_409"]["obj_name"],
                acl=ALL_USERS_CFG["test_409"]["acl"])
            assert_false(resp[0], resp[1])
        except CTException as error:
            assert_in(
                ALL_USERS_CFG["test_409"]["err_message"],
                error.message,
                error.message)
        self.log.info(
            "Step 4: Updating object ACL through other "
            "unsigned account failed")
        self.log.info(
            "ENDED: Update an object ACL from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")
