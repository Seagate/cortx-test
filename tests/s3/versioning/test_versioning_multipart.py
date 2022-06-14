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

""" test module for Multipart Object Versioning."""

import logging
import os
import time
import pytest


from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.utils import s3_utils
from commons import error_messages as errmsg

from time import perf_counter_ns

from config.s3 import MPART_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3 import s3_versioning_common_test_lib as s3ver_cmn_lib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib


class TestVersioningMultipart:
    """Test suite for multipart with versioning"""

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
        self.object_name = f"s3obj-versioning-{perf_counter_ns()}"
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestMultipartVersioning")
        self.test_file_path = os.path.join(self.test_dir_path, self.object_name)
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        resp = system_utils.create_file(self.test_file_path, count=20)
        assert_utils.assert_true(resp[0], resp[1])
        res = self.s3test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)
        self.log.info("ENDED: Setup operations.")
        yield
        self.log.info("STARTED: Teardown operations.")
        s3ver_cmn_lib.empty_versioned_bucket(self.s3ver_test_obj, self.bucket_name)
        res = self.s3test_obj.delete_bucket(self.bucket_name, force=True)
        assert_utils.assert_true(res[0], res[1])
        if system_utils.path_exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)
        self.log.info("ENDED: Teardown operations.")

    @CTFailOn(error_handler)
    def test_preexist_mpu_versioning_enabled_bkt_41284(self):
        """
        Test pre-existing multipart upload in a versioning enabled bucket
        """
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
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name)
        self.log.info("Step 8: Check GET/HEAD Object with versionId = null")
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    version_id="null")
        self.log.info("ENDED: Test pre-existing multipart upload in a versioning enabled bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41285")
    @CTFailOn(error_handler)
    def test_mpu_ver_enabled_bkt_41285(self):
        """
        Test multipart upload in a versioning enabled bucket.
        """
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
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name)
        self.log.info("Step 10: Check GET/HEAD Object with versionId")
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    version_id=versions[self.object_name]
                                                    ["version_history"][0])
        self.log.info("ENDED: Test multipart upload in a versioning enabled bucket.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41286")
    @CTFailOn(error_handler)
    def test_mpu_versioning_suspended_bkt_41286(self):
        """
        Test multipart upload in a versioning suspended bucket
        """
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
                                                total_parts=2, file_size=10, is_unversioned=False,
                                                chk_null_version=True)
        self.log.info("Step 8: List Object Versions")
        s3ver_cmn_lib.check_list_object_versions(self.s3ver_test_obj, bucket_name=self.bucket_name,
                                                 expected_versions=versions)
        self.log.info("Step 9: Check GET/HEAD Object")
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name)
        self.log.info("Step 10: Check GET/HEAD Object with versionId = null")
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    version_id="null")
        self.log.info("ENDED: Test multipart upload in a versioning suspended bucket.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41287")
    @CTFailOn(error_handler)
    def test_mpu_del_versioning_enabled_bkt_41287(self):
        """
        Test deletion of multipart upload in a versioning enabled bucket
        """
        self.log.info("STARTED: Test deletion of multipart upload in a versioning enabled bucket")
        self.log.info("Step 2: PUT Bucket versioning with status as Enabled")
        res = self.s3ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        versions = {}
        self.log.info("Step 3: Upload multipart object")
        s3ver_cmn_lib.upload_version(self.s3mp_test_obj, self.bucket_name, self.object_name,
                                     self.test_file_path, versions_dict=versions, is_multipart=True,
                                     total_parts=2, file_size=10, is_unversioned=False)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 4: Perform DELETE Object for uploaded object ")
        """TODO: this test needs to be rechecked and executed throughly in next sprint"""
        s3ver_cmn_lib.delete_version(self.s3ver_test_obj, self.bucket_name, self.object_name,
                                     versions_dict=versions,
                                     version_id=versions[self.object_name]["version_history"][0])
        self.log.info("Step 5: Check GET/HEAD Object")
        s3ver_cmn_lib.check_get_head_object_version(self.s3test_obj, self.s3ver_test_obj,
                                                    bucket_name=self.bucket_name,
                                                    object_name=self.object_name,
                                                    get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                                    head_error_msg=errmsg.NOT_FOUND_ERR)
        self.log.info("Step 6: List Object Versions")
        s3ver_cmn_lib.check_list_object_versions(self.s3ver_test_obj, bucket_name=self.bucket_name,
                                                 expected_versions=versions,)
        self.log.info("Step 7: List Objects")
        s3ver_cmn_lib.check_list_objects(self.s3test_obj, self.bucket_name,
                                         expected_objects=[self.object_name])
        self.log.info("ENDED: Test deletion of multipart upload in a versioning enabled bucket")
