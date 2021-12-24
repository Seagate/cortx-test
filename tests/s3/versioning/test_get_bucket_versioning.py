#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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

"""PUT Object test module for Object Versioning."""

import logging
import os
import time
from collections import defaultdict
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils.system_utils import create_file, path_exists, remove_file
from commons.utils.system_utils import make_dirs, remove_dirs
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib


class TestVersioningGetObject:
    """Test PUT Object API with Object Versioning"""

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_test_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestVersioningPutObject")
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        file_name = "{0}{1}".format("ver_put_obj", time.perf_counter_ns())
        self.file_path = os.path.join(self.test_dir_path, file_name)
        create_file(fpath=self.file_path, count=1)
        self.log.info("Created file: %s", self.file_path)
        self.bucket_name = "ver-bkt-{}".format(time.perf_counter_ns())
        self.object_name = "ver-obj-{}".format(time.perf_counter_ns())
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info("Clean : %s", self.test_dir_path)
        if path_exists(self.file_path):
            res = remove_file(self.file_path)
            self.log.info("cleaned path: %s, res: %s", self.file_path, res)
        if path_exists(self.test_dir_path):
            remove_dirs(self.test_dir_path)
        self.log.info("Cleanup test directory: %s", self.test_dir_path)
        res = self.s3_test_obj.bucket_list()
        pref_list = [
            each_bucket for each_bucket in res[1] if each_bucket.startswith("ver-bkt")]
        if pref_list:
            res = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(res[0], res[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32713')
    @CTFailOn(error_handler)
    def test_get_object_unversioned_32715(self):
        """
        Verify that HTTP status code 200 returned to bucket owner when versioning not Enabled.

        Create bucket.
        Upload object
        Perform GET Bucket Versioning on bucket1
        """
        self.log.info("STARTED : Verify that HTTP status code 200 returned to bucket owner when versioning not Enabled.")
        versions = defaultdict(list)
        self.log.info("Step 1: Upload object")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        self.log.debug("Step 1: response", res)
        versions[self.object_name].insert(0, ("null", "version", res[1]["ETag"]))

        res = self.s3_ver_test_obj.get_bucket_versioning(bucket_name=self.bucket_name)
        self.log.debug("Step 1: response", res)
        assert_utils.assert_true(res[0], res[1])

