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

from libs.s3 import s3_test_lib, s3_cmd_test_lib, s3_multipart_test_lib

from commons.utils.system_utils import create_file, remove_file
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml

S3_TEST_OBJ = s3_test_lib.S3TestLib()
S3_CMD_OBJ = s3_cmd_test_lib.S3CmdTestLib()
S3_MP_OBJ = s3_multipart_test_lib.S3MultipartTestLib()

OBJ_OPS_CONF = read_yaml(
    "config/s3/test_object_workflow_operations.yaml")


class TestObjectWorkflowOperations:
    """Object Workflow Operations Testsuite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.LOGGER = logging.getLogger(__name__)

    def setup_method(self):
        """Setup method."""
        self.LOGGER.info("STARTED: setup method")
        bucket_list = S3_TEST_OBJ.bucket_list()
        pref_list = [
            each_bucket for each_bucket in bucket_list[1] if each_bucket.startswith(
                OBJ_OPS_CONF["object_workflow"]["bkt_name_prefix"])]
        S3_TEST_OBJ.delete_multiple_buckets(pref_list)
        if os.path.exists(OBJ_OPS_CONF["object_workflow"]["file_path"]):
            remove_file(OBJ_OPS_CONF["object_workflow"]["file_path"])
        if os.path.exists(OBJ_OPS_CONF["object_workflow"]["folder_path"]):
            shutil.rmtree(OBJ_OPS_CONF["object_workflow"]["folder_path"])
        self.LOGGER.info("ENDED: setup method")

    def teardown_method(self):
        """Teardown method."""
        self.LOGGER.info("STARTED: teardown method")
        self.setup_method()
        self.LOGGER.info("ENDED: teardown method")

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
        self.LOGGER.info(
            "Step 1: Creating a bucket with name %s", bucket_name)
        resp = S3_TEST_OBJ.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == bucket_name, resp[0]
        self.LOGGER.info(
            "Step 1: Created a bucket with name %s", bucket_name)
        self.LOGGER.info(
            "Step 2: Uploading %s objects to the bucket ",
            object_count)
        for cnt in range(object_count):
            obj_name = f"{OBJ_OPS_CONF['object_workflow']['obj_name_prefix']}{cnt}"
            create_file(
                OBJ_OPS_CONF["object_workflow"]["file_path"],
                OBJ_OPS_CONF["object_workflow"]["mb_count"])
            resp = S3_TEST_OBJ.put_object(
                bucket_name,
                obj_name,
                OBJ_OPS_CONF["object_workflow"]["file_path"])
            assert resp[0], resp[1]
            obj_list.append(obj_name)
        self.LOGGER.info(
            "Step 2: Uploaded %s objects to the bucket ", object_count)

        return obj_list

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5498")
    @ CTFailOn(error_handler)
    def test_2208(self):
        """Copying/PUT a local file to s3."""
        self.LOGGER.info("Copying/PUT a local file to s3")
        self.LOGGER.info(
            "STARTED: Creating a bucket with name %s",
            OBJ_OPS_CONF["test_2208"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            OBJ_OPS_CONF["test_2208"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["test_2208"]["bucket_name"], resp[0]
        self.LOGGER.info(
            "Created a bucket with name %s",
            OBJ_OPS_CONF["test_2208"]["bucket_name"])
        create_file(
            OBJ_OPS_CONF["object_workflow"]["file_path"],
            OBJ_OPS_CONF["object_workflow"]["mb_count"])
        self.LOGGER.info(
            "Uploading an object %s to a bucket %s",
            OBJ_OPS_CONF["test_2208"]["obj_name"],
            OBJ_OPS_CONF["test_2208"]["bucket_name"])
        resp = S3_TEST_OBJ.put_object(
            OBJ_OPS_CONF["test_2208"]["bucket_name"],
            OBJ_OPS_CONF["test_2208"]["obj_name"],
            OBJ_OPS_CONF["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        self.LOGGER.info("Uploaded an object to a bucket")
        self.LOGGER.info("Verifying object is successfully uploaded")
        resp = S3_TEST_OBJ.object_list(
            OBJ_OPS_CONF["test_2208"]["bucket_name"])
        assert resp[0], resp[1]
        assert OBJ_OPS_CONF["test_2208"]["obj_name"] in resp[1], resp[1]
        self.LOGGER.info("Verified that object is uploaded successfully")
        self.LOGGER.info("ENDED: Copying/PUT a local file to s3")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5499")
    @ CTFailOn(error_handler)
    def test_2209(self):
        """Copying file/object of different type & size to s3."""
        self.LOGGER.info(
            "STARTED: Copying file/object of different type & size to s3")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            OBJ_OPS_CONF["test_2209"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            OBJ_OPS_CONF["test_2209"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["test_2209"]["bucket_name"], resp[0]
        self.LOGGER.info(
            "Created a bucket with name %s",
            OBJ_OPS_CONF["test_2209"]["bucket_name"])
        self.LOGGER.info(
            "Uploading different size objects to a bucket %s",
            OBJ_OPS_CONF["test_2209"]["bucket_name"])
        put_object = S3_TEST_OBJ.put_random_size_objects(
            OBJ_OPS_CONF["test_2209"]["bucket_name"],
            OBJ_OPS_CONF["test_2209"]["obj_name"],
            OBJ_OPS_CONF["test_2209"]["start_range"],
            OBJ_OPS_CONF["test_2209"]["stop_range"],
            OBJ_OPS_CONF["test_2209"]["file_count"],
            OBJ_OPS_CONF["object_workflow"]["file_path"])
        assert put_object[0], put_object[1]
        self.LOGGER.info("Uploaded different size of objects")
        self.LOGGER.info("Validating objects are uploaded or not")
        obj_list = S3_TEST_OBJ.object_list(
            OBJ_OPS_CONF["test_2209"]["bucket_name"])
        assert obj_list[0], obj_list[1]
        assert obj_list[1] == put_object[1], obj_list[1]
        self.LOGGER.info(
            "ENDED: Copying file/object of different type & size to s3")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5496")
    @ CTFailOn(error_handler)
    def test_2210(self):
        """Recursively copying local files to s3."""
        self.LOGGER.info("STARTED: Recursively copying local files to s3")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            OBJ_OPS_CONF["test_2210"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            OBJ_OPS_CONF["test_2210"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["test_2210"]["bucket_name"], resp[0]
        self.LOGGER.info(
            "Created a bucket with name %s",
            OBJ_OPS_CONF["test_2210"]["bucket_name"])
        self.LOGGER.info(
            "Recursively copying local files to a bucket %s",
            OBJ_OPS_CONF["test_2210"]["bucket_name"])
        resp = S3_CMD_OBJ.upload_folder_cli(
            OBJ_OPS_CONF["test_2210"]["bucket_name"],
            OBJ_OPS_CONF["object_workflow"]["folder_path"],
            OBJ_OPS_CONF["test_2210"]["file_count"])
        assert resp[0], resp[1]
        self.LOGGER.info("Copied local files to a bucket")
        self.LOGGER.info("ENDED: Recursively copying local files to s3")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5502")
    def test_2211(self):
        """Add Object to non existing bucket."""
        self.LOGGER.info("STARTED: Add Object to non existing bucket")
        self.LOGGER.info("Uploading an object to non existing bucket")
        create_file(
            OBJ_OPS_CONF["object_workflow"]["file_path"],
            OBJ_OPS_CONF["object_workflow"]["mb_count"])
        try:
            S3_TEST_OBJ.object_upload(
                OBJ_OPS_CONF["test_2211"]["bucket_name"],
                OBJ_OPS_CONF["test_2211"]["obj_name"],
                OBJ_OPS_CONF["object_workflow"]["file_path"])
        except CTException as error:
            assert OBJ_OPS_CONF["test_2211"]["error_message"] in str(
                error.message), error.message
        self.LOGGER.info("Uploading an object to non existing is failed")
        self.LOGGER.info("ENDED: Add Object to non existing bucket")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5500")
    @ CTFailOn(error_handler)
    def test_2213(self):
        """Copying an s3 object to a local file."""
        self.LOGGER.info("STARTED: Copying an s3 object to a local file")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            OBJ_OPS_CONF["test_2213"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            OBJ_OPS_CONF["test_2213"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["test_2213"]["bucket_name"], resp[0]
        self.LOGGER.info(
            "Created a bucket with name %s",
            OBJ_OPS_CONF["test_2213"]["bucket_name"])
        create_file(
            OBJ_OPS_CONF["object_workflow"]["file_path"],
            OBJ_OPS_CONF["object_workflow"]["mb_count"])
        self.LOGGER.info(
            "Uploading an object %s to a bucket %s",
            OBJ_OPS_CONF["test_2213"]["obj_name"],
            OBJ_OPS_CONF["test_2213"]["bucket_name"])
        resp = S3_TEST_OBJ.object_upload(
            OBJ_OPS_CONF["test_2213"]["bucket_name"],
            OBJ_OPS_CONF["test_2213"]["obj_name"],
            OBJ_OPS_CONF["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["object_workflow"]["file_path"], resp[1]
        self.LOGGER.info("Uploaded an object to a bucket")
        self.LOGGER.info(
            "Listing an object from a bucket %s",
            OBJ_OPS_CONF["test_2213"]["bucket_name"])
        resp = S3_TEST_OBJ.object_list(
            OBJ_OPS_CONF["test_2213"]["bucket_name"])
        assert resp[0], resp[1]
        assert OBJ_OPS_CONF["test_2213"]["obj_name"] in resp[1], resp[1]
        self.LOGGER.info("Objects are listed from a bucket")
        self.LOGGER.info(
            "Downloading an object from a bucket %s",
            OBJ_OPS_CONF["test_2213"]["bucket_name"])
        resp = S3_TEST_OBJ.object_download(
            OBJ_OPS_CONF["test_2213"]["bucket_name"],
            OBJ_OPS_CONF["test_2213"]["obj_name"],
            OBJ_OPS_CONF["test_2213"]["file_path"])
        assert resp[0], resp[1]
        assert os.path.exists(OBJ_OPS_CONF["test_2213"]["file_path"]), resp[1]
        self.LOGGER.info("Objects are downloaded from a bucket")
        self.LOGGER.info("Cleanup activity")
        if os.path.exists(OBJ_OPS_CONF["test_2213"]["file_path"]):
            remove_file(OBJ_OPS_CONF["test_2213"]["file_path"])
        self.LOGGER.info("ENDED: Copying an s3 object to a local file")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5495")
    @ CTFailOn(error_handler)
    def test_2214(self):
        """Recursively copying s3 objects to a local directory."""
        self.LOGGER.info(
            "STARTED: Recursively copying s3 objects to a local directory")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            OBJ_OPS_CONF["test_2214"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            OBJ_OPS_CONF["test_2214"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["test_2214"]["bucket_name"], resp[0]
        self.LOGGER.info(
            "Created a bucket with name %s",
            OBJ_OPS_CONF["test_2214"]["bucket_name"])
        self.LOGGER.info(
            "Recursively copying local files to a bucket %s",
            OBJ_OPS_CONF["test_2214"]["bucket_name"])
        resp = S3_CMD_OBJ.upload_folder_cli(
            OBJ_OPS_CONF["test_2214"]["bucket_name"],
            OBJ_OPS_CONF["object_workflow"]["folder_path"],
            OBJ_OPS_CONF["test_2214"]["file_count"])
        assert resp[0], resp[1]
        self.LOGGER.info("Copied local files to a bucket")
        self.LOGGER.info(
            "Downloading an object from a bucket %s",
            OBJ_OPS_CONF["test_2214"]["bucket_name"])
        resp = S3_CMD_OBJ.download_bucket_cli(
            OBJ_OPS_CONF["test_2214"]["bucket_name"],
            OBJ_OPS_CONF["object_workflow"]["folder_path"])
        assert resp[0], resp[1]
        self.LOGGER.info("Downloaded an object rom a bucket")
        self.LOGGER.info(
            "ENDED: Recursively copying s3 objects to a local directory")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5501")
    @ CTFailOn(error_handler)
    def test_2215(self):
        """Copy/Download byte range of object."""
        self.LOGGER.info("STARTED: Copy/Download byte range of object")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            OBJ_OPS_CONF["test_2215"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            OBJ_OPS_CONF["test_2215"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["test_2215"]["bucket_name"], resp[0]
        self.LOGGER.info(
            "Created a bucket with name %s",
            OBJ_OPS_CONF["test_2215"]["bucket_name"])
        create_file(
            OBJ_OPS_CONF["object_workflow"]["file_path"],
            OBJ_OPS_CONF["test_2215"]["file_size"])
        self.LOGGER.info(
            "Uploading an object to a bucket %s",
            OBJ_OPS_CONF["test_2215"]["bucket_name"])
        resp = S3_TEST_OBJ.object_upload(
            OBJ_OPS_CONF["test_2215"]["bucket_name"],
            OBJ_OPS_CONF["test_2215"]["obj_name"],
            OBJ_OPS_CONF["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        self.LOGGER.info("Object is uploaded to a bucket")
        self.LOGGER.info("Getting object within byte range")
        resp = S3_MP_OBJ.get_byte_range_of_object(
            OBJ_OPS_CONF["test_2215"]["bucket_name"],
            OBJ_OPS_CONF["test_2215"]["obj_name"],
            OBJ_OPS_CONF["test_2215"]["start_byte"],
            OBJ_OPS_CONF["test_2215"]["stop_byte"])
        assert resp[0], resp[1]
        self.LOGGER.info("Byte range of an object is downloaded")
        self.LOGGER.info("ENDED: Copy/Download byte range of object")

    # def test_2216(self):
    #   """Cancel the in-progess GET object operation"""
    #   Cannot automate this test case as it needs manual intervention to abort
    #   GET operation

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5493")
    @ CTFailOn(error_handler)
    def test_2217(self):
        """Retrieve Metadata of object."""
        self.LOGGER.info("STARTED: Retrieve Metadata of object")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            OBJ_OPS_CONF["test_2217"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            OBJ_OPS_CONF["test_2217"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["test_2217"]["bucket_name"], resp[0]
        self.LOGGER.info(
            "Created a bucket with name %s",
            OBJ_OPS_CONF["test_2217"]["bucket_name"])
        create_file(
            OBJ_OPS_CONF["object_workflow"]["file_path"],
            OBJ_OPS_CONF["object_workflow"]["mb_count"])
        self.LOGGER.info(
            "Uploading an object to a bucket %s",
            OBJ_OPS_CONF["test_2217"]["bucket_name"])
        resp = S3_TEST_OBJ.object_upload(
            OBJ_OPS_CONF["test_2217"]["bucket_name"],
            OBJ_OPS_CONF["test_2217"]["obj_name"],
            OBJ_OPS_CONF["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        self.LOGGER.info("Object is uploaded to a bucket")
        self.LOGGER.info("Verifying object is successfully uploaded")
        resp = S3_TEST_OBJ.object_list(
            OBJ_OPS_CONF["test_2217"]["bucket_name"])
        assert resp[0], resp[1]
        assert OBJ_OPS_CONF["test_2217"]["obj_name"] in resp[1], resp[1]
        self.LOGGER.info("Verified that object is uploaded successfully")
        self.LOGGER.info("Retrieving metadata of an object")
        resp = S3_TEST_OBJ.object_info(
            OBJ_OPS_CONF["test_2217"]["bucket_name"],
            OBJ_OPS_CONF["test_2217"]["obj_name"])
        assert resp[0], resp[1]
        self.LOGGER.info("Retrieved metadata of an object")
        self.LOGGER.info("ENDED: Retrieve Metadata of object")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5503")
    @ CTFailOn(error_handler)
    def test_2218(self):
        """Add new metadata to the object and check if the new data is getting reflected."""
        self.LOGGER.info(
            "STARTED: Add new metadata to the object and check "
            "if the new data is getting reflected")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            OBJ_OPS_CONF["test_2218"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            OBJ_OPS_CONF["test_2218"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["test_2218"]["bucket_name"], resp[0]
        self.LOGGER.info(
            "Created a bucket with name %s",
            OBJ_OPS_CONF["test_2218"]["bucket_name"])
        create_file(
            OBJ_OPS_CONF["object_workflow"]["file_path"],
            OBJ_OPS_CONF["object_workflow"]["mb_count"])
        self.LOGGER.info(
            "Uploading an object to a bucket %s",
            OBJ_OPS_CONF["test_2218"]["bucket_name"])
        resp = S3_TEST_OBJ.object_upload(
            OBJ_OPS_CONF["test_2218"]["bucket_name"],
            OBJ_OPS_CONF["test_2218"]["obj_name"],
            OBJ_OPS_CONF["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        self.LOGGER.info("Object is uploaded to a bucket")
        self.LOGGER.info("Verifying object is successfully uploaded")
        resp = S3_TEST_OBJ.object_list(
            OBJ_OPS_CONF["test_2218"]["bucket_name"])
        assert resp[0], resp[1]
        assert OBJ_OPS_CONF["test_2218"]["obj_name"] in resp[1], resp[1]
        self.LOGGER.info("Verified that object is uploaded successfully")
        self.LOGGER.info("Retrieving metadata of an object")
        resp = S3_TEST_OBJ.object_info(
            OBJ_OPS_CONF["test_2218"]["bucket_name"],
            OBJ_OPS_CONF["test_2218"]["obj_name"])
        assert resp[0], resp[1]
        self.LOGGER.info("Retrieved metadata of an object")
        self.LOGGER.info(
            "Adding new metadata to an object %s",
            OBJ_OPS_CONF["test_2218"]["obj_name"])
        resp = S3_TEST_OBJ.put_object(
            OBJ_OPS_CONF["test_2218"]["bucket_name"],
            OBJ_OPS_CONF["test_2218"]["obj_name"],
            OBJ_OPS_CONF["object_workflow"]["file_path"],
            OBJ_OPS_CONF["test_2218"]["key"],
            OBJ_OPS_CONF["test_2218"]["value"])
        assert resp[0], resp[1]
        self.LOGGER.info("Added new metadata to an object")
        self.LOGGER.info(
            "Retrieving info of a object %s after adding new metadata",
            OBJ_OPS_CONF["test_2218"]["obj_name"])
        resp = S3_TEST_OBJ.object_info(
            OBJ_OPS_CONF["test_2218"]["bucket_name"],
            OBJ_OPS_CONF["test_2218"]["obj_name"])
        assert resp[0], resp[1]
        assert OBJ_OPS_CONF["test_2218"]["key"] in resp[1]["Metadata"], resp[1]
        self.LOGGER.info("Retrieved new metadata of an object")
        self.LOGGER.info(
            "ENDED: Add new metadata to the object and check if the new data is getting reflected")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5494")
    @ CTFailOn(error_handler)
    def test_2219(self):
        """Remove the existing metadata and check if the entry is not shown."""
        self.LOGGER.info(
            "Remove the existing metadata and check if the entry is not shown")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            OBJ_OPS_CONF["test_2219"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            OBJ_OPS_CONF["test_2219"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["test_2219"]["bucket_name"], resp[0]
        self.LOGGER.info(
            "Created a bucket with name %s",
            OBJ_OPS_CONF["test_2219"]["bucket_name"])
        create_file(
            OBJ_OPS_CONF["object_workflow"]["file_path"],
            OBJ_OPS_CONF["object_workflow"]["mb_count"])
        self.LOGGER.info("Uploading an object with metadata")
        resp = S3_TEST_OBJ.put_object(
            OBJ_OPS_CONF["test_2219"]["bucket_name"],
            OBJ_OPS_CONF["test_2219"]["obj_name"],
            OBJ_OPS_CONF["object_workflow"]["file_path"],
            OBJ_OPS_CONF["test_2219"]["key"],
            OBJ_OPS_CONF["test_2219"]["value"])
        assert resp[0], resp[1]
        self.LOGGER.info("Uploaded an object with metadata")
        self.LOGGER.info("Retrieving metadata of an object")
        resp = S3_TEST_OBJ.object_info(
            OBJ_OPS_CONF["test_2219"]["bucket_name"],
            OBJ_OPS_CONF["test_2219"]["obj_name"])
        assert resp[0], resp[1]
        assert OBJ_OPS_CONF["test_2219"]["key"] in resp[1]["Metadata"], resp[1]
        self.LOGGER.info("Retrieved metadata of an object")
        self.LOGGER.info("Deleting metadata")
        resp = S3_TEST_OBJ.delete_object(
            OBJ_OPS_CONF["test_2219"]["bucket_name"],
            OBJ_OPS_CONF["test_2219"]["obj_name"])
        assert resp[0], resp[1]
        self.LOGGER.info("Deleted metadata")
        self.LOGGER.info("Retrieving metadata of an object")
        try:
            S3_TEST_OBJ.object_info(
                OBJ_OPS_CONF["test_2219"]["bucket_name"],
                OBJ_OPS_CONF["test_2219"]["obj_name"])
        except CTException as error:
            assert OBJ_OPS_CONF["test_2219"]["error_message"] in str(
                error.message), error.message
        self.LOGGER.info("Retrieving of metadata is failed")
        self.LOGGER.info(
            "Remove the existing metadata and check if the entry is not shown")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5497")
    @ CTFailOn(error_handler)
    def test_2220(self):
        """Delete object from bucket."""
        self.LOGGER.info("STARTED: Delete object from bucket")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            OBJ_OPS_CONF["test_2220"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            OBJ_OPS_CONF["test_2220"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["test_2220"]["bucket_name"], resp[0]
        self.LOGGER.info(
            "Created a bucket with name %s",
            OBJ_OPS_CONF["test_2220"]["bucket_name"])
        create_file(
            OBJ_OPS_CONF["object_workflow"]["file_path"],
            OBJ_OPS_CONF["object_workflow"]["mb_count"])
        self.LOGGER.info(
            "Uploading an object %s to a bucket %s",
            OBJ_OPS_CONF["test_2220"]["obj_name"],
            OBJ_OPS_CONF["test_2220"]["bucket_name"])
        resp = S3_TEST_OBJ.put_object(
            OBJ_OPS_CONF["test_2220"]["bucket_name"],
            OBJ_OPS_CONF["test_2220"]["obj_name"],
            OBJ_OPS_CONF["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        self.LOGGER.info("Uploaded an object to a bucket")
        self.LOGGER.info("Verifying object is successfully uploaded")
        resp = S3_TEST_OBJ.object_list(
            OBJ_OPS_CONF["test_2220"]["bucket_name"])
        assert resp[0], resp[1]
        assert OBJ_OPS_CONF["test_2220"]["obj_name"] in resp[1], resp[1]
        self.LOGGER.info("Verified that object is uploaded successfully")
        self.LOGGER.info(
            "Deleting object %s from a bucket %s",
            OBJ_OPS_CONF["test_2220"]["obj_name"],
            OBJ_OPS_CONF["test_2220"]["bucket_name"])
        resp = S3_TEST_OBJ.delete_object(
            OBJ_OPS_CONF["test_2220"]["bucket_name"],
            OBJ_OPS_CONF["test_2220"]["obj_name"])
        assert resp[0], resp[1]
        self.LOGGER.info("Object deleted from a bucket")
        self.LOGGER.info("Verifying object is deleted")
        resp = S3_TEST_OBJ.object_list(
            OBJ_OPS_CONF["test_2220"]["bucket_name"])
        assert resp[0], resp[1]
        assert OBJ_OPS_CONF["test_2220"]["obj_name"] not in resp[1], resp[1]
        self.LOGGER.info("Verified that object is deleted from a bucket")
        self.LOGGER.info("ENDED: Delete object from bucket")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5492")
    @ CTFailOn(error_handler)
    def test_2221(self):
        """Try deleting object not present."""
        self.LOGGER.info("STARTED: Try deleting object not present")
        self.LOGGER.info(
            "Creating a bucket with name %s",
            OBJ_OPS_CONF["test_2221"]["bucket_name"])
        resp = S3_TEST_OBJ.create_bucket(
            OBJ_OPS_CONF["test_2221"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == OBJ_OPS_CONF["test_2221"]["bucket_name"], resp[0]
        self.LOGGER.info(
            "Created a bucket with name %s",
            OBJ_OPS_CONF["test_2221"]["bucket_name"])
        self.LOGGER.info("Deleting object which is not present")
        resp = S3_TEST_OBJ.delete_object(
            OBJ_OPS_CONF["test_2221"]["bucket_name"],
            OBJ_OPS_CONF["test_2221"]["obj_name"])
        assert resp[0], resp[1]
        self.LOGGER.info(
            "Performed object delete operation on non exist object")
        self.LOGGER.info("ENDED: Try deleting object not present")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-8713", "delete_objects")
    @ CTFailOn(error_handler)
    def test_7653(self):
        """Test Delete objects which exists with verbose mode."""
        self.LOGGER.info(
            "STARTED: Test Delete objects which exists with verbose mode .")
        cfg_7653 = OBJ_OPS_CONF["test_7653"]
        bucket_name = cfg_7653["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7653["no_of_objects"])
        self.LOGGER.info(
            "Step 3: Deleting %s objects from bucket",
            cfg_7653["no_of_objects"])
        resp = S3_TEST_OBJ.delete_multiple_objects(bucket_name, obj_list)
        assert resp[0], resp[1]
        self.LOGGER.info(
            "Step 3: Deleted %s objects from bucket",
            cfg_7653["no_of_objects"])
        self.LOGGER.info(
            "Step 4: Listing objects of a bucket to verify all objects are deleted")
        resp = S3_TEST_OBJ.object_list(bucket_name)
        assert resp[0], resp[1]
        assert len(resp[1]) == 0, resp[1]
        self.LOGGER.info(
            "Step 4: Listed objects and verified that all objects are deleted successfully")
        self.LOGGER.info(
            "ENDED: Test Delete objects which exists with verbose mode .")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-8714", "delete_objects")
    @ CTFailOn(error_handler)
    def test_7655(self):
        """Delete objects mentioning object which doesn't exists as well with quiet mode."""
        self.LOGGER.info(
            "STARTED: Delete objects mentioning object "
            "which doesn't exists as well with quiet mode.")
        cfg_7655 = OBJ_OPS_CONF["test_7655"]
        bucket_name = cfg_7655["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7655["no_of_objects"])
        # Adding a dummy object to the object list which isn't uploaded to
        # bucket
        obj_list.append(OBJ_OPS_CONF['object_workflow']['obj_name_prefix'],
                        str(int(time.time())))
        self.LOGGER.info(
            "Step 3: Deleting all existing objects along with one non existing object from bucket "
            "with quiet mode")
        resp = S3_TEST_OBJ.delete_multiple_objects(
            bucket_name, obj_list, quiet=True)
        assert resp[0], resp[1]
        self.LOGGER.info(
            "Step 3: Deleting all existing objects along with one non existing object from bucket "
            "with quiet mode")
        self.LOGGER.info(
            "Step 4: Listing objects of a bucket to verify all objects are deleted")
        resp = S3_TEST_OBJ.object_list(bucket_name)
        assert resp[0], resp[1]
        assert len(resp[1]) == 0, resp[1]
        self.LOGGER.info(
            "Step 4: Listed objects and verified that all objects are deleted successfully")
        self.LOGGER.info(
            "ENDED: Delete objects mentioning object which doesn't exists as well with quiet mode.")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-8175", "delete_objects")
    def test_7656(self):
        """Delete objects and mention 1001 objects."""
        self.LOGGER.info("STARTED: Delete objects and mention 1001 objects.")
        cfg_7656 = OBJ_OPS_CONF["test_7656"]
        bucket_name = cfg_7656["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7656["no_of_objects"])
        self.LOGGER.info(
            "Step 3: Deleting %s objects from a bucket",
            cfg_7656["del_obj_cnt"])
        try:
            S3_TEST_OBJ.delete_multiple_objects(
                bucket_name, obj_list[:cfg_7656["del_obj_cnt"]])
        except CTException as error:
            self.LOGGER.error(error.message)
            assert cfg_7656["err_message"] in error.message, error.message
        self.LOGGER.info(
            "Step 3: Deleting %s objects from a bucket failed with %s",
            cfg_7656["del_obj_cnt"],
            cfg_7656["err_message"])
        self.LOGGER.info("ENDED: Delete objects and mention 1001 objects.")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-8716", "delete_objects")
    @ CTFailOn(error_handler)
    def test_7657(self):
        """Delete objects and mention 1000 objects."""
        self.LOGGER.info("STARTED: Delete objects and mention 1000 objects.")
        cfg_7657 = OBJ_OPS_CONF["test_7657"]
        bucket_name = cfg_7657["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7657["no_of_objects"])
        self.LOGGER.info(
            "Step 3: Deleting %s objects from a bucket",
            cfg_7657["del_obj_cnt"])
        resp = S3_TEST_OBJ.delete_multiple_objects(
            bucket_name, obj_list[:cfg_7657["del_obj_cnt"]])
        assert resp[0], resp[1]
        self.LOGGER.info(
            "Step 3: Deleted %s objects from a bucket",
            cfg_7657["del_obj_cnt"])
        self.LOGGER.info(
            "Step 4: Listing objects to verify %s objects are deleted",
            cfg_7657["del_obj_cnt"])
        resp = S3_TEST_OBJ.object_list(bucket_name)
        assert resp[0], resp[1]
        no_obj_left = cfg_7657["no_of_objects"] - cfg_7657["del_obj_cnt"]
        assert len(resp[1]) == no_obj_left, resp[1]
        self.LOGGER.info(
            "Step 4: Listed objects and verified that %s objects are deleted successfully",
            cfg_7657["del_obj_cnt"])
        self.LOGGER.info("ENDED: Delete objects and mention 1000 objects.")
