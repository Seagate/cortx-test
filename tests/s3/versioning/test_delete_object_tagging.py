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
import random
import pytest

from commons.ct_fail_on import CTFailOn
from commons.error_messages import NO_SUCH_KEY_ERR
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils as sysutils
from config.s3 import S3_CFG
from libs.s3 import s3_versioning_common_test_lib as s3_ver_tlib
from libs.s3.s3_tagging_test_lib import S3TaggingTestLib
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib

# Global Constants
LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
# pylint: disable=attribute-defined-outside-init

class TestTaggingDeleteObject:
    """Test Delete Object Tagging"""

    def setup_method(self):
        """Function will be invoked perform setup prior to each test case."""
        LOGGER.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_tag_obj = S3TaggingTestLib(endpoint_url=S3_CFG["s3_url"])
        self.ver_tag = {}
        self.versions = {}
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestTaggingDeleteObject")
        if not sysutils.path_exists(self.test_dir_path):
            sysutils.make_dirs(self.test_dir_path)
            LOGGER.info("Created path: %s", self.test_dir_path)
        self.file_path1 = os.path.join(self.test_dir_path, f"del_obj_tag_{time.perf_counter_ns()}")
        self.file_path2 = os.path.join(self.test_dir_path, f"del_obj_tag_{time.perf_counter_ns()}")
        self.file_path3 = os.path.join(self.test_dir_path, f"del_obj_tag_{time.perf_counter_ns()}")
        download_file = f"tag_download{time.perf_counter_ns()}"
        self.download_path = os.path.join(self.test_dir_path, download_file)
        self.upload_file_paths = [self.file_path1, self.file_path2, self.file_path3]
        for file_path in self.upload_file_paths:
            sysutils.create_file(file_path, 1, "/dev/urandom")
            LOGGER.info("Created file: %s", file_path)
        self.bucket_name = f"tag-bkt-{time.perf_counter_ns()}"
        self.object_name = f"tag-obj-{time.perf_counter_ns()}"
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        LOGGER.info("Created a bucket with name : %s", self.bucket_name)
        LOGGER.info("ENDED: Setup operations")

    def teardown_method(self):
        """Function will be performed cleanup after each test case."""
        LOGGER.info("STARTED: Teardown operations")
        LOGGER.info("CleanUP : %s", self.test_dir_path)
        for file_path in (self.file_path1, self.file_path2, self.file_path3, self.download_path):
            if sysutils.path_exists(file_path):
                res = sysutils.remove_file(file_path)
                LOGGER.info("cleaned path: %s, res: %s", file_path, res)
        if sysutils.path_exists(self.test_dir_path):
            sysutils.remove_dirs(self.test_dir_path)
        LOGGER.info("Cleanup test directory: %s", self.test_dir_path)
        res = self.s3_test_obj.bucket_list()
        pref_list = []
        for bucket_name in res[1]:
            if bucket_name.startswith("tag-bkt"):
                s3_ver_tlib.empty_versioned_bucket(self.s3_ver_obj, bucket_name)
                pref_list.append(bucket_name)
        if pref_list:
            res = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("ENDED: Teardown operations")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-40435")
    @CTFailOn(error_handler)
    def test_del_obj_tag_40435(self):
        """Test DELETE object tagging for pre-existing object in a versioning enabled bucket."""
        LOGGER.info("STARTED: Test DELETE object tagging for pre-existing object in a versioning "
                    "enabled bucket")
        self.ver_tag.update({self.object_name: {}})
        LOGGER.info("Step 1: Upload object %s before enabling versioning on bucket %s",
                    self.object_name, self.bucket_name)
        s3_ver_tlib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                   file_path=self.file_path1, object_name=self.object_name,
                                   versions_dict=self.versions, is_unversioned=True)
        latest_v = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 1: Successfully uploaded object %s before enabling versioning on  "
                    "bucket %s with version ID %s", self.object_name, self.bucket_name, latest_v)
        LOGGER.info("Step 2: Perform PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 2: Performed PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        resp = s3_ver_tlib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name,
                                              version_tag=self.ver_tag, versions_dict=self.versions)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Performed PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        put_tag = self.ver_tag[self.object_name][latest_v][-1]
        resp = s3_ver_tlib.get_object_tagging(bucket_name=self.bucket_name,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              s3_tag_test_obj=self.s3_tag_obj,
                                              object_name=self.object_name, version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 4: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_v, get_tag)
        LOGGER.info("Step 5: Perform DELETE Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        resp = s3_ver_tlib.delete_object_tagging(bucket_name=self.bucket_name,
                                                 s3_ver_test_obj=self.s3_ver_obj,
                                                 s3_tag_test_obj=self.s3_tag_obj,
                                                 object_name=self.object_name, version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 5: Performed DELETE Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        LOGGER.info("Step 6: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name, version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)
        # For null version ID, expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 6: Performed GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        LOGGER.info("Step 7: Perform GET Object Tagging for %s without versionId specified",
                    self.object_name)
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        # For null version ID, expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 7: Performed GET Object Tagging for %s without versionId specified",
                    self.object_name)
        LOGGER.info("ENDED: Test DELETE object tagging for pre-existing object in a versioning "
                    "enabled bucket")

    # pylint:disable-msg=too-many-statements
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-40436")
    @CTFailOn(error_handler)
    def test_del_obj_tag_40436(self):
        """Test DELETE object tagging in a versioning enabled bucket."""
        LOGGER.info("STARTED: Test DELETE object tagging in a versioning enabled bucket")
        LOGGER.info("Step 1: PUT Bucket versioning with status as Enabled")
        res = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Step 2: Upload 2 versions of object - %s ", self.object_name)
        self.versions = s3_ver_tlib.upload_versions(s3_test_obj=self.s3_test_obj,
                                                    s3_ver_test_obj=self.s3_ver_obj,
                                                    bucket_name=self.bucket_name,
                                                    file_paths=self.upload_file_paths,
                                                    obj_list=[("Enabled", self.object_name, 2)])
        ver_list = list(self.versions[self.object_name]["versions"].keys())
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with a tag key-value pair for "
                    "versionIds %s", self.object_name, ver_list)
        self.ver_tag.update({self.object_name: {}})
        for v_id in ver_list:
            resp = s3_ver_tlib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj, version_id=v_id,
                                                  s3_ver_test_obj=self.s3_ver_obj,
                                                  version_tag=self.ver_tag,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name)
            assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 4: GET Object Tagging for %s with versionId=%s", self.object_name,
                    ver_list)
        for v_id in ver_list:
            LOGGER.info("GET Object Tagging for %s with versionId=%s", self.object_name, v_id)
            resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                                  s3_ver_test_obj=self.s3_ver_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  version_id=v_id)
            assert_utils.assert_true(resp[0], resp)
            get_tag = resp[1]
            put_tag = self.ver_tag[self.object_name][v_id]
            assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                        f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 5: GET Object Tagging for %s (without versionId specified)",
                    self.object_name)
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1]
        latest = self.versions[self.object_name]["version_history"][-1]  # Get the latest Version ID
        put_tag = self.ver_tag[self.object_name][latest]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 6: DELETE Object Tagging for %s", self.object_name)
        resp = s3_ver_tlib.delete_object_tagging(bucket_name=self.bucket_name,
                                                 s3_ver_test_obj=self.s3_ver_obj,
                                                 s3_tag_test_obj=self.s3_tag_obj,
                                                 object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 7: GET Object Tagging for %s with versionId=%s", self.object_name,
                    ver_list[0])
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name,
                                              version_id=ver_list[0])
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1]
        put_tag = self.ver_tag[self.object_name][f"{ver_list[0]}"]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 8: GET Object Tagging for %s with versionId=%s", self.object_name,
                    ver_list[1])
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name,
                                              version_id=ver_list[1])
        assert_utils.assert_true(resp[0], resp)
        # expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 9: GET Object Tagging for %s (without versionId specified)",
                    self.object_name)
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        # expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 10: DELETE Object Tagging for %s with versionId=%s", self.object_name,
                    ver_list[0])
        resp = s3_ver_tlib.delete_object_tagging(bucket_name=self.bucket_name,
                                                 s3_ver_test_obj=self.s3_ver_obj,
                                                 s3_tag_test_obj=self.s3_tag_obj,
                                                 object_name=self.object_name,
                                                 version_id=ver_list[0])
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 11: GET Object Tagging for %s with versionId=%s", self.object_name,
                    ver_list)
        for v_id in ver_list:
            LOGGER.info("GET Object Tagging for %s with versionId=%s", self.object_name, v_id)
            resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                                  s3_ver_test_obj=self.s3_ver_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name,
                                                  version_id=v_id)
            assert_utils.assert_true(resp[0], resp)
            # expecting "TagSet": []
            assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 12: GET Object Tagging for %s (without versionId specified)",
                    self.object_name)
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        # expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 13: Perform PUT Object Tagging for %s with a tag key-value pair for "
                    "versionId=%s", self.object_name, ver_list[1])
        resp = s3_ver_tlib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              version_id=ver_list[1],
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              version_tag=self.ver_tag,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 14: GET Object Tagging for %s with versionId=%s", self.object_name,
                    ver_list[0])
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name,
                                              version_id=ver_list[0])
        assert_utils.assert_true(resp[0], resp)
        # expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 15: GET Object Tagging for %s with versionId=%s", self.object_name,
                    ver_list[1])
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name,
                                              version_id=ver_list[1])
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1]
        put_tag = self.ver_tag[self.object_name][f"{ver_list[1]}"]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 16: GET Object Tagging for %s (without versionId specified)",
                    self.object_name)
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1]
        latest = self.versions[self.object_name]["version_history"][-1]  # Get the latest Version ID
        put_tag = self.ver_tag[self.object_name][latest]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("ENDED: Test DELETE object tagging in a versioning enabled bucket.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-40437")
    def test_del_obj_tag_40437(self):
        """
        Test DELETE object tagging in a versioning suspended  bucket
        """
        LOGGER.info("STARTED: Test DELETE object tagging in a versioning suspended bucket")
        LOGGER.info("STEP 1: Bucket %s Created", self.bucket_name)
        LOGGER.info("Step 2: PUT Bucket versioning with status as Enabled")
        res = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Step 3: Upload (creates version with versionId) of object - %s ",
                    self.object_name)
        s3_ver_tlib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                   file_path=self.file_path1, object_name=self.object_name,
                                   versions_dict=self.versions)
        versionid1 = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 4: Perform PUT Bucket versioning with status as Suspended")
        res = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                    status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Step 5 Perform PUT Object for object1 (creates version with null versionId)")
        s3_ver_tlib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                   file_path=self.file_path2, object_name=self.object_name,
                                   versions_dict=self.versions, chk_null_version=True)
        ver_list = self.versions[self.object_name]["version_history"]  # [versionid1, "null"]
        LOGGER.info("Step 6: Perform PUT Object Tagging for object1 with a tag key-value pair for "
                    "versionIds %s ", ver_list)
        self.ver_tag.update({self.object_name: {}})
        for v_id in ver_list:
            LOGGER.info("PUT Object Tagging for %s with versionId=%s", self.object_name, v_id)
            resp = s3_ver_tlib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                                  version_id=v_id,  s3_ver_test_obj=self.s3_ver_obj,
                                                  version_tag=self.ver_tag,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name)
            assert_utils.assert_true(resp[0], resp)
        LOGGER.info(
            "Step 7: GET Object Tagging for %s with versionIds=%s", self.object_name, ver_list)
        for v_id in ver_list:
            resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                                  s3_ver_test_obj=self.s3_ver_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name, version_id=v_id)
            assert_utils.assert_true(resp[0], resp)
            get_tag = resp[1]
            put_tag = self.ver_tag[self.object_name][v_id]
            assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                        f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 8: Done GET Object Tagging for %s with versionIds=%s",
                    self.object_name, ver_list)
        LOGGER.info(
            "Step 9: GET Object Tagging for %s (without versionId specified)",
            self.object_name)
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1]
        latest = self.versions[self.object_name]["version_history"][-1]
        put_tag = self.ver_tag[self.object_name][latest]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 10: DELETE Object Tagging for %s with versionId=%s", self.object_name,
                    versionid1)
        resp = s3_ver_tlib.delete_object_tagging(bucket_name=self.bucket_name,
                                                 s3_ver_test_obj=self.s3_ver_obj,
                                                 s3_tag_test_obj=self.s3_tag_obj,
                                                 object_name=self.object_name,
                                                 version_id=versionid1)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 11: GET Object Tagging for %s with versionIds=%s", self.object_name,
                    versionid1)
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name, version_id=versionid1)
        assert_utils.assert_true(resp[0], resp)
        # expecting "TagSet": []
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 12: GET Object Tagging for %s with versionIds=%s", self.object_name,
                    "null")
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name, version_id="null")
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1]
        put_tag = self.ver_tag[self.object_name]["null"]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 13 GET Object Tagging for %s (without versionId specified)",
                    self.object_name)
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1]
        latest = self.versions[self.object_name]["version_history"][-1]
        put_tag = self.ver_tag[self.object_name][latest]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 14: DELETE Object Tagging for %s with versionId=null", self.object_name)
        resp = s3_ver_tlib.delete_object_tagging(bucket_name=self.bucket_name,
                                                 s3_ver_test_obj=self.s3_ver_obj,
                                                 s3_tag_test_obj=self.s3_tag_obj,
                                                 object_name=self.object_name, version_id="null")
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 15-16: GET Object Tagging for %s with versionId=%s", self.object_name,
                    ver_list)
        for v_id in ver_list:
            resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                                  s3_ver_test_obj=self.s3_ver_obj,
                                                  bucket_name=self.bucket_name,
                                                  object_name=self.object_name, version_id=v_id)
            assert_utils.assert_true(resp[0], resp)
            assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 17: GET Object Tagging for %s (without versionId specified)",
                    self.object_name)
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp)
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("ENDED: Test DELETE object tagging in a versioning suspended bucket.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-40438")
    def test_del_obj_tag_40438(self):
        """Test DELETE object tagging for a deleted versioned object."""
        LOGGER.info("STARTED: Test DELETE object tagging for a deleted versioned object")
        self.ver_tag.update({self.object_name: {}})
        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 1: Performed PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        LOGGER.info("Step 2: Upload object %s on bucket %s", self.object_name, self.bucket_name)
        s3_ver_tlib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                   file_path=self.file_path1, object_name=self.object_name,
                                   versions_dict=self.versions)
        latest_v = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 2: Successfully uploaded object %s on  "
                    "bucket %s with version ID %s", self.object_name, self.bucket_name, latest_v)
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        resp = s3_ver_tlib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name,
                                              version_tag=self.ver_tag, versions_dict=self.versions)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Performed PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        put_tag = self.ver_tag[self.object_name][latest_v][-1]
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name, version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 4: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_v, get_tag)
        LOGGER.info("Step 5: Perform DELETE Object %s to creates delete marker(versionId)",
                    self.object_name)
        s3_ver_tlib.delete_version(s3_test_obj=self.s3_test_obj, s3_ver_test_obj=self.s3_ver_obj,
                                   bucket_name=self.bucket_name, object_name=self.object_name,
                                   versions_dict=self.versions, check_deletemarker=True)
        dm_id = self.versions[self.object_name]["delete_markers"][0]
        assert_utils.assert_in("No Content", resp[1].message)
        LOGGER.info("Step 5: Performed DELETE Object  %s and created versionId(delete market id)="
                    "%s", self.object_name, str(dm_id))
        LOGGER.info("Step 6: Perform DELETE Object tagging  %s with versionId %s",
                    self.object_name, latest_v)
        resp = s3_ver_tlib.delete_object_tagging(bucket_name=self.bucket_name,
                                                 s3_ver_test_obj=self.s3_ver_obj,
                                                 s3_tag_test_obj=self.s3_tag_obj,
                                                 object_name=self.object_name, version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 6: Performed DELETE Object tagging %s with versionId %s",
                    self.object_name, latest_v)
        LOGGER.info("Step 7: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        resp = s3_ver_tlib.get_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name, version_id=latest_v)
        assert_utils.assert_false(resp[0], resp)
        LOGGER.info("Step 7: Performed GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        LOGGER.info("Step 8: Perform Delete Object Tagging for %s with "
                    "delete marker id(versionId) specified %s", self.object_name, str(dm_id))
        resp = s3_ver_tlib.delete_object_tagging(bucket_name=self.bucket_name,
                                                 s3_ver_test_obj=self.s3_ver_obj,
                                                 s3_tag_test_obj=self.s3_tag_obj,
                                                 object_name=self.object_name, version_id=dm_id)
        assert_utils.assert_true(resp[0], resp)
        assert_utils.assert_false(resp[1], resp)
        LOGGER.info("Step 8: Performed Delete Object Tagging for %s "
                    "with delete marker(versionId) specified %s", self.object_name, str(dm_id))
        LOGGER.info("ENDED:Test DELETE object tagging for a deleted versioned object")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-40439")
    @CTFailOn(error_handler)
    def test_del_obj_tag_40439(self):
        """
        Test DELETE object tagging for non-existing version or object.
        """
        LOGGER.info(
            "Test DELETE object tagging for non-existing version or object.")
        self.ver_tag.update({self.object_name: {}})
        LOGGER.info("Step 1: Perform PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        resp = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 1: Performed PUT Bucket versioning with status as Enabled on %s",
                    self.bucket_name)
        LOGGER.info("Step 2: Upload object %s to create version on bucket %s",
                    self.object_name, self.bucket_name)
        s3_ver_tlib.upload_version(self.s3_test_obj, bucket_name=self.bucket_name,
                                   file_path=self.file_path1, object_name=self.object_name,
                                   versions_dict=self.versions)
        latest_v = self.versions[self.object_name]["version_history"][-1]
        LOGGER.info("Step 2: Successfully uploaded object %s enabling versioning on "
                    "bucket %s with version ID %s", self.object_name, self.bucket_name, latest_v)
        LOGGER.info("Step 3: Perform PUT Object Tagging for %s "
                    "with a tag key-value pair with Version ID %s",
                    self.object_name, latest_v)
        resp = s3_ver_tlib.put_object_tagging(s3_tag_test_obj=self.s3_tag_obj,
                                              s3_ver_test_obj=self.s3_ver_obj,
                                              bucket_name=self.bucket_name,
                                              object_name=self.object_name,
                                              version_tag=self.ver_tag, version_id=latest_v,
                                              versions_dict=self.versions)
        assert_utils.assert_true(resp[0], resp)
        LOGGER.info("Step 3: Performed PUT Object Tagging for %s with a tag key-value pair",
                    self.object_name)
        LOGGER.info("Step 4: Perform GET Object Tagging for %s with versionId=%s",
                    self.object_name, latest_v)
        put_tag = self.ver_tag[self.object_name][latest_v][-1]
        resp = s3_ver_tlib.delete_object_tagging(bucket_name=self.bucket_name,
                                                 s3_ver_test_obj=self.s3_ver_obj,
                                                 s3_tag_test_obj=self.s3_tag_obj,
                                                 object_name=self.object_name, version_id=latest_v)
        assert_utils.assert_true(resp[0], resp)
        get_tag = resp[1][0]
        assert_utils.assert_equal(get_tag, put_tag, "Mismatch in tag Key-Value pair."
                                                    f"Expected: {put_tag} \n Actual: {get_tag}")
        LOGGER.info("Step 4: Performed GET Object Tagging for %s with versionId=%s is %s",
                    self.object_name, latest_v, get_tag)
        non_existing_version = ''.join(random.sample(latest_v, len(latest_v)))
        LOGGER.info("Step 5: Perform DELETE Object Tagging for object1  %s "
                    "with a tag key-value pair for non-existing "
                    "versionId=%s",
                    self.object_name, non_existing_version)
        resp = s3_ver_tlib.delete_object_tagging(bucket_name=self.bucket_name,
                                                 s3_ver_test_obj=self.s3_ver_obj,
                                                 s3_tag_test_obj=self.s3_tag_obj,
                                                 object_name=self.object_name,
                                                 version_id=non_existing_version)
        # For non-existing version ID , expecting "404 Not Found (NoSuchKey)"
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(NO_SUCH_KEY_ERR, resp[1].message)
        LOGGER.info("Step 5: Perform DELETE Object Tagging for object1  %s for non-existing"
                    "versionId=%s", self.object_name, non_existing_version)
        non_existing_object = ''.join(random.sample(self.object_name, len(self.object_name)))
        LOGGER.info("Step 6: Perform DELETE Object Tagging for non-existing object %s "
                    "with a tag key-value pair with versionId=%s", non_existing_object, latest_v)
        resp = s3_ver_tlib.delete_object_tagging(bucket_name=self.bucket_name,
                                                 s3_ver_test_obj=self.s3_ver_obj,
                                                 s3_tag_test_obj=self.s3_tag_obj,
                                                 object_name=non_existing_object,
                                                 version_id=latest_v)
        # For non-existing object, expecting "404 Not Found (NoSuchKey)"
        assert_utils.assert_false(resp[0], resp)
        assert_utils.assert_in(NO_SUCH_KEY_ERR, resp[1].message)
        LOGGER.info("Step 6: Perform DELETE Object Tagging for non-existing object %s "
                    "with a tag key-value pair with versionId=%s", non_existing_object, latest_v)
        LOGGER.info("ENDED: Test DELETE object tagging for non-existing version or object.")
