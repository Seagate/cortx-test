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

"""Object Workflow Operations Test Module."""

import os
import time
import logging
import shutil
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from config import S3_OBJ_TST
from libs.s3 import s3_test_lib, s3_cmd_test_lib, s3_multipart_test_lib
from commons.utils.system_utils import create_file, remove_file, path_exists, make_dirs, cleanup_dir

S3_TEST_OBJ = s3_test_lib.S3TestLib()
S3_CMD_OBJ = s3_cmd_test_lib.S3CmdTestLib()
S3_MP_OBJ = s3_multipart_test_lib.S3MultipartTestLib()



class TestGetObjectFaultTolerance:
    """Object Workflow Operations Testsuite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup suite method")
        cls.bkt_name_prefix= "objworkflow"
        cls.obj_name_prefix= "objworkflowobj"
        cls.folder_path = os.path.join(os.getcwd(), "test_data")
        cls.file_path = os.path.join(cls.folder_path, "obj_workflow.txt")
        cls.log.info("ENDED: setup suite method")

    def setup_method(self):
        """Setup method."""
        self.log.info("STARTED: setup method")
        if not path_exists(self.folder_path):
            resp = make_dirs(self.folder_path)
            self.log.info("Created path: %s", resp)
        self.log.info("ENDED: setup method")

    def teardown_method(self):
        """Teardown method."""
        self.log.info("STARTED: teardown method")
        self.log.info("Clean : %s", self.folder_path)
        if path_exists(self.folder_path):
            resp = cleanup_dir(self.folder_path)
            self.log.info(
                "cleaned path: %s, resp: %s",
                self.folder_path,
                resp)
        bucket_list = S3_TEST_OBJ.bucket_list()
        pref_list = [
            each_bucket for each_bucket in bucket_list[1] if each_bucket.startswith(self.bkt_name_prefix)]
        S3_TEST_OBJ.delete_multiple_buckets(pref_list)
        if os.path.exists(self.file_path):
            remove_file(self.file_path)
        if os.path.exists(self.folder_path):
            shutil.rmtree(self.folder_path)
        self.log.info("ENDED: teardown method")

    def create_bucket_put_objects(self, bucket_name, object_count):
        """
        Function will create a bucket with specified name and uploads.

        given no of objects to the bucket.
        :param str bucket_name: Name of a bucket to be created.
        :param int object_count: No of objects to be uploaded into the bucket.
        :return: List of objects uploaded to bucket.
        :rtype: list
        """
        obj_list = []
        self.log.info(
            "Step 1: Creating a bucket with name %s", bucket_name)
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == bucket_name, resp[0]
        self.log.info(
            "Step 1: Created a bucket with name %s", bucket_name)
        self.log.info(
            "Step 2: Uploading %s objects to the bucket ",
            object_count)
        for cnt in range(object_count):
            obj_name = f"{self.obj_name_prefix}{cnt}"
            create_file(
                self.file_path,
                S3_OBJ_TST["s3_object"]["mb_count"])
            resp = S3_TEST_OBJ.put_object(
                bucket_name,
                obj_name,
                self.file_path)
            assert resp[0], resp[1]
            obj_list.append(obj_name)
        self.log.info(
            "Step 2: Uploaded %s objects to the bucket ", object_count)

        return obj_list

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5498")
    @CTFailOn(error_handler)
    def test_put_file_2208(self):
        """Copying/PUT a local file to s3."""
        self.log.info("Copying/PUT a local file to s3")
        self.log.info(
            "STARTED: Creating a bucket with name %s",
            S3_OBJ_TST["test_2208"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            S3_OBJ_TST["test_2208"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == S3_OBJ_TST["test_2208"]["bucket_name"], resp[0]
        self.log.info(
            "Created a bucket with name %s",
            S3_OBJ_TST["test_2208"]["bucket_name"])
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object %s to a bucket %s",
            S3_OBJ_TST["test_2208"]["obj_name"],
            S3_OBJ_TST["test_2208"]["bucket_name"])
        resp = S3_TEST_OBJ.put_object(
            S3_OBJ_TST["test_2208"]["bucket_name"],
            S3_OBJ_TST["test_2208"]["obj_name"],
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Uploaded an object to a bucket")
        self.log.info("Verifying object is successfully uploaded")
        resp = S3_TEST_OBJ.object_list(
            S3_OBJ_TST["test_2208"]["bucket_name"])
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_2208"]["obj_name"] in resp[1], resp[1]
        self.log.info("Verified that object is uploaded successfully")
        self.log.info("ENDED: Copying/PUT a local file to s3")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5499")
    @CTFailOn(error_handler)
    def test_copy_different_sizes_2209(self):
        """Copying file/object of different type & size to s3."""
        self.log.info(
            "STARTED: Copying file/object of different type & size to s3")
        self.log.info(
            "Creating a bucket with name %s",
            S3_OBJ_TST["test_2209"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            S3_OBJ_TST["test_2209"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == S3_OBJ_TST["test_2209"]["bucket_name"], resp[0]
        self.log.info(
            "Created a bucket with name %s",
            S3_OBJ_TST["test_2209"]["bucket_name"])
        self.log.info(
            "Uploading different size objects to a bucket %s",
            S3_OBJ_TST["test_2209"]["bucket_name"])
        put_object = S3_TEST_OBJ.put_random_size_objects(
            S3_OBJ_TST["test_2209"]["bucket_name"],
            S3_OBJ_TST["test_2209"]["obj_name"],
            S3_OBJ_TST["test_2209"]["start_range"],
            S3_OBJ_TST["test_2209"]["stop_range"],
            object_count=S3_OBJ_TST["test_2209"]["file_count"],
            file_path=self.file_path)
        assert put_object[0], put_object[1]
        self.log.info("Uploaded different size of objects")
        self.log.info("Validating objects are uploaded or not")
        obj_list = S3_TEST_OBJ.object_list(
            S3_OBJ_TST["test_2209"]["bucket_name"])
        assert obj_list[0], obj_list[1]
        assert obj_list[1] == put_object[1], obj_list[1]
        self.log.info(
            "ENDED: Copying file/object of different type & size to s3")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5496")
    @CTFailOn(error_handler)
    def test_recursive_copy_2210(self):
        """Recursively copying local files to s3."""
        self.log.info("STARTED: Recursively copying local files to s3")
        self.log.info(
            "Creating a bucket with name %s",
            S3_OBJ_TST["test_2210"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            S3_OBJ_TST["test_2210"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == S3_OBJ_TST["test_2210"]["bucket_name"], resp[0]
        self.log.info(
            "Created a bucket with name %s",
            S3_OBJ_TST["test_2210"]["bucket_name"])
        self.log.info(
            "Recursively copying local files to a bucket %s",
            S3_OBJ_TST["test_2210"]["bucket_name"])
        resp = S3_CMD_OBJ.upload_folder_cli(
            S3_OBJ_TST["test_2210"]["bucket_name"],
            self.folder_path,
            S3_OBJ_TST["test_2210"]["file_count"])
        assert resp[0], resp[1]
        self.log.info("Copied local files to a bucket")
        self.log.info("ENDED: Recursively copying local files to s3")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5502")
    def test_add_object_non_existing_bucket2211(self):
        """Add Object to non existing bucket."""
        self.log.info("STARTED: Add Object to non existing bucket")
        self.log.info("Uploading an object to non existing bucket")
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        try:
            S3_TEST_OBJ.object_upload(
                S3_OBJ_TST["test_2211"]["bucket_name"],
                S3_OBJ_TST["test_2211"]["obj_name"],
                self.file_path)
        except CTException as error:
            assert S3_OBJ_TST["test_2211"]["error_message"] in str(
                error.message), error.message
        self.log.info("Uploading an object to non existing is failed")
        self.log.info("ENDED: Add Object to non existing bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5500")
    @CTFailOn(error_handler)
    def test_copy_object_local_file_2213(self):
        """Copying an s3 object to a local file."""
        self.log.info("STARTED: Copying an s3 object to a local file")
        self.log.info(
            "Creating a bucket with name %s",
            S3_OBJ_TST["test_2213"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            S3_OBJ_TST["test_2213"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == S3_OBJ_TST["test_2213"]["bucket_name"], resp[0]
        self.log.info(
            "Created a bucket with name %s",
            S3_OBJ_TST["test_2213"]["bucket_name"])
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object %s to a bucket %s",
            S3_OBJ_TST["test_2213"]["obj_name"],
            S3_OBJ_TST["test_2213"]["bucket_name"])
        resp = S3_TEST_OBJ.object_upload(
            S3_OBJ_TST["test_2213"]["bucket_name"],
            S3_OBJ_TST["test_2213"]["obj_name"],
            self.file_path)
        assert resp[0], resp[1]
        assert resp[1] == self.file_path, resp[1]
        self.log.info("Uploaded an object to a bucket")
        self.log.info(
            "Listing an object from a bucket %s",
            S3_OBJ_TST["test_2213"]["bucket_name"])
        resp = S3_TEST_OBJ.object_list(
            S3_OBJ_TST["test_2213"]["bucket_name"])
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_2213"]["obj_name"] in resp[1], resp[1]
        self.log.info("Objects are listed from a bucket")
        self.log.info(
            "Downloading an object from a bucket %s",
            S3_OBJ_TST["test_2213"]["bucket_name"])
        resp = S3_TEST_OBJ.object_download(
            S3_OBJ_TST["test_2213"]["bucket_name"],
            S3_OBJ_TST["test_2213"]["obj_name"],
            self.file_path)
        assert resp[0], resp[1]
        assert os.path.exists(self.file_path), resp[1]
        self.log.info("Objects are downloaded from a bucket")
        self.log.info("Cleanup activity")
        if os.path.exists(self.file_path):
            remove_file(self.file_path)
        self.log.info("ENDED: Copying an s3 object to a local file")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5495")
    @CTFailOn(error_handler)
    def test_recursive_copy_local_dir_2214(self):
        """Recursively copying s3 objects to a local directory."""
        self.log.info(
            "STARTED: Recursively copying s3 objects to a local directory")
        self.log.info(
            "Creating a bucket with name %s",
            S3_OBJ_TST["test_2214"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            S3_OBJ_TST["test_2214"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == S3_OBJ_TST["test_2214"]["bucket_name"], resp[0]
        self.log.info(
            "Created a bucket with name %s",
            S3_OBJ_TST["test_2214"]["bucket_name"])
        self.log.info(
            "Recursively copying local files to a bucket %s",
            S3_OBJ_TST["test_2214"]["bucket_name"])
        resp = S3_CMD_OBJ.upload_folder_cli(
            S3_OBJ_TST["test_2214"]["bucket_name"],
            self.folder_path,
            S3_OBJ_TST["test_2214"]["file_count"])
        assert resp[0], resp[1]
        self.log.info("Copied local files to a bucket")
        self.log.info(
            "Downloading an object from a bucket %s",
            S3_OBJ_TST["test_2214"]["bucket_name"])
        resp = S3_CMD_OBJ.download_bucket_cli(
            S3_OBJ_TST["test_2214"]["bucket_name"],
            self.folder_path)
        assert resp[0], resp[1]
        self.log.info("Downloaded an object rom a bucket")
        self.log.info(
            "ENDED: Recursively copying s3 objects to a local directory")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5501")
    @CTFailOn(error_handler)
    def test_download_byte_range_2215(self):
        """Copy/Download byte range of object."""
        self.log.info("STARTED: Copy/Download byte range of object")
        self.log.info(
            "Creating a bucket with name %s",
            S3_OBJ_TST["test_2215"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            S3_OBJ_TST["test_2215"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == S3_OBJ_TST["test_2215"]["bucket_name"], resp[0]
        self.log.info(
            "Created a bucket with name %s",
            S3_OBJ_TST["test_2215"]["bucket_name"])
        create_file(
            self.file_path,
            S3_OBJ_TST["test_2215"]["file_size"])
        self.log.info(
            "Uploading an object to a bucket %s",
            S3_OBJ_TST["test_2215"]["bucket_name"])
        resp = S3_TEST_OBJ.object_upload(
            S3_OBJ_TST["test_2215"]["bucket_name"],
            S3_OBJ_TST["test_2215"]["obj_name"],
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Getting object within byte range")
        resp = S3_MP_OBJ.get_byte_range_of_object(
            S3_OBJ_TST["test_2215"]["bucket_name"],
            S3_OBJ_TST["test_2215"]["obj_name"],
            S3_OBJ_TST["test_2215"]["start_byte"],
            S3_OBJ_TST["test_2215"]["stop_byte"])
        assert resp[0], resp[1]
        self.log.info("Byte range of an object is downloaded")
        self.log.info("ENDED: Copy/Download byte range of object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5493")
    @CTFailOn(error_handler)
    def test_retrieve_metadata_2217(self):
        """Retrieve Metadata of object."""
        self.log.info("STARTED: Retrieve Metadata of object")
        self.log.info(
            "Creating a bucket with name %s",
            S3_OBJ_TST["test_2217"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            S3_OBJ_TST["test_2217"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == S3_OBJ_TST["test_2217"]["bucket_name"], resp[0]
        self.log.info(
            "Created a bucket with name %s",
            S3_OBJ_TST["test_2217"]["bucket_name"])
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object to a bucket %s",
            S3_OBJ_TST["test_2217"]["bucket_name"])
        resp = S3_TEST_OBJ.object_upload(
            S3_OBJ_TST["test_2217"]["bucket_name"],
            S3_OBJ_TST["test_2217"]["obj_name"],
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Verifying object is successfully uploaded")
        resp = S3_TEST_OBJ.object_list(
            S3_OBJ_TST["test_2217"]["bucket_name"])
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_2217"]["obj_name"] in resp[1], resp[1]
        self.log.info("Verified that object is uploaded successfully")
        self.log.info("Retrieving metadata of an object")
        resp = S3_TEST_OBJ.object_info(
            S3_OBJ_TST["test_2217"]["bucket_name"],
            S3_OBJ_TST["test_2217"]["obj_name"])
        assert resp[0], resp[1]
        self.log.info("Retrieved metadata of an object")
        self.log.info("ENDED: Retrieve Metadata of object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5503")
    @CTFailOn(error_handler)
    def test_add_metadata_verify_object_2218(self):
        """Add new metadata to the object and check if the new data is getting reflected."""
        self.log.info(
            "STARTED: Add new metadata to the object and check "
            "if the new data is getting reflected")
        self.log.info(
            "Creating a bucket with name %s",
            S3_OBJ_TST["test_2218"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            S3_OBJ_TST["test_2218"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == S3_OBJ_TST["test_2218"]["bucket_name"], resp[0]
        self.log.info(
            "Created a bucket with name %s",
            S3_OBJ_TST["test_2218"]["bucket_name"])
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object to a bucket %s",
            S3_OBJ_TST["test_2218"]["bucket_name"])
        resp = S3_TEST_OBJ.object_upload(
            S3_OBJ_TST["test_2218"]["bucket_name"],
            S3_OBJ_TST["test_2218"]["obj_name"],
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Verifying object is successfully uploaded")
        resp = S3_TEST_OBJ.object_list(
            S3_OBJ_TST["test_2218"]["bucket_name"])
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_2218"]["obj_name"] in resp[1], resp[1]
        self.log.info("Verified that object is uploaded successfully")
        self.log.info("Retrieving metadata of an object")
        resp = S3_TEST_OBJ.object_info(
            S3_OBJ_TST["test_2218"]["bucket_name"],
            S3_OBJ_TST["test_2218"]["obj_name"])
        assert resp[0], resp[1]
        self.log.info("Retrieved metadata of an object")
        self.log.info(
            "Adding new metadata to an object %s",
            S3_OBJ_TST["test_2218"]["obj_name"])
        resp = S3_TEST_OBJ.put_object(
            S3_OBJ_TST["test_2218"]["bucket_name"],
            S3_OBJ_TST["test_2218"]["obj_name"],
            self.file_path,
            m_key=S3_OBJ_TST["test_2218"]["key"],
            m_value=S3_OBJ_TST["test_2218"]["value"])
        assert resp[0], resp[1]
        self.log.info("Added new metadata to an object")
        self.log.info(
            "Retrieving info of a object %s after adding new metadata",
            S3_OBJ_TST["test_2218"]["obj_name"])
        resp = S3_TEST_OBJ.object_info(
            S3_OBJ_TST["test_2218"]["bucket_name"],
            S3_OBJ_TST["test_2218"]["obj_name"])
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_2218"]["key"] in resp[1]["Metadata"], resp[1]
        self.log.info("Retrieved new metadata of an object")
        self.log.info(
            "ENDED: Add new metadata to the object and check if the new data is getting reflected")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5494")
    @CTFailOn(error_handler)
    def test_remove_metadata_2219(self):
        """Remove the existing metadata and check if the entry is not shown."""
        self.log.info(
            "Remove the existing metadata and check if the entry is not shown")
        self.log.info(
            "Creating a bucket with name %s",
            S3_OBJ_TST["test_2219"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            S3_OBJ_TST["test_2219"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == S3_OBJ_TST["test_2219"]["bucket_name"], resp[0]
        self.log.info(
            "Created a bucket with name %s",
            S3_OBJ_TST["test_2219"]["bucket_name"])
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Uploading an object with metadata")
        resp = S3_TEST_OBJ.put_object(
            S3_OBJ_TST["test_2219"]["bucket_name"],
            S3_OBJ_TST["test_2219"]["obj_name"],
            self.file_path,
            m_key=S3_OBJ_TST["test_2219"]["key"],
            m_value=S3_OBJ_TST["test_2219"]["value"])
        assert resp[0], resp[1]
        self.log.info("Uploaded an object with metadata")
        self.log.info("Retrieving metadata of an object")
        resp = S3_TEST_OBJ.object_info(
            S3_OBJ_TST["test_2219"]["bucket_name"],
            S3_OBJ_TST["test_2219"]["obj_name"])
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_2219"]["key"] in resp[1]["Metadata"], resp[1]
        self.log.info("Retrieved metadata of an object")
        self.log.info("Deleting metadata")
        resp = S3_TEST_OBJ.delete_object(
            S3_OBJ_TST["test_2219"]["bucket_name"],
            S3_OBJ_TST["test_2219"]["obj_name"])
        assert resp[0], resp[1]
        self.log.info("Deleted metadata")
        self.log.info("Retrieving metadata of an object")
        try:
            S3_TEST_OBJ.object_info(
                S3_OBJ_TST["test_2219"]["bucket_name"],
                S3_OBJ_TST["test_2219"]["obj_name"])
        except CTException as error:
            assert S3_OBJ_TST["test_2219"]["error_message"] in str(
                error.message), error.message
        self.log.info("Retrieving of metadata is failed")
        self.log.info(
            "Remove the existing metadata and check if the entry is not shown")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5497")
    @CTFailOn(error_handler)
    def test_delete_object_2220(self):
        """Delete object from bucket."""
        self.log.info("STARTED: Delete object from bucket")
        self.log.info(
            "Creating a bucket with name %s",
            S3_OBJ_TST["test_2220"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            S3_OBJ_TST["test_2220"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == S3_OBJ_TST["test_2220"]["bucket_name"], resp[0]
        self.log.info(
            "Created a bucket with name %s",
            S3_OBJ_TST["test_2220"]["bucket_name"])
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object %s to a bucket %s",
            S3_OBJ_TST["test_2220"]["obj_name"],
            S3_OBJ_TST["test_2220"]["bucket_name"])
        resp = S3_TEST_OBJ.put_object(
            S3_OBJ_TST["test_2220"]["bucket_name"],
            S3_OBJ_TST["test_2220"]["obj_name"],
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Uploaded an object to a bucket")
        self.log.info("Verifying object is successfully uploaded")
        resp = S3_TEST_OBJ.object_list(
            S3_OBJ_TST["test_2220"]["bucket_name"])
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_2220"]["obj_name"] in resp[1], resp[1]
        self.log.info("Verified that object is uploaded successfully")
        self.log.info(
            "Deleting object %s from a bucket %s",
            S3_OBJ_TST["test_2220"]["obj_name"],
            S3_OBJ_TST["test_2220"]["bucket_name"])
        resp = S3_TEST_OBJ.delete_object(
            S3_OBJ_TST["test_2220"]["bucket_name"],
            S3_OBJ_TST["test_2220"]["obj_name"])
        assert resp[0], resp[1]
        self.log.info("Object deleted from a bucket")
        self.log.info("Verifying object is deleted")
        resp = S3_TEST_OBJ.object_list(
            S3_OBJ_TST["test_2220"]["bucket_name"])
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_2220"]["obj_name"] not in resp[1], resp[1]
        self.log.info("Verified that object is deleted from a bucket")
        self.log.info("ENDED: Delete object from bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-5492")
    @CTFailOn(error_handler)
    def test_delete_non_existing_object_2221(self):
        """Try deleting object not present."""
        self.log.info("STARTED: Try deleting object not present")
        self.log.info(
            "Creating a bucket with name %s",
            S3_OBJ_TST["test_2221"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            S3_OBJ_TST["test_2221"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == S3_OBJ_TST["test_2221"]["bucket_name"], resp[0]
        self.log.info(
            "Created a bucket with name %s",
            S3_OBJ_TST["test_2221"]["bucket_name"])
        self.log.info("Deleting object which is not present")
        resp = S3_TEST_OBJ.delete_object(
            S3_OBJ_TST["test_2221"]["bucket_name"],
            S3_OBJ_TST["test_2221"]["obj_name"])
        assert resp[0], resp[1]
        self.log.info(
            "Performed object delete operation on non exist object")
        self.log.info("ENDED: Try deleting object not present")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8713")
    @CTFailOn(error_handler)
    def test_del_object_verbose_mode_7653(self):
        """Test Delete objects which exists with verbose mode."""
        self.log.info(
            "STARTED: Test Delete objects which exists with verbose mode .")
        cfg_7653 = S3_OBJ_TST["test_7653"]
        bucket_name = cfg_7653["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7653["no_of_objects"])
        self.log.info(
            "Step 3: Deleting %s objects from bucket",
            cfg_7653["no_of_objects"])
        resp = S3_TEST_OBJ.delete_multiple_objects(bucket_name, obj_list)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Deleted %s objects from bucket",
            cfg_7653["no_of_objects"])
        self.log.info(
            "Step 4: Listing objects of a bucket to verify all objects are deleted")
        resp = S3_TEST_OBJ.object_list(bucket_name)
        assert resp[0], resp[1]
        assert len(resp[1]) == 0, resp[1]
        self.log.info(
            "Step 4: Listed objects and verified that all objects are deleted successfully")
        self.log.info(
            "ENDED: Test Delete objects which exists with verbose mode .")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8714")
    @CTFailOn(error_handler)
    def test_delete_object_quiet_mode_7655(self):
        """Delete objects mentioning object which doesn't exists as well with quiet mode."""
        self.log.info(
            "STARTED: Delete objects mentioning object "
            "which doesn't exists as well with quiet mode.")
        cfg_7655 = S3_OBJ_TST["test_7655"]
        bucket_name = cfg_7655["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7655["no_of_objects"])
        # Adding a dummy object to the object list which isn't uploaded to
        # bucket
        obj_list.append(self.obj_name_prefix + str(int(time.time())))
        self.log.info(
            "Step 3: Deleting all existing objects along with one non existing object from bucket "
            "with quiet mode")
        resp = S3_TEST_OBJ.delete_multiple_objects(
            bucket_name, obj_list, quiet=True)
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Deleting all existing objects along with one non existing object from bucket "
            "with quiet mode")
        self.log.info(
            "Step 4: Listing objects of a bucket to verify all objects are deleted")
        resp = S3_TEST_OBJ.object_list(bucket_name)
        assert resp[0], resp[1]
        assert len(resp[1]) == 0, resp[1]
        self.log.info(
            "Step 4: Listed objects and verified that all objects are deleted successfully")
        self.log.info(
            "ENDED: Delete objects mentioning object which doesn't exists as well with quiet mode.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8715")
    @CTFailOn(error_handler)
    def test_delete_objects_and_mention_1001_objects_7656(self):
        """Delete objects and mention 1001 objects."""
        self.log.info("STARTED: Delete objects and mention 1001 objects.")
        cfg_7656 = S3_OBJ_TST["test_7656"]
        bucket_name = cfg_7656["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7656["no_of_objects"])
        self.log.info(
            "Step 3: Deleting %s objects from a bucket",
            cfg_7656["del_obj_cnt"])
        try:
            S3_TEST_OBJ.delete_multiple_objects(
                bucket_name, obj_list[:cfg_7656["del_obj_cnt"]])
        except CTException as error:
            self.log.error(error.message)
            assert cfg_7656["err_message"] in error.message, error.message
        self.log.info(
            "Step 3: Deleting %s objects from a bucket failed with %s",
            cfg_7656["del_obj_cnt"],
            cfg_7656["err_message"])
        self.log.info("ENDED: Delete objects and mention 1001 objects.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-8716")
    @CTFailOn(error_handler)
    def test_delete_objects_and_mention_1000_objects_7657(self):
        """Delete objects and mention 1000 objects.."""
        self.log.info("STARTED: Delete objects and mention 1000 objects.")
        cfg_7657 = S3_OBJ_TST["test_7657"]
        bucket_name = cfg_7657["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7657["no_of_objects"])
        self.log.info(
            "Step 3: Deleting %s objects from a bucket",
            cfg_7657["del_obj_cnt"])
        resp = S3_TEST_OBJ.delete_multiple_objects(
            bucket_name, obj_list[:cfg_7657["del_obj_cnt"]])
        assert resp[0], resp[1]
        self.log.info(
            "Step 3: Deleted %s objects from a bucket",
            cfg_7657["del_obj_cnt"])
        self.log.info(
            "Step 4: Listing objects to verify %s objects are deleted",
            cfg_7657["del_obj_cnt"])
        resp = S3_TEST_OBJ.object_list(bucket_name)
        assert resp[0], resp[1]
        no_obj_left = cfg_7657["no_of_objects"] - cfg_7657["del_obj_cnt"]
        assert len(resp[1]) == no_obj_left, resp[1]
        self.log.info(
            "Step 4: Listed objects and verified that %s objects are deleted successfully",
            cfg_7657["del_obj_cnt"])
        self.log.info("ENDED: Delete objects and mention 1000 objects.")
