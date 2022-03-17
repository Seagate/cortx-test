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

"""Multipart Upload Partcopy test module."""

import logging
import random
import time
import os
import multiprocessing
from time import perf_counter_ns

import pytest
from commons.ct_fail_on import CTFailOn
from commons import error_constants as errconst
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.system_utils import remove_file, path_exists
from commons.utils.s3_utils import get_precalculated_parts, calc_checksum
from commons.utils.system_utils import make_dirs, remove_dirs, create_file
from commons.utils import assert_utils
from commons.params import TEST_DATA_FOLDER
from commons.greenlet_worker import GeventPool
from config.s3 import MPART_CFG
from libs.s3.s3_common_test_lib import S3BackgroundIO
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from libs.s3.s3_test_lib import S3TestLib
from libs.s3 import S3_CFG
from libs.s3 import s3_common_test_lib as cmn_lib


class TestMultipartUploadPartCopy:
    """Multipart Upload Part Copy Test Suite."""

    # pylint: disable=too-many-instance-attributes
    # pylint: disable=attribute-defined-outside-init
    # pylint: disable-msg=too-many-statements
    # pylint: disable=too-many-arguments
    # pylint: disable-msg=too-many-locals

    @pytest.yield_fixture(autouse=True)
    def setup(self):
        """Setup method is called before/after each test in this test suite."""
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.test_file = "mpu_obj-{}".format(perf_counter_ns())
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestMultipartUploadPartCopy")
        self.mp_obj_path = os.path.join(self.test_dir_path, self.test_file)
        self.mp_obj_path_partcopy = os.path.join(
            self.test_dir_path, "mpu_partcopy_obj{}".format(perf_counter_ns()))
        self.mp_down_obj_pth = os.path.join(
            self.test_dir_path, "mpu_down_obj{}".format(perf_counter_ns()))
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.download_path = os.path.join(self.test_dir_path, "s3-obj-{}".format(perf_counter_ns()))
        self.acc_name_prefix = "mpu-s3acc-{}"
        self.acc_email_prefix = "{}@seagate.com"
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.mpu_partcopy_bkt = "mpu-partcopy-bkt-{}".format(perf_counter_ns())
        self.mpu_partcopy_obj = "mpu-partcopy-obj-{}".format(perf_counter_ns())
        self.io_bucket_name = "mpu-io-bkt-{}".format(perf_counter_ns())
        self.bucket_name = "mpu-bkt-{}".format(perf_counter_ns())
        self.bucket_name1 = "mpu-bkt1-{}".format(perf_counter_ns())
        self.object_name = "mpu-obj-{}".format(perf_counter_ns())
        self.object_name1 = "mpu-obj1-{}".format(perf_counter_ns())
        self.object_name2 = "mpu-obj2-{}".format(perf_counter_ns())
        self.s3mpu_obj = S3MultipartTestLib()
        self.s3t_obj = S3TestLib()
        self.rest_obj = S3AccountOperationsRestAPI()
        self.s3bio_obj = S3BackgroundIO(self.s3t_obj, self.io_bucket_name)
        self.account_list = []
        self.s3t_obj_list = []
        self.log.info("ENDED: Setup operations")
        yield
        self.log.info("STARTED: Teardown operations")
        self.s3t_obj_list.append(self.s3t_obj)
        self.s3bio_obj.cleanup()
        for s3tobj in self.s3t_obj_list:
            resp = s3tobj.bucket_list()
            if resp[1]:
                resp = s3tobj.delete_multiple_buckets(resp[1])
                assert_utils.assert_true(resp[0], resp[1])
        if path_exists(self.mp_obj_path):
            remove_file(self.mp_obj_path)
        for s3account in self.account_list:
            resp = self.rest_obj.delete_s3_account(s3account)
            assert_utils.assert_true(resp[0], resp[1])
        if path_exists(self.test_dir_path):
            remove_dirs(self.test_dir_path)
        self.log.info("Cleanup test directory: %s", self.test_dir_path)
        self.log.info("ENDED: Teardown operations")

    def create_and_complete_mpu(self, putchecksum, mpu_cfg):
        """
        Initiate and verify multipart.

        Create multipart, uploads parts, completes multipart upload, gets the uploaded object
        and compares ETags.
        :param mpu_cfg : configuration for the test
        """
        resp = self.s3t_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id = self.initiate_multipart(self.bucket_name, self.object_name)
        uploaded_parts = get_precalculated_parts(self.mp_obj_path, mpu_cfg["part_sizes"],
                                                 chunk_size=mpu_cfg["chunk_size"])
        keys = list(uploaded_parts.keys())
        random.shuffle(keys)
        self.log.info("Uploading parts")
        status, new_parts = self.s3mpu_obj.upload_parts_sequential(mpu_id, self.bucket_name,
                                                                   self.object_name,
                                                                   parts=uploaded_parts)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        res = self.s3mpu_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        self.log.info("Complete the multipart ")
        resp = self.s3mpu_obj.complete_multipart_upload(mpu_id, sorted_part_list,
                                                        self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        upload_etag = resp[1]["ETag"]
        self.log.info("Get the uploaded object")
        status, res = self.s3t_obj.get_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(status, res)
        get_etag = res['ETag']
        self.log.info("Compare ETags")
        assert_utils.assert_equal(resp[1]["ETag"], get_etag,
                                  f"Failed to match ETag: {upload_etag}, {get_etag}")
        self.log.info("Matched ETag: %s, %s", upload_etag, get_etag)
        self.log.info("Download the object..")
        resp = self.s3t_obj.object_download(
            self.bucket_name, self.object_name, self.download_path)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = calc_checksum(self.download_path)
        assert_utils.assert_equal(putchecksum, download_checksum, "Checksum match failed.")

    def initiate_multipart(self, bucket_name, object_name):
        """Initialise multipart and returns mpuID."""
        res = self.s3mpu_obj.create_multipart_upload(bucket_name, object_name)

        return res[1]["UploadId"]

    def multiprocess_upload_parts(self, event, mpu_id, parts):
        """process to upload parts for one session of client."""
        self.log.info("Creating s3_client session")
        client_instance = S3MultipartTestLib()
        self.log.info("uploading parts in client session")
        status, all_parts = client_instance.upload_parts_sequential(
            mpu_id, self.mpu_partcopy_bkt, self.mpu_partcopy_obj, parts=parts)
        if event.is_set():
            assert_utils.assert_true(status, f"Failed to upload parts: {all_parts}")
        else:
            assert_utils.assert_true(status, f"Failed to upload parts: {all_parts}")
        response = client_instance.upload_part_copy(
            f"{self.bucket_name}/{self.object_name}", self.mpu_partcopy_bkt, self.mpu_partcopy_obj,
            part_number=2, upload_id=mpu_id)
        all_parts.append({"PartNumber": 2, "ETag": response[1]["CopyPartResult"]["ETag"]})
        self.log.info(all_parts)

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32702')
    @CTFailOn(error_handler)
    def test_mpu_upload_partcopy_32702(self):
        """Test is for getting object uploaded using multipart UploadPartCopy api."""
        mp_config = MPART_CFG["test_32702_1"]
        multipart_obj_path = self.mp_obj_path
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        create_file(multipart_obj_path, mp_config["file_size"])
        put_checksum = calc_checksum(multipart_obj_path)
        mp_config_2 = MPART_CFG["test_32702_2"]
        if os.path.exists(self.mp_obj_path_partcopy):
            os.remove(self.mp_obj_path_partcopy)
        create_file(self.mp_obj_path_partcopy, mp_config_2["file_size"])
        self.log.info("STARTED: Test get the object uploaded using MPU UploadPartCopy")

        self.log.info("start s3 IO's")
        self.s3bio_obj.start(log_prefix="TEST-32702_s3bench_ios", duration="0h2m")
        self.create_and_complete_mpu(put_checksum, mp_config)
        self.log.info("Creating a bucket with name : %s", self.mpu_partcopy_bkt)
        res = self.s3t_obj.create_bucket(self.mpu_partcopy_bkt)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.mpu_partcopy_bkt, res[1])
        self.log.info("Created a bucket with name : %s", self.mpu_partcopy_bkt)
        mpu_id2 = self.initiate_multipart(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        uploaded_parts2 = get_precalculated_parts(self.mp_obj_path_partcopy,
                                                  mp_config_2["part_sizes"],
                                                  chunk_size=mp_config_2["chunk_size"])
        keys = list(uploaded_parts2.keys())
        uploaded_parts2[3] = uploaded_parts2.pop(2)  # modified the part 2 as part 3
        random.shuffle(keys)
        self.log.info("Uploading parts")
        status, new_parts = self.s3mpu_obj.upload_parts_sequential(mpu_id2,
                                                                   self.mpu_partcopy_bkt,
                                                                   self.mpu_partcopy_obj,
                                                                   parts=uploaded_parts2)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        response = self.s3mpu_obj.upload_part_copy(f"{self.bucket_name}/{self.object_name}",
                                                   self.mpu_partcopy_bkt,
                                                   self.mpu_partcopy_obj,
                                                   part_number=2,
                                                   upload_id=mpu_id2)
        new_parts.append({"PartNumber": 2, "ETag": response[1]["CopyPartResult"]["ETag"]})
        res = self.s3mpu_obj.list_parts(mpu_id2, self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Complete the multipart")
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(mpu_id2, sorted_part_list,
                                                        self.mpu_partcopy_bkt,
                                                        self.mpu_partcopy_obj)
        assert_utils.assert_true(resp[0], resp[1])
        upload_etag2 = resp[1]["ETag"]
        self.log.info("Get the uploaded object (using uploadPartCopy)")
        status, res = self.s3t_obj.get_object(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(status, res)
        get_etag2 = res['ETag']
        self.log.info("Compare ETags")
        assert_utils.assert_equal(resp[1]["ETag"], get_etag2,
                                  f"Failed to match ETag: {upload_etag2}, {get_etag2}")
        self.log.info("Matched ETag: %s, %s", upload_etag2, get_etag2)

        self.log.info("Stop and validate parallel S3 IOs")
        self.s3bio_obj.stop()
        self.log.info("ENDED: Get the object uploaded using MPU UploadPartCopy")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32711')
    @CTFailOn(error_handler)
    def test_mpu_upload_partcopy_32711(self):
        """Test is for copying uploaded using multipart UploadPartCopy api to another buckets."""
        mp_config = MPART_CFG["test_32702_1"]
        multipart_obj_path = self.mp_obj_path
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        create_file(multipart_obj_path, mp_config["file_size"])
        put_checksum = calc_checksum(multipart_obj_path)
        self.log.info("STARTED: Test Copy object created by MPU uploadPartCopy to another bucket")
        self.log.info("start s3 IO's")
        self.s3bio_obj.start(log_prefix="TEST-32711_s3bench_ios", duration="0h2m")
        self.create_and_complete_mpu(put_checksum, mp_config)
        self.put_object_name = "mpu-uploadpartcopy-put-obj"
        status, put_etag = self.s3t_obj.put_object(self.bucket_name, self.put_object_name,
                                                   multipart_obj_path)
        assert_utils.assert_true(status, put_etag)
        self.log.info("Creating a bucket with name : %s", self.mpu_partcopy_bkt)
        res = self.s3t_obj.create_bucket(self.mpu_partcopy_bkt)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.mpu_partcopy_bkt, res[1])
        self.log.info("Created a bucket with name : %s", self.mpu_partcopy_bkt)
        mp_config_2 = MPART_CFG["test_32702_2"]
        if os.path.exists(self.mp_obj_path_partcopy):
            os.remove(self.mp_obj_path_partcopy)
        create_file(self.mp_obj_path_partcopy, mp_config_2["file_size"])
        mpu_id2 = self.initiate_multipart(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        uploaded_parts2 = get_precalculated_parts(self.mp_obj_path_partcopy,
                                                  mp_config_2["part_sizes"],
                                                  chunk_size=mp_config_2["chunk_size"])
        keys = list(uploaded_parts2.keys())
        uploaded_parts2[3] = uploaded_parts2.pop(2)  # modified the part 2 as part 3
        random.shuffle(keys)
        self.log.info("Uploading parts")
        status, new_parts = self.s3mpu_obj.upload_parts_sequential(mpu_id2,
                                                                   self.mpu_partcopy_bkt,
                                                                   self.mpu_partcopy_obj,
                                                                   parts=uploaded_parts2)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        response1 = self.s3mpu_obj.upload_part_copy(
            self.bucket_name + "/" + self.put_object_name,
            self.mpu_partcopy_bkt, self.mpu_partcopy_obj, part_number=4, upload_id=mpu_id2)
        self.log.info("copy part retult is %s", response1[1]["CopyPartResult"])
        new_parts.append({"PartNumber": 4, "ETag": response1[1]["CopyPartResult"]["ETag"]})
        response = self.s3mpu_obj.upload_part_copy(self.bucket_name + "/" + self.object_name,
                                                   self.mpu_partcopy_bkt,
                                                   self.mpu_partcopy_obj,
                                                   part_number=2,
                                                   upload_id=mpu_id2)
        new_parts.append({"PartNumber": 2, "ETag": response[1]["CopyPartResult"]["ETag"]})

        res = self.s3mpu_obj.list_parts(mpu_id2, self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(res[0], res[1])
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        self.log.info("Complete the multipart")
        resp = self.s3mpu_obj.complete_multipart_upload(mpu_id2, sorted_part_list,
                                                        self.mpu_partcopy_bkt,
                                                        self.mpu_partcopy_obj)
        assert_utils.assert_true(resp[0], resp[1])
        upload_etag2 = resp[1]["ETag"]
        self.log.info("Get the uploaded object (using uploadPartCopy)")
        status, res = self.s3t_obj.get_object(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(status, res)
        get_etag2 = res['ETag']
        self.log.info("Compare ETags")
        assert_utils.assert_equal(resp[1]["ETag"], get_etag2,
                                  f"Failed to match ETag: {upload_etag2}, {get_etag2}")
        self.log.info("Matched ETag: %s, %s", upload_etag2, get_etag2)
        # copy object2 to bucket3 and bucket1
        src_bkt = self.mpu_partcopy_bkt
        dst_bkt = "mp-bkt3-{}".format(time.perf_counter_ns())
        self.log.info("Creating a bucket with name : %s", dst_bkt)
        resp = self.s3t_obj.create_bucket(dst_bkt)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(resp[1], dst_bkt, resp[1])
        self.log.info("Created a bucket with name : %s", dst_bkt)
        self.log.info("Copy object from bucket2 named %s to bucket3 named %s", src_bkt, dst_bkt)
        resp = self.s3t_obj.copy_object(
            source_bucket=src_bkt, source_object=self.mpu_partcopy_obj, dest_bucket=dst_bkt,
            dest_object=self.mpu_partcopy_obj)
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        self.log.info("Verify copy and source etags match")
        assert_utils.assert_equal(upload_etag2, copy_etag)
        dst_bkt = self.bucket_name
        self.log.info("Copy object from bucket2 named %s to bucket1 named %s", src_bkt, dst_bkt)
        resp = self.s3t_obj.copy_object(
            source_bucket=src_bkt, source_object=self.mpu_partcopy_obj, dest_bucket=dst_bkt,
            dest_object=self.mpu_partcopy_obj)
        assert_utils.assert_true(resp[0], resp[1])
        copy_etag = resp[1]['CopyObjectResult']['ETag']
        self.log.info("Verify copy and source etags match")
        assert_utils.assert_equal(upload_etag2, copy_etag)
        self.log.info("Stop and validate parallel S3 IOs")
        self.s3bio_obj.stop()
        self.log.info("ENDED: Test Copy object created by MPU uploadPartCopy to another bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32710')
    @CTFailOn(error_handler)
    def test_mpu_upload_partcopy_32710(self):
        """Test is for Copy object created recursively by MPU-UploadPartCopy."""
        mp_config = MPART_CFG["test_32702_1"]
        multipart_obj_path = self.mp_obj_path
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        create_file(multipart_obj_path, mp_config["file_size"])
        put_checksum = calc_checksum(multipart_obj_path)
        mp_config_2 = MPART_CFG["test_32702_2"]
        if os.path.exists(self.mp_obj_path_partcopy):
            os.remove(self.mp_obj_path_partcopy)
        create_file(self.mp_obj_path_partcopy, mp_config_2["file_size"])
        self.log.info("STARTED: Test Multipart upload with invalid json input")
        self.log.info("start s3 IO's")
        self.s3bio_obj.start(log_prefix="TEST-32710_s3bench_ios", duration="0h2m")
        self.create_and_complete_mpu(put_checksum, mp_config)
        self.log.info("Creating a bucket with name : %s", self.mpu_partcopy_bkt)
        res = self.s3t_obj.create_bucket(self.mpu_partcopy_bkt)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.mpu_partcopy_bkt, res[1])
        self.log.info("Created a bucket with name : %s", self.mpu_partcopy_bkt)
        mpu_id2 = self.initiate_multipart(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        uploaded_parts2 = get_precalculated_parts(self.mp_obj_path_partcopy,
                                                  mp_config_2["part_sizes"],
                                                  chunk_size=mp_config_2["chunk_size"])
        uploaded_parts2.pop(2)  # removed part 2 as we are going to upload only one part here
        self.log.info("Uploading parts")
        status, new_parts = self.s3mpu_obj.upload_parts_sequential(mpu_id2,
                                                                   self.mpu_partcopy_bkt,
                                                                   self.mpu_partcopy_obj,
                                                                   parts=uploaded_parts2)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        response = self.s3mpu_obj.upload_part_copy(self.bucket_name + "/" + self.object_name,
                                                   self.mpu_partcopy_bkt,
                                                   self.mpu_partcopy_obj,
                                                   part_number=2,
                                                   upload_id=mpu_id2)
        new_parts.append({"PartNumber": 2, "ETag": response[1]["CopyPartResult"]["ETag"]})
        res = self.s3mpu_obj.list_parts(mpu_id2, self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(res[0], res[1])
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        self.log.info("Complete the multipart")
        resp = self.s3mpu_obj.complete_multipart_upload(mpu_id2, sorted_part_list,
                                                        self.mpu_partcopy_bkt,
                                                        self.mpu_partcopy_obj)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_partcopy_bkt3 = "mpu-partcopy-bkt3-{}".format(perf_counter_ns())
        mpu_partcopy_obj3 = "mpu-partcopy-obj3-{}".format(perf_counter_ns())
        self.log.info("Creating a bucket with name : %s", mpu_partcopy_bkt3)
        res = self.s3t_obj.create_bucket(mpu_partcopy_bkt3)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], mpu_partcopy_bkt3, res[1])
        self.log.info("Created a bucket with name : %s", mpu_partcopy_bkt3)
        mpu_id3 = self.initiate_multipart(mpu_partcopy_bkt3, mpu_partcopy_obj3)
        uploaded_parts2 = get_precalculated_parts(self.mp_obj_path_partcopy,
                                                  mp_config_2["part_sizes"],
                                                  chunk_size=mp_config_2["chunk_size"])
        uploaded_parts2.pop(2)  # removed part 2 as we are going to upload only one part here
        self.log.info("Uploading parts")
        status, new_parts = self.s3mpu_obj.upload_parts_sequential(mpu_id3,
                                                                   mpu_partcopy_bkt3,
                                                                   mpu_partcopy_obj3,
                                                                   parts=uploaded_parts2)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        response = self.s3mpu_obj.upload_part_copy(
            self.mpu_partcopy_bkt + "/" + self.mpu_partcopy_obj, mpu_partcopy_bkt3,
            mpu_partcopy_obj3, part_number=2, upload_id=mpu_id3)
        new_parts.append({"PartNumber": 2, "ETag": response[1]["CopyPartResult"]["ETag"]})
        response = self.s3mpu_obj.upload_part_copy(
            self.bucket_name + "/" + self.object_name, mpu_partcopy_bkt3,
            mpu_partcopy_obj3, part_number=3, upload_id=mpu_id3,
            copy_source_range="bytes=0-157286400")
        new_parts.append({"PartNumber": 3, "ETag": response[1]["CopyPartResult"]["ETag"]})
        res = self.s3mpu_obj.list_parts(mpu_id3, mpu_partcopy_bkt3, mpu_partcopy_obj3)
        assert_utils.assert_true(res[0], res[1])
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        self.log.info("Complete the multipart")
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id3, sorted_part_list, mpu_partcopy_bkt3, mpu_partcopy_obj3)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Stop and validate parallel S3 IOs")
        self.s3bio_obj.stop()
        self.log.info("ENDED: Test Copy object created  recursively by MPU-UploadPartCopy")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32712')
    @CTFailOn(error_handler)
    def test_mpu_upload_partcopy_32712(self):
        """

        This test is for aborting Copy object created recursively by MPU-UploadPartCopy from
        one session while parts are getting uploaded via session 2
        """
        mp_config = MPART_CFG["test_32702_1"]
        multipart_obj_path = self.mp_obj_path
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        create_file(multipart_obj_path, mp_config["file_size"])
        put_checksum = calc_checksum(multipart_obj_path)
        mp_config_2 = MPART_CFG["test_32702_2"]
        if os.path.exists(self.mp_obj_path_partcopy):
            os.remove(self.mp_obj_path_partcopy)
        create_file(self.mp_obj_path_partcopy, mp_config_2["file_size"])
        self.log.info("STARTED: Test abort copy object created recursively by MPU-UploadPartCopy")
        self.log.info("start s3 IO's")
        self.s3bio_obj.start(log_prefix="TEST-32712_s3bench_ios", duration="0h2m")
        self.create_and_complete_mpu(put_checksum, mp_config)
        self.log.info("Creating a bucket with name : %s", self.mpu_partcopy_bkt)
        res = self.s3t_obj.create_bucket(self.mpu_partcopy_bkt)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.mpu_partcopy_bkt, res[1])
        self.log.info("Created a bucket with name : %s", self.mpu_partcopy_bkt)
        mpu_id2 = self.initiate_multipart(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        uploaded_parts2 = get_precalculated_parts(self.mp_obj_path_partcopy,
                                                  mp_config_2["part_sizes"],
                                                  chunk_size=mp_config_2["chunk_size"])
        uploaded_parts2.pop(2)  # removed part 2 as we are going to upload only one part here
        event = multiprocessing.Event()
        proc = multiprocessing.Process(target=self.multiprocess_upload_parts,
                                       args=(mpu_id2, dict(list(uploaded_parts2.items())[0:])))
        event.set()
        proc.start()
        while proc.is_alive():
            self.log.info("Abort multipart upload")
            resp = self.s3mpu_obj.abort_multipart_upload(self.mpu_partcopy_bkt,
                                                         self.mpu_partcopy_obj, mpu_id2)
            assert_utils.assert_true(resp[0], resp[1])
        proc.join()
        try:
            resp = self.s3mpu_obj.list_parts(mpu_id2, self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            self.log.info("Failed to list parts after the abort of the multipart upload")
        self.log.info("Failed to upload parts of multipart upload")
        self.log.info("Stop and validate parallel S3 IOs")
        self.s3bio_obj.stop()
        self.log.info("ENDED: Test abort Copy object created recursively by MPU-UploadPartCopy")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32714')
    @CTFailOn(error_handler)
    def test_mpu_upload_partcopy_32714(self):
        """Test is for aborting the MPU-UploadPartCopy."""
        mp_config = MPART_CFG["test_32702_1"]
        multipart_obj_path = self.mp_obj_path
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        create_file(multipart_obj_path, mp_config["file_size"])
        put_checksum = calc_checksum(multipart_obj_path)
        mp_config_2 = MPART_CFG["test_32702_2"]
        if os.path.exists(self.mp_obj_path_partcopy):
            os.remove(self.mp_obj_path_partcopy)
        create_file(self.mp_obj_path_partcopy, mp_config_2["file_size"])
        self.log.info("STARTED: Test abort MPU-UploadPartCopy")
        self.log.info("start s3 IO's")
        self.s3bio_obj.start(log_prefix="TEST-32714_s3bench_ios", duration="0h2m")
        self.create_and_complete_mpu(put_checksum, mp_config)
        self.log.info("Creating a bucket with name : %s", self.mpu_partcopy_bkt)
        res = self.s3t_obj.create_bucket(self.mpu_partcopy_bkt)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.mpu_partcopy_bkt, res[1])
        self.log.info("Created a bucket with name : %s", self.mpu_partcopy_bkt)
        mpu_id2 = self.initiate_multipart(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        uploaded_parts2 = get_precalculated_parts(self.mp_obj_path_partcopy,
                                                  mp_config_2["part_sizes"],
                                                  chunk_size=mp_config_2["chunk_size"])
        uploaded_parts2.pop(2)  # removed part 2 as we are going to upload only one part here
        event = multiprocessing.Event()
        self.log.info("Uploading parts")
        self.multiprocess_upload_parts(event, mpu_id2, uploaded_parts2)
        res = self.s3mpu_obj.list_parts(mpu_id2, self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Abort multipart upload")
        resp = self.s3mpu_obj.abort_multipart_upload(self.mpu_partcopy_bkt,
                                                     self.mpu_partcopy_obj, mpu_id2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Stop and validate parallel S3 IOs")
        self.s3bio_obj.stop()
        self.log.info("ENDED: Test abort MPU-UploadPartCopy")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32720')
    @CTFailOn(error_handler)
    def test_mpu_upload_partcopy_32720(self):
        """Test is for uploading parts using bytge range for MPU-UploadPartCopy."""
        mp_config = MPART_CFG["test_32702_1"]
        multipart_obj_path = self.mp_obj_path
        if os.path.exists(multipart_obj_path):
            os.remove(multipart_obj_path)
        create_file(multipart_obj_path, mp_config["file_size"])
        mp_config_2 = MPART_CFG["test_32702_2"]
        if os.path.exists(self.mp_obj_path_partcopy):
            os.remove(self.mp_obj_path_partcopy)
        create_file(self.mp_obj_path_partcopy, mp_config_2["file_size"])
        put_checksum = calc_checksum(multipart_obj_path)
        self.log.info("STARTED: Upload object UploadPartCopy having part sizes within "
                      "aws part size limits limits using byte-range param")
        self.log.info("start s3 IO's")
        self.s3bio_obj.start(log_prefix="TEST-32720_s3bench_ios", duration="0h2m")
        self.create_and_complete_mpu(put_checksum, mp_config)
        self.log.info("Creating a bucket with name : %s", self.mpu_partcopy_bkt)
        res = self.s3t_obj.create_bucket(self.mpu_partcopy_bkt)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.mpu_partcopy_bkt, res[1])
        self.log.info("Created a bucket with name : %s", self.mpu_partcopy_bkt)
        mpu_id2 = self.initiate_multipart(self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        uploaded_parts2 = get_precalculated_parts(self.mp_obj_path_partcopy,
                                                  mp_config_2["part_sizes"],
                                                  chunk_size=mp_config_2["chunk_size"])
        uploaded_parts2.pop(2)  # removed part 2 as we are going to uplaod only one part here
        self.log.info("Uploading parts")
        status, new_parts = self.s3mpu_obj.upload_parts_sequential(mpu_id2,
                                                                   self.mpu_partcopy_bkt,
                                                                   self.mpu_partcopy_obj,
                                                                   parts=uploaded_parts2)
        assert_utils.assert_true(status, f"Failed to upload parts: {new_parts}")
        response = self.s3mpu_obj.upload_part_copy(self.bucket_name + "/" + self.object_name,
                                                   self.mpu_partcopy_bkt,
                                                   self.mpu_partcopy_obj,
                                                   copy_source_range="bytes=0-10485760",
                                                   part_number=2,
                                                   upload_id=mpu_id2)
        new_parts.append({"PartNumber": 2, "ETag": response[1]["CopyPartResult"]["ETag"]})
        response = self.s3mpu_obj.upload_part_copy(self.bucket_name + "/" + self.object_name,
                                                   self.mpu_partcopy_bkt,
                                                   self.mpu_partcopy_obj,
                                                   part_number=3,
                                                   upload_id=mpu_id2)
        new_parts.append({"PartNumber": 3, "ETag": response[1]["CopyPartResult"]["ETag"]})
        response = self.s3mpu_obj.upload_part_copy(self.bucket_name + "/" + self.object_name,
                                                   self.mpu_partcopy_bkt,
                                                   self.mpu_partcopy_obj,
                                                   copy_source_range="bytes=0-15728640",
                                                   part_number=4,
                                                   upload_id=mpu_id2)
        new_parts.append({"PartNumber": 4, "ETag": response[1]["CopyPartResult"]["ETag"]})
        res = self.s3mpu_obj.list_parts(mpu_id2, self.mpu_partcopy_bkt, self.mpu_partcopy_obj)
        assert_utils.assert_true(res[0], res[1])
        sorted_part_list = sorted(new_parts, key=lambda x: x['PartNumber'])
        self.log.info("Complete the multipart")
        resp = self.s3mpu_obj.complete_multipart_upload(mpu_id2, sorted_part_list,
                                                        self.mpu_partcopy_bkt,
                                                        self.mpu_partcopy_obj)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Stop and validate parallel S3 IOs")
        self.s3bio_obj.stop()
        self.log.info("ENDED: Upload object UploadPartCopy having part sizes within "
                      "aws part size limits limits using byte-range param")

    # pylint:disable-msg=too-many-statements
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32721')
    @CTFailOn(error_handler)
    def test_32721(self):
        """Upload 2 objects parallelly using uploadPartCopy."""
        self.log.info("STARTED: Upload 2 objects parallelly using uploadPartCopy.")
        self.log.info("Start S3 background IOs.")
        self.s3bio_obj.start(log_prefix="TEST-32721_s3bench_ios", duration="0h14m")
        self.log.info("Step 1: Create bucket1.")
        resp = self.s3t_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 2: Upload 10 parts of various sizes and in random order. The uploaded "
                      "parts can have sizes aligned and unaligned with motr unit sizes. "
                      "Make sure the entire object is > 5GB.")
        resp = create_file(self.mp_obj_path, count=6, b_size="1G")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3mpu_obj.complete_multipart_upload_with_di(
            self.bucket_name, self.object_name, self.mp_obj_path, total_parts=10, random=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Create bucket2.")
        resp = self.s3t_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 4: Initiate multipart upload by performing CreateMultipartUpload2.")
        resp = self.s3mpu_obj.create_multipart_upload(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id1 = resp[1]["UploadId"]
        parts1 = list()
        self.log.info("Step 5: Initiate multipart upload by performing CreateMultipartUpload3.")
        resp = self.s3mpu_obj.create_multipart_upload(self.bucket_name1, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id2 = resp[1]["UploadId"]
        parts2 = list()
        self.log.info("Step 6: Parallelly upload part1 by copying object1 to both these uploadIDs.")
        gevent_pool = GeventPool(2)
        gevent_pool.wait_available()
        # 'bytes=1-1073741824' 1GB object size.
        gevent_pool.spawn(self.s3mpu_obj.upload_part_copy, f"{self.bucket_name}/{self.object_name}",
                          self.bucket_name1, self.object_name1, part_number=1, upload_id=mpu_id1,
                          copy_source_range="bytes=0-1073741824")
        gevent_pool.spawn(self.s3mpu_obj.upload_part_copy, f"{self.bucket_name}/{self.object_name}",
                          self.bucket_name1, self.object_name2, part_number=1, upload_id=mpu_id2,
                          copy_source_range="bytes=0-1073741824")
        gevent_pool.join_group()
        responses = gevent_pool.result()
        self.log.info(responses)
        resp1 = responses.get("Greenlet-0",
                              (False, {"CopyPartResult": {"error": {"Execution failed."}}}))
        resp2 = responses.get("Greenlet-1",
                              (False, {"CopyPartResult": {"error": {"Execution failed."}}}))
        assert_utils.assert_true(resp1[0], resp1[1])
        parts1.append({"PartNumber": 1, "ETag": resp1[1]["CopyPartResult"]["ETag"]})
        assert_utils.assert_true(resp2[0], resp2[1])
        parts2.append({"PartNumber": 1, "ETag": resp2[1]["CopyPartResult"]["ETag"]})
        self.log.info("Step 7: Perform ListParts prallely on these 2 uploadIDs.")
        gevent_pool.spawn(self.s3mpu_obj.list_parts, mpu_id1, self.bucket_name1, self.object_name1)
        gevent_pool.spawn(self.s3mpu_obj.list_parts, mpu_id2, self.bucket_name1, self.object_name2)
        gevent_pool.join_group()
        responses = gevent_pool.result()
        self.log.info(responses)
        resp1 = responses.get("Greenlet-2", (False, {"error": "Execution failed."}))
        resp2 = responses.get("Greenlet-3", (False, {"error": "Execution failed."}))
        assert_utils.assert_true(resp1[0], resp1[1])
        assert_utils.assert_true(resp2[0], resp2[1])
        gevent_pool.shutdown()
        self.log.info("Step 8: Complete MPU for multipart1 and download it.")
        sorted_part_list = sorted(parts1, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3t_obj.object_download(
            self.bucket_name1, self.object_name1, self.mp_down_obj_pth)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 9: Complete MPU for multipart2 and download it.")
        sorted_part_list = sorted(parts2, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id2, sorted_part_list, self.bucket_name1, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3t_obj.object_download(
            self.bucket_name1, self.object_name2, self.mp_down_obj_pth)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Stop & validate S3 background IOs.")
        self.s3bio_obj.stop()
        self.s3bio_obj.validate()
        self.log.info("ENDED: Upload 2 objects parallelly using uploadPartCopy.")

    # pylint:disable-msg=too-many-statements
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32730')
    @CTFailOn(error_handler)
    def test_32730(self):
        """
        Upload part copy.

        Upload object UploadPartCopy having part sizes within aws part size limits using byte-range.
        """
        self.log.info("STARTED: Upload object UploadPartCopy using byte-range param")
        self.log.info("Start S3 background IOs.")
        self.s3bio_obj.start(log_prefix="TEST-32730_s3bench_ios", duration="0h9m")
        self.log.info("Step 1: Create bucket1.")
        resp = self.s3t_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 2: Upload 10 parts of various sizes and in random order. The uploaded "
                      "parts can have sizes aligned and unaligned with motr unit sizes."
                      " Make sure the entire object is <= 5GB")
        resp = create_file(self.mp_obj_path, count=7, b_size="533M")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3mpu_obj.complete_multipart_upload_with_di(
            self.bucket_name, self.object_name, self.mp_obj_path, total_parts=10, random=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Create bucket2.")
        resp = self.s3t_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 4: Initiate multipart upload by performing CreateMultipartUpload2.")
        resp = self.s3mpu_obj.create_multipart_upload(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id1 = resp[1]["UploadId"]
        parts = list()
        self.log.info("Step 5: Upload part1 by copying object1 to it.")
        response = self.s3mpu_obj.upload_part_copy(
            f"{self.bucket_name}/{self.object_name}", self.bucket_name1, self.object_name1,
            part_number=1, upload_id=mpu_id1, copy_source_range="bytes=0-1073741824")
        assert_utils.assert_true(response[0], response)
        parts.append({"PartNumber": 1, "ETag": response[1]["CopyPartResult"]["ETag"]})
        self.log.info("Step 6: Upload part part 2, 3 using simple upload.")
        resp = self.s3mpu_obj.upload_part(os.urandom(6291456), self.bucket_name1, self.object_name1,
                                          upload_id=mpu_id1, part_number=2)
        assert_utils.assert_true(resp[0], f"Failed to upload part2: {resp}")
        parts.append({"PartNumber": 2, "ETag": resp[1]["ETag"]})
        resp = self.s3mpu_obj.upload_part(os.urandom(5242880), self.bucket_name1, self.object_name1,
                                          upload_id=mpu_id1, part_number=3)
        assert_utils.assert_true(resp[0], f"Failed to upload part3: {resp}")
        parts.append({"PartNumber": 3, "ETag": resp[1]["ETag"]})
        self.log.info("Step 7: list the parts uploaded.")
        resp = self.s3mpu_obj.list_parts(mpu_id1, self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Parts: %s", parts)
        self.log.info("Step 8: Complete the MPU.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 9: Download multipart object.")
        resp = self.s3t_obj.object_download(
            self.bucket_name1, self.object_name1, self.mp_down_obj_pth)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Stop & validate S3 background IOs.")
        self.s3bio_obj.stop()
        self.s3bio_obj.validate()
        self.log.info("ENDED: Upload object UploadPartCopy using byte-range param")

    # pylint:disable-msg=too-many-statements
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32734')
    @CTFailOn(error_handler)
    def test_32734(self):
        """Overwrite the failed UploadCopyPart for byte range to successful uploadPartCopy."""
        self.log.info("STARTED: Overwrite the failed UploadCopyPart for byte range to successful.")
        self.log.info("Start S3 background IOs.")
        self.s3bio_obj.start(log_prefix="TEST-32734_s3bench_ios", duration="0h9m")
        self.log.info("Step 1: Create bucket1.")
        resp = self.s3t_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 2: Upload 10 parts of various sizes and in random order. The uploaded "
                      "parts can have sizes aligned and unaligned with motr unit sizes."
                      " Make sure the entire object is > 5GB.")
        resp = create_file(self.mp_obj_path, count=6, b_size="1G")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3mpu_obj.complete_multipart_upload_with_di(
            self.bucket_name, self.object_name, self.mp_obj_path, total_parts=10, random=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Create bucket2.")
        resp = self.s3t_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 4: Initiate multipart upload by performing CreateMultipartUpload.")
        resp = self.s3mpu_obj.create_multipart_upload(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id1 = resp[1]["UploadId"]
        parts = list()
        self.log.info("Step 5: Upload part2 by copying entire object1 >5GB to uploadID2.")
        try:
            response = self.s3mpu_obj.upload_part_copy(
                f"{self.bucket_name}/{self.object_name}", self.bucket_name1, self.object_name1,
                part_number=2, upload_id=mpu_id1, copy_source_range="bytes=0-6442450944")
            assert_utils.assert_false(response[0], response)
        except CTException as error:
            assert_utils.assert_in("EntityTooLarge", error.message)
        self.log.info("Step 6: Upload part1 by copying byte range < 5MB from object1 to uploadID2.")
        response = self.s3mpu_obj.upload_part_copy(
            f"{self.bucket_name}/{self.object_name}", self.bucket_name1, self.object_name1,
            part_number=1, upload_id=mpu_id1, copy_source_range="bytes=0-10")
        assert_utils.assert_true(response[0], response)
        parts.append({"PartNumber": 1, "ETag": response[1]["CopyPartResult"]["ETag"]})
        self.log.info("Step 7: Upload part2 by normal file upload.")
        resp = self.s3mpu_obj.upload_part(os.urandom(5242880), self.bucket_name1,
                                          self.object_name1, part_number=2, upload_id=mpu_id1)
        assert_utils.assert_true(resp[0], resp)
        parts.append({"PartNumber": 2, "ETag": resp[1]["ETag"]})
        try:
            resp = self.s3mpu_obj.complete_multipart_upload(
                mpu_id1, parts, self.bucket_name1, self.object_name1)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_utils.assert_in("EntityTooSmall", error.message)
        self.log.info("Step 8: Upload part1 by copying byte range within upload part size limits.")
        response = self.s3mpu_obj.upload_part_copy(
            f"{self.bucket_name}/{self.object_name}", self.bucket_name1, self.object_name1,
            part_number=1, upload_id=mpu_id1, copy_source_range="bytes=0-1073741824")
        assert_utils.assert_true(response[0], response)
        parts.pop(0)
        parts.append({"PartNumber": 1, "ETag": response[1]["CopyPartResult"]["ETag"]})
        self.log.info("Step 9: list the parts uploaded.")
        resp = self.s3mpu_obj.list_parts(mpu_id1, self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Parts: %s", parts)
        self.log.info("Step 10: Complete the MPU.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 11: Download multipart object.")
        resp = self.s3t_obj.object_download(
            self.bucket_name1, self.object_name1, self.mp_down_obj_pth)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Stop & validate S3 background IOs.")
        self.s3bio_obj.stop()
        self.s3bio_obj.validate()
        self.log.info("ENDED: Overwrite the failed UploadCopyPart for byte range to successful.")

    # pylint:disable-msg=too-many-statements
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32737')
    @CTFailOn(error_handler)
    def test_32737(self):
        """Uploading part using UploadPartCopy which is from another account."""
        self.log.info("STARTED: Uploading part using UploadPartCopy which is from another account.")
        self.log.info("Start S3 background IOs.")
        self.s3bio_obj.start(log_prefix="TEST-32737_s3bench_ios", duration="0h5m")
        s3_account1 = self.acc_name_prefix.format(perf_counter_ns())
        response = cmn_lib.create_s3_account_get_s3lib_objects(
            s3_account1, self.acc_email_prefix.format(s3_account1), self.s3acc_passwd)
        self.account_list.append(s3_account1)
        self.log.info("Step 1: Create bucket1")
        resp = response[1].create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp)
        self.s3t_obj_list.append(response[1])
        self.log.info("Step 2: Upload 10 parts of various sizes and in random order.")
        resp = create_file(self.mp_obj_path, count=4, b_size="1G")
        assert_utils.assert_true(resp[0], resp[1])
        resp = response[8].complete_multipart_upload_with_di(
            self.bucket_name, self.object_name, self.mp_obj_path, total_parts=10, random=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Create bucket2 in account 2 and have the default settings. Meaning,"
                      " account account 2 does not have read permission on account1’s resources.")
        s3_account2 = self.acc_name_prefix.format(perf_counter_ns())
        response1 = cmn_lib.create_s3_account_get_s3lib_objects(
            s3_account2, self.acc_email_prefix.format(s3_account2), self.s3acc_passwd)
        self.account_list.append(s3_account2)
        resp = response1[1].create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp)
        self.s3t_obj_list.append(response1[1])
        self.log.info("Step 4: Initiate multipart upload by performing CreateMultipartUpload.")
        resp = response1[8].create_multipart_upload(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id1 = resp[1]["UploadId"]
        parts = list()
        self.log.info("Step 5: Upload part 2 by copying entire object 1 to uploadID 2.")
        try:
            resp = response1[8].upload_part_copy(
                f"{self.bucket_name}/{self.object_name}", self.bucket_name1, self.object_name1,
                part_number=2, upload_id=mpu_id1, copy_source_range="bytes=0-4294967296")
            assert_utils.assert_false(resp[0], resp)
        except CTException as error:
            assert_utils.assert_in(errconst.ACCESS_DENIED_ERR_KEY, error.message)
        self.log.info("Step 6: Upload part 1 by using regular file upload.")
        resp = response1[8].upload_part(os.urandom(5242880), self.bucket_name1,
                                        self.object_name1, part_number=1, upload_id=mpu_id1)
        assert_utils.assert_true(resp[0], resp)
        parts.append({"PartNumber": 1, "ETag": resp[1]["ETag"]})
        self.log.info("Step 7: Give read permission to account 2 on account 1.")
        resp = response[2].put_object_canned_acl(self.bucket_name, self.object_name,
                                                 grant_read="{}{}".format("id=", response1[0]))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 8: After that upload part 2 by copying entire object 1.")
        resp = response1[8].upload_part_copy(
            f"{self.bucket_name}/{self.object_name}", self.bucket_name1, self.object_name1,
            part_number=2, upload_id=mpu_id1, copy_source_range="bytes=0-4294967296")
        assert_utils.assert_true(resp[0], resp)
        parts.append({"PartNumber": 2, "ETag": resp[1]["CopyPartResult"]["ETag"]})
        self.log.info("Step 9: list the parts uploaded.")
        resp = response1[8].list_parts(mpu_id1, self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Parts: %s", parts)
        self.log.info("Step 10: Complete the MPU.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = response1[8].complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 11: Download multipart object.")
        resp = response1[1].object_download(
            self.bucket_name1, self.object_name1, self.mp_down_obj_pth)
        assert_utils.assert_true(resp[0], resp[1])
        resp = response[2].put_object_canned_acl(self.bucket_name, self.object_name, acl="private")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Stop & validate S3 background IOs.")
        self.s3bio_obj.stop()
        self.s3bio_obj.validate()
        self.log.info("ENDED: Uploading part using UploadPartCopy which is from another account.")
