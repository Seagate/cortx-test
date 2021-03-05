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

import json
import hashlib
import logging
import time
import os
import pytest
from commons import commands
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import assert_utils
from commons.utils.system_utils import run_local_cmd, create_file, split_file, remove_file
from libs.s3.s3_test_lib import S3TestLib


LOGGER = logging.getLogger(__name__)


class TestAwsCliS3Api:
    """Blackbox AWS CLI S3API Testsuite"""

    @classmethod
    def setup_class(cls):
        """
        Setup all the states required for execution of this test suit.
        """
        LOGGER.info("STARTED : Setup operations at test suit level")
        cls.s3test_obj = S3TestLib()
        cls.bucket_prefix = "blackboxs3bkt"
        cls.object_name = "blackboxs3obj"
        cls.bucket_name = None
        LOGGER.info("ENDED : Setup operations at test suit level")

    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite
        It is performing below operations as pre-requisites
            - Initializes common variables
        """
        LOGGER.info("STARTED : Setup operations at test function level")
        self.bucket_name = "-".join([self.bucket_prefix,
                                     str(int(time.time()))])
        LOGGER.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        """
        Teardown any state that was previously setup with a setup_method
        It is performing below operations as pre-requisites
            - Deletes bucket created during test execution
            - Remove local files created during test execution
        """
        LOGGER.info("STARTED : Teardown operations at test function level")
        buckets = self.s3test_obj.bucket_list()[1]
        if self.bucket_name in buckets:
            self.s3test_obj.delete_bucket_awscli(self.bucket_name, force=True)
        if os.path.exists(self.object_name):
            remove_file(self.object_name)
        LOGGER.info("ENDED : Teardown operations at test function level")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.
        It will clean up resources which are getting created during test suite setup.
        """
        LOGGER.info("STARTED : Teardown operations at test suit level")
        buckets = cls.s3test_obj.bucket_list()[1]
        buckets = [bkt for bkt in buckets if bkt.startswith(cls.bucket_prefix)]
        cls.s3test_obj.delete_multiple_buckets(buckets)
        LOGGER.info("ENDED : Teardown operations at test suit level")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7113")
    @CTFailOn(error_handler)
    def test_2328(self):
        """
        create single bucket using aws cli
        """
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Successfully create single bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7114")
    @CTFailOn(error_handler)
    def test_2329(self):
        """
        Create multiple buckets using aws cli
        """
        buckets = []
        for i in range(2):
            buckets.append("-".join([self.bucket_name, str(i)]))
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=" ".join(buckets))
        assert_utils.assert_false(resp[0], resp[1])
        LOGGER.info("Failed to create multiple buckets at a time using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7115")
    @CTFailOn(error_handler)
    def test_2330(self):
        """
        list buckets using aws cli
        """
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = run_local_cmd(cmd=commands.AWSCLI_LIST_BUCKETS)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.bucket_name)
        LOGGER.info("Successfully listed buckets using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7116")
    @CTFailOn(error_handler)
    def test_2331(self):
        """
        max no of buckets supported using aws cli
        """
        max_buckets = 1000
        for i in range(max_buckets):
            bucket_name = f"{self.bucket_name}{i}"
            resp = self.s3test_obj.create_bucket_awscli(
                bucket_name=bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Successfully created max no. of buckets using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7117")
    @CTFailOn(error_handler)
    def test_2332(self):
        """
        delete empty bucket using aws cli
        """
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3test_obj.delete_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Successfully deleted empty bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7118")
    @CTFailOn(error_handler)
    def test_2333(self):
        """
        delete bucket which has objects using aws cli
        """
        error_msg = "BucketNotEmpty"
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = create_file(fpath=self.object_name, count=1)
        resp = run_local_cmd(
            cmd=commands.AWSCLI_PUT_OBJECT.format(
                self.object_name,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3test_obj.delete_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        LOGGER.info("Failed to delete bucket having objects in it")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7119")
    @CTFailOn(error_handler)
    def test_2334(self):
        """
        Verify HEAD bucket using aws client
        """
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_HEAD_BUCKET.format(
                self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Successfully verified head bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7120")
    @CTFailOn(error_handler)
    def test_2335(self):
        """
        Verification of bucket location using aws
        """
        location = '"LocationConstraint": "US"'
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_GET_BUCKET_LOCATION.format(
                self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], location)
        LOGGER.info("Successfully verified bucket location using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7121")
    @CTFailOn(error_handler)
    def test_2336(self):
        """
        create bucket using existing bucket name using aws cli
        """
        error_msg = "BucketAlreadyOwnedByYou"
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], error_msg)
        LOGGER.info("Failed to create bucket using existing bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7122")
    @CTFailOn(error_handler)
    def test_2337(self):
        """
        Delete bucket forcefully which has objects using aws cli
        """
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = create_file(fpath=self.object_name, count=1)
        resp = run_local_cmd(
            cmd=commands.AWSCLI_PUT_OBJECT.format(
                self.object_name,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3test_obj.delete_bucket_awscli(
            bucket_name=self.bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Successfully deleted bucket having objects in it")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7123")
    @CTFailOn(error_handler)
    def test_2338(self):
        """
        list objects in bucket using AWS
        """
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = create_file(fpath=self.object_name, count=1)
        resp = run_local_cmd(
            cmd=commands.AWSCLI_PUT_OBJECT.format(
                self.object_name,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_LIST_OBJECTS.format(self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)
        LOGGER.info("Successfully listed objects from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7124")
    @CTFailOn(error_handler)
    def test_2339(self):
        """
        delete single object using aws cli
        """
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        create_file(fpath=self.object_name, count=1)
        resp = run_local_cmd(
            cmd=commands.AWSCLI_PUT_OBJECT.format(
                self.object_name,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_LIST_OBJECTS.format(self.bucket_name))
        assert_utils.assert_exact_string(resp[1], self.object_name)
        resp = run_local_cmd(
            cmd=commands.AWSCLI_REMOVE_OBJECTS.format(
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)
        LOGGER.info("Successfully deleted object from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7125")
    @CTFailOn(error_handler)
    def test_2340(self):
        """
        delete multiple object using aws cli
        """
        object_list = list()
        object_count = 3
        filename = "blackboxs3obj"
        create_file(fpath=filename, count=1)
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for i in range(object_count):
            self.object_name = "".join([filename, str(i)])
            resp = run_local_cmd(
                cmd=commands.AWSCLI_PUT_OBJECT.format(
                    filename,
                    self.bucket_name,
                    self.object_name))
            assert_utils.assert_true(resp[0], resp[1])
            resp = run_local_cmd(
                cmd=commands.AWSCLI_LIST_OBJECTS.format(self.bucket_name))
            assert_utils.assert_exact_string(resp[1], self.object_name)
            object_list.append(self.object_name)
        delete_objs_cmd = commands.AWSCLI_REMOVE_OBJECTS.format(
            self.bucket_name, "")
        delete_objs_cmd = " ".join([delete_objs_cmd,
                                    commands.AWSCLI_RECURSIVE_FLAG,
                                    commands.AWSCLI_EXCLUDE_FLAG.format("*"),
                                    commands.AWSCLI_INCLUDE_FLAG.format(object_list[0]),
                                    commands.AWSCLI_INCLUDE_FLAG.format(object_list[1]),
                                    ])
        resp = run_local_cmd(cmd=delete_objs_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], object_list[0])
        assert_utils.assert_exact_string(resp[1], object_list[1])
        LOGGER.info(
            "Successfully deleted multiple objects from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7126")
    @CTFailOn(error_handler)
    def test_2341(self):
        """
        delete max no of objects using aws cli
        """
        object_list = list()
        object_count = 3
        filename = "blackboxs3obj"
        create_file(fpath=filename, count=1)
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for i in range(object_count):
            self.object_name = "".join([filename, str(i)])
            resp = run_local_cmd(
                cmd=commands.AWSCLI_PUT_OBJECT.format(
                    filename,
                    self.bucket_name,
                    self.object_name))
            assert_utils.assert_true(resp[0], resp[1])
            resp = run_local_cmd(
                cmd=commands.AWSCLI_LIST_OBJECTS.format(self.bucket_name))
            assert_utils.assert_exact_string(resp[1], self.object_name)
            object_list.append(self.object_name)
        delete_objs_cmd = " ".join([commands.AWSCLI_REMOVE_OBJECTS.format(
            self.bucket_name, ""), commands.AWSCLI_RECURSIVE_FLAG])
        resp = run_local_cmd(cmd=delete_objs_cmd)
        assert_utils.assert_true(resp[0], resp[1])
        for obj in object_list:
            assert_utils.assert_exact_string(resp[1], obj)
        LOGGER.info(
            "Successfully deleted all objects from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7127")
    @CTFailOn(error_handler)
    def test_2342(self):
        """
        update object of large size of(10gb) using aws cli
        """
        file_size = 10000
        no_of_parts = 10
        split_parts = split_file(self.object_name, file_size, no_of_parts)
        mpu_parts_list = [part["Output"] for part in split_parts]
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Creating Multipart upload")
        resp = run_local_cmd(
            cmd=commands.AWSCLI_CREATE_MULTIPART_UPLOAD.format(
                self.bucket_name, self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        mpu_upload_id = resp[1][resp[1].find(
            "{"):resp[1].rfind("}") + 1]
        mpu_upload_id = json.loads(mpu_upload_id.replace("\\n", ""))["UploadId"]

        LOGGER.info("Listing Multipart uploads")
        resp = run_local_cmd(
            cmd=commands.AWSCLI_LIST_MULTIPART_UPLOADS.format(
                self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], mpu_upload_id)

        LOGGER.info("Uploading parts to bucket")
        for i in range(no_of_parts):
            upload_parts = run_local_cmd(
                commands.AWSCLI_UPLOAD_PARTS.format(
                    self.bucket_name,
                    self.object_name,
                    i + 1,
                    mpu_parts_list[i],
                    mpu_upload_id))
            assert_utils.assert_true(upload_parts[0], upload_parts[1])

        LOGGER.info("Listing uploaded parts")
        resp = run_local_cmd(
            cmd=commands.AWSCLI_LIST_PARTS.format(
                self.bucket_name, self.object_name, mpu_upload_id))
        assert_utils.assert_true(resp[0], resp[1])
        parts_str = resp[1][resp[1].find("{"):resp[1].rfind("}") + 1]
        LOGGER.info(parts_str.replace("\\n", "").replace("\\\\", "\\"))
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

        LOGGER.info("Creating json file for multipart upload")
        json_file = "parts.json"
        with open(json_file, "w") as file:
            json.dump(part_data, file)

        LOGGER.info("Completing multipart upload")
        resp = run_local_cmd(
            cmd=commands.AWSCLI_COMPLETE_MULTIPART.format(
                json_file,
                self.bucket_name,
                self.object_name,
                mpu_upload_id))
        assert_utils.assert_true(resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_LIST_OBJECTS.format(self.bucket_name))
        assert_utils.assert_exact_string(resp[1], self.object_name)
        remove_file(json_file)
        for part in mpu_parts_list:
            remove_file(part)
        LOGGER.info("Successfuly completed multipart upload of a large file")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7128")
    @CTFailOn(error_handler)
    def test_2343(self):
        """
        copy object from bucket using aws cli
        """
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = create_file(fpath=self.object_name, count=1)
        resp = run_local_cmd(
            cmd=commands.AWSCLI_PUT_OBJECT.format(
                self.object_name,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_LIST_OBJECTS.format(self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)
        LOGGER.info("Successfully copied objects to bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3
    @pytest.mark.tags("TEST-7130")
    @CTFailOn(error_handler)
    def test_2344(self):
        """
        download an object using aws cli
        """
        downloaded_file = "get_blackboxs3obj"
        resp = self.s3test_obj.create_bucket_awscli(
            bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = create_file(fpath=self.object_name, count=1)
        before_md5 = hashlib.md5(
            open(
                self.object_name,
                "rb").read()).hexdigest()
        LOGGER.info("Uploading objects to bucket using awscli")
        resp = run_local_cmd(
            cmd=commands.AWSCLI_PUT_OBJECT.format(
                self.object_name,
                self.bucket_name,
                self.object_name))
        assert_utils.assert_true(resp[0], resp[1])
        resp = run_local_cmd(
            cmd=commands.AWSCLI_LIST_OBJECTS.format(self.bucket_name))
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)

        LOGGER.info("Downloading object from bucket using awscli")
        resp = run_local_cmd(
            cmd=commands.AWSCLI_DOWNLOAD_OBJECT.format(
                self.bucket_name,
                self.object_name,
                downloaded_file))
        assert_utils.assert_true(resp[0], resp[1])
        after_md5 = hashlib.md5(open(downloaded_file, "rb").read()).hexdigest()
        assert_utils.assert_equals(
            before_md5,
            after_md5,
            "Downloaded file is not same as uploaded")
        remove_file(downloaded_file)
        LOGGER.info("Successfully downloaded object from bucket using awscli")
