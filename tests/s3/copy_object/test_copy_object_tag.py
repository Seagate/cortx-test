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

"""S3 copy object test module."""

# pylint: disable=too-many-lines

import os
import random
from time import perf_counter_ns
import logging
import pytest

from commons.utils import assert_utils
from commons.utils import system_utils
from commons.params import TEST_DATA_FOLDER
from config.s3 import S3_CFG
from config.s3 import S3_OBJ_TST
from libs.s3 import s3_test_lib
from libs.s3.s3_tagging_test_lib import S3TaggingTestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_common_test_lib import copy_obj_di_check


# pylint: disable=too-many-public-methods
class TestCopyObjectsTag():
    """S3 copy object class."""

    # pylint: disable=attribute-defined-outside-init
    # pylint: disable-msg=too-many-statements
    # pylint: disable=too-many-arguments
    # pylint: disable-msg=too-many-locals
    # pylint: disable=too-many-instance-attributes
    @pytest.yield_fixture(autouse=True)
    def setup(self):
        """
        Function will be invoked test before and after yield part each test case execution.

        1. Create bucket name, object name, account name.
        2. Check cluster status, all services are running.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: test setup.")
        self.s3_test_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.tag_obj = S3TaggingTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_mp_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestS3CopyObject")
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.bucket_name1 = "bkt1-copyobject-{}".format(perf_counter_ns())
        self.bucket_name2 = "bkt2-copyobject-{}".format(perf_counter_ns())
        self.object_name1 = "obj1-copyobject-{}".format(perf_counter_ns())
        self.object_name2 = "obj2-copyobject-{}".format(perf_counter_ns())
        self.key_src = S3_OBJ_TST["s3_object"]["key"] + "-src"
        self.value_src = S3_OBJ_TST["test_9413"]["value"] + "-src"
        self.key_dest = S3_OBJ_TST["s3_object"]["key"] + "-dest"
        self.value_dest = S3_OBJ_TST["test_9413"]["value"] + "-dest"
        self.mb_count = S3_OBJ_TST["s3_object"]["mb_count"]
        self.file_path = os.path.join(self.test_dir_path, self.object_name1)
        self.log.info("Creating a source bucket: %s", self.bucket_name1)
        resp = self.s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Source bucket is created with name %s", self.bucket_name1)
        self.log.info("Creating a destination bucket: %s", self.bucket_name2)
        resp = self.s3_test_obj.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Destination bucket is created with name %s", self.bucket_name2)
        self.log.info("ENDED: test setup.")
        yield
        self.log.info("STARTED: test teardown.")
        bucket_list = self.s3_test_obj.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket in [
                self.bucket_name1,
                self.bucket_name2]]
        if pref_list:
            resp = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(resp[0], resp[1])
        if system_utils.path_exists(self.file_path):
            system_utils.remove_file(self.file_path)
        self.log.info("ENDED: test teardown.")

    def create_put_set_object_tag(self, bucket_name, obj_name, file_path, **kwargs):
        """
        Helper function is used to put object and set object tags.

        :param bucket_name:
        :param bucket_name: Name of bucket to be created
        :param obj_name: Name of an object
        :param file_path: Path of the file
        :mb_count: Size of file in MB
        :param tag_count: Number of tags to be set
        :return: Etag of Put object
        """
        mb_count = kwargs.get("mb_count", None)
        key = kwargs.get("key", None)
        value = kwargs.get("value", None)
        tag_count = kwargs.get("tag_count", 1)
        system_utils.create_file(file_path, mb_count)
        self.log.info("Uploading an object %s to bucket %s", obj_name, bucket_name)
        put_resp = self.s3_test_obj.put_object(bucket_name, obj_name, file_path)
        put_etag = put_resp[1]["ETag"].replace('"', '')
        assert put_resp[0], put_resp[1]
        self.log.info("Setting tag to an object %s", obj_name)
        resp = self.tag_obj.set_object_tag(bucket_name, obj_name, key, value, tag_count=tag_count)
        assert resp[0], resp[1]
        return put_etag

    # pylint: disable=too-many-arguments
    def complete_multipart_upload_with_tagging(self,
                                               bucket_name,
                                               object_name,
                                               file_path,
                                               object_tag,
                                               total_parts,
                                               file_size):
        """
        Helper function is used to upload multipart object and set object tags.

        :param bucket_name: Name of the bucket used for multipart upload
        :param object_name: Name of the object used for multipart upload
        :param file_path: File path
        :param object_tag: Object tag to be set for multipart object
        :param total_parts: Total number of parts to be uploaded
        :param file_size: Size of file
        """
        self.log.info("Creating multipart upload with tagging")
        self.log.info("Create file")
        resp = system_utils.create_file(file_path, count=file_size, b_size="1G")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.tag_obj.create_multipart_upload_with_tagging(bucket_name,
                                                                 object_name,
                                                                 object_tag)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Created multipart upload with tagging support")
        self.log.info("Performing list multipart uploads")
        resp = self.s3_mp_obj.list_multipart_uploads(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        upload_id = resp[1]["Uploads"][0]["UploadId"]
        self.log.info("Performed list multipart upload on a bucket %s", bucket_name)
        self.log.info("Uploading parts to a bucket %s", bucket_name)
        resp = self.s3_mp_obj.upload_parts(upload_id, bucket_name, object_name,
                                           S3_OBJ_TST["test_9418"]["single_part_size"],
                                           total_parts=total_parts,
                                           multipart_obj_path=file_path)
        assert_utils.assert_true(resp[0], resp[1])
        upload_parts_list = resp[1]
        self.log.info("Parts are uploaded to a object %s", object_name)
        self.log.info("Performing list parts of object %s", object_name)
        resp = self.s3_mp_obj.list_parts(upload_id, bucket_name, object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed list parts operation")
        self.log.info("Performing complete multipart upload of an object %s", bucket_name)
        resp = self.s3_mp_obj.complete_multipart_upload(upload_id, upload_parts_list,
                                                        bucket_name, object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Performed complete multipart upload of an object %s", bucket_name)
        return resp

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44811")
    def test_44811(self):
        """
        TEST-44811: Test simple copy-object with destination tag set same as
        source object.(--tagging-directive=COPY)
        """
        self.log.info("STARTED: Simple copy-object with destination tag set same as source object"
                      " (--tagging-directive=COPY)")
        self.log.info("Simple Copy-object with destination tag set same as source object"
                      " in the same bucket")
        self.log.info("Step 1: Uploading an object and setting tag for object")
        put_etag = self.create_put_set_object_tag(self.bucket_name1,
                                                  self.object_name1,
                                                  self.file_path,
                                                  mb_count=self.mb_count,
                                                  key=self.key_src,
                                                  value=self.value_src)
        self.log.info("Step 1: Uploaded an object and tag is set for object")
        self.log.debug("Retrieving tag of an object %s", self.object_name1)
        put_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        self.log.debug("Retrieved tag of an object")
        self.log.info("Step 2: Copy object to same bucket with different object.")
        tag_str = put_resp[1][0]["Key"] + "=" + put_resp[1][0]["Value"]
        status, response = self.s3_test_obj.copy_object(self.bucket_name1,
                                                        self.object_name1,
                                                        self.bucket_name1,
                                                        self.object_name2,
                                                        TaggingDirective='COPY',
                                                        Tagging=tag_str)
        assert_utils.assert_true(status, response)
        copy_etag = str(response['CopyObjectResult']['ETag'])
        self.log.info("Step 3: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Step 3: Retrieved tag of an object")
        self.log.info("Step 4: Compare tagset of source and destination object")
        assert_utils.assert_equal(copy_resp[1][0]["Key"], put_resp[1][0]["Key"],
                                  put_resp[1][0]["Key"])
        assert_utils.assert_equal(copy_resp[1][0]["Value"], put_resp[1][0]["Value"],
                                  put_resp[1][0]["Value"])
        self.log.info("Step 4: Compared and verified tag of source and destination object")
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name1,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        self.log.info("Simple Copy-object with destination tag set same as source object"
                      "in the different bucket")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name2, self.object_name2,
                                                        TaggingDirective='COPY', Tagging=tag_str)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 6: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Step 7: Compare tagset of source and destination object")
        assert_utils.assert_equal(copy_resp[1][0]["Key"], put_resp[1][0]["Key"],
                                  put_resp[1][0]["Key"])
        assert_utils.assert_equal(copy_resp[1][0]["Value"], put_resp[1][0]["Value"],
                                  put_resp[1][0]["Value"])
        self.log.info("Step 7: Compared and verified tag of source and destination object")
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        self.log.info("ENDED: copy-object with destination tag set same as source object"
                      " (--tagging-directive=COPY)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44812")
    def test_44812(self):
        """
        TEST-44812: Test simple copy-object with destination tag set replaces source
        object tag(--tagging-directive=REPLACE)
        """
        self.log.info("STARTED: Test simple copy-object with destination tag set replaces source"
                      " object tag(--tagging-directive=REPLACE)")
        self.log.info("Simple copy-object with destination tag set replaces source object tag"
                      " in the same bucket")
        self.log.info("Step 1: Uploading an object and setting tag for object")
        tag_str = self.key_dest + "=" + self.value_dest
        put_etag = self.create_put_set_object_tag(self.bucket_name1, self.object_name1,
                                                  self.file_path, mb_count=self.mb_count,
                                                  key=self.key_src, value=self.value_src)
        self.log.info("Step 1: Uploaded an object and tag is set for object")
        self.log.debug("Retrieving tag of an object %s", self.object_name1)
        put_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        self.log.debug("Retrieved tag of an object")
        self.log.info("Step 2: Copy object to same bucket with different object.")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name1, self.object_name2,
                                                        TaggingDirective='REPLACE', Tagging=tag_str)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 3: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Step 3: Retrieved tag of an object")
        self.log.info("Step 4: Compare tagset of source and destination object")
        assert_utils.assert_not_equal(copy_resp[1][0]["Key"], put_resp[1][0]["Key"],
                                      put_resp[1][0]["Key"])
        assert_utils.assert_not_equal(copy_resp[1][0]["Value"], put_resp[1][0]["Value"],
                                      put_resp[1][0]["Value"])
        self.log.info("Step 4: Compared and verified tags of source and destination object"
                      " are different")
        self.log.info("Verify destination tag set match with assigned tag set in copy object")
        assert_utils.assert_equal(copy_resp[1][0]["Key"], self.key_dest, self.key_dest)
        assert_utils.assert_equal(copy_resp[1][0]["Value"], self.value_dest, self.value_dest)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name1,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        self.log.info("Simple Copy-object with destination tag set replaces source object tag"
                      "in the different bucket")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name2, self.object_name2,
                                                        TaggingDirective='REPLACE', Tagging=tag_str)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 6: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Step 7: Compare tagset of source and destination object")
        assert_utils.assert_not_equal(copy_resp[1][0]["Key"], put_resp[1][0]["Key"],
                                      put_resp[1][0]["Key"])
        assert_utils.assert_not_equal(copy_resp[1][0]["Value"], put_resp[1][0]["Value"],
                                      put_resp[1][0]["Value"])
        self.log.info("Verify destination tag set match with assigned tag set in copy object")
        assert_utils.assert_equal(copy_resp[1][0]["Key"], self.key_dest, self.key_dest)
        assert_utils.assert_equal(copy_resp[1][0]["Value"], self.value_dest, self.value_dest)
        self.log.info("Step 7: Compared and verified tags of source and destination object"
                      "are different and do not match")
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        self.log.info("ENDED: Test simple copy-object with destination tag set replaces source"
                      " object tag(--tagging-directive=REPLACE)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44813")
    def test_44813(self):
        """
        TEST-44813 :Test simple copy-object with source object having max number of tags(10)
        and parameter (--tagging-directive=COPY)
        """
        self.log.info("STARTED:Test simple copy-object with source object having max number of"
                      " tags(10) and parameter (--tagging-directive=COPY)")
        self.log.info("Simple copy-object with source object having max number of tags(10)"
                      " in the same bucket")
        self.log.info("Step 1: Uploading an object and setting tag for object")
        tag_str = ""
        put_etag = self.create_put_set_object_tag(self.bucket_name1, self.object_name1,
                                                  self.file_path, mb_count=self.mb_count,
                                                  key=self.key_src, value=self.value_src,
                                                  tag_count=10)
        self.log.info("Step 1: Uploaded an object and tag is set for object")
        self.log.debug("Retrieving tag of an object %s", self.object_name1)
        put_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        self.log.debug("Retrieved tag of an object")
        self.log.info("Step 2: Copy object to same bucket with different object.")
        for num in range(len(put_resp[1])):
            tag_str = tag_str + put_resp[1][num]["Key"] + "=" + put_resp[1][num]["Value"] + "&"
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name1, self.object_name2,
                                                        TaggingDirective='COPY',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 3: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Step 3: Retrieved tag of an object")
        self.log.info("Step 4: Compare tagset of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), len(put_resp[1]), len(put_resp[1]))
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"],
                                      put_resp[1][num]["Key"], put_resp[1][num]["Key"])
            assert_utils.assert_equal(copy_resp[1][num]["Value"],
                                      put_resp[1][num]["Value"], put_resp[1][num]["Value"])
        self.log.info("Step 4: Compared and verified tag of source and destination object")
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name1,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        self.log.info("Step 5: Copy-object with destination tag set same as source object"
                      "in the different bucket")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name2, self.object_name2,
                                                        TaggingDirective='COPY',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 6: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Step 7: Compare tagset of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), len(put_resp[1]), len(put_resp[1]))
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"],
                                      put_resp[1][num]["Key"], put_resp[1][num]["Key"])
            assert_utils.assert_equal(copy_resp[1][num]["Value"],
                                      put_resp[1][num]["Value"], put_resp[1][num]["Value"])
        self.log.info("Step 7: Compared and verified tag of source and destination object")
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        self.log.info("STARTED:Test simple copy-object with source object having max number of"
                      " tags(10) and parameter (--tagging-directive=COPY)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44814")
    def test_44814(self):
        """
        TEST-44814 :Test simple copy-object with source object having max number of tags(10)
        and parameter (--tagging-directive=REPLACE)
        """
        self.log.info("STARTED: Test simple copy-object with source object having max number of"
                      " tags(10) and parameter (--tagging-directive=REPLACE)")
        self.log.info("Simple copy-object with source object having max number of tags(10)"
                      " in the same bucket")
        self.log.info("Step 1: Uploading an object and setting tag for object")
        tag_str = ""
        put_etag = self.create_put_set_object_tag(self.bucket_name1, self.object_name1,
                                                  self.file_path, mb_count=self.mb_count,
                                                  key=self.key_src, value=self.value_src,
                                                  tag_count=10)
        self.log.info("Step 1: Uploaded an object and tag is set for object")
        self.log.debug("Retrieving tag of an object %s", self.object_name1)
        put_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        self.log.debug("Retrieved tag of an object")
        self.log.info("Step 2: Copy object to same bucket with different object.")
        for num in range(len(put_resp[1])):
            tag_str = tag_str + "{}{}".format(self.key_dest, str(num)) + "=" \
                      + "{}{}".format(self.value_dest, str(num)) + "&"
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name1, self.object_name2,
                                                        TaggingDirective='REPLACE',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 3: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Step 3: Retrieved tag of an object")
        self.log.info("Step 4: Compare tagset of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), len(put_resp[1]), len(put_resp[1]))
        for num in range(len(copy_resp[1])):
            assert_utils.assert_not_equal(copy_resp[1][num]["Key"],
                                          put_resp[1][num]["Key"], put_resp[1][num]["Key"])
            assert_utils.assert_not_equal(copy_resp[1][num]["Value"],
                                          put_resp[1][num]["Value"], put_resp[1][num]["Value"])
        self.log.info("Step 4: Compared and verified tag of source and destination object"
                      "are different and do not match")
        self.log.info("Step : Verify tag set of destination object should match with tagset"
                      "assigned in copy object")
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"],
                                      "{}{}".format(self.key_dest, str(num)),
                                      "{}{}".format(self.key_dest, str(num)))
            assert_utils.assert_equal(copy_resp[1][num]["Value"],
                                      "{}{}".format(self.value_dest, str(num)),
                                      "{}{}".format(self.value_dest, str(num)))
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name1,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        self.log.info("Simple copy-object with destination tag set same as source object"
                      "in the different bucket")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name2, self.object_name2,
                                                        TaggingDirective='REPLACE',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 6: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name2, self.object_name2)
        self.log.info("Retrieved tag of an object")
        self.log.info("Step 7: Compare tagset of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), len(put_resp[1]), len(put_resp[1]))
        for num in range(len(copy_resp[1])):
            assert_utils.assert_not_equal(copy_resp[1][num]["Key"],
                                          put_resp[1][num]["Key"], put_resp[1][num]["Key"])
            assert_utils.assert_not_equal(copy_resp[1][num]["Value"],
                                          put_resp[1][num]["Value"], put_resp[1][num]["Value"])
        self.log.info("Step 7: Compared and verified tag of source and destination object"
                      "are different and do not match")
        self.log.info("Step :Verify tagset of destination object should match with"
                      " tagset assigned in copy_object")
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"],
                                      "{}{}".format(self.key_dest, str(num)),
                                      "{}{}".format(self.key_dest, str(num)))
            assert_utils.assert_equal(copy_resp[1][num]["Value"],
                                      "{}{}".format(self.value_dest, str(num)),
                                      "{}{}".format(self.value_dest, str(num)))
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        self.log.info("ENDED: Test simple copy-object with source object having max number of"
                      " tags(10) and parameter (--tagging-directive=REPLACE)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44817")
    def test_44817(self):
        """
        TEST-44817 :Test simple copy-object with source object tag count different
        than destination object. (--tagging-directive=REPLACE)
        """
        self.log.info("STARTED: Test simple copy-object with source object tag count"
                      " different than destination object. (--tagging-directive=REPLACE)")
        self.log.info("Simple copy-object with source object having max number of tags(N<=10)"
                      " in the same bucket")
        self.log.info("Step 1: Uploading an object and setting tag for object")
        tag_str = ""
        secret_range = random.SystemRandom()
        tag_count_src = secret_range.randint(1, 10)
        tag_count_dest = secret_range.randint(1, 10)
        put_etag = self.create_put_set_object_tag(self.bucket_name1, self.object_name1,
                                                  self.file_path, mb_count=self.mb_count,
                                                  key=self.key_src, value=self.value_src,
                                                  tag_count=tag_count_src)
        self.log.info("Step 1: Uploaded an object and tag is set for object")
        self.log.debug("Retrieving tag of an object %s", self.object_name1)
        put_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        self.log.debug("Retrieved tag of an object")
        self.log.info("Step 2: Copy object to same bucket with different object.")
        for num in range(tag_count_dest):
            tag_str = tag_str + "{}{}".format(self.key_dest, str(num)) + "=" \
                      + "{}{}".format(self.value_dest, str(num)) + "&"
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name1, self.object_name2,
                                                        TaggingDirective='REPLACE',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 3: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Step 3: Retrieved tag of an object")
        self.log.info("Step 4: Compare tag count of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), tag_count_dest, tag_count_dest)
        self.log.info("Step 4: Compared and verified tag count of source and destination object"
                      "are different and do not match")
        self.log.info("Step : Verify tag set of destination object should match with tagset"
                      "assigned in copy object")
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"],
                                      "{}{}".format(self.key_dest, str(num)),
                                      "{}{}".format(self.key_dest, str(num)))
            assert_utils.assert_equal(copy_resp[1][num]["Value"],
                                      "{}{}".format(self.value_dest, str(num)),
                                      "{}{}".format(self.value_dest, str(num)))
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name1,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        self.log.info("Simple copy-object with destination tag set same as source object"
                      "in the different bucket")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name2, self.object_name2,
                                                        TaggingDirective='REPLACE',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 6: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Step 7: Compare tagset of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), tag_count_dest, tag_count_dest)
        self.log.info("Step 7: Compared and verified tag of source and destination object"
                      "are different and do not match")
        self.log.info("Step :Verify tagset of destination object should match with"
                      " tagset assigned in copy_object")
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"],
                                      "{}{}".format(self.key_dest, str(num)),
                                      "{}{}".format(self.key_dest, str(num)))
            assert_utils.assert_equal(copy_resp[1][num]["Value"],
                                      "{}{}".format(self.value_dest, str(num)),
                                      "{}{}".format(self.value_dest, str(num)))
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        self.log.info("ENDED: Test simple copy-object with source object tag count"
                      " different than destination object. (--tagging-directive=REPLACE)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44820")
    def test_44820(self):
        """
        TEST-44820: Test multipart copy-object with destination tag set same as
        source object.(--tagging-directive=COPY)
        """
        self.log.info("STARTED: Test multipart copy-object with multipart upload and destination"
                      " tag set same as source object (--tagging-directive=COPY)")
        self.log.info("Multipart copy multipart object with destination tag set same as source"
                      " object in the same bucket")
        self.log.info("Step 1:Upload multipart object to bucket")
        tag_str = self.key_src + "=" + self.value_src
        resp = self.complete_multipart_upload_with_tagging(self.bucket_name1, self.object_name1,
                                                          self.file_path, total_parts=2,
                                                          file_size=10, object_tag=tag_str)
        self.log.info("Step 1: Uploaded multipart object and tag is set for object")
        self.log.debug("Retrieving tag of an object %s", self.object_name1)
        put_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        self.log.debug("Retrieved tag of an object")
        self.log.info("Step 2: Copy object to same bucket with different object.")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name1, self.object_name2,
                                                        TaggingDirective='COPY', Tagging=tag_str)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        put_etag = resp[1]["ETag"].replace('"', '')
        self.log.info("Step 3: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Step 3: Retrieved tag of an object")
        self.log.info("Step 4: Compare tagset of source and destination object")
        assert_utils.assert_equal(copy_resp[1][0]["Key"], self.key_src, self.key_src)
        assert_utils.assert_equal(copy_resp[1][0]["Value"], self.value_src, self.value_src)
        self.log.info("Step 4: Compared and verified tag of source and destination object")
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name1,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        self.log.info("Multipart copy-object with destination tag set same as source object"
                      "in the different bucket")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name2, self.object_name2,
                                                        TaggingDirective='COPY', Tagging=tag_str)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 6: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Step 7: Compare tagset of source and destination object")
        assert_utils.assert_equal(copy_resp[1][0]["Key"], self.key_src, self.key_src)
        assert_utils.assert_equal(copy_resp[1][0]["Value"], self.value_src, self.value_src)
        self.log.info("Step 7: Compared and verified tag of source and destination object")
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step 8: Verified of etag and metadata for data integrity check")
        self.log.info("ENDED: Test multipart copy-object with multipart upload and destination"
                      " tag set same as source object (--tagging-directive=COPY)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44821")
    def test_44821(self):
        """
        TEST-44821: Test Multipart copy-object with destination tag set replaces
        source object tag set.(--tagging-directive=REPLACE)
        """
        self.log.info("STARTED: Test multipart Copy-object with destination tag set replaces"
                      " source object tag set(--tagging-directive=REPLACE)")
        self.log.info("Multipart Copy-object with destination tag set replaces source object"
                      " tag set in the same bucket")
        self.log.info("Step 1: Uploading an multipart object and setting tag for object")
        tag_str =self.key_src + "=" + self.value_src
        resp = self.complete_multipart_upload_with_tagging(self.bucket_name1, self.object_name1,
                                                          self.file_path, total_parts=2,
                                                          file_size=10, object_tag=tag_str)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Uploaded an multipart object and tag is set for object")
        self.log.debug("Retrieving tag of an object %s", self.object_name1)
        put_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        self.log.debug("Retrieved tag of an object")
        self.log.info("Step 2: Copy object to same bucket with different object.")
        tag_str = self.key_dest + "=" + self.value_dest
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name1, self.object_name2,
                                                        TaggingDirective='REPLACE', Tagging=tag_str)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        put_etag = resp[1]["ETag"].replace('"', '')
        self.log.info("Step 3: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Step 3: Retrieved tag of an object")
        self.log.info("Step 4: Compare tagset of source and destination object")
        assert_utils.assert_not_equal(copy_resp[1][0]["Key"], self.key_src, self.key_src)
        assert_utils.assert_not_equal(copy_resp[1][0]["Value"], self.value_src, self.value_src)
        self.log.info("Step 4: Compared and verified tags of source and destination object"
                      " are different")
        self.log.info("Verify destination tag set match with assigned tag set in copy object")
        assert_utils.assert_equal(copy_resp[1][0]["Key"], self.key_dest, self.key_dest)
        assert_utils.assert_equal(copy_resp[1][0]["Value"], self.value_dest, self.value_dest)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name1,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        self.log.info("Step 5: Copy-object with destination tag set same as source object"
                      "in the different bucket")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name2, self.object_name2,
                                                        TaggingDirective='REPLACE', Tagging=tag_str)
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 6: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Step 7: Compare tagset of source and destination object")
        assert_utils.assert_not_equal(copy_resp[1][0]["Key"], self.key_src, self.key_src)
        assert_utils.assert_not_equal(copy_resp[1][0]["Value"], self.value_src, self.value_src)
        self.log.info("Step 7: Compared and verified tags of source and destination object"
                      "are different and do not match")
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        self.log.info("ENDED: Test multipart Copy-object with destination tag set replaces "
                      "source object tag set(--tagging-directive=REPLACE)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44822")
    def test_44822(self):
        """
        TEST-44822 :Test multipart copy-object with source object having max number of tags(10)
        and parameter (--tagging-directive=COPY)
        """
        self.log.info("STARTED: Test multipart copy-object with source object having max number"
                      " of tags(10) and parameter (--tagging-directive=COPY)")
        self.log.info("Multipart copy-object with source object having max number of tags(10)"
                      "in the same bucket")
        self.log.info("Step 1: Uploading multipart object and setting tag for object")
        tag_str = ""
        for num in range(10):
            tag_str = tag_str + "{}{}".format(self.key_src, str(num)) + "=" \
                      + "{}{}".format(self.value_src, str(num)) + "&"
        resp = self.complete_multipart_upload_with_tagging(self.bucket_name1, self.object_name1,
                                                          self.file_path, total_parts=2,
                                                          file_size=10, object_tag=tag_str[:-1])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Uploaded an object and tag is set for object")
        self.log.debug("Retrieving tag of an object %s", self.object_name1)
        put_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        self.log.debug("Retrieved tag of an object")
        self.log.info("Step 2: Copy object to same bucket with different object.")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name1, self.object_name2,
                                                        TaggingDirective='COPY',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        put_etag = resp[1]["ETag"].replace('"', '')
        self.log.info("Step 3: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Step 3: Retrieved tag of an object")
        self.log.info("Step 4: Compare tagset of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), len(put_resp[1]), len(put_resp[1]))
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"], put_resp[1][num]["Key"],
                                      put_resp[1][num]["Key"])
            assert_utils.assert_equal(copy_resp[1][num]["Value"], put_resp[1][num]["Value"],
                                      put_resp[1][num]["Value"])
        self.log.info("Step 4: Compared and verified tag of source and destination object")
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name1,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        self.log.info("Multipart copy-object with destination tag set same as source object"
                      "in the different bucket")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name2, self.object_name2,
                                                        TaggingDirective='COPY',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 6: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Step 7: Compare tagset of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), len(put_resp[1]), len(put_resp[1]))
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"], put_resp[1][num]["Key"],
                                      put_resp[1][num]["Key"])
            assert_utils.assert_equal(copy_resp[1][num]["Value"], put_resp[1][num]["Value"],
                                      put_resp[1][num]["Value"])
        self.log.info("Step 7: Compared and verified tag of source and destination object")
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        self.log.info("ENDED: Test multipart copy-object with source object having max number"
                      " of tags(10) and parameter (--tagging-directive=COPY)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44824")
    def test_44824(self):
        """
        TEST-44824 :Test multipart copy-object with source object having max number of tags(10)
        and parameter (--tagging-directive=REPLACE)
        """
        self.log.info("STARTED: Test multipart copy-object with source object having max number"
                      " of tags(10) and parameter (--tagging-directive=REPLACE)")
        self.log.info("Multipart Copy-object with source object having max number of tags(10)"
                      "in the same bucket")
        self.log.info("Step 1: Uploading multipart object and setting tag for object")
        tag_str = ""
        for num in range(10):
            tag_str = tag_str + "{}{}".format(self.key_src, str(num)) + "=" \
                      + "{}{}".format(self.value_src, str(num)) + "&"
        resp = self.complete_multipart_upload_with_tagging(self.bucket_name1, self.object_name1,
                                                           self.file_path, total_parts=2,
                                                           file_size=10, object_tag=tag_str[:-1])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Uploaded an object and tag is set for object")
        self.log.debug("Retrieving tag of an object %s", self.object_name1)
        put_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        self.log.debug("Retrieved tag of an object")
        self.log.info("Step 2: Copy object to same bucket with different object.")
        tag_str = ""
        for num in range(10):
            tag_str = tag_str + "{}{}".format(self.key_dest, str(num)) + "=" \
                      + "{}{}".format(self.value_dest, str(num)) + "&"
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name1, self.object_name2,
                                                        TaggingDirective='REPLACE',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        put_etag = resp[1]["ETag"].replace('"', '')
        self.log.info("Step 3: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Step 3: Retrieved tag of an object")
        self.log.info("Step 4: Compare tagset of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), len(put_resp[1]), len(put_resp[1]))
        for num in range(len(copy_resp[1])):
            assert_utils.assert_not_equal(copy_resp[1][num]["Key"], put_resp[1][num]["Key"],
                                          put_resp[1][num]["Key"])
            assert_utils.assert_not_equal(copy_resp[1][num]["Value"], put_resp[1][num]["Value"],
                                          put_resp[1][num]["Value"])
        self.log.info("Step 4: Compared and verified tag of source and destination object"
                      "are different and do not match")
        self.log.info("Step : Verify tag set of destination object should match with tagset"
                      "assigned in copy object")
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"],
                                      "{}{}".format(self.key_dest, str(num)),
                                      "{}{}".format(self.key_dest, str(num)))
            assert_utils.assert_equal(copy_resp[1][num]["Value"],
                                      "{}{}".format(self.value_dest, str(num)),
                                      "{}{}".format(self.value_dest, str(num)))
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name1,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        self.log.info("Multipart copy-object with destination tag set same as source object"
                      "in the different bucket")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name2, self.object_name2,
                                                        TaggingDirective='REPLACE',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 6: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Step 7: Compare tagset of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), len(put_resp[1]), len(put_resp[1]))
        for num in range(len(copy_resp[1])):
            assert_utils.assert_not_equal(copy_resp[1][num]["Key"],
                                          put_resp[1][num]["Key"], put_resp[1][num]["Key"])
            assert_utils.assert_not_equal(copy_resp[1][num]["Value"],
                                          put_resp[1][num]["Value"], put_resp[1][num]["Value"])
        self.log.info("Step 7: Compared and verified tag of source and destination object"
                      "are different and do not match")
        self.log.info("Step :Verify tagset of destination object should match with"
                      " tagset assigned in copy_object")
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"],
                                      "{}{}".format(self.key_dest, str(num)),
                                      "{}{}".format(self.key_dest, str(num)))
            assert_utils.assert_equal(copy_resp[1][num]["Value"],
                                      "{}{}".format(self.value_dest, str(num)),
                                      "{}{}".format(self.value_dest, str(num)))
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        self.log.info("ENDED: Test multipart copy-object with source object having max number"
                      " of tags(10) and parameter (--tagging-directive=REPLACE)")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_object_copy
    @pytest.mark.tags("TEST-44826")
    def test_44826(self):
        """
        TEST-44826 : Test multipart copy-object with source object tag count different than
        destination object. (--tagging-directive=REPLACE).
        """
        self.log.info("STARTED: Test multipart copy-object with source object tag count"
                      " different than destination object. (--tagging-directive=REPLACE).")
        self.log.info("Multipart copy-object with source object having max number of tags(N<=10)"
                      "in the same bucket")
        self.log.info("Step 1: Uploading multipart object and setting tag for object")
        secret_range = random.SystemRandom()
        tag_count_src = secret_range.randint(1, 10)
        tag_count_dest = secret_range.randint(1, 10)
        tag_str = ""
        for num in range(tag_count_src):
            tag_str = tag_str + "{}{}".format(self.key_src, str(num)) + "=" \
                      + "{}{}".format(self.value_src, str(num)) + "&"
        resp = self.complete_multipart_upload_with_tagging(self.bucket_name1, self.object_name1,
                                                           self.file_path, total_parts=2,
                                                           file_size=10, object_tag=tag_str[:-1])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Uploaded an object and tag is set for object")
        self.log.debug("Retrieving tag of an object %s", self.object_name1)
        put_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(put_resp[0], put_resp[1])
        self.log.debug("Retrieved tag of an object")
        self.log.info("Step 2: Copy object to same bucket with different object.")
        tag_str = ""
        for num in range(tag_count_dest):
            tag_str = tag_str + "{}{}".format(self.key_dest, str(num)) + "=" \
                      + "{}{}".format(self.value_dest, str(num)) + "&"
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name1, self.object_name2,
                                                        TaggingDirective='REPLACE',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        put_etag = resp[1]["ETag"].replace('"', '')
        self.log.info("Step 3: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Step 3: Retrieved tag of an object")
        self.log.info("Step 4: Compare tag count of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), tag_count_dest, tag_count_dest)
        self.log.info("Step 4: Compared and verified tag count of source and destination object"
                      "are different and do not match")
        self.log.info("Step : Verify tag set of destination object should match with tagset"
                      "assigned in copy object")
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"],
                                      "{}{}".format(self.key_dest, str(num)),
                                      "{}{}".format(self.key_dest, str(num)))
            assert_utils.assert_equal(copy_resp[1][num]["Value"],
                                      "{}{}".format(self.value_dest, str(num)),
                                      "{}{}".format(self.value_dest, str(num)))
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name1,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step : Verification of etag and metadata for data integrity check")
        self.log.info("Multipart copy-object with destination tag set same as source object"
                      "in the different bucket")
        status, response = self.s3_test_obj.copy_object(self.bucket_name1, self.object_name1,
                                                        self.bucket_name2, self.object_name2,
                                                        TaggingDirective='REPLACE',
                                                        Tagging=tag_str[:-1])
        assert_utils.assert_true(status, response)
        copy_etag = response['CopyObjectResult']['ETag']
        self.log.info("Step 6: Retrieving tag of a destination object %s", self.object_name2)
        copy_resp = self.tag_obj.get_object_tags(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(copy_resp[0], copy_resp[1])
        self.log.info("Retrieved tag of an object")
        self.log.info("Step 7: Compare tagset of source and destination object")
        assert_utils.assert_equal(len(copy_resp[1]), tag_count_dest, tag_count_dest)
        self.log.info("Step 7: Compared and verified tag of source and destination object"
                      "are different and do not match")
        self.log.info("Step :Verify tagset of destination object should match with"
                      " tagset assigned in copy_object")
        for num in range(len(copy_resp[1])):
            assert_utils.assert_equal(copy_resp[1][num]["Key"],
                                      "{}{}".format(self.key_dest, str(num)),
                                      "{}{}".format(self.key_dest, str(num)))
            assert_utils.assert_equal(copy_resp[1][num]["Value"],
                                      "{}{}".format(self.value_dest, str(num)),
                                      "{}{}".format(self.value_dest, str(num)))
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        copy_obj_di_check(self.bucket_name1, self.object_name1, self.bucket_name2,
                          self.object_name2, put_etag=put_etag, copy_etag=copy_etag,
                          s3_testobj=self.s3_test_obj)
        self.log.info("Step 8: Verification of etag and metadata for data integrity check")
        self.log.info("ENDED: Test multipart copy-object with source object tag count"
                      " different than destination object. (--tagging-directive=REPLACE).")
