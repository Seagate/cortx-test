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

"""Multipart Upload delete test module."""

import os
import logging
import time
from time import perf_counter_ns

import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.utils import s3_utils
from config.s3 import S3_CFG
from config.s3 import MPART_CFG

from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_common_test_lib import S3BackgroundIO
from libs.s3.s3_common_test_lib import get_cortx_capacity
from libs.s3.s3_common_test_lib import upload_random_size_objects
from libs.s3.s3_common_test_lib import create_s3_account_get_s3lib_objects
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI


class TestMultipartUploadDelete:
    """Multipart Upload Delete Test Suite."""

    # pylint: disable=too-many-instance-attributes
    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations.")
        self.bucket_name = "s3-bkt-{}".format(perf_counter_ns())
        self.object_name = "s3-upload-obj-{}".format(perf_counter_ns())
        self.acc_name = "s3-acc-{}"
        self.acc_mail = "{}@seagate.com"
        self.acc_password = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.s3_test_obj = S3TestLib()
        self.s3_mp_test_obj = S3MultipartTestLib()
        self.s3_rest_obj = S3AccountOperationsRestAPI()
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "MultipartUploadDelete")
        self.s3_accounts = []
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
        self.file_path = os.path.join(self.test_dir_path, self.object_name)
        self.download_path = os.path.join(self.test_dir_path, "s3-obj-{}".format(perf_counter_ns()))
        self.group_uri = "uri=http://acs.amazonaws.com/groups/global/AllUsers"
        self.log.info("Setting up S3 background IO")
        self.s3_background_io = S3BackgroundIO(s3_test_lib_obj=self.s3_test_obj)
        self.log.info("ENDED: Setup operations.")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        self.log.info("STARTED: Teardown operations")
        if system_utils.path_exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)
        resp = self.s3_test_obj.bucket_list()[1]
        if self.bucket_name in resp:
            resp = self.s3_test_obj.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        for s3acc in self.s3_accounts:
            self.s3_rest_obj.delete_s3_account(s3acc)
        self.s3_background_io.cleanup()
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.skip(reason=" size is not supported on vm hence marking skip.")
    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29163')
    @CTFailOn(error_handler)
    def test_29163(self):
        """
        Delete multipart object limit test.
        Abort multipart upload completed object with size 5TB and max parts 10000 and then
        delete that object.
        """
        self.log.info("STARTED: Abort multipart upload completed object with size 5TB and max parts"
                      " 10000 and then delete that object")
        cortx_capacity1 = get_cortx_capacity()
        self.log.info("Step 1: Create bucket.")
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)
        self.log.info("Step 2: Initiate multipart upload by performing CreateMultipartUpload.")
        res = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Step 3: Upload 5TB(max size) Object with random 10000 parts.")
        resp = system_utils.create_file(self.file_path, count=MPART_CFG["test_29163"]["file_size"])
        assert_utils.assert_true(resp[0], resp[1])
        put_checksum = s3_utils.calc_checksum(self.file_path)
        chunks = s3_utils.get_unaligned_parts(
            self.file_path, total_parts=MPART_CFG["test_29163"]["total_parts"], random=True)
        status, parts = self.s3_mp_test_obj.upload_parts_sequential(
            mpu_id, self.bucket_name, self.object_name, parts=chunks)
        assert_utils.assert_true(status, f"Failed to upload parts: {parts}")
        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        for _ in range(10):
            res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
            assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 5: Perform CompleteMultipartUpload.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id, sorted_part_list, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: Verify uploaded object and downloaded object are identical.")
        resp = self.s3_test_obj.object_download(
            self.bucket_name, self.object_name, self.download_path)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = s3_utils.calc_checksum(self.download_path)
        assert_utils.assert_equal(put_checksum, download_checksum, "Data Integrity failed.")
        self.log.info("Step 7: Abort Multipart Upload using AbortMultipartUpload API.")
        resp = self.s3_mp_test_obj.abort_multipart_upload(
            self.bucket_name, self.object_name, mpu_id)
        assert_utils.assert_false(resp[0], resp[1])
        self.log.info("Step 8: Delete the object using DeleteObject API.")
        resp = self.s3_test_obj.delete_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 9: List the contents of bucket to verify object deleted.")
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_not_in(self.object_name, resp[1],
                                   f"Failed to delete object {self.object_name}")
        self.log.info("Step 10: Check the space reclaim after 6 hrs.")
        time.sleep(MPART_CFG["test_29163"]["delay"])
        cortx_capacity2 = get_cortx_capacity()
        assert cortx_capacity1[-1] <= cortx_capacity2[-1], "Space not reclaimed."
        self.log.info("ENDED: Abort multipart upload completed object with size 5TB and max parts"
                      " 10000 and then delete that object")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29169')
    @CTFailOn(error_handler)
    def test_29169(self):
        """
        Delete multipart.
        Initiate multipart and try to delete the object before even uploading parts to it, Then
        upload parts and complete multipart upload
        """
        self.log.info("STARTED: Initiate multipart and try to delete the object before even "
                      "uploading parts to it, Then upload parts and complete multipart upload.")
        self.log.info("Start S3 IO.")
        self.s3_background_io.start(log_prefix="TEST-29169_s3bench_ios", duration="0h2m")
        self.log.info("Step 1: Create bucket.")
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)
        self.log.info("Step 2: Initiate multipart upload by performing CreateMultipartUpload.")
        res = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Step 3: Delete the object using DeleteObject API.")
        resp = self.s3_test_obj.delete_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Upload multiple parts of various size.")
        resp = system_utils.create_file(self.file_path, count=MPART_CFG["test_29169"]["file_size"])
        assert_utils.assert_true(resp[0], resp[1])
        chunks = s3_utils.get_unaligned_parts(
            self.file_path, total_parts=MPART_CFG["test_29169"]["total_parts"], random=True)
        status, parts = self.s3_mp_test_obj.upload_parts_sequential(
            mpu_id, self.bucket_name, self.object_name, parts=chunks)
        assert_utils.assert_true(status, f"Failed to upload parts: {parts}")
        self.log.info("Step 5: Do ListParts to see the parts uploaded.")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: Perform CompleteMultipartUpload.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id, sorted_part_list, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 7: List the contents of bucket to verify object is not deleted.")
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, resp[1],
                               f"Object is not present {self.object_name}")
        self.log.info("Stop S3 IO & Validate logs.")
        self.s3_background_io.stop()
        self.log.info("ENDED: Initiate multipart and try to delete the object before even "
                      "uploading parts to it, Then upload parts and complete multipart upload.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29171')
    @CTFailOn(error_handler)
    def test_29171(self):
        """
        Delete multipart.
        Delete multiple objects in bucket which are uploaded and not uploaded completely
        """
        self.log.info("STARTED: Delete multiple objects in bucket which are uploaded and not"
                      " uploaded completely.")
        self.s3_background_io.start(log_prefix="TEST-29171_s3bench_ios", duration="0h1m")
        self.log.info("Step 1: Create bucket.")
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)
        self.log.info("Step 2: Upload 3 (random number)objects using simple upload.")
        objects = upload_random_size_objects(
            self.s3_test_obj, self.bucket_name, num_sample=MPART_CFG["test_29171"]["num_sample"])
        assert_utils.assert_equal(
            len(objects), MPART_CFG["test_29171"]["num_sample"], "Failed to create/upload objects.")
        self.log.info("Step 3: Initiate multipart upload by performing CreateMultipartUpload.")
        res = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Step 4: Upload multiple parts of various size.")
        resp = system_utils.create_file(self.file_path, count=MPART_CFG["test_29171"]["file_size"])
        assert_utils.assert_true(resp[0], resp[1])
        chunks = s3_utils.get_unaligned_parts(
            self.file_path, total_parts=MPART_CFG["test_29171"]["total_parts"], random=True)
        status, parts = self.s3_mp_test_obj.upload_parts_sequential(
            mpu_id, self.bucket_name, self.object_name, parts=chunks)
        assert_utils.assert_true(status, f"Failed to upload parts: {parts}")
        self.log.info("Step 5: Do ListParts to see the parts uploaded.")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: Perform CompleteMultipartUpload.")
        sorted_part_list = sorted(parts, key=lambda x: x['PartNumber'])
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id, sorted_part_list, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 7: Initiate 5th objectUpload by performing CreateMultipartUpload.")
        res = self.s3_mp_test_obj.create_multipart_upload(
            self.bucket_name, f"{self.object_name}-{1}")
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 8: list the contents of bucket should show four objects.")
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_not_in(f"{self.object_name}-{1}", resp[1])
        self.log.info("Step 9: Delete all objects from bucket.")
        resp = self.s3_test_obj.object_list(self.bucket_name)[1]
        resp = self.s3_test_obj.delete_multiple_objects(self.bucket_name, resp[1])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Stop S3 IO & Validate logs.")
        self.s3_background_io.stop()
        self.log.info("ENDED: Delete multiple objects in bucket which are uploaded and not"
                      " uploaded completely.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29172')
    @CTFailOn(error_handler)
    def test_29172(self):
        """
        Delete multipart.
        Upload object2 in bucket1 of accnt1 from accnt 2 and try to delete object from both
        accnt1 and accnt2.
        """
        self.log.info("STARTED: Upload object2 in bucket1 of accnt1 from accnt 2 and try to delete"
                      " object from both accnt1 and accnt2.")
        self.s3_background_io.start(log_prefix="TEST-29172_s3bench_ios", duration="0h1m")
        self.log.info("Step 1: Multipart upload an object1 in bucket1 from accnt1")
        acc1 = self.acc_name.format(perf_counter_ns())
        acc_resp1 = create_s3_account_get_s3lib_objects(
            acc1, self.acc_mail.format(acc1), self.acc_password)
        self.s3_accounts.append(acc1)
        acc2 = self.acc_name.format(perf_counter_ns())
        acc_resp2 = create_s3_account_get_s3lib_objects(
            acc2, self.acc_mail.format(acc2), self.acc_password)
        self.s3_accounts.append(acc2)
        resp = acc_resp1[1].create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        acc_resp1[-1].simple_multipart_upload(
            self.bucket_name, self.object_name, MPART_CFG["test_29172"]["file_size"],
            self.file_path, parts=MPART_CFG["test_29172"]["total_parts"])
        self.log.info("Step 2: list contents of bucket1.")
        resp = acc_resp1[1].object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Grant accnt2 a write permission on bucket of accnt1.")
        resp = acc_resp1[2].put_bucket_acl(
            bucket_name=self.bucket_name,
            grant_full_control=self.group_uri)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: upload object2 from accnt 2 to accnt1's bucket.")
        acc_resp2[-1].simple_multipart_upload(
            self.bucket_name, f"{self.object_name}-{1}", MPART_CFG["test_29172"]["file_size"],
            self.file_path, parts=MPART_CFG["test_29172"]["total_parts"])
        self.log.info("Step 5: list contents of bucket1.")
        resp = acc_resp1[1].object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(f"{self.object_name}-{1}", resp[1])
        self.log.info("Step 6: DeleteObjects object1 from accnt1.")
        resp = acc_resp1[1].delete_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 7: DeleteObjects from accnt2.")
        resp = acc_resp2[1].delete_object(self.bucket_name, f"{self.object_name}-{1}")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Stop S3 IO & Validate logs.")
        self.s3_background_io.stop()
        self.log.info("ENDED: Upload object2 in bucket1 of accnt1 from accnt 2 and try to delete"
                      " object from both accnt1 and accnt2.")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-29173')
    @CTFailOn(error_handler)
    def test_29173(self):
        """
        Delete multipart.
        Check Space reclaim after Deleting an object 1hr.
        """
        self.log.info("STARTED: Check Space reclaim after Deleting an object 1hr.")
        cortx_capacity1 = get_cortx_capacity()
        self.log.info("Step 1: Create bucket.")
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)
        self.log.info("Step 2: Initiate multipart performing CreateMultipartUpload.")
        res = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Step 3: Upload 20GB Object : Upload 20 parts of various sizes.")
        resp = system_utils.create_file(self.file_path, count=MPART_CFG["test_29173"]["file_size"])
        assert_utils.assert_true(resp[0], resp[1])
        status, mpu_upload = self.s3_mp_test_obj.upload_precalculated_parts(
            mpu_id, self.bucket_name, self.object_name, multipart_obj_path=self.file_path,
            part_sizes=MPART_CFG["test_29173"]["part_sizes"],
            chunk_size=MPART_CFG["test_29173"]["chunk_size"])
        assert_utils.assert_true(status, f"Failed to upload parts: {mpu_upload}")
        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 5: uploaded perform CompleteMultipartUpload.")
        sorted_part_list = sorted(mpu_upload["uploaded_parts"], key=lambda x: x['PartNumber'])
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id, sorted_part_list, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(mpu_upload["expected_etag"], res[1]["ETag"])
        self.log.info("Step 6: Delete the object.")
        resp = self.s3_test_obj.delete_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 7: Check space reclaim after 1hr.")
        time.sleep(MPART_CFG["test_29173"]["delay"])
        cortx_capacity2 = get_cortx_capacity()
        assert cortx_capacity1[-1] <= cortx_capacity2[-1], "Space not reclaimed."
        self.log.info("ENDED: Check Space reclaim after Deleting an object 1hr.")
