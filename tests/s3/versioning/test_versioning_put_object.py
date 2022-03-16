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

    def check_list_object_versions(self,
                                   bucket_name: str = None,
                                   expected_versions: dict = None) -> None:
        """
        List all the versions and delete markers present in a bucket and verify the output

        :param bucket_name: Bucket name for calling List Object Versions
        :param expected_versions: dict containing list of version tuples, ordered from the latest
            to oldest version created i.e. latest version is at index 0 and oldest at index n-1
            for an object having n versions.

            Expected format of the dict -
                dict keys should be the object name
                tuple for version should have the format (<VersionId>, "version", <ETag>)
                tuple for delete marker should have the format (<VersionId>, "deletemarker", None)

            For eg.
                {"object1": [(<obj1-version-id-2>, 'deletemarker', None),
                             (<obj1-version-id-1>, 'version', <etag1>)],
                 "object2": [(<obj2-version-id-1>, 'version', <etag2>)]}
        """
        self.log.info("Fetching bucket object versions list")
        list_response = self.s3_ver_test_obj.list_object_versions(bucket_name=bucket_name)
        self.log.info("Verifying bucket object versions list for expected contents")
        assert_utils.assert_true(list_response[0], list_response[1])
        actual_versions = list_response[1]["Versions"]
        actual_deletemarkers = list_response[1]["DeleteMarkers"]
        ver_idx = 0
        dm_idx = 0
        for key in sorted(expected_versions.keys()):
            expected_islatest = True
            for expected_version in expected_versions[key]:
                if expected_version[1] == "version":
                    actual_version = actual_versions[ver_idx]
                    assert_utils.assert_equal(
                        actual_version["ETag"], expected_version[2], "Version ETag mismatch")
                    ver_idx = ver_idx + 1
                else:
                    actual_version = actual_deletemarkers[dm_idx]
                    dm_idx = dm_idx + 1
                assert_utils.assert_equal(
                    actual_version["IsLatest"], expected_islatest, "Version IsLatest mismatch")
                assert_utils.assert_equal(
                    actual_version["VersionId"], expected_version[0], "Version VersionId mismatch")
                if expected_islatest:
                    expected_islatest = False
        assert_utils.assert_equal(
            len(actual_versions), ver_idx, "Unexpected Version entry count in the response")
        assert_utils.assert_equal(
            len(actual_deletemarkers), dm_idx,
            "Unexpected DeleteMarker entry count in the response")
        self.log.info("Completed verifying bucket object versions list for expected contents")

    def check_list_objects(self,
                           bucket_name: str = None,
                           expected_objects: list = None) -> None:
        """
        List bucket and verify there are single entries for each versioned object

        :param bucket_name: Bucket name for calling List Object Versions
        :param expected_objects: list containing versioned objects that should be present in
            List Objects output
        """
        self.log.info("Fetching bucket object list")
        list_response = self.s3_ver_test_obj.list_objects_with_prefix(
            bucket_name=bucket_name, maxkeys=1000)
        self.log.info("Verifying bucket object versions list for expected contents")
        assert_utils.assert_true(list_response[0], list_response[1])
        actual_objects = [o["Key"] for o in list_response[1]["Contents"]]
        assert_utils.assert_equal(sorted(actual_objects),
                                  sorted(expected_objects),
                                  "List Objects response does not contain expected object names")

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
        self.check_list_object_versions(bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 4: Upload a new version for the object")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_equal(res[1]["VersionId"], "null", "Unexpected VersionId")
        versions[self.object_name].insert(0, (res[1]["VersionId"], "version", res[1]["ETag"]))
        self.log.info("Step 5: Verify ListObjectVersions output")
        self.check_list_object_versions(bucket_name=self.bucket_name, expected_versions=versions)
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
        self.check_list_object_versions(bucket_name=self.bucket_name, expected_versions=versions)
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
        self.check_list_object_versions(bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 12: Verify bucket listing contains a single entry for the object")
        self.check_list_objects(bucket_name=self.bucket_name, expected_objects=[self.object_name])

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
        self.check_list_object_versions(bucket_name=self.bucket_name, expected_versions=versions)
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
        self.check_list_object_versions(bucket_name=self.bucket_name, expected_versions=versions)
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
        self.check_list_object_versions(bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 10: Verify bucket listing contains a single entry for the object")
        self.check_list_objects(bucket_name=self.bucket_name, expected_objects=[self.object_name])

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
        self.check_list_object_versions(bucket_name=self.bucket_name, expected_versions=versions)
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
        self.check_list_object_versions(bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 7: Verify bucket listing contains a single entry for the object")
        self.check_list_objects(bucket_name=self.bucket_name, expected_objects=[self.object_name])
