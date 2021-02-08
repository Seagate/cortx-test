#!/usr/bin/python
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

LOGGER = logging.getLogger(__name__)
s3_test_obj = s3_test_lib.S3TestLib()
s3_cmd_obj = s3_cmd_test_lib.S3CmdTestLib()
s3_mp_obj = s3_multipart_test_lib.S3MultipartTestLib()

obj_ops_conf = read_yaml(
    "config/s3/test_object_workflow_operations.yaml")


class ObjectWorkflowOperations():
    """Object Workflow Operations Testsuite."""

    def setup_method(self):
        """Setup method."""
        bucket_list = s3_test_obj.bucket_list()
        pref_list = [
            each_bucket for each_bucket in bucket_list[1] if each_bucket.startswith(
                obj_ops_conf["object_workflow"]["bkt_name_prefix"])]
        s3_test_obj.delete_multiple_buckets(pref_list)
        if os.path.exists(obj_ops_conf["object_workflow"]["file_path"]):
            remove_file(obj_ops_conf["object_workflow"]["file_path"])
        if os.path.exists(obj_ops_conf["object_workflow"]["folder_path"]):
            shutil.rmtree(obj_ops_conf["object_workflow"]["folder_path"])

    def teardown_method(self):
        """Teardown method."""
        LOGGER.info("STARTED: teardown method")
        LOGGER.info("ENDED: teardown method")

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
        LOGGER.info(
            "Step 1: Creating a bucket with name %s", bucket_name)
        resp = s3_test_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == bucket_name, resp[0]
        LOGGER.info(
            "Step 1: Created a bucket with name %s", bucket_name)
        LOGGER.info(
            "Step 2: Uploading %s objects to the bucket ",
            object_count)
        for n in range(object_count):
            obj_name = f"{obj_ops_conf['object_workflow']['obj_name_prefix']}{n}"
            create_file(
                obj_ops_conf["object_workflow"]["file_path"],
                obj_ops_conf["object_workflow"]["mb_count"])
            resp = s3_test_obj.put_object(
                bucket_name,
                obj_name,
                obj_ops_conf["object_workflow"]["file_path"])
            assert resp[0], resp[1]
            obj_list.append(obj_name)
        LOGGER.info(
            "Step 2: Uploaded %s objects to the bucket ", object_count)

        return obj_list

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5498", "object_workflow_operations")
    @ CTFailOn(error_handler)
    def test_2208(self):
        """Copying/PUT a local file to s3."""
        LOGGER.info("Copying/PUT a local file to s3")
        LOGGER.info(
            "STARTED: Creating a bucket with name %s",
            obj_ops_conf["test_2208"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_ops_conf["test_2208"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["test_2208"]["bucket_name"], resp[0]
        LOGGER.info(
            "Created a bucket with name %s",
            obj_ops_conf["test_2208"]["bucket_name"])
        create_file(
            obj_ops_conf["object_workflow"]["file_path"],
            obj_ops_conf["object_workflow"]["mb_count"])
        LOGGER.info(
            "Uploading an object %s to a bucket %s",
            obj_ops_conf["test_2208"]["obj_name"],
            obj_ops_conf["test_2208"]["bucket_name"])
        resp = s3_test_obj.put_object(
            obj_ops_conf["test_2208"]["bucket_name"],
            obj_ops_conf["test_2208"]["obj_name"],
            obj_ops_conf["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Uploaded an object to a bucket")
        LOGGER.info("Verifying object is successfully uploaded")
        resp = s3_test_obj.object_list(
            obj_ops_conf["test_2208"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_ops_conf["test_2208"]["obj_name"] in resp[1], resp[1]
        LOGGER.info("Verified that object is uploaded successfully")
        LOGGER.info("ENDED: Copying/PUT a local file to s3")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5499", "object_workflow_operations")
    @ CTFailOn(error_handler)
    def test_2209(self):
        """Copying file/object of different type & size to s3."""
        LOGGER.info(
            "STARTED: Copying file/object of different type & size to s3")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_ops_conf["test_2209"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_ops_conf["test_2209"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["test_2209"]["bucket_name"], resp[0]
        LOGGER.info(
            "Created a bucket with name %s",
            obj_ops_conf["test_2209"]["bucket_name"])
        LOGGER.info(
            "Uploading different size objects to a bucket %s",
            obj_ops_conf["test_2209"]["bucket_name"])
        put_object = s3_test_obj.put_random_size_objects(
            obj_ops_conf["test_2209"]["bucket_name"],
            obj_ops_conf["test_2209"]["obj_name"],
            obj_ops_conf["test_2209"]["start_range"],
            obj_ops_conf["test_2209"]["stop_range"],
            obj_ops_conf["test_2209"]["file_count"],
            obj_ops_conf["object_workflow"]["file_path"])
        assert put_object[0], put_object[1]
        LOGGER.info("Uploaded different size of objects")
        LOGGER.info("Validating objects are uploaded or not")
        obj_list = s3_test_obj.object_list(
            obj_ops_conf["test_2209"]["bucket_name"])
        assert obj_list[0], obj_list[1]
        assert obj_list[1] == put_object[1], obj_list[1]
        LOGGER.info("ENDED: Copying file/object of different type & size to s3")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5496", "object_workflow_operations")
    @ CTFailOn(error_handler)
    def test_2210(self):
        """Recursively copying local files to s3."""
        LOGGER.info("STARTED: Recursively copying local files to s3")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_ops_conf["test_2210"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_ops_conf["test_2210"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["test_2210"]["bucket_name"], resp[0]
        LOGGER.info(
            "Created a bucket with name %s",
            obj_ops_conf["test_2210"]["bucket_name"])
        LOGGER.info(
            "Recursively copying local files to a bucket %s",
            obj_ops_conf["test_2210"]["bucket_name"])
        resp = s3_cmd_obj.upload_folder_cli(
            obj_ops_conf["test_2210"]["bucket_name"],
            obj_ops_conf["object_workflow"]["folder_path"],
            obj_ops_conf["test_2210"]["file_count"])
        assert resp[0], resp[1]
        LOGGER.info("Copied local files to a bucket")
        LOGGER.info("ENDED: Recursively copying local files to s3")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5502", "object_workflow_operations")
    def test_2211(self):
        """Add Object to non existing bucket."""
        LOGGER.info("STARTED: Add Object to non existing bucket")
        LOGGER.info("Uploading an object to non existing bucket")
        create_file(
            obj_ops_conf["object_workflow"]["file_path"],
            obj_ops_conf["object_workflow"]["mb_count"])
        try:
            s3_test_obj.object_upload(
                obj_ops_conf["test_2211"]["bucket_name"],
                obj_ops_conf["test_2211"]["obj_name"],
                obj_ops_conf["object_workflow"]["file_path"])
        except CTException as error:
            assert obj_ops_conf["test_2211"]["error_message"] in str(
                error.message), error.message
        LOGGER.info("Uploading an object to non existing is failed")
        LOGGER.info("ENDED: Add Object to non existing bucket")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5500", "object_workflow_operations")
    @ CTFailOn(error_handler)
    def test_2213(self):
        """Copying an s3 object to a local file."""
        LOGGER.info("STARTED: Copying an s3 object to a local file")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_ops_conf["test_2213"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_ops_conf["test_2213"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["test_2213"]["bucket_name"], resp[0]
        LOGGER.info(
            "Created a bucket with name %s",
            obj_ops_conf["test_2213"]["bucket_name"])
        create_file(
            obj_ops_conf["object_workflow"]["file_path"],
            obj_ops_conf["object_workflow"]["mb_count"])
        LOGGER.info(
            "Uploading an object %s to a bucket %s",
            obj_ops_conf["test_2213"]["obj_name"],
            obj_ops_conf["test_2213"]["bucket_name"])
        resp = s3_test_obj.object_upload(
            obj_ops_conf["test_2213"]["bucket_name"],
            obj_ops_conf["test_2213"]["obj_name"],
            obj_ops_conf["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["object_workflow"]["file_path"], resp[1]
        LOGGER.info("Uploaded an object to a bucket")
        LOGGER.info(
            "Listing an object from a bucket %s",
            obj_ops_conf["test_2213"]["bucket_name"])
        resp = s3_test_obj.object_list(
            obj_ops_conf["test_2213"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_ops_conf["test_2213"]["obj_name"] in resp[1], resp[1]
        LOGGER.info("Objects are listed from a bucket")
        LOGGER.info(
            "Downloading an object from a bucket %s",
            obj_ops_conf["test_2213"]["bucket_name"])
        resp = s3_test_obj.object_download(
            obj_ops_conf["test_2213"]["bucket_name"],
            obj_ops_conf["test_2213"]["obj_name"],
            obj_ops_conf["test_2213"]["file_path"])
        assert resp[0], resp[1]
        assert os.path.exists(obj_ops_conf["test_2213"]["file_path"]), resp[1]
        LOGGER.info("Objects are downloaded from a bucket")
        LOGGER.info("Cleanup activity")
        if os.path.exists(obj_ops_conf["test_2213"]["file_path"]):
            remove_file(obj_ops_conf["test_2213"]["file_path"])
        LOGGER.info("ENDED: Copying an s3 object to a local file")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5495", "object_workflow_operations")
    @ CTFailOn(error_handler)
    def test_2214(self):
        """Recursively copying s3 objects to a local directory."""
        LOGGER.info(
            "STARTED: Recursively copying s3 objects to a local directory")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_ops_conf["test_2214"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_ops_conf["test_2214"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["test_2214"]["bucket_name"], resp[0]
        LOGGER.info(
            "Created a bucket with name %s",
            obj_ops_conf["test_2214"]["bucket_name"])
        LOGGER.info(
            "Recursively copying local files to a bucket %s",
            obj_ops_conf["test_2214"]["bucket_name"])
        resp = s3_cmd_obj.upload_folder_cli(
            obj_ops_conf["test_2214"]["bucket_name"],
            obj_ops_conf["object_workflow"]["folder_path"],
            obj_ops_conf["test_2214"]["file_count"])
        assert resp[0], resp[1]
        LOGGER.info("Copied local files to a bucket")
        LOGGER.info(
            "Downloading an object from a bucket %s",
            obj_ops_conf["test_2214"]["bucket_name"])
        resp = s3_cmd_obj.download_bucket_cli(
            obj_ops_conf["test_2214"]["bucket_name"],
            obj_ops_conf["object_workflow"]["folder_path"])
        assert resp[0], resp[1]
        LOGGER.info("Downloaded an object rom a bucket")
        LOGGER.info(
            "ENDED: Recursively copying s3 objects to a local directory")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5501", "object_workflow_operations")
    @ CTFailOn(error_handler)
    def test_2215(self):
        """Copy/Download byte range of object."""
        LOGGER.info("STARTED: Copy/Download byte range of object")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_ops_conf["test_2215"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_ops_conf["test_2215"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["test_2215"]["bucket_name"], resp[0]
        LOGGER.info(
            "Created a bucket with name %s",
            obj_ops_conf["test_2215"]["bucket_name"])
        create_file(
            obj_ops_conf["object_workflow"]["file_path"],
            obj_ops_conf["test_2215"]["file_size"])
        LOGGER.info(
            "Uploading an object to a bucket %s",
            obj_ops_conf["test_2215"]["bucket_name"])
        resp = s3_test_obj.object_upload(
            obj_ops_conf["test_2215"]["bucket_name"],
            obj_ops_conf["test_2215"]["obj_name"],
            obj_ops_conf["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info("Getting object within byte range")
        resp = s3_mp_obj.get_byte_range_of_object(
            obj_ops_conf["test_2215"]["bucket_name"],
            obj_ops_conf["test_2215"]["obj_name"],
            obj_ops_conf["test_2215"]["start_byte"],
            obj_ops_conf["test_2215"]["stop_byte"])
        assert resp[0], resp[1]
        LOGGER.info("Byte range of an object is downloaded")
        LOGGER.info("ENDED: Copy/Download byte range of object")

    # def test_2216(self):
    #   """Cancel the in-progess GET object operation"""
    #   Cannot automate this test case as it needs manual intervention to abort
    #   GET operation

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5493", "object_workflow_operations")
    @ CTFailOn(error_handler)
    def test_2217(self):
        """Retrieve Metadata of object."""
        LOGGER.info("STARTED: Retrieve Metadata of object")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_ops_conf["test_2217"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_ops_conf["test_2217"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["test_2217"]["bucket_name"], resp[0]
        LOGGER.info(
            "Created a bucket with name %s",
            obj_ops_conf["test_2217"]["bucket_name"])
        create_file(
            obj_ops_conf["object_workflow"]["file_path"],
            obj_ops_conf["object_workflow"]["mb_count"])
        LOGGER.info(
            "Uploading an object to a bucket %s",
            obj_ops_conf["test_2217"]["bucket_name"])
        resp = s3_test_obj.object_upload(
            obj_ops_conf["test_2217"]["bucket_name"],
            obj_ops_conf["test_2217"]["obj_name"],
            obj_ops_conf["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info("Verifying object is successfully uploaded")
        resp = s3_test_obj.object_list(
            obj_ops_conf["test_2217"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_ops_conf["test_2217"]["obj_name"] in resp[1], resp[1]
        LOGGER.info("Verified that object is uploaded successfully")
        LOGGER.info("Retrieving metadata of an object")
        resp = s3_test_obj.object_info(
            obj_ops_conf["test_2217"]["bucket_name"],
            obj_ops_conf["test_2217"]["obj_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved metadata of an object")
        LOGGER.info("ENDED: Retrieve Metadata of object")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5503", "object_workflow_operations")
    @ CTFailOn(error_handler)
    def test_2218(self):
        """Add new metadata to the object and check if the new data is getting reflected."""
        LOGGER.info(
            "STARTED: Add new metadata to the object and check "
            "if the new data is getting reflected")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_ops_conf["test_2218"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_ops_conf["test_2218"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["test_2218"]["bucket_name"], resp[0]
        LOGGER.info(
            "Created a bucket with name %s",
            obj_ops_conf["test_2218"]["bucket_name"])
        create_file(
            obj_ops_conf["object_workflow"]["file_path"],
            obj_ops_conf["object_workflow"]["mb_count"])
        LOGGER.info(
            "Uploading an object to a bucket %s",
            obj_ops_conf["test_2218"]["bucket_name"])
        resp = s3_test_obj.object_upload(
            obj_ops_conf["test_2218"]["bucket_name"],
            obj_ops_conf["test_2218"]["obj_name"],
            obj_ops_conf["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info("Verifying object is successfully uploaded")
        resp = s3_test_obj.object_list(
            obj_ops_conf["test_2218"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_ops_conf["test_2218"]["obj_name"] in resp[1], resp[1]
        LOGGER.info("Verified that object is uploaded successfully")
        LOGGER.info("Retrieving metadata of an object")
        resp = s3_test_obj.object_info(
            obj_ops_conf["test_2218"]["bucket_name"],
            obj_ops_conf["test_2218"]["obj_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved metadata of an object")
        LOGGER.info(
            "Adding new metadata to an object %s",
            obj_ops_conf["test_2218"]["obj_name"])
        resp = s3_test_obj.put_object(
            obj_ops_conf["test_2218"]["bucket_name"],
            obj_ops_conf["test_2218"]["obj_name"],
            obj_ops_conf["object_workflow"]["file_path"],
            obj_ops_conf["test_2218"]["key"],
            obj_ops_conf["test_2218"]["value"])
        assert resp[0], resp[1]
        LOGGER.info("Added new metadata to an object")
        LOGGER.info(
            "Retrieving info of a object %s after adding new metadata",
            obj_ops_conf["test_2218"]["obj_name"])
        resp = s3_test_obj.object_info(
            obj_ops_conf["test_2218"]["bucket_name"],
            obj_ops_conf["test_2218"]["obj_name"])
        assert resp[0], resp[1]
        assert obj_ops_conf["test_2218"]["key"] in resp[1]["Metadata"], resp[1]
        LOGGER.info("Retrieved new metadata of an object")
        LOGGER.info(
            "ENDED: Add new metadata to the object and check if the new data is getting reflected")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5494", "object_workflow_operations")
    @ CTFailOn(error_handler)
    def test_2219(self):
        """Remove the existing metadata and check if the entry is not shown."""
        LOGGER.info(
            "Remove the existing metadata and check if the entry is not shown")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_ops_conf["test_2219"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_ops_conf["test_2219"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["test_2219"]["bucket_name"], resp[0]
        LOGGER.info(
            "Created a bucket with name %s",
            obj_ops_conf["test_2219"]["bucket_name"])
        create_file(
            obj_ops_conf["object_workflow"]["file_path"],
            obj_ops_conf["object_workflow"]["mb_count"])
        LOGGER.info("Uploading an object with metadata")
        resp = s3_test_obj.put_object(
            obj_ops_conf["test_2219"]["bucket_name"],
            obj_ops_conf["test_2219"]["obj_name"],
            obj_ops_conf["object_workflow"]["file_path"],
            obj_ops_conf["test_2219"]["key"],
            obj_ops_conf["test_2219"]["value"])
        assert resp[0], resp[1]
        LOGGER.info("Uploaded an object with metadata")
        LOGGER.info("Retrieving metadata of an object")
        resp = s3_test_obj.object_info(
            obj_ops_conf["test_2219"]["bucket_name"],
            obj_ops_conf["test_2219"]["obj_name"])
        assert resp[0], resp[1]
        assert obj_ops_conf["test_2219"]["key"] in resp[1]["Metadata"], resp[1]
        LOGGER.info("Retrieved metadata of an object")
        LOGGER.info("Deleting metadata")
        resp = s3_test_obj.delete_object(
            obj_ops_conf["test_2219"]["bucket_name"],
            obj_ops_conf["test_2219"]["obj_name"])
        assert resp[0], resp[1]
        LOGGER.info("Deleted metadata")
        LOGGER.info("Retrieving metadata of an object")
        try:
            s3_test_obj.object_info(
                obj_ops_conf["test_2219"]["bucket_name"],
                obj_ops_conf["test_2219"]["obj_name"])
        except CTException as error:
            assert obj_ops_conf["test_2219"]["error_message"] in str(
                error.message), error.message
        LOGGER.info("Retrieving of metadata is failed")
        LOGGER.info(
            "Remove the existing metadata and check if the entry is not shown")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5497", "object_workflow_operations")
    @ CTFailOn(error_handler)
    def test_2220(self):
        """Delete object from bucket."""
        LOGGER.info("STARTED: Delete object from bucket")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_ops_conf["test_2220"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_ops_conf["test_2220"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["test_2220"]["bucket_name"], resp[0]
        LOGGER.info(
            "Created a bucket with name %s",
            obj_ops_conf["test_2220"]["bucket_name"])
        create_file(
            obj_ops_conf["object_workflow"]["file_path"],
            obj_ops_conf["object_workflow"]["mb_count"])
        LOGGER.info(
            "Uploading an object %s to a bucket %s",
            obj_ops_conf["test_2220"]["obj_name"],
            obj_ops_conf["test_2220"]["bucket_name"])
        resp = s3_test_obj.put_object(
            obj_ops_conf["test_2220"]["bucket_name"],
            obj_ops_conf["test_2220"]["obj_name"],
            obj_ops_conf["object_workflow"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Uploaded an object to a bucket")
        LOGGER.info("Verifying object is successfully uploaded")
        resp = s3_test_obj.object_list(
            obj_ops_conf["test_2220"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_ops_conf["test_2220"]["obj_name"] in resp[1], resp[1]
        LOGGER.info("Verified that object is uploaded successfully")
        LOGGER.info(
            "Deleting object %s from a bucket %s",
            obj_ops_conf["test_2220"]["obj_name"],
            obj_ops_conf["test_2220"]["bucket_name"])
        resp = s3_test_obj.delete_object(
            obj_ops_conf["test_2220"]["bucket_name"],
            obj_ops_conf["test_2220"]["obj_name"])
        assert resp[0], resp[1]
        LOGGER.info("Object deleted from a bucket")
        LOGGER.info("Verifying object is deleted")
        resp = s3_test_obj.object_list(
            obj_ops_conf["test_2220"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_ops_conf["test_2220"]["obj_name"] not in resp[1], resp[1]
        LOGGER.info("Verified that object is deleted from a bucket")
        LOGGER.info("ENDED: Delete object from bucket")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5492", "object_workflow_operations")
    @ CTFailOn(error_handler)
    def test_2221(self):
        """Try deleting object not present."""
        LOGGER.info("STARTED: Try deleting object not present")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_ops_conf["test_2221"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_ops_conf["test_2221"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_ops_conf["test_2221"]["bucket_name"], resp[0]
        LOGGER.info(
            "Created a bucket with name %s",
            obj_ops_conf["test_2221"]["bucket_name"])
        LOGGER.info("Deleting object which is not present")
        resp = s3_test_obj.delete_object(
            obj_ops_conf["test_2221"]["bucket_name"],
            obj_ops_conf["test_2221"]["obj_name"])
        assert resp[0], resp[1]
        LOGGER.info("Performed object delete operation on non exist object")
        LOGGER.info("ENDED: Try deleting object not present")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-8713", "delete_objects")
    @ CTFailOn(error_handler)
    def test_7653(self):
        """Test Delete objects which exists with verbose mode."""
        LOGGER.info(
            "STARTED: Test Delete objects which exists with verbose mode .")
        cfg_7653 = obj_ops_conf["test_7653"]
        bucket_name = cfg_7653["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7653["no_of_objects"])
        LOGGER.info(
            "Step 3: Deleting %s objects from bucket",
            cfg_7653["no_of_objects"])
        resp = s3_test_obj.delete_multiple_objects(bucket_name, obj_list)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Deleted %s objects from bucket",
            cfg_7653["no_of_objects"])
        LOGGER.info(
            "Step 4: Listing objects of a bucket to verify all objects are deleted")
        resp = s3_test_obj.object_list(bucket_name)
        assert resp[0], resp[1]
        assert len(resp[1]) == 0, resp[1]
        LOGGER.info(
            "Step 4: Listed objects and verified that all objects are deleted successfully")
        LOGGER.info(
            "ENDED: Test Delete objects which exists with verbose mode .")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-8714", "delete_objects")
    @ CTFailOn(error_handler)
    def test_7655(self):
        """Delete objects mentioning object which doesn't exists as well with quiet mode."""
        LOGGER.info(
            "STARTED: Delete objects mentioning object "
            "which doesn't exists as well with quiet mode.")
        cfg_7655 = obj_ops_conf["test_7655"]
        bucket_name = cfg_7655["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7655["no_of_objects"])
        # Adding a dummy object to the object list which isn't uploaded to
        # bucket
        obj_list.append(obj_ops_conf['object_workflow']['obj_name_prefix'],
                        str(int(time.time())))
        LOGGER.info(
            "Step 3: Deleting all existing objects along with one non existing object from bucket "
            "with quiet mode")
        resp = s3_test_obj.delete_multiple_objects(
            bucket_name, obj_list, quiet=True)
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Deleting all existing objects along with one non existing object from bucket "
            "with quiet mode")
        LOGGER.info(
            "Step 4: Listing objects of a bucket to verify all objects are deleted")
        resp = s3_test_obj.object_list(bucket_name)
        assert resp[0], resp[1]
        assert len(resp[1]) == 0, resp[1]
        LOGGER.info(
            "Step 4: Listed objects and verified that all objects are deleted successfully")
        LOGGER.info(
            "ENDED: Delete objects mentioning object which doesn't exists as well with quiet mode.")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-8175", "delete_objects")
    def test_7656(self):
        """Delete objects and mention 1001 objects."""
        LOGGER.info("STARTED: Delete objects and mention 1001 objects.")
        cfg_7656 = obj_ops_conf["test_7656"]
        bucket_name = cfg_7656["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7656["no_of_objects"])
        LOGGER.info(
            "Step 3: Deleting %s objects from a bucket",
            cfg_7656["del_obj_cnt"])
        try:
            s3_test_obj.delete_multiple_objects(
                bucket_name, obj_list[:cfg_7656["del_obj_cnt"]])
        except CTException as error:
            LOGGER.error(error.message)
            assert cfg_7656["err_message"] in error.message, error.message
        LOGGER.info(
            "Step 3: Deleting %s objects from a bucket failed with %s",
            cfg_7656["del_obj_cnt"],
            cfg_7656["err_message"])
        LOGGER.info("ENDED: Delete objects and mention 1001 objects.")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-8716", "delete_objects")
    @ CTFailOn(error_handler)
    def test_7657(self):
        """Delete objects and mention 1000 objects."""
        LOGGER.info("STARTED: Delete objects and mention 1000 objects.")
        cfg_7657 = obj_ops_conf["test_7657"]
        bucket_name = cfg_7657["bucket_name"]
        obj_list = self.create_bucket_put_objects(
            bucket_name, cfg_7657["no_of_objects"])
        LOGGER.info(
            "Step 3: Deleting %s objects from a bucket",
            cfg_7657["del_obj_cnt"])
        resp = s3_test_obj.delete_multiple_objects(
            bucket_name, obj_list[:cfg_7657["del_obj_cnt"]])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Deleted %s objects from a bucket",
            cfg_7657["del_obj_cnt"])
        LOGGER.info(
            "Step 4: Listing objects to verify %s objects are deleted",
            cfg_7657["del_obj_cnt"])
        resp = s3_test_obj.object_list(bucket_name)
        assert resp[0], resp[1]
        no_obj_left = cfg_7657["no_of_objects"] - cfg_7657["del_obj_cnt"]
        assert len(resp[1]) == no_obj_left, resp[1]
        LOGGER.info(
            "Step 4: Listed objects and verified that %s objects are deleted successfully",
            cfg_7657["del_obj_cnt"])
        LOGGER.info("ENDED: Delete objects and mention 1000 objects.")
