#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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

"""Multipart Upload test module."""

import logging
import random
import time
import multiprocessing
import os
import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.system_utils import create_file, remove_file, path_exists
from commons.utils.s3_utils import get_precalculated_parts
from commons.utils.system_utils import backup_or_restore_files, make_dirs, remove_dirs
from commons.utils import assert_utils
from commons.params import TEST_DATA_FOLDER
from config.s3 import MPART_CFG
from libs.s3.s3_common_test_lib import S3BackgroundIO
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_test_lib import S3TestLib
from libs.s3 import S3_CFG, S3H_OBJ, CMN_CFG


class TestMultipartUploadGetPut:
    """Multipart Upload Test Suite."""
    @classmethod
    def setup_class(cls):
        """
        This is called only once before starting any tests in this class
        """
        cls.log = logging.getLogger(__name__)
        cls.s3_test_obj = S3TestLib()
        cls.s3_mpu_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.aws_config_path = []
        cls.aws_config_path.append(S3_CFG["aws_config_path"])
        cls.actions = ["backup", "restore"]
        cls.test_file = "mpu_obj"
        cls.test_file_partcopy = "mpu_partcopy_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestMultipartUploadRedesign")
        cls.mp_obj_path = os.path.join(cls.test_dir_path, cls.test_file)
        cls.mp_obj_path_partcopy = os.path.join(cls.test_dir_path, cls.test_file_partcopy)
        cls.config_backup_path = os.path.join(cls.test_dir_path, "config_backup")
        if not path_exists(cls.test_dir_path):
            make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.downloaded_file = "{}{}".format("get_blackboxs3obj", time.perf_counter_ns())
        cls.downloaded_file_path = os.path.join(
            cls.test_dir_path, cls.downloaded_file)

    @classmethod
    def teardown_class(cls):
        """
        This is called after all tests in this class finished execution
        """
        cls.log.info("STARTED: teardown test suite operations.")
        if path_exists(cls.test_dir_path):
            remove_dirs(cls.test_dir_path)
        cls.log.info("Cleanup test directory: %s", cls.test_dir_path)
        cls.log.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        This is called before each test in this test suite
        """
        self.log.info("STARTED: Setup operations")
        self.random_time = int(time.perf_counter_ns())
        self.bucket_name = "mpu-bkt-{}".format(self.random_time)
        self.object_name = "mpu-obj-{}".format(self.random_time)
        self.mpu_partcopy_bkt = "mpu-partcopy-bkt-{}".format(self.random_time)
        self.mpu_partcopy_obj = "mpu-partcopy-obj-{}".format(self.random_time)

        self.log.info("Taking a backup of aws config file located at %s to %s...",
                      self.aws_config_path, self.config_backup_path)
        resp = backup_or_restore_files(self.actions[0], self.config_backup_path,
                                       self.aws_config_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Taken a backup of aws config file located at %s to %s",
                      self.aws_config_path, self.config_backup_path)
        # create bucket
        self.log.info("Creating a bucket with name : %s", self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        This is called after each test in this test suite
        """
        self.log.info("STARTED: Teardown operations")
        resp = self.s3_test_obj.bucket_list()
        pref_list = [
            each_bucket for each_bucket in resp[1] if each_bucket.startswith("mpu-bkt")]
        if pref_list:
            resp = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Restoring aws config file from %s to %s...",
            self.config_backup_path,
            self.aws_config_path)
        resp = backup_or_restore_files(
            self.actions[1], self.config_backup_path, self.aws_config_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Restored aws config file from %s to %s",
            self.config_backup_path,
            self.aws_config_path)
        self.log.info("Deleting a backup file and directory...")
        if path_exists(self.config_backup_path):
            remove_dirs(self.config_backup_path)
        if path_exists(self.mp_obj_path):
            remove_file(self.mp_obj_path)
        self.log.info("Deleted a backup file and directory")
        self.log.info("ENDED: Teardown operations")

    def create_and_complete_mpu(self, mpu_cfg):
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        uploaded_parts = get_precalculated_parts(self.mp_obj_path, mpu_cfg["part_sizes"],
                                                 chunk_size=mpu_cfg["chunk_size"])
        keys = list(uploaded_parts.keys())
        random.shuffle(keys)
        self.log.info("Uploading parts")
        status, new_parts = self.s3_mpu_test_obj.upload_parts_sequential(mpu_id, self.bucket_name,
                                                                         self.object_name,
                                                                         parts=uploaded_parts)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        self.log.info("Complete the multipart ")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(mpu_id, sorted_part_list,
                                                                  self.bucket_name,
                                                                  self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            self.log.info("Failed to complete the multipart with provided part details")
        upload_etag = resp[1]["ETag"]
        self.log.info("Get the uploaded object")
        status, res = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(status, res)
        get_etag = res['ETag']
        self.log.info("Compare ETags")
        assert_utils.assert_equal(resp[1]["ETag"], get_etag,
                                  f"Failed to match ETag: {upload_etag}, {get_etag}")
        self.log.info("Matched ETag: %s, %s", upload_etag, get_etag)

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32702')
    @CTFailOn(error_handler)
    def test_mpu_upload_partcopy_32702(self):
        """
        This test is for getting object uploaded using multipart UploadPartCopy api
        """
        mp_config = MPART_CFG["test_32702_1"]
        multipart_obj_path = self.mp_obj_path
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        create_file(multipart_obj_path, mp_config["file_size"])
        mp_config_2 = MPART_CFG["test_32702_2"]
        if os.path.exists(self.mp_obj_path_partcopy):
            os.remove(self.mp_obj_path_partcopy)
        create_file(self.mp_obj_path_partcopy, mp_config_2["file_size"])
        self.log.info("STARTED: Test get the object uploaded using MPU UploadPartCopy")
        s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        self.log.info("start s3 IO's")
        s3_background_io.start(log_prefix="TEST-32702_s3bench_ios", duration="0h2m")
        # create and complete MPU for Bucket1/object1
        self.create_and_complete_mpu(mp_config)
        self.log.info("Creating a bucket with name : %s", self.mpu_partcopy_bkt)
        res = self.s3_test_obj.create_bucket(self.mpu_partcopy_bkt)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.mpu_partcopy_bkt, res[1])
        self.log.info("Created a bucket with name : %s", self.mpu_partcopy_bkt)
        mpu_id2 = self.initiate_multipart(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        uploaded_parts2 = get_precalculated_parts(self.mp_obj_path_partcopy,
                                                  mp_config_2["part_sizes"],
                                                  chunk_size=mp_config_2["chunk_size"])
        keys = list(uploaded_parts2.keys())
        uploaded_parts2['3'] = uploaded_parts2.pop('2') # modified the part 2 as part 3
        random.shuffle(keys)
        self.log.info("Uploading parts")
        status, new_parts = self.s3_mpu_test_obj.upload_parts_sequential(mpu_id2,
                                                                         self.mpu_partcopy_bkt,
                                                                         self.mpu_partcopy_obj,
                                                                         parts=uploaded_parts2)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        response = self.s3_mpu_test_obj.upload_part_copy(self.bucket_name/self.object_name,
                                                             self.mpu_partcopy_bkt,
                                                             self.mpu_partcopy_obj,
                                                             part_number=2,
                                                             upload_id=mpu_id2)
        new_parts.append({"PartNumber": 2, "ETag": response["ETag"]})
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id2, self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Complete the multipart")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(mpu_id2, new_parts[1],
                                                                  self.mpu_partcopy_bkt,
                                                                  self.mpu_partcopy_obj)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            self.log.info("Failed to complete the multipart with provided part details ")
        upload_etag2 = resp[1]["ETag"]
        self.log.info("Get the uploaded object (using uploadPartCopy)")
        status, res = self.s3_test_obj.get_object(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(status, res)
        get_etag2 = res['ETag']
        self.log.info("Compare ETags")
        assert_utils.assert_equal(resp[1]["ETag"], get_etag2,
                                  f"Failed to match ETag: {upload_etag2}, {get_etag2}")
        self.log.info("Matched ETag: %s, %s", upload_etag2, get_etag2)

        self.log.info("Stop and validate parallel S3 IOs")
        s3_background_io.stop()
        s3_background_io.cleanup()
        self.log.info("ENDED: Get the object uploaded using MPU UploadPartCopy")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32711')
    @CTFailOn(error_handler)
    def test_mpu_upload_partcopy_32711(self):
        """
        This test is for copying uploaded using multipart UploadPartCopy api to another buckets
        """
        mp_config = MPART_CFG["test_32702_1"]
        multipart_obj_path = self.mp_obj_path
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        create_file(multipart_obj_path, mp_config["file_size"])

        self.log.info("STARTED: Test Copy object created by MPU uploadPartCopy to another bucket")
        s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        self.log.info("start s3 IO's")
        s3_background_io.start(log_prefix="TEST-32711_s3bench_ios", duration="0h2m")
        # create and complete MPU for Bucket1/object1
        self.create_and_complete_mpu(mp_config)
        # upload anotherobject using simple put operation
        self.put_object_name = "mpu-uploadpartcopy-put-obj"
        status, put_etag = self.s3_test_obj.put_object(self.bucket_name, self.put_object_name,
                                                       multipart_obj_path)
        assert_utils.assert_true(status, put_etag)
        # create and complete MPU for Bucket2/object2
        self.log.info("Creating a bucket with name : %s", self.mpu_partcopy_bkt)
        res = self.s3_test_obj.create_bucket(self.mpu_partcopy_bkt)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.mpu_partcopy_bkt, res[1])
        self.log.info("Created a bucket with name : %s", self.mpu_partcopy_bkt)
        mp_config_2 = MPART_CFG["test_32702_2"]
        self.create_file_mpu(mp_config_2["file_size"], self.mp_obj_path_partcopy)
        mpu_id2 = self.initiate_multipart(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        uploaded_parts2 = get_precalculated_parts(self.mp_obj_path_partcopy,
                                                  mp_config_2["part_sizes"],
                                                  chunk_size=mp_config_2["chunk_size"])
        keys = list(uploaded_parts2.keys())
        uploaded_parts2['3'] = uploaded_parts2.pop('2')  # modified the part 2 as part 3
        random.shuffle(keys)
        self.log.info("Uploading parts")
        status, new_parts = self.s3_mpu_test_obj.upload_parts_sequential(mpu_id2,
                                                                         self.mpu_partcopy_bkt,
                                                                         self.mpu_partcopy_obj,
                                                                         parts=uploaded_parts2)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        response = self.s3_mpu_test_obj.upload_part_copy(self.bucket_name / self.object_name,
                                                         self.mpu_partcopy_bkt,
                                                         self.mpu_partcopy_obj,
                                                         part_number=2,
                                                         upload_id=mpu_id2)
        new_parts.append({"PartNumber": 2, "ETag": response["ETag"]})
        response1 = self.s3_mpu_test_obj.upload_part_copy(self.bucket_name / self.put_object_name,
                                                         self.mpu_partcopy_bkt,
                                                         self.mpu_partcopy_obj,
                                                         part_number=4,
                                                         upload_id=mpu_id2)
        new_parts.append({"PartNumber": 4, "ETag": response["ETag"]})
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id2, self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Complete the multipart")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(mpu_id2, new_parts[1],
                                                                  self.mpu_partcopy_bkt,
                                                                  self.mpu_partcopy_obj)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            self.log.info("Failed to complete the multipart with provided part details ")
        upload_etag2 = resp[1]["ETag"]
        self.log.info("Get the uploaded object (using uploadPartCopy)")
        status, res = self.s3_test_obj.get_object(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(status, res)
        get_etag2 = res['ETag']
        self.log.info("Compare ETags")
        assert_utils.assert_equal(resp[1]["ETag"], get_etag2,
                                  f"Failed to match ETag: {upload_etag2}, {get_etag2}")
        self.log.info("Matched ETag: %s, %s", upload_etag2, get_etag2)
        # copy object2 to bucket3 and bucket1
        src_bkt = self.mpu_partcopy_bkt
        dst_bkt = "mp-bkt3-{}".format(perf_counter_ns())
        self.log.info("Creating a bucket with name : %s", dst_bkt)
        resp = self.s3_test_obj.create_bucket(dst_bkt)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], dst_bkt, resp[1])
        self.log.info("Created a bucket with name : %s", dst_bkt)
        self.log.info("Copy object from bucket2 named %s to bucket3 named %s", src_bkt, dst_bkt)
        resp = self.s3_test_obj.copy_object(
            source_bucket=src_bkt, source_object=self.mpu_partcopy_obj, dest_bucket=dst_bkt,
            dest_object=self.mpu_partcopy_obj)
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        self.log.info("Verify copy and source etags match")
        assert_utils.assert_equal(upload_etag2, copy_etag)
        dst_bkt = self.bucket_name
        self.log.info("Copy object from bucket2 named %s to bucket1 named %s", src_bkt, dst_bkt)
        resp = self.s3_test_obj.copy_object(
            source_bucket=src_bkt, source_object=self.mpu_partcopy_obj, dest_bucket=dst_bkt,
            dest_object=self.mpu_partcopy_obj)
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        self.log.info("Verify copy and source etags match")
        assert_utils.assert_equal(upload_etag2, copy_etag)
        self.log.info("Stop and validate parallel S3 IOs")
        s3_background_io.stop()
        s3_background_io.cleanup()
        self.log.info("ENDED: Test Copy object created by MPU uploadPartCopy to another bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32710')
    @CTFailOn(error_handler)
    def test_mpu_upload_partcopy_32710(self):
        """
        This test is for Copy object created recursively by MPU-UploadPartCopy
        """
        mp_config = MPART_CFG["test_32702_1"]
        multipart_obj_path = self.mp_obj_path
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        create_file(multipart_obj_path, mp_config["file_size"])
        mp_config_2 = MPART_CFG["test_32702_2"]
        if os.path.exists(self.mp_obj_path_partcopy):
            os.remove(self.mp_obj_path_partcopy)
        create_file(self.mp_obj_path_partcopy, mp_config_2["file_size"])
        self.log.info("STARTED: Test Multipart upload with invalid json input")
        s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        self.log.info("start s3 IO's")
        s3_background_io.start(log_prefix="TEST-32710_s3bench_ios", duration="0h2m")
        # create and complete MPU for Bucket1/object1
        self.create_and_complete_mpu(mp_config)
        self.log.info("Creating a bucket with name : %s", self.mpu_partcopy_bkt)
        res = self.s3_test_obj.create_bucket(self.mpu_partcopy_bkt)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.mpu_partcopy_bkt, res[1])
        self.log.info("Created a bucket with name : %s", self.mpu_partcopy_bkt)
        mpu_id2 = self.initiate_multipart(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        uploaded_parts2 = get_precalculated_parts(self.mp_obj_path_partcopy,
                                                  mp_config_2["part_sizes"],
                                                  chunk_size=mp_config_2["chunk_size"])
        keys = list(uploaded_parts2.keys())
        uploaded_parts2.pop('2')  #removed part 2 as we are going to uplaod only one part here
        self.log.info("Uploading parts")
        status, new_parts = self.s3_mpu_test_obj.upload_parts_sequential(mpu_id2,
                                                                         self.mpu_partcopy_bkt,
                                                                         self.mpu_partcopy_obj,
                                                                         parts=uploaded_parts2)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        response = self.s3_mpu_test_obj.upload_part_copy(self.bucket_name / self.object_name,
                                                         self.mpu_partcopy_bkt,
                                                         self.mpu_partcopy_obj,
                                                         part_number=2,
                                                         upload_id=mpu_id2)
        new_parts.append({"PartNumber": 2, "ETag": response["ETag"]})
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id2, self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Complete the multipart")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(mpu_id2, new_parts[1],
                                                                  self.mpu_partcopy_bkt,
                                                                  self.mpu_partcopy_obj)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            self.log.info("Failed to complete the multipart with provided part details ")
        self.log.info("Creating a bucket with name : %s", self.mpu_partcopy_bkt)
        res = self.s3_test_obj.create_bucket(self.mpu_partcopy_bkt)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.mpu_partcopy_bkt, res[1])
        self.log.info("Created a bucket with name : %s", self.mpu_partcopy_bkt)
        mpu_partcopy_bkt3 = "mpu-partcopy-bkt3".format(self.random_time)
        mpu_partcopy_obj3 = "mpu-partcopy-obj3".format(self.random_time)
        self.log.info("Creating a bucket with name : %s", mpu_partcopy_bkt3)
        res = self.s3_test_obj.create_bucket(mpu_partcopy_bkt3)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], mpu_partcopy_bkt3, res[1])
        self.log.info("Created a bucket with name : %s", mpu_partcopy_bkt3)
        mpu_id3 = self.initiate_multipart(mpu_partcopy_bkt3, mpu_partcopy_obj3)
        uploaded_parts2 = get_precalculated_parts(self.mp_obj_path_partcopy,
                                                  mp_config_2["part_sizes"],
                                                  chunk_size=mp_config_2["chunk_size"])
        keys = list(uploaded_parts2.keys())
        uploaded_parts2.pop('2')  # removed part 2 as we are going to uplaod only one part here
        self.log.info("Uploading parts")
        status, new_parts = self.s3_mpu_test_obj.upload_parts_sequential(mpu_id3,
                                                                         mpu_partcopy_bkt3,
                                                                         mpu_partcopy_obj3,
                                                                         parts=uploaded_parts2)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        response = self.s3_mpu_test_obj.upload_part_copy(
            self.mpu_partcopy_bkt / self.mpu_partcopy_obj, mpu_partcopy_bkt3,
            mpu_partcopy_obj3, part_number=2, upload_id=mpu_id3)
        new_parts.append({"PartNumber": 2, "ETag": response["ETag"]})
        response = self.s3_mpu_test_obj.upload_part_copy(
            self.bucket_name / self.object_name, mpu_partcopy_bkt3,
            mpu_partcopy_obj3, part_number=3, upload_id=mpu_id3)
        new_parts.append({"PartNumber": 3, "ETag": response["ETag"]})
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id3, mpu_partcopy_bkt3, mpu_partcopy_obj3)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Complete the multipart")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(mpu_id3, new_parts[1],
                                                                  mpu_partcopy_bkt3,
                                                                  mpu_partcopy_obj3)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            self.log.info("Failed to complete the multipart with provided part details ")
        self.log.info("Stop and validate parallel S3 IOs")
        s3_background_io.stop()
        s3_background_io.cleanup()
        self.log.info("ENDED: Test Copy object created  recursively by MPU-UploadPartCopy")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32721')
    @CTFailOn(error_handler)
    def test_32721(self):
        """
        Upload part copy.

        Upload object UploadPartCopy having part sizes within aws part size limits using byte-range.
        """
        self.log.info("STARTED: Upload object UploadPartCopy using byte-range param")
        self.log.info("Step 1: Create bucket1.")
        self.log.info("Step 2: Initiate multipart upload by performing CreateMultipartUpload.")
        self.log.info("Step 3: Upload 10 parts of various sizes and in random order. The uploaded "
                      "parts can have sizes aligned and unaligned with motr unit sizes. Make sure "
                      "the entire object is > 5GB.")
        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        self.log.info("Step 5: Get the part details and perform CompleteMultipartUpload.")
        self.log.info("Step 6: Create bucket 2.")
        self.log.info("Step 7: Initiate multipart upload by performing CreateMultipartUpload2.")
        self.log.info("Step 8: Upload part2 by copying byterange 5MB-5GB from object1 to uploadID2")
        self.log.info("Step 9: Upload part1 by copying entire object1 byterange >5GB to uploadID2.")
        self.log.info("Step 10: Upload part4 by copying byterange <5MB from object1 to uploadID2.")
        self.log.info("Step 11: Upload part3 by normal file upload.")
        self.log.info("Step 12: list the parts uploaded.")
        self.log.info("Step 13: Complete the MPU.")
        self.log.info("Step 14: Check IOs running or not.")
        self.log.info("ENDED: Upload object UploadPartCopy using byte-range param")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32730')
    @CTFailOn(error_handler)
    def test_32730(self):
        """Upload 2 objects parallelly using uploadPartCopy."""
        self.log.info("STARTED: Upload 2 objects parallelly using uploadPartCopy.")
        self.log.info("Step 1: Create bucket1.")
        self.log.info("Step 2: Initiate multipart upload by performing CreateMultipartUpload1.")
        self.log.info("Step 3: Upload 10 parts of various sizes and in random order. The uploaded "
                      "parts can have sizes aligned and unaligned with motr unit sizes. "
                      "Make sure the entire object is > 5GB.")
        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        self.log.info("Step 5: Get the part details and perform CompleteMultipartUpload.")
        self.log.info("Step 6: Create bucket 2.")
        self.log.info("Step 7: Initiate multipart upload by performing CreateMultipartUpload2.")
        self.log.info("Step 8: Initiate multipart upload by performing CreateMultipartUpload3.")
        self.log.info("Step 9: Parallelly upload part1 by copying object1 to both these uploadIDs.")
        self.log.info("Step 10: Perform ListParts prallely on these 2 uploadIDs.")
        self.log.info("Step 11: Complete MPU for both uploadIDs.")
        self.log.info("Step 12: Check IOs running or not.")
        self.log.info("ENDED: Upload 2 objects parallelly using uploadPartCopy.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32734')
    @CTFailOn(error_handler)
    def test_32734(self):
        """Overwrite the failed UploadCopyPart for byte range to successful uploadPartCopy."""
        self.log.info("STARTED: Overwrite the failed UploadCopyPart for byte range to successful.")
        self.log.info("Step 1: Create bucket1.")
        self.log.info("Step 2: Initiate multipart upload by performing CreateMultipartUpload.")
        self.log.info("Step 3: Upload 10 parts of various sizes and in random order. The uploaded "
                      "parts can have sizes aligned and unaligned with motr unit sizes."
                      " Make sure the entire object is > 5GB.")
        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        self.log.info("Step 5: Get the part details and perform CompleteMultipartUpload.")
        self.log.info("Step 6: Create bucket 2.")
        self.log.info("Step 7: Initiate multipart upload by performing CreateMultipartUpload.")
        self.log.info("Step 8: Upload part2 by copying entire object1 byte range(>5GB) to uploadID2.")
        self.log.info("Step 9: Upload part1 by copying byte range less than 5MB from object1 to uploadID2.")
        self.log.info("Step 10: Upload part2 by normal file upload.")
        self.log.info("Step 11: Upload part1 by copying byte range within upload part size limits.")
        self.log.info("Step 12: list the parts uploaded.")
        self.log.info("Step 13: Complete the MPU.")
        self.log.info("Step 14: Check IOs running or not.")
        self.log.info("ENDED: Overwrite the failed UploadCopyPart for byte range to successful.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32734')
    @CTFailOn(error_handler)
    def test_32734(self):
        """Uploading part using UploadPartCopy which is from another account."""
        self.log.info("STARTED: Uploading part using UploadPartCopy which is from another account.")
        self.log.info("Step 1: Create bucket1")
        self.log.info("Step 2: Initiate multipart upload by performing CreateMultipartUpload.")
        self.log.info("Step 3: Upload 10 parts of various sizes and in random order.")
        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        self.log.info("Step 5: Get the part details and perform CompleteMultipartUpload.")
        self.log.info("Step 6: Create bucket 2 in account 2 and have the default settings. Meaning,"
                      " account account 2 does not have read permission on account1’s resources.")
        self.log.info("Step 7: Initiate multipart upload by performing CreateMultipartUpload.")
        self.log.info("Step 8: Upload part 2 by copying entire object 1 to uploadID 2.")
        self.log.info("Step 9: Upload part 1 by using regular file upload.")
        self.log.info("Step 10: Give read permission to account 2 on account 1.")
        self.log.info("Step 11: After that upload part 2 by copying entire object 1.")
        self.log.info("Step 12: list the parts uploaded.")
        self.log.info("Step 13: Complete the MPU.")
        self.log.info("Step 14: Check IOs running or not.")
        self.log.info("ENDED: Uploading part using UploadPartCopy which is from another account.")
