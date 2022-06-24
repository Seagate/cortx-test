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

"""Test module for Limits for Object Tagging with versioning support"""

import logging
import os
import time

import pytest

from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils as sysutils
from commons import error_messages as err_msg
from config.s3 import S3_CFG
from libs.s3.s3_tagging_test_lib import S3TaggingTestLib
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3 import s3_versioning_common_test_lib as s3_cmn_lib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class TestObjectTaggingVerLimits:
    """Test Limits tests for Object Tagging with versioning support"""

    def setup_method(self):
        """
        Function will be invoked perform setup prior to each test case.
        """
        LOGGER.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_tag_obj = S3TaggingTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestTaggingVerLimitsObject")
        if not sysutils.path_exists(self.test_dir_path):
            sysutils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", self.test_dir_path)
        self.file_path = os.path.join(self.test_dir_path, f"limit_obj_tag_{time.perf_counter_ns()}")
        sysutils.create_file(fpath=self.file_path, count=1)
        LOGGER.info("Created file: %s", self.file_path)
        self.bucket_name = f"tag-ver-bkt-{time.perf_counter_ns()}"
        self.object_name = f"tag-ver-obj-{time.perf_counter_ns()}"
        self.versions = dict()
        self.ver_tag = dict()
        self.ver_tag.update({self.object_name: dict()})
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
        if sysutils.path_exists(self.file_path):
            res = sysutils.remove_file(self.file_path)
            LOGGER.info("cleaned path: %s, res: %s", self.file_path, res)
        if sysutils.path_exists(self.test_dir_path):
            sysutils.remove_dirs(self.test_dir_path)
        LOGGER.info("Cleanup test directory: %s", self.test_dir_path)
        res = self.s3_test_obj.bucket_list()
        pref_list = []
        for bucket_name in res[1]:
            if bucket_name.startswith("tag-ver-bkt"):
                s3_cmn_lib.empty_versioned_bucket(self.s3_ver_obj, bucket_name)
                pref_list.append(bucket_name)
        if pref_list:
            res = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(res[0], res[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41277")
    @pytest.mark.parametrize("versioning_status", ["Enabled", "Suspended"])
    def test_tag_key_limit_41277(self, versioning_status):
        """
        Test maximum key length of a tag for a versioned object - 128 Unicode characters
        """
        LOGGER.info("Started: Test maximum key length of a tag for a versioned object - 128 "
                    "Unicode characters")
        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                     status=versioning_status)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 1: Performed PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        LOGGER.info("Step 2: Upload object %s with version %s bucket %s", self.object_name,
                    versioning_status, self.bucket_name)
        if versioning_status == "Suspended":
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions, chk_null_version=True)
        else:
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions)
        latest_ver = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 2: Successfully uploaded object %s to versioned bucket %s with "
                    "version ID %s", self.object_name, self.bucket_name, latest_ver)
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with 128 char tag key",
                    self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_tag=self.ver_tag,
                                             versions_dict=self.versions, tag_key_ran=[(128, 128)])
        assert_utils.assert_true(resp[0], resp)
        put_tag = self.ver_tag[self.object_name][latest_ver][-1]
        LOGGER.info("Step 3: Performed PUT Object Tagging for %s with 128 char tag key",
                    self.object_name)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 4: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_ver, get_tag)
        LOGGER.info("Step 5: Perform PUT Object Tagging for %s with 129 char tag key",
                    self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_tag=self.ver_tag,
                                             versions_dict=self.versions, tag_key_ran=[(129, 129)],
                                             version_id=latest_ver)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(err_msg.S3_RGW_BKT_INVALID_TAG_ERR, resp[1].message)
        LOGGER.info("Step 5: PUT Object Tagging for %s with 129 char tag key failed as expected",
                    self.object_name)
        LOGGER.info("Step 6: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        get_tag1 = resp[1][0]
        assert_utils.assert_equal(get_tag1, put_tag, "Mismatch in tag Key-Value pair."
                                                     f"Expected: {put_tag} \n Actual: {get_tag1}")
        LOGGER.info("Step 6: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_ver, get_tag1)
        LOGGER.info("Completed: Test maximum key length of a tag for a versioned object - 128 "
                    "Unicode characters")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41278")
    @pytest.mark.parametrize("versioning_status", ["Enabled", "Suspended"])
    def test_tag_key_min_41278(self, versioning_status):
        """
        Test minimum key length of a tag for a versioned object - 1 character
        """
        LOGGER.info("Started: Test minimum key length of a tag for a versioned object - "
                    "1 character")
        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                     status=versioning_status)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 1: Performed PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        LOGGER.info("Step 2: Upload object %s with version %s bucket %s", self.object_name,
                    versioning_status, self.bucket_name)
        if versioning_status == "Suspended":
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions, chk_null_version=True)
        else:
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions)
        latest_ver = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 2: Successfully uploaded object %s to versioned bucket %s with "
                    "version ID %s", self.object_name, self.bucket_name, latest_ver)
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with 1 char tag key",
                    self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_tag=self.ver_tag,
                                             versions_dict=self.versions, tag_key_ran=[(1, 1)],
                                             version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        put_tag = self.ver_tag[self.object_name][latest_ver][-1]
        LOGGER.info("Step 3: Performed PUT Object Tagging for %s with 1 char tag key",
                    self.object_name)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 4: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_ver, get_tag)
        LOGGER.info("Completed: Test minimum key length of a tag for a versioned object - "
                    "1 character")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41279")
    @pytest.mark.parametrize("versioning_status", ["Enabled", "Suspended"])
    def test_tag_value_limit_41279(self, versioning_status):
        """
        Test maximum value length of a tag for a versioned object - 256 Unicode characters
        """
        LOGGER.info("Started: Test maximum value length of a tag for a versioned object - "
                    "256 Unicode characters")
        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                     status=versioning_status)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 1: Performed PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        LOGGER.info("Step 2: Upload object %s with version %s bucket %s", self.object_name,
                    versioning_status, self.bucket_name)
        if versioning_status == "Suspended":
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions, chk_null_version=True)
        else:
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions)
        latest_ver = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 2: Successfully uploaded object %s to versioned bucket %s with "
                    "version ID %s", self.object_name, self.bucket_name, latest_ver)
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with 256 char tag value",
                    self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_tag=self.ver_tag,
                                             versions_dict=self.versions, tag_val_ran=[(256, 256)],
                                             version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        put_tag = self.ver_tag[self.object_name][latest_ver][-1]
        LOGGER.info("Step 3: Performed PUT Object Tagging for %s with 256 char tag value",
                    self.object_name)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 4: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_ver, get_tag)
        LOGGER.info("Step 5: Perform PUT Object Tagging for %s with 257 char tag value",
                    self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_tag=self.ver_tag,
                                             versions_dict=self.versions, tag_val_ran=[(257, 257)],
                                             version_id=latest_ver)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(err_msg.S3_RGW_BKT_INVALID_TAG_ERR, resp[1].message)
        LOGGER.info("Step 5: PUT Object Tagging for %s with 257 char tag value failed as expected",
                    self.object_name)
        LOGGER.info("Step 6: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        get_tag1 = resp[1][0]
        assert_utils.assert_equal(get_tag1, put_tag, "Mismatch in tag Key-Value pair."
                                                     f"Expected: {put_tag} \n Actual: {get_tag1}")
        LOGGER.info("Step 6: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_ver, get_tag1)
        LOGGER.info("Completed: Test maximum value length of a tag for a versioned object - "
                    "256 Unicode characters")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41281")
    @pytest.mark.parametrize("versioning_status", ["Enabled", "Suspended"])
    def test_tag_count_limit_41281(self, versioning_status):
        """
        Test maximum tags for a versioned object
        """
        LOGGER.info("Started: Test maximum tags for a versioned object")
        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                     status=versioning_status)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 1: Performed PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        LOGGER.info("Step 2: Upload object %s with version %s bucket %s", self.object_name,
                    versioning_status, self.bucket_name)
        if versioning_status == "Suspended":
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions, chk_null_version=True)
        else:
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions)
        latest_ver = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 2: Successfully uploaded object %s to versioned bucket %s with "
                    "version ID %s", self.object_name, self.bucket_name, latest_ver)
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with 10 tag key-value pairs",
                    self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_tag=self.ver_tag,
                                             versions_dict=self.versions, tag_count=10,
                                             version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        put_tag = self.ver_tag[self.object_name][latest_ver]
        LOGGER.info("Step 3: Performed PUT Object Tagging for %s with 10 tag key-value pairs",
                    self.object_name)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1]
        get_tag = sorted(get_tag, key=lambda item: item['Key'])
        put_tag = sorted(put_tag, key=lambda item: item['Key'])
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 4: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_ver, get_tag)
        LOGGER.info("Step 5: Perform PUT Object Tagging for %s with more than 10 tag key-value "
                    "pairs", self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_tag=self.ver_tag,
                                             versions_dict=self.versions, tag_count=11,
                                             version_id=latest_ver)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(err_msg.S3_RGW_BKT_INVALID_TAG_ERR, resp[1].message)
        LOGGER.info("Step 5: PUT Object Tagging for %s with more than 10 tag key-value pairs "
                    "failed as expected", self.object_name)
        LOGGER.info("Step 6: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        get_tag1 = resp[1]
        assert_utils.assert_equal(get_tag1, put_tag, "Mismatch in tag Key-Value pair."
                                                     f"Expected: {put_tag} \n Actual: {get_tag1}")
        LOGGER.info("Step 6: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_ver, get_tag1)
        LOGGER.info("Completed: Test maximum tags for a versioned object")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41282")
    @pytest.mark.parametrize("versioning_status", ["Enabled", "Suspended"])
    def test_tag_case_sensitive_41282(self, versioning_status):
        """
        Test case sensitivity of tag key-value for a versioned object
        """
        LOGGER.info("Started: Test case sensitivity of tag key-value for a versioned object")
        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                     status=versioning_status)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 1: Performed PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        LOGGER.info("Step 2: Upload object %s with version %s bucket %s", self.object_name,
                    versioning_status, self.bucket_name)
        if versioning_status == "Suspended":
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions, chk_null_version=True)
        else:
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions)
        latest_ver = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 2: Successfully uploaded object %s to versioned bucket %s with "
                    "version ID %s", self.object_name, self.bucket_name, latest_ver)
        tag_or = [{ "Key": "Tag1Key", "Value": "Tag1Value" },
                  { "Key": "tag1key", "Value": "tag1value" }]
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with tag set as %s",
                    self.object_name, tag_or)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_tag=self.ver_tag,
                                             versions_dict=self.versions, tag_overrides=tag_or,
                                             version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        put_tag = self.ver_tag[self.object_name][latest_ver]
        LOGGER.info("Step 3: Performed PUT Object Tagging for %s with tag set as %s",
                    self.object_name, tag_or)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1]
        for pair in put_tag:
            assert_utils.assert_in(pair, get_tag, "Mismatch in tag Key-Value pair."
                                                  f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 4: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_ver, get_tag)
        LOGGER.info("Completed: Test case sensitivity of tag key-value for a versioned object")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41283")
    @pytest.mark.parametrize("versioning_status", ["Enabled", "Suspended"])
    def test_tag_key_spl_char_41283(self, versioning_status):
        """
        Test allowed special characters in tag key for a versioned object
        """
        LOGGER.info("Started: Test allowed special characters in tag key for a versioned object")
        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                     status=versioning_status)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 1: Performed PUT Bucket versioning with status as %s on %s",
                    versioning_status, self.bucket_name)
        LOGGER.info("Step 2: Upload object %s with version %s bucket %s", self.object_name,
                    versioning_status, self.bucket_name)
        if versioning_status == "Suspended":
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions, chk_null_version=True)
        else:
            s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                      object_name=self.object_name, file_path=self.file_path,
                                      versions_dict=self.versions)
        latest_ver = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 2: Successfully uploaded object %s to versioned bucket %s with "
                    "version ID %s", self.object_name, self.bucket_name, latest_ver)
        tag_or = list()
        for char in S3_CFG["object_tagging_special_char"]:
            tag_key = f"tag{char}key"
            tag_or.append({"Key": tag_key, "Value": "tag1value"})
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with tag set as %s with tag key "
                    "containing allowed special characters", self.object_name, tag_or)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_tag=self.ver_tag,
                                             versions_dict=self.versions, tag_overrides=tag_or,
                                             version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        put_tag = self.ver_tag[self.object_name][latest_ver]
        LOGGER.info("Step 3: Performed PUT Object Tagging for %s with tag set as %s with tag key "
                    "containing allowed special characters", self.object_name, tag_or)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1]
        for pair in put_tag:
            assert_utils.assert_in(pair, get_tag, "Mismatch in tag Key-Value pair."
                                                  f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 4: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_ver, get_tag)
        tag_or = [{"Key": "tag*key", "Value": "tag1value"},
                  {"Key": "tag,key", "Value": "tag1value"}]
        LOGGER.info("Step 5: Perform PUT Object Tagging for %s with tag set as %s with tag key "
                    "containing other than allowed special characters", self.object_name, tag_or)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_tag=self.ver_tag,
                                             versions_dict=self.versions, tag_overrides=tag_or,
                                             version_id=latest_ver)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(err_msg.S3_RGW_BKT_INVALID_TAG_ERR, resp[1].message)
        LOGGER.info("Step 5: PUT Object Tagging for %s with tag set as %s with tag key containing "
                    "other than allowed special characters failed as expected", self.object_name,
                    tag_or)
        LOGGER.info("Step 6: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_ver)
        assert_utils.assert_true(resp[0], resp)
        get_tag1 = resp[1]
        for pair in put_tag:
            assert_utils.assert_in(pair, get_tag1, "Mismatch in tag Key-Value pair."
                                                  f"Expected: {put_tag} \n Actual: {get_tag1}")
        LOGGER.info("Step 6: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_ver, get_tag)
        LOGGER.info("Completed: Test allowed special characters in tag key for a versioned object")
