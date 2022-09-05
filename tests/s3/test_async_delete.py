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

"""CORTX RGW Async Delete test module"""

import logging
import os
import random
import time
import pytest

from commons import error_messages as errmsg
from commons.params import TEST_DATA_FOLDER
from commons.utils.s3_utils import create_random_file
from commons.utils.system_utils import create_file
from commons.utils.system_utils import path_exists
from commons.utils.system_utils import remove_file
from commons.utils.system_utils import make_dirs
from commons.utils.system_utils import remove_dirs
from commons.utils import assert_utils
from config.s3 import DEL_CFG
from config.s3 import S3_CFG
from libs.s3.s3_common_test_lib import get_cortx_rgw_bytecount
from libs.s3.s3_common_test_lib import poll_cluster_capacity
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_versioning_test_lib import S3VersioningTestLib
from libs.s3.s3_versioning_common_test_lib import check_get_head_object_version
from libs.s3.s3_versioning_common_test_lib import check_list_objects
from libs.s3.s3_versioning_common_test_lib import check_list_object_versions
from libs.s3.s3_versioning_common_test_lib import delete_version
from libs.s3.s3_versioning_common_test_lib import download_and_check
from libs.s3.s3_versioning_common_test_lib import empty_versioned_bucket
from libs.s3.s3_versioning_common_test_lib import upload_version


