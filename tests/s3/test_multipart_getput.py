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
import time
import pytest
import os

import multiprocessing
from test_copy_object import TestCopyObjects
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import create_file, remove_file, path_exists
from commons.utils.system_utils import get_unaligned_parts, calc_etag
from commons.utils.system_utils import backup_or_restore_files, make_dirs, remove_dirs
from commons.utils import assert_utils

from commons.params import TEST_DATA_FOLDER

from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_common_test_lib import check_cluster_health
from libs.s3 import S3_CFG, S3H_OBJ

s3_copy_obj = TestCopyObjects()

MPART_CFG = read_yaml("config/s3/test_multipart_upload.yaml")[1]  # To - this needs to be checked


class TestMultipartUploadGetPut:
    """Multipart Upload Test Suite."""

    def setup_class(cls):
        """This is called only once before starting any tests in this class
        """

        # To - create s3 account for lc
        cls.log = logging.getLogger(__name__)
        cls.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.s3_mpu_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.aws_config_path = []
        cls.aws_config_path.append(S3_CFG["aws_config_path"])
        cls.actions = ["backup", "restore"]
        cls.test_file = "mpu_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestMultipartUploadRedesign")
        cls.mp_obj_path = os.path.join(cls.test_dir_path, cls.test_file)
        cls.config_backup_path = os.path.join(cls.test_dir_path, "config_backup")

        if not path_exists(cls.test_dir_path):
            make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)

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
        # check health of cluster
        check_cluster_health()

        self.log.info("STARTED: Setup operations")
        self.random_time = int(time.time())
        self.bucket_name = "mpu-bkt-{}".format(self.random_time)
        self.object_name = "mpu-obj-{}".format(self.random_time)
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
        # check health of cluster
        check_cluster_health()
        self.log.info("STARTED: Teardown operations")

        self.log.info("Restoring aws config file from %s to %s...",
                      self.config_backup_path, self.aws_config_path)
        resp = backup_or_restore_files(self.actions[1], self.config_backup_path,
                                       self.aws_config_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Restored aws config file from %s to %s",
                      self.config_backup_path, self.aws_config_path)
        self.log.info("Deleting a backup file and directory...")
        if path_exists(self.config_backup_path):
            remove_dirs(self.config_backup_path)
        if path_exists(self.mp_obj_path):
            remove_file(self.mp_obj_path)
        self.log.info("Deleted a backup file and directory")

        # test cleanup
        self.log.info("Test cleanup")

        self.log.info("Deleting object in a bucket")
        res = self.s3_test_obj.delete_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Deleting Bucket")
        resp = self.s3_mpu_test_obj.delete_bucket(self.bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Deleted Bucket")
        self.log.info("ENDED: Teardown operations")

    def initiate_multipart(self, bucket_name, object_name):
        self.log.info("Initiating multipart upload")
        res = self.s3_mpu_test_obj.create_multipart_upload(bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        return mpu_id

    def create_file_mpu(self, multipart_obj_size: int = None, object_path: str = None):
        """
         Create file of given size and get the aligned size parts
        :param multipart_obj_size: Size of object need to be uploaded.
        :return: etag string.
        """
        multipart_obj_path = object_path
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        create_file(multipart_obj_path, multipart_obj_size)
        etag = calc_etag(multipart_obj_path)
        return etag

    def compare_etags(self, upload_etag, download_etag):
        self.log.info("Compare ETag of uploaded and downloaded object ")
        self.log.info("ETags: upload: %s, download: %s", upload_etag, download_etag)
        assert_utils.assert_equal(upload_etag, download_etag,
                                  f"Failed to match ETag: {upload_etag}, {download_etag}")
        self.log.info("Matched ETag: %s, %s", upload_etag, download_etag)

    def upload_parts_get_etags(self, bucket_name, object_name, mpu_id, parts):
        self.log.info("Uploading parts")
        new_parts = []
        for key in parts:
            response = self.s3_mpu_test_obj.upload_multipart(parts[key], bucket_name,
                                                             object_name, mpu_id,
                                                             key)  # To - check field content_md5
            new_parts.append({"PartNumber": key, "ETag": response[1]["ETag"]})
        return new_parts

    def multiprocess_uploads(self, mpu_id, all_parts,
                             parts: tuple = None, ):
        self.log.info("Creating s3_client instance")
        S3MultipartTestLib()
        self.log.info("uploading parts in client session")
        new_parts = self.upload_parts_get_etags(
            self.bucket_name, self.object_name, mpu_id, parts[0:2])
        all_parts.append(new_parts)

    def get_obj_compare_etags(self, bucket_name, object_name, upload_etag):
        # check downloaded and uploaded objects are identical
        self.log.info("Download the uploaded object")
        status, res = self.s3_test_obj.get_object(bucket_name, object_name)
        assert_utils.assert_true(status, res)
        get_etag = res['ETag']  # To: Check if this param is correct
        self.compare_etags(upload_etag, get_etag)

    def list_parts_completempu(self, mpu_id, mpcfg, bucket_name, object_name, all_parts, etag):
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]), mpcfg["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])

        self.log.info("Complete the multipart upload")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(
                mpu_id, all_parts, bucket_name, object_name)
        except CTException as error:
            self.log.error(error)
            self.log.info("Failed to complete the multipart")

        self.get_obj_compare_etags(self.bucket_name, self.object_name, etag)
        self.log.info("Stop and validate parallel S3 IOs")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28532')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28532(self):
        """
        This test is for providing wrong json file while doing completeUpload of an object
        Initiate multipartUpload, UploadParts, ListParts, give wrong
        json file while doing completeMultipartUpload
        """
        mp_config = MPART_CFG["test_28532"]
        self.log.info("STARTED: Test Multipart upload with invalid json input")

        self.log.info("start s3 IO's")
        s3_copy_obj.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-28532_s3bench_ios", duration="0h4m")

        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)

        upload_etag = self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        # To - Get aligned and unaligned  parts

        parts = get_unaligned_parts(self.mp_obj_path, mp_config["total_parts"],
                                    mp_config["chunk_size"], True)

        self.log.info("Uploading parts")
        # To - Method to upload parts ; check the part no .order is shuffled in get_unaligned parts
        new_parts = self.upload_parts_get_etags(self.bucket_name, self.object_name, mpu_id, parts)

        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]), mp_config["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])

        wrong_json = mp_config["wrong_json"]
        self.log.info("Created wrong json for input as multipart-upload %s", wrong_json)

        self.log.info("Complete the multipart with input of wrong json/etag")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(mpu_id, wrong_json,
                                                                  self.bucket_name,
                                                                  self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_equal(mp_config["error_msg"], error.message, error.message)
            self.log.info("Failed to complete the multipart with input of wrong json/etag")

        # DO completeMultipartUpload with correct part details after 30 mins to check
        # background producer does not clean up object due to
        # failure on wrong json in completeMultipartUplaod
        time.sleep(30*60)
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(mpu_id, parts,
                                                                  self.bucket_name,
                                                                  self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
            # TO: Check above if parts is sequential or random order
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_equal(mp_config["error_msg"], error.message, error.message)
            self.log.info(
                "Failed to complete the multipart upload after 30 mins of failure mpu with wrong "
                "json ")

        self.get_obj_compare_etags(self.bucket_name, self.object_name, upload_etag)
        self.log.info("ENDED: Test Multipart upload with invalid json input")
        self.log.info("Stop and validate parallel S3 IOs")
        s3_copy_obj.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-28532_s3bench_ios")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28538')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28538(self):
        """
        This test is for uploading skipping part upload between first and last part
        Initiate multipart upload, upload parts, List parts, completeMultipartUpload
        """
        mp_config = MPART_CFG["test_28538"]
        self.log.info("STARTED: Test Multipart upload with 2 part details")

        self.log.info("start s3 IO's")
        s3_copy_obj.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-28538_s3bench_ios", duration="0h4m")

        # Initiate multipart upload
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)

        upload_etag = self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        self.log.info(" Uploading parts")   # Upload part number 1 and 10000 only
        # Method to get parts
        parts = get_unaligned_parts(self.mp_obj_path, mp_config["total_parts"],
                                    mp_config["chunk_size"], True)
        # Method to upload parts for 1 and 10000 part number
        new_parts = []
        response1 = self.s3_mpu_test_obj.upload_multipart(parts[1], self.bucket_name,
                                                          self.object_name,
                                                          mpu_id, 10000)
        new_parts.append({"PartNumber": 10000, "ETag": response1[1]["ETag"]})
        response2 = self.s3_mpu_test_obj.upload_multipart(parts[2], self.bucket_name,
                                                          self.object_name,
                                                          mpu_id, 1)   # To-check field content_md5
        new_parts.append({"PartNumber": 1, "ETag": response2[1]["ETag"]})

        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]), mp_config["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])

        self.log.info(" Complete the multipart with first and last part upload")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(mpu_id, new_parts,
                                                                  self.bucket_name,
                                                                  self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_equal(mp_config["error_msg"], error.message, error.message)
            self.log.info("Failed to complete the multipart with incomplete part details ")

        self.log.info("Aborting multipart uploads")
        res = self.s3_mpu_test_obj.abort_multipart_upload(self.bucket_name,
                                                          self.object_name, mpu_id)
        self.log.info("Stop and validate parallel S3 IOs")
        s3_copy_obj.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-28538_s3bench_ios")
        self.log.info("ENDED: Test upload part number 1 and 10000 only")

    @pytest.mark('TEST_28539')
    @pytest.mark.s3_ops
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28539(self):
        """
        This test is for simple upload of an object followed by multipart upload of an object
        Upload 150M object
        """
        mp_config = MPART_CFG["test_28539"]

        self.log.info("STARTED: test Simple upload followed by Multipart upload of an object ")
        self.log.info("start s3 IO's")
        s3_copy_obj.start_stop_validate_parallel_s3ios(
                        ios="Start", log_prefix="TEST-28539_s3bench_ios", duration="0h4m")

        etag = self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)

        status, put_etag = self.s3_test_obj.put_object(self.bucket_name, self.object_name,
                                                       self.mp_obj_path)
        assert_utils.assert_true(status, put_etag)
        self.log.info("Put object ETag: %s", put_etag)

        # split that object into smaller parts :2 parts: 100.1M and 49.9M and do mpu of it
        # chunk size is 55MB
        parts = get_unaligned_parts(self.mp_obj_path, mp_config["total_parts"],
                                    mp_config["chunk_size"], True)
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)

        self.log.info("Uploading parts")
        new_parts = self.upload_parts_get_etags(self.bucket_name, self.object_name, mpu_id, parts)

        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  mp_config["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Complete the multipart upload")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(
                    mpu_id, new_parts, self.bucket_name, self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_equal(mp_config["error_msg"], error.message,  error.message)
            self.log.info("Failed to complete the multipart")

        self.get_obj_compare_etags(self.bucket_name, self.object_name, etag)
        self.log.info("Stop and validate parallel S3 IOs")
        s3_copy_obj.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-28539_s3bench_ios")

        self.log.info("ENDED: Test Simple and Multipart upload of an object")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28540')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28540(self):
        """
        Multipart upload of an object (2 parts) followed by mpu of same object with 3 parts
        """
        self.log.info("STARTED: test Simple upload followed by Multipart upload of an object ")
        self.log.info("start s3 IO's")
        s3_copy_obj.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-28540_s3bench_ios", duration="0h4m")  # check timefor ios

        mp_config = MPART_CFG["test_28540"]

        # Initiate multipart upload with 2 parts
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        etag = self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        parts = get_unaligned_parts(self.mp_obj_path, mp_config["total_parts"],
                                    mp_config["chunk_size"], True)
        new_parts = self.upload_parts_get_etags(self.bucket_name, self.object_name, mpu_id, parts)

        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        # check these config params according to new lib
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  mp_config["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Complete the multipart upload with 2 parts")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(
                mpu_id, new_parts, self.bucket_name, self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_equal(
                mp_config["error_msg"], error.message, error.message)
            self.log.info("Failed to complete the multipart with 2 parts")
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)

        parts = get_unaligned_parts(self.mp_obj_path, mp_config["total_parts2"],
                                    mp_config["chunk_size2"], True)
        new_parts = self.upload_parts_get_etags(self.bucket_name, self.object_name, mpu_id, parts)
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),  mp_config["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Complete the multipart upload with 3 parts")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(
                mpu_id, new_parts, self.bucket_name, self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_equal(mp_config["error_msg"], error.message, error.message)
            self.log.info("Failed to complete the multipart")
        self.get_obj_compare_etags(self.bucket_name, self.object_name, etag)

        self.log.info("Stop and validate parallel S3 IOs")
        s3_copy_obj.start_stop_validate_parallel_s3ios(ios="Stop",
                                                       log_prefix="TEST-28540_s3bench_ios")
        self.log.info("ENDED: Test multipart followed by multipart upload of an object")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28537')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28537(self):
        """
        This test is for initiating 2000 multipart uploads and listing them twice
        """
        mp_config = MPART_CFG["test_28537"]
        self.log.info("STARTED: test to upload and list 2000 multipart uploads")
        self.log.info("start s3 IO's")
        s3_copy_obj.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-28537_s3bench_ios", duration="0h4m")  # check timefor ios

        self.log.info("Initiating multipart uploads")
        mpu_ids1 = []
        # Upload 100 mpu of same object
        for i in range(100):
            res1 = self.s3_mpu_test_obj.create_multipart_upload(self.bucket_name,
                                                                self.object_name + str(i))
            assert_utils.assert_true(res1[0], res1[1])
            mpu_id = res1[1]["UploadId"]
            self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
            mpu_ids1.append(mpu_id)

        # Upload 1900 mpu of various objects
        mpu_ids2 = []
        for j in range(mp_config["multipart_uploads"]):
            res2 = self.s3_mpu_test_obj.create_multipart_upload(self.bucket_name,
                                                                self.object_name + str(j))
            assert_utils.assert_true(res2[0], res2[1])
            mpu_id = res2[1]["UploadId"]
            self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
            mpu_ids2.append(mpu_id)

        # list multipart uploads twice

        self.log.info("list multipart uploads")
        response = self.s3_mpu_test_obj.list_multipart_uploads(self.bucket_name)
        self.log.info("Next key marker is %s and list is trunkated %s", response['NextKeyMarker'],
                      response['IsTruncated'])

        self.log.info("list 2 multipart uploads")
        response2 = self.s3_mpu_test_obj.list_multipart_uploads_with_keymarker(
            self.bucket_name, response['NextKeyMarker'])

        for mpu_id in mpu_ids1:
            assert_utils.assert_in(mpu_id, str(response[1]),
                                   f"mpu ID {mpu_id} is not present in {response[1]}")
        for mpu_id in mpu_ids2:
            assert_utils.assert_in(mpu_id, str(response2[1]),
                                   f"mpu ID {mpu_id} is not present in {response2[1]}")

        self.log.info("Aborting multipart uploads")
        for i in range(100):
            mpu_id = mpu_ids1[i]
            res = self.s3_mpu_test_obj.abort_multipart_upload(self.bucket_name,
                                                              self.object_name + str(i), mpu_id)
            assert_utils.assert_true(res[0], res[1])

        for i in range(mp_config['multipart_uploads']):
            mpu_id = mpu_ids2[i]
            res = self.s3_mpu_test_obj.abort_multipart_upload(self.bucket_name,
                                                              self.object_name + str(i), mpu_id)
            assert_utils.assert_true(res[0], res[1])
        self.log.info("Aborted multipart upload")

        self.log.info("ENDED: Test Multipart upload with 2000 uploads")
        self.log.info("Stop and validate parallel S3 IOs")
        s3_copy_obj.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-28537_s3bench_ios")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28534')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28534(self):
        self.log.info(
            "STARTED: test for an object multipart from 10 different sessions of same client")

        self.log.info("start s3 IO's")
        s3_copy_obj.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-28534_s3bench_ios", duration="0h4m")  # check timefor ios

        mp_config = MPART_CFG['test_28537']
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        etag = self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        # get all the parts
        parts = get_unaligned_parts(self.mp_obj_path, mp_config["total_parts"],
                                    mp_config["chunk_size"], True)
        all_parts = []
        # create 10 client instances
        process_list = []
        p1 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[0:2]))
        p2 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[2:6]))
        p3 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[6]))
        p4 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[22:]))
        p5 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[20]))
        p6 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[7:9]))
        p7 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[9:13]))
        p8 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[13:15]))
        p9 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[15:20]))
        p10 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                              parts[20:22]))
        process_list.append(p1)
        process_list.append(p2)
        process_list.append(p3)
        process_list.append(p4)
        process_list.append(p5)
        process_list.append(p6)
        process_list.append(p9)
        process_list.append(p7)
        process_list.append(p10)
        process_list.append(p8)
        for x in process_list:
            x.start()

        for x in process_list:
            x.join()

        self.list_parts_completempu(mpu_id, mp_config, self.bucket_name, self.object_name,
                                    all_parts, etag)

        s3_copy_obj.start_stop_validate_parallel_s3ios(ios="Stop",
                                                       log_prefix="TEST-28534_s3bench_ios")
        self.log.info("ENDED: Test multipart upload of object from 10 different client sessions")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28535')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_283535(self):
        """
        ths test is for restarting s3server
        """
        host_ip = S3_CFG["nodes"][0]["hostname"]
        uname = S3_CFG["nodes"][0]["username"]
        passwd = S3_CFG["nodes"][0]["password"]

        self.log.info(
            "STARTED: test for an object multipart from 10 different sessions of same client")

        self.log.info("start s3 IO's")
        s3_copy_obj.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-28535_s3bench_ios", duration="0h4m")  # check timefor ios

        mp_config = MPART_CFG['test_28537']
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        etag = self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        # get all the parts
        parts = get_unaligned_parts(self.mp_obj_path, mp_config["total_parts"],
                                    mp_config["chunk_size"], True)
        all_parts = []
        # create 5 client instances
        p1 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[0:2]))
        p2 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[2:6]))
        p3 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[6:20]))
        p4 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[21:]))
        p5 = multiprocessing.Process(target=self.multiprocess_uploads, args=(mpu_id, all_parts,
                                                                             parts[20]))
        p1.start()
        p2.start()
        p3.start()
        self.log.info("Restart s3server instances")
        resp = S3H_OBJ.restart_s3server_processes(host_ip, uname, passwd)
        assert_utils.assert_true(resp[0], resp[1])
        p4.start()
        self.log.info("Restart s3server instances")
        resp = S3H_OBJ.restart_s3server_processes(host_ip, uname, passwd)
        assert_utils.assert_true(resp[0], resp[1])
        p5.start()
        p1.join()
        p2.join()
        p3.join()
        p4.join()
        p5.join()

        self.list_parts_completempu(mpu_id, mp_config, self.bucket_name, self.object_name,
                                    all_parts, etag)

        s3_copy_obj.start_stop_validate_parallel_s3ios(ios="Stop",
                                                       log_prefix="TEST-28535_s3bench_ios")
        self.log.info("ENDED: Test multipart upload of object from 5 different client sessions "
                      "and restarting s3server randomly")
