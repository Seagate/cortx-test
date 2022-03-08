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
from commons import constants as const
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
        # To - create s3 account for lc
        cls.log = logging.getLogger(__name__)
        cls.s3_test_obj = S3TestLib()
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

    def initiate_multipart(self, bucket_name, object_name):
        """
        This initialises multipart and returns mpuID
        """
        self.log.info("Initiating multipart upload")
        res = self.s3_mpu_test_obj.create_multipart_upload(bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        return mpu_id

    @staticmethod
    def create_file_mpu(multipart_obj_size: int = None, object_path: str = None):
        """
         Create file of given size and get the aligned size parts
        :param multipart_obj_size: Size of object need to be uploaded.
        :param object_path: path of the file
        :return: etag string.
        """
        multipart_obj_path = object_path
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        return create_file(multipart_obj_path, multipart_obj_size)

    def compare_checksums(self, upload_checksum, download_checksum):
        """
        Comapres checksums
        param: upload_checksum: upload checksum
        param: download_checksum: download_checksum
        """
        self.log.info("Compare ETag of uploaded and downloaded object ")
        self.log.info("ETags: upload: %s, download: %s", upload_checksum, download_checksum)
        assert_utils.assert_equal(upload_checksum, download_checksum,
                                  f"Failed to match ETag: {upload_checksum}, {download_checksum}")
        self.log.info("Matched ETag: %s, %s", upload_checksum, download_checksum)

    def multiprocess_uploads(self, mpu_id, all_parts,
                             parts: tuple = None):
        """
        uploads multipart
        """
        self.log.info("Creating s3_client session")
        client_instance = S3MultipartTestLib()
        self.log.info("uploading parts in client session")
        response = client_instance.upload_parts_parallel(mpu_id, self.bucket_name,
                                                         self.object_name,
                                                         parts=parts)
        # response = self.multipart  # To - check field content_md5
        all_parts.append(response[1])
        return all_parts

    def get_obj_compare_checksums(self, bucket_name: str = None,
                                  object_name: str = None, upload_checksum: str = None):
        """
        Downloads object and compares checksums
        """
        self.log.info("Get the uploaded object")
        status, res = self.s3_test_obj.get_object(bucket_name, object_name)
        assert_utils.assert_true(status, res)
        get_etag = res['ETag']
        self.log.info("Uploaded ETag is %s", upload_checksum)
        self.log.info("get object ETag is %s", res["ETag"])
        self.compare_checksums(upload_checksum, get_etag)

    def list_parts_completempu(self, mpu_id, bucket_name, **kwargs,):
        """
        Lists parts and completes multipart
        """
        obj_name = kwargs.get("object_name")
        all_parts = kwargs.get("parts_list")
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, bucket_name, obj_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Complete the multipart upload")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(
                mpu_id, all_parts, bucket_name, obj_name)
        except CTException as error:
            self.log.error(error)
            self.log.info("Failed to complete the multipart")
        return resp

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
        s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        self.log.info("start s3 IO's")
        s3_background_io.start(log_prefix="TEST-28532_s3bench_ios", duration="0h32m")
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        # To - Get aligned and unaligned  parts
        uploaded_parts = get_precalculated_parts(self.mp_obj_path, mp_config["part_sizes"],
                                                 chunk_size=mp_config["chunk_size"])
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
        wrong_json = mp_config["wrong_json_file"]
        self.log.info("Created wrong json for input as multipart-upload %s", wrong_json)
        self.log.info("Complete the multipart with input of wrong json/etag")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(mpu_id, wrong_json,
                                                                  self.bucket_name,
                                                                  self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            if const.S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
                assert_utils.assert_equal(mp_config["error_msg_rgw"],
                                          error.message, error.message)
            else:
                assert_utils.assert_equal(mp_config["error_msg_cortx"], error.message,
                                          error.message)
            self.log.info("Failed to complete the multipart with input of wrong json/etag")
        # DO completeMultipartUpload with correct part details after 30 mins to check
        # background producer does not clean up object due to
        # failure on wrong json in completeMultipartUplaod
        self.log.info("wait for 30 mins to confirm object is not cleared because of wrong json")
        time.sleep(30*60)
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(mpu_id,
                                                                  sorted_part_list,
                                                                  self.bucket_name,
                                                                  self.object_name)
            assert_utils.assert_true(resp[0], resp[1])
            # TO: Check above if parts is sequential or random order
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_equal(mp_config["error_msg"], error.message, error.message)
            self.log.info(
                "Failed to complete the multipart upload after 30 mins of failure mpu with wrong "
                "json ")
        self.get_obj_compare_checksums(self.bucket_name, self.object_name, resp[1]["ETag"])
        self.log.info("Stop and validate parallel S3 IOs")
        s3_background_io.stop()
        s3_background_io.cleanup()
        self.log.info("ENDED: Test Multipart upload with invalid json input")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28538')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28538(self):
        """
        This test is for uploading skipping part upload between first and last part
        Initiate multipart upload, upload parts, List parts, completeMultipartUpload
        """
        mp_config = MPART_CFG["test_28538"]
        s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        self.log.info("STARTED: Test Multipart upload with 2 part details")
        self.log.info("start s3 IO's")
        s3_background_io.start(log_prefix="TEST-28538_s3bench_ios", duration="0h1m")
        # Initiate multipart upload
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        self.log.info(" Uploading parts")
        parts = get_precalculated_parts(self.mp_obj_path, mp_config["part_sizes"],
                                        chunk_size=mp_config["chunk_size"])
        lis = list(parts.keys())
        self.log.info("parts after upload multipart are ")
        parts[10000] = parts.pop(lis[0])
        parts[1] = parts.pop(lis[1])
        uploaded_parts = self.s3_mpu_test_obj.upload_parts_sequential(
            upload_id=mpu_id, bucket_name=self.bucket_name, object_name=self.object_name,
            parts=parts)
        # To-check field content_md5
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info(" Complete the multipart with first and last part upload")
        uploaded_parts[1].reverse()
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(mpu_id, uploaded_parts[1],
                                                                  self.bucket_name,
                                                                  self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            if const.S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
                assert_utils.assert_equal("An error occurred (InvalidPart) when calling the "
                                          "CompleteMultipartUpload operation: Unknown",
                                          error.message, error.message)
            else:
                assert_utils.assert_equal(mp_config["error_msg"], error.message, error.message)
            self.log.info("Failed to complete the multipart with incomplete part details ")
        self.log.info("Aborting multipart uploads")
        self.s3_mpu_test_obj.abort_multipart_upload(self.bucket_name,
                                                    self.object_name, mpu_id)
        self.log.info("Stop and validate parallel S3 IOs")
        s3_background_io.stop()
        s3_background_io.cleanup()
        self.log.info("ENDED: Test upload part number 1 and 10000 only")

    @pytest.mark.tags('TEST-28539')
    @pytest.mark.s3_ops
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28539(self):
        """
        This test is for simple upload of an object followed by multipart upload of an object
        Upload 150M object
        """
        mp_config = MPART_CFG["test_28539"]
        s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        self.log.info("STARTED: test Simple upload followed by Multipart upload of an object ")
        self.log.info("start s3 IO's")
        s3_background_io.start(log_prefix="TEST-28539_s3bench_ios", duration="0h2m")
        self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        status, put_etag = self.s3_test_obj.put_object(self.bucket_name, self.object_name,
                                                       self.mp_obj_path)
        assert_utils.assert_true(status, put_etag)
        self.log.info("Put object ETag: %s", put_etag)
        parts = get_precalculated_parts(self.mp_obj_path, mp_config["part_sizes"],
                                        chunk_size=mp_config["chunk_size"])
        keys = list(parts.keys())
        random.shuffle(keys)
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        self.log.info("Uploading parts")
        status, new_parts = self.s3_mpu_test_obj.upload_parts_sequential(mpu_id, self.bucket_name,
                                                                         self.object_name,
                                                                         parts=parts)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        self.log.info("Complete the multipart upload")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(
                    mpu_id, sorted_part_list, self.bucket_name, self.object_name)
            assert_utils.assert_true(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            self.log.info("Failed to complete the multipart")
        self.get_obj_compare_checksums(self.bucket_name, self.object_name, resp[1]["ETag"])
        self.log.info("Stop and validate parallel S3 IOs")
        s3_background_io.stop()
        s3_background_io.cleanup()
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
        mp_config = MPART_CFG["test_28540"]
        mp_config1 = MPART_CFG["test_28538"]
        s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        s3_background_io.start(log_prefix="TEST-28540_s3bench_ios", duration="0h1m")
        # Initiate multipart upload with 2 parts
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        uploaded_parts = get_precalculated_parts(self.mp_obj_path, mp_config1["part_sizes"],
                                                 chunk_size=mp_config1["chunk_size"])
        keys = list(uploaded_parts.keys())
        random.shuffle(keys)
        status, new_parts = self.s3_mpu_test_obj.upload_parts_sequential(mpu_id, self.bucket_name,
                                                                         self.object_name,
                                                                         parts=uploaded_parts)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        self.log.info("Complete the multipart upload with 2 parts")
        try:
            resp = self.s3_mpu_test_obj.complete_multipart_upload(
                mpu_id, sorted_part_list, self.bucket_name, self.object_name)
            assert_utils.assert_true(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            self.log.info("Failed to complete the multipart with 2 parts")
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        uploaded_parts = get_precalculated_parts(self.mp_obj_path, mp_config["part_sizes"],
                                                 chunk_size=mp_config["chunk_size"])
        status, new_parts = self.s3_mpu_test_obj.upload_parts_sequential(mpu_id, self.bucket_name,
                                                                         self.object_name,
                                                                         parts=uploaded_parts)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        self.log.info("Complete the multipart upload with 3 parts")
        try:
            resp2 = self.s3_mpu_test_obj.complete_multipart_upload(
                mpu_id, sorted_part_list, self.bucket_name, self.object_name)
            assert_utils.assert_true(resp2[0], resp2[1])
        except CTException as error:
            self.log.error(error)
            self.log.info("Failed to complete the multipart")
        self.get_obj_compare_checksums(self.bucket_name, self.object_name, resp2[1]["ETag"])
        self.log.info("Stop and validate parallel S3 IOs")
        s3_background_io.stop()
        s3_background_io.cleanup()
        self.log.info("ENDED: Test multipart followed by multipart upload of an object")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28537')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28537(self):
        """
        This test is for initiating 2000 multipart uploads and listing them twice
        """
        mp_config = MPART_CFG["test_28537"]
        s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        self.log.info("STARTED: test to upload and list 2000 multipart uploads")
        self.log.info("start s3 IO's")
        s3_background_io.start(log_prefix="TEST-28537_s3bench_ios", duration="0h2m")
        self.log.info("Initiating multipart uploads")
        mpu_ids1 = []
        all_mpuids = []
        for i in range(100):
            res1 = self.s3_mpu_test_obj.create_multipart_upload(self.bucket_name,
                                                                self.object_name)
            assert_utils.assert_true(res1[0], res1[1])
            mpu_id = res1[1]["UploadId"]
            self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
            mpu_ids1.append(mpu_id)
            all_mpuids.append(mpu_id)
        # Upload 1900 mpu of various objects
        mpu_ids2 = []
        for j in range(mp_config["multipart_uploads"]):
            res2 = self.s3_mpu_test_obj.create_multipart_upload(self.bucket_name,
                                                                self.object_name + str(j))
            assert_utils.assert_true(res2[0], res2[1])
            mpu_id = res2[1]["UploadId"]
            self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
            mpu_ids2.append(mpu_id)
            all_mpuids.append(mpu_id)
        self.log.info("list multipart uploads")
        response = self.s3_mpu_test_obj.list_multipart_uploads(self.bucket_name)

        self.log.info("Next key marker is %s and list is truncated %s",
                      response[1]['NextKeyMarker'], response[1]['IsTruncated'])
        mpuids_fromlist = []
        for j in response[1]["Uploads"]:
            mpuids_fromlist.append(j['UploadId'])
        self.log.info("list 2 multipart uploads")
        response2 = self.s3_mpu_test_obj.list_multipart_uploads_with_keymarker(
            self.bucket_name, response[1]['NextKeyMarker'])
        mpuids_fromlist1 = []
        for k in response2["Uploads"]:
            mpuids_fromlist1.append(k["UploadId"])
        total_mpuids_listed = [*mpuids_fromlist, *mpuids_fromlist1]
        assert_utils.assert_list_items(all_mpuids, total_mpuids_listed)
        self.log.info("Aborting multipart uploads")
        for i in range(100):
            mpu_id = mpu_ids1[i]
            res = self.s3_mpu_test_obj.abort_multipart_upload(self.bucket_name,
                                                              self.object_name, mpu_id)
            assert_utils.assert_true(res[0], res[1])
        for i in range(mp_config['multipart_uploads']):
            mpu_id = mpu_ids2[i]
            res = self.s3_mpu_test_obj.abort_multipart_upload(self.bucket_name,
                                                              self.object_name + str(i), mpu_id)
            assert_utils.assert_true(res[0], res[1])
        self.log.info("Aborted multipart upload")

        self.log.info("Stop and validate parallel S3 IOs")
        s3_background_io.stop()
        s3_background_io.cleanup()

        self.log.info("ENDED: Test Multipart upload with 2000 uploads")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28534')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28534(self):
        """
        This is for uploading multipart from 10 different sessions
        """
        self.log.info(
            "STARTED: test for an object multipart from 10 different sessions of same client")
        mp_config = MPART_CFG['test_28534']
        s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        self.log.info("start s3 IO's")
        s3_background_io.start(log_prefix="TEST-28534_s3bench_ios", duration="0h1m")
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        parts = get_precalculated_parts(self.mp_obj_path, mp_config["part_sizes"],
                                        chunk_size=mp_config["chunk_size"])
        listp = []
        for i in parts:
            listp.append(parts[i])
        all_parts = []
        pool = multiprocessing.Pool(processes=10)
        all_parts = pool.starmap(self.multiprocess_uploads,
                                 [(mpu_id, all_parts, dict(list(parts.items())[0:2])),
                                  (mpu_id, all_parts, dict(list(parts.items())[2:4])),
                                  (mpu_id, all_parts, dict(list(parts.items())[4:6])),
                                  (mpu_id, all_parts, dict(list(parts.items())[6:7])),
                                  (mpu_id, all_parts, dict(list(parts.items())[12:13])),
                                  (mpu_id, all_parts, dict(list(parts.items())[7:9])),
                                  (mpu_id, all_parts, dict(list(parts.items())[9:11])),
                                  (mpu_id, all_parts, dict(list(parts.items())[11:12])),
                                  (mpu_id, all_parts, dict(list(parts.items())[13:15])),
                                  (mpu_id, all_parts, dict(list(parts.items())[15:]))])
        new_list = []
        part_list = []
        for listed_parts in all_parts:
            for partlst in listed_parts:
                part_list.append([{'PartNumber': part_entry['PartNumber'],
                                   'ETag': part_entry['ETag']} for part_entry in partlst['Parts']])
        for lst_parts in part_list:
            for prt_entry in lst_parts:
                if prt_entry not in new_list:
                    new_list.append(prt_entry)
        sorted_lst = sorted(new_list, key=lambda d: d['PartNumber'])
        res = self.list_parts_completempu(mpu_id, self.bucket_name,
                                          object_name=self.object_name,
                                          parts_list=sorted_lst)
        self.get_obj_compare_checksums(self.bucket_name, self.object_name, res[1]["ETag"])
        self.log.info("Stop and validate parallel S3 IOs")
        s3_background_io.stop()
        s3_background_io.cleanup()
        self.log.info("ENDED: Test multipart upload of object from 10 different client sessions")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28535')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28535(self):
        """
        ths test is for restarting s3server
        """
        host_ip = CMN_CFG["nodes"][0]["hostname"]
        uname = CMN_CFG["nodes"][0]["username"]
        passwd = CMN_CFG["nodes"][0]["password"]
        s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        self.log.info(
            "STARTED: test for an object multipart from 10 different sessions of same client")
        mp_config = MPART_CFG['test_28535']
        self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        self.log.info("start s3 IO's")
        s3_background_io.start(log_prefix="TEST-28535_s3bench_ios", duration="0h2m")
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        uploaded_parts = get_precalculated_parts(self.mp_obj_path, mp_config["part_sizes"],
                                                 chunk_size=mp_config["chunk_size"])
        all_parts = []
        pool = multiprocessing.Pool(processes=8)
        all_parts = pool.starmap(self.multiprocess_uploads,
                                 [(mpu_id, all_parts, dict(list(uploaded_parts.items())[0:2])),
                                  (mpu_id, all_parts, dict(list(uploaded_parts.items())[2:4])),
                                  (mpu_id, all_parts, dict(list(uploaded_parts.items())[4:6])),
                                  (mpu_id, all_parts, dict(list(uploaded_parts.items())[6:7])),
                                  (mpu_id, all_parts, dict(list(uploaded_parts.items())[11:13])),
                                  (mpu_id, all_parts, dict(list(uploaded_parts.items())[7:9])),
                                  (mpu_id, all_parts, dict(list(uploaded_parts.items())[9:11])),
                                  (mpu_id, all_parts, dict(list(uploaded_parts.items())[13:14])),
                                  (mpu_id, all_parts, dict(list(uploaded_parts.items())[14:15]))
                                  ])
        new_list = []
        new_lst = []
        proc_4 = multiprocessing.Process(target=self.multiprocess_uploads,
                                         args=(mpu_id, all_parts,
                                               dict(list(uploaded_parts.items())[15:16])))
        proc_5 = multiprocessing.Process(target=self.multiprocess_uploads,
                                         args=(mpu_id, all_parts,
                                               dict(list(uploaded_parts.items())[16:])))
        proc_4.start()
        proc_5.start()
        self.log.info("Restart s3server instances")
        resp = S3H_OBJ.restart_s3server_processes(host_ip, uname, passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Restart s3server instances")
        resp = S3H_OBJ.restart_s3server_processes(host_ip, uname, passwd)
        assert_utils.assert_true(resp[0], resp[1])
        proc_4.join()
        proc_5.join()
        for k in all_parts:
            for j in k:
                new_list.append(j)
        for k in new_list:
            for j in k:
                new_lst.append(j)
        sorted_lst = sorted(new_lst, key=lambda d: d['PartNumber'])
        self.log.info("length of sorted list is %d", len(sorted_lst))
        self.list_parts_completempu(mpu_id, self.bucket_name,
                                    object_name=self.object_name,
                                    parts_list=sorted_lst)
        self.log.info("Stop and validate parallel S3 IOs")
        s3_background_io.stop()
        s3_background_io.cleanup()
        self.log.info("ENDED: Test multipart upload of object from 5 different client sessions "
                      "and restarting s3server randomly")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28530')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28530(self):
        """
        This is for listing parts after completion of multipart upload
        """
        self.log.info("STARTED: List parts after completion of multipart upload of an object ")
        s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        mp_config = MPART_CFG["test_28530"]
        self.log.info("start s3 IO's")
        s3_background_io.start(log_prefix="TEST-28530_s3bench_ios", duration="0h1m")
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        uploaded_parts = get_precalculated_parts(self.mp_obj_path, mp_config["part_sizes"],
                                                 chunk_size=mp_config["chunk_size"])
        keys = list(uploaded_parts.keys())
        random.shuffle(keys)
        status, new_parts = self.s3_mpu_test_obj.upload_parts_sequential(mpu_id, self.bucket_name,
                                                                         self.object_name,
                                                                         parts=uploaded_parts)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        res = self.list_parts_completempu(mpu_id, self.bucket_name,
                                          object_name=self.object_name,
                                          parts_list=sorted_part_list)
        self.log.info("Listing parts of multipart upload upon completion of multipart upload")
        self.get_obj_compare_checksums(self.bucket_name, self.object_name, res[1]["ETag"])
        try:
            resp = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_equal(mp_config["error_msg"], error.message, error.message)
            self.log.info("Failed to list parts after the completion of the multipart upload")
        self.log.info("list parts can't be done after completion of multipart upload")
        self.log.info("Stop and validate parallel S3 IOs")
        s3_background_io.stop()
        s3_background_io.cleanup()
        self.log.info("ENDED: Test List multipart followed by completion of multipart upload")

    # @pytest.mark.skip(reason="need to execute on hw as vm has limited space")
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28526')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28526(self):
        """
        This test is for uploading 5TB max size object using multipart upload
        """
        # TODO FIX
        self.log.info("STARTED: Multipart upload of 5TB object ")
        mp_config = MPART_CFG["test_28526"]
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        status, output = self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        if status:
            self.file_path = self.mp_obj_path
            self.log.info(output)
        status, mpu_upload = self.s3_mpu_test_obj.upload_precalculated_parts(
            mpu_id, self.bucket_name, self.object_name, multipart_obj_path=self.file_path,
            part_sizes=MPART_CFG["test_28526"]["part_sizes"],
            chunk_size=MPART_CFG["test_28526"]["chunk_size"])
        assert_utils.assert_true(status, f"Failed to upload parts: {mpu_upload}")
        sorted_part_list = sorted(mpu_upload["uploaded_parts"], key=lambda x: x['PartNumber'])
        res = self.list_parts_completempu(mpu_id, self.bucket_name,
                                          object_name=self.object_name,
                                          parts_list=sorted_part_list)
        self.get_obj_compare_checksums(self.bucket_name, self.object_name, res[1]["ETag"])
        self.log.info("ENDED: Test multipart upload of 5TB object")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-28528')
    @CTFailOn(error_handler)
    def test_multipart_upload_test_28528(self):
        """
        This test is for multipart upload of an object having 10000 parts
        """
        self.log.info("STARTED: List parts after completion of Multipart upload of an object ")
        mp_config = MPART_CFG["test_28528"]
        self.create_file_mpu(mp_config["file_size"], self.mp_obj_path)
        self.log.info("start s3 IO's")
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        self.log.info("calculating parts...")
        status, mpu_upload = self.s3_mpu_test_obj.upload_precalculated_parts(
            mpu_id, self.bucket_name, self.object_name, multipart_obj_path=self.mp_obj_path,
            part_sizes=mp_config["part_sizes"],
            chunk_size=mp_config["chunk_size"])
        assert_utils.assert_true(status, f"Failed to upload parts: {mpu_upload}")
        sorted_part_list = sorted(mpu_upload["uploaded_parts"], key=lambda x: x['PartNumber'])
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mpu_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Part Number marker is %s and list is truncated %s",
                      res[1]['PartNumberMarker'],
                      res[1]['IsTruncated'])
        part_num_marker = res[1]['PartNumberMarker']
        is_truncated = res[1]['IsTruncated']
        all_parts = list()
        all_parts.append(res[1]["Parts"])
        while is_truncated:
            response = self.s3_mpu_test_obj.list_parts(
                mpu_id, self.bucket_name, self.object_name, PartNumberMarker=part_num_marker)
            assert_utils.assert_true(response[0], response[1])
            part_num_marker = res[1]['PartNumberMarker']
            is_truncated = response[1]['IsTruncated']
            all_parts.append(res[1]["Parts"])
        self.log.info("Listed parts of multipart upload: %s", len(all_parts))
        assert_utils.assert_equal(len(all_parts), 10000, "Failed to list 10000 parts.")
        self.log.info("Complete the multipart upload")
        resp = self.s3_mpu_test_obj.complete_multipart_upload(
                mpu_id, sorted_part_list, self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], "Failed to complete the 10000 multipart")
        self.get_obj_compare_checksums(self.bucket_name, self.object_name, resp[1]["ETag"])
        self.log.info("Stop and validate parallel S3 IOs")
        self.log.info("ENDED: Test List multipart with 10000 parts")