class TestAsyncDelete:
    """Test CORTX RGW Async Delete"""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to all the test cases.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup test suite level operations.")
        cls.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.s3_ver_obj = S3VersioningTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.fixed_size_fpaths = []
        cls.total_fixed_file_size = 0
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestAsyncDelete")
        if not path_exists(cls.test_dir_path):
            make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.file_prefix = "async_del"
        cls.object_prefix = "obj_async_del"
        cls.bucket_prefix = "buck-async-del"
        for file_size in DEL_CFG["fixed_obj_size"]:
            file_name = f"{cls.file_prefix}{time.perf_counter_ns()}"
            file_path = os.path.join(cls.test_dir_path, file_name)
            create_file(file_path, file_size, "/dev/urandom")
            cls.log.info("Created file: %s", file_path)
            cls.fixed_size_fpaths.append(file_path)
            cls.total_fixed_file_size += os.path.getsize(file_path)
        cls.log.info("ENDED: Setup test suite level operations.")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all the test cases.
        """
        cls.log.info("STARTED: teardown test suite operations.")
        if path_exists(cls.test_dir_path):
            remove_dirs(cls.test_dir_path)
        cls.log.info("Cleanup test directory: %s", cls.test_dir_path)
        cls.log.info("ENDED: teardown test suite operations.")

    # pylint: disable=attribute-defined-outside-init
    def setup_method(self):
        """
        Function will perform prerequisite test steps prior to each test case.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup test method operations")
        self.bucket_name = f"{self.bucket_prefix}-{time.perf_counter_ns()}"
        self.obj_names = []
        self.upload_paths = []
        for _ in self.fixed_size_fpaths:
            obj_name = f"{self.object_prefix}-{time.perf_counter_ns()}"
            self.obj_names.append(obj_name)
            # Upload file paths for overwrite scenario
            file_name = f"{self.file_prefix}{time.perf_counter_ns()}"
            file_path = os.path.join(self.test_dir_path, file_name)
            self.upload_paths.append(file_path)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name: %s", self.bucket_name)
        download_file = f"{self.file_prefix}_download_{time.perf_counter_ns()}"
        self.download_path = os.path.join(self.test_dir_path, download_file)
        self.file_paths = self.upload_paths + [self.download_path]
        self.log.info("ENDED: Setup test method operations")

    def teardown_method(self):
        """
        Function will be invoked after each test case to clean up any test artifacts.
        """
        self.log.info("STARTED: Teardown test method operations")
        for fpath in self.file_paths:
            if path_exists(fpath):
                res = remove_file(fpath)
                self.log.info("cleaned path: %s, res: %s", fpath, res)
        res = self.s3_test_obj.bucket_list()
        empty_versioned_bucket(self.s3_ver_obj, self.bucket_name)
        self.s3_test_obj.delete_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("ENDED: Teardown test method operations")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-44815")
    def test_random_sized_object_delete_and_overwrite_44815(self):
        """
        Test delete and overwrite for simple object having random size.
        """
        self.log.info("STARTED: Test delete and overwrite for simple object having random size")
        self.log.info("Step 1: Upload 2 objects having random size")
        create_random_file(self.upload_paths[0], DEL_CFG["random_obj_size"]["min"],
                           DEL_CFG["random_obj_size"]["max"])
        resp = self.s3_test_obj.put_object(self.bucket_name, self.obj_names[0],
                                           self.upload_paths[0])
        assert_utils.assert_true(resp[0], resp[1])
        overwrite_file_size_1 = os.path.getsize(self.upload_paths[0])
        self.log.info("Original file size for overwrite: %s", overwrite_file_size_1)
        used_capacity1 = get_cortx_rgw_bytecount()['healthy']
        self.log.info("Initial CORTX capacity: %s", used_capacity1)
        create_random_file(self.upload_paths[1], DEL_CFG["random_obj_size"]["min"],
                           DEL_CFG["random_obj_size"]["max"])
        resp = self.s3_test_obj.put_object(self.bucket_name, self.obj_names[1],
                                           self.upload_paths[1])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Overwrite object 1")
        create_random_file(self.upload_paths[2], DEL_CFG["random_obj_size"]["min"],
                           DEL_CFG["random_obj_size"]["max"])
        overwrite_resp = self.s3_test_obj.put_object(self.bucket_name, self.obj_names[0],
                                                     self.upload_paths[2])
        assert_utils.assert_true(overwrite_resp[0], overwrite_resp[1])
        overwrite_file_size_2 = os.path.getsize(self.upload_paths[2])
        self.log.info("Overwritten file size: %s", overwrite_file_size_2)
        self.log.info("Step 3: Delete object 2")
        resp = self.s3_test_obj.delete_object(self.bucket_name, self.obj_names[1])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Verify object deletion")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_obj,
                                      bucket_name=self.bucket_name, object_name=self.obj_names[1],
                                      get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                      head_error_msg=errmsg.NOT_FOUND_ERR)
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=[self.obj_names[0]])
        self.log.info("Step 5: Sleep for GC minimum wait time")
        time.sleep(DEL_CFG["gc_min_wait_time"])
        self.log.info("Step 6: Verify space reclaimed")
        # NOTE: we can compare exact bytecount after F-71B
        chk_increase = overwrite_file_size_1 <= overwrite_file_size_2
        space_reclaimed = poll_cluster_capacity(chk_increase, DEL_CFG["space_reclaim_retry_time"],
                                                DEL_CFG["space_reclaim_max_retries"],
                                                initial_capacity=used_capacity1)
        assert_utils.assert_true(space_reclaimed, "Space not reclaimed.")
        self.log.info("Step 7: Verify object overwrite")
        check_get_head_object_version(self.s3_test_obj, self.s3_ver_obj,
                                      bucket_name=self.bucket_name, object_name=self.obj_names[0],
                                      etag=overwrite_resp[1]["ETag"])
        download_and_check(self.s3_test_obj, self.bucket_name, self.obj_names[0],
                           file_path=self.upload_paths[2], download_path=self.download_path)
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=[self.obj_names[0]])
        self.log.info("ENDED: Test delete and overwrite for simple object having random size")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-44816")
    def test_object_deletion_unversioned_bucket_44816(self):
        """
        Test object deletion with GC in an unversioned bucket.
        """
        self.log.info("STARTED: Test object deletion with GC in an unversioned bucket")
        used_capacity1 = get_cortx_rgw_bytecount()['healthy']
        self.log.info("Initial CORTX capacity: %s", used_capacity1)
        self.log.info("Step 1: Upload objects")
        for obj_name, fpath in zip(self.obj_names, self.fixed_size_fpaths):
            resp = self.s3_test_obj.put_object(self.bucket_name, obj_name, fpath)
            assert_utils.assert_true(resp[0], resp[1])
        used_capacity1 = get_cortx_rgw_bytecount()['healthy']
        self.log.info("Initial CORTX capacity: %s", used_capacity1)
        self.log.info("Step 2: Delete objects")
        for obj_name in self.obj_names:
            resp = self.s3_test_obj.delete_object(self.bucket_name, obj_name)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Verify object deletion")
        for obj_name in self.obj_names:
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_obj,
                                          bucket_name=self.bucket_name, object_name=obj_name,
                                          get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                          head_error_msg=errmsg.NOT_FOUND_ERR)
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name, expected_objects=[])
        self.log.info("Step 4: Sleep for GC minimum wait time")
        time.sleep(DEL_CFG["gc_min_wait_time"])
        self.log.info("Step 5: Verify space reclaimed")
        # NOTE: we can compare exact bytecount after F-71B
        space_reclaimed = poll_cluster_capacity(False, DEL_CFG["space_reclaim_retry_time"],
                                                DEL_CFG["space_reclaim_max_retries"],
                                                initial_capacity=used_capacity1)
        assert_utils.assert_true(space_reclaimed, "Space not reclaimed.")
        self.log.info("ENDED: Test object deletion with GC in an unversioned bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-44819")
    def test_object_overwrite_unversioned_bucket_44819(self):
        """
        Test object overwrite with GC in an unversioned bucket.
        """
        self.log.info("STARTED: Test object overwrite with GC in an unversioned bucket")
        self.log.info("Step 1: Upload objects")
        for obj_name, fpath in zip(self.obj_names, self.fixed_size_fpaths):
            resp = self.s3_test_obj.put_object(self.bucket_name, obj_name, fpath)
            assert_utils.assert_true(resp[0], resp[1])
        used_capacity1 = get_cortx_rgw_bytecount()['healthy']
        self.log.info("Initial CORTX capacity: %s", used_capacity1)
        self.log.info("Step 2: Overwrite objects with random size")
        overwrite_resp = []
        total_overwrite_file_size = 0
        for obj_name, fpath in zip(self.obj_names, self.upload_paths):
            create_random_file(fpath, DEL_CFG["random_obj_size"]["min"],
                               DEL_CFG["random_obj_size"]["max"])
            resp = self.s3_test_obj.put_object(self.bucket_name, obj_name, fpath)
            assert_utils.assert_true(resp[0], resp[1])
            overwrite_resp.append(resp)
            total_overwrite_file_size += os.path.getsize(fpath)
        self.log.info("Step 3: Sleep for GC minimum wait time")
        time.sleep(DEL_CFG["gc_min_wait_time"])
        self.log.info("Step 4: Verify space reclaimed")
        # NOTE: we can compare exact bytecount after F-71B
        chk_increase = self.total_fixed_file_size <= total_overwrite_file_size
        space_reclaimed = poll_cluster_capacity(chk_increase, DEL_CFG["space_reclaim_retry_time"],
                                                DEL_CFG["space_reclaim_max_retries"],
                                                initial_capacity=used_capacity1)
        assert_utils.assert_true(space_reclaimed, "Space not reclaimed.")
        for obj_name, fpath, resp in zip(self.obj_names, self.upload_paths, overwrite_resp):
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_obj,
                                          bucket_name=self.bucket_name, object_name=obj_name,
                                          etag=resp[1]["ETag"])
            download_and_check(self.s3_test_obj, self.bucket_name, obj_name,
                               file_path=fpath, download_path=self.download_path)
            check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                               expected_objects=self.obj_names)
        self.log.info("ENDED: Test object overwrite with GC in an unversioned bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-44825")
    def test_object_deletion_versioning_enabled_bucket_44825(self):
        """
        Test object deletion with GC in a versioning enabled bucket.
        """
        self.log.info("STARTED: Test object deletion with GC in a versioning enabled bucket")
        versions = {}
        self.log.info("Step 1: Enable bucket versioning")
        res = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 2: Upload objects")
        for obj_name, fpath in zip(self.obj_names, self.fixed_size_fpaths):
            upload_version(self.s3_test_obj, self.bucket_name, obj_name, fpath, versions)
        used_capacity1 = get_cortx_rgw_bytecount()['healthy']
        self.log.info("Initial CORTX capacity: %s", used_capacity1)
        self.log.info("Step 3: Delete objects by version id")
        for obj_name in self.obj_names:
            v_id = versions[obj_name]["is_latest"]
            delete_version(self.s3_test_obj, self.s3_ver_obj, self.bucket_name, obj_name,
                           versions, v_id)
        self.log.info("Step 4: Verify object deletion")
        for obj_name in self.obj_names:
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_obj,
                                          bucket_name=self.bucket_name, object_name=obj_name,
                                          get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                          head_error_msg=errmsg.NOT_FOUND_ERR)
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name, expected_objects=[])
        check_list_object_versions(self.s3_ver_obj, self.bucket_name, versions)
        self.log.info("Step 5: Sleep for GC minimum wait time")
        time.sleep(DEL_CFG["gc_min_wait_time"])
        self.log.info("Step 6: Verify space reclaimed")
        # NOTE: we can compare exact bytecount after F-71B
        space_reclaimed = poll_cluster_capacity(False, DEL_CFG["space_reclaim_retry_time"],
                                                DEL_CFG["space_reclaim_max_retries"],
                                                initial_capacity=used_capacity1)
        assert_utils.assert_true(space_reclaimed, "Space not reclaimed.")
        self.log.info("ENDED: Test object deletion with GC in a versioning enabled bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-44828")
    def test_object_overwrite_versioning_enabled_bucket_44828(self):
        """
        Test object overwrite with GC in a versioning enabled bucket.
        """
        self.log.info("STARTED: Test object overwrite with GC in a versioning enabled bucket")
        versions = {}
        self.log.info("Step 1: Upload objects")
        for obj_name, fpath in zip(self.obj_names, self.fixed_size_fpaths):
            upload_version(self.s3_test_obj, self.bucket_name, obj_name, fpath, versions,
                           is_unversioned=True)
        total_uploaded_file_size = self.total_fixed_file_size
        self.log.info("Step 2: Enable bucket versioning")
        res = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 3: Upload new versions")
        new_versions_file_size = 0
        for obj_name, fpath in zip(self.obj_names, self.upload_paths):
            create_random_file(fpath, DEL_CFG["random_obj_size"]["min"],
                               DEL_CFG["random_obj_size"]["max"])
            upload_version(self.s3_test_obj, self.bucket_name, obj_name, fpath, versions)
            new_versions_file_size += os.path.getsize(fpath)
        total_uploaded_file_size += new_versions_file_size
        used_capacity1 = get_cortx_rgw_bytecount()['healthy']
        self.log.info("Initial CORTX capacity: %s", used_capacity1)
        self.log.info("Step 4: Suspend bucket versioning")
        res = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                    status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 5: Overwrite null version with random size")
        total_overwrite_file_size = new_versions_file_size
        for obj_name, fpath in zip(self.obj_names, self.upload_paths):
            create_random_file(fpath, DEL_CFG["random_obj_size"]["min"],
                               DEL_CFG["random_obj_size"]["max"])
            upload_version(self.s3_test_obj, self.bucket_name, obj_name, fpath, versions,
                           chk_null_version=True)
            total_overwrite_file_size += os.path.getsize(fpath)
        self.log.info("Step 6: Sleep for GC minimum wait time")
        time.sleep(DEL_CFG["gc_min_wait_time"])
        self.log.info("Step 7: Verify space reclaimed")
        # NOTE: we can compare exact bytecount after F-71B
        chk_increase = total_uploaded_file_size <= total_overwrite_file_size
        space_reclaimed = poll_cluster_capacity(chk_increase, DEL_CFG["space_reclaim_retry_time"],
                                                DEL_CFG["space_reclaim_max_retries"],
                                                initial_capacity=used_capacity1)
        assert_utils.assert_true(space_reclaimed, "Space not reclaimed.")
        self.log.info("Step 8: Verify object overwrite")
        for obj_name, fpath in zip(self.obj_names, self.upload_paths):
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_obj,
                                          bucket_name=self.bucket_name, object_name=obj_name,
                                          etag=versions[obj_name]["versions"]["null"])
            download_and_check(self.s3_test_obj, self.bucket_name, obj_name,
                               file_path=fpath, download_path=self.download_path)
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=self.obj_names)
        check_list_object_versions(self.s3_ver_obj, self.bucket_name, versions)
        self.log.info("ENDED: Test object overwrite with GC in a versioning enabled bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-44830")
    def test_object_deletion_versioning_suspended_bucket_44830(self):
        """
        Test object deletion with GC in a versioning suspended bucket.
        """
        self.log.info("STARTED: Test object deletion with GC in a versioning suspended bucket")
        versions = {}
        self.log.info("Step 1: Upload objects")
        for obj_name, fpath in zip(self.obj_names, self.fixed_size_fpaths):
            upload_version(self.s3_test_obj, self.bucket_name, obj_name, fpath, versions,
                           is_unversioned=True)
        used_capacity1 = get_cortx_rgw_bytecount()['healthy']
        self.log.info("Initial CORTX capacity: %s", used_capacity1)
        self.log.info("Step 2: Suspend bucket versioning")
        res = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                    status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 3: Delete objects wit/without version id by random selection")
        for obj_name in self.obj_names:
            with_vid = random.choice([True, False]) #nosec
            if with_vid:
                v_id = versions[obj_name]["is_latest"]
                delete_version(self.s3_test_obj, self.s3_ver_obj, self.bucket_name,
                               obj_name, versions, v_id)
            else:
                delete_version(self.s3_test_obj, self.s3_ver_obj, self.bucket_name,
                               obj_name, versions)
        self.log.info("Step 4: Verify object deletion")
        for obj_name in self.obj_names:
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_obj,
                                          bucket_name=self.bucket_name, object_name=obj_name,
                                          get_error_msg=errmsg.NO_SUCH_KEY_ERR,
                                          head_error_msg=errmsg.NOT_FOUND_ERR)
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name, expected_objects=[])
        check_list_object_versions(self.s3_ver_obj, self.bucket_name, versions)
        self.log.info("Step 5: Sleep for GC minimum wait time")
        time.sleep(DEL_CFG["gc_min_wait_time"])
        self.log.info("Step 6: Verify space reclaimed")
        # NOTE: we can compare exact bytecount after F-71B
        space_reclaimed = poll_cluster_capacity(False, DEL_CFG["space_reclaim_retry_time"],
                                                DEL_CFG["space_reclaim_max_retries"],
                                                initial_capacity=used_capacity1)
        assert_utils.assert_true(space_reclaimed, "Space not reclaimed.")
        self.log.info("ENDED: Test object deletion with GC in a versioning suspended bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-44832")
    def test_object_overwrite_versioning_suspended_bucket_44832(self):
        """
        Test object overwrite with GC in a versioned suspended bucket.
        """
        self.log.info("STARTED: Test object overwrite with GC in a versioning suspended bucket")
        versions = {}
        self.log.info("Step 1: Upload objects")
        for obj_name, fpath in zip(self.obj_names, self.fixed_size_fpaths):
            upload_version(self.s3_test_obj, self.bucket_name, obj_name, fpath, versions,
                           is_unversioned=True)
        self.log.info("Step 2: Suspend bucket versioning")
        res = self.s3_ver_obj.put_bucket_versioning(bucket_name=self.bucket_name,
                                                    status="Suspended")
        assert_utils.assert_true(res[0], res[1])
        used_capacity1 = get_cortx_rgw_bytecount()['healthy']
        self.log.info("Initial CORTX capacity: %s", used_capacity1)
        self.log.info("Step 3: Overwrite null version with random size")
        total_overwrite_file_size = 0
        for obj_name, fpath in zip(self.obj_names, self.upload_paths):
            create_random_file(fpath, DEL_CFG["random_obj_size"]["min"],
                               DEL_CFG["random_obj_size"]["max"])
            upload_version(self.s3_test_obj, self.bucket_name, obj_name, fpath, versions,
                           chk_null_version=True)
            total_overwrite_file_size += os.path.getsize(fpath)
        self.log.info("Step 4: Sleep for GC minimum wait time")
        time.sleep(DEL_CFG["gc_min_wait_time"])
        self.log.info("Step 5: Verify space reclaimed")
        # NOTE: we can compare exact bytecount after F-71B
        chk_increase = self.total_fixed_file_size <= total_overwrite_file_size
        space_reclaimed = poll_cluster_capacity(chk_increase, DEL_CFG["space_reclaim_retry_time"],
                                                DEL_CFG["space_reclaim_max_retries"],
                                                initial_capacity=used_capacity1)
        assert_utils.assert_true(space_reclaimed, "Space not reclaimed.")
        self.log.info("Step 6: Verify object overwrite")
        for obj_name, fpath in zip(self.obj_names, self.upload_paths):
            check_get_head_object_version(self.s3_test_obj, self.s3_ver_obj,
                                          bucket_name=self.bucket_name, object_name=obj_name,
                                          etag=versions[obj_name]["versions"]["null"])
            download_and_check(self.s3_test_obj, self.bucket_name, obj_name,
                               file_path=fpath, download_path=self.download_path)
        check_list_objects(self.s3_test_obj, bucket_name=self.bucket_name,
                           expected_objects=self.obj_names)
        check_list_object_versions(self.s3_ver_obj, self.bucket_name, versions)
        self.log.info("ENDED: Test object overwrite with GC in a versioning suspended bucket")
