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
#
"""Tests Account capacity scenarios using REST API
"""
import logging
import os
import random
import time
from http import HTTPStatus
from time import perf_counter_ns

from multiprocessing import Pool, Process

import pytest

from commons import cortxlogging, configmanager
from commons.constants import NORMAL_UPLOAD_SIZES_IN_MB
from commons.utils import assert_utils
from commons.params import TEST_DATA_FOLDER
from commons.exceptions import CTException
from libs.csm.rest.csm_rest_acc_capacity import AccountCapacity
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.s3 import s3_misc
from config.s3 import MPART_CFG
from libs.s3.s3_common_test_lib import S3BackgroundIO
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from commons.utils.s3_utils import get_unaligned_parts
from commons.utils.s3_utils import get_multipart_etag
from commons.utils import system_utils
from commons.utils.s3_utils import get_precalculated_parts
from commons.utils.system_utils import create_file, remove_file, path_exists
from libs.s3.s3_test_lib import S3TestLib


class TestAccountCapacity():
    """Account Capacity Testsuite"""

    @classmethod
    def setup_class(cls):
        """ This is method is for test suite set-up """
        cls.log = logging.getLogger(__name__)
        cls.log.info("Initializing test setups ......")
        cls.acc_capacity = AccountCapacity()
        cls.log.info("Initiating Rest Client ...")
        cls.s3user = RestS3user()
        cls.buckets_created = []
        cls.account_created = []
        cls.bucket_name = "s3-bkt-{}".format(perf_counter_ns())
        cls.s3_test_obj = S3TestLib()
        cls.s3_mp_test_obj = S3MultipartTestLib()
        cls.s3_test_obj = S3TestLib()
        cls.s3_background_io = S3BackgroundIO(s3_test_lib_obj=cls.s3_test_obj)
        cls.s3_rest_obj = S3AccountOperationsRestAPI()
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "MultipartUploadDelete")
        cls.object_name = "s3-upload-obj-{}".format(perf_counter_ns())
        cls.s3_mp_test_obj = S3MultipartTestLib()
        cls.s3_accounts = []
        if not system_utils.path_exists(cls.test_dir_path):
            system_utils.make_dirs(cls.test_dir_path)
        cls.mp_obj_path = os.path.join(cls.test_dir_path, cls.test_file)
        cls.test_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_rest_account_capacity.yaml")

    def teardown_method(self):
        """
        Teardown for deleting any account and buckets created during tests
        """
        self.log.info("[STARTED] ######### Teardown #########")
        self.log.info("Deleting buckets %s & associated objects", self.buckets_created)
        for bucket in self.buckets_created:
            resp = s3_misc.delete_objects_bucket(bucket[0], bucket[1], bucket[2])
            assert_utils.assert_true(resp, "Failed to delete bucket.")
        self.log.info("Deleting S3 account %s created in test", self.account_created)
        for account in self.account_created:
            resp = self.s3user.delete_s3_account_user(account)
            assert_utils.assert_true(resp.status_code == HTTPStatus.OK, "Failed to delete account")
        self.log.info("[ENDED] ######### Teardown #########")

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33362')
    def test_33362(self):
        """
        Test data usage per account for PUT operation with same object name but different size.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Creating S3 account")
        resp = self.s3user.create_s3_account()
        assert_utils.assert_true(resp.status_code == HTTPStatus.CREATED,
                                 "Failed to create S3 account.")
        access_key = resp.json()["access_key"]
        secret_key = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        self.account_created.append(s3_user)
        total_cap = 0
        for _ in range(10):
            bucket = "bucket%s" % int(time.time())
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket, access_key, secret_key)
            assert_utils.assert_true(s3_misc.create_bucket(bucket, access_key, secret_key),
                                     "Failed to create bucket")
            self.log.info("bucket created successfully")
            self.buckets_created.append([bucket, access_key, secret_key])
            self.log.info("Start: Put operations")
            obj = f"object{s3_user}.txt"
            write_bytes_mb = random.randint(10, 100)
            total_cap = total_cap + write_bytes_mb
            self.log.info("Verify Perform %s of %s MB write in the bucket: %s", obj, write_bytes_mb,
                          bucket)
            resp = s3_misc.create_put_objects(
                obj, bucket, access_key, secret_key, object_size=write_bytes_mb)
            assert_utils.assert_true(resp, "Put object Failed")
            self.log.info("End: Put operations")
            self.log.info("verify capacity of account after put operations")
            s3_account = [{"account_name": s3_user, "capacity": total_cap, "unit": 'MB'}]
            resp = self.acc_capacity.verify_account_capacity(s3_account)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("verified capacity of account after put operations")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33369')
    def test_33369(self):
        """
        Test data usage per account while performing concurrent IO operations on multiple accounts.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        s3acct_cnt = self.test_conf["test_33369"]["s3acct_cnt"]
        validate_data_usage = self.test_conf["test_33369"]["validate_data_usage"]

        data_all = []
        self.log.info("Creating  %s S3 account and buckets", s3acct_cnt)
        for cnt in range(0, s3acct_cnt):
            self.log.info("Create S3 Account : %s", cnt)
            resp = self.s3user.create_s3_account()
            assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
            access_key = resp.json()["access_key"]
            secret_key = resp.json()["secret_key"]
            s3_user = resp.json()["account_name"]
            self.account_created.append(s3_user)
            bucket = f"test-33371-s3user{cnt}-bucket"
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket, access_key, secret_key)
            assert s3_misc.create_bucket(bucket, access_key, secret_key), "Failed to create bucket"
            self.log.info("bucket created successfully")
            self.buckets_created.append([bucket, access_key, secret_key])
            data_all.append(([s3_user, access_key, secret_key, bucket], NORMAL_UPLOAD_SIZES_IN_MB,
                             validate_data_usage))

        with Pool(len(data_all)) as pool:
            resp = pool.starmap(self.acc_capacity.perform_io_validate_data_usage, data_all)
        assert_utils.assert_true(all(resp),
                                 "Failure in Performing IO operations on S3 accounts")

        self.log.info("##### Test Ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33370')
    def test_33370(self):
        """
        Test data usage per account while performing concurrent IO operations on multiple buckets
        in same account.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        bucket_cnt = self.test_conf["test_33370"]["bucket_cnt"]
        validate_data_usage = self.test_conf["test_33370"]["validate_data_usage"]

        data_all = []
        self.log.info("Create S3 Account")
        resp = self.s3user.create_s3_account()
        assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
        access_key = resp.json()["access_key"]
        secret_key = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        self.account_created.append(s3_user)

        for cnt in range(0, bucket_cnt):
            bucket = f"test-33370-bucket{cnt}"
            self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                          bucket, access_key, secret_key)
            assert s3_misc.create_bucket(bucket, access_key, secret_key), "Failed to create bucket"
            self.log.info("bucket created successfully")
            self.buckets_created.append([bucket, access_key, secret_key])
            data_all.append(([s3_user, access_key, secret_key, bucket], NORMAL_UPLOAD_SIZES_IN_MB,
                             validate_data_usage))

        with Pool(len(data_all)) as pool:
            resp = pool.starmap(self.acc_capacity.perform_io_validate_data_usage, data_all)
        assert_utils.assert_true(all(resp),
                                 "Failure in Performing IO operations on S3 accounts")

        self.log.info("Verify capacity of account after put operations")
        expected_data_usage = bucket_cnt * sum(NORMAL_UPLOAD_SIZES_IN_MB)
        self.log.info("Expected data usage in MB : %s", expected_data_usage)
        s3_account = [{"account_name": s3_user, "capacity": expected_data_usage, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("##### Test Ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33371')
    def test_33371(self):
        """
        Test data usage per account while performing concurrent IO operations on same bucket.
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)

        parallel_io_cnt = self.test_conf["test_33371"]["parallel_io_cnt"]
        validate_data_usage = self.test_conf["test_33371"]["validate_data_usage"]

        data_all = []
        self.log.info("Create S3 Account")
        resp = self.s3user.create_s3_account()
        assert resp.status_code == HTTPStatus.CREATED, "Failed to create S3 account."
        access_key = resp.json()["access_key"]
        secret_key = resp.json()["secret_key"]
        s3_user = resp.json()["account_name"]
        self.account_created.append(s3_user)

        bucket = "test-33371-bucket"
        self.log.info("Verify Create bucket: %s with access key: %s and secret key: %s",
                      bucket, access_key, secret_key)
        assert s3_misc.create_bucket(bucket, access_key, secret_key), "Failed to create bucket"
        self.log.info("bucket created successfully")
        self.buckets_created.append([bucket, access_key, secret_key])

        for _ in range(0, parallel_io_cnt):
            data_all.append(([s3_user, access_key, secret_key, bucket], NORMAL_UPLOAD_SIZES_IN_MB,
                             validate_data_usage))

        with Pool(len(data_all)) as pool:
            resp = pool.starmap(self.acc_capacity.perform_io_validate_data_usage, data_all)
        assert_utils.assert_true(all(resp),
                                 "Failure in Performing IO operations on S3 accounts")

        self.log.info("Verify capacity of account after put operations")
        expected_data_usage = parallel_io_cnt * sum(NORMAL_UPLOAD_SIZES_IN_MB)
        self.log.info("Expected data usage in MB : %s", expected_data_usage)
        s3_account = [{"account_name": s3_user, "capacity": expected_data_usage, "unit": 'MB'}]
        resp = self.acc_capacity.verify_account_capacity(s3_account)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("##### Test Ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33365')
    def test_33365(self):
        """
        Test data usage per account while performing multipart uploads..
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("Multipart upload - create few parts more than 5 GB size")
        mp_config = MPART_CFG["test_33365"]
        file_size = mp_config["file_size"]
        total_parts = mp_config["total_parts"]
        self.log.info("Creating a bucket with name : %s", self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)
        self.log.info("Initiating multipart upload")
        res = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Uploading parts into bucket")
        try:
            res = self.s3_mp_test_obj.upload_parts(
                mpu_id,
                self.bucket_name,
                self.object_name,
                file_size,
                total_parts=total_parts,
                multipart_obj_path=self.mp_obj_path)
            assert_utils.assert_false(res[0], res[1])
            assert_utils.assert_not_equal(len(res[1]), total_parts, res[1])
        except CTException as error:
            self.log.error(error.message)
            assert_utils.assert_in(
                MPART_CFG["test_33365"]["err_msg"],
                error.message,
                error.message)
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_equal(len(res[1].get("Parts", [])), mp_config["total_parts"], res)
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33367')
    def test_33367(self):
        """
        Testing copying a copied object uploaded using multipart.

        Initiate a multipart upload, upload parts and complete it.
        Create multiple copies of the uploaded object.
        Verify copied objects
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("STARTED: Test copying a copied object uploaded using multipart")
        mp_config = MPART_CFG["test_33367"]
        self.log.info("Start background S3 IOs")
        self.s3_background_io.start(log_prefix="TEST-33367_s3bench_ios", duration="0h2m")
        self.log.info("Step 1: Initiating multipart upload")
        resp = self.s3_mp_test_obj.create_multipart_upload(
            self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id = resp[1]["UploadId"]
        self.log.info("Step 2: Upload unaligned parts")
        res = create_file(self.mp_obj_path, mp_config["file_size"], b_size="1M")
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_true(path_exists(self.mp_obj_path))
        parts = get_precalculated_parts(
            self.mp_obj_path, mp_config["part_sizes"], chunk_size=mp_config["chunk_size"])
        source_etag = get_multipart_etag(parts)
        status, uploaded_parts = self.s3_mp_test_obj.upload_parts_sequential(
            upload_id=mpu_id, bucket_name=self.bucket_name, object_name=self.object_name,
            parts=parts)
        assert_utils.assert_true(status, uploaded_parts)
        sorted_part_list = sorted(uploaded_parts, key=lambda x: x['PartNumber'])
        self.log.info("Step 3: Complete multipart upload")
        resp = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id=mpu_id, parts=sorted_part_list, bucket=self.bucket_name,
            object_name=self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_equal(source_etag, resp[1]["ETag"])
        resp = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, resp[1], resp[1])
        self.log.info("Step 4: Copy multipart object 10 times")
        src_bkt = self.bucket_name
        for _ in range(10):
            dst_bkt = "mp-bkt-{}".format(perf_counter_ns())
            self.log.info("Creating a bucket with name : %s", dst_bkt)
            resp = self.s3_test_obj.create_bucket(dst_bkt)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_equal(resp[1], dst_bkt, resp[1])
            self.log.info("Created a bucket with name : %s", dst_bkt)
            self.log.info("Copy object from %s to %s", src_bkt, dst_bkt)
            resp = self.s3_test_obj.copy_object(
                source_bucket=src_bkt, source_object=self.object_name, dest_bucket=dst_bkt,
                dest_object=self.object_name)
            assert_utils.assert_true(resp[0], resp[1])
            copy_etag = resp[1]['CopyObjectResult']['ETag']
            self.log.info("Verify copy and source etags match")
            assert_utils.assert_equal(source_etag, copy_etag)
            src_bkt = dst_bkt
        self.log.info("Stop background S3 IOs")
        self.s3_background_io.stop()
        self.log.info("ENDED: Test copying a copied object uploaded using multipart")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33368')
    def test_33368(self):
        """
        Multipart upload - create few parts more than 5 GB size.

        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("STARTED: Multipart upload - create few parts more than 5 GB size")
        mp_config = MPART_CFG["test_33368"]
        file_size = mp_config["file_size"]
        total_parts = mp_config["total_parts"]
        self.log.info("Creating a bucket with name : %s", self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)
        self.log.info("Initiating multipart upload")
        res = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Uploading parts into bucket")
        try:
            res = self.s3_mp_test_obj.upload_parts(
                mpu_id,
                self.bucket_name,
                self.object_name,
                file_size,
                total_parts=total_parts,
                multipart_obj_path=self.mp_obj_path)
            assert_utils.assert_false(res[0], res[1])
            assert_utils.assert_not_equal(len(res[1]), total_parts, res[1])
        except CTException as error:
            self.log.error(error.message)
            assert_utils.assert_in(
                MPART_CFG["test_33368"]["err_msg"],
                error.message,
                error.message)
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_equal(len(res[1].get("Parts", [])), mp_config["total_parts"], res)
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("ENDED: Multipart upload - create few parts more than 5 GB size")
        self.log.info("##### Test ended -  %s #####", test_case_name)

    @pytest.mark.csmrest
    @pytest.mark.cluster_user_ops
    @pytest.mark.account_capacity
    @pytest.mark.tags('TEST-33366')
    def test_33366(self):
        """
        Abort multipart while upload part is in progress.
        Initiate a multipart upload, upload parts.Abort it before upload part operations complete.
        Verify with list multipart
        """
        test_case_name = cortxlogging.get_frame()
        self.log.info("##### Test started -  %s #####", test_case_name)
        self.log.info("STARTED: Test aborting multipart upload that is in progress")
        mp_config = MPART_CFG["test_33366"]
        self.log.info("Start background S3 IOs")
        self.s3_background_io.start(log_prefix="TEST-33366_s3bench_ios", duration="0h2m")
        self.log.info("Step 1: Initiate multipart upload")
        resp = self.s3_mp_test_obj.create_multipart_upload(self.bucket_name, self.object_name)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_id = resp[1]["UploadId"]
        self.log.info("Step 2: Upload unaligned parts")
        res = create_file(self.mp_obj_path, mp_config["file_size"], b_size="1M")
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_true(path_exists(self.mp_obj_path))
        parts = get_unaligned_parts(
            self.mp_obj_path, total_parts=mp_config["total_parts"],
            chunk_size=mp_config["chunk_size"], random=True)
        process = Process(
            target=self.s3_mp_test_obj.upload_parts_parallel,
            args=(mpu_id, self.bucket_name, self.object_name), kwargs={"parts": parts})
        process.start()
        self.log.info("Sleep for 5 seconds for multipart uploads to start")
        time.sleep(5)
        self.log.info("Step 3: Abort multipart upload")
        resp = self.s3_mp_test_obj.abort_multipart_upload(
            self.bucket_name, self.object_name, mpu_id)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Wait for upload parts to complete and check list multipart "
                      "  uploads result")
        while process.is_alive():
            resp = self.s3_mp_test_obj.list_multipart_uploads(self.bucket_name)
            if mpu_id not in resp[1]:
                break
        self.log.info("Step 4: Check list multipart uploads result does not contain "
                      "upload id")
        assert_utils.assert_not_in(mpu_id, resp[1], resp[1])
        process.join()
        self.log.info("Stop background S3 IOs")
        self.s3_background_io.stop()
        self.log.info("ENDED: Test aborting multipart upload that is in progress")
        self.log.info("##### Test ended -  %s #####", test_case_name)
