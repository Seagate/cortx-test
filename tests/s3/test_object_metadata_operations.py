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

"""Object Metadata Operations Test Module."""
import os
import random
import string
import logging
import pytest
from libs.s3 import s3_test_lib
from commons.utils.system_utils import create_file, remove_file
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml

s3_test_obj = s3_test_lib.S3TestLib()
obj_metadata_conf = read_yaml(
    "config/s3/test_object_metadata_operations.yaml")


class TestObjectMetadataOperations():
    """"Object Metadata Operations Testsuite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.LOGGER = logging.getLogger(__name__)

    def setup_method(self):
        """Setup method."""
        self.LOGGER.info("STARTED: Setup/Teardown operations")
        bucket_list = s3_test_obj.bucket_list()
        pref_list = [
            each_bucket for each_bucket in bucket_list[1] if each_bucket.startswith(
                obj_metadata_conf["object_metadata"]["bkt_name_prefix"])]
        s3_test_obj.delete_multiple_buckets(pref_list)
        if os.path.exists(obj_metadata_conf["object_metadata"]["file_path"]):
            remove_file(
                obj_metadata_conf["object_metadata"]["file_path"])
        self.LOGGER.info("ENDED: Setup/Teardown operations")

    def teardown_method(self):
        """Teardown Method."""
        self.LOGGER.info("STARTED: Teardown operations")
        self.LOGGER.info("ENDED: Teardown operations")

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
        :param m_key: Key for metadata
        :param m_value: Value for metadata
        """
        m_key = kwargs.get("m_key", None)
        m_value = kwargs.get("m_value", None)
        self.LOGGER.info("Creating a bucket %s", bucket_name)
        resp = s3_test_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        self.LOGGER.info("Created a bucket %s", bucket_name)
        create_file(file_path, mb_count)
        self.LOGGER.info(
            "Uploading an object %s to bucket %s",
            obj_name, bucket_name)
        resp = s3_test_obj.put_object(
            bucket_name, obj_name, file_path, m_key, m_value)
        assert resp[0], resp[1]
        self.LOGGER.info(
            "Uploaded an object %s to bucket %s", obj_name, bucket_name)
        self.LOGGER.info("Listing objects from a bucket %s", bucket_name)
        resp = s3_test_obj.object_list(bucket_name)
        assert resp[0], resp[1]
        assert obj_name in resp[1], resp[1]
        self.LOGGER.info(
            "Objects are listed from a bucket %s", bucket_name)
        if m_key:
            self.LOGGER.info(
                "Retrieving metadata of an object %s", obj_name)
            resp = s3_test_obj.object_info(bucket_name, obj_name)
            assert resp[0], resp[1]
            assert m_key in resp[1]["Metadata"], resp[1]
            self.LOGGER.info(
                "Retrieved metadata of an object %s", obj_name)

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @CTFailOn(error_handler)
    def test_1983(self):
        """Create object key with alphanumeric characters."""
        self.LOGGER.info("Create object key with alphanumeric characters")
        self.create_bucket_put_list_object(
            obj_metadata_conf["test_8543"]["bucket_name"],
            obj_metadata_conf["test_8543"]["obj_name"],
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        self.LOGGER.info("Create object key with alphanumeric characters")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @CTFailOn(error_handler)
    def test_1984(self):
        """Create object key with valid special characters."""
        self.LOGGER.info("Create object key with valid special characters")
        self.create_bucket_put_list_object(
            obj_metadata_conf["test_8544"]["bucket_name"],
            obj_metadata_conf["test_8544"]["obj_name"],
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        self.LOGGER.info("Create object key with valid special characters")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @CTFailOn(error_handler)
    def test_1985(self):
        """Create object key with combinations of alphanumeric and valid special characters."""
        self.LOGGER.info(
            "Create object key with combinations of alphanumeric and valid special characters")
        self.create_bucket_put_list_object(
            obj_metadata_conf["test_8545"]["bucket_name"],
            obj_metadata_conf["test_8545"]["obj_name"],
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        self.LOGGER.info(
            "Create object key with combinations of alphanumeric and valid special characters")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @CTFailOn(error_handler)
    def test_1986(self):
        """Create object key with existing object key in the same bucket."""
        self.LOGGER.info(
            "Create object key with existing object key in the same bucket")
        self.create_bucket_put_list_object(
            obj_metadata_conf["test_8546"]["bucket_name"],
            obj_metadata_conf["test_8546"]["obj_name"],
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"],
            key=obj_metadata_conf["test_8546"]["key"],
            value=obj_metadata_conf["test_8546"]["value"])
        create_file(
            obj_metadata_conf["test_8546"]["new_file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        self.LOGGER.info("Uploading an object with same key and new content")
        resp = s3_test_obj.object_upload(
            obj_metadata_conf["test_8546"]["bucket_name"],
            obj_metadata_conf["test_8546"]["obj_name"],
            obj_metadata_conf["test_8546"]["new_file_path"])
        assert resp[0], resp[1]
        assert resp[1] == obj_metadata_conf["test_8546"]["new_file_path"], resp[1]
        self.LOGGER.info(
            "Verified that object is uploaded with same key and new content")
        self.LOGGER.info("Listing objects from a bucket")
        resp = s3_test_obj.object_list(
            obj_metadata_conf["test_8546"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_metadata_conf["test_8546"]["obj_name"] in resp[1], resp[1]
        self.LOGGER.info("Objects are listed from a bucket")
        self.LOGGER.info("Cleanup activity")
        if os.path.exists(obj_metadata_conf["test_8546"]["new_file_path"]):
            remove_file(obj_metadata_conf["test_8546"]["new_file_path"])
        self.LOGGER.info(
            "Create object key with existing object key in the same bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @CTFailOn(error_handler)
    def test_1987(self):
        """Create object key 1024 byte long."""
        self.LOGGER.info("Create object key 1024 byte long")
        obj_key = "".join(
            random.choices(
                "{0}{1}{2}".format(
                    string.ascii_uppercase,
                    string.ascii_lowercase,
                    string.digits),
                k=obj_metadata_conf["test_8547"]["obj_key_length"]))
        self.create_bucket_put_list_object(
            obj_metadata_conf["test_8547"]["bucket_name"],
            obj_key,
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        self.LOGGER.info("Create object key 1024 byte long")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @CTFailOn(error_handler)
    def test_1989(self):
        """Create object key name with numbers only in the name and no other characters."""
        self.LOGGER.info(
            "Create object key name with numbers only in the name and no other characters")
        self.create_bucket_put_list_object(
            obj_metadata_conf["test_8549"]["bucket_name"],
            obj_metadata_conf["test_8549"]["obj_name"],
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        self.LOGGER.info(
            "Create object key name with numbers only in the name and no other characters")

    def test_1990(self):
        """Create object key greater than 1024 byte long."""
        self.LOGGER.info("Create object key greater than 1024 byte long")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            obj_metadata_conf["test_8550"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_metadata_conf["test_8550"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_metadata_conf["test_8550"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Created a bucket with name %s",
            obj_metadata_conf["test_8550"]["bucket_name"])
        create_file(
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        count_limit = random.choice(
            range(
                obj_metadata_conf["test_8550"]["start_range"],
                obj_metadata_conf["test_8550"]["stop_range"]))
        obj_key = "".join(
            random.choices(
                string.ascii_lowercase,
                k=count_limit))
        self.LOGGER.info("Uploading an object to a bucket %s",
                         obj_metadata_conf["test_8550"]["bucket_name"])
        try:
            s3_test_obj.put_object(
                obj_metadata_conf["test_8550"]["bucket_name"],
                obj_key,
                obj_metadata_conf["object_metadata"]["file_path"])
        except CTException as error:
            assert obj_metadata_conf["test_8550"]["error_message"] in error.message, error.message
        self.LOGGER.info("Create object key greater than 1024 byte long")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @CTFailOn(error_handler)
    def test_1991(self):
        """Create object key-name with delimiters and prefixes to enable.

        or use the concept of hierarchy and folders
        """
        self.LOGGER.info(
            "Create object-key name with delimiters to "
            "enable or use the concept of hierarchy and folders")
        self.create_bucket_put_list_object(
            obj_metadata_conf["test_8551"]["bucket_name"],
            obj_metadata_conf["test_8551"]["obj_name"],
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        self.LOGGER.info(
            "Create object key name with delimiters to "
            "enable or use the concept of hierarchy and folders")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @CTFailOn(error_handler)
    def test_1992(self):
        """Create object key name with Characters That Might Require Special Handling."""
        self.LOGGER.info(
            "Create object key name with Characters That Might Require Special Handling")
        object_list = []
        self.LOGGER.info(
            "Creating a bucket with name %s",
            obj_metadata_conf["test_8552"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_metadata_conf["test_8552"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_metadata_conf["test_8552"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Created a bucket with name %s",
            obj_metadata_conf["test_8552"]["bucket_name"])
        create_file(
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        for each_obj in obj_metadata_conf["test_8552"]["obj_list"]:
            self.LOGGER.info(
                "Uploading an oject %s to a bucket", each_obj)
            resp = s3_test_obj.put_object(
                obj_metadata_conf["test_8552"]["bucket_name"],
                each_obj,
                obj_metadata_conf["object_metadata"]["file_path"])
            assert resp[0], resp[1]
            object_list.append(each_obj)
            self.LOGGER.info(
                "Uploaded an object %s to a bucket", each_obj)
        self.LOGGER.info(
            "Verifying objects are uploaded to a bucket %s",
            obj_metadata_conf["test_8552"]["bucket_name"])
        resp = s3_test_obj.object_list(
            obj_metadata_conf["test_8552"]["bucket_name"])
        assert resp[0], resp[1]
        for each_obj in object_list:
            assert each_obj in resp[1], resp[1]
        self.LOGGER.info(
            "Verified that objects are uploaded to a bucket %s",
            obj_metadata_conf["test_8552"]["bucket_name"])
        self.LOGGER.info(
            "Create object key name with Characters That Might Require Special Handling")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @CTFailOn(error_handler)
    def test_1993(self):
        """Create object key name from Characters to Avoid list."""
        self.LOGGER.info(
            "Create object key name from Characters to Avoid list")
        object_list = []
        self.LOGGER.info(
            "Creating a bucket with name %s",
            obj_metadata_conf["test_8553"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_metadata_conf["test_8553"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_metadata_conf["test_8553"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Created a bucket with name %s",
            obj_metadata_conf["test_8553"]["bucket_name"])
        create_file(
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        for each_obj in obj_metadata_conf["test_8553"]["obj_list"]:
            self.LOGGER.info(
                "Uploading an oject %s to a bucket", each_obj)
            resp = s3_test_obj.put_object(
                obj_metadata_conf["test_8553"]["bucket_name"],
                each_obj,
                obj_metadata_conf["object_metadata"]["file_path"])
            assert resp[0], resp[1]
            object_list.append(each_obj)
            self.LOGGER.info(
                "Uploaded an object %s to a bucket", each_obj)
        self.LOGGER.info(
            "Verifying objects are uploaded to a bucket %s",
            obj_metadata_conf["test_8553"]["bucket_name"])
        resp = s3_test_obj.object_list(
            obj_metadata_conf["test_8553"]["bucket_name"])
        assert resp[0], resp[1]
        for each_obj in object_list:
            assert each_obj in resp[1], resp[1]
        self.LOGGER.info(
            "Verified that objects are uploaded to a bucket %s",
            obj_metadata_conf["test_8553"]["bucket_name"])
        self.LOGGER.info(
            "Create object key name from Characters to Avoid list")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @CTFailOn(error_handler)
    def test_1994(self):
        """Add user defined metadata while adding the new object to the bucket."""
        self.LOGGER.info(
            "Add user defined metadata while adding the new object to the bucket")
        self.create_bucket_put_list_object(
            obj_metadata_conf["test_8554"]["bucket_name"],
            obj_metadata_conf["test_8554"]["obj_name"],
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"],
            obj_metadata_conf["test_8554"]["key"],
            obj_metadata_conf["test_8554"]["value"])
        self.LOGGER.info(
            "Add user defined metadata while adding the new object to the bucket")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @CTFailOn(error_handler)
    def test_1995(self):
        """Add or update user defined metadata while copying.

        updating an existing object to the bucket.
        """
        self.LOGGER.info(
            "Add or update user defined metadata while "
            "copying/ updating an existing object to the bucket")
        self.create_bucket_put_list_object(
            obj_metadata_conf["test_8555"]["bucket_name"],
            obj_metadata_conf["test_8555"]["obj_name"],
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"],
            obj_metadata_conf["test_8555"]["key"],
            obj_metadata_conf["test_8555"]["value"])
        create_file(
            obj_metadata_conf["test_8555"]["new_file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        self.LOGGER.info(
            "Updating user defined metadata while adding new object")
        resp = s3_test_obj.put_object(
            obj_metadata_conf["test_8555"]["bucket_name"],
            obj_metadata_conf["test_8555"]["new_obj"],
            obj_metadata_conf["test_8555"]["new_file_path"],
            obj_metadata_conf["test_8555"]["new_key"],
            obj_metadata_conf["test_8555"]["new_value"])
        assert resp[0], resp[1]
        self.LOGGER.info("Updated user defined metadata")
        self.LOGGER.info("Listing object from a bucket %s",
                         obj_metadata_conf["test_8555"]["bucket_name"])
        resp = s3_test_obj.object_list(
            obj_metadata_conf["test_8555"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_metadata_conf["test_8555"]["new_obj"] in resp[1], resp[1]
        self.LOGGER.info("Objects are listed from a bucket")
        self.LOGGER.info("Retrieving updated object info")
        resp = s3_test_obj.object_info(
            obj_metadata_conf["test_8555"]["bucket_name"],
            obj_metadata_conf["test_8555"]["new_obj"])
        assert resp[0], resp[1]
        assert obj_metadata_conf["test_8555"]["new_key"] in resp[1]["Metadata"], resp[1]
        self.LOGGER.info("Retrieved updated object info")
        self.LOGGER.info("Cleanup activity")
        if os.path.exists(obj_metadata_conf["test_8555"]["new_file_path"]):
            remove_file(obj_metadata_conf["test_8555"]["new_file_path"])
        self.LOGGER.info(
            "Add or update user defined metadata while "
            "copying/ updating an existing object to the bucket")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @ CTFailOn(error_handler)
    def test_1997(self):
        """Update user defined metadata upto 2KB."""
        self.LOGGER.info("Update user defined metadata upto 2KB")
        m_key = "".join(
            random.choices(
                "{0}{1}{2}".format(
                    string.ascii_uppercase,
                    string.ascii_lowercase,
                    string.digits),
                k=obj_metadata_conf["test_8557"]["byte_count"]))
        m_val = "".join(
            random.choices(
                "{0}{1}{2}".format(
                    string.ascii_uppercase,
                    string.ascii_lowercase,
                    string.digits),
                k=obj_metadata_conf["test_8557"]["byte_count"]))
        self.create_bucket_put_list_object(
            obj_metadata_conf["test_8557"]["bucket_name"],
            obj_metadata_conf["test_8557"]["obj_name"],
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"],
            m_key,
            m_val)
        self.LOGGER.info("Update user defined metadata upto 2KB")

    def test_1998(self):
        """Update user defined metadata greater than 2 KB."""
        self.LOGGER.info("Update user defined metadata greater than 2 KB")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            obj_metadata_conf["test_8558"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_metadata_conf["test_8558"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_metadata_conf["test_8558"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Created a bucket with name %s",
            obj_metadata_conf["test_8558"]["bucket_name"])
        create_file(
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        count_limit = random.choice(
            range(
                obj_metadata_conf["test_8558"]["start_range"],
                obj_metadata_conf["test_8558"]["stop_range"]))
        m_key = "".join(
            random.choices("{0}{1}{2}".format(
                string.ascii_uppercase,
                string.ascii_lowercase,
                string.digits), k=count_limit))
        m_val = "".join(
            random.choices("{0}{1}{2}".format(
                string.ascii_uppercase,
                string.ascii_lowercase,
                string.digits), k=count_limit))
        self.LOGGER.info(
            "Uploading an object to a bucket %s with metadata size greater than 2KB",
            obj_metadata_conf["test_8558"]["bucket_name"])
        try:
            s3_test_obj.put_object(
                obj_metadata_conf["test_8558"]["bucket_name"],
                obj_metadata_conf["test_8558"]["obj_name"],
                obj_metadata_conf["object_metadata"]["file_path"],
                m_key,
                m_val)
        except CTException as error:
            assert obj_metadata_conf["test_8558"]["error_message"] in error.message, error.message
        self.LOGGER.info("Update user defined metadata greater than 2 KB")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @ CTFailOn(error_handler)
    def test_2287(self):
        """Verification of max. no. of objects user can upload."""
        self.LOGGER.info("Verification of max. no. of objects user can upload")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            obj_metadata_conf["test_8913"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_metadata_conf["test_8913"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_metadata_conf["test_8913"]["bucket_name"], resp[1]
        self.LOGGER.info(
            "Created a bucket with name %s",
            obj_metadata_conf["test_8913"]["bucket_name"])
        create_file(
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["object_metadata"]["mb_count"])
        self.LOGGER.info("Uploading objects to a bucket %s",
                         obj_metadata_conf["test_8913"]["bucket_name"])
        for count in range(obj_metadata_conf["test_8913"]["obj_count"]):
            obj_name = "{0}{1}".format(
                obj_metadata_conf["test_8913"]["obj_name"], str(count))
            resp = s3_test_obj.object_upload(
                obj_metadata_conf["test_8913"]["bucket_name"],
                obj_name,
                obj_metadata_conf["object_metadata"]["file_path"])
            assert resp[0], resp[1]
        self.LOGGER.info("Objects are uploaded to a bucket %s",
                         obj_metadata_conf["test_8913"]["bucket_name"])
        self.LOGGER.info(
            "Verifying objects are uploaded to a bucket %s",
            obj_metadata_conf["test_8913"]["bucket_name"])
        resp = s3_test_obj.object_list(
            obj_metadata_conf["test_8913"]["bucket_name"])
        assert resp[0], resp[1]
        assert len(
            resp[1]) == obj_metadata_conf["test_8913"]["obj_count"], resp[1]
        self.LOGGER.info(
            "Verified that %s objects are uploaded to a bucket",
            obj_metadata_conf["test_8913"]["obj_count"])
        self.LOGGER.info("Verification of max. no. of objects user can upload")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5432", "object_metadata_operations")
    @ CTFailOn(error_handler)
    def test_2292(self):
        """Verification of max size of object, user can upload."""
        self.LOGGER.info("Verification of max size of object, user can upload")
        self.create_bucket_put_list_object(
            obj_metadata_conf["test_8918"]["bucket_name"],
            obj_metadata_conf["test_8918"]["obj_name"],
            obj_metadata_conf["object_metadata"]["file_path"],
            obj_metadata_conf["test_8918"]["mb_count"])
        self.LOGGER.info("Verification of max size of object, user can upload")
