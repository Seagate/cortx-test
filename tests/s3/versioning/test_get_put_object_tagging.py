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

"""Test module for GET PUT Object Tagging with versioning support"""

import logging
import os
import time

import pytest

from commons.error_messages import NO_SUCH_KEY_ERR
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils as sysutils
from config.s3 import S3_CFG
from libs.s3.s3_tagging_test_lib import S3TaggingTestLib
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3 import s3_versioning_common_test_lib as s3_cmn_lib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-statements
# pylint: disable=too-many-instance-attributes
class TestGetPutObjectTagging:
    """Test GET PUT Object Tagging with versioning support"""

    def setup_method(self):
        """
        Function will be invoked perform setup prior to each test case.
        """
        LOGGER.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_tag_obj = S3TaggingTestLib(endpoint_url=S3_CFG["s3_url"])
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestGetPutObjectTagging")
        if not sysutils.path_exists(self.test_dir_path):
            sysutils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", self.test_dir_path)
        self.file_path = os.path.join(self.test_dir_path, f"del_obj_tag_{time.perf_counter_ns()}")
        sysutils.create_file(fpath=self.file_path, count=1)
        LOGGER.info("Created file: %s", self.file_path)
        self.bucket_name = f"tag-bkt-{time.perf_counter_ns()}"
        self.object_name = f"tag-obj-{time.perf_counter_ns()}"
        self.versions = dict()
        self.ver_tag = dict()
        self.ver_tag.update({self.object_name: dict()})
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        LOGGER.info("Created a bucket with name : %s", self.bucket_name)

    def teardown_method(self):
        """
        Function will be performed cleanup after each test case.
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
            if bucket_name.startswith("tag-bkt"):
                s3_cmn_lib.empty_versioned_bucket(self.s3_ver_obj, bucket_name)
                pref_list.append(bucket_name)
        if pref_list:
            res = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(res[0], res[1])

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-40429")
    def test_get_put_obj_tags_40429(self):
        """Test GET and PUT object tagging for pre-existing object in a versioning enabled
        bucket"""

        LOGGER.info("STARTED: Test GET and PUT object tagging for pre-existing object in"
                    " a versioning enabled bucket ")
        LOGGER.info("Step 1: Upload object %s before enabling versioning on bucket %s",
                    self.object_name, self.bucket_name)
        s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                  file_path=self.file_path, object_name=self.object_name,
                                  versions_dict=self.versions, is_unversioned=True)
        LOGGER.info("Step 2: Perform PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        latest_v = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 3: Perform GET Object Tagging for %s with versionId=%s and "
                    "check TagSet as empty", self.object_name, latest_v)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)
        # For null version ID, expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 4: Perform PUT Object Tagging for %s with a tag key-value pair"
                    " with versionId=%s", self.object_name, latest_v)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions,
                                             version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)

        LOGGER.info("Step 5: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        put_tag = self.ver_tag[self.object_name][latest_v][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 6: Perform PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions)
        assert_utils.assert_true(resp[0], resp)
        put_tag = self.ver_tag[self.object_name][latest_v][-1]
        LOGGER.info("Step 7: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 8: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 9: Upload Object %s with version enabled bucket %s",
                    self.object_name, self.bucket_name)
        s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                  file_path=self.file_path, object_name=self.object_name,
                                  versions_dict=self.versions)
        latest_ver_id = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 10: Perform GET Object Tagging for %s with versionId=%s "
                    "and check TagSet is empty", self.object_name, latest_ver_id)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id)
        assert_utils.assert_true(resp[0], resp)
        # For new version ID, expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 11: Perform PUT Object Tagging for %s with a tag key-value pair"
                    " with versionId=%s", self.object_name, latest_ver_id)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions,
                                             version_id=latest_ver_id)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 12: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        put_tag = self.ver_tag[self.object_name][latest_v][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 13: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id)
        put_tag = self.ver_tag[self.object_name][latest_ver_id][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 14: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        put_tag = self.ver_tag[self.object_name][latest_ver_id][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 15: Perform PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 16: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        put_tag = self.ver_tag[self.object_name][latest_v][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 17: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id)
        put_tag = self.ver_tag[self.object_name][latest_ver_id][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 18: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("ENDED: Test GET and PUT object tagging for pre-existing object in"
                    " a versioning enabled bucket ")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-40431")
    def test_get_put_obj_tags_ver_bkt_40431(self):
        """Test GET and PUT object tagging in a versioning enabled bucket"""

        LOGGER.info("STARTED: Test GET and PUT object tagging in a versioning enabled bucket")

        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp)

        LOGGER.info("Step 2: Upload Object %s with version enabled bucket %s",
                    self.object_name, self.bucket_name)
        s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                  file_path=self.file_path, object_name=self.object_name,
                                  versions_dict=self.versions)
        latest_ver_id1 = self.versions[self.object_name]["version_history"][-1]

        LOGGER.info("Step 3: Perform GET Object Tagging for %s with versionId=%s"
                    "and check TagSet is empty", self.object_name, latest_ver_id1)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        # For new version ID, expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)

        LOGGER.info("Step 4: Perform PUT Object Tagging for %s with a tag key-value pair"
                    " with versionId=%s", self.object_name, latest_ver_id1)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)

        LOGGER.info("Step 5: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id1)
        put_tag = self.ver_tag[self.object_name][latest_ver_id1][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")

        LOGGER.info("Step 6: Perform PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions)
        assert_utils.assert_true(resp[0], resp)

        put_tag = self.ver_tag[self.object_name][latest_ver_id1][-1]
        LOGGER.info("Step 7: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id1)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")

        LOGGER.info("Step 8: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")

        LOGGER.info("Step 9: Upload Object %s with version enabled bucket %s",
                    self.object_name, self.bucket_name)
        s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                  file_path=self.file_path, object_name=self.object_name,
                                  versions_dict=self.versions)
        latest_ver_id2 = self.versions[self.object_name]["version_history"][-1]

        LOGGER.info("Step 10: Perform GET Object Tagging for %s with versionId=%s and "
                    "check TagSet is empty", self.object_name, latest_ver_id2)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id2)
        assert_utils.assert_true(resp[0], resp)
        # For new version ID, expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)

        LOGGER.info("Step 11: Perform PUT Object Tagging for %s with a tag key-value pair"
                    " with versionId=%s", self.object_name, latest_ver_id2)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions,
                                             version_id=latest_ver_id2)
        assert_utils.assert_true(resp[0], resp)

        LOGGER.info("Step 12: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id1)
        put_tag = self.ver_tag[self.object_name][latest_ver_id1][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")

        LOGGER.info("Step 13: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id2)
        put_tag = self.ver_tag[self.object_name][latest_ver_id2][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id2)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")

        LOGGER.info("Step 14: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")

        LOGGER.info("Step 15: Perform PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions)
        assert_utils.assert_true(resp[0], resp)

        LOGGER.info("Step 16: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id1)
        put_tag = self.ver_tag[self.object_name][latest_ver_id1][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")

        LOGGER.info("Step 17: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id2)
        put_tag = self.ver_tag[self.object_name][latest_ver_id2][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id2)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")

        LOGGER.info("Step 18: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")

        LOGGER.info("ENDED: Test GET and PUT object tagging in a versioning enabled bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-40432")
    def test_get_put_obj_tags_susp_bkt_40432(self):
        """Test GET and PUT object tagging in a versioning suspended bucket"""

        LOGGER.info("STARTED: Test GET and PUT object tagging in a versioning suspended bucket")
        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 2: Upload Object %s to version enabled bucket %s",
                    self.object_name, self.bucket_name)
        s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                  file_path=self.file_path, object_name=self.object_name,
                                  versions_dict=self.versions)
        latest_ver_id1 = self.versions[self.object_name]["version_history"][-1]
        s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                  file_path=self.file_path, object_name=self.object_name,
                                  versions_dict=self.versions)
        latest_ver_id2 = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 3: Perform PUT Bucket versioning with status as Suspended on %s",
                    self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                     status="Suspended")
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s and versionID=%s"
                    "and check TagSet is empty", self.object_name, latest_ver_id1, latest_ver_id2)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        assert_utils.assert_false(resp[1], resp)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id2)
        assert_utils.assert_true(resp[0], resp)
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 5: Perform PUT Object Tagging for %s with a tag key-value "
                    "pair", self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Perform GET Object Tagging for %s with versionId=%s"
                    "and check TagSet is empty", self.object_name, latest_ver_id1)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 7: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id2)
        put_tag = self.ver_tag[self.object_name][latest_ver_id2][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id2)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 8: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 9: Perform PUT Object Tagging for %s with a tag key-value pair"
                    " with versionId=%s", self.object_name, latest_ver_id1)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 10: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id1)
        put_tag = self.ver_tag[self.object_name][latest_ver_id1][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 11: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id2)
        put_tag = self.ver_tag[self.object_name][latest_ver_id2][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id2)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")

        LOGGER.info("Step 12: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 13: Perform PUT Object for %s", self.object_name)
        s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                  object_name=self.object_name, file_path=self.file_path,
                                  versions_dict=self.versions, chk_null_version=True)
        LOGGER.info("Step 14: Perform PUT Object Tagging for %s with a tag key-value "
                    "pair", self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions)
        assert_utils.assert_true(resp[0], resp)
        latest_v = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 15: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id1)
        put_tag = self.ver_tag[self.object_name][latest_ver_id1][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 16: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id2)
        put_tag = self.ver_tag[self.object_name][latest_ver_id2][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id2)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 17: Perform GET Object Tagging for %s with versionId=null",
                    self.object_name)
        put_tag = self.ver_tag[self.object_name][latest_v][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_id="null")
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 18: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("ENDED: Test GET and PUT object tagging in a versioning suspended bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-40433")
    def test_get_put_obj_tags_del_bkt_40433(self):
        """Test GET and PUT object tagging for deleted versioned object"""

        LOGGER.info("STARTED: Test GET and PUT object tagging for deleted versioned object")
        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 2: Upload Object %s with version enabled bucket %s",
                    self.object_name, self.bucket_name)
        s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                  file_path=self.file_path, object_name=self.object_name,
                                  versions_dict=self.versions)
        latest_ver_id = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id)
        put_tag = self.ver_tag[self.object_name][latest_ver_id][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 5: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")

        LOGGER.info("Step 6: Perform Delete Object %s and create deletemarkerid", self.object_name)
        s3_cmn_lib.delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_obj,
                                  bucket_name=self.bucket_name, object_name=self.object_name,
                                  versions_dict=self.versions, check_deletemarker=True)
        dm_id = self.versions[self.object_name]["delete_markers"][0]
        LOGGER.info("Step 7: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 8: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(NO_SUCH_KEY_ERR, resp[1].message)
        LOGGER.info("Step 9: Perform GET Object Tagging for %s with deletemarkerid=%s",
                    self.object_name, dm_id)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=dm_id)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(NO_SUCH_KEY_ERR, resp[1].message)
        LOGGER.info("Step 10: Perform PUT Object Tagging for %s with a tag key-value pair"
                    " with versionId=%s", self.object_name, latest_ver_id)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions,
                                             version_id=latest_ver_id)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 11: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id)
        put_tag = self.ver_tag[self.object_name][latest_ver_id][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 12: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(NO_SUCH_KEY_ERR, resp[1].message)
        LOGGER.info("Step 13: Perform GET Object Tagging for %s with deletemarkerid=%s",
                    self.object_name, dm_id)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=dm_id)
        assert_utils.assert_true(resp[0], resp)
        assert_utils.assert_in(NO_SUCH_KEY_ERR, resp[1].message)
        LOGGER.info("Step 14: Perform PUT Object Tagging for %s with a tag key-value pair"
                    " with deletemarkerid=%s", self.object_name, dm_id)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions,
                                             version_id=dm_id)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(NO_SUCH_KEY_ERR, resp[1].message)
        LOGGER.info("ENDED: Test GET and PUT object tagging for deleted versioned object")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-40434")
    def test_get_put_obj_tags_no_ver_40434(self):
        """Test GET and PUT object tagging for non-existing version or object"""

        LOGGER.info("STARTED: Test GET and PUT object tagging for non-existing version or object")
        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 2: Upload Object %s with version enabled bucket %s",
                    self.object_name, self.bucket_name)
        s3_cmn_lib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                  file_path=self.file_path, object_name=self.object_name,
                                  versions_dict=self.versions)
        latest_ver_id1 = self.versions[self.object_name]["version_history"][-1]
        non_existing_version_id = "Vr1" * 9  # non-existing opaque strings' version id of length 27
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with a tag key-value pair"
                    " with versionId=%s", self.object_name, latest_ver_id1)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name, version_tag=self.ver_tag,
                                             versions_dict=self.versions, version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_ver_id1)
        put_tag = self.ver_tag[self.object_name][latest_ver_id1][-1]
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=latest_ver_id1)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 5: Perform PUT Object Tagging for %s with a tag key-value pair"
                    " with non-existing versionId=%s", self.object_name, non_existing_version_id)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_tag=self.ver_tag, versions_dict=self.versions,
                                             version_id=non_existing_version_id)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(NO_SUCH_KEY_ERR, resp[1].message)
        LOGGER.info("Step 6: Perform GET Object Tagging for %s with  non-existing versionId=%s",
                    self.object_name, non_existing_version_id)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=self.object_name,
                                             version_id=non_existing_version_id)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(NO_SUCH_KEY_ERR, resp[1].message)

        object_name_new = f"tag-obj-{time.perf_counter_ns()}"
        LOGGER.info("Step 7: Perform PUT Object Tagging for non-existing %s with a tag key-value"
                    " pair with versionId=%s", object_name_new, latest_ver_id1)
        resp = s3_cmn_lib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=object_name_new,
                                             version_tag=self.ver_tag, versions_dict=self.versions,
                                             version_id=latest_ver_id1)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(NO_SUCH_KEY_ERR, resp[1].message)

        LOGGER.info("Step 8: Perform GET Object Tagging for non-existing %s with versionId=%s",
                    object_name_new, latest_ver_id1)
        resp = s3_cmn_lib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                             s3_ver_test_obj=self.s3_ver_obj,
                                             bucket_name=self.bucket_name,
                                             object_name=object_name_new,
                                             version_id=latest_ver_id1)
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(NO_SUCH_KEY_ERR, resp[1].message)

        LOGGER.info("ENDED: Test GET and PUT object tagging for non-existing version or object")
