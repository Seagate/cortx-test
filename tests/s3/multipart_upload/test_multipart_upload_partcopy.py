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

"""Multipart upload PartCopy object test module."""

import logging
import os
from time import perf_counter_ns

import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.system_utils import create_file, remove_file, path_exists
from commons.utils.system_utils import make_dirs, remove_dirs
from commons.utils import assert_utils
from commons.utils import s3_utils
from commons.params import TEST_DATA_FOLDER
from commons.greenlet_worker import GeventPool
from libs.s3 import S3_CFG
from libs.s3 import s3_common_test_lib as cmn_lib
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_common_test_lib import S3BackgroundIO
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI


# pylint:disable-msg=too-many-instance-attributes
class TestMultipartUploadPartCopy:
    """Multipart Upload PartCopy Test Suite."""

    # pylint:disable=attribute-defined-outside-init
    @pytest.yield_fixture(autouse=True)
    def setup(self):
        """Setup method is called before/after each test in this test suite."""
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.test_file = "mpu_obj-{}".format(perf_counter_ns())
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestMultipartUploadRedesign")
        self.mp_obj_path = os.path.join(self.test_dir_path, self.test_file)
        if not path_exists(self.test_dir_path):
            make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.acc_name_prefix = "mpu-s3acc-{}"
        self.acc_email_prefix = "{}@seagate.com"
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.bucket_name = "mpu-bkt-{}".format(perf_counter_ns())
        self.io_bucket_name = "mpu-io-bkt-{}".format(perf_counter_ns())
        self.bucket_name1 = "mpu-bkt1-{}".format(perf_counter_ns())
        self.bucket_name2 = "mpu-bkt2-{}".format(perf_counter_ns())
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
                resp = self.s3t_obj.delete_multiple_buckets(resp[1])
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

    # pylint:disable-msg=too-many-statements
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-32721')
    @CTFailOn(error_handler)
    def test_32721(self):
        """Upload 2 objects parallelly using uploadPartCopy."""
        self.log.info("STARTED: Upload 2 objects parallelly using uploadPartCopy.")
        self.log.info("Start S3 background IOs.")
        self.s3bio_obj.start(log_prefix="TEST-32721_s3bench_ios", duration="0h2m")
        self.log.info("Step 1: Create bucket1.")
        resp = self.s3t_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 2: Initiate multipart upload by performing CreateMultipartUpload1.")
        resp = self.s3mpu_obj.create_multipart_upload(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id1 = resp[1]["UploadId"]
        self.log.info("Step 3: Upload 10 parts of various sizes and in random order. The uploaded "
                      "parts can have sizes aligned and unaligned with motr unit sizes. "
                      "Make sure the entire object is > 5GB.")
        resp = create_file(self.test_file, count=6, b_size="1G")
        assert_utils.assert_true(resp[0], resp[1])
        chunks = s3_utils.get_unaligned_parts(
            self.test_file, total_parts=10, random=True)
        status, parts = self.s3mpu_obj.upload_parts_sequential(
            mpu_id1, self.bucket_name, self.object_name, parts=chunks)
        assert_utils.assert_true(status, f"Failed to upload parts: {parts}")
        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        resp = self.s3mpu_obj.list_parts(mpu_id1, self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        parts = resp[1]["Parts"]
        self.log.info("Parts: %s", parts)
        self.log.info("Step 5: Get the part details and perform CompleteMultipartUpload.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Create bucket2.")
        resp = self.s3t_obj.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 7: Initiate multipart upload by performing CreateMultipartUpload2.")
        resp = self.s3mpu_obj.create_multipart_upload(self.bucket_name2, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id2 = resp[1]["UploadId"]
        self.log.info("Step 8: Initiate multipart upload by performing CreateMultipartUpload3.")
        resp = self.s3mpu_obj.create_multipart_upload(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id1 = resp[1]["UploadId"]
        self.log.info("Step 9: Parallelly upload part1 by copying object1 to both these uploadIDs.")
        gevent_pool = GeventPool(2)
        gevent_pool.wait_available()
        gevent_pool.spawn(self.s3mpu_obj.upload_part_copy, f"{self.bucket_name}/{self.object_name}",
                          self.bucket_name2, self.object_name1, part_number=1, upload_id=mpu_id2,
                          copy_source_range="'bytes=1-100000'")
        gevent_pool.spawn(self.s3mpu_obj.upload_part_copy, f"{self.bucket_name}/{self.object_name}",
                          self.bucket_name2, self.object_name2, part_number=1, upload_id=mpu_id2,
                          copy_source_range="'bytes=1-100000'")
        gevent_pool.join_group()
        responses = gevent_pool.result()
        self.log.info(responses)
        resp1 = responses.get("Greenlet-0", (False, "Execution failed."))
        resp2 = responses.get("Greenlet-1", (False, "Execution failed."))
        assert_utils.assert_true(resp1[0], resp1[1])
        assert_utils.assert_true(resp2[0], resp2[1])
        self.log.info("Step 10: Perform ListParts prallely on these 2 uploadIDs.")
        gevent_pool.spawn(self.s3mpu_obj.list_parts, mpu_id1, self.bucket_name2, self.object_name1)
        gevent_pool.spawn(self.s3mpu_obj.list_parts, mpu_id1, self.bucket_name2, self.object_name2)
        gevent_pool.join_group()
        responses = gevent_pool.result()
        self.log.info(responses)
        resp1 = responses.get("Greenlet-2", (False, "Execution failed."))
        resp2 = responses.get("Greenlet-3", (False, "Execution failed."))
        assert_utils.assert_true(resp1[0], resp1[1])
        assert_utils.assert_true(resp2[0], resp2[1])
        gevent_pool.shutdown()
        self.log.info("Step 11: Complete MPU for both uploadIDs.")
        parts = resp1[1]["Parts"]
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name2, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        parts = resp2[1]["Parts"]
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name2, self.object_name2)
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
        self.s3bio_obj.start(log_prefix="TEST-32730_s3bench_ios", duration="0h2m")
        self.log.info("Step 1: Create bucket1.")
        resp = self.s3t_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 2: Initiate multipart upload by performing CreateMultipartUpload.")
        resp = self.s3mpu_obj.create_multipart_upload(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id1 = resp[1]["UploadId"]
        self.log.info("Step 3: Upload 10 parts of various sizes and in random order. The uploaded "
                      "parts can have sizes aligned and unaligned with motr unit sizes."
                      " Make sure the entire object is <= 5GB")
        resp = create_file(self.test_file, count=9, b_size="533M")
        assert_utils.assert_true(resp[0], resp[1])
        chunks = s3_utils.get_unaligned_parts(
            self.test_file, total_parts=10, random=True)
        status, parts = self.s3mpu_obj.upload_parts_sequential(
            mpu_id1, self.bucket_name, self.object_name, parts=chunks)
        assert_utils.assert_true(status, f"Failed to upload parts: {parts}")
        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        resp = self.s3mpu_obj.list_parts(mpu_id1, self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Get the part details and perform CompleteMultipartUpload.")
        parts = resp[1]["Parts"]
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Create bucket2.")
        resp = self.s3t_obj.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 7: Initiate multipart upload by performing CreateMultipartUpload2.")
        resp = self.s3mpu_obj.create_multipart_upload(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id2 = resp[1]["UploadId"]
        self.log.info("Step 8: Upload part1 by copying object1 to it.")
        response = self.s3mpu_obj.upload_part_copy(
            f"{self.bucket_name}/{self.object_name}", self.bucket_name2, self.object_name2,
            part_number=1, upload_id=mpu_id2)
        assert_utils.assert_true(response[0], response)
        self.log.info("Step 9: Upload part part 2, 3 using simple upload.")
        resp = self.s3mpu_obj.upload_part(
            os.urandom(5000), self.bucket_name, self.object_name, upload_id=mpu_id2, part_number=2)
        assert_utils.assert_true(resp[0], f"Failed to upload part2: {resp}")
        resp = self.s3mpu_obj.upload_part(
            os.urandom(3000), self.bucket_name, self.object_name, upload_id=mpu_id2, part_number=3)
        assert_utils.assert_true(resp[0], f"Failed to upload part3: {resp}")
        self.log.info("Step 10: list the parts uploaded.")
        resp = self.s3mpu_obj.list_parts(mpu_id1, self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        parts = resp[1]["Parts"]
        self.log.info("Parts: %s", parts)
        self.log.info("Step 11: Complete the MPU.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name2, self.object_name2)
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
        self.s3bio_obj.start(log_prefix="TEST-32734_s3bench_ios", duration="0h2m")
        self.log.info("Step 1: Create bucket1.")
        resp = self.s3t_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 2: Initiate multipart upload by performing CreateMultipartUpload.")
        resp = self.s3mpu_obj.create_multipart_upload(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id1 = resp[1]["UploadId"]
        self.log.info("Step 3: Upload 10 parts of various sizes and in random order. The uploaded "
                      "parts can have sizes aligned and unaligned with motr unit sizes."
                      " Make sure the entire object is > 5GB.")
        resp = create_file(self.test_file, count=11, b_size="1G")
        assert_utils.assert_true(resp[0], resp[1])
        chunks = s3_utils.get_unaligned_parts(self.test_file, total_parts=10, random=True)
        status, parts = self.s3mpu_obj.upload_parts_sequential(
            mpu_id1, self.bucket_name, self.object_name, parts=chunks)
        assert_utils.assert_true(status, f"Failed to upload parts: {parts}")
        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        resp = self.s3mpu_obj.list_parts(mpu_id1, self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        parts = resp[1]["Parts"]
        self.log.info("Parts: %s", parts)
        self.log.info("Step 5: Get the part details and perform CompleteMultipartUpload.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Create bucket2.")
        resp = self.s3t_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 7: Initiate multipart upload by performing CreateMultipartUpload.")
        resp = self.s3mpu_obj.create_multipart_upload(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id2 = resp[1]["UploadId"]
        self.log.info("Step 8: Upload part2 by copying entire object1 >5GB to uploadID2.")
        try:
            response = self.s3mpu_obj.upload_part_copy(
                f"{self.bucket_name}/{self.object_name}", self.bucket_name2, self.object_name2,
                part_number=2, upload_id=mpu_id2)
            assert_utils.assert_false(response[0], response)
        except CTException as error:
            assert_utils.assert_in("InvalidParts", error.message)
        self.log.info("Step 9: Upload part1 by copying byte range > 5MB from object1 to uploadID2.")
        try:
            response = self.s3mpu_obj.upload_part_copy(
                f"{self.bucket_name}/{self.object_name}", self.bucket_name2, self.object_name2,
                part_number=1, upload_id=mpu_id2, copy_source_range="'bytes=1-10'")
            assert_utils.assert_false(response[0], response)
        except CTException as error:
            assert_utils.assert_in("InvalidParts", error.message)
        self.log.info("Step 10: Upload part2 by normal file upload.")
        resp = self.s3mpu_obj.upload_part(os.urandom(1000), self.bucket_name2,
                                          self.object_name2, part_number=2, upload_id=mpu_id2)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 11: Upload part1 by copying byte range within upload part size limits.")
        response = self.s3mpu_obj.upload_part_copy(
            f"{self.bucket_name}/{self.object_name}", self.bucket_name2, self.object_name2,
            part_number=1, upload_id=mpu_id2, copy_source_range="'bytes=1-1073741824'")
        assert_utils.assert_false(response[0], response)
        self.log.info("Step 12: list the parts uploaded.")
        resp = self.s3mpu_obj.list_parts(mpu_id1, self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        parts = resp[1]["Parts"]
        self.log.info("Parts: %s", parts)
        self.log.info("Step 13: Complete the MPU.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = self.s3mpu_obj.complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name2, self.object_name2)
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
        self.s3bio_obj.start(log_prefix="TEST-32737_s3bench_ios", duration="0h2m")
        s3_account1 = self.acc_name_prefix.format(perf_counter_ns())
        response = cmn_lib.create_s3_account_get_s3lib_objects(
            s3_account1, self.acc_email_prefix.format(s3_account1), self.s3acc_passwd)
        self.account_list.append(s3_account1)
        self.log.info("Step 1: Create bucket1")
        resp = response[1].create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp)
        self.s3t_obj_list.append(response[1])
        self.log.info("Step 2: Initiate multipart upload by performing CreateMultipartUpload.")
        resp = response[8].create_multipart_upload(self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id1 = resp[1]["UploadId"]
        self.log.info("Step 3: Upload 10 parts of various sizes and in random order.")
        resp = create_file(self.test_file, count=5, b_size="1G")
        assert_utils.assert_true(resp[0], resp[1])
        chunks = s3_utils.get_unaligned_parts(
            self.test_file, total_parts=10, random=True)
        status, parts = response[8].upload_parts_sequential(
            mpu_id1, self.bucket_name, self.object_name, parts=chunks)
        assert_utils.assert_true(status, f"Failed to upload parts: {parts}")
        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        resp = response[8].list_parts(mpu_id1, self.bucket_name1, self.object_name1)
        assert_utils.assert_true(resp[0], resp[1])
        parts = resp[1]["Parts"]
        self.log.info("Parts: %s", parts)
        self.log.info("Step 5: Get the part details and perform CompleteMultipartUpload.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = response[8].complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Create bucket2 in account 2 and have the default settings. Meaning,"
                      " account account 2 does not have read permission on account1’s resources.")
        s3_account2 = self.acc_name_prefix.format(perf_counter_ns())
        response1 = cmn_lib.create_s3_account_get_s3lib_objects(
            s3_account2, self.acc_email_prefix.format(s3_account2), self.s3acc_passwd)
        self.account_list.append(s3_account2)
        resp = response1[1].create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp)
        self.s3t_obj_list.append(response1[1])
        self.log.info("Step 7: Initiate multipart upload by performing CreateMultipartUpload.")
        resp = response1[8].create_multipart_upload(self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id2 = resp[1]["UploadId"]
        self.log.info("Step 8: Upload part 2 by copying entire object 1 to uploadID 2.")
        try:
            response = response1[8].upload_part_copy(
                f"{self.bucket_name1}/{self.object_name1}", self.bucket_name2, self.object_name2,
                part_number=1, upload_id=mpu_id2, copy_source_range="'bytes=1-10'")
            assert_utils.assert_false(response[0], response)
        except CTException as error:
            assert_utils.assert_in("InvalidParts", error.message)
        self.log.info("Step 9: Upload part 1 by using regular file upload.")
        resp = response1[8].upload_part(os.urandom(1000), self.bucket_name2,
                                        self.object_name2, part_number=2, upload_id=mpu_id2)
        assert_utils.assert_true(resp[0], resp)
        self.log.info("Step 10: Give read permission to account 2 on account 1.")
        resp = response1[2].put_bucket_acl(self.bucket_name1,
                                           grant_read="{}{}".format("id=", response1[0]))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 11: After that upload part 2 by copying entire object 1.")
        response = response1[8].upload_part_copy(
            f"{self.bucket_name1}/{self.object_name1}", self.bucket_name2, self.object_name2,
            part_number=2, upload_id=mpu_id2)
        assert_utils.assert_true(response[0], response)
        self.log.info("Step 12: list the parts uploaded.")
        resp = response1[8].list_parts(mpu_id1, self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        parts = resp[1]["Parts"]
        self.log.info("Parts: %s", parts)
        self.log.info("Step 13: Complete the MPU.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        resp = response1[8].complete_multipart_upload(
            mpu_id1, sorted_part_list, self.bucket_name2, self.object_name2)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Stop & validate S3 background IOs.")
        self.s3bio_obj.stop()
        self.s3bio_obj.validate()
        self.log.info("ENDED: Uploading part using UploadPartCopy which is from another account.")
