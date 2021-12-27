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

"""PUT bucket versioning test module for bucket Versioning."""

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


class TestVersioningPutBucket:
    """Test PUT bucket versioning for Enabled/Suspended state."""

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_test_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestVersioningPutBucket")####
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
    @pytest.mark.tags('TEST-32631')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_enabled_32631(self):
        """
        Test PUT bucket versioning API for Enabling bucket versioning.

        Create bucket.
        Perform PUT Bucket Versioning API with status set to Enabled.
        Perform GET Bucket Versioning on bucket1.
        Verify versioning status as Enabled.
        """
        self.log.info("STARTED: Test PUT bucket versioning API for Enabling bucket versioning")
        versions = defaultdict(list)
        self.log.info("Step 1: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Get bucket versioning")
        res = self.s3_ver_test_obj.get_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])

        #self.log.info("Step 2: Upload object after enabling versioning")
        #res = self.s3_test_obj.put_object(
        #    bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        #assert_utils.assert_true(res[0], res[1])
        #assert_utils.assert_not_equal(res[1]["VersionId"], "null", "Unexpected VersionId")
        #versions[self.object_name].insert(0, (res[1]["VersionId"], "version", res[1]["ETag"]))
        #self.log.info("Step 3: Verify ListObjectVersions output")
        #self.s3_ver_test_obj.check_list_object_versions(
        #    bucket_name=self.bucket_name, expected_versions=versions)
        # self.log.info("Step 4: Suspend bucket versioning")
        # res = self.s3_ver_test_obj.put_bucket_versioning(
        #     bucket_name=self.bucket_name, status="Suspended")
        # assert_utils.assert_true(res[0], res[1])
        # self.log.info("Step 5: Perform PUT Object to versioning suspended bucket")
        # res = self.s3_test_obj.put_object(
        #     bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        # assert_utils.assert_true(res[0], res[1])
        # assert_utils.assert_equal(res[1]["VersionId"], "null", "Unexpected VersionId returned")
        # versions[self.object_name].insert(0, ("null", "version", res[1]["ETag"]))
        # self.log.info("Step 6: Verify ListObjectVersions output")
        # self.s3_ver_test_obj.check_list_object_versions(
        #     bucket_name=self.bucket_name, expected_versions=versions)
        # self.log.info("Step 7: Enable bucket versioning again")
        # res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        # assert_utils.assert_true(res[0], res[1])
        # self.log.info("Step 8: Upload new version of the object")
        # res = self.s3_test_obj.put_object(
        #     bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        # assert_utils.assert_true(res[0], res[1])
        # assert_utils.assert_not_equal(res[1]["VersionId"], "null", "Unexpected VersionId ")
        # versions[self.object_name].insert(0, (res[1]["VersionId"], "version", res[1]["ETag"]))
        # self.log.info("Step 9: Verify ListObjectVersions output")
        # self.s3_ver_test_obj.check_list_object_versions(
        #     bucket_name=self.bucket_name, expected_versions=versions)
        # self.log.info("Step 10: Verify bucket listing contains a single entry for the object")
        # self.s3_ver_test_obj.check_list_objects(
        #     bucket_name=self.bucket_name, expected_objects=[self.object_name])

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32713')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_suspended_TEST-32713(self):
        """
        Test PUT Suspended bucket versioning.

        Create bucket.
        Perform PUT API to Suspend the bucket versioning.
        Verify the response HTTP status 200.
        Perform Get bucket versioning and validate the Suspended versioning state of the bucket..
        """
        self.log.info("STARTED: Test PUT Suspended bucket versioning.")
        versions = defaultdict(list)
        self.log.info("Step 1: Suspend the bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Get bucket versioning status after suspending versioning")
        res = self.s3_test_obj.put_object(
            bucket_name=self.bucket_name, object_name=self.object_name, file_path=self.file_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1]["VersionId"], "null", "Unexpected VersionId")
        versions[self.object_name].insert(0, ("null", "version", res[1]["ETag"]))
        self.log.info("Step 3: Verify ListObjectVersions output")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32718')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_non_bucket_owner_TEST-32718(self):
        """
        Test PUT Enabled/Suspended bucket versioning by non bucket owner.

        Create bucket.
        Perform PUT API to Enable/Suspend the bucket versioning.
        Verify the response HTTP status 403 and error message: Access Denied.
        """
        self.log.info("STARTED: PUT Enabled/Suspended bucket versioning by non bucket owner.")
        versions = defaultdict(list)
        self.log.info("Step 1: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.
        self.log.info("Step 1: Suspend the bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32719')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_non_bucket_owner_TEST-32719(self):
        """
        Test PUT Enabled/Suspended bucket versioning by non bucket owner.

        Create bucket.
        Perform PUT API to Enable/Suspend the bucket versioning.
        Verify the response HTTP status 403 and error message: Access Denied.
        """
        self.log.info("STARTED: PUT Enabled/Suspended bucket versioning by non bucket owner.")
        versions = defaultdict(list)
        self.log.info("Step 1: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.
        self.log.info("Step 1: Suspend the bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.


    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32747')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_non_bucket_owner_TEST-32719(self):
        """
        Test PUT Unversion/Disable bucket versioning when versioning not set.

        Create bucket.
        Perform PUT API to Disable/Unversioning the bucket versioning by non bucket owner.
        Perform PUT API to Disable/Unversioning the bucket versioning by bucket owner.
        """
        self.log.info("STARTED: PUT Unversion/Disable bucket versioning when versioning not set.")
        versions = defaultdict(list)
        self.log.info("Step 1: PUT API to Disable/Unversioning the bucket versioning by non bucket owner")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.
        self.log.info("Step 1: PUT API to Disable/Unversioning the bucket versioning by bucket owner")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Disable")
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32749')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_unversioned_non_bucket_owner_TEST-32749(self):
        """
        Test PUT Unversioned/Disable bucket versioning when versioning set Enabed/Suspended.

        Create bucket.
        Perform PUT Bucket Versioning API with status set to Enabled.
        Perform PUT bucket versioning API with status set to 'Unversioned/Disable' by non bucket owner/user.
        PUT Bucket Versioning with status=Unversioned as bucket owner
        """
        self.log.info("STARTED: PUT Unversioned/Disable bucket versioning when versioning set Enabed/Suspended.")
        versions = defaultdict(list)
        self.log.info("Step 1: Perform PUT Bucket Versioning API with status set to Enabled")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.
        self.log.info("Step 2: PUT bucket versioning API with status set to 'Unversioned/Disable' by non bucket owner/user")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Disable")
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.
        self.log.info("Step 3: PUT Bucket Versioning with status=Unversioned as bucket owner")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Disable")
        assert_utils.assert_true(res[0], res[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-33514')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_enabled/suspended_deleted_bucket_TEST-33514(self):
        """
        Test PUT Enabled/Suspended bucket versioning when bucket is deleted.

        Create bucket.
        DELETE bucket bucket1.
        Perform PUT Bucket Versioning API with status set to 'Enabled/Suspended' by bucket owner.
        """
        self.log.info("STARTED: PUT Enabled/Suspended bucket versioning when bucket is deleted.")
        versions = defaultdict(list)
        self.log.info("Step 1: Perform PUT Bucket Versioning API with status set to Enabled")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.
        self.log.info("Step 2: Perform PUT Bucket Versioning API with status set to Suspended")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Disable")
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32750')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_enabled/suspended_across_instances_TEST-32750(self):
        """
        Test PUT bucket versioning status is Enabled/Suspended across instances.

        Create bucket.
        Perform PUT Bucket Versioning API with status set to 'Enabled/Suspended' by bucket owner, against node IPs.
        Perform GET Bucket Versioning for the bucket against node IPs.
        """
        self.log.info("STARTED: PUT bucket versioning status is Enabled/Suspended across instances.")
        versions = defaultdict(list)
        self.log.info("Step 1: PUT Bucket Versioning API with status set to 'Enabled/Suspended' by bucket owner, against node IPs.")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.
        self.log.info("Step 2: Perform GET Bucket Versioning for the bucket against node IPs.")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Disable")
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-33513')
    @CTFailOn(error_handler)
    def test_put_bucket_versioning_enabled/suspended_across_instances_TEST-33513(self):
        """
        Test PUT bucket versioning status is Enabled/Suspended across instances post reboot.

        Create bucket.
        Perform PUT Bucket Versioning API with status set to 'Enabled/Suspended' by bucket owner, against node IPs.
        Perform GET Bucket Versioning for the bucket against node IPs.
        """
        self.log.info("STARTED: PUT bucket versioning status is Enabled/Suspended across instances.")
        versions = defaultdict(list)
        self.log.info("Step 1: Connect to server/s3 instance.")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.
        self.log.info("Step 2: Reboot the server/s3 instance.")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Disable")
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.
        self.log.info("Step 3: Perform GET Bucket Versioning API.")
        res = self.s3_ver_test_obj.put_bucket_versioning(
            bucket_name=self.bucket_name, status="Enabled/Suspeded")
        assert_utils.assert_true(res[0], res[1])
        #verify error code 403.
