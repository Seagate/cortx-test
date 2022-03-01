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
"""All User Bucket ACL test module."""

import os
import logging
import time

import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils import s3_utils
from config.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_test_lib import S3LibNoAuth
from libs.s3.s3_acl_test_lib import S3AclTestLib


class TestAllUsersBucketAcl:
    """All Users bucket Acl Testsuite."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: setup test suite operations.")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.acl_obj = S3AclTestLib(endpoint_url=S3_CFG["s3_url"])
        self.no_auth_obj = S3LibNoAuth(endpoint_url=S3_CFG["s3_url"])
        self.test_file = "all_users{}.txt".format(time.perf_counter_ns())
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestAllUsersBucketAcl")
        self.test_file_path = os.path.join(self.test_dir_path, self.test_file)
        if not os.path.exists(self.test_dir_path):
            os.makedirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.log.info("Test file path: %s", self.test_file_path)
        self.mb_count = 5
        self.group_uri = "uri=http://acs.amazonaws.com/groups/global/AllUsers"
        self.log.info("ENDED: setup test suite operations.")
        self.bucket_name = "allusersbktacl-bkt{}".format(time.perf_counter_ns())
        self.obj_name = "testobj{}".format(time.perf_counter_ns())
        self.new_obj_name = "newtestobj{}".format(time.perf_counter_ns())
        self.log.info("ENDED: Setup operations")
        yield
        self.log.info("STARTED: Teardown operations")
        if system_utils.path_exists(self.test_file_path):
            system_utils.remove_file(self.test_file_path)
        bucket_list = self.s3_test_obj.bucket_list()[1]
        if self.bucket_name in bucket_list:
            self.acl_obj.put_bucket_acl(
                self.bucket_name,
                grant_full_control=self.group_uri
            )
            resp = self.s3_test_obj.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
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
        resp = self.s3_test_obj.create_bucket(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Created a bucket %s", bucket_name)
        system_utils.create_file(file_path, mb_count)
        self.log.info(
            "Uploading an object %s to bucket %s", obj_name, bucket_name
        )
        resp = self.s3_test_obj.put_object(bucket_name, obj_name, file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Uploaded an object %s to bucket %s", obj_name, bucket_name
        )

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
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
            self.bucket_name, self.obj_name, self.test_file_path, self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = self.acl_obj.put_bucket_acl(self.bucket_name, grant_read=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = s3_utils.poll(self.acl_obj.get_bucket_acl,
                             self.bucket_name, condition='{}[1][1][0]["Permission"]=="READ"')
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][1][0]["Permission"], "READ", resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Trying to list objects of a bucket from other unsigned user")
        resp = s3_utils.poll(self.no_auth_obj.object_list, self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Listed objects of a bucket from other unsigned user successfully")
        self.log.info(
            "ENDED: Check listing of objects in bucket without Authentication"
            " when AllUsers have READ permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags('TEST-6092')
    @CTFailOn(error_handler)
    def test_376(self):
        """Put an object in bucket without Authentication when AllUsers have READ permission."""
        self.log.info(
            "STARTED: Put an object in bucket without Authentication"
            " when AllUsers have READ permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(self.bucket_name, self.obj_name,
                                      self.test_file_path,
                                      self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = self.acl_obj.put_bucket_acl(self.bucket_name,
                                           grant_read=self.group_uri
                                           )
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "READ",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to put an object to a bucket "
            "from other unsigned user")
        try:
            resp = self.no_auth_obj.put_object(self.bucket_name, "testobj",
                                               self.test_file_path
                                               )
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Putting an object to bucket from other unsigned"
            " user is failed")
        self.log.info(
            "ENDED: Put an object in bucket without Authentication when"
            " AllUsers have READ permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags('TEST-6090')
    @CTFailOn(error_handler)
    def test_377(self):
        """Delete an object from bucket without Authentication
        when AllUsers have READ permission."""
        self.log.info(
            "STARTED: Delete an object from bucket without Authentication "
            "when AllUsers have READ permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(self.bucket_name, self.obj_name,
                                      self.test_file_path,
                                      self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = self.acl_obj.put_bucket_acl(self.bucket_name,
                                           grant_read=self.group_uri
                                           )
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "READ",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to delete an object from other unsigned user")
        try:
            resp = self.no_auth_obj.delete_object(
                self.bucket_name, self.obj_name
            )
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Deleting object from other unsigned user failed")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication "
            "when AllUsers have READ permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.tags('TEST-6088')
    @CTFailOn(error_handler)
    def test_378(self):
        """Read an object ACL from bucket without Authentication
        when AllUsers have READ permission."""
        self.log.info(
            "STARTED: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ permission")
        self.log.info("Step 1: Creating a bucket and uploading an object")
        self.create_bucket_put_object(self.bucket_name, self.obj_name,
                                      self.test_file_path,
                                      self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = self.acl_obj.put_bucket_acl(self.bucket_name,
                                           grant_read=self.group_uri
                                           )
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = s3_utils.poll(self.acl_obj.get_bucket_acl,
                             self.bucket_name, condition='{}[1][1][0]["Permission"]=="READ"')
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][1][0]["Permission"], "READ", resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Trying to read an object's ACL from other unsigned user")
        try:
            resp = self.no_auth_obj.get_object_acl(
                self.bucket_name, self.obj_name
            )
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading object's ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have READ permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_read=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name
        )
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "READ",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Reading bucket's ACL from other unsigned user")
        try:
            resp = self.no_auth_obj.get_bucket_acl(
                self.bucket_name
            )
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading bucket's ACL from other unsigned user failed")
        self.log.info(
            "ENDED: Read a bucket ACL of a bucket without Authentication "
            "when AllUsers have READ permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_read=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name
        )
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "READ",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Updating bucket ACL from other unsigned user")
        try:
            resp = self.no_auth_obj.put_bucket_acl(
                self.bucket_name,
                acl="private")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Updating bucket ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Update a bucket ACL for a bucket without Authentication "
            "when AllUsers have READ permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers READ")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_read=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = s3_utils.poll(self.acl_obj.get_bucket_acl,
                             self.bucket_name, condition='{}[1][1][0]["Permission"]=="READ"')
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][1][0]["Permission"], "READ", resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Updating object's ACL from other unsigned user")
        try:
            resp = self.no_auth_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                acl="private")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Updating object's ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Update an object ACL from bucket without Authentication"
            " when AllUsers have READ permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = s3_utils.poll(self.acl_obj.get_bucket_acl,
                             self.bucket_name, condition='{}[1][1][0]["Permission"]=="WRITE"')
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][1][0]["Permission"], "WRITE", resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Listing objects in bucket from other unsigned user")
        try:
            resp = self.no_auth_obj.object_list(
                self.bucket_name
            )
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Listing objects in bucket from other unsigned user is failed")
        self.log.info(
            "ENDED: Listing of objects in bucket without Authentication when"
            " AllUsers have WRITE permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = self.acl_obj.put_bucket_acl(self.bucket_name, grant_write=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = s3_utils.poll(self.acl_obj.get_bucket_acl,
                             self.bucket_name, condition='{}[1][1][0]["Permission"]=="WRITE"')
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][1][0]["Permission"], "WRITE", resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Putting an object in the bucket from other unsigned user")
        resp = s3_utils.poll(self.no_auth_obj.put_object,
                             self.bucket_name,
                             self.new_obj_name,
                             self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 4: An object %s is put to bucket %s successfully",
            self.new_obj_name,
            self.bucket_name)
        self.log.info("Step 5: Setting the bucket ACL to 'private'")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Bucket ACL is set to 'private' successfully")
        self.log.info("Step 6: Reading objects of bucket %s", self.bucket_name)
        resp = s3_utils.poll(self.s3_test_obj.object_list, self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Read objects of bucket %s successfully", self.bucket_name)
        self.log.info(
            "ENDED: Create an object in bucket without Authentication when "
            "AllUsers have WRITE permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
    @pytest.mark.regression
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
            self.bucket_name, self.obj_name, self.test_file_path, self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = self.acl_obj.put_bucket_acl(self.bucket_name, grant_write=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = s3_utils.poll(self.acl_obj.get_bucket_acl,
                             self.bucket_name, condition='{}[1][1][0]["Permission"]=="WRITE"')
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1][1][0]["Permission"], "WRITE", resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Deleting an object of a bucket from other unsigned user")
        resp = s3_utils.poll(self.no_auth_obj.delete_object, self.bucket_name, self.obj_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Deleted an object of a bucket from other unsigned user successfully")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication when "
            "AllUsers have WRITE permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "WRITE",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Reading an object ACL from other unsigned user")
        try:
            resp = self.no_auth_obj.get_object_acl(
                self.bucket_name,
                self.obj_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading an object ACL from other unsigned user failed")
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication "
            "when AllUsers have WRITE permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info("Step 1: Created a bucket and uploaded an object")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "WRITE",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Reading bucket ACL from other unsigned user")
        try:
            resp = self.no_auth_obj.get_bucket_acl(
                self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 3: Reading bucket ACL from other unsigned user failed")
        self.log.info(
            "ENDED: Read a bucket ACL from bucket without Authentication"
            " when AllUsers have WRITE permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "WRITE",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to change bucket ACL to private from "
            "other unsigned user")
        try:
            resp = self.no_auth_obj.put_bucket_acl(
                self.bucket_name,
                acl="private")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Changing bucket ACL to private from "
            "other unsigned user is failed")
        self.log.info(
            "ENDED: Update a bucket ACL from bucket without Authentication "
            "when AllUsers have WRITE permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info("Step 2: Changing bucket permission to AllUsers WRITE")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers WRITE")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "WRITE",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to change object ACL from other unsigned user")
        try:
            resp = self.no_auth_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                acl="private")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Changing object ACL to private from "
            "other unsigned user is failed")
        self.log.info(
            "ENDED: Update an object ACL from bucket without Authentication"
            " when AllUsers have WRITE permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_read_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "READ_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info("Step 4: Get list of objects from other unsigned user")
        try:
            resp = self.no_auth_obj.object_list(
                self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Get list of objects from other unsigned user failed")
        self.log.info(
            "ENDED: Check listing of objects in bucket without Authentication"
            " when AllUsers have READ_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_read_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "READ_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to upload an object from other unsigned user")
        try:
            resp = self.no_auth_obj.put_object(
                self.bucket_name,
                self.new_obj_name,
                self.test_file_path)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Uploading object from other unsigned user failed")
        self.log.info(
            "ENDED: Create an object in bucket without Authentication "
            "when AllUsers have READ_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_read_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "READ_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4:Trying to delete existing object from other unsigned user")
        try:
            resp = self.no_auth_obj.delete_object(
                self.bucket_name,
                self.obj_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Deleting existing object from other unsigned user failed")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication "
            "when AllUsers have READ_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_read_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "READ_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to read existing object's ACL from"
            " other unsigned user")
        try:
            resp = self.no_auth_obj.get_object_acl(
                self.bucket_name,
                self.obj_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading object's ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication"
            " when AllUsers have READ_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_read_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        time.sleep(S3_CFG["sync_delay"])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "READ_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to read bucket's ACL from other unsigned user")
        resp = self.no_auth_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 4: Read bucket's ACL from other unsigned user successfully")
        self.log.info(
            "ENDED: Read a bucket ACL from bucket without Authentication when"
            " AllUsers have READ_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_read_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "READ_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to update bucket's ACL from other unsigned user")
        try:
            resp = self.no_auth_obj.put_bucket_acl(
                self.bucket_name,
                acl="private")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Updating bucket's ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Update a bucket ACL from bucket without Authentication"
            " when AllUsers have READ_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers READ_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_read_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Changed bucket permission to AllUsers READ_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "READ_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Trying to update object's ACL from other unsigned user")
        try:
            resp = self.no_auth_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                acl="private")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Updating object's ACL from other unsigned user is failed")
        self.log.info(
            "ENDED: Update an object ACL from bucket without Authentication "
            "when AllUsers have READ_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "WRITE_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Getting list of objects in bucket from other unsigned user")
        try:
            resp = self.no_auth_obj.object_list(
                self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Getting list of objects in bucket from other unsigned user failed")
        self.log.info(
            "ENDED: Check listing of objects in bucket without Authentication "
            "when AllUsers have WRITE_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        time.sleep(S3_CFG["sync_delay"])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "WRITE_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Uploading an object to a bucket from other unsigned user")
        try:
            resp = self.no_auth_obj.put_object(
                self.bucket_name,
                self.new_obj_name,
                self.test_file_path)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Uploading an object to a bucket from other unsigned user is failed")
        self.log.info(
            "ENDED: Create an object in bucket without Authentication when "
            "AllUsers have WRITE_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "WRITE_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Deleting an object to a bucket from other unsigned user")
        try:
            resp = self.no_auth_obj.delete_object(
                self.bucket_name,
                self.obj_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Deleting an object from other unsigned user is failed")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication when "
            "AllUsers have WRITE_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "WRITE_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Reading object ACL through other unsigned account")
        try:
            resp = self.no_auth_obj.get_object_acl(
                self.bucket_name,
                self.obj_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading object ACL through other unsigned account failed")
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication when "
            "AllUsers have WRITE_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "WRITE_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Reading bucket ACL through other unsigned account")
        try:
            resp = self.no_auth_obj.get_bucket_acl(
                self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading bucket ACL through other unsigned account failed")
        self.log.info(
            "ENDED: Read a bucket ACL from bucket without Authentication "
            "when AllUsers have WRITE_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "WRITE_ACP",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Updating bucket ACL through other unsigned account")
        resp = self.no_auth_obj.put_bucket_acl(
            self.bucket_name,
            grant_full_control=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.no_auth_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info(
            "Step 4: Updated bucket ACL through from other unsigned"
            " user successfully")
        self.log.info(
            "ENDED: Update a bucket ACL from bucket without Authentication"
            " when AllUsers have WRITE_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers WRITE_ACP")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_write_acp=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers WRITE_ACP")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = s3_utils.poll(self.acl_obj.get_bucket_acl,
                             self.bucket_name, condition='{}[1][1][0]["Permission"]=="WRITE_ACP"')
        assert_utils.assert_equal(resp[1][1][0]["Permission"], "WRITE_ACP", resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Updating object ACL through other unsigned account")
        try:
            resp = self.no_auth_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                acl="private")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4:Updating object ACL through other unsigned account failed")
        self.log.info(
            "ENDED: Update an object ACL from bucket without Authentication"
            " when AllUsers have WRITE_ACP permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_full_control=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Listing objects in bucket through other unsigned account")
        resp = self.no_auth_obj.object_list(
            self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            self.obj_name, str(
                resp[1]), resp[1])
        self.log.info(
            "Step 4: Listed objects in bucket through other "
            "unsigned account successfully")
        self.log.info(
            "ENDED: Listing of objects in bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_full_control=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4:Uploading object in bucket through other unsigned account")
        resp = self.no_auth_obj.put_object(
            self.bucket_name,
            self.new_obj_name,
            self.test_file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.no_auth_obj.object_list(
            self.bucket_name)
        assert_utils.assert_in(
            self.new_obj_name, str(
                resp[1]), resp[1])
        self.log.info(
            "Step 4: Uploaded object in bucket through other "
            "unsigned account successfully")
        self.log.info(
            "ENDED: Put an object in bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_full_control=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4:Deleting obj from bucket through other unsigned account")
        resp = self.no_auth_obj.delete_object(
            self.bucket_name,
            self.obj_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.no_auth_obj.object_list(
            self.bucket_name)
        assert_utils.assert_not_in(
            self.obj_name,
            str(resp[1]), resp[1])
        self.log.info(
            "Step 4:Deleted object from bucket through other unsigned account")
        self.log.info(
            "ENDED: Delete an object from bucket without Authentication when"
            " AllUsers have FULL_CONTROL permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_full_control=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Reading object ACL through other unsigned account")
        try:
            resp = self.no_auth_obj.get_object_acl(
                self.bucket_name,
                self.obj_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Reading object ACL through other unsigned account failed")
        self.log.info(
            "ENDED: Read an object ACL from bucket without Authentication when"
            " AllUsers have FULL_CONTROL permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_full_control=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        time.sleep(S3_CFG["sync_delay"])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Reading bucket ACL through other unsigned account")
        resp = self.no_auth_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info(
            "Step 4: Read bucket ACL through other unsigned "
            "account successfully")
        self.log.info(
            "ENDED: Read a bucket ACL from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_full_control=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Updating bucket ACL through other unsigned account")
        resp = self.no_auth_obj.put_bucket_acl(
            self.bucket_name,
            acl="private")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info(
            "Step 4: Updated bucket ACL through other unsigned"
            " account successfully")
        self.log.info(
            "ENDED: Update a bucket ACL from bucket without Authentication"
            " when AllUsers have FULL_CONTROL permission")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_bucket_acl
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
            self.bucket_name,
            self.obj_name,
            self.test_file_path,
            self.mb_count)
        self.log.info(
            "Step 1: Created a bucket and uploaded an object to bucket")
        self.log.info(
            "Step 2: Changing bucket permission to AllUsers FULL_CONTROL")
        resp = self.acl_obj.put_bucket_acl(
            self.bucket_name,
            grant_full_control=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Changed bucket permission to AllUsers FULL_CONTROL")
        self.log.info("Step 3: Verifying bucket permission is changed")
        resp = self.acl_obj.get_bucket_acl(
            self.bucket_name)
        assert_utils.assert_equal(
            resp[1][1][0]["Permission"],
            "FULL_CONTROL",
            resp[1])
        self.log.info("Step 3: Verified bucket permission is changed")
        self.log.info(
            "Step 4: Updating object ACL through other unsigned account")
        try:
            resp = self.no_auth_obj.put_object_canned_acl(
                self.bucket_name,
                self.obj_name,
                acl="private")
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in(
                "AccessDenied",
                error.message,
                error.message)
        self.log.info(
            "Step 4: Updating object ACL through other "
            "unsigned account failed")
        self.log.info(
            "ENDED: Update an object ACL from bucket without Authentication "
            "when AllUsers have FULL_CONTROL permission")
