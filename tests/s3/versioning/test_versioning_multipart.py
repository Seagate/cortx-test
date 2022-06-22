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

"""Test module for Multipart object versioning."""

import logging
import os
from time import perf_counter_ns

import pytest

from commons import error_messages as err_msg
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from libs.s3 import s3_versioning_common_test_lib as s3ver_cmn_lib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib


class TestVersioningMultipart:
    """Test suite for multipart with versioning."""

    # pylint: disable=attribute-defined-outside-init, too-many-instance-attributes
    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Summary: Function will be invoked prior to each test case.

        Description: It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        perform the cleanup.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations.")
        self.s3test_obj = S3TestLib()
        self.s3ver_test_obj = S3VersioningTestLib()
        self.s3mp_test_obj = S3MultipartTestLib()
        self.bucket_name = f"s3bkt-versioning-{perf_counter_ns()}"
        self.object_prefix = "s3obj-versioning-{}"
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestMultipartVersioning")
        self.object_name = self.object_prefix.format(perf_counter_ns())
        self.test_file_path = os.path.join(self.test_dir_path, self.object_name)
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        resp = system_utils.create_file(self.test_file_path, count=20)
        assert_utils.assert_true(resp[0], resp[1])
        res = self.s3test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.bkt_list = self.s3test_obj.bucket_list()[1]
        self.log.info("Created a bucket with name : %s", self.bucket_name)
        self.log.info("ENDED: Setup operations.")
        yield
        self.log.info("STARTED: Teardown operations.")
        s3ver_cmn_lib.empty_versioned_bucket(self.s3ver_test_obj, self.bucket_name)
        res = self.s3test_obj.delete_bucket(self.bucket_name, force=True)
        assert_utils.assert_true(res[0], res[1])
        if system_utils.path_exists(self.test_file_path):
            system_utils.remove_file(self.test_file_path)
        self.log.info("ENDED: Teardown operations.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41284")
    def test_preexist_mpu_versioning_enabled_bkt_41284(self):
        """Test pre-existing multipart upload in a versioning enabled bucket."""
        self.log.info("STARTED: Test pre-existing multipart upload in a versioning enabled bucket")
        self.log.info("Step 2-4: Upload multipart object to a bucket")
        versions = {}
        s3ver_cmn_lib.upload_version(self.s3mp_test_obj, self.bucket_name, self.object_name,
                                     self.test_file_path, versions_dict=versions,
                                     is_multipart=True, total_parts=2, file_size=10,
                                     is_unversioned=True)
        self.log.info("Step 5: Put bucket versioning with status as Enabled")
        res = self.s3ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: List Object Versions")
        s3ver_cmn_lib.check_list_object_versions(self.s3ver_test_obj, bucket_name=self.bucket_name,
                                                 expected_versions=versions)
        self.log.info("Step 7: Check GET/HEAD Object")
        v_id = versions[self.object_name]["version_history"][0]
        etag = versions[self.object_name]["versions"][v_id]
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    etag=etag)
        self.log.info("Step 8: Check GET/HEAD Object with versionId = null")
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    version_id="null", etag=etag)
        self.log.info("ENDED: Test pre-existing multipart upload in a versioning enabled bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41285")
    def test_mpu_ver_enabled_bkt_41285(self):
        """Test multipart upload in a versioning enabled bucket."""
        self.log.info("STARTED: Test multipart upload in a versioning enabled bucket.")
        self.log.info("Step 2: PUT Bucket versioning with status as Enabled")
        res = self.s3ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 3-7: Upload multipart object to a bucket")
        versions = {}
        s3ver_cmn_lib.upload_version(self.s3mp_test_obj, self.bucket_name,
                                     self.object_name, self.test_file_path,
                                     versions_dict=versions, is_multipart=True,
                                     total_parts=2, file_size=10, is_unversioned=False)
        self.log.info("Step 8: List Object Versions")
        s3ver_cmn_lib.check_list_object_versions(self.s3ver_test_obj, bucket_name=self.bucket_name,
                                                 expected_versions=versions)
        self.log.info("Step 9: Check GET/HEAD Object")
        v_id = versions[self.object_name]["version_history"][0]
        etag = versions[self.object_name]["versions"][v_id]
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name, etag=etag)
        self.log.info("Step 10: Check GET/HEAD Object with versionId")
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    version_id=v_id, etag=etag)
        self.log.info("ENDED: Test multipart upload in a versioning enabled bucket.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41286")
    def test_mpu_versioning_suspended_bkt_41286(self):
        """Test multipart upload in a versioning suspended bucket."""
        self.log.info("STARTED: Test multipart upload in a versioning suspended bucket.")
        self.log.info("Step 2: PUT Bucket versioning with status as Suspended")
        res = self.s3ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                        status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 3-7: Upload multipart object to a bucket")
        versions = {}
        s3ver_cmn_lib.upload_version(self.s3mp_test_obj, self.bucket_name,
                                     self.object_name, self.test_file_path,
                                     versions_dict=versions, is_multipart=True,
                                     total_parts=2, file_size=10,
                                     chk_null_version=True)
        self.log.info("Step 8: List Object Versions")
        s3ver_cmn_lib.check_list_object_versions(self.s3ver_test_obj, bucket_name=self.bucket_name,
                                                 expected_versions=versions)
        self.log.info("Step 9: Check GET/HEAD Object")
        v_id = versions[self.object_name]["version_history"][0]
        etag = versions[self.object_name]["versions"][v_id]
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name, etag=etag)
        self.log.info("Step 10: Check GET/HEAD Object with versionId = null")
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    version_id="null", etag=etag)
        self.log.info("ENDED: Test multipart upload in a versioning suspended bucket.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41287")
    def test_mpu_del_versioning_enabled_bkt_41287(self):
        """Test deletion of multipart upload in a versioning enabled bucket."""
        self.log.info("STARTED: Test deletion of multipart upload in a versioning enabled bucket")
        self.log.info("Step 2: PUT Bucket versioning with status as Enabled")
        res = self.s3ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        versions = {}
        self.log.info("Step 3: Upload multipart object")
        s3ver_cmn_lib.upload_version(self.s3mp_test_obj, self.bucket_name, self.object_name,
                                     self.test_file_path, versions_dict=versions, is_multipart=True,
                                     total_parts=2, file_size=10)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 4: Perform DELETE Object for uploaded object ")
        s3ver_cmn_lib.delete_version(self.s3ver_test_obj, self.bucket_name, self.object_name,
                                     versions_dict=versions)
        self.log.info("Step 5: Check GET/HEAD Object")
        v_id = versions[self.object_name]["version_history"][0]
        etag = versions[self.object_name]["versions"][v_id]
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    get_error_msg=err_msg.NO_SUCH_KEY_ERR,
                                                    head_error_msg=err_msg.NOT_FOUND_ERR, etag=etag)
        self.log.info("Step 6: List Object Versions")
        s3ver_cmn_lib.check_list_object_versions(self.s3ver_test_obj, bucket_name=self.bucket_name,
                                                 expected_versions=versions,)
        self.log.info("Step 7: List Objects")
        s3ver_cmn_lib.check_list_objects(self.s3test_obj, self.bucket_name,
                                         expected_objects=[])
        self.log.info("ENDED: Test deletion of multipart upload in a versioning enabled bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-41288')
    def test_abort_multipart_upload_does_not_create_a_new_version_41288(self):
        """Test Abort Multipart Upload does not create a new version."""
        self.log.info("STARTED: Test Abort Multipart Upload does not create a new version.")
        self.log.info("Step 1: Create bucket.")
        assert_utils.assert_in(self.bucket_name, self.bkt_list,
                               f"Bucket '{self.bucket_name}' does not exists")
        self.log.info("Step 2: PUT Bucket versioning with status as Enabled.")
        self.s3ver_test_obj.put_bucket_versioning(self.bucket_name, status="Enabled")
        self.log.info("Step 3: Initiate multipart upload.")
        res = self.s3mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Step 4: Upload parts.")
        self.log.info("Uploading parts into bucket")
        res = self.s3mp_test_obj.upload_parts(mpu_id, self.bucket_name, self.object_name,
                                              multipart_obj_size=100, total_parts=10,
                                              multipart_obj_path=self.test_file_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]), 10, res[1])
        self.log.info("Step 5: Abort multipart upload.")
        res = self.s3mp_test_obj.abort_multipart_upload(self.bucket_name, self.object_name, mpu_id)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: Perform List Object Versions.")
        s3ver_cmn_lib.check_list_object_versions(
            self.s3ver_test_obj, bucket_name=self.bucket_name, expected_versions={})
        self.log.info("Step 7: Perform GET/HEAD Object on aborted object.")
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    self.bucket_name, self.object_name,
                                                    get_error_msg=err_msg.NO_SUCH_KEY_ERR,
                                                    head_error_msg=err_msg.NOT_FOUND_ERR)
        self.log.info("ENDED: Test Abort Multipart Upload does not create a new version.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-41289')
    def test_upload_multiple_versions_to_multipart_uploaded_object_in_versioned_bucket_41289(self):
        """Test Upload multiple versions to a multipart uploaded object in a versioned bucket."""
        self.log.info("STARTED: Test Upload multiple versions to a multipart uploaded object in "
                      "a versioned bucket.")
        versions = {}
        self.log.info("Step 1: Create bucket.")
        assert_utils.assert_in(self.bucket_name, self.bkt_list,
                               f"Bucket '{self.bucket_name}' does not exists")
        self.log.info("Step 2: PUT Bucket versioning with status as Enabled.")
        self.s3ver_test_obj.put_bucket_versioning(self.bucket_name, status="Enabled")
        self.log.info("Step 3: Upload a multipart object - mpobject1: mpversionid1")
        s3ver_cmn_lib.upload_version(self.s3mp_test_obj, self.bucket_name, self.object_name,
                                     self.test_file_path, versions_dict=versions,
                                     is_multipart=True, total_parts=10, file_size=100)
        self.log.info("Step 4: Upload 4 more versions to mpobject1 and then multipart upload.")
        for i in range(1, 4):
            system_utils.create_file(self.test_file_path, count=10 * i)
            s3ver_cmn_lib.upload_version(self.s3test_obj, self.bucket_name, self.object_name,
                                         self.test_file_path, versions_dict=versions)
        s3ver_cmn_lib.upload_version(self.s3mp_test_obj, self.bucket_name, self.object_name,
                                     self.test_file_path, versions_dict=versions,
                                     is_multipart=True, total_parts=10, file_size=200)
        self.log.info("Step 5: PUT Bucket versioning with status as Suspended.")
        self.s3ver_test_obj.put_bucket_versioning(self.bucket_name, status="Suspended")
        self.log.info("Step 6: Perform PUT Object to mpobject1 (version with 'versionId=null').")
        s3ver_cmn_lib.upload_version(self.s3test_obj, self.bucket_name, self.object_name,
                                     self.test_file_path, versions_dict=versions,
                                     chk_null_version=True)
        self.log.info("Step 7: Perform List Object Versions.")
        s3ver_cmn_lib.check_list_object_versions(self.s3ver_test_obj, self.bucket_name, versions)
        self.log.info("Step 8: Perform List Objects.")
        s3ver_cmn_lib.check_list_objects(self.s3test_obj, self.bucket_name,
                                         expected_objects=[self.object_name])
        self.log.info("Step 9: Perform GET/HEAD Object.")
        latest = versions[self.object_name]["is_latest"]
        obj_versions = versions[self.object_name]["versions"]
        self.log.info("Object '%s': version dict '%s'", self.object_name, obj_versions)
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    self.bucket_name, self.object_name,
                                                    etag=obj_versions[latest],
                                                    version_id=latest)
        self.log.info("Step 10: Perform DELETE Object for all 6 versions viz. null, id1..id5.")
        s3ver_cmn_lib.empty_versioned_bucket(self.s3ver_test_obj, self.bucket_name)
        self.log.info("Step 11: Perform List Object Versions.")
        s3ver_cmn_lib.check_list_object_versions(
            self.s3ver_test_obj, bucket_name=self.bucket_name, expected_versions={})
        self.log.info("Step 12: Perform List Objects.")
        s3ver_cmn_lib.check_list_objects(
            self.s3test_obj, self.bucket_name, expected_objects=[])
        self.log.info("Step 13: Perform GET/HEAD Object.")
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    self.bucket_name, self.object_name,
                                                    get_error_msg=err_msg.NO_SUCH_KEY_ERR,
                                                    head_error_msg=err_msg.NOT_FOUND_ERR)
        self.log.info("ENDED: Test Upload multiple versions to a multipart uploaded object in a "
                      "versioned bucket.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-41290')
    def test_upload_new_versions_to_existing_objects_using_multipart_upload_41290(self):
        """Test Upload new versions to existing objects using multipart upload."""
        self.log.info("STARTED: Upload new versions to existing objects using multipart upload.")
        versions = {}
        object_name1 = self.object_prefix.format(perf_counter_ns())
        object_name2 = self.object_prefix.format(perf_counter_ns())
        self.log.info("Step 1: Create bucket.")
        assert_utils.assert_in(self.bucket_name, self.bkt_list,
                               f"Bucket '{self.bucket_name}' does not exists")
        self.log.info("Step 2: Upload object - object1.")
        s3ver_cmn_lib.upload_version(self.s3test_obj, self.bucket_name, object_name1,
                                     self.test_file_path, versions_dict=versions,
                                     is_unversioned=True)
        self.log.info("Step 3: PUT Bucket versioning with status as Enabled.")
        resp = self.s3ver_test_obj.put_bucket_versioning(self.bucket_name, status="Enabled")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Upload object - object2 (creates version with id = obj2versionid1).")
        s3ver_cmn_lib.upload_version(self.s3test_obj, self.bucket_name, object_name2,
                                     self.test_file_path, versions_dict=versions)
        self.log.info("Step 5: Upload a new version to object2 using multipart upload (creates "
                      "version with id = obj2versionid2).")
        s3ver_cmn_lib.upload_version(self.s3mp_test_obj, self.bucket_name, object_name2,
                                     self.test_file_path, versions_dict=versions,
                                     is_multipart=True, total_parts=10, file_size=150)
        self.log.info("Step 6: PUT Bucket versioning with status as Suspended.")
        self.s3ver_test_obj.put_bucket_versioning(self.bucket_name, status="Suspended")
        self.log.info("Step 7: Upload a new version to object1 using multipart upload ("
                      "overwrites version with versionid = null).")
        s3ver_cmn_lib.upload_version(self.s3mp_test_obj, self.bucket_name, object_name1,
                                     self.test_file_path, versions_dict=versions,
                                     is_multipart=True, total_parts=10, file_size=100,
                                     chk_null_version=True)
        self.log.info("Step 8: Perform List Object Versions.")
        s3ver_cmn_lib.check_list_object_versions(
            self.s3ver_test_obj, bucket_name=self.bucket_name, expected_versions=versions)
        self.log.info("Step 9: Perform List Objects.")
        s3ver_cmn_lib.check_list_objects(self.s3test_obj, self.bucket_name,
                                         expected_objects=[object_name1, object_name2])
        self.log.info("Step 10: Perform GET/HEAD Object for object1.")
        latest = versions[object_name1]["is_latest"]
        obj1_versions = versions[object_name1]["versions"]
        self.log.info("Object1 '%s': version dict '%s'", object_name1, obj1_versions)
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    self.bucket_name, object_name1,
                                                    etag=obj1_versions[latest],
                                                    version_id=latest)
        self.log.info("Step 11: Perform GET/HEAD Object for object2.")
        latest = versions[object_name2]["is_latest"]
        obj2_versions = versions[object_name2]["versions"]
        self.log.info("Object2 '%s': version dict '%s'", object_name2, obj2_versions)
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    self.bucket_name, object_name2,
                                                    etag=obj2_versions[latest],
                                                    version_id=latest)
        self.log.info("ENDED: Upload new versions to existing objects using multipart upload.")
