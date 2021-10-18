#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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

"""Multipart Abort and Copy test module."""

import os
import time
import logging
from multiprocessing import Process
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.s3_utils import calc_etag, get_unaligned_parts
from commons.utils.system_utils import create_file, remove_file, path_exists
from commons.utils.system_utils import backup_or_restore_files, make_dirs, remove_dirs
from commons.utils import assert_utils
from commons.params import TEST_DATA_FOLDER
from config import S3_MPART_CFG
from libs.s3 import S3_CFG
from libs.s3 import S3H_OBJ
from libs.s3.s3_common_test_lib import S3BackgroundIO
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib


class TestMultipartAbortCopy:
    """Multipart Abort and Copy Test Suite."""

    @classmethod
    def setup_class(cls):
        """
         Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.aws_config_path = []
        cls.aws_config_path.append(S3_CFG["aws_config_path"])
        cls.actions = ["backup", "restore"]
        cls.test_file = "mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestMultipartUpload")
        cls.mp_obj_path = os.path.join(cls.test_dir_path, cls.test_file)
        cls.config_backup_path = os.path.join(
            cls.test_dir_path, "config_backup")
        cls.aws_set_cmd = "aws configure set"
        cls.aws_get_cmd = "aws configure get"
        if not path_exists(cls.test_dir_path):
            make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        cls.log.info("STARTED: teardown test suite operations.")
        if path_exists(cls.test_dir_path):
            remove_dirs(cls.test_dir_path)
        cls.log.info("Cleanup test directory: %s", cls.test_dir_path)
        cls.log.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        self.log.info("STARTED: Setup operations")
        self.random_time = int(time.time())
        self.bucket_name = "mp-bkt-{}".format(self.random_time)
        self.object_name = "mp-obj-{}".format(self.random_time)
        self.log.info(
            "Taking a backup of aws config file located at %s to %s...",
            self.aws_config_path, self.config_backup_path)
        resp = backup_or_restore_files(
            self.actions[0], self.config_backup_path, self.aws_config_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Taken a backup of aws config file located at %s to %s",
            self.aws_config_path, self.config_backup_path)

        self.log.info(
            "Creating a bucket with name : %s",
            self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info(
            "Created a bucket with name : %s", self.bucket_name)

        self.log.info("Setting up S3 background IO")
        self.s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        self.log.info("STARTED: Teardown operations")
        resp = self.s3_test_obj.bucket_list()
        pref_list = [
            each_bucket for each_bucket in resp[1] if each_bucket.startswith("mp-bkt")]
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

        self.log.info("Cleanup S3 background IO artifacts")
        self.s3_background_io.cleanup()
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29167')
    @CTFailOn(error_handler)
    def test_multipart_upload_after_abort_29167(self):
        """
        Upload parts to an aborted multipart upload ID.

        Initiate a multipart upload, upload parts and abort it.
        Upload parts to the same upload ID.
        Verify expected error message is generated
        """
        self.log.info("STARTED: Test uploading parts to an aborted multipart upload")

        mp_config = S3_MPART_CFG["test_29167"]

        self.log.info("Create file for multipart upload")
        res = create_file(self.mp_obj_path, mp_config["file_size"],b_size="1M")
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_true(path_exists(self.mp_obj_path))

        self.log.info("Calculate unaligned parts to upload")
        parts = get_unaligned_parts(self.mp_obj_path,
                                    total_parts=mp_config["total_parts"],
                                    chunk_size=mp_config["chunk_size"],
                                    random=True)

        self.log.info("Start background S3 IOs")
        self.s3_background_io.start(log_prefix="TEST-29167_s3bench_ios",
                                    duration="0h5m")

        self.log.info("Initiating multipart upload")
        resp = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name,
                                                           self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id = resp[1]["UploadId"]

        self.log.info("Upload parts")
        self.s3_mp_test_obj.upload_prepared_parts_sequential(
            upload_id=mpu_id,
            bucket_name=self.bucket_name,
            object_name=self.object_name,
            parts=parts)

        self.log.info("Abort multipart upload")
        res = self.s3_mp_test_obj.abort_multipart_upload(
            upload_id=mpu_id,
            bucket=self.bucket_name,
            object_name=self.object_name)
        assert_utils.assert_true(res[0], res[1])

        self.log.info("Upload parts to aborted multipart upload ID")
        try:
            self.s3_mp_test_obj.upload_prepared_parts_sequential(
                upload_id=mpu_id,
                bucket_name=self.bucket_name,
                object_name=self.object_name,
                parts=parts)
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_equal(
                mp_config["error_msg"],
                error.message,
                error.message)
            self.log.info(
                "Uploading parts to the aborted multipart upload ID failed")

        self.log.info("Stop background S3 IOs")
        self.s3_background_io.stop()

        self.log.info("ENDED: Test uploading parts to an aborted multipart upload")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29164')
    @CTFailOn(error_handler)
    def test_multipart_abort_during_upload_29164(self):
        """
        Abort multipart while upload part is in progress.

        Initiate a multipart upload, upload parts.
        Abort it before upload part operations complete.
        Verify with list multipart
        """
        self.log.info("STARTED: Test aborting multipart upload that is in progress")

        mp_config = S3_MPART_CFG["test_29164"]

        self.log.info("Create file for multipart upload")
        res = create_file(self.mp_obj_path, mp_config["file_size"], b_size="1M")
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_true(path_exists(self.mp_obj_path))

        self.log.info("Calculate unaligned parts to upload")
        parts = get_unaligned_parts(self.mp_obj_path,
                                    total_parts=mp_config["total_parts"],
                                    chunk_size=mp_config["chunk_size"],
                                    random=True)

        self.log.info("Start background S3 IOs")
        self.s3_background_io.start(log_prefix="TEST-29164_s3bench_ios",
                                    duration="0h5m")

        self.log.info("Initiating multipart upload")
        resp = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name,
                                                           self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id = resp[1]["UploadId"]

        self.log.info("Upload parts in parallel")
        process = Process(target=self.s3_mp_test_obj.upload_parts_parallel,
                          args=(mpu_id, self.bucket_name, self.object_name),
                          kwargs={"parts": parts})
        process.start()

        self.log.info("Sleep for 5 seconds for multipart uploads to start")
        time.sleep(5)

        self.log.info("Aborting multipart upload")
        resp = self.s3_mp_test_obj.abort_multipart_upload(
            self.bucket_name,
            self.object_name,
            mpu_id)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Wait for concurrent upload part process to finish")
        while process.is_alive():
            resp = self.s3_mp_test_obj.list_multipart_uploads(
                self.bucket_name)
            if mpu_id not in resp[1]:
                break

        self.log.info("Verify upload ID is not present in list multipart uploads result")
        assert_utils.assert_not_in(mpu_id, resp[1], resp[1])
        self.log.info(
            "Aborted multipart upload with upload ID: %s", mpu_id)

        self.log.info("Stop background S3 IOs")
        self.s3_background_io.stop()

        self.log.info("ENDED: Test aborting multipart upload that is in progress")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29165')
    @CTFailOn(error_handler)
    def test_copy_of_copied_multipart_object_29165(self):
        """
        Testing copying a copied object uploaded using multipart.

        Initiate a multipart upload, upload parts and complete it.
        Create multiple copies of the uploaded object.
        Verify copied objects
        """
        self.log.info("STARTED: Test copying a copied object uploaded using multipart")

        mp_config = S3_MPART_CFG["test_29165"]

        self.log.info("Create file for multipart upload and calculate etag")
        res = create_file(self.mp_obj_path, mp_config["file_size"], b_size="1M")
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_true(path_exists(self.mp_obj_path))
        source_etag = calc_etag(self.mp_obj_path)

        self.log.info("Calculate unaligned parts to upload")
        parts = get_unaligned_parts(self.mp_obj_path,
                                    total_parts=mp_config["total_parts"],
                                    chunk_size=mp_config["chunk_size"],
                                    random=True)

        self.log.info("Start background S3 IOs")
        self.s3_background_io.start(log_prefix="TEST-29165_s3bench_ios",
                                    duration="0h5m")

        self.log.info("Initiating multipart upload")
        resp = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name,
                                                           self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id = resp[1]["UploadId"]

        self.log.info("Upload parts")
        uploaded_parts = self.s3_mp_test_obj.upload_prepared_parts_sequential(
            upload_id=mpu_id,
            bucket_name=self.bucket_name,
            object_name=self.object_name,
            parts=parts)

        self.log.info("Complete multipart upload")
        resp = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id=mpu_id,
            parts=uploaded_parts,
            bucket=self.bucket_name,
            object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(source_etag, resp[1]["ETag"])

        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, resp[1], resp[1])
        self.log.info("Multipart upload completed")

        src_bkt = self.bucket_name
        for _ in range(10):
            dst_bkt = "mp-bkt-{}".format(self.random_time)
            self.log.info(
                "Creating a bucket with name : %s",
                dst_bkt)
            resp = self.s3_test_obj.create_bucket(dst_bkt)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_equal(resp[1], dst_bkt, resp[1])
            self.log.info(
                "Created a bucket with name : %s", dst_bkt)

            self.log.info("Copy object from %s to %s", src_bkt, dst_bkt)
            resp = self.s3_test_obj.copy_object(source_bucket=src_bkt,
                                         source_object=self.object_name,
                                         dest_bucket=dst_bkt,
                                         dest_object=self.object_name)
            assert_utils.assert_true(resp[0], resp[1])
            copy_etag = resp[1]['CopyObjectResult']['ETag']

            self.log.info("Verify copy and source etags match")
            assert_utils.assert_equal(source_etag, copy_etag)

            src_bkt = dst_bkt

        self.log.info("Stop background S3 IOs")
        self.s3_background_io.stop()

        self.log.info("ENDED: Test copying a copied object uploaded using multipart")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29166')
    @CTFailOn(error_handler)
    def test_copy_multipart_upload_parallel_delete_29166(self):
        """
        Testing deleting a completed multipart upload being copied.

        Initiate a multipart upload, upload parts and complete it.
        Copy uploaded object.
        Delete object while copy is in progress.
        Verify copy object fails.
        """
        self.log.info("STARTED: Test deleting completed multipart object during copy operation")

        mp_config = S3_MPART_CFG["test_29166"]

        self.log.info("Create file for multipart upload and calculate etag")
        res = create_file(self.mp_obj_path, mp_config["file_size"], b_size="1M")
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_true(path_exists(self.mp_obj_path))
        source_etag = calc_etag(self.mp_obj_path)

        self.log.info("Calculate unaligned parts to upload")
        parts = get_unaligned_parts(self.mp_obj_path,
                                    total_parts=mp_config["total_parts"],
                                    chunk_size=mp_config["chunk_size"],
                                    random=True)

        self.log.info("Start background S3 IOs")
        self.s3_background_io.start(log_prefix="TEST-29166_s3bench_ios",
                                    duration="0h5m")

        self.log.info("Initiating multipart upload")
        resp = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name,
                                                           self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id = resp[1]["UploadId"]

        self.log.info("Upload parts")
        uploaded_parts = self.s3_mp_test_obj.upload_prepared_parts_sequential(
            upload_id=mpu_id,
            bucket_name=self.bucket_name,
            object_name=self.object_name,
            parts=parts)

        self.log.info("Complete multipart upload")
        resp = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id=mpu_id,
            parts=uploaded_parts,
            bucket=self.bucket_name,
            object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(source_etag, resp[1]["ETag"])

        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, resp[1], resp[1])
        self.log.info("Multipart upload completed")

        dst_bkt = "mp-bkt-{}".format(self.random_time)
        self.log.info(
            "Creating a bucket with name : %s",
            dst_bkt)
        resp = self.s3_test_obj.create_bucket(dst_bkt)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], dst_bkt, resp[1])
        self.log.info(
            "Created a bucket with name : %s", dst_bkt)

        self.log.info("Copy completed multipart object in a parallel process")
        process = Process(target=self.s3_test_obj.copy_object,
                          kwargs={"source_bucket": self.bucket_name,
                                  "source_object": self.object_name,
                                  "dest_bucket": dst_bkt,
                                  "dest_object": self.object_name})
        process.start()

        self.log.info("Delete object uploaded as multipart")
        resp = self.s3_test_obj.delete_object(bucket_name=self.bucket_name,
                                              obj_name=self.object_name)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Wait for copy process to complete")
        process.join()

        self.log.info("Retrieve metadata of source object")
        try:
            self.s3_test_obj.object_info(
                self.bucket_name,
                self.object_name)
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_equal(
                mp_config["error_msg"],
                error.message,
                error.message)
            self.log.info(
                "Retrieving info of deleted source object failed")

        self.log.info("Retrieve metadata of copy object")
        try:
            self.s3_test_obj.object_info(
                dst_bkt,
                self.object_name)
        except CTException as error:
            self.log.error(error)
            assert_utils.assert_equal(
                mp_config["error_msg"],
                error.message,
                error.message)
            self.log.info(
                "Retrieving info of incomplete copy object failed")

        self.log.info("Stop background S3 IOs")
        self.s3_background_io.stop()

        self.log.info("ENDED: Test deleting completed multipart object during copy operation")

    @pytest.mark.skip(reason="Storage requirements - min 100TB on cluster, 5TB on client")
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29168')
    @CTFailOn(error_handler)
    def test_upload_20_5tb_multiparts_29168(self):
        """
        Testing 20 5TB simultaneous multipart uploads.

        Initiate 20 5TB multipart uploads and upload parts.
        Restart S3 server when 15 multipart uploads are being completed.
        Verify with list parts complete multipart calls that failed.
        Retry failed complete multipart calls.
        Verify all uploaded multiparts.
        """
        self.log.info("STARTED: Test uploading 20 5TB multipart objects")

        mp_config = S3_MPART_CFG["test_29168"]

        self.log.info("Create file for multipart upload and calculate etag")
        res = create_file(self.mp_obj_path, mp_config["file_size"], b_size="1M")
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_true(path_exists(self.mp_obj_path))
        source_etag = calc_etag(self.mp_obj_path)

        self.log.info("Calculate unaligned parts to upload")
        parts = get_unaligned_parts(self.mp_obj_path,
                                    total_parts=mp_config["total_parts"],
                                    chunk_size=mp_config["chunk_size"],
                                    random=True)

        upload_mpu_list = []
        upload_process_list = []
        self.log.info("Initiate 20 multipart uploads")
        for i in range(mp_config["mpu_count"]):
            self.log.info("Initiating multipart upload")
            mpu_name = self.object_name + str(i)
            resp = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name,
                                                               mpu_name)
            assert_utils.assert_true(resp[0], resp[1])
            mpu_id = resp[1]["UploadId"]
            mpu_dict = ({"object_name": mpu_name,
                         "mpu_id": mpu_id,
                         "parts": parts,
                         "bucket_name": self.bucket_name})
            upload_mpu_list.append(mpu_dict)

            process = Process(target=self.s3_mp_test_obj.upload_prepared_parts_sequential,
                              kwargs=mpu_dict)
            upload_process_list.append(process)

        self.log.info("Upload parts in parallel")
        for process in upload_process_list:
            process.start()

        self.log.info("Wait for upload to complete")
        for process in upload_process_list:
            process.join()

        complete_mpu_process_list = []
        complete_mpu_list = []
        for mpu_dict in upload_mpu_list:
            resp = self.s3_mp_test_obj.list_parts(mpu_id=mpu_dict["mpu_id"],
                                                  bucket_name=self.bucket_name,
                                                  object_name=mpu_dict["object_name"])
            assert_utils.assert_true(resp[0], resp[1])

            uploaded_parts = [{"PartNumber": part_info["PartNumber"],
                               "ETag": part_info["ETag"]}
                              for part_info in resp[1]]
            complete_mpu_dict = {"object_name": mpu_dict["object_name"],
                                 "mpu_id": mpu_dict["object_name"],
                                 "parts": uploaded_parts,
                                 "bucket": self.bucket_name}

            complete_mpu_list.append(complete_mpu_dict)

            process = Process(target=self.s3_mp_test_obj.complete_multipart_upload,
                              kwargs=complete_mpu_dict)
            complete_mpu_process_list.append(process)

        self.log.info("Complete multipart upload in parallel")
        for process in complete_mpu_process_list:
            process.start()

        self.log.info("Restart S3 server during upload")
        resp = S3H_OBJ.restart_s3server_processes(S3_CFG["nodes"][0]["hostname"],
                                                  S3_CFG["nodes"][0]["username"],
                                                  S3_CFG["nodes"][0]["password"])
        assert_utils.assert_true(resp[0], resp[1])

        for process in complete_mpu_process_list:
            process.join()

        self.log.info("Retry failed complete multipart requests")
        for mpu_dict in complete_mpu_list:
            resp = self.s3_mp_test_obj.list_parts(mpu_id=mpu_dict["mpu_id"],
                                                  bucket_name=self.bucket_name,
                                                  object_name=mpu_dict["object_name"])
            if resp[0]:
                resp = self.s3_mp_test_obj.complete_multipart_upload(
                    mpu_id=mpu_dict["mpu_id"],
                    bucket=self.bucket_name,
                    object_name=mpu_dict["object_name"],
                    parts=mpu_dict["parts"])
                assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Verify multipart uploads")
        status, object_list_resp = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_true(status, object_list_resp)

        for mpu_dict in upload_mpu_list:
            assert_utils.assert_in(mpu_dict["object_name"], object_list_resp, object_list_resp)

            resp = self.s3_test_obj.object_info(bucket_name=self.bucket_name,
                                                key=mpu_dict["object_name"])
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_equal(source_etag, resp[1]["ETag"])

        self.log.info("ENDED: Test uploading 20 5TB multipart objects")
