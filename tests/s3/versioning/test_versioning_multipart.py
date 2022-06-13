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
from commons.utils.system_utils import create_file
from commons.utils.system_utils import path_exists
from commons.utils.system_utils import make_dirs
from commons.utils.system_utils import remove_dirs
from commons.utils import assert_utils
from commons.utils import s3_utils

from config.s3 import S3_CFG
from config.s3 import MPART_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3.s3_versioning_common_test_lib import check_list_object_versions, upload_mpu_versions
from libs.s3.s3_versioning_common_test_lib import check_get_head_object_version
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_versioning_common_test_lib import upload_versions


class TestVersioningMultipart:
    """Test suite for multipart with versioning"""

    def setup_method(self):
        """
        Function will perform setup prior to each test case.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_ver_test_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        self.s3_mp_test_obj = S3MultipartTestLib()
        self.bucket_name = "ver-bkt-{}".format(time.perf_counter_ns())
        self.object_name = "ver-obj-{}".format(time.perf_counter_ns())
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestVersioningMultipart")
        self.versions = {}
        self.test_file = "mpu_obj_ver"
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.mp_obj_path = os.path.join(self.test_dir_path, self.test_file)
        self.file_path = os.path.join(self.test_dir_path, self.object_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)

    def teardown_method(self):
        """
        Function will perform cleanup after each test case.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info("Clean : %s", self.test_dir_path)
        if path_exists(self.test_dir_path):
            remove_dirs(self.test_dir_path)
        self.log.info("Cleanup test directory: %s", self.test_dir_path)
        # DELETE Object with VersionId is WIP, uncomment once feature is available
        # res = self.s3_ver_test_obj.bucket_list()
        # pref_list = []
        # for bucket_name in res[1]:
        #     if bucket_name.startswith("ver-bkt"):
        #         empty_versioned_bucket(self.s3_ver_test_obj, bucket_name)
        #         pref_list.append(bucket_name)
        # if pref_list:
        #     res = self.s3_test_obj.delete_multiple_buckets(pref_list)
        #     assert_utils.assert_true(res[0], res[1])

    # pylint: disable=no-self-use
    # pylint: disable-msg=too-many-locals
    def initiate_upload_list_mpu(self, bucket_name, object_name, **kwargs):
        """
        This initialises multipart, upload parts, list parts, complete mpu and return the
        response and mpu id
        """
        is_part_upload = kwargs.get("is_part_upload", False)
        is_lst_mpu = kwargs.get("is_lst_mpu", False)
        parts = kwargs.get("parts", None)
        res = self.s3_mp_test_obj.create_multipart_upload(bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_in("VersionId", res[1])
        mpu_id = res[1]["UploadId"]
        parts_details = []
        if is_part_upload and is_lst_mpu:
            self.log.info("Uploading parts")
            resp = self.s3_mp_test_obj.upload_parts_parallel(mpu_id, bucket_name,
                                                              object_name, parts=parts)
            assert_utils.assert_not_in("VersionId", resp[1])
            for i in resp[1]['Parts']:
                parts_details.append({"PartNumber": i['PartNumber'],
                                      "ETag": i["ETag"]})
            sorted_lst = sorted(parts_details, key=lambda x: x['PartNumber'])
            res = self.s3_mp_test_obj.list_parts(mpu_id, bucket_name, object_name)
            assert_utils.assert_true(res[0], res[1])
            assert_utils.assert_not_in("VersionId", resp[1])
            self.log.info("List Multipart uploads")
            return mpu_id, resp, sorted_lst
        return mpu_id

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41284")
    @CTFailOn(error_handler)
    def test_preexist_mpu_versioning_enabled_bkt_41284(self):
        """
        Test pre-existing multipart upload in a versioning enabled bucket
        """
        self.log.info("STARTED: Test pre-existing multipart upload in a versioning enabled bucket")
        mp_config = MPART_CFG["test_40265"]
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        create_file(self.file_path, mp_config["file_size"])
        precalc_parts = s3_utils.get_precalculated_parts(self.file_path, mp_config["part_sizes"],
                                                         chunk_size=mp_config["chunk_size"])
        self.log.info("Step 2-3: Upload multipart object to a bucket")
        mpu_id, resp, sorted_lst = self.initiate_upload_list_mpu(self.bucket_name, self.object_name,
                                                                 is_part_upload=True,
                                                                 is_lst_mpu=True,
                                                                 parts=precalc_parts)
        self.log.info("Step 4: Complete multipart upload")
        _, resp = self.s3_mp_test_obj.complete_multipart_upload(mpu_id, sorted_lst,
                                                                self.bucket_name, self.object_name)
        self.log.info("Step 5: Put bucket versioning with status as Enabled")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Enabled")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: List Object Versions")
        _, list_resp = check_list_object_versions(self.s3_ver_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  expected_versions={})
        versions = list_resp[1]["Versions"][0]
        self.log.info("list_resp is %s",versions)
        self.log.info("Step 7: Check GET/HEAD Object")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      version_id=versions["VersionId"],
                                      etag=versions["ETag"])
        self.log.info("Step 8: Check GET/HEAD Object with versionId = null")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      version_id="null", etag=versions["ETag"])
        self.log.info("ENDED: Test pre-existing multipart upload in a versioning enabled bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41285")
    @CTFailOn(error_handler)
    def test_preexist_mpu_versioning_enabled_bkt_41285(self):
        """
        Test multipart upload in a versioning enabled bucket.
        """
        self.log.info("STARTED: Test multipart upload in a versioning enabled bucket.")
        mp_config = MPART_CFG["test_40265"]
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        create_file(self.file_path, mp_config["file_size"])
        self.log.info("Step 2: PUT Bucket versioning with status as Enabled")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Enabled")
        assert_utils.assert_true(res[0], res[1])
        precalc_parts = s3_utils.get_precalculated_parts(self.file_path, mp_config["part_sizes"],
                                                         chunk_size=mp_config["chunk_size"])
        self.log.info("Step 3-5: Upload multipart object to a bucket")
        mpu_id, resp, sorted_lst = self.initiate_upload_list_mpu(self.bucket_name, self.object_name,
                                                                 is_part_upload=True,
                                                                 is_lst_mpu=True,
                                                                 parts=precalc_parts)
        self.log.info("Step 6: List multipart uploads")
        res = self.s3_mp_test_obj.list_multipart_uploads(self.bucket_name)
        assert_utils.assert_not_in("VersionId", res[1])
        self.log.info("Step 7: Complete multipart upload")
        _, resp = self.s3_mp_test_obj.complete_multipart_upload(mpu_id, sorted_lst,
                                                                self.bucket_name, self.object_name)
        assert_utils.assert_in("VersionId", resp)
        assert_utils.assert_in("ETag", resp)
        self.log.info("Step 8: List Object Versions")
        _, list_resp = check_list_object_versions(self.s3_ver_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  expected_versions={})
        versions = list_resp[1]["Versions"][0]
        self.log.info("list_resp is %s", versions)
        self.log.info("Step 9: Check GET/HEAD Object")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name)
        self.log.info("Step 10: Check GET/HEAD Object with versionId")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name, object_name=self.object_name,
                                      version_id=versions["VersionId"], etag=versions["ETag"])
        self.log.info("ENDED: Test multipart upload in a versioning enabled bucket.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41286")
    @CTFailOn(error_handler)
    def test_preexist_mpu_versioning_enabled_bkt_41286(self):
        """
        Test multipart upload in a versioning suspended bucket
        """
        self.log.info("STARTED: Test multipart upload in a versioning suspended bucket.")
        mp_config = MPART_CFG["test_40265"]
        self.log.info("Step 2: PUT Bucket versioning with status as Suspended")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        create_file(self.file_path, mp_config["file_size"])
        precalc_parts = s3_utils.get_precalculated_parts(self.file_path, mp_config["part_sizes"],
                                                         chunk_size=mp_config["chunk_size"])
        self.log.info("Step 3-5: Upload multipart object to a bucket")
        mpu_id, resp, sorted_lst = self.initiate_upload_list_mpu(self.bucket_name, self.object_name,
                                                                 is_part_upload=True,
                                                                 is_lst_mpu=True,
                                                                 parts=precalc_parts)
        self.log.info("Step 6: List multipart uploads")
        res = self.s3_mp_test_obj.list_multipart_uploads(self.bucket_name)
        assert_utils.assert_not_in("VersionId", res[1])
        self.log.info("Step 7: Complete multipart upload")
        _, resp = self.s3_mp_test_obj.complete_multipart_upload(mpu_id, sorted_lst,
                                                                self.bucket_name, self.object_name)
        assert_utils.assert_in("VersionId", resp)
        assert_utils.assert_in("ETag", resp)
        self.log.info("Step 8: List Object Versions")
        _, list_resp = check_list_object_versions(self.s3_ver_test_obj,
                                                  bucket_name=self.bucket_name,
                                                  expected_versions={}, )
        versions = list_resp[1]["Versions"][0]
        self.log.info("list_resp is %s", versions)
        assert_utils.assert_equal(versions["VersionId"], "null", "VersionId is not None")
        assert_utils.assert_equal(versions["IsLatest"], "True", "IsLatest is not True")
        assert_utils.assert_in(versions["ETag"], versions.keys(), "ETag is not available")
        self.log.info("Step 9: Check GET/HEAD Object")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name,
                                      object_name=self.object_name)
        self.log.info("Step 10: Check GET/HEAD Object with versionId = null")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name,
                                      object_name=self.object_name,
                                      version_id="null")
        self.log.info("ENDED: Test multipart upload in a versioning suspended bucket.")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-41287")
    @CTFailOn(error_handler)
    def test_preexist_mpu_versioning_enabled_bkt_41287(self):
        """
        Test multipart upload in a versioning suspended bucket
        """
        self.log.info("STARTED: Test deletion of multipart upload in a versioning enabled bucket")
        mp_config = MPART_CFG["test_8926"]
        self.log.info("Step 2: PUT Bucket versioning with status as Enabled")
        res = self.s3_ver_test_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                         status="Enabled")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 3: Upload multipart object to a bucket")
        _, resp = self.s3_mp_test_obj.simple_multipart_upload(self.bucket_name,
                                                              self.object_name,
                                                              mp_config["file_size"],
                                                              self.file_path,
                                                              mp_config["total_parts"])
        self.log.info("Step 4: Perform DELETE Object for uploaded object ")
        self.s3_test_obj.delete_object(self.bucket_name, self.object_name)
        self.log.info("Step 5: Check GET/HEAD Object")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_test_obj,
                                      bucket_name=self.bucket_name,
                                      object_name=self.object_name)
        self.log.info("Step 6: List Object Versions")
        check_list_object_versions(self.s3_ver_test_obj, bucket_name=self.bucket_name,
                                   expected_versions={})
        self.log.info("Step 7: List Objects")
        self.s3_test_obj.list_objects_details(self.bucket_name)
        self.log.info("ENDED: Test deletion of multipart upload in a versioning enabled bucket")







