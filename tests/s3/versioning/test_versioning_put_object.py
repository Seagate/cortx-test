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
#

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


class TestVersioningPutObject:
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
    @pytest.mark.tags('TEST-32724')
    @CTFailOn(error_handler)
    def test_put_object_preexisting_32724(self):
        """
        Test PUT Object for pre-existing object in versioned bucket.
        """
        self.log.info("STARTED: Test PUT Object for preexisting objects with versioning")
        versions = defaultdict(list)
        self.log.info("Step 1: Upload object before enabling versioning")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        versions[self.object_name].insert(0, ("null", "version", res[1]["ETag"]))
        self.log.info("Step 2: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 3: Verify ListObjectVersions output")
        self.s3_ver_test_obj.check_list_object_versions(
            bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 4: Upload a new version for the object")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_equal(res[1]["VersionId"], "null", "Unexpected VersionId")
        versions[self.object_name].insert(0, (res[1]["VersionId"], "version", res[1]["ETag"]))
        self.log.info("Step 5: Verify ListObjectVersions output")
        self.s3_ver_test_obj.check_list_object_versions(
            bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 6: Suspend bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 7: Perform PUT Object to versioning suspended bucket")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1]["VersionId"], "null", "Unexpected VersionId returned")
        versions[self.object_name] = [x for x in versions[self.object_name] if x[0] != "null"]
        versions[self.object_name].insert(0, ("null", "version", res[1]["ETag"]))
        self.log.info("Step 8: Verify ListObjectVersions output")
        self.s3_ver_test_obj.check_list_object_versions(
            bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 9: Enable bucket versioning again")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 10: Upload new version of the object")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_equal(res[1]["VersionId"], "null", "Unexpected VersionId")
        versions[self.object_name].insert(0, (res[1]["VersionId"], "version", res[1]["ETag"]))
        self.log.info("Step 11: Verify ListObjectVersions output")
        self.s3_ver_test_obj.check_list_object_versions(
            bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 12: Verify bucket listing contains a single entry for the object")
        self.s3_ver_test_obj.check_list_objects(
            bucket_name=self.bucket_name, expected_objects=[self.object_name])

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32728')
    @CTFailOn(error_handler)
    def test_put_object_versioning_enabled_32728(self):
        """
        Test PUT Object for object uploaded to a versioned bucket.
        """
        self.log.info("STARTED: Test PUT Object object uploaded to a versioned bucket")
        versions = defaultdict(list)
        self.log.info("Step 1: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Upload object after enabling versioning")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_equal(res[1]["VersionId"], "null", "Unexpected VersionId")
        versions[self.object_name].insert(0, (res[1]["VersionId"], "version", res[1]["ETag"]))
        self.log.info("Step 3: Verify ListObjectVersions output")
        self.s3_ver_test_obj.check_list_object_versions(
            bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 4: Suspend bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 5: Perform PUT Object to versioning suspended bucket")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1]["VersionId"], "null", "Unexpected VersionId returned")
        versions[self.object_name].insert(0, ("null", "version", res[1]["ETag"]))
        self.log.info("Step 6: Verify ListObjectVersions output")
        self.s3_ver_test_obj.check_list_object_versions(
            bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 7: Enable bucket versioning again")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 8: Upload new version of the object")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_equal(res[1]["VersionId"], "null", "Unexpected VersionId ")
        versions[self.object_name].insert(0, (res[1]["VersionId"], "version", res[1]["ETag"]))
        self.log.info("Step 9: Verify ListObjectVersions output")
        self.s3_ver_test_obj.check_list_object_versions(
            bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 10: Verify bucket listing contains a single entry for the object")
        self.s3_ver_test_obj.check_list_objects(
            bucket_name=self.bucket_name, expected_objects=[self.object_name])

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32733')
    @CTFailOn(error_handler)
    def test_put_object_versioning_suspended_32733(self):
        """
        Test PUT Object for object uploaded to a versioning suspended bucket.
        """
        self.log.info("STARTED: Test PUT Object object uploaded to a versioning suspended bucket")
        versions = defaultdict(list)
        self.log.info("Step 1: Suspend bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Upload object after suspending versioning")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1]["VersionId"], "null", "Unexpected VersionId")
        versions[self.object_name].insert(0, ("null", "version", res[1]["ETag"]))
        self.log.info("Step 3: Verify ListObjectVersions output")
        self.s3_ver_test_obj.check_list_object_versions(
            bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 4: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 5: Perform PUT Object to versioning enabled bucket")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_equal(res[1]["VersionId"], "null", "Unexpected VersionId")
        versions[self.object_name].insert(0, (res[1]["VersionId"], "version", res[1]["ETag"]))
        self.log.info("Step 6: Verify ListObjectVersions output")
        self.s3_ver_test_obj.check_list_object_versions(
            bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 7: Verify bucket listing contains a single entry for the object")
        self.s3_ver_test_obj.check_list_objects(
            bucket_name=self.bucket_name, expected_objects=[self.object_name])
