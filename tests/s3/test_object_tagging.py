#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Object Tagging Test Module."""
import os
import logging
import pytest
from libs.s3 import s3_test_lib, s3_tagging_test_lib, s3_multipart_test_lib
from commons.utils.system_utils import create_file, remove_file
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml

LOGGER = logging.getLogger(__name__)
s3_test_obj = s3_test_lib.S3TestLib()
tag_obj = s3_tagging_test_lib.S3TaggingTestLib()
s3_mp_obj = s3_multipart_test_lib.S3MultipartTestLib()

obj_tag_config = read_yaml("config/s3/test_object_tagging.yaml")


class ObjectTagging():
    """Object Tagging Testsuite."""

    @CTFailOn(error_handler)
    def setup_method(self):
        """setup method."""
        bucket_list = s3_test_obj.bucket_list()
        pref_list = [
            each_bucket for each_bucket in bucket_list[1] if each_bucket.startswith(
                obj_tag_config["object_tagging"]["bkt_name_prefix"])]
        s3_test_obj.delete_multiple_buckets(pref_list)
        if os.path.exists(obj_tag_config["object_tagging"]["file_path"]):
            remove_file(obj_tag_config["object_tagging"]["file_path"])

    def teardown_method(self):
        """TearDown Method."""
        self.setup_method()

    def create_put_set_object_tag(
            self,
            bucket_name,
            obj_name,
            file_path,
            *args,
            tag_count=1):
        """
        Helper function is used to create bucket, put object and set object tags.

        :param bucket: Name of bucket to be created
        :param obj_name: Name of an object
        :param file_path: Path of the file
        :mb_count: Size of file in MB
        :param key: Key for object tagging
        :param value: Value for object tagging
        :param tag_count: Number of tags to be set
        """
        mb_count = args[0]
        key = args[1]
        value = args[2]
        LOGGER.info("Creating a bucket %s", bucket_name)
        resp = s3_test_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        create_file(file_path, mb_count)
        LOGGER.info(
            "Uploading an object %s to bucket %s",
            obj_name,
            bucket_name)
        resp = s3_test_obj.put_object(bucket_name, obj_name, file_path)
        assert resp[0], resp[1]
        LOGGER.info("Setting tag to an object %s", obj_name)
        resp = tag_obj.set_object_tag(
            bucket_name, obj_name, key, value, tag_count)
        assert resp[0], resp[1]

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5549", "object_tagging")
    @CTFailOn(error_handler)
    def test_2457(self):
        """Verify PUT object tagging."""
        LOGGER.info("Verify PUT object tagging")
        LOGGER.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            obj_tag_config["test_9413"]["bucket_name"],
            obj_tag_config["test_9413"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"],
            obj_tag_config["test_9413"]["key"],
            obj_tag_config["test_9413"]["value"])
        LOGGER.info(
            "Created a bucket, uploaded an object and tag is set for object")
        LOGGER.info("Retrieving tag of an object %s",
                    obj_tag_config["test_9413"]["object_name"])
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9413"]["bucket_name"],
            obj_tag_config["test_9413"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info("Verify PUT object tagging")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5557", "object_tagging")
    @CTFailOn(error_handler)
    def test_2458(self):
        """Verify GET object tagging."""
        LOGGER.info("Verify GET object tagging")
        LOGGER.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            obj_tag_config["test_9414"]["bucket_name"],
            obj_tag_config["test_9414"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"],
            obj_tag_config["test_9414"]["key"],
            obj_tag_config["test_9414"]["value"])
        LOGGER.info(
            "Created a bucket, uploaded an object and tag is set for object")
        LOGGER.info("Retrieving tag of an object %s",
                    obj_tag_config["test_9414"]["object_name"])
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9414"]["bucket_name"],
            obj_tag_config["test_9414"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info("Verify GET object tagging")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5561", "object_tagging")
    @CTFailOn(error_handler)
    def test_2459(self):
        """Verify DELETE object tagging."""
        LOGGER.info("Verify DELETE object tagging")
        LOGGER.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            obj_tag_config["test_9415"]["bucket_name"],
            obj_tag_config["test_9415"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"],
            obj_tag_config["test_9415"]["key"],
            obj_tag_config["test_9415"]["value"])
        LOGGER.info(
            "Created a bucket, uploaded an object and tag is set for object")
        LOGGER.info("Retrieving tag of an object %s",
                    obj_tag_config["test_9415"]["object_name"])
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9415"]["bucket_name"],
            obj_tag_config["test_9415"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info(
            "Deleting tag of an object and verifying tag of a same object")
        resp = tag_obj.delete_object_tagging(
            obj_tag_config["test_9415"]["bucket_name"],
            obj_tag_config["test_9415"]["object_name"])
        assert resp[0], resp[1]
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9415"]["bucket_name"],
            obj_tag_config["test_9415"]["object_name"])
        assert len(
            resp[1]) == obj_tag_config["test_9415"]["tag_length"], resp[1]
        LOGGER.info("Verified that tags are deleted")
        LOGGER.info("Verify DELETE object tagging")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5547", "object_tagging")
    @CTFailOn(error_handler)
    def test_2460(self):
        """Verify put object with tagging support."""
        LOGGER.info("Verify put object with tagging support")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9416"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9416"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_tag_config["test_9416"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9416"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info(
            "Uploading an object %s to a bucket %s with tagging support",
            obj_tag_config["test_9416"]["object_name"],
            obj_tag_config["test_9416"]["bucket_name"])
        resp = tag_obj.put_object_with_tagging(
            obj_tag_config["test_9416"]["bucket_name"],
            obj_tag_config["test_9416"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["test_9416"]["object_tag"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9416"]["object_name"] == resp[1].key, resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info("Verify put object with tagging support")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5555", "object_tagging")
    @CTFailOn(error_handler)
    def test_2461(self):
        """Verify get object with tagging support."""
        LOGGER.info("Verify get object with tagging support")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9417"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9417"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_tag_config["test_9417"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9417"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info(
            "Uploading an object %s to a bucket %s with tagging support",
            obj_tag_config["test_9417"]["object_name"],
            obj_tag_config["test_9417"]["bucket_name"])
        resp = tag_obj.put_object_with_tagging(
            obj_tag_config["test_9417"]["bucket_name"],
            obj_tag_config["test_9417"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["test_9417"]["object_tag"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9417"]["object_name"] == resp[1].key, resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info("Retrieving tag of an object %s",
                    obj_tag_config["test_9417"]["object_name"])
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9417"]["bucket_name"],
            obj_tag_config["test_9417"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info("Verify get object with tagging support")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5553", "object_tagging")
    @CTFailOn(error_handler)
    def test_2462(self):
        """Verify Multipart Upload with tagging support."""
        LOGGER.info("Verify Multipart Upload with tagging support")
        LOGGER.info("Creating a bucket with name %s",
                    obj_tag_config["test_9418"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9418"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_tag_config["test_9418"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9418"]["bucket_name"])
        LOGGER.info("Creating multipart upload with tagging")
        resp = tag_obj.create_multipart_upload_with_tagging(
            obj_tag_config["test_9418"]["bucket_name"],
            obj_tag_config["test_9418"]["object_name"],
            obj_tag_config["test_9418"]["object_tag"])
        assert(resp[0]), resp[1]
        LOGGER.info("Created multipart upload with tagging support")
        LOGGER.info("Performing list multipart uploads")
        resp = s3_mp_obj.list_multipart_uploads(
            obj_tag_config["test_9418"]["bucket_name"])
        assert resp[0], resp[1]
        upload_id = resp[1]["Uploads"][0]["UploadId"]
        LOGGER.info(
            "Performed list multipart upload on a bucket %s",
            obj_tag_config["test_9418"]["bucket_name"])
        LOGGER.info("Uploading parts to a bucket %s",
                    obj_tag_config["test_9418"]["bucket_name"])
        resp = s3_mp_obj.upload_parts(
            upload_id,
            obj_tag_config["test_9418"]["bucket_name"],
            obj_tag_config["test_9418"]["object_name"],
            obj_tag_config["test_9418"]["single_part_size"],
            obj_tag_config["test_9418"]["total_parts"],
            obj_tag_config["object_tagging"]["file_path"])
        assert resp[0], resp[1]
        upload_parts_list = resp[1]
        LOGGER.info(
            "Parts are uploaded to a bucket %s",
            obj_tag_config["test_9418"]["bucket_name"])
        LOGGER.info(
            "Performing list parts of object %s",
            obj_tag_config["test_9418"]["object_name"])
        resp = s3_mp_obj.list_parts(upload_id,
                                    obj_tag_config["test_9418"]["bucket_name"],
                                    obj_tag_config["test_9418"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Performed list parts operation")
        LOGGER.info(
            "Performing complete multipart upload on a bucket %s",
            obj_tag_config["test_9418"]["bucket_name"])
        resp = s3_mp_obj.complete_multipart_upload(
            upload_id,
            upload_parts_list,
            obj_tag_config["test_9418"]["bucket_name"],
            obj_tag_config["test_9418"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Performed complete multipart upload on a bucket %s",
            obj_tag_config["test_9418"]["bucket_name"])
        LOGGER.info("Verify Multipart Upload with tagging support")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5574", "object_tagging")
    @CTFailOn(error_handler)
    def test_2463(self):
        """Add up to 10 or maximum tags with an existing object."""
        LOGGER.info("Add up to 10 or maximum tags with an existing object")
        LOGGER.info(
            "Creating a bucket, uploading an object and setting 10 tags for object")
        self.create_put_set_object_tag(
            obj_tag_config["test_9419"]["bucket_name"],
            obj_tag_config["test_9419"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"],
            obj_tag_config["test_9419"]["key"],
            obj_tag_config["test_9419"]["value"],
            obj_tag_config["test_9419"]["tag_count"])
        LOGGER.info(
            "Created a bucket, uploading an object and setting tag for object")
        LOGGER.info("Retrieving tags of an object")
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9419"]["bucket_name"],
            obj_tag_config["test_9419"]["object_name"])
        assert resp[0], resp[1]
        assert len(
            resp[1]) == obj_tag_config["test_9419"]["tag_count"], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info("Add up to 10 or maximum tags with an existing object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5576", "object_tagging")
    @CTFailOn(error_handler)
    def test_2464(self):
        """Add more than 10 tags to an existing object."""
        LOGGER.info("Add more than 10 tags to an existing object")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9420"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9420"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9420"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9420"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info("Uploading an object %s",
                    obj_tag_config["test_9420"]["object_name"])
        resp = s3_test_obj.put_object(
            obj_tag_config["test_9420"]["bucket_name"],
            obj_tag_config["test_9420"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info("Adding more than 10 tags to an existing object")
        try:
            tag_obj.set_object_tag(
                obj_tag_config["test_9420"]["bucket_name"],
                obj_tag_config["test_9420"]["object_name"],
                obj_tag_config["test_9420"]["key"],
                obj_tag_config["test_9420"]["value"],
                obj_tag_config["test_9420"]["tag_count"])
        except CTException as error:
            assert obj_tag_config["test_9420"]["error_message"] in str(
                error.message), error.message
        LOGGER.info("Add more than 10 tags to an existing object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5564", "object_tagging")
    def test_2465(self):
        """Tag associated with an object must have unique tag keys."""
        LOGGER.info(
            "Tags associated with an object must have unique tag keys.")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9421"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9421"]["bucket_name"])
        assert obj_tag_config["test_9421"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9421"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info("Uploading an object %s",
                    obj_tag_config["test_9421"]["object_name"])
        resp = s3_test_obj.put_object(
            obj_tag_config["test_9421"]["bucket_name"],
            obj_tag_config["test_9421"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info("Adding tags to an existing object with unique keys")
        try:
            tag_obj.set_duplicate_object_tags(
                obj_tag_config["test_9421"]["bucket_name"],
                obj_tag_config["test_9421"]["object_name"],
                obj_tag_config["test_9421"]["key"],
                obj_tag_config["test_9421"]["value"])
        except CTException as error:
            assert obj_tag_config["test_9421"]["error_message"] in str(
                error.message), error.message
        LOGGER.info(
            "Tags associated with an object must have unique tag keys.")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5578", "object_tagging")
    @CTFailOn(error_handler)
    def test_2466(self):
        """Add a tag with duplicate tag values to an existing object."""
        LOGGER.info(
            "Add a tag with duplicate tag values to an existing object")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9422"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9422"]["bucket_name"])
        assert obj_tag_config["test_9422"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9422"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info("Uploading an object %s",
                    obj_tag_config["test_9422"]["object_name"])
        resp = s3_test_obj.put_object(
            obj_tag_config["test_9422"]["bucket_name"],
            obj_tag_config["test_9422"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info(
            "Adding tags to an existing object with duplicate values")
        resp = tag_obj.set_duplicate_object_tags(
            obj_tag_config["test_9422"]["bucket_name"],
            obj_tag_config["test_9422"]["object_name"],
            obj_tag_config["test_9422"]["key"],
            obj_tag_config["test_9422"]["value"],
            obj_tag_config["test_9422"]["duplicate_key"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Tags are added to an existing object with duplicate values")
        LOGGER.info("Retrieving tags of an object")
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9422"]["bucket_name"],
            obj_tag_config["test_9422"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info(
            "Add a tag with duplicate tag values to an existing object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5579", "object_tagging")
    @CTFailOn(error_handler)
    def test_2467(self):
        """A tag key can be up to 128 Unicode characters in length."""
        LOGGER.info(
            "A tag key can be up to 128 Unicode characters in length")
        LOGGER.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            obj_tag_config["test_9423"]["bucket_name"],
            obj_tag_config["test_9423"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"],
            obj_tag_config["test_9423"]["key"],
            obj_tag_config["test_9423"]["value"])
        LOGGER.info(
            "Created a bucket, uploaded an object and tag is set for object")
        LOGGER.info("Retrieving tag of an object %s",
                    obj_tag_config["test_9423"]["object_name"])
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9423"]["bucket_name"],
            obj_tag_config["test_9423"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info(
            "A tag key can be up to 128 Unicode characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5570", "object_tagging")
    def test_2468(self):
        """Create a tag whose key is more than 128 Unicode characters in length."""
        LOGGER.info(
            "Create a tag whose key is more than 128 Unicode characters in length")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9424"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9424"]["bucket_name"])
        assert obj_tag_config["test_9424"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9424"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info("Uploading an object %s",
                    obj_tag_config["test_9424"]["object_name"])
        resp = s3_test_obj.put_object(
            obj_tag_config["test_9424"]["bucket_name"],
            obj_tag_config["test_9424"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info(
            "Adding tags to an existing object whose key is greater than 128 character in length")
        try:
            tag_obj.set_object_tag(
                obj_tag_config["test_9424"]["bucket_name"],
                obj_tag_config["test_9424"]["object_name"],
                obj_tag_config["test_9424"]["key"],
                obj_tag_config["test_9424"]["value"])
        except CTException as error:
            assert obj_tag_config["test_9424"]["error_message"] in str(
                error.message), error.message
        LOGGER.info(
            "Create a tag whose key is more than 128 Unicode characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5572", "object_tagging")
    @CTFailOn(error_handler)
    def test_2469(self):
        """Create a tag having tag values up to 256 Unicode characters in length."""
        LOGGER.info(
            "Create a tag having tag values up to 256 Unicode characters in length")
        LOGGER.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            obj_tag_config["test_9425"]["bucket_name"],
            obj_tag_config["test_9425"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"],
            obj_tag_config["test_9425"]["key"],
            obj_tag_config["test_9425"]["value"])
        LOGGER.info(
            "Created a bucket, uploaded an object and tag is set for object")
        LOGGER.info("Retrieving tag of an object %s",
                    obj_tag_config["test_9425"]["object_name"])
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9425"]["bucket_name"],
            obj_tag_config["test_9425"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info(
            "Create a tag having tag values up to 256 Unicode characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5571", "object_tagging")
    def test_2470(self):
        """Create a tag having values more than 512 Unicode characters in length."""
        LOGGER.info(
            "Create a tag having values more than 512 Unicode characters in length")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9426"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9426"]["bucket_name"])
        assert obj_tag_config["test_9426"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9426"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info("Uploading an object %s",
                    obj_tag_config["test_9426"]["object_name"])
        resp = s3_test_obj.put_object(
            obj_tag_config["test_9426"]["bucket_name"],
            obj_tag_config["test_9426"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info(
            "Adding tags to an existing object whose value is greater than 512 character in length")
        try:
            tag_obj.set_object_tag(
                obj_tag_config["test_9426"]["bucket_name"],
                obj_tag_config["test_9426"]["object_name"],
                obj_tag_config["test_9426"]["key"],
                obj_tag_config["test_9426"]["value"])
        except CTException as error:
            assert obj_tag_config["test_9426"]["error_message"] in str(
                error.message), error.message
        LOGGER.info(
            "Create a tag having values more than 512 Unicode characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5552", "object_tagging")
    @CTFailOn(error_handler)
    def test_2471(self):
        """Verify Object Tag Keys with case sensitive labels."""
        LOGGER.info("Verify Object Tag Keys with case sensitive labels")
        LOGGER.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            obj_tag_config["test_9427"]["bucket_name"],
            obj_tag_config["test_9427"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"],
            obj_tag_config["test_9427"]["key1"],
            obj_tag_config["test_9427"]["value"])
        LOGGER.info(
            "Created a bucket, uploaded an object and tag is set for object")
        LOGGER.info("Retrieving tag of an object %s",
                    obj_tag_config["test_9427"]["object_name"])
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9427"]["bucket_name"],
            obj_tag_config["test_9427"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info("Setting object tags keys with case sensitive labels")
        resp = tag_obj.set_object_tag(
            obj_tag_config["test_9427"]["bucket_name"],
            obj_tag_config["test_9427"]["object_name"],
            obj_tag_config["test_9427"]["key2"],
            obj_tag_config["test_9427"]["value"])
        assert resp[0], resp[1]
        LOGGER.info("Tags are set to object with case sensitive labesls")
        LOGGER.info("Retrieving object tags after case sensitive labels")
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9427"]["bucket_name"],
            obj_tag_config["test_9427"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tags of an object")
        LOGGER.info("Verify Object Tag Keys with case sensitive labels")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5551", "object_tagging")
    @CTFailOn(error_handler)
    def test_2472(self):
        """Verify Object Tag Values with case sensitive labels."""
        LOGGER.info("Verify Object Tag Values with case sensitive labels")
        LOGGER.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            obj_tag_config["test_9428"]["bucket_name"],
            obj_tag_config["test_9428"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"],
            obj_tag_config["test_9428"]["key"],
            obj_tag_config["test_9428"]["value1"])
        LOGGER.info(
            "Created a bucket, uploaded an object and tag is set for object")
        LOGGER.info("Retrieving tag of an object %s",
                    obj_tag_config["test_9428"]["object_name"])
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9428"]["bucket_name"],
            obj_tag_config["test_9428"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info("Setting object tag values with case sensitive labels")
        resp = tag_obj.set_object_tag(
            obj_tag_config["test_9428"]["bucket_name"],
            obj_tag_config["test_9428"]["object_name"],
            obj_tag_config["test_9428"]["key"],
            obj_tag_config["test_9428"]["value2"])
        assert resp[0], resp[1]
        LOGGER.info("Tags are set to object with case sensitive labesls")
        LOGGER.info("Retrieving object tags after case sensitive labels")
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9428"]["bucket_name"],
            obj_tag_config["test_9428"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tags of an object")
        LOGGER.info("Verify Object Tag Values with case sensitive labels")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5566", "object_tagging")
    @CTFailOn(error_handler)
    def test_2473(self):
        """Create Object tags with valid special characters."""
        LOGGER.info("Create Object tags with valid special characters.")
        LOGGER.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            obj_tag_config["test_9429"]["bucket_name"],
            obj_tag_config["test_9429"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"],
            obj_tag_config["test_9429"]["key"],
            obj_tag_config["test_9429"]["value"])
        LOGGER.info(
            "Created a bucket, uploaded an object and tag is set for object")
        LOGGER.info("Retrieving tag of an object %s",
                    obj_tag_config["test_9429"]["object_name"])
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9429"]["bucket_name"],
            obj_tag_config["test_9429"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info("Create Object tags with valid special characters.")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5569", "object_tagging")
    def test_2474(self):
        """Create multiple tags with tag keys having invalid special characters."""
        LOGGER.info(
            "Create multiple tags with tag keys having invalid special characters")
        invalid_chars_list = obj_tag_config["test_9430"]["invalid_chars_list"]
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9430"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9430"]["bucket_name"])
        assert obj_tag_config["test_9430"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9430"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info(
            "Uploading an object %s to a bucket %s",
            obj_tag_config["test_9430"]["object_name"],
            obj_tag_config["test_9430"]["bucket_name"])
        resp = s3_test_obj.put_object(
            obj_tag_config["test_9430"]["bucket_name"],
            obj_tag_config["test_9430"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        for each_char in invalid_chars_list:
            invalid_key = "{0}{1}{2}".format(
                obj_tag_config["test_9430"]["key"],
                each_char,
                obj_tag_config["test_9430"]["key"])
            LOGGER.info(
                "Setting object tags with invalid key %s", each_char)
            try:
                tag_obj.set_object_tag(
                    obj_tag_config["test_9430"]["bucket_name"],
                    obj_tag_config["test_9430"]["object_name"],
                    invalid_key,
                    obj_tag_config["test_9430"]["value"])
            except CTException as error:
                assert obj_tag_config["test_9430"]["error_message"] \
                    in str(error.message), error.message
        LOGGER.info(
            "Create multiple tags with tag keys having invalid special characters")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5568", "object_tagging")
    def test_2475(self):
        """Create multiple tags with tag values having invalid special characters."""
        LOGGER.info(
            "Create multiple tags with tag values having invalid special characters")
        invalid_chars_list = obj_tag_config["test_9431"]["invalid_chars_list"]
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9431"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9431"]["bucket_name"])
        assert obj_tag_config["test_9431"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9431"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info(
            "Uploading an object %s to a bucket %s",
            obj_tag_config["test_9431"]["object_name"],
            obj_tag_config["test_9431"]["bucket_name"])
        resp = s3_test_obj.put_object(
            obj_tag_config["test_9431"]["bucket_name"],
            obj_tag_config["test_9431"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        for each_char in invalid_chars_list:
            invalid_value = "{0}{1}{2}".format(
                obj_tag_config["test_9431"]["value"],
                each_char,
                obj_tag_config["test_9431"]["value"])
            LOGGER.info(
                "Setting object tags with invalid key %s", each_char)
            try:
                tag_obj.set_object_tag(
                    obj_tag_config["test_9431"]["bucket_name"],
                    obj_tag_config["test_9431"]["object_name"],
                    obj_tag_config["test_9431"]["key"],
                    invalid_value)
            except CTException as error:
                assert obj_tag_config["test_9431"]["error_message"] in \
                    str(error.message), error.message
        LOGGER.info(
            "Create multiple tags with tag values having invalid special characters")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5567", "object_tagging")
    @ CTFailOn(error_handler)
    def test_2476(self):
        """Create Object tags with invalid (characters o/s the allowed set) special characters."""
        LOGGER.info(
            "Create Object tags with invalid "
            "(characters outside the allowed set) special characters")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9432"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9432"]["bucket_name"])
        assert obj_tag_config["test_9432"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9432"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info(
            "Uplading an object %s to a bucket %s",
            obj_tag_config["test_9432"]["object_name"],
            obj_tag_config["test_9432"]["bucket_name"])
        resp = s3_test_obj.put_object(
            obj_tag_config["test_9432"]["bucket_name"],
            obj_tag_config["test_9432"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info("Setting object tag with invalid character")
        resp = tag_obj.set_object_tag_invalid_char(
            obj_tag_config["test_9432"]["bucket_name"],
            obj_tag_config["test_9432"]["object_name"],
            obj_tag_config["test_9432"]["key"],
            obj_tag_config["test_9432"]["value"])
        assert resp[0], resp[1]
        LOGGER.info("Tags with invalid character is set to object")
        LOGGER.info("Retrieving tags of an object")
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9432"]["bucket_name"],
            obj_tag_config["test_9432"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info(
            "Create Object tags with invalid "
            "(characters outside the allowed set) special characters")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5565", "object_tagging")
    @ CTFailOn(error_handler)
    def test_2477(self):
        """PUT object when object with same name already present in bucket with tag support."""
        LOGGER.info(
            "PUT object when object with same name already present in bucket with tag support")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9433"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9433"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_tag_config["test_9433"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9433"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info(
            "Uploading an object with tagging suport to an existing bucket")
        resp = tag_obj.put_object_with_tagging(
            obj_tag_config["test_9433"]["bucket_name"],
            obj_tag_config["test_9433"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["test_9433"]["object_tag"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9433"]["object_name"] == resp[1].key, resp[1]
        LOGGER.info("Object is uploaded with tagging support")
        LOGGER.info("Retrieving tags of an object")
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9433"]["bucket_name"],
            obj_tag_config["test_9433"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info(
            "Uploading object tag with same name in an existing bucket")
        resp = tag_obj.put_object_with_tagging(
            obj_tag_config["test_9433"]["bucket_name"],
            obj_tag_config["test_9433"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["test_9433"]["object_tag"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9433"]["object_name"] == resp[1].key, resp[1]
        LOGGER.info("Object tags with same name is uploaded")
        LOGGER.info("Retrieving duplicate object tags")
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9433"]["bucket_name"],
            obj_tag_config["test_9433"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved duplicate object tags")
        LOGGER.info(
            "PUT object when object with same name already present in bucket with tag support")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5562", "object_tagging")
    @ CTFailOn(error_handler)
    def test_2478(self):
        """Verification of max. no. of Objects user can upload with max no. of tags per Object."""
        LOGGER.info(
            "Verification of max. no. of Objects user can upload with max no. of tags per Object")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9434"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9434"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_tag_config["test_9434"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9434"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info("Uploading objects to an existing bucket")
        for each_obj in range(obj_tag_config["test_9434"]["object_count"]):
            obj = "{0}{1}".format(
                obj_tag_config["test_9434"]["object_name"],
                str(each_obj))
            resp = s3_test_obj.put_object(
                obj_tag_config["test_9434"]["bucket_name"],
                obj,
                obj_tag_config["object_tagging"]["file_path"])
            assert resp[0], resp[1]
        LOGGER.info("Objects are uploaded to an existing bucket")
        LOGGER.info("Performing list object operations")
        resp = s3_test_obj.object_list(
            obj_tag_config["test_9434"]["bucket_name"])
        assert resp[0], resp[1]
        LOGGER.info("Objects are listed")
        for each_obj in resp[1]:
            LOGGER.info("Setting tag to an object %s", each_obj)
            resp = tag_obj.set_object_tag(
                obj_tag_config["test_9434"]["bucket_name"],
                each_obj,
                obj_tag_config["test_9434"]["key"],
                obj_tag_config["test_9434"]["value"],
                obj_tag_config["test_9434"]["tag_count"])
            assert resp[0], resp[1]
            LOGGER.info("Tag is set to an object %s", each_obj)
            LOGGER.info("Retrieving tags of an object")
            resp = tag_obj.get_object_tags(
                obj_tag_config["test_9434"]["bucket_name"], each_obj)
            assert resp[0], resp[1]
            assert len(
                resp[1]) == obj_tag_config["test_9434"]["tag_count"], resp[1]
            LOGGER.info("Retrieved tags of an object")
        LOGGER.info(
            "Verification of max. no. of Objects user can upload with max no. of tags per Object")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5573", "object_tagging")
    @ CTFailOn(error_handler)
    def test_2479(self):
        """Add user defined metadata and Object tags while adding the new object to the bucket."""
        LOGGER.info(
            "Add user defined metadata and Object tags while adding the new object to the bucket")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9435"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9435"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_tag_config["test_9435"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9435"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info(
            "Uploading an object with user defined metadata and tags")
        resp = tag_obj.put_object_with_tagging(
            obj_tag_config["test_9435"]["bucket_name"],
            obj_tag_config["test_9435"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["test_9435"]["object_tag"],
            obj_tag_config["test_9435"]["key"],
            obj_tag_config["test_9435"]["value"])
        assert resp[0], resp[1]
        assert resp[1].key == obj_tag_config["test_9435"]["object_name"], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info("Retrieving tags of an object")
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9435"]["bucket_name"],
            obj_tag_config["test_9435"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info(
            "Add user defined metadata and Object tags while adding the new object to the bucket")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5575", "object_tagging")
    @ CTFailOn(error_handler)
    def test_2480(self):
        """Add or update user defined metadata and verify the Object Tags."""
        LOGGER.info(
            "Add or update user defined metadata and verify the Object Tags")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9436"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9436"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_tag_config["test_9436"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9436"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info(
            "Uploading an object with user defined metadata and tags")
        resp = tag_obj.put_object_with_tagging(
            obj_tag_config["test_9436"]["bucket_name"],
            obj_tag_config["test_9436"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["test_9436"]["object_tag"],
            obj_tag_config["test_9436"]["key1"],
            obj_tag_config["test_9436"]["value1"])
        assert resp[0], resp[1]
        assert resp[1].key == obj_tag_config["test_9436"]["object_name"], resp[1]
        LOGGER.info(
            "Object is uploaded to a bucket with user defined metadata")
        LOGGER.info("Retrieving tags of an object")
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9436"]["bucket_name"],
            obj_tag_config["test_9436"]["object_name"])
        assert resp[0], resp[1]
        LOGGER.info("Retrieving object info")
        resp = s3_test_obj.object_info(
            obj_tag_config["test_9436"]["bucket_name"],
            obj_tag_config["test_9436"]["object_name"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9436"]["key1"] in resp[1]["Metadata"], resp[1]
        LOGGER.info("Retrieved info of an object")
        LOGGER.info("Updating user defined metadata of an existing object")
        resp = s3_test_obj.put_object(
            obj_tag_config["test_9436"]["bucket_name"],
            obj_tag_config["test_9436"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["test_9436"]["key2"],
            obj_tag_config["test_9436"]["value2"])
        assert resp[0], resp[1]
        LOGGER.info("Updated user defined metadata of an existing object")
        LOGGER.info("Retrieving object info after updating metadata")
        resp = s3_test_obj.object_info(
            obj_tag_config["test_9436"]["bucket_name"],
            obj_tag_config["test_9436"]["object_name"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9436"]["key2"] in resp[1]["Metadata"], resp[1]
        LOGGER.info("Retrieved object info after updating metadata")
        LOGGER.info("Retrieving tags of an object after updating metadata")
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9436"]["bucket_name"],
            obj_tag_config["test_9436"]["object_name"])
        assert len(resp[1]) == obj_tag_config["test_9436"]["tag_len"], resp[1]
        LOGGER.info("Retrieved tags of an object after updating metadata")
        LOGGER.info(
            "Add or update user defined metadata and verify the Object Tags")

    @ pytest.mark.parallel
    @ pytest.mark.s3
    @ pytest.mark.tags("TEST-5563", "object_tagging")
    @ CTFailOn(error_handler)
    def test_2481(self):
        """Upload Object with user definced metadata upto 2KB and upto 10 object tags."""
        LOGGER.info(
            "Upload Object with user definced metadata upto 2KB and upto 10 object tags")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9437"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9437"]["bucket_name"])
        assert resp[0], resp[1]
        assert resp[1] == obj_tag_config["test_9437"]["bucket_name"], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9437"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info(
            "Uploading an object with user defined metadata and tags")
        resp = tag_obj.put_object_with_tagging(
            obj_tag_config["test_9437"]["bucket_name"],
            obj_tag_config["test_9437"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["test_9437"]["object_tag"],
            obj_tag_config["test_9437"]["key"],
            obj_tag_config["test_9437"]["value"])
        assert resp[0], resp[1]
        assert resp[1].key == obj_tag_config["test_9437"]["object_name"], resp[1]
        LOGGER.info("Uploaded an object with user defined metadata and tags")
        LOGGER.info("Retrieving tag of an object")
        resp = tag_obj.get_object_tags(
            obj_tag_config["test_9437"]["bucket_name"],
            obj_tag_config["test_9437"]["object_name"])
        assert resp[0], resp[1]
        assert len(
            resp[1]) == obj_tag_config["test_9437"]["tag_count"], resp[1]
        LOGGER.info("Retrieved tag of an object")
        LOGGER.info(
            "Upload Object with user definced metadata upto 2KB and upto 10 object tags")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5577", "object_tagging")
    def test_2482(self):
        """Add maximum nos. of Object tags >100 using json file."""
        LOGGER.info("Add maximum nos. of Object tags >100 using json file")
        LOGGER.info(
            "Creating a bucket with name %s",
            obj_tag_config["test_9438"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9438"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9438"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9438"]["bucket_name"])
        create_file(
            obj_tag_config["object_tagging"]["file_path"],
            obj_tag_config["object_tagging"]["mb_count"])
        LOGGER.info(
            "Uploading an object %s to a bucket %s",
            obj_tag_config["test_9438"]["object_name"],
            obj_tag_config["test_9438"]["bucket_name"])
        resp = s3_test_obj.put_object(
            obj_tag_config["test_9438"]["bucket_name"],
            obj_tag_config["test_9438"]["object_name"],
            obj_tag_config["object_tagging"]["file_path"])
        assert resp[0], resp[1]
        LOGGER.info("Object is uploaded to a bucket")
        LOGGER.info("Adding tags to an existing object")
        try:
            tag_obj.set_object_tag(
                obj_tag_config["test_9438"]["bucket_name"],
                obj_tag_config["test_9438"]["object_name"],
                obj_tag_config["test_9438"]["key"],
                obj_tag_config["test_9438"]["value"],
                obj_tag_config["test_9438"]["tag_count"])
        except CTException as error:
            assert obj_tag_config["test_9438"]["error_message"] in str(
                error.message), error.message
        LOGGER.info("Add maximum nos. of Object tags >100 using json file")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5548", "object_tagging")
    def test_2483(self):
        """Verify PUT object tagging to non-existing object."""
        LOGGER.info("verify PUT object tagging to non-existing object")
        LOGGER.info("Creating a bucket with name %s",
                    obj_tag_config["test_9439"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9439"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9439"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9439"]["bucket_name"])
        LOGGER.info("Setting tag to non existing object")
        try:
            tag_obj.set_object_tag(
                obj_tag_config["test_9439"]["bucket_name"],
                obj_tag_config["test_9439"]["object_name"],
                obj_tag_config["test_9439"]["key"],
                obj_tag_config["test_9439"]["value"])
        except CTException as error:
            assert obj_tag_config["test_9439"]["error_message"] in str(
                error.message), error.message
        LOGGER.info("verify PUT object tagging to non-existing object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5556", "object_tagging")
    def test_2484(self):
        """Verify GET object tagging to non-existing object."""
        LOGGER.info("verify GET object tagging to non-existing object")
        LOGGER.info("Creating a bucket with name %s",
                    obj_tag_config["test_9440"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9440"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9440"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9440"]["bucket_name"])
        LOGGER.info("Retrieving tags from non existing object")
        try:
            tag_obj.get_object_tags(
                obj_tag_config["test_9440"]["bucket_name"],
                obj_tag_config["test_9440"]["object_name"])
        except CTException as error:
            assert obj_tag_config["test_9440"]["error_message"] in str(
                error.message), error.message
        LOGGER.info("verify GET object tagging to non-existing object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5559", "object_tagging")
    def test_2485(self):
        """Verify DELETE object tagging to non-existing object."""
        LOGGER.info("verify DELETE object tagging to non-existing object")
        LOGGER.info("Creating a bucket with name %s",
                    obj_tag_config["test_9441"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9441"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9441"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9441"]["bucket_name"])
        LOGGER.info("Deleting tags of non-existing object")
        try:
            tag_obj.delete_object_tagging(
                obj_tag_config["test_9441"]["bucket_name"],
                obj_tag_config["test_9441"]["object_name"])
        except CTException as error:
            assert obj_tag_config["test_9441"]["error_message"] in str(
                error.message), error.message
        LOGGER.info("verify DELETE object tagging to non-existing object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5546", "object_tagging")
    def test_2486(self):
        """Verify put object with tagging support to non-existing object."""
        LOGGER.info(
            "Verify put object with tagging support to non-existing object")
        LOGGER.info("Creating a bucket with name %s",
                    obj_tag_config["test_9442"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9442"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9442"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9442"]["bucket_name"])
        LOGGER.info("Setting tags to non-existing object")
        try:
            tag_obj.set_object_tag(
                obj_tag_config["test_9442"]["bucket_name"],
                obj_tag_config["test_9442"]["object_name"],
                obj_tag_config["test_9442"]["key"],
                obj_tag_config["test_9442"]["value"])
        except CTException as error:
            assert obj_tag_config["test_9442"]["error_message"] in str(
                error.message), error.message
        LOGGER.info(
            "Verify put object with tagging support to non-existing object")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-5554", "object_tagging")
    def test_2487(self):
        """Verify get object with tagging support to non-existing object."""
        LOGGER.info(
            "Verify get object with tagging support to non-existing object")
        LOGGER.info("Creating a bucket with name %s",
                    obj_tag_config["test_9443"]["bucket_name"])
        resp = s3_test_obj.create_bucket(
            obj_tag_config["test_9443"]["bucket_name"])
        assert resp[0], resp[1]
        assert obj_tag_config["test_9443"]["bucket_name"] == resp[1], resp[1]
        LOGGER.info(
            "Bucket is created with name %s",
            obj_tag_config["test_9443"]["bucket_name"])
        LOGGER.info("Retrieving tags from non existing object")
        try:
            tag_obj.get_object_with_tagging(
                obj_tag_config["test_9443"]["bucket_name"],
                obj_tag_config["test_9443"]["object_name"])
        except CTException as error:
            assert obj_tag_config["test_9443"]["error_message"] in str(
                error.message), error.message
        LOGGER.info(
            "Verify get object with tagging support to non-existing object")
