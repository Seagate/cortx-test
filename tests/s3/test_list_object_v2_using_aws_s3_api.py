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

"""List-Object-V2 test module."""

import os
import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.params import TEST_DATA_FOLDER
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_test_lib import AWScliS3api

S3_OBJ = S3TestLib()
AWS_CLI_OBJ = AWScliS3api()


class TestObjectV2List:
    """List-Object-V2 TestSuite."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Summary: Setup method.

        Description: This function will be invoked prior to each test case. It will perform all
        prerequisite test steps if any and cleanup.
        """
        self.log = logging.getLogger(__name__)
        self.bucket_name = "s3bkt-{}".format(time.perf_counter_ns())
        self.object_prefix = "s3obj"
        self.folder_path = os.path.join(TEST_DATA_FOLDER, "TestObjectV2List")
        if not system_utils.path_exists(self.folder_path):
            system_utils.make_dirs(self.folder_path)
        self.log.info("Test data path: %s", self.folder_path)
        yield
        if system_utils.path_exists(self.folder_path):
            system_utils.remove_dirs(self.folder_path)
        bktlist = S3_OBJ.bucket_list()[1]
        if self.bucket_name in bktlist:
            resp = S3_OBJ.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])

    def create_bucket_upload_folder(self, bucket_name) -> list:
        """
        Create a bucket using aws s3 mb upload folder in it.

        :param bucket_name: Name of the bucket.
        :return: Upload file response.
        """
        self.log.info("Create a bucket '%s' using aws s3 mb.", bucket_name)
        resp = AWS_CLI_OBJ.create_bucket(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Upload few object in hierarchical and non-hierarchical list.")
        system_utils.create_dir_hierarchy_and_objects(self.folder_path,
                                                      self.object_prefix,
                                                      depth=6,
                                                      obj_count=10)
        resp = AWS_CLI_OBJ.upload_directory(bucket_name, self.folder_path)
        assert_utils.assert_true(resp[0], resp[1])

        return resp[1]

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-15187")
    @CTFailOn(error_handler)
    def test_15187(self):
        """Test to lists the objects in the specified bucket using list-objects-v2."""
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info(
            "Run list-objects-v2 to lists the objects in the specified bucket.")
        resp = AWS_CLI_OBJ.list_objects_v2(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-15188")
    @CTFailOn(error_handler)
    def test_15188(self):
        """Test list-objects-v2--delimiter options using aws s3api."""
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info("Run list-objects-v2 --delimiter to group keys.")
        resp = AWS_CLI_OBJ.list_objects_v2(self.bucket_name, delimiter="/")
        assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-15189")
    @CTFailOn(error_handler)
    def test_15189(self):
        """Test list-objects-v2 --prefix options using aws s3api."""
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info(
            "Run list-objects-v2 --prefix to Limits the response to keys that begin "
            "with the specified prefix.")
        resp = AWS_CLI_OBJ.list_objects_v2(
            self.bucket_name, prefix=self.object_prefix)
        assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-15190")
    @CTFailOn(error_handler)
    def test_15190(self):
        """Test list-objects-v2 --delimiter and --prefix options using aws s3api."""
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info(
            "Run list-objects-v2  --delimiter and --prefix to Limits the response to keys"
            " that begin with the specified prefix and group similar key with delimiter")
        resp = AWS_CLI_OBJ.list_objects_v2(
            self.bucket_name, prefix=self.object_prefix, delimiter='/')
        assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-15191")
    @CTFailOn(error_handler)
    def test_15191(self):
        """Test list-objects-v2 --max-items and --starting-token option using aws s3api."""
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info(
            "Run list-objects-v2 --max-items and --starting-token option for total number"
            " of items to return in the command's output and then token to specify where"
            " to start paginating. This is the NextToken from a previously truncated response.")
        resp = AWS_CLI_OBJ.list_objects_v2(
            self.bucket_name, prefix=self.bucket_name, max_items=2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = AWS_CLI_OBJ.list_objects_v2(
            self.bucket_name,
            prefix=self.bucket_name,
            starting_token="")
        assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-15194")
    @CTFailOn(error_handler)
    def test_15194(self):
        """Test list-objects-v2 --fetch-owner and --no-fetch-owner using aws s3api."""
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info(
            "Run list-objects-v2 to test --fetch-owner and --no-fetch-owner using existing bucket.")
        resp = AWS_CLI_OBJ.list_objects_v2(self.bucket_name, fetch_owner=None)
        assert_utils.assert_true(resp[0], resp[1])
        resp = AWS_CLI_OBJ.list_objects_v2(
            self.bucket_name, no_fetch_owner=None)
        assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-15192")
    @CTFailOn(error_handler)
    def test_15192(self):
        """Test list-objects-v2 --start-after option using aws s3api."""
        self.create_bucket_upload_folder(self.bucket_name)
        self.log.info(
            "Run list-objects-v2 --start-after to list all keys after the key specified.")
        resp = AWS_CLI_OBJ.list_objects_v2(
            self.bucket_name, start_after=self.object_prefix)
        assert_utils.assert_true(resp[0], resp[1])
