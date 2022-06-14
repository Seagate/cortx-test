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

"""Object Tagging Test Module."""
import os
import logging
import time
from time import perf_counter
import urllib.parse

import pytest

from commons.ct_fail_on import CTFailOn
from commons import error_messages as errmsg
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils.system_utils import create_file
from commons.utils.system_utils import make_dirs
from commons.utils.system_utils import path_exists
from commons.utils.system_utils import remove_file
from config.s3 import S3_OBJ_TST
from config.s3 import S3_CFG
from libs.s3 import s3_test_lib
from libs.s3 import s3_tagging_test_lib
from libs.s3 import s3_multipart_test_lib


# pylint: disable-msg=too-many-instance-attributes
class TestObjectTagging:
    """Object Tagging Testsuite."""

    # pylint: disable=attribute-defined-outside-init
    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.s3_test_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.tag_obj = s3_tagging_test_lib.S3TaggingTestLib(
            endpoint_url=S3_CFG["s3_url"])
        self.s3_mp_obj = s3_multipart_test_lib.S3MultipartTestLib(
            endpoint_url=S3_CFG["s3_url"])
        self.object_name = "{}{}".format("objtag", time.perf_counter_ns())
        self.bucket_name = "{}{}".format("objtagbkt", time.perf_counter_ns())
        self.folder_path = os.path.join(TEST_DATA_FOLDER, "TestObjectTagging")
        self.file_name = "{}{}".format("obj_tag", time.perf_counter_ns())
        self.file_path = os.path.join(self.folder_path, self.file_name)
        if not path_exists(self.folder_path):
            resp = make_dirs(self.folder_path)
            self.log.info("Created path: %s", resp)

    def teardown_method(self):
        """setup method."""
        self.log.info("STARTED:  Teardown Method")
        self.s3_test_obj.delete_bucket(self.bucket_name, force=True)
        if os.path.exists(self.file_path):
            remove_file(self.file_path)
        self.log.info("ENDED: Teardown Method")

    def create_put_set_object_tag(
            self,
            bucket_name,
            obj_name,
            file_path,
            **kwargs):
        """
        Helper function is used to create bucket, put object and set object tags.

        :param bucket_name:
        :param bucket_name: Name of bucket to be created
        :param obj_name: Name of an object
        :param file_path: Path of the file
        :mb_count: Size of file in MB
        :param tag_count: Number of tags to be set
        """
        mb_count = kwargs.get("mb_count", None)
        key = kwargs.get("key", None)
        value = kwargs.get("value", None)
        tag_count = kwargs.get("tag_count", 1)
        self.log.info("Creating a bucket %s", bucket_name)
        resp = self.s3_test_obj.create_bucket(bucket_name)
        assert resp[0], resp[1]
        create_file(file_path, mb_count)
        self.log.info(
            "Uploading an object %s to bucket %s",
            obj_name,
            bucket_name)
        resp = self.s3_test_obj.put_object(bucket_name, obj_name, file_path)
        assert resp[0], resp[1]
        self.log.info("Setting tag to an object %s", obj_name)
        resp = self.tag_obj.set_object_tag(
            bucket_name, obj_name, key, value, tag_count=tag_count)
        assert resp[0], resp[1]

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5549")
    @CTFailOn(error_handler)
    def test_verify_putobj_tagging_2457(self):
        """Verify PUT object tagging."""
        self.log.info("Verify PUT object tagging")
        self.log.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            self.bucket_name,
            self.object_name,
            self.file_path,
            mb_count=S3_OBJ_TST["s3_object"]["mb_count"],
            key=S3_OBJ_TST["s3_object"]["key"],
            value=S3_OBJ_TST["test_9413"]["value"])
        self.log.info(
            "Created a bucket, uploaded an object and tag is set for object")
        self.log.info("Retrieving tag of an object %s",
                      self.object_name)
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info("Verify PUT object tagging")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5557")
    @CTFailOn(error_handler)
    def test_getobj_tagging_2458(self):
        """Verify GET object tagging."""
        self.log.info("Verify GET object tagging")
        self.log.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            self.bucket_name,
            self.object_name,
            self.file_path,
            mb_count=S3_OBJ_TST["s3_object"]["mb_count"],
            key=S3_OBJ_TST["s3_object"]["key"],
            value=S3_OBJ_TST["test_9414"]["value"])
        self.log.info(
            "Created a bucket, uploaded an object and tag is set for object")
        self.log.info("Retrieving tag of an object %s",
                      self.object_name)
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info("Verify GET object tagging")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5561")
    @CTFailOn(error_handler)
    def test_delobj_tagging_2459(self):
        """Verify DELETE object tagging."""
        self.log.info("Verify DELETE object tagging")
        self.log.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            self.bucket_name,
            self.object_name,
            self.file_path,
            mb_count=S3_OBJ_TST["s3_object"]["mb_count"],
            key=S3_OBJ_TST["s3_object"]["key"],
            value=S3_OBJ_TST["test_9415"]["value"])
        self.log.info(
            "Created a bucket, uploaded an object and tag is set for object")
        self.log.info("Retrieving tag of an object %s",
                      self.object_name)
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info(
            "Deleting tag of an object and verifying tag of a same object")
        resp = self.tag_obj.delete_object_tagging(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert len(
            resp[1]) == S3_OBJ_TST["test_9415"]["tag_length"], resp[1]
        self.log.info("Verified that tags are deleted")
        self.log.info("Verify DELETE object tagging")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5547")
    @CTFailOn(error_handler)
    def test_putobj_taggingsupport_2460(self):
        """Verify put object with tagging support."""
        self.log.info("Verify put object with tagging support")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object %s to a bucket %s with tagging support",
            self.object_name,
            self.bucket_name)
        resp = self.tag_obj.put_object_with_tagging(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["test_9416"]["object_tag"])
        assert resp[0], resp[1]
        assert self.object_name == resp[1].key, resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Verify put object with tagging support")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5555")
    @CTFailOn(error_handler)
    def test_getobj_taggingsupport_2461(self):
        """Verify get object with tagging support."""
        self.log.info("Verify get object with tagging support")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object %s to a bucket %s with tagging support",
            self.object_name,
            self.bucket_name)
        resp = self.tag_obj.put_object_with_tagging(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["test_9417"]["object_tag"])
        assert resp[0], resp[1]
        assert self.object_name == resp[1].key, resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Retrieving tag of an object %s",
                      self.object_name)
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info("Verify get object with tagging support")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5553")
    @CTFailOn(error_handler)
    def test_multipartupload_taggingsupport_2462(self):
        """Verify Multipart Upload with tagging support."""
        self.log.info("Verify Multipart Upload with tagging support")
        self.log.info("Creating a bucket with name %s",
                      self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        self.log.info("Creating multipart upload with tagging")
        resp = self.tag_obj.create_multipart_upload_with_tagging(
            self.bucket_name,
            self.object_name,
            S3_OBJ_TST["test_9418"]["object_tag"])
        assert (resp[0]), resp[1]
        self.log.info("Created multipart upload with tagging support")
        self.log.info("Performing list multipart uploads")
        resp = self.s3_mp_obj.list_multipart_uploads(
            self.bucket_name)
        assert resp[0], resp[1]
        upload_id = resp[1]["Uploads"][0]["UploadId"]
        self.log.info(
            "Performed list multipart upload on a bucket %s",
            self.bucket_name)
        self.log.info("Uploading parts to a bucket %s",
                      self.bucket_name)
        resp = self.s3_mp_obj.upload_parts(
            upload_id,
            self.bucket_name,
            self.object_name,
            S3_OBJ_TST["test_9418"]["single_part_size"],
            total_parts=S3_OBJ_TST["test_9418"]["total_parts"],
            multipart_obj_path=self.file_path)
        assert resp[0], resp[1]
        upload_parts_list = resp[1]
        self.log.info(
            "Parts are uploaded to a bucket %s",
            self.bucket_name)
        self.log.info(
            "Performing list parts of object %s",
            self.object_name)
        resp = self.s3_mp_obj.list_parts(upload_id,
                                         self.bucket_name,
                                         self.object_name)
        assert resp[0], resp[1]
        self.log.info("Performed list parts operation")
        self.log.info(
            "Performing complete multipart upload on a bucket %s",
            self.bucket_name)
        resp = self.s3_mp_obj.complete_multipart_upload(
            upload_id,
            upload_parts_list,
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info(
            "Performed complete multipart upload on a bucket %s",
            self.bucket_name)
        self.log.info("Verify Multipart Upload with tagging support")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.regression
    @pytest.mark.tags("TEST-5574")
    @CTFailOn(error_handler)
    def test_add_maximum_tags_existing_object_2463(self):
        """Add up to 10 or maximum tags with an existing object."""
        self.log.info(
            "Add up to 10 or maximum tags with an existing object")
        self.log.info(
            "Creating a bucket, uploading an object and setting 10 tags for object")
        self.create_put_set_object_tag(
            self.bucket_name,
            self.object_name,
            self.file_path,
            mb_count=S3_OBJ_TST["s3_object"]["mb_count"],
            key=S3_OBJ_TST["s3_object"]["key"],
            value=S3_OBJ_TST["test_9419"]["value"],
            tag_count=S3_OBJ_TST["test_9419"]["tag_count"])
        self.log.info(
            "Created a bucket, uploading an object and setting tag for object")
        self.log.info("Retrieving tags of an object")
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        assert len(
            resp[1]) == S3_OBJ_TST["test_9419"]["tag_count"], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info(
            "Add up to 10 or maximum tags with an existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5576")
    @CTFailOn(error_handler)
    def test_add10tags_existingobject_2464(self):
        """Add more than 10 tags to an existing object."""
        self.log.info("Add more than 10 tags to an existing object")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Uploading an object %s",
                      self.object_name)
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Adding more than 10 tags to an existing object")
        try:
            self.tag_obj.set_object_tag(
                self.bucket_name,
                self.object_name,
                S3_OBJ_TST["s3_object"]["key"],
                S3_OBJ_TST["test_9420"]["value"],
                tag_count=S3_OBJ_TST["test_9420"]["tag_count"])
        except CTException as error:
            assert errmsg.S3_BKT_INVALID_TAG_ERR in str(error.message), error.message
        self.log.info("Add more than 10 tags to an existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5564")
    @CTFailOn(error_handler)
    def test_unique_tagkeys_2465(self):
        """Tag associated with an object must have unique tag keys."""
        self.log.info(
            "Tags associated with an object must have unique tag keys.")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Uploading an object %s",
                      self.object_name)
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Adding tags to an existing object with unique keys")
        try:
            self.tag_obj.set_duplicate_object_tags(
                self.bucket_name,
                self.object_name,
                S3_OBJ_TST["s3_object"]["key"],
                S3_OBJ_TST["test_9421"]["value"])
        except CTException as error:
            assert errmsg.MALFORMED_XML_ERR in str(error.message), error.message
        self.log.info(
            "Tags associated with an object must have unique tag keys.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5578")
    @CTFailOn(error_handler)
    def test_add_duplicate_tags_2466(self):
        """Add a tag with duplicate tag values to an existing object."""
        self.log.info(
            "Add a tag with duplicate tag values to an existing object")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Uploading an object %s",
                      self.object_name)
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info(
            "Adding tags to an existing object with duplicate values")
        resp = self.tag_obj.set_duplicate_object_tags(
            self.bucket_name,
            self.object_name,
            S3_OBJ_TST["s3_object"]["key"],
            S3_OBJ_TST["test_9422"]["value"],
            duplicate_key=S3_OBJ_TST["test_9422"]["duplicate_key"])
        assert resp[0], resp[1]
        self.log.info(
            "Tags are added to an existing object with duplicate values")
        self.log.info("Retrieving tags of an object")
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info(
            "Add a tag with duplicate tag values to an existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5579")
    @CTFailOn(error_handler)
    def test_key_128unicodechars_2467(self):
        """A tag key can be up to 128 Unicode characters in length."""
        self.log.info(
            "A tag key can be up to 128 Unicode characters in length")
        self.log.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            self.bucket_name,
            self.object_name,
            self.file_path,
            mb_count=S3_OBJ_TST["s3_object"]["mb_count"],
            key=S3_OBJ_TST["test_9423"]["key"],
            value=S3_OBJ_TST["test_9423"]["value"])
        self.log.info(
            "Created a bucket, uploaded an object and tag is set for object")
        self.log.info("Retrieving tag of an object %s",
                      self.object_name)
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info(
            "A tag key can be up to 128 Unicode characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5570")
    @CTFailOn(error_handler)
    def test_key_with_more_than_128_unichargs_2468(self):
        """Create a tag whose key is more than 128 Unicode characters in length."""
        self.log.info(
            "Create a tag whose key is more than 128 Unicode characters in length")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Uploading an object %s",
                      self.object_name)
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info(
            "Adding tags to an existing object whose key is greater than 128 character in length")
        try:
            self.tag_obj.set_object_tag(
                self.bucket_name,
                self.object_name,
                S3_OBJ_TST["s3_object"]["key"],
                S3_OBJ_TST["test_9424"]["value"])
        except CTException as error:
            assert errmsg.S3_BKT_INVALID_TAG_ERR in str(error.message), error.message
        self.log.info(
            "Create a tag whose key is more than 128 Unicode characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5572")
    @CTFailOn(error_handler)
    def test_tagvalue256chars_2469(self):
        """Create a tag having tag values up to 256 Unicode characters in length."""
        self.log.info(
            "Create a tag having tag values up to 256 Unicode characters in length")
        self.log.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            self.bucket_name,
            self.object_name,
            self.file_path,
            mb_count=S3_OBJ_TST["s3_object"]["mb_count"],
            key=S3_OBJ_TST["s3_object"]["key"],
            value=S3_OBJ_TST["test_9425"]["value"])
        self.log.info(
            "Created a bucket, uploaded an object and tag is set for object")
        self.log.info("Retrieving tag of an object %s",
                      self.object_name)
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info(
            "Create a tag having tag values up to 256 Unicode characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5571")
    @CTFailOn(error_handler)
    def test_tag_value_512_unichars_2470(self):
        """Create a tag having values more than 512 Unicode characters in length."""
        self.log.info(
            "Create a tag having values more than 512 Unicode characters in length")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Uploading an object %s",
                      self.object_name)
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info(
            "Adding tags to an existing object whose value is greater than 512 character in length")
        try:
            self.tag_obj.set_object_tag(
                self.bucket_name,
                self.object_name,
                S3_OBJ_TST["s3_object"]["key"],
                S3_OBJ_TST["test_9426"]["value"])
        except CTException as error:
            assert errmsg.S3_BKT_INVALID_TAG_ERR in str(error.message), error.message
        self.log.info(
            "Create a tag having values more than 512 Unicode characters in length")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5552")
    @CTFailOn(error_handler)
    def test_tagkeys_labels_2471(self):
        """Verify Object Tag Keys with case sensitive labels."""
        self.log.info("Verify Object Tag Keys with case sensitive labels")
        self.log.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            self.bucket_name,
            self.object_name,
            self.file_path,
            mb_count=S3_OBJ_TST["s3_object"]["mb_count"],
            key=S3_OBJ_TST["test_9427"]["key1"],
            value=S3_OBJ_TST["test_9427"]["value"])
        self.log.info(
            "Created a bucket, uploaded an object and tag is set for object")
        self.log.info("Retrieving tag of an object %s",
                      self.object_name)
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info("Setting object tags keys with case sensitive labels")
        resp = self.tag_obj.set_object_tag(
            self.bucket_name,
            self.object_name,
            S3_OBJ_TST["test_9427"]["key2"],
            S3_OBJ_TST["test_9427"]["value"])
        assert resp[0], resp[1]
        self.log.info("Tags are set to object with case sensitive labesls")
        self.log.info("Retrieving object tags after case sensitive labels")
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tags of an object")
        self.log.info("Verify Object Tag Keys with case sensitive labels")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5551")
    @CTFailOn(error_handler)
    def test_case_sensitive_labels_2472(self):
        """Verify Object Tag Values with case sensitive labels."""
        self.log.info("Verify Object Tag Values with case sensitive labels")
        self.log.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            self.bucket_name,
            self.object_name,
            self.file_path,
            mb_count=S3_OBJ_TST["s3_object"]["mb_count"],
            key=S3_OBJ_TST["s3_object"]["key"],
            value=S3_OBJ_TST["test_9428"]["value1"])
        self.log.info(
            "Created a bucket, uploaded an object and tag is set for object")
        self.log.info("Retrieving tag of an object %s",
                      self.object_name)
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info(
            "Setting object tag values with case sensitive labels")
        resp = self.tag_obj.set_object_tag(
            self.bucket_name,
            self.object_name,
            S3_OBJ_TST["s3_object"]["key"],
            S3_OBJ_TST["test_9428"]["value2"])
        assert resp[0], resp[1]
        self.log.info("Tags are set to object with case sensitive labesls")
        self.log.info("Retrieving object tags after case sensitive labels")
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tags of an object")
        self.log.info("Verify Object Tag Values with case sensitive labels")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5566")
    @CTFailOn(error_handler)
    def test_valid_specialchars_2473(self):
        """Create Object tags with valid special characters."""
        self.log.info("Create Object tags with valid special characters.")
        self.log.info(
            "Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(
            self.bucket_name,
            self.object_name,
            self.file_path,
            mb_count=S3_OBJ_TST["s3_object"]["mb_count"],
            key=S3_OBJ_TST["test_9429"]["key"],
            value=S3_OBJ_TST["test_9429"]["value"])
        self.log.info(
            "Created a bucket, uploaded an object and tag is set for object")
        self.log.info("Retrieving tag of an object %s",
                      self.object_name)
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info("Create Object tags with valid special characters.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5569")
    @CTFailOn(error_handler)
    def test_invalid_specialchars_2474(self):
        """Create multiple tags with tag keys having invalid special characters."""
        self.log.info(
            "Create multiple tags with tag keys having invalid special characters")
        invalid_chars_list = S3_OBJ_TST["test_9430"]["invalid_chars_list"]
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object %s to a bucket %s",
            self.object_name,
            self.bucket_name)
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        for each_char in invalid_chars_list:
            invalid_key = "{0}{1}{2}".format(
                S3_OBJ_TST["s3_object"]["key"],
                each_char,
                S3_OBJ_TST["s3_object"]["key"])
            self.log.info(
                "Setting object tags with invalid key %s", each_char)
            try:
                self.tag_obj.set_object_tag(
                    self.bucket_name,
                    self.object_name,
                    invalid_key,
                    S3_OBJ_TST["test_9430"]["value"])
            except CTException as error:
                assert errmsg.S3_BKT_INVALID_TAG_ERR in str(error.message), error.message
        self.log.info(
            "Create multiple tags with tag keys having invalid special characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5568")
    @CTFailOn(error_handler)
    def test_invalid_specialchars_2475(self):
        """Create multiple tags with tag values having invalid special characters."""
        self.log.info(
            "Create multiple tags with tag values having invalid special characters")
        invalid_chars_list = S3_OBJ_TST["test_9431"]["invalid_chars_list"]
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object %s to a bucket %s",
            self.object_name,
            self.bucket_name)
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        for each_char in invalid_chars_list:
            invalid_value = "{0}{1}{2}".format(
                S3_OBJ_TST["test_9431"]["value"],
                each_char,
                S3_OBJ_TST["test_9431"]["value"])
            self.log.info(
                "Setting object tags with invalid key %s", each_char)
            try:
                self.tag_obj.set_object_tag(
                    self.bucket_name,
                    self.object_name,
                    S3_OBJ_TST["s3_object"]["key"],
                    invalid_value)
            except CTException as error:
                assert errmsg.S3_BKT_INVALID_TAG_ERR in str(error.message), error.message
        self.log.info(
            "Create multiple tags with tag values having invalid special characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5567")
    @CTFailOn(error_handler)
    def test_special_chars_2476(self):
        """Create Object tags with invalid (characters o/s the allowed set) special characters."""
        self.log.info(
            "Create Object tags with invalid "
            "(characters outside the allowed set) special characters")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uplading an object %s to a bucket %s",
            self.object_name,
            self.bucket_name)
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Setting object tag with invalid character")
        resp = self.tag_obj.set_object_tag_invalid_char(
            self.bucket_name,
            self.object_name,
            S3_OBJ_TST["s3_object"]["key"],
            S3_OBJ_TST["test_9432"]["value"])
        assert resp[0], resp[1]
        self.log.info("Tags with invalid character is set to object")
        self.log.info("Retrieving tags of an object")
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info(
            "Create Object tags with invalid "
            "(characters outside the allowed set) special characters")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5565")
    @CTFailOn(error_handler)
    def test_duplicate_name_object_tag_support_2477(self):
        """PUT object when object with same name already present in bucket with tag support."""
        self.log.info(
            "PUT object when object with same name already present in bucket with tag support")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object with tagging suport to an existing bucket")
        resp = self.tag_obj.put_object_with_tagging(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["test_9433"]["object_tag"])
        assert resp[0], resp[1]
        assert self.object_name == resp[1].key, resp[1]
        self.log.info("Object is uploaded with tagging support")
        self.log.info("Retrieving tags of an object")
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info(
            "Uploading object tag with same name in an existing bucket")
        resp = self.tag_obj.put_object_with_tagging(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["test_9433"]["object_tag"])
        assert resp[0], resp[1]
        assert self.object_name == resp[1].key, resp[1]
        self.log.info("Object tags with same name is uploaded")
        self.log.info("Retrieving duplicate object tags")
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved duplicate object tags")
        self.log.info(
            "PUT object when object with same name already present in bucket with tag support")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5562")
    @CTFailOn(error_handler)
    def test_multiple_object_max_tags_2478(self):
        """Verification of multiple no. of Objects user
        can upload with max no. of tags per Object."""
        self.log.info("Verification of multiple no. of Objects user can "
                      "upload with max no. of tags per Object")
        self.log.info("Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Uploading objects to an existing bucket")
        for each_obj in range(S3_OBJ_TST["test_9434"]["object_count"]):
            obj = "{0}{1}".format(
                self.object_name,
                str(each_obj))
            resp = self.s3_test_obj.put_object(
                self.bucket_name,
                obj,
                self.file_path)
            assert resp[0], resp[1]
        self.log.info("Objects are uploaded to an existing bucket")
        self.log.info("Performing list object operations")
        resp = self.s3_test_obj.object_list(
            self.bucket_name)
        assert resp[0], resp[1]
        self.log.info("Objects are listed")
        for each_obj in resp[1]:
            self.log.info("Setting tag to an object %s", each_obj)
            resp = self.tag_obj.set_object_tag(
                self.bucket_name,
                each_obj,
                S3_OBJ_TST["s3_object"]["key"],
                S3_OBJ_TST["test_9434"]["value"],
                tag_count=S3_OBJ_TST["test_9434"]["tag_count"])
            assert resp[0], resp[1]
            self.log.info("Tag is set to an object %s", each_obj)
            self.log.info("Retrieving tags of an object")
            resp = self.tag_obj.get_object_tags(
                self.bucket_name, each_obj)
            assert resp[0], resp[1]
            assert len(
                resp[1]) == S3_OBJ_TST["test_9434"]["tag_count"], resp[1]
            self.log.info("Retrieved tags of an object")
        self.log.info(
            "Verification of max. no. of Objects user can upload with max no. of tags per Object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5573")
    @CTFailOn(error_handler)
    def test_metadata_object_tags_2479(self):
        """Add user defined metadata and Object tags while adding the new object to the bucket."""
        self.log.info(
            "Add user defined metadata and Object tags while adding the new object to the bucket")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object with user defined metadata and tags")
        resp = self.tag_obj.put_object_with_tagging(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["test_9435"]["object_tag"],
            key=S3_OBJ_TST["s3_object"]["key"],
            value=S3_OBJ_TST["test_9435"]["value"])
        assert resp[0], resp[1]
        assert resp[1].key == self.object_name, resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Retrieving tags of an object")
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info(
            "Add user defined metadata and Object tags while adding the new object to the bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5575")
    @CTFailOn(error_handler)
    def test_user_defined_metadata_2480(self):
        """Add or update user defined metadata and verify the Object Tags."""
        self.log.info(
            "Add or update user defined metadata and verify the Object Tags")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object with user defined metadata and tags")
        resp = self.tag_obj.put_object_with_tagging(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["test_9436"]["object_tag"],
            key=S3_OBJ_TST["test_9436"]["key1"],
            value=S3_OBJ_TST["test_9436"]["value1"])
        assert resp[0], resp[1]
        assert resp[1].key == self.object_name, resp[1]
        self.log.info(
            "Object is uploaded to a bucket with user defined metadata")
        self.log.info("Retrieving tags of an object")
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        self.log.info("Retrieving object info")
        resp = self.s3_test_obj.object_info(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_9436"]["key1"] in resp[1]["Metadata"], resp[1]
        self.log.info("Retrieved info of an object")
        self.log.info(
            "Updating user defined metadata of an existing object")
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path,
            m_key=S3_OBJ_TST["test_9436"]["key2"],
            m_value=S3_OBJ_TST["test_9436"]["value2"])
        assert resp[0], resp[1]
        self.log.info("Updated user defined metadata of an existing object")
        self.log.info("Retrieving object info after updating metadata")
        resp = self.s3_test_obj.object_info(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        assert S3_OBJ_TST["test_9436"]["key2"] in resp[1]["Metadata"], resp[1]
        self.log.info("Retrieved object info after updating metadata")
        self.log.info(
            "Retrieving tags of an object after updating metadata")
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert len(resp[1]) == S3_OBJ_TST["test_9436"]["tag_len"], resp[1]
        self.log.info("Retrieved tags of an object after updating metadata")
        self.log.info(
            "Add or update user defined metadata and verify the Object Tags")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5563")
    @CTFailOn(error_handler)
    def test_user_defined_metadata_2481(self):
        """Upload Object with user defined metadata upto 2KB and upto 10 object tags."""
        self.log.info(
            "Upload Object with user defined metadata upto 2KB and upto 10 object tags")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert resp[1] == self.bucket_name, resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object with user defined metadata and tags")
        resp = self.tag_obj.put_object_with_tagging(
            self.bucket_name,
            self.object_name,
            self.file_path,
            S3_OBJ_TST["test_9437"]["object_tag"],
            key=S3_OBJ_TST["s3_object"]["key"],
            value=S3_OBJ_TST["test_9437"]["value"])
        assert resp[0], resp[1]
        assert resp[1].key == self.object_name, resp[1]
        self.log.info(
            "Uploaded an object with user defined metadata and tags")
        self.log.info("Retrieving tag of an object")
        resp = self.tag_obj.get_object_tags(
            self.bucket_name,
            self.object_name)
        assert resp[0], resp[1]
        assert len(
            resp[1]) == S3_OBJ_TST["test_9437"]["tag_count"], resp[1]
        self.log.info("Retrieved tag of an object")
        self.log.info(
            "Upload Object with user definced metadata upto 2KB and upto 10 object tags")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5577")
    @CTFailOn(error_handler)
    def test_maximum_object_tags_2482(self):
        """Add maximum nos. of Object tags >100 using json file."""
        self.log.info(
            "Add maximum nos. of Object tags >100 using json file")
        self.log.info(
            "Creating a bucket with name %s",
            self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        create_file(
            self.file_path,
            S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info(
            "Uploading an object %s to a bucket %s",
            self.object_name,
            self.bucket_name)
        resp = self.s3_test_obj.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert resp[0], resp[1]
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Adding tags to an existing object")
        try:
            self.tag_obj.set_object_tag(
                self.bucket_name,
                self.object_name,
                S3_OBJ_TST["s3_object"]["key"],
                S3_OBJ_TST["test_9438"]["value"],
                tag_count=S3_OBJ_TST["test_9438"]["tag_count"])
        except CTException as error:
            assert errmsg.S3_BKT_INVALID_TAG_ERR in str(error.message), error.message
        self.log.info(
            "Add maximum nos. of Object tags >100 using json file")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5548")
    @CTFailOn(error_handler)
    def test_put_object_tagging_2483(self):
        """Verify PUT object tagging to non-existing object."""
        self.log.info("verify PUT object tagging to non-existing object")
        self.log.info("Creating a bucket with name %s",
                      self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        self.log.info("Setting tag to non existing object")
        try:
            self.tag_obj.set_object_tag(
                self.bucket_name,
                self.object_name,
                S3_OBJ_TST["s3_object"]["key"],
                S3_OBJ_TST["test_9439"]["value"])
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["key_err"] in str(
                error.message), error.message
        self.log.info("verify PUT object tagging to non-existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5556")
    @CTFailOn(error_handler)
    def test_get_object_tagging_2484(self):
        """Verify GET object tagging to non-existing object."""
        self.log.info("verify GET object tagging to non-existing object")
        self.log.info("Creating a bucket with name %s",
                      self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        self.log.info("Retrieving tags from non existing object")
        try:
            self.tag_obj.get_object_tags(
                self.bucket_name,
                self.object_name)
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["key_err"] in str(
                error.message), error.message
        self.log.info("verify GET object tagging to non-existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5559")
    @CTFailOn(error_handler)
    def test_delobj_tagging_2485(self):
        """Verify DELETE object tagging to non-existing object."""
        self.log.info("verify DELETE object tagging to non-existing object")
        self.log.info("Creating a bucket with name %s",
                      self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        self.log.info("Deleting tags of non-existing object")
        try:
            self.tag_obj.delete_object_tagging(
                self.bucket_name,
                self.object_name)
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["key_err"] in str(
                error.message), error.message
        self.log.info("verify DELETE object tagging to non-existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5546")
    @CTFailOn(error_handler)
    def test_put_non_existing_object_tagging_2486(self):
        """Verify put object with tagging support to non-existing object."""
        self.log.info(
            "Verify put object with tagging support to non-existing object")
        self.log.info("Creating a bucket with name %s",
                      self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        self.log.info("Setting tags to non-existing object")
        try:
            self.tag_obj.set_object_tag(
                self.bucket_name,
                self.object_name,
                S3_OBJ_TST["s3_object"]["key"],
                S3_OBJ_TST["test_9442"]["value"])
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["key_err"] in str(
                error.message), error.message
        self.log.info(
            "Verify put object with tagging support to non-existing object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-5554")
    @CTFailOn(error_handler)
    def test_get_non_existing_object_tagging_2487(self):
        """Verify get object with tagging support to non-existing object."""
        self.log.info(
            "Verify get object with tagging support to non-existing object")
        self.log.info("Creating a bucket with name %s",
                      self.bucket_name)
        resp = self.s3_test_obj.create_bucket(
            self.bucket_name)
        assert resp[0], resp[1]
        assert self.bucket_name == resp[1], resp[1]
        self.log.info(
            "Bucket is created with name %s",
            self.bucket_name)
        self.log.info("Retrieving tags from non existing object")
        try:
            self.tag_obj.get_object_with_tagging(
                self.bucket_name,
                self.object_name)
        except CTException as error:
            assert S3_OBJ_TST["s3_object"]["key_err"] in str(
                error.message), error.message
        self.log.info(
            "Verify get object with tagging support to non-existing object")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-42780")
    def test_delobj_tagging_42780(self):
        """Verify already deleted tag using DELETE object tagging."""
        self.log.info("Verify already deleted tag using DELETE object tagging")
        self.log.info("Creating a bucket, uploading an object and setting tag for object")
        self.create_put_set_object_tag(self.bucket_name, self.object_name, self.file_path,
                                       mb_count=S3_OBJ_TST["s3_object"]["mb_count"],
                                       key=S3_OBJ_TST["s3_object"]["key"],
                                       value=S3_OBJ_TST["test_9415"]["value"])
        self.log.info("Created a bucket, uploaded an object and tag is set for object")
        self.log.info("Retrieving tag of an object %s", self.object_name)
        resp = self.tag_obj.get_object_tags(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Deleting tag of an object")
        resp = self.tag_obj.delete_object_tagging(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Deleting already deleted tag")
        try:
            self.tag_obj.delete_object_tagging(self.bucket_name, self.object_name)
        except CTException as error:
            assert_utils.assert_in(S3_OBJ_TST["s3_object"]["key_err"], str(error.message),
                                   error.message)
        self.log.info("verifying tag of same object after DELETE object tagging")
        resp = self.tag_obj.get_object_tags(self.bucket_name, self.object_name)
        assert_utils.assert_equal(len(resp[1]), S3_OBJ_TST["test_9415"]["tag_length"], resp[1])
        self.log.info("Verify already deleted tag using DELETE object tagging")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-42781")
    def test_object_tag_count_get_object_42781(self):
        """ verify Get object tags count using GET object on non tagged object"""
        self.log.info("verify Get object tags count using GET object on non tagged object")
        self.log.info("Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], self.bucket_name, resp[1])
        self.log.info("Bucket is created with name %s", self.bucket_name)
        create_file(self.file_path, S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Uploading an object %s", self.object_name)
        resp = self.s3_test_obj.put_object(self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Getting uploaded object")
        resp = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1]['TagCount'], 0, resp[1])
        self.log.info("Object is Retrieved using GET object")
        self.log.info("verify Get object tags count using GET object on non tagged object")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-42782")
    def test_object_tag_count_get_object_42782(self):
        """ verify Get object tags count using GET object on tagged object"""
        self.log.info("verify Get object tags count using GET object on tagged object")
        self.log.info("Creating a bucket, uploading an object and setting 10 tags for object")
        self.create_put_set_object_tag(self.bucket_name, self.object_name, self.file_path,
                                       mb_count=S3_OBJ_TST["s3_object"]["mb_count"],
                                       key=S3_OBJ_TST["s3_object"]["key"],
                                       value=S3_OBJ_TST["test_9419"]["value"],
                                       tag_count=S3_OBJ_TST["test_9419"]["tag_count"])
        self.log.info("Created a bucket, uploading an object and setting tags for object")
        self.log.info("Getting uploaded object")
        resp = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(
            resp[1]['TagCount'], S3_OBJ_TST["test_9419"]["tag_count"], resp[1])
        self.log.info("Object is Retrieved using GET object")
        self.log.info("verify Get object tags count using GET object on non tagged object")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-42774")
    def test_multipartupload_max_tags_42774(self):
        """Verify Multipart Upload with max no. of tags"""
        self.log.info("Verify Multipart Upload with max no.of tags for an Object")
        self.log.info("Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], self.bucket_name, resp[1])
        self.log.info("Bucket is created with name %s", self.bucket_name)
        self.log.info("Creating multipart upload with tagging")
        resp = self.tag_obj.create_multipart_upload_with_tagging(self.bucket_name,
                                                                 self.object_name,
                                                                 S3_OBJ_TST["test_9437"]["object_tag"])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Created multipart upload with max no.of tags for an Object")
        self.log.info("Performing list multipart uploads")
        resp = self.s3_mp_obj.list_multipart_uploads(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        upload_id = resp[1]["Uploads"][0]["UploadId"]
        self.log.info("Performed list multipart upload on a bucket %s", self.bucket_name)
        self.log.info("Uploading parts to a bucket %s", self.bucket_name)
        resp = self.s3_mp_obj.upload_parts(upload_id, self.bucket_name, self.object_name,
                                           S3_OBJ_TST["test_9418"]["single_part_size"],
                                           total_parts=S3_OBJ_TST["test_9418"]["total_parts"],
                                           multipart_obj_path=self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        upload_parts_list = resp[1]
        self.log.info("Parts are uploaded to a bucket %s", self.bucket_name)
        self.log.info("Performing list parts of object %s", self.object_name)
        resp = self.s3_mp_obj.list_parts(upload_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed list parts operation")
        self.log.info("Performing complete multipart upload on a bucket %s", self.bucket_name)
        resp = self.s3_mp_obj.complete_multipart_upload(upload_id, upload_parts_list,
                                                        self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed complete multipart upload on a bucket %s", self.bucket_name)
        self.log.info("Retrieving tag of an object")
        resp = self.tag_obj.get_object_tags(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(len(resp[1]), 10, resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Verify Multipart Upload with max no.of tags for an Object")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-42775")
    def test_mpupload_valid_tagkeyspecialchars_42775(self):
        """Verify Multipart Upload with tag key having valid special characters"""
        self.log.info("Verify Multipart Upload with tag key having valid special characters")
        self.log.info("Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], self.bucket_name, resp[1])
        self.log.info("Bucket is created with name %s", self.bucket_name)
        self.log.info("Creating multipart upload with tagging")
        tag = urllib.parse.urlencode({
            S3_OBJ_TST["test_9429"]["key"]: S3_OBJ_TST["test_9429"]["value"]})
        resp = self.tag_obj.create_multipart_upload_with_tagging(self.bucket_name,
                                                                 self.object_name, tag)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Created multipart upload with tag key having valid special characters")
        self.log.info("Performing list multipart uploads")
        resp = self.s3_mp_obj.list_multipart_uploads(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        upload_id = resp[1]["Uploads"][0]["UploadId"]
        self.log.info("Performed list multipart upload on a bucket %s", self.bucket_name)
        self.log.info("Uploading parts to a bucket %s", self.bucket_name)
        resp = self.s3_mp_obj.upload_parts(upload_id, self.bucket_name, self.object_name,
                                           S3_OBJ_TST["test_9418"]["single_part_size"],
                                           total_parts=S3_OBJ_TST["test_9418"]["total_parts"],
                                           multipart_obj_path=self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        upload_parts_list = resp[1]
        self.log.info("Parts are uploaded to a bucket %s", self.bucket_name)
        self.log.info("Performing list parts of object %s", self.object_name)
        resp = self.s3_mp_obj.list_parts(upload_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed list parts operation")
        self.log.info("Performing complete multipart upload on a bucket %s", self.bucket_name)
        resp = self.s3_mp_obj.complete_multipart_upload(upload_id, upload_parts_list,
                                                        self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed complete multipart upload on a bucket %s", self.bucket_name)
        self.log.info("Retrieving tag of an object %s", self.object_name)
        resp = self.tag_obj.get_object_tags(self.bucket_name, self.object_name)
        assert_utils.assert_equal(
            resp[1], {S3_OBJ_TST["test_9429"]["key"]: S3_OBJ_TST["test_9429"]["value"]}, resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Verify Multipart Upload with tag key having valid special characters")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-42776")
    def test_mpupload_with_tagvalue256chars_42776(self):
        """Verify Multipart Upload with tag having
        tag values up to 256 Unicode characters in length"""
        self.log.info("Verify Multipart Upload with tag having "
                      "tag values up to 256 Unicode characters in length")
        self.log.info("Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], self.bucket_name, resp[1])
        self.log.info("Bucket is created with name %s", self.bucket_name)
        self.log.info("Creating multipart upload with tagging")
        resp = self.tag_obj.create_multipart_upload_with_tagging(
            self.bucket_name, self.object_name, S3_OBJ_TST["test_42776"]["object_tag"])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Created multipart upload with tag values up to 256 Unicode characters in length")
        self.log.info("Performing list multipart uploads")
        resp = self.s3_mp_obj.list_multipart_uploads(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        upload_id = resp[1]["Uploads"][0]["UploadId"]
        self.log.info("Performed list multipart upload on a bucket %s", self.bucket_name)
        self.log.info("Uploading parts to a bucket %s", self.bucket_name)
        resp = self.s3_mp_obj.upload_parts(upload_id, self.bucket_name, self.object_name,
                                           S3_OBJ_TST["test_9418"]["single_part_size"],
                                           total_parts=S3_OBJ_TST["test_9418"]["total_parts"],
                                           multipart_obj_path=self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        upload_parts_list = resp[1]
        self.log.info("Parts are uploaded to a bucket %s", self.bucket_name)
        self.log.info("Performing list parts of object %s", self.object_name)
        resp = self.s3_mp_obj.list_parts(upload_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed list parts operation")
        self.log.info("Performing complete multipart upload on a bucket %s", self.bucket_name)
        resp = self.s3_mp_obj.complete_multipart_upload(upload_id, upload_parts_list,
                                                        self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed complete multipart upload on a bucket %s", self.bucket_name)
        self.log.info("Retrieving tag of an object %s", self.object_name)
        resp = self.tag_obj.get_object_tags(self.bucket_name, self.object_name)
        assert_utils.assert_equal(len(resp[1]), S3_OBJ_TST["test_42776"]["tag_count"], resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Verify Multipart Upload with tag having "
                      "tag values up to 256 Unicode characters in length")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-42777")
    def test_mpupload_tagkey128chars_42777(self):
        """Verify Multipart Upload with tag having tag key up to 128 Unicode characters in length"""
        self.log.info("Verify Multipart Upload with tag having "
                      "tag key up to 128 Unicode characters in length")
        self.log.info("Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], self.bucket_name, resp[1])
        self.log.info("Bucket is created with name %s", self.bucket_name)
        self.log.info("Creating multipart upload with tagging")
        resp = self.tag_obj.create_multipart_upload_with_tagging(
            self.bucket_name, self.object_name, S3_OBJ_TST["test_42777"]["object_tag"])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Created multipart upload with tag key up to 128 Unicode characters in length")
        self.log.info("Performing list multipart uploads")
        resp = self.s3_mp_obj.list_multipart_uploads(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        upload_id = resp[1]["Uploads"][0]["UploadId"]
        self.log.info("Performed list multipart upload on a bucket %s", self.bucket_name)
        self.log.info("Uploading parts to a bucket %s", self.bucket_name)
        resp = self.s3_mp_obj.upload_parts(upload_id, self.bucket_name, self.object_name,
                                           S3_OBJ_TST["test_9418"]["single_part_size"],
                                           total_parts=S3_OBJ_TST["test_9418"]["total_parts"],
                                           multipart_obj_path=self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        upload_parts_list = resp[1]
        self.log.info("Parts are uploaded to a bucket %s", self.bucket_name)
        self.log.info("Performing list parts of object %s", self.object_name)
        resp = self.s3_mp_obj.list_parts(upload_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed list parts operation")
        self.log.info("Performing complete multipart upload on a bucket %s", self.bucket_name)
        resp = self.s3_mp_obj.complete_multipart_upload(upload_id, upload_parts_list,
                                                        self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed complete multipart upload on a bucket %s", self.bucket_name)
        self.log.info("Retrieving tag of an object %s", self.object_name)
        resp = self.tag_obj.get_object_tags(self.bucket_name, self.object_name)
        assert_utils.assert_equal(len(resp[1]), S3_OBJ_TST["test_42777"]["tag_count"], resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Verify Multipart Upload with tag having "
                      "tag key up to 128 Unicode characters in length")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-42778")
    def test_mpupload_casesensitive_tag_42778(self):
        """Verify Multipart Upload with tag Keys & value having case sensitive labels"""
        self.log.info("Verify Multipart Upload with tag Keys & value having case sensitive labels")
        self.log.info("Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], self.bucket_name, resp[1])
        self.log.info("Bucket is created with name %s", self.bucket_name)
        self.log.info("Creating multipart upload with tagging")
        resp = self.tag_obj.create_multipart_upload_with_tagging(
            self.bucket_name, self.object_name,
            S3_OBJ_TST["test_42778"]["object_tag"])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Created multipart upload with Keys & value having case sensitive labels")
        self.log.info("Performing list multipart uploads")
        resp = self.s3_mp_obj.list_multipart_uploads(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        upload_id = resp[1]["Uploads"][0]["UploadId"]
        self.log.info("Performed list multipart upload on a bucket %s", self.bucket_name)
        self.log.info("Uploading parts to a bucket %s", self.bucket_name)
        resp = self.s3_mp_obj.upload_parts(upload_id, self.bucket_name, self.object_name,
                                           S3_OBJ_TST["test_9418"]["single_part_size"],
                                           total_parts=S3_OBJ_TST["test_9418"]["total_parts"],
                                           multipart_obj_path=self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        upload_parts_list = resp[1]
        self.log.info("Parts are uploaded to a bucket %s", self.bucket_name)
        self.log.info("Performing list parts of object %s", self.object_name)
        resp = self.s3_mp_obj.list_parts(upload_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed list parts operation")
        self.log.info("Performing complete multipart upload on a bucket %s", self.bucket_name)
        resp = self.s3_mp_obj.complete_multipart_upload(upload_id, upload_parts_list,
                                                        self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed complete multipart upload on a bucket %s", self.bucket_name)
        self.log.info("Retrieving tag of an object %s", self.object_name)
        resp = self.tag_obj.get_object_tags(self.bucket_name, self.object_name)
        assert_utils.assert_equal(len(resp[1]), S3_OBJ_TST["test_42778"]["tag_count"], resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Verify Multipart Upload with tag Keys & value having case sensitive labels")

    @pytest.mark.s3_ops
    @pytest.mark.s3_object_tags
    @pytest.mark.tags("TEST-42852")
    def test_object_tag_count_get_object_42852(self):
        """ verify Get object tags count doing GET object immediately after adding tag."""
        self.log.info("Verify Get object tags count doing GET object immediately after adding tag")
        self.log.info("Creating a bucket with name %s", self.bucket_name)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], self.bucket_name, resp[1])
        self.log.info("Bucket is created with name %s", self.bucket_name)
        create_file(self.file_path, S3_OBJ_TST["s3_object"]["mb_count"])
        self.log.info("Uploading an object %s to a bucket %s", self.object_name, self.bucket_name)
        resp = self.s3_test_obj.put_object(self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Object is uploaded to a bucket")
        self.log.info("Adding tags to an existing object")
        start_time = perf_counter()
        resp = self.tag_obj.set_object_tag(self.bucket_name, self.object_name,
                                           S3_OBJ_TST["s3_object"]["key"],
                                           S3_OBJ_TST["test_9434"]["value"], tag_count=1)
        end_time = perf_counter()
        self.log.info("#### set object tag TIME : %f ####", (end_time - start_time))
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1]['TagCount'], 1, resp[1])
        self.log.info("Object is Retrieved using GET object")
