#!/usr/bin/python
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
#
"""Test suite for awscli s3api operations"""

import os
import time
import json
import logging
import pytest

from commons import commands
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import assert_utils
from commons.utils import system_utils
from libs.s3.s3_test_lib import S3TestLib

S3T_OBJ = S3TestLib()


class TestAwsCliS3Api:
    """Blackbox AWS CLI S3API Testsuite"""

    @classmethod
    def setup_class(cls):
        """
        Setup all the states required for execution of this test suit.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED : Setup operations at test suit level")
        cls.bucket_prefix = "blackboxs3bkt"
        cls.object_name = "blackboxs3obj"
        cls.file_name = "blackboxs3file"
        cls.downloaded_file = "get_blackboxs3obj"
        cls.test_dir_path = os.path.join(os.getcwd(), "testdata", "TestAwsCliS3Api")
        cls.file_path = os.path.join(cls.test_dir_path, cls.file_name)
        cls.downloaded_file_path = os.path.join(cls.test_dir_path, cls.downloaded_file)
        if not os.path.exists(cls.test_dir_path):
            os.makedirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.log.info("Test file path: %s", cls.file_path)
        cls.bucket_name = None
        cls.log.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite.

        It is performing below operations as pre-requisites
            - Initializes common variables
        """
        self.log.info("STARTED : Setup operations at test function level")
        self.bucket_name = "-".join([self.bucket_prefix,
                                     str(int(time.time()))])
        self.log.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        """
        Teardown any state that was previously setup with a setup_method.

        It is performing below operations as pre-requisites
            - Deletes bucket created during test execution
            - Remove local files created during test execution
        """
        self.log.info("STARTED : Teardown operations at test function level")
        buckets = S3T_OBJ.bucket_list()[1]
        if self.bucket_name in buckets:
            resp = S3T_OBJ.delete_bucket_awscli(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        if system_utils.path_exists(self.file_path):
            system_utils.remove_file(self.file_path)
        if system_utils.path_exists(self.downloaded_file_path):
            system_utils.remove_file(self.downloaded_file_path)
        self.log.info("ENDED : Teardown operations at test function level")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        cls.log.info("STARTED : Teardown operations at test suit level")
        if system_utils.path_exists(cls.test_dir_path):
            system_utils.remove_dirs(cls.test_dir_path)
        cls.log.info("Cleanup test directory: %s", cls.test_dir_path)
        buckets = [bkt for bkt in S3T_OBJ.bucket_list()[1] if bkt.startswith(cls.bucket_prefix)]
        cls.log.info(buckets)
        if buckets:
            resp = S3T_OBJ.delete_multiple_buckets(buckets)
            assert_utils.assert_true(resp[0], resp[1])
        cls.log.info("ENDED : Teardown operations at test suit level")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7113")
    @CTFailOn(error_handler)
    def test_create_single_bucket_2328(self):
        """create single bucket using aws cli."""
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Successfully create single bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7114")
    @CTFailOn(error_handler)
    def test_create_multiple_bucket_2329(self):
        """Create multiple buckets using aws cli."""
        buckets = []
        for i in range(2):
            buckets.append("-".join([self.bucket_name, str(i)]))
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=" ".join(buckets))
        assert_utils.assert_false(resp[0], resp[1])
        self.log.info("Failed to create multiple buckets at a time using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7115")
    @CTFailOn(error_handler)
    def test_list_buckets_2330(self):
        """list buckets using aws cli."""
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.run_local_cmd(cmd=commands.CMD_AWSCLI_LIST_BUCKETS)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.bucket_name)
        self.log.info("Successfully listed buckets using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7116")
    @CTFailOn(error_handler)
    def test_create_max_buckets_2331(self):
        """max no of buckets supported using aws cli."""
        max_buckets = 1000
        for i in range(max_buckets):
            bucket_name = f"{self.bucket_name}{i}"
            resp = S3T_OBJ.create_bucket_awscli(
                bucket_name=bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Successfully created max no. of buckets using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7117")
    @CTFailOn(error_handler)
    def test_delete_empty_bucket_2332(self):
        """delete empty bucket using aws cli."""
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3T_OBJ.delete_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Successfully deleted empty bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7118")
    @CTFailOn(error_handler)
    def test_delete_non_empty_bucket_2333(self):
        """delete bucket which has objects using aws cli."""
        error_msg = "BucketNotEmpty"
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file(fpath=self.file_path, count=1)
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3T_OBJ.delete_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.log.info("Failed to delete bucket having objects in it")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7119")
    @CTFailOn(error_handler)
    def test_head_bucket_2334(self):
        """Verify HEAD bucket using aws client."""
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_HEAD_BUCKET.format(
                self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Successfully verified head bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7120")
    @CTFailOn(error_handler)
    def test_bucket_location_2335(self):
        """Verification of bucket location using aws."""
        location = '"LocationConstraint": "US"'
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_GET_BUCKET_LOCATION.format(
                self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], location)
        self.log.info("Successfully verified bucket location using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7121")
    @CTFailOn(error_handler)
    def test_create_duplicate_bucket_2336(self):
        """create bucket using existing bucket name using aws cli."""
        error_msg = "BucketAlreadyOwnedByYou"
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        self.log.info("Failed to create bucket using existing bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7122")
    @CTFailOn(error_handler)
    def test_delete_bucket_forcefully_2337(self):
        """Delete bucket forcefully which has objects using aws cli."""
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file(fpath=self.file_path, count=1)
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3T_OBJ.delete_bucket_awscli(
            bucket_name=self.bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Successfully deleted bucket having objects in it")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7123")
    @CTFailOn(error_handler)
    def test_list_objects_2338(self):
        """list objects in bucket using AWS."""
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file(fpath=self.file_path, count=1)
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)
        self.log.info("Successfully listed objects from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7124")
    @CTFailOn(error_handler)
    def test_delete_single_object_2339(self):
        """delete single object using aws cli."""
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        system_utils.create_file(fpath=self.file_path, count=1)
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name))
        assert_utils.assert_exact_string(resp[1], self.object_name)
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_REMOVE_OBJECTS.format(
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)
        self.log.info("Successfully deleted object from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7125")
    @CTFailOn(error_handler)
    def test_delete_multiple_objects_2340(self):
        """delete multiple object using aws cli."""
        object_list = list()
        object_count = 3
        system_utils.create_file(fpath=self.file_path, count=1)
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for i in range(object_count):
            self.object_name = "".join([self.file_name, str(i)])
            resp = system_utils.run_local_cmd(
                cmd=commands.CMD_AWSCLI_PUT_OBJECT.format(
                    self.file_path,
                    self.bucket_name,
                    self.object_name))
            assert_utils.assert_true(resp[0], resp[1])
            resp = system_utils.run_local_cmd(
                cmd=commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name))
            assert_utils.assert_exact_string(resp[1], self.object_name)
            object_list.append(self.object_name)
        delete_objs_cmd = commands.CMD_AWSCLI_REMOVE_OBJECTS.format(
            self.bucket_name, "")
        delete_objs_cmd = " ".join([delete_objs_cmd,
                                    commands.CMD_AWSCLI_RECURSIVE_FLAG,
                                    commands.CMD_AWSCLI_EXCLUDE_FLAG.format("*"),
                                    commands.CMD_AWSCLI_INCLUDE_FLAG.format(object_list[0]),
                                    commands.CMD_AWSCLI_INCLUDE_FLAG.format(object_list[1]),
                                    ])
        resp = system_utils.run_local_cmd(cmd=delete_objs_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], object_list[0])
        assert_utils.assert_exact_string(resp[1], object_list[1])
        self.log.info(
            "Successfully deleted multiple objects from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7126")
    @CTFailOn(error_handler)
    def test_delete_all_objects_2341(self):
        """delete max no of objects using aws cli."""
        object_list = list()
        object_count = 3
        system_utils.create_file(fpath=self.file_path, count=1)
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for i in range(object_count):
            self.object_name = "".join([self.file_name, str(i)])
            resp = system_utils.run_local_cmd(
                cmd=commands.CMD_AWSCLI_PUT_OBJECT.format(
                    self.file_path,
                    self.bucket_name,
                    self.object_name))
            assert_utils.assert_true(resp[0], resp[1])
            resp = system_utils.run_local_cmd(
                cmd=commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name))
            assert_utils.assert_exact_string(resp[1], self.object_name)
            object_list.append(self.object_name)
        delete_objs_cmd = " ".join([commands.CMD_AWSCLI_REMOVE_OBJECTS.format(
            self.bucket_name, ""), commands.CMD_AWSCLI_RECURSIVE_FLAG])
        resp = system_utils.run_local_cmd(cmd=delete_objs_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        for obj in object_list:
            assert_utils.assert_exact_string(resp[1], obj)
        self.log.info(
            "Successfully deleted all objects from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7127")
    @CTFailOn(error_handler)
    def test_multipart_upload_2342(self):
        """update object of large size of(10gb) using aws cli."""
        file_size = 10000
        no_of_parts = 10
        split_parts = system_utils.split_file(self.file_path, file_size, no_of_parts)
        mpu_parts_list = [part["Output"] for part in split_parts]
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Creating Multipart upload")
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_CREATE_MULTIPART_UPLOAD.format(
                self.bucket_name, self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        mpu_upload_id = resp[1][resp[1].find(
            "{"):resp[1].rfind("}") + 1]
        mpu_upload_id = json.loads(mpu_upload_id.replace("\\n", ""))["UploadId"]
        self.log.info("Listing Multipart uploads")
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_LIST_MULTIPART_UPLOADS.format(
                self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], mpu_upload_id)
        self.log.info("Uploading parts to bucket")
        for i in range(no_of_parts):
            upload_parts = system_utils.run_local_cmd(
                commands.CMD_AWSCLI_UPLOAD_PARTS.format(
                    self.bucket_name,
                    self.object_name,
                    i + 1,
                    mpu_parts_list[i],
                    mpu_upload_id))
            assert_utils.assert_true(upload_parts[0], upload_parts[1])
        self.log.info("Listing uploaded parts")
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_LIST_PARTS.format(
                self.bucket_name, self.object_name, mpu_upload_id))
        assert_utils.assert_true(resp[0], resp[1])
        parts_str = resp[1][resp[1].find("{"):resp[1].rfind("}") + 1]
        self.log.info(parts_str.replace("\\n", "").replace("\\\\", "\\"))
        list_parts = json.loads(
            parts_str.replace(
                "\\n",
                "").replace(
                "\\\\",
                "\\"))["Parts"]
        part_data = dict()
        part_data["Parts"] = list()
        for i in range(no_of_parts):
            part_data["Parts"].append(
                {"PartNumber": list_parts[i]["PartNumber"], "ETag": list_parts[i]["ETag"]})
        self.log.info("Creating json file for multipart upload")
        json_file = "parts.json"
        with open(json_file, "w") as file:
            json.dump(part_data, file)
        self.log.info("Completing multipart upload")
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_COMPLETE_MULTIPART.format(
                json_file,
                self.bucket_name,
                self.object_name,
                mpu_upload_id))
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name))
        assert_utils.assert_exact_string(resp[1], self.object_name)
        system_utils.remove_file(json_file)
        for part in mpu_parts_list:
            system_utils.remove_file(part)
        self.log.info("Successfully completed multipart upload of a large file")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7128")
    @CTFailOn(error_handler)
    def test_copy_object_to_bucket_2343(self):
        """copy object from bucket using aws cli."""
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file(fpath=self.file_path, count=1)
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)
        self.log.info("Successfully copied objects to bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7130")
    @CTFailOn(error_handler)
    def test_download_object_from_bucket_2344(self):
        """download an object using aws cli."""
        resp = S3T_OBJ.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file(fpath=self.file_path, count=1)
        before_checksum = system_utils.calculate_checksum(self.file_path)
        self.log.info("File path: %s, before_checksum: %s", self.file_path, before_checksum)
        self.log.info("Uploading objects to bucket using awscli")
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)
        self.log.info("Downloading object from bucket using awscli")
        resp = system_utils.run_local_cmd(
            cmd=commands.CMD_AWSCLI_DOWNLOAD_OBJECT.format(
                self.bucket_name,
                self.object_name,
                self.downloaded_file_path))
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = system_utils.calculate_checksum(self.downloaded_file_path)
        self.log.info("File path: %s, before_checksum: %s", self.downloaded_file_path, before_checksum)
        assert_utils.assert_equals(
            before_checksum,
            download_checksum,
            f"Downloaded file is not same as uploaded: {before_checksum}, {download_checksum}")
        system_utils.remove_file(self.downloaded_file_path)
        self.log.info("Successfully downloaded object from bucket using awscli")
