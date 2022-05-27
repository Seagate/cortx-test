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

"""Object Metadata Operations Test Module."""
import os
import random
import string
import logging
import time

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils.system_utils import create_file, remove_file, path_exists, make_dirs
from commons.utils.s3_utils import assert_s3_err_msg
from commons import error_messages as errmsg
from config.s3 import S3_OBJ_TST
from config.s3 import S3_CFG
from libs.s3 import s3_test_lib, CMN_CFG

# pylint: disable=too-many-instance-attributes

class TestObjectMetadataOperations:
    """"Object Metadata Operations Testsuite."""

    # pylint: disable=attribute-defined-outside-init
    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.s3_test_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.bkt_name_prefix = "obj-metadata"
        self.file_name = f"metadata{time.perf_counter_ns()}"
        self.folder_path = os.path.join(TEST_DATA_FOLDER, "TestObjectMetadataOperations")
        self.file_path = os.path.join(self.folder_path, self.file_name)
        self.new_file_path = f"new_objmetadata{time.perf_counter_ns()}"
        self.new_file_path = os.path.join(self.folder_path, self.new_file_path)
        self.object_name = f"metaobj{time.perf_counter_ns()}"
        self.bucket_name = f"metaobjbkt{time.perf_counter_ns()}"
        if not path_exists(self.folder_path):
            resp = make_dirs(self.folder_path)
            self.log.info("Created path: %s", resp)

    def teardown_method(self):
        """Teardown method."""
        self.log.info("STARTED: Setup/Teardown operations")
        self.s3_test_obj.delete_bucket(self.bucket_name, force=True)
        if os.path.exists(self.file_path):
            remove_file(
                self.file_path)
        self.log.info("ENDED: Setup/Teardown operations")

    def create_bucket_put_list_object(
            self,
            bucket_name,
            obj_name,
            file_path,
            mb_count,
            **kwargs):
        """
        Function creates a bucket, uploads an object.

        to the bucket and list objects from the bucket.
        :param bucket_name: Name of bucket to be created
        :param obj_name: Name of an object to be put to the bucket
        :param file_path: Path of the file to be created and uploaded to bucket
        :param mb_count: Size of file in MBs
        """
        m_key = kwargs.get("m_key", None)
        m_value = kwargs.get("m_value", None)
        self.log.info("Creating a bucket %s", bucket_name)
        resp = self.s3_test_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        self.log.info("Created a bucket %s", bucket_name)
        create_file(file_path, mb_count)
        self.log.info(
            "Uploading an object %s to bucket %s",
            obj_name, bucket_name)
        resp = self.s3_test_obj.put_object(
            bucket_name, obj_name, file_path, m_key=m_key, m_value=m_value)
        assert resp[0], resp[1]
        self.log.info(
            "Uploaded an object %s to bucket %s", obj_name, bucket_name)
        self.log.info("Listing objects from a bucket %s", bucket_name)
        resp = self.s3_test_obj.object_list(bucket_name)
        assert resp[0], resp[1]
        assert obj_name in resp[1], resp[1]
        self.log.info(
            "Objects are listed from a bucket %s", bucket_name)
        if m_key:
            self.log.info(
                "Retrieving metadata of an object %s", obj_name)
            resp = self.s3_test_obj.object_info(bucket_name, obj_name)
            assert resp[0], resp[1]
            assert m_key in resp[1]["Metadata"], resp[1]
            self.log.info(
                "Retrieved metadata of an object %s", obj_name)

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.sanity
    @pytest.mark.tags("TEST-5482")
    @CTFailOn(error_handler)
    def test_object_key_alphanumeric_chars_1983(self):
        """Create object key with alphanumeric characters."""
        self.log.info("Create object key with alphanumeric characters")
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Create object key with alphanumeric characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5478")
    @CTFailOn(error_handler)
    def test_object_valid_special_chars_1984(self):
        """Create object key with valid special characters."""
        self.log.info("Create object key with valid special characters")
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Create object key with valid special characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5480")
    @CTFailOn(error_handler)
    def test_key_alphanumeric_valid_special_chars_1985(self):
        """Create object key with combinations of alphanumeric and valid special characters."""
        self.log.info(
            "Create object key with combinations of alphanumeric and valid special characters")
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Create object key with combinations of alphanumeric and valid special characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5479")
    @CTFailOn(error_handler)
    def test_key_existing_object_key_1986(self):
        """Create object key with existing object key in the same bucket."""
        self.log.info(
            "Create object key with existing object key in the same bucket")
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"],
            m_key=S3_OBJ_TST["test_8546"]["key"],
            m_value=S3_OBJ_TST["test_8546"]["value"])
        create_file(
            self.new_file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Uploading an object with same key and new content")
        resp = self.s3_test_obj.object_upload(
            self.bucket_name,
            self.object_name,
            self.new_file_path)
        assert resp[0], resp[1]
        assert resp[1] == self.new_file_path, resp[1]
        self.log.info(
            "Verified that object is uploaded with same key and new content")
        self.log.info("Listing objects from a bucket")
        resp = self.s3_test_obj.object_list(
            self.bucket_name)
        assert resp[0], resp[1]
        assert self.object_name in resp[1], resp[1]
        self.log.info("Objects are listed from a bucket")
        self.log.info("Cleanup activity")
        if os.path.exists(self.new_file_path):
            remove_file(self.new_file_path)
        self.log.info(
            "Create object key with existing object key in the same bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5487")
    @CTFailOn(error_handler)
    def test_key_1024byte_long_1987(self):
        """Create object key 1024 byte long."""
        self.log.info("Create object key 1024 byte long")
        obj_key = "".join(
            random.choices(
                f"{string.ascii_uppercase}{string.ascii_lowercase}{string.digits}",
                k=S3_OBJ_TST["test_8547"]["obj_key_length"]))
        self.create_bucket_put_list_object(
            self.bucket_name,
            obj_key,
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Create object key 1024 byte long")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5483")
    @CTFailOn(error_handler)
    def test_key_with_numeric_1989(self):
        """Create object key name with numbers only in the name and no other characters."""
        self.log.info(
            "Create object key name with numbers only in the name and no other characters")
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Create object key name with numbers only in the name and no other characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5486")
    @CTFailOn(error_handler)
    def test_keysize_morethan_1024bytes_1990(self):
        """Create object key greater than 1024 byte long."""
        self.log.info("Create object key greater than 1024 byte long")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Created a bucket with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        system_random = random.SystemRandom()
        count_limit = system_random.randrange(
                S3_OBJ_TST["test_8550"]["start_range"],
                S3_OBJ_TST["test_8550"]["stop_range"])
        obj_key = "".join(
            random.choices(
                string.ascii_lowercase,
                k=count_limit))
        self.log.info("Uploading an object to a bucket %s",
                      self.bucket_name)
        try:
            self.s3_test_obj.put_object(
                self.bucket_name,
                obj_key,
                self.file_path)
        except CTException as error:
            assert_s3_err_msg(errmsg.RGW_ERR_LONG_OBJ_NAME, errmsg.CORTX_ERR_LONG_OBJ_NAME,
                              CMN_CFG["s3_engine"], error)
        self.log.info("Create object key greater than 1024 byte long")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-7636")
    @CTFailOn(error_handler)
    def test_keyname_delimiters_prefixes_1991(self):
        """Create object key-name with delimiters and prefixes to enable.

        or use the concept of hierarchy and folders
        """
        self.log.info(
            "Create object-key name with delimiters to "
            "enable or use the concept of hierarchy and folders")
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Create object key name with delimiters to "
            "enable or use the concept of hierarchy and folders")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5484")
    @CTFailOn(error_handler)
    def test_key_chars_require_special_handling_1992(self):
        """Create object key name with Characters That Might Require Special Handling."""
        self.log.info(
            "Create object key name with Characters That Might Require Special Handling")
        object_list = []
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Created a bucket with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        for each_obj in S3_OBJ_TST["test_8552"]["obj_list"]:
            self.log.info(
                "Uploading an oject %s to a bucket", each_obj)
            resp = self.s3_test_obj.put_object(
                self.bucket_name,
                each_obj,
                self.file_path)
            assert resp[0], resp[1]
            object_list.append(each_obj)
            self.log.info(
                "Uploaded an object %s to a bucket", each_obj)
        self.log.info(
            "Verifying objects are uploaded to a bucket %s",
            self.bucket_name)
        resp = self.s3_test_obj.object_list(
            self.bucket_name)
        assert resp[0], resp[1]
        for each_obj in object_list:
            assert each_obj in resp[1], resp[1]
        self.log.info(
            "Verified that objects are uploaded to a bucket %s",
            self.bucket_name)
        self.log.info(
            "Create object key name with Characters That Might Require Special Handling")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5485")
    @CTFailOn(error_handler)
    def test_keyname_chars_avoidlist_1993(self):
        """Create object key name from Characters to Avoid list."""
        self.log.info(
            "Create object key name from Characters to Avoid list")
        object_list = []
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Created a bucket with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        for each_obj in S3_OBJ_TST["test_8553"]["obj_list"]:
            self.log.info(
                "Uploading an oject %s to a bucket", each_obj)
            resp = self.s3_test_obj.put_object(
                self.bucket_name,
                each_obj,
                self.file_path)
            assert resp[0], resp[1]
            object_list.append(each_obj)
            self.log.info(
                "Uploaded an object %s to a bucket", each_obj)
        self.log.info(
            "Verifying objects are uploaded to a bucket %s",
            self.bucket_name)
        resp = self.s3_test_obj.object_list(
            self.bucket_name)
        assert resp[0], resp[1]
        for each_obj in object_list:
            assert each_obj in resp[1], resp[1]
        self.log.info(
            "Verified that objects are uploaded to a bucket %s",
            self.bucket_name)
        self.log.info(
            "Create object key name from Characters to Avoid list")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5488")
    @CTFailOn(error_handler)
    def test_metadata_with_adding_new_object_1994(self):
        """Add user defined metadata while adding the new object to the bucket."""
        self.log.info(
            "Add user defined metadata while adding the new object to the bucket")
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"],
            m_key=S3_OBJ_TST["test_8554"]["key"],
            m_value=S3_OBJ_TST["test_8554"]["value"])
        self.log.info(
            "Add user defined metadata while adding the new object to the bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5489")
    @CTFailOn(error_handler)
    def test_update_metadat_while_copying_1995(self):
        """Add or update user defined metadata while copying.

        updating an existing object to the bucket.
        """
        self.log.info(
            "Add or update user defined metadata while "
            "copying/ updating an existing object to the bucket")
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"],
            m_key=S3_OBJ_TST["test_8555"]["key"],
            m_value=S3_OBJ_TST["test_8555"]["value"])
        create_file(
            self.new_file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Updating user defined metadata while adding new object")
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            S3_OBJ_TST["test_8555"]["new_obj"],
            self.new_file_path,
            m_key=S3_OBJ_TST["test_8555"]["new_key"],
            m_value=S3_OBJ_TST["test_8555"]["new_value"])
        assert resp[0], resp[1]
        self.log.info("Updated user defined metadata")
        self.log.info("Listing object from a bucket %s",
                      self.bucket_name)
        resp = self.s3_test_obj.object_list(
            self.bucket_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_8555"]["new_obj"] in resp[1], resp[1]
        self.log.info("Objects are listed from a bucket")
        self.log.info("Retrieving updated object info")
        resp = self.s3_test_obj.object_info(
            self.bucket_name,
            S3_OBJ_TST["test_8555"]["new_obj"])
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_8555"]["new_key"] in resp[1]["Metadata"], resp[1]
        self.log.info("Retrieved updated object info")
        self.log.info("Cleanup activity")
        if os.path.exists(self.new_file_path):
            remove_file(self.new_file_path)
        self.log.info(
            "Add or update user defined metadata while "
            "copying/ updating an existing object to the bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5476")
    @CTFailOn(error_handler)
    def test_update_metadata_upto2kb_1997(self):
        """Update user defined metadata upto 2KB."""
        self.log.info("Update user defined metadata upto 2KB")
        m_key = "".join(
            random.choices(
                f"{string.ascii_uppercase}{string.ascii_lowercase}{string.digits}",
                k=S3_OBJ_TST["test_8557"]["byte_count"]))
        m_val = "".join(
            random.choices(
                "{string.ascii_uppercase}{string.ascii_lowercase}{string.digits}",
                k=S3_OBJ_TST["test_8557"]["byte_count"]))
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"],
            m_key=m_key,
            m_value=m_val)
        self.log.info("Update user defined metadata upto 2KB")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5477")
    @CTFailOn(error_handler)
    def test_metadata_morethan2kb_1998(self):
        """Update user defined metadata greater than 2 KB."""
        self.log.info("Update user defined metadata greater than 2 KB")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Created a bucket with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        count_limit = random.choice(
            range(
                S3_OBJ_TST["test_8558"]["start_range"],
                S3_OBJ_TST["test_8558"]["stop_range"]))
        m_key = "".join(
            random.choices("{string.ascii_uppercase}{string.ascii_lowercase}{string.digits}",
                           k=count_limit))
        m_val = "".join(
            random.choices("{string.ascii_uppercase}{string.ascii_lowercase}{string.digits}",
                           k=count_limit))
        self.log.info(
            "Uploading an object to a bucket %s with metadata size greater than 2KB",
            self.bucket_name)
        try:
            self.s3_test_obj.put_object(
                self.bucket_name,
                self.object_name,
                self.file_path,
                m_key=m_key,
                m_value=m_val)
        except CTException as error:
            assert errmsg.S3_META_DATA_HEADER_EXCEED_ERR in error.message, error.message
        self.log.info("Update user defined metadata greater than 2 KB")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5474")
    @CTFailOn(error_handler)
    def test_max_objects_2287(self):
        """Verification of max. no. of objects user can upload."""
        self.log.info("Verification of max. no. of objects user can upload")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Created a bucket with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Uploading objects to a bucket %s",
                      self.bucket_name)
        for count in range(S3_OBJ_TST["test_8913"]["obj_count"]):
            obj_name = "{0}{1}".format(
                S3_OBJ_TST["test_8913"]["obj_name"], str(count))
            resp = self.s3_test_obj.object_upload(
                self.bucket_name,
                obj_name,
                self.file_path)
            assert resp[0], resp[1]
        self.log.info("Objects are uploaded to a bucket %s",
                      self.bucket_name)
        self.log.info(
            "Verifying objects are uploaded to a bucket %s",
            self.bucket_name)
        resp = self.s3_test_obj.object_list(
            self.bucket_name)
        assert resp[0], resp[1]
        assert len(
            resp[1]) == S3_OBJ_TST["test_8913"]["obj_count"], resp[1]
        self.log.info(
            "Verified that %s objects are uploaded to a bucket",
            S3_OBJ_TST["test_8913"]["obj_count"])
        self.log.info("Verification of max. no. of objects user can upload")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_ops
    @pytest.mark.tags("TEST-5475")
    @CTFailOn(error_handler)
    def test_max_object_size_2292(self):
        """Verification of max size of object, user can upload."""
        self.log.info("Verification of max size of object, user can upload")
        self.create_bucket_put_list_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["test_8918"]["mb_count"])
        self.log.info("Verification of max size of object, user can upload")
