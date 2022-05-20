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

"""Data Integrity test module."""

import os
import logging
from datetime import datetime
import pytest
from config import CMN_CFG
from commons.constants import NORMAL_UPLOAD_SIZES
from commons.constants import const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_PATH
from commons.utils import assert_utils
from commons.utils import system_utils as sys_util
from libs.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.di.di_feature_control import DIFeatureControl
from libs.di.data_generator import DataGenerator
from libs.di.fi_adapter import S3FailureInjection
from libs.di.di_error_detection_test_lib import DIErrorDetection
from libs.di import di_lib


class TestDIWithChangingS3Params:

    """Data Integrity Test suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.s3obj = S3TestLib()
        cls.di_control = DIFeatureControl(cmn_cfg=CMN_CFG)
        cls.data_gen = DataGenerator()
        cls.di_err_lib = DIErrorDetection()
        cls.fi_adapter = S3FailureInjection(cmn_cfg=CMN_CFG)
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.config_section = "S3_SERVER_CONFIG"
        cls.write_param = const.S3_DI_WRITE_CHECK
        cls.read_param = const.S3_DI_READ_CHECK
        cls.params = dict()
        cls.test_dir_path = os.path.join(TEST_DATA_PATH, "TestDI")
        if not sys_util.path_exists(cls.test_dir_path):
            resp = sys_util.make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", resp)
        cls.F_PATH = cls.test_dir_path + "/temp.txt"
        cls.F_PATH_COPY = cls.test_dir_path + "/temp-copy.txt"
        cls.log.info("ENDED: setup test suite operations.")

    @staticmethod
    def get_bucket_name():
        """
        function will return bucket name
        """
        return "di-test-bkt-{}".format(datetime.utcnow().strftime('%Y%m%d%H%M%S%f'))

    @staticmethod
    def get_object_name():
        """
        function will return object name
        """
        return "di-test-obj-{}".format(datetime.utcnow().strftime('%Y%m%d%H%M%S%f'))

    def setup_method(self):
        """
        Function will be invoked before test execution.

        It will perform prerequisite test steps if any
        """
        self.log.info("STARTED: Setup operations")
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        This function will be invoked after each test case.
        It will perform all cleanup operations.
        This function will delete buckets and accounts and files created for tests.
        """
        self.log.info("STARTED: Teardown operations.")
        self.log.info("ENDED: Teardown operations.")

    @classmethod
    def teardown_class(cls):
        """
        teardown class
        """
        cls.log.info("STARTED: Teardown cls operations.")
        cls.log.info("Deleting a backup file and directory...")
        if sys_util.path_exists(cls.F_PATH):
            sys_util.remove_file(cls.F_PATH)
        if sys_util.path_exists(cls.F_PATH_COPY):
            sys_util.remove_file(cls.F_PATH_COPY)
        if sys_util.path_exists(cls.test_dir_path):
            sys_util.remove_dirs(cls.test_dir_path)
        cls.log.info("Deleted a backup file and directory")
        cls.log.info("ENDED: Teardown class operations.")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29273')
    @CTFailOn(error_handler)
    def test_29273(self):
        """
        this will test normal file upload
        with DI flag ON for both write and read
        """
        valid, skipmark = self.di_err_lib.validate_enabled_config()
        if not valid or skipmark:
            self.log.info("Skipping test DI flags are not enabled")
            pytest.skip()
        self.log.info("STARTED: Normal File upload with DI flag enable for read and write")
        bucket_name = self.get_bucket_name()
        obj_name = self.get_object_name()
        self.s3obj.create_bucket(bucket_name=bucket_name)
        result = True
        for size in NORMAL_UPLOAD_SIZES:
            self.log.info("Step 1: create a file of size %s MB", size)

            file_path_upload = self.F_PATH + "TEST_29173_" + str(size) + "_upload"
            if os.path.exists(file_path_upload):
                os.remove(file_path_upload)
            buff, csm = self.data_gen.generate(size=size,
                                               seed=self.data_gen.get_random_seed())
            location = self.data_gen.create_file_from_buf(fbuf=buff, name=file_path_upload,
                                                          size=size)
            self.s3obj.put_object(bucket_name=bucket_name, object_name=obj_name,
                                  file_path=location)
            self.log.debug("Step 1: Checksum of uploaded file is %s",csm)
            self.log.info("Step 1: Created a bucket and upload object of %s.", size)
            self.log.info("Step 2: Download chunk uploaded object of size %s.", size)
            file_path_download = self.F_PATH + "TEST_29173_"+ str(size) + "_download"
            if os.path.exists(file_path_download):
                os.remove(file_path_download)
            res = self.s3obj.object_download(bucket_name, obj_name, file_path_download)
            assert_utils.assert_true(res[0], res)
            self.log.info("Step 2: Download chunk uploaded object is successful.")
            self.log.info("Step 3: Validate checksum of both uploaded and downloaded file.")
            self.s3obj.delete_object(bucket_name=bucket_name, obj_name=obj_name)
            result = sys_util.validate_checksum(file_path_1=file_path_upload,
                                                file_path_2=file_path_download)
            if not result:
                self.log.info("Step 3: Checksum validation failed.")
                break
            self.log.info("Step 3: Checksum validation is successful.")
        self.s3obj.delete_bucket(bucket_name, force=True)
        if result:
            assert True
        else:
            assert False
        self.log.info("ENDED:Normal File upload with DI flag enable for read and write")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29276')
    @CTFailOn(error_handler)
    def test_29276(self):
        """
        this will test copy object to same bucket with diff name
        with DI disabled
        """
        valid, skipmark = self.di_err_lib.validate_disabled_config()
        if not valid or skipmark:
            self.log.info("Skipping test as DI flags are not disabled" )
            pytest.skip()
        self.log.info("STARTED: With DI flag  Disabled, copy object to the same" "bucket with "
                      "different name")
        self.log.info("Step 1:: Creating  bucket and upload object")
        bucket_name = self.get_bucket_name()
        obj_name_1 = self.get_object_name()
        self.s3obj.create_bucket(bucket_name=bucket_name)
        sys_util.create_file(fpath=self.F_PATH, count=1)
        resp = self.s3obj.put_object(bucket_name=bucket_name, object_name=obj_name_1,
                                     file_path=self.F_PATH)
        self.log.info(resp)
        self.log.info("Step 1:: Created bucket with  %s and uploading object %s", bucket_name,
                      obj_name_1)
        self.log.info("Step 2:: List object in bucket")
        res = self.s3obj.object_list(bucket_name)
        if obj_name_1 not in res[1]:
            assert_utils.assert_true(False, "object not listed in bucket")
        self.log.info("Step 2:: Object listed in bucket")
        obj_name_2 = self.get_object_name()
        self.log.info("Step 3:: Copy object=%s to  same bucket in destination object=%s",
                      obj_name_1, obj_name_2)
        resp_cp = self.s3obj.copy_object(source_bucket=bucket_name, source_object=obj_name_1,
                                         dest_bucket=bucket_name, dest_object=obj_name_2)
        self.log.info(resp_cp)
        self.log.info("Step 3:: Successfully Copied object to same bucket")
        res = self.s3obj.object_list(bucket_name)
        if obj_name_2 not in res[1]:
            assert_utils.assert_true(False, "object not listed in bucket")
        self.s3obj.object_download(bucket_name=bucket_name,
                                   obj_name=obj_name_2, file_path=self.F_PATH_COPY)
        self.log.info("Step 4:: Validate ETAG and checksum")
        result = sys_util.validate_checksum(file_path_1=self.F_PATH, file_path_2=self.F_PATH_COPY)
        if result:
            assert_utils.assert_equals(resp[1]['ETag'], resp_cp[1]['CopyObjectResult']['ETag'],
                                       "ETAG validation failed:")
        else:
            assert_utils.assert_true(False, "Checksum validation failed")
        self.log.info("Step 4:Checksum and ETAG validation is successful")
        self.s3obj.delete_bucket(bucket_name, force=True)
        self.log.info("ENDED: With DI flag  Disabled, copy object to the same bucket with "
                      "different name")

    @pytest.mark.skip(reason="Not yet automated")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29277')
    @CTFailOn(error_handler)
    def test_29277(self):
        """
        this will test copy object to same bucket with diff name
        with DI enabled
        """
        valid, skipmark = self.di_err_lib.validate_enabled_config()
        if not valid or skipmark:
            self.log.info("Skipping test as DI flags are not enabled" )
            pytest.skip()

        self.log.info("STARTED: With DI flag  Enabled, copy object to the same bucket with "
                      "different name")
        self.log.info("Step 1:: Creating  bucket and upload object")
        bucket_name = self.get_bucket_name()
        obj_name_1 = self.get_object_name()
        self.s3obj.create_bucket(bucket_name=bucket_name)
        sys_util.create_file(fpath=self.F_PATH, count=1)
        resp = self.s3obj.put_object(bucket_name=bucket_name, object_name=obj_name_1,
                                     file_path=self.F_PATH)
        self.log.info(resp)
        self.log.info("Step 1:: Created bucket with  %s and uploading object %s", bucket_name,
                      obj_name_1)
        self.log.info("Step 2:: List object in bucket")
        res = self.s3obj.object_list(bucket_name)
        if obj_name_1 not in res[1]:
            assert_utils.assert_true(False, "object not listed in bucket")
        self.log.info("Step 2:: Object listed in bucket")
        obj_name_2 = self.get_object_name()
        self.log.info("Step 3:: Copy object=%s to  same bucket in destination object=%s",
                      obj_name_1, obj_name_2)
        resp_cp = self.s3obj.copy_object(source_bucket=bucket_name, source_object=obj_name_1,
                                         dest_bucket=bucket_name, dest_object=obj_name_2)
        self.log.info(resp_cp)
        self.log.info("Step 3:: Successfully Copied object to same bucket")
        res = self.s3obj.object_list(bucket_name)
        if obj_name_2 not in res[1]:
            assert_utils.assert_true(False, "object not listed in bucket")

        self.s3obj.object_download(bucket_name=bucket_name,
                                   obj_name=obj_name_2, file_path=self.F_PATH_COPY)
        self.log.info("Step 4:: Validate ETAG and checksum")
        result = sys_util.validate_checksum(file_path_1=self.F_PATH, file_path_2=self.F_PATH_COPY)
        if result:
            assert_utils.assert_equals(resp[1]['ETag'], resp_cp[1]['CopyObjectResult']['ETag'],
                                       "ETAG validation failed:")
        else:
            assert_utils.assert_true(False, "Checksum validation failed")
        self.log.info("Step 4:: Checksum and ETAG validation is successful")
        self.s3obj.delete_bucket(bucket_name, force=True)
        self.log.info("ENDED: With DI flag Enabled, copy object to the same bucket with "
                      "different name")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29281')
    @CTFailOn(error_handler)
    def test_29281(self):
        """
        Test to verify copy object to different bucket with same
        object name with Data Integrity disabled.
        """
        valid, skipmark = self.di_err_lib.validate_disabled_config()
        if not valid or skipmark:
            self.log.info("Skipping test when DI flags are not set to disabled config" )
            pytest.skip()
        self.log.info("STARTED: Test to verify copy object to different bucket with same object "
                      "name with Data Integrity disabled.")
        bucket_name_1 = self.get_bucket_name()
        bucket_name_2 = self.get_bucket_name()
        obj_name = self.get_object_name()
        self.log.info("Step 1: Create a 2 different bucket1 = %s and bucket2 = %s.",
                      bucket_name_1, bucket_name_2)
        self.s3obj.create_bucket(bucket_name=bucket_name_1)
        self.s3obj.create_bucket(bucket_name=bucket_name_2)
        self.log.info("Step 1: create a file ")
        if os.path.exists(self.F_PATH):
            os.remove(self.F_PATH)
        sys_util.create_file(fpath=self.F_PATH, count=1)
        self.log.info("Step 2: Upload file to a bucket = %s",bucket_name_1)
        resp = self.s3obj.put_object(bucket_name=bucket_name_1, object_name=obj_name,
                                     file_path=self.F_PATH)
        self.log.info("Step 2: Upload file to a bucket = %s",bucket_name_1)
        self.log.info(resp)
        res = self.s3obj.object_list(bucket_name_1)
        if obj_name not in res[1]:
            assert_utils.assert_true(False, "object not listed in bucket")
        self.log.info("Step 3: Copy object to different bucket = {bucket_name_2}")
        resp_cp = self.s3obj.copy_object(source_bucket=bucket_name_1, source_object=obj_name,
                                         dest_bucket=bucket_name_2, dest_object=obj_name)
        self.log.info(resp_cp)
        assert_utils.assert_true(resp_cp[0], resp_cp)
        self.log.info("Step 3: Copy object to different bucket is successful.")
        res = self.s3obj.object_list(bucket_name_2)
        if obj_name not in res[1]:
            assert_utils.assert_true(False, "object not listed in bucket")
        self.s3obj.delete_bucket(bucket_name_1, force=True)
        self.s3obj.delete_bucket(bucket_name_2, force=True)
        self.log.info("Step 4: Validate Etag of source and copied object.")
        assert_utils.assert_equals(resp[1]['ETag'], resp_cp[1]['CopyObjectResult']['ETag'],
                                   "ETAG validation failed:")
        self.log.info("Step 4: Etag validation is successful.")
        self.log.info("ENDED: Test to verify copy object to different bucket with same object "
                      "name with Data Integrity disabled.")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29282')
    @CTFailOn(error_handler)
    def test_29282(self):
        """
        Test to verify copy of copied object using simple object upload with
        Data Integrity flag ON for write and OFF for read
        """
        self.log.info("STARTED: Test to verify copy of copied object using simple object upload "
                      "with Data Integrity flag ON for write and OFF for read")
        failed_file_sizes = []
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        self.log.info("Step 1: Create buckets.")
        bkt_name_1 = self.get_bucket_name()
        self.s3obj.create_bucket(bucket_name=bkt_name_1)
        bkt_name_2 = self.get_bucket_name()
        self.s3obj.create_bucket(bucket_name=bkt_name_2)
        bkt_name_3 = self.get_bucket_name()
        self.s3obj.create_bucket(bucket_name=bkt_name_3)
        for file_size in NORMAL_UPLOAD_SIZES:
            obj_name_1 = self.get_object_name()
            obj_name_2 = self.get_object_name()
            obj_name_3 = self.get_object_name()
            self.log.info("Step 2: Generation files of sizes %s", file_size)
            location, csm = self.di_err_lib.get_file_and_csum(size=file_size,
                                                              data_folder_prefix=self.test_dir_path)
            self.log.debug("location: %s, csm: %s", location, csm)
            try:
                self.log.debug("Uploading object to bucket %s", bkt_name_1)
                self.s3obj.put_object(bucket_name=bkt_name_1, object_name=obj_name_1,
                                      file_path=location)
                self.log.debug("Copying object from bucket %s to bucket %s", bkt_name_1, bkt_name_2)
                self.s3obj.copy_object(source_bucket=bkt_name_1, source_object=obj_name_1,
                                       dest_bucket=bkt_name_2, dest_object=obj_name_2)
                self.s3obj.copy_object(source_bucket=bkt_name_2, source_object=obj_name_2,
                                       dest_bucket=bkt_name_3, dest_object=obj_name_3)
                self.s3obj.object_download(bucket_name=bkt_name_3, obj_name=obj_name_3,
                                           file_path=self.F_PATH_COPY)
                csm_down = sys_util.calculate_checksum(file_path=self.F_PATH_COPY, filter_resp=True)
                if csm != csm_down:
                    failed_file_sizes.append(file_size)
            except CTException as err:
                self.log.info("Test failed with %s", err)
                failed_file_sizes.append(file_size)
        self.s3obj.delete_bucket(bkt_name_1, force=True)
        self.s3obj.delete_bucket(bkt_name_2, force=True)
        self.s3obj.delete_bucket(bkt_name_3, force=True)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
            assert False
        self.log.info("ENDED: Test to verify copy of copied object using simple object upload "
                      "with Data Integrity flag ON for write and OFF for read")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29286')
    @CTFailOn(error_handler)
    def test_29286(self):
        """
        Test to overwrite an object using copy object api with
        Data Integrity flag ON for write and OFF for read
        """
        self.log.info("STARTED: Test to overwrite an object using copy object api with Data "
                      "Integrity flag ON for write and OFF for read")
        failed_file_sizes = []
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        bucket_name_1 = self.get_bucket_name()
        self.s3obj.create_bucket(bucket_name=bucket_name_1)
        bucket_name_2 = self.get_bucket_name()
        self.s3obj.create_bucket(bucket_name=bucket_name_2)
        for file_size in NORMAL_UPLOAD_SIZES:
            obj_name_1 = self.get_object_name()
            location, csm = self.di_err_lib.get_file_and_csum(size=file_size,
                                                              data_folder_prefix=self.test_dir_path)
            self.log.debug("location: %s, csm: %s", location, csm)
            try:
                self.s3obj.put_object(bucket_name=bucket_name_1, object_name=obj_name_1,
                                      file_path=location)
                self.s3obj.copy_object(source_bucket=bucket_name_1, source_object=obj_name_1,
                                       dest_bucket=bucket_name_2, dest_object=obj_name_1)
                self.s3obj.copy_object(source_bucket=bucket_name_2, source_object=obj_name_1,
                                       dest_bucket=bucket_name_1, dest_object=obj_name_1)
                self.s3obj.object_download(bucket_name=bucket_name_1, obj_name=obj_name_1,
                                           file_path=self.F_PATH_COPY)
                csm_down = sys_util.calculate_checksum(file_path=self.F_PATH_COPY, filter_resp=True)
                if csm != csm_down:
                    failed_file_sizes.append(file_size)
            except CTException as err:
                self.log.info("Test failed with %s", err)
                failed_file_sizes.append(file_size)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
            assert False
        self.s3obj.delete_bucket(bucket_name_1, force=True)
        self.s3obj.delete_bucket(bucket_name_2, force=True)
        self.log.info("ENDED: Test to overwrite an object using copy object api with Data "
                      "Integrity flag ON for write and OFF for read")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29288')
    @CTFailOn(error_handler)
    def test_29288(self):
        """
        Test to verify multipart upload with s3server restart after every upload
        with Data Integrity flag ON for write and OFF for read
        """
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        bucket_name = self.get_bucket_name()
        obj_name = self.get_object_name()
        parts = list()
        res_sp_file = sys_util.split_file(filename=self.F_PATH, size=25, split_count=5,
                                          random_part_size=False)
        self.log.info(res_sp_file)
        self.s3obj.create_bucket(bucket_name=bucket_name)
        res = self.s3_mp_test_obj.create_multipart_upload(bucket_name, obj_name)
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Uploading parts into bucket")
        i = 0
        while i < 5:
            with open(res_sp_file[i]["Output"], "rb") as file_pointer:
                data = file_pointer.read()
            resp = self.s3_mp_test_obj.upload_part(body=data, bucket_name=bucket_name,
                                                   object_name=obj_name, upload_id=mpu_id,
                                                   part_number=i + 1)
            parts.append({"PartNumber": i+1, "ETag": resp[1]["ETag"]})
            if not di_lib.restart_s3_processes_k8s():
                assert False
            i += 1
        resp_cu = self.s3_mp_test_obj.complete_multipart_upload(mpu_id=mpu_id, parts=parts,
                                                                bucket=bucket_name,
                                                                object_name=obj_name)
        self.log.info(resp_cu)
        self.s3obj.object_download(bucket_name=bucket_name, obj_name=obj_name,
                                   file_path=self.F_PATH_COPY)
        self.s3obj.delete_bucket(bucket_name, force=True)
        result = sys_util.validate_checksum(file_path_1=self.F_PATH, file_path_2=self.F_PATH_COPY)
        if result:
            assert True, "Checksum matched"
        else:
            assert False, "Checksum not matched"
