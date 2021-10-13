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

"""Multipart Upload delete test module."""

import os
import logging
from time import perf_counter_ns

import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from commons.utils import assert_utils
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib


class TestMultipartUploadDelete:
    """Multipart Upload Delete Test Suite."""

    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup operations")
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "MultipartUploadDelete")
        self.bucket_name = "s3-bkt-MultipartUploadDelete-{}".format(perf_counter_ns())
        self.object_name = "s3-obj-MultipartUploadDelete-{}".format(perf_counter_ns())
        self.acc_name = "s3-acc-{}".format(perf_counter_ns())
        self.s3_test_obj = S3TestLib()
        self.s3_mp_test_obj = S3MultipartTestLib()
        self.file_path = os.path.join(self.test_dir_path, self.object_name)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        self.log.info("STARTED: Teardown operations")
        if system_utils.path_exists(self.test_dir_path):
            system_utils.remove_dirs(self.test_dir_path)
        resp = self.s3_test_obj.delete_bucket(self.bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: Teardown operations")

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
        resp = system_utils.create_file(self.file_path, count=1000)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 5: Perform CompleteMultipartUpload.")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id, None, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: Verify uploaded object and downloaded object are identical.")

        self.log.info("Step 7: Abort Multipart Upload using AbortMultipartUpload API.")
        resp = self.s3_mp_test_obj.abort_multipart_upload(
            self.bucket_name, self.object_name, mpu_id)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 8: Delete the object using DeleteObject API.")
        resp = self.s3_test_obj.delete_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 9: List the contents of bucket to verify object deleted.")
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_not_in(self.object_name, resp[1],
                                   f"Failed to delete object {self.object_name}")
        self.log.info("Step 10: Check the space reclaim after 6 hrs.")
        # TODO: Logic to check space reclaimed.
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

        self.log.info("Step 5: Do ListParts to see the parts uploaded.")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: Perform CompleteMultipartUpload.")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id, None, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 7: List the contents of bucket to verify object deleted.")
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
        self.log.info("Step 1: Create bucket.")
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)
        self.log.info("Step 2: Upload 3 (random number)objects using simple upload.")
        self.log.info("Step 3: Initiate multipart upload by performing CreateMultipartUpload.")
        res = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Step 4: Upload multiple parts of various size.")
        self.log.info("Step 5: Do ListParts to see the parts uploaded.")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: Perform CompleteMultipartUpload.")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id, None, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 7: Initiate 5th objectUpload by performing CreateMultipartUpload.")
        res = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 8: list the contents of bucket should show four objects.")
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 9: Delete all objects from bucket.")
        resp = self.s3_test_obj.object_list(self.bucket_name)[1]
        resp = self.s3_test_obj.delete_multiple_objects(self.bucket_name, resp[1])
        assert_utils.assert_true(resp[0], resp[1])
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
        self.log.info("Step 1: Multipart upload an object1 in bucket1 from accnt1")
        self.log.info("Step 2: list contents of bucket1.")
        self.log.info("Step 3: Grant accnt2 a write permission on bucket of accnt1.")
        self.log.info("Step 4: upload object2 from accnt 2 to accnt1’s bucket.")
        self.log.info("Step 5: list contents of bucket1.")
        self.log.info("Step 6: DeleteObjects (object1 and 2) from accnt1.")
        self.log.info("Step 7: DeleteObjects from accnt2.")
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
        self.log.info("Step 4: Do ListParts to see the parts uploaded.")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 5: uploaded perform CompleteMultipartUpload.")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id, None, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        self.log.info("Step 6: Delete the object.")
        resp = self.s3_test_obj.delete_object(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 7: Check space reclaim after 1hr.")
        # TODO: Logic to check space reclaimed.
        self.log.info("ENDED: Check Space reclaim after Deleting an object 1hr.")
