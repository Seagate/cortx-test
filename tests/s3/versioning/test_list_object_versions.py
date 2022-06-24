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

"""List Object Versions test module for Object Versioning."""

import copy
import logging
import os
import time
import pytest

from commons import error_messages as errmsg
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils.system_utils import create_file, path_exists, remove_file
from commons.utils.system_utils import make_dirs, remove_dirs
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3.s3_versioning_common_test_lib import check_list_object_versions
from libs.s3.s3_versioning_common_test_lib import empty_versioned_bucket
from libs.s3.s3_versioning_common_test_lib import upload_versions


class TestListObjectVersions:
    """Test List Object Versions API with Object Versioning"""

    # pylint:disable=attribute-defined-outside-init
    # pylint:disable-msg=too-many-instance-attributes
    def setup_method(self):
        """
        Function will be perform prerequisite test steps prior to each test case.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_test_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestListObjectVersions")
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        file_name1 = "{0}{1}".format("ver_list_versions", time.perf_counter_ns())
        file_name2 = "{0}{1}".format("ver_list_versions", time.perf_counter_ns())
        file_name3 = "{0}{1}".format("ver_list_versions", time.perf_counter_ns())
        download_file = "{0}{1}".format("ver_download", time.perf_counter_ns())
        self.file_path1 = os.path.join(self.test_dir_path, file_name1)
        self.file_path2 = os.path.join(self.test_dir_path, file_name2)
        self.file_path3 = os.path.join(self.test_dir_path, file_name3)
        self.download_path = os.path.join(self.test_dir_path, download_file)
        self.upload_file_paths = [self.file_path1, self.file_path2, self.file_path3]
        for file_path in self.upload_file_paths:
            create_file(file_path, 1, "/dev/urandom")
            self.log.info("Created file: %s", file_path)
        self.bucket_name = "ver-bkt-{}".format(time.perf_counter_ns())
        self.object_name1 = "key-name-obj1-{}".format(time.perf_counter_ns())
        self.object_name2 = "key-name-obj2-{}".format(time.perf_counter_ns())
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)

    def teardown_method(self):
        """
        Function will be invoked after each test case to clean up any test artifacts.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info("Clean : %s", self.test_dir_path)
        for file_path in (self.file_path1, self.file_path2, self.file_path3, self.download_path):
            if path_exists(file_path):
                res = remove_file(file_path)
                self.log.info("cleaned path: %s, res: %s", file_path, res)
        if path_exists(self.test_dir_path):
            remove_dirs(self.test_dir_path)
        self.log.info("Cleanup test directory: %s", self.test_dir_path)
        res = self.s3_test_obj.bucket_list()
        pref_list = []
        for bucket_name in res[1]:
            if bucket_name.startswith("ver-bkt"):
                empty_versioned_bucket(self.s3_ver_test_obj, bucket_name)
                pref_list.append(bucket_name)
        if pref_list:
            res = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(res[0], res[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-34290")
    @CTFailOn(error_handler)
    def test_list_object_versions_nonexisting_or_empty_bucket_34290(self):
        """
        Test List Object Versions on a non-existing or empty bucket.
        """
        self.log.info("STARTED: Test List Object Versions on non-existent/empty bucket")
        self.log.info("Step 1: Test List Object Versions on a non-existent bucket")
        non_existent_bucket = "ver-bkt-{}".format(time.perf_counter_ns())
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=non_existent_bucket,
                                   expected_error=errmsg.NO_BUCKET_OBJ_ERR_KEY,
                                   expected_versions={})
        self.log.info("Step 2: Test List Object Versions on empty bucket")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions={})
        self.log.info("Step 3: Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 4: Test List Object Versions on an empty versioned bucket")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions={})
        self.log.info("Step 5: Suspend bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: Test List Object Versions on an empty versioning suspended bucket")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions={})
        self.log.info("ENDED: Test List Object Versions on non-existent/empty bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-34291")
    @CTFailOn(error_handler)
    def test_list_object_versions_delimiter_34291(self):
        """
        Test List Object Versions with delimiter request parameter
        """
        self.log.info("STARTED: Test List Object Versions with delimiter request parameter.")
        self.log.info("Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Setup versions in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", self.object_name1, 3),
                                             ("Enabled", self.object_name2, 3)])
        for versioning_status in ["Enabled", "Suspended"]:
            versioning_status_log = "Set bucket versioning status to {}".format(versioning_status)
            self.log.info(versioning_status_log)
            res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                             status=versioning_status)
            assert_utils.assert_true(res[0], res[1])
            self.log.info("Step 1: Test List Object Versions with non-existing delimiter")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"Delimiter": "%"}, expected_versions=versions)
            self.log.info("Step 2: Test List Object Versions with empty delimiter")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"Delimiter": ""}, expected_versions=versions)
            self.log.info("Step 3: Test List Object Versions with valid delimiter")
            expected_flags = {"CommonPrefixes": [{"Prefix": self.object_name2}]}
            expected_versions = {self.object_name1: versions[self.object_name1]}
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"Delimiter": self.object_name2},
                                       expected_versions=expected_versions,
                                       expected_flags=expected_flags)
            self.log.info("Step 4: Test List Object Versions with valid delimiter and prefix")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"Delimiter": "obj2", "Prefix": "key"},
                                       expected_versions=expected_versions,
                                       expected_flags=expected_flags)
            self.log.info("Step 5: Test List Object Versions with valid delimiter and non-existent"
                          " prefix")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"Delimiter": "obj2", "Prefix": "key1"},
                                       expected_versions={})
            self.log.info("Step 6: Test List Object Versions with non-existent delimiter and "
                          "valid prefix")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"Delimiter": "obj3", "Prefix": "key"},
                                       expected_versions=versions)
            self.log.info("Step 7: Test List Object Versions with valid delimiter and valid prefix"
                          " and max-keys set to value greater than mumber of entries")
            flags = {"Delimiter": "obj2", "Prefix": "key", "MaxKeys": 4}
            expected_flags = {"Delimiter": "obj2", "Prefix": "key", "MaxKeys": 4,
                              "CommonPrefixes": [{"Prefix": self.object_name2}]}
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params=flags, expected_flags=expected_flags,
                                       expected_versions=expected_versions)
            self.log.info("Step 8: Test List Object Versions with valid delimiter and valid prefix"
                          " and max-keys set to value less than or equal to number of entries")
            flags = {"Delimiter": "obj2", "Prefix": "key", "MaxKeys": 3}
            expected_flags = {"Delimiter": "obj2", "Prefix": "key", "MaxKeys": 3,
                              "IsTruncated": "true", "NextKeyMarker": self.object_name1,
                              "NextVersionIdMarker": versions[self.object_name1]["is_latest"]}
            expected_versions = {self.object_name1: versions[self.object_name1]}
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params=flags, expected_flags=flags,
                                       expected_versions=expected_versions)
            self.log.info("Step 9: Fetch next page of results")
            flags = {"KeyMarker": self.object_name1, "Delimiter": "obj2", "Prefix": "key",
                     "VersionIdMarker": versions[self.object_name1]["is_latest"],  "MaxKeys": 3}
            expected_flags = {"IsTruncated": "false",
                              "CommonPrefixes": [{"Prefix": self.object_name2}]}
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params=flags, expected_flags=expected_flags,
                                       expected_versions={})
        self.log.info("ENDED: Test List Object Versions with delimiter request parameter.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-34292")
    @CTFailOn(error_handler)
    def test_list_object_versions_encoding_type_34292(self):
        """
        Test List Object Versions with encoding-type request parameter
        """
        self.log.info("STARTED: Test List Object Versions with encoding-type request parameter")
        self.log.info("Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Setup versions in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", self.object_name1, 3),
                                             ("Enabled", self.object_name2, 3)])
        for versioning_status in ["Enabled", "Suspended"]:
            versioning_status_log = "Set bucket versioning status to {}".format(versioning_status)
            self.log.info(versioning_status_log)
            res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                             status=versioning_status)
            assert_utils.assert_true(res[0], res[1])
            self.log.info("Step 1: Test List Object Versions with empty encoding-type")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"EncodingType": ""},
                                       expected_versions=versions)
            self.log.info("Step 2: Test List Object Versions with invalid encoding-type")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"EncodingType": "text"},
                                       expected_versions=versions)
            self.log.info("Step 3: Test List Object Versions with valid encoding-type")
            flags = {"EncodingType": "url"}
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params=flags, expected_flags=flags,
                                       expected_versions=versions)
        self.log.info("ENDED: Test List Object Versions with encoding-type request parameter")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-34293")
    @CTFailOn(error_handler)
    def test_list_object_versions_key_marker_34293(self):
        """
        Test List Object Versions with key-marker request parameter
        """
        self.log.info("STARTED: Test List Object Versions with key-marker request parameter")
        self.log.info("Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Setup versions in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", self.object_name1, 3),
                                             ("Enabled", self.object_name2, 3)])
        for versioning_status in ["Enabled", "Suspended"]:
            versioning_status_log = "Set bucket versioning status to {}".format(versioning_status)
            self.log.info(versioning_status_log)
            res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                             status=versioning_status)
            assert_utils.assert_true(res[0], res[1])
            self.log.info("Step 1: Test List Object Versions with empty key-marker")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"KeyMarker": ""},
                                       expected_versions=versions)
            self.log.info("Step 2: Test List Object Versions with non-existing key as key-marker")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"KeyMarker": "nonexistent"},
                                       expected_versions={})
            self.log.info("Step 3: Test List Object Versions with valid key-marker")
            expected_versions = {self.object_name2: versions[self.object_name2]}
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"KeyMarker": self.object_name2},
                                       expected_versions=expected_versions)
        self.log.info("ENDED: Test List Object Versions with key-marker request parameter")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-34294")
    @CTFailOn(error_handler)
    def test_list_object_versions_max_keys_bucket_34294(self):
        """
        Test List Object Versions with max-keys request parameter
        """
        self.log.info("STARTED: Test List Object Versions with max-keys request parameter")
        self.log.info("Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Setup versions in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", self.object_name1, 1001)])
        for versioning_status in ["Enabled", "Suspended"]:
            versioning_status_log = "Set bucket versioning status to {}".format(versioning_status)
            self.log.info(versioning_status_log)
            res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                             status=versioning_status)
            assert_utils.assert_true(res[0], res[1])
            self.log.info("Step 2: Test List Object Versions with max-keys=0")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"MaxKeys": 0}, expected_versions={})
            self.log.info("Step 3: Test List Object Versions with negative max-keys")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"MaxKeys": -1}, expected_versions={})
            self.log.info("Step 4: Test List Object Versions with default max-keys")
            expected_obj1_versions = copy.deepcopy(versions[self.object_name1])
            version_id = versions[self.object_name1]["version_history"][0]
            expected_obj1_versions["versions"].pop(version_id)
            expected_versions = {self.object_name1: expected_obj1_versions}
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       expected_versions=expected_versions)
            self.log.info("Step 5: Test List Object Versions with default max-keys=1001")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"MaxKeys": 1001}, expected_versions=versions)
        self.log.info("ENDED: Test List Object Versions with  max-keys request parameter")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-34295")
    @CTFailOn(error_handler)
    def test_list_object_versions_prefix_34295(self):
        """
        Test List Object Versions with prefix request parameter
        """
        self.log.info("STARTED: Test List Object Versions with prefix request parameter")
        self.log.info("Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Setup versions in the bucket")
        object_name1 = "key1-name-obj-{}".format(time.perf_counter_ns())
        object_name2 = "key2-name-obj-{}".format(time.perf_counter_ns())
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", object_name1, 3),
                                             ("Enabled", object_name2, 3)])
        for versioning_status in ["Enabled", "Suspended"]:
            versioning_status_log = "Set bucket versioning status to {}".format(versioning_status)
            self.log.info(versioning_status_log)
            res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                             status=versioning_status)
            assert_utils.assert_true(res[0], res[1])
            self.log.info("Step 1: Test List Object Versions with empty prefix")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"Prefix": ""}, expected_versions=versions)
            self.log.info("Step 2: Test List Object Versions with non-existent prefix")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"Prefix": "key3"}, expected_versions={})
            self.log.info("Step 3: Test List Object Versions with valid prefix")
            expected_versions = {object_name2: versions[object_name2]}
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"Prefix": "key2"},
                                       expected_versions=expected_versions)
        self.log.info("ENDED: Test List Object Versions with prefix request parameter")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-34296")
    @CTFailOn(error_handler)
    def test_list_object_versions_version_id_marker_34296(self):
        """
        Test List Object Versions with version-id-marker request parameter
        """
        self.log.info("STARTED: Test List Object Versions with version-id-marker request "
                      "parameter")
        self.log.info("Enable bucket versioning")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Setup versions in the bucket")
        versions = upload_versions(s3_test_obj=self.s3_test_obj,
                                   s3_ver_test_obj=self.s3_ver_test_obj,
                                   bucket_name=self.bucket_name,
                                   file_paths=self.upload_file_paths,
                                   obj_list=[("Enabled", self.object_name1, 3),
                                             ("Enabled", self.object_name2, 3)])
        for versioning_status in ["Enabled", "Suspended"]:
            versioning_status_log = "Set bucket versioning status to {}".format(versioning_status)
            self.log.info(versioning_status_log)
            res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                             status=versioning_status)
            assert_utils.assert_true(res[0], res[1])
            self.log.info("Step 1: Test List Object Versions with empty version-id-marker")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"VersionIdMarker": ""},
                                       expected_versions=versions)
            self.log.info("Step 2: Test List Object Versions with invalid version-id-marker and "
                          "no key-marker")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"VersionIdMarker": "abc"},
                                       expected_versions=versions)
            self.log.info("Step 3: Test List Object Versions with invalid version-id-marker and "
                          "valid key-marker")
            expected_versions = {self.object_name2: versions[self.object_name2]}
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"VersionIdMarker": "abc",
                                                    "KeyMarker": self.object_name1},
                                       expected_versions=expected_versions)
            version_id = versions[self.object_name1]["is_latest"]
            self.log.info("Step 4: Test List Object Versions with valid version-id-marker and no "
                          "key-marker")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"VersionIdMarker": version_id},
                                       expected_versions=versions)
            self.log.info("Step 5: Test List Object Versions with valid version-id-marker and "
                          "non-existent key-marker")
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"KeyMarker": "nonexistent",
                                                    "VersionIdMarker": version_id},
                                       expected_versions={})
            self.log.info("Step 6: Test List Object Versions with valid version-id-marker and "
                          "valid key-marker")
            expected_obj1_versions = copy.deepcopy(versions[self.object_name1])
            expected_obj1_versions["versions"].pop(version_id)
            expected_versions.update({self.object_name1: expected_obj1_versions})
            check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                       list_params={"KeyMarker": self.object_name1,
                                                    "VersionIdMarker": version_id},
                                       expected_versions=expected_versions)
        self.log.info("ENDED: Test List Object Versions with version-id-marker request parameter")
