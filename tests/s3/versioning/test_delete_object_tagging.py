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

"""Test module for DELETE Object Tagging"""

import logging
import os
import time

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils.system_utils import create_file, path_exists, remove_file
from commons.utils.system_utils import make_dirs, remove_dirs
from config.s3 import S3_CFG
from libs.s3.s3_tagging_test_lib import S3TaggingTestLib
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_common_test_lib import put_object_tagging
from libs.s3.s3_versioning_common_test_lib import upload_version
from libs.s3.s3_versioning_common_test_lib import upload_versions
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestTaggingDeleteObject:
    """Test Delete Object Tagging"""

    def setup_method(self):
        """
        Function will be invoked perform setup prior to each test case.
        """
        LOGGER.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_tag_obj = S3TaggingTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestTaggingDeleteObject")
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", self.test_dir_path)
        self.file_path = os.path.join(self.test_dir_path, f"del_obj_tag_{time.perf_counter_ns()}")
        create_file(fpath=self.file_path, count=1)
        LOGGER.info("Created file: %s", self.file_path)
        self.bucket_name = f"tag-bkt-{time.perf_counter_ns()}"
        self.object_name = f"tag-obj-{time.perf_counter_ns()}"
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        LOGGER.info("Created a bucket with name : %s", self.bucket_name)

    def teardown_method(self):
        """
        Function will be perform cleanup after each test case.
        """
        LOGGER.info("STARTED: Teardown operations")
        LOGGER.info("Clean : %s", self.test_dir_path)
        if path_exists(self.file_path):
            res = remove_file(self.file_path)
            LOGGER.info("cleaned path: %s, res: %s", self.file_path, res)
        if path_exists(self.test_dir_path):
            remove_dirs(self.test_dir_path)
        LOGGER.info("Cleanup test directory: %s", self.test_dir_path)
        # DELETE Object with VersionId is WIP, uncomment once feature is available
        # res = self.s3_test_obj.bucket_list()
        # pref_list = []
        # for bucket_name in res[1]:
        #     if bucket_name.startswith("tag-bkt"):
        #         empty_versioned_bucket(self.s3_ver_obj, bucket_name)
        #         pref_list.append(bucket_name)
        # if pref_list:
        #     res = self.s3_test_obj.delete_multiple_buckets(pref_list)
        #     assert_utils.assert_true(res[0], res[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-40435")
    @CTFailOn(error_handler)
    def test_del_obj_tag_40435(self):
        """
        Test DELETE object tagging for pre-existing object in a versioning enabled bucket
        """
        LOGGER.info("STARTED: Test DELETE object tagging for pre-existing object in a versioning "
                    "enabled bucket")
        ver_tag = dict()
        ver_tag.update({self.object_name: dict()})
        versions = dict()
        LOGGER.info("Step 1: Upload object %s before enabling versioning on bucket %s",
                    self.object_name, self.bucket_name)
        upload_version(self.s3_test_obj, bucket_name=self.bucket_name, file_path=self.file_path,
                       object_name=self.object_name, versions_dict=versions, is_unversioned=True)
        last_v = versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 1: Successfully uploaded object %s before enabling versioning on  "
                    "bucket %s with version ID %s", self.object_name, self.bucket_name, last_v)
        LOGGER.info("Step 2: Perform PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 2: Performed PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        put_object_tagging(s3_tag_test_obj=self.s3_tag_obj, s3_ver_test_obj=self.s3_ver_obj,
                           bucket_name=self.bucket_name, object_name=self.object_name,
                           version_tag=ver_tag)
        LOGGER.info("Step 3: Performed PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, last_v)
        put_tag = ver_tag[self.object_name][last_v][-1]
        resp = self.s3_ver_obj.get_obj_tag_ver(bucket_name=self.bucket_name,
                                               object_name=self.object_name, version=last_v)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1]['TagSet'][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 4: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, last_v, get_tag)
        LOGGER.info("Step 5: Perform DELETE Object Tagging for %s with versionId=%s",
                    self.object_name, last_v)
        resp = self.s3_ver_obj.delete_obj_tag_ver(bucket_name=self.bucket_name,
                                                  object_name=self.object_name, version=last_v)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Performed DELETE Object Tagging for %s with versionId=%s",
                    self.object_name, last_v)
        LOGGER.info("Step 6: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, last_v)
        resp = self.s3_ver_obj.get_obj_tag_ver(bucket_name=self.bucket_name,
                                               object_name=self.object_name, version=last_v)
        assert_utils.assert_true(resp[0], resp)
        # For null version ID, expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 6: Performed GET Object Tagging for %s with versionId=%s",
                    self.object_name, last_v)
        LOGGER.info("Step 7: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = self.s3_ver_obj.get_obj_tag_ver(bucket_name=self.bucket_name,
                                               object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        # For null version ID, expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 7: Performed GET Object Tagging for %s without versionId specified",
                    self.object_name)
        LOGGER.info("ENDED: Test DELETE object tagging for pre-existing object in a versioning "
                    "enabled bucket")
