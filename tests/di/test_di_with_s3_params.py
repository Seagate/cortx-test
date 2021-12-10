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

"""Data Integrity test module."""

import os
import logging
from datetime import datetime
import pytest
from libs.di.di_error_detection_test_lib import DIErrorDetection
from libs.s3 import S3H_OBJ
from libs.s3 import S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.di.di_feature_control import DIFeatureControl
from libs.di.data_generator import DataGenerator
from libs.di.fi_adapter import S3FailureInjection
from config import CMN_CFG
from commons.constants import const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_PATH
from commons.utils import system_utils as sys_util


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

    @pytest.mark.skip(reason="not tested hence marking skip")
    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-29273')
    @CTFailOn(error_handler)
    def test_29273(self):
        """
        this will test normal file upload
        with DI flag ON for both write and read
        """
        # to do verify configs
        self.log.info("Step 1::: Setting up params and restarting server")
        bucket_name = self.get_bucket_name()
        obj_name = self.get_object_name()
        self.s3obj.create_bucket(bucket_name=bucket_name)
        file_size = [1, 2, 3, 4, 5]
        result = True
        for size in file_size:
            self.log.info("creating a file of size %s MB", size)
            sys_util.create_file(fpath=self.F_PATH, count=size)
            self.s3obj.put_object(bucket_name=bucket_name, object_name=obj_name,
                                  file_path=self.F_PATH)
            self.s3obj.object_download(bucket_name=bucket_name,
                                       obj_name=obj_name, file_path=self.F_PATH_COPY)
            self.s3obj.delete_object(bucket_name=bucket_name, obj_name=obj_name)
            result = sys_util.validate_checksum(file_path_1=self.F_PATH,
                                                file_path_2=self.F_PATH_COPY)
            if not result:
                break
        self.s3obj.delete_bucket(bucket_name, force=True)
        self.log.info("Step 2::: Calculating checksum")
        if result:
            assert True
        else:
            assert False

    @pytest.mark.skip(reason="not tested hence marking skip")
    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-29276')
    @CTFailOn(error_handler)
    def test_29276(self):
        """
        this will test copy object to same bucket with diff name
        with DI disabled
        """
        # to do verify configs
        self.log.info("Step 1::: Setting up params and restarting server")
        self.log.info("Step 2::: Creating file and bucket")
        bucket_name = self.get_bucket_name()
        obj_name_1 = self.get_object_name()
        obj_name_2 = self.get_object_name()
        self.s3obj.create_bucket(bucket_name=bucket_name)
        sys_util.create_file(fpath=self.F_PATH, count=1)
        resp = self.s3obj.put_object(bucket_name=bucket_name, object_name=obj_name_1,
                                     file_path=self.F_PATH)
        self.log.info(resp)
        resp_cp = self.s3obj.copy_object(source_bucket=bucket_name,
                                         source_object=obj_name_1,
                                         dest_bucket=bucket_name,
                                         dest_object=obj_name_2)
        self.log.info(resp_cp)
        self.s3obj.delete_bucket(bucket_name, force=True)
        self.log.info("Step 3::: Comparing ETags")
        if resp[1]['ETag'] == resp_cp[1]['CopyObjectResult']['ETag']:
            assert True
        else:
            assert False

    @pytest.mark.skip(reason="not tested hence marking skip")
    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-29277')
    @CTFailOn(error_handler)
    def test_29277(self):
        """
        this will test copy object to same bucket with diff name
        with DI enabled
        """
        # to do verify configs
        self.log.info("Step 2::: Creating file and bucket")
        bucket_name = self.get_bucket_name()
        obj_name_1 = self.get_object_name()
        obj_name_2 = self.get_object_name()
        self.s3obj.create_bucket(bucket_name=bucket_name)
        sys_util.create_file(fpath=self.F_PATH, count=1)
        resp = self.s3obj.put_object(bucket_name=bucket_name, object_name=obj_name_1,
                                     file_path=self.F_PATH)
        self.log.info(resp)
        resp_cp = self.s3obj.copy_object(source_bucket=bucket_name,
                                         source_object=obj_name_1,
                                         dest_bucket=bucket_name,
                                         dest_object=obj_name_2)
        self.log.info(resp_cp)
        self.s3obj.delete_bucket(bucket_name, force=True)
        self.log.info("Step 3::: Comparing ETags")
        if resp[1]['ETag'] == resp_cp[1]['CopyObjectResult']['ETag']:
            assert False
        else:
            assert True

    @pytest.mark.skip(reason="not tested hence marking skip")
    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-29281')
    @CTFailOn(error_handler)
    def test_29281(self):
        """
        Test to verify copy object to different bucket with same
        object name with Data Integrity disabled.
        """
        # to do verify configs
        bucket_name_1 = self.get_bucket_name()
        bucket_name_2 = self.get_bucket_name()
        obj_name = self.get_object_name()
        self.s3obj.create_bucket(bucket_name=bucket_name_1)
        self.s3obj.create_bucket(bucket_name=bucket_name_2)
        sys_util.create_file(fpath=self.F_PATH, count=1)
        resp = self.s3obj.put_object(bucket_name=bucket_name_1, object_name=obj_name,
                                     file_path=self.F_PATH)
        self.log.info(resp)
        resp_cp = self.s3obj.copy_object(source_bucket=bucket_name_1,
                                         source_object=obj_name,
                                         dest_bucket=bucket_name_2,
                                         dest_object=obj_name)
        self.log.info(resp_cp)
        self.s3obj.delete_bucket(bucket_name_1, force=True)
        self.s3obj.delete_bucket(bucket_name_2, force=True)
        if resp[1]['ETag'] == resp_cp[1]['CopyObjectResult']['ETag']:
            assert True
        else:
            assert False

    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-29282')
    @CTFailOn(error_handler)
    def test_29282(self):
        """
        Test to verify copy of copied object using simple object upload with
        Data Integrity flag ON for write and OFF for read
        """
        self.log.info("Started: Test to verify copy of copied object using simple object upload "
                      "with Data Integrity flag ON for write and OFF for read")
        self.log.debug("Checking setup status")
        config_res = self.di_err_lib.validate_default_config()
        if config_res[1]:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        bucket_name_1 = self.get_bucket_name()
        bucket_name_2 = self.get_bucket_name()
        bucket_name_3 = self.get_bucket_name()
        obj_name_1 = self.get_object_name()
        obj_name_2 = self.get_object_name()
        obj_name_3 = self.get_object_name()
        sys_util.create_file(fpath=self.F_PATH, count=1)
        try:
            self.s3obj.create_bucket(bucket_name=bucket_name_1)
            self.s3obj.create_bucket(bucket_name=bucket_name_2)
            self.s3obj.create_bucket(bucket_name=bucket_name_3)
            resp_put = self.s3obj.put_object(bucket_name=bucket_name_1, object_name=obj_name_1,
                                             file_path=self.F_PATH)
            self.log.debug(resp_put)
            resp_cp = self.s3obj.copy_object(source_bucket=bucket_name_1,
                                             source_object=obj_name_1, dest_bucket=bucket_name_2,
                                             dest_object=obj_name_2)
            self.log.debug(resp_cp)
            resp_cp_cp = self.s3obj.copy_object(source_bucket=bucket_name_2,
                                                source_object=obj_name_2,
                                                dest_bucket=bucket_name_3, dest_object=obj_name_3)
            self.log.debug(resp_cp_cp)
            self.s3obj.object_download(bucket_name=bucket_name_3, obj_name=obj_name_3,
                                       file_path=self.F_PATH_COPY)
            self.s3obj.delete_bucket(bucket_name_1, force=True)
            self.s3obj.delete_bucket(bucket_name_2, force=True)
            self.s3obj.delete_bucket(bucket_name_3, force=True)
            result = sys_util.validate_checksum(file_path_1=self.F_PATH,
                                                file_path_2=self.F_PATH_COPY)
            if result:
                self.log.info("Checksum matched for downloaded files")
            else:
                self.log.info("Checksum match failed for downloaded files")
                assert False
        except CTException as err:
            self.log.info("Test failed with %s", err)
        self.log.info("Ended: Test to verify copy of copied object using simple object upload "
                      "with Data Integrity flag ON for write and OFF for read")

    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-29284')
    @CTFailOn(error_handler)
    def test_29284(self):
        """
        Test to verify copy object with chunk upload and
        GET operation with range read with file size 50mb
        with Data Integrity flag ON for write and OFF for read
        """
        self.log.info("Started: Test to verify copy object with chunk upload and GET operation "
                      "with range read with file size 50mb with DI flag ON for write and OFF for "
                      "read")
        self.log.debug("Checking setup status")
        config_res = self.di_err_lib.validate_default_config()
        if config_res[1]:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        bucket_name_1 = self.get_bucket_name()
        bucket_name_2 = self.get_bucket_name()
        obj_name_1 = self.get_object_name()
        obj_name_2 = self.get_object_name()
        sys_util.create_file(fpath=self.F_PATH, count=50)
        try:
            self.s3obj.create_bucket(bucket_name=bucket_name_1)
            self.s3obj.create_bucket(bucket_name=bucket_name_2)
            resp_put = self.s3obj.put_object(bucket_name=bucket_name_1, object_name=obj_name_1,
                                             file_path=self.F_PATH)
            self.log.debug(resp_put)
            resp_cp = self.s3obj.copy_object(source_bucket=bucket_name_1, source_object=obj_name_1,
                                             dest_bucket=bucket_name_2, dest_object=obj_name_2)
            self.log.debug(resp_cp)
            resp_rr = self.s3_mp_test_obj.get_byte_range_of_object(bucket_name=bucket_name_2,
                                                                   my_key=obj_name_2,
                                                                   start_byte=8888, stop_byte=9999)
            self.log.debug(resp_rr)
            self.s3obj.delete_bucket(bucket_name_1, force=True)
            self.s3obj.delete_bucket(bucket_name_2, force=True)
        except CTException as err:
            self.log.info("Test failed with %s", err)
        self.log.info("Ended: Test to verify copy object with chunk upload and GET operation "
                      "with range read with file size 50mb with DI flag ON for write and OFF for "
                      "read")

    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-29286')
    @CTFailOn(error_handler)
    def test_29286(self):
        """
        Test to overwrite an object using copy object api with
        Data Integrity flag ON for write and OFF for read
        """
        self.log.info("Started: Test to overwrite an object using copy object api with Data "
                      "Integrity flag ON for write and OFF for read")
        self.log.debug("Checking setup status")
        config_res = self.di_err_lib.validate_default_config()
        if config_res[1]:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        bucket_name_1 = self.get_bucket_name()
        bucket_name_2 = self.get_bucket_name()
        obj_name_1 = self.get_object_name()
        sys_util.create_file(fpath=self.F_PATH, count=1)
        try:
            self.s3obj.create_bucket(bucket_name=bucket_name_1)
            self.s3obj.create_bucket(bucket_name=bucket_name_2)
            resp_put = self.s3obj.put_object(bucket_name=bucket_name_1, object_name=obj_name_1,
                                             file_path=self.F_PATH)
            self.log.debug(resp_put)
            resp_cp = self.s3obj.copy_object(source_bucket=bucket_name_1, source_object=obj_name_1,
                                             dest_bucket=bucket_name_2, dest_object=obj_name_1)
            self.log.debug(resp_cp)
            resp_cp_cp = self.s3obj.copy_object(source_bucket=bucket_name_2,
                                                source_object=obj_name_1,
                                                dest_bucket=bucket_name_1, dest_object=obj_name_1)
            self.log.info(resp_cp_cp)
            self.s3obj.object_download(bucket_name=bucket_name_1, obj_name=obj_name_1,
                                       file_path=self.F_PATH_COPY)
            res = sys_util.validate_checksum(file_path_1=self.F_PATH, file_path_2=self.F_PATH_COPY)
            self.s3obj.delete_bucket(bucket_name_1, force=True)
            self.s3obj.delete_bucket(bucket_name_2, force=True)
            if res:
                assert True
            else:
                assert False
        except CTException as err:
            self.log.info("Test failed with %s", err)
        self.log.info("Ended: Test to overwrite an object using copy object api with Data "
                      "Integrity flag ON for write and OFF for read")

    @pytest.mark.skip(reason="Not tested hence marking skip")
    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-29288')
    @CTFailOn(error_handler)
    def test_29288(self):
        """
        Test to verify multipart upload with s3server restart after every upload
        with Data Integrity flag ON for write and OFF for read
        """
        self.log.debug("Checking setup status")
        config_res = self.di_err_lib.validate_default_config()
        if config_res[1]:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        bucket_name = self.get_bucket_name()
        obj_name = self.get_object_name()
        parts = list()
        res_sp_file = sys_util.split_file(filename=self.F_PATH, size=25, split_count=5,
                                          random_part_size=False)
        self.log.debug(res_sp_file)
        try:
            self.s3obj.create_bucket(bucket_name=bucket_name)
            res_mpu = self.s3_mp_test_obj.create_multipart_upload(bucket_name, obj_name)
            mpu_id = res_mpu[1]["UploadId"]
            self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
            self.log.debug("Uploading parts into bucket")
            i = 0
            while i < 5:
                with open(res_sp_file[i]["Output"], "rb") as file_pointer:
                    data = file_pointer.read()
                resp = self.s3_mp_test_obj.upload_part(body=data, bucket_name=bucket_name,
                                                       object_name=obj_name, upload_id=mpu_id,
                                                       part_number=i+1)
                parts.append({"PartNumber": i+1, "ETag": resp[1]["ETag"]})
                S3H_OBJ.restart_s3server_processes()
                # to do for LC
                i += 1
            resp_cu = self.s3_mp_test_obj.complete_multipart_upload(mpu_id=mpu_id, parts=parts,
                                                                    bucket=bucket_name,
                                                                    object_name=obj_name)
            self.log.info(resp_cu)
            self.s3obj.object_download(bucket_name=bucket_name, obj_name=obj_name,
                                       file_path=self.F_PATH_COPY)
            self.s3obj.delete_bucket(bucket_name, force=True)
            result = sys_util.validate_checksum(file_path_1=self.F_PATH,
                                                file_path_2=self.F_PATH_COPY)
            if result:
                assert True
            else:
                assert False
        except CTException as err:
            self.log.info("Test failed with %s", err)

    @pytest.mark.skip("Not tested, hence marking skip")
    @pytest.mark.data_integrity
    @pytest.mark.tags('TEST-29289')
    @CTFailOn(error_handler)
    def test_29289(self):
        """
        Test to verify Fault Injection with different modes
        using simple object upload with Data Integrity
        flag ON for write and OFF for read
        """
        self.log.debug("Checking setup status")
        config_res = self.di_err_lib.validate_default_config()
        if config_res[1]:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        bucket_name_1 = self.get_bucket_name()
        bucket_name_2 = self.get_bucket_name()
        obj_name_1 = self.get_object_name()
        obj_name_2 = self.get_object_name()
        try:
            self.s3obj.create_bucket(bucket_name=bucket_name_1)
            self.s3obj.create_bucket(bucket_name=bucket_name_2)
            self.log.info("Step 1: Create a corrupted file.")
            location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='f',
                                                             data_folder_prefix=self.test_dir_path)
            self.log.info("Step 1: created a corrupted file at location %s", location)
            self.log.info("Step 2: Enable data corruption")
            fault_status = self.fi_adapter.set_fault_injection(flag=True)
            if fault_status[0]:
                self.log.debug("Step 2: fault injection set")
            else:
                self.log.debug("Step 2: failed to set fault injection. Reason: %s", fault_status[1])
                assert False
            status = self.fi_adapter.enable_data_block_corruption()
            if status:
                self.log.debug("Step 2: enabled data corruption")
            else:
                self.log.debug("Step 2: failed to enable data corruption")
                assert False
            self.log.info("Step 2: Enabled data corruption")
            self.s3obj.put_object(bucket_name=bucket_name_1, object_name=obj_name_1,
                                  file_path=location)
            resp = self.s3obj.copy_object(source_bucket=bucket_name_1, source_object=obj_name_1,
                                          dest_bucket=bucket_name_2, dest_object=obj_name_2)
            self.log.info(resp)
            # this copy operation should fail
            resp = self.s3obj.object_download(bucket_name=bucket_name_1,
                                              obj_name=obj_name_1, file_path=self.F_PATH)
            self.log.info(resp)
            # this get operation should fail
            # test scene 2
            location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='z',
                                                             data_folder_prefix=self.test_dir_path)
            self.s3obj.put_object(bucket_name=bucket_name_1, object_name=obj_name_1,
                                  file_path=location)
            resp = self.s3obj.copy_object(source_bucket=bucket_name_1, source_object=obj_name_1,
                                          dest_bucket=bucket_name_2, dest_object=obj_name_2)
            self.log.info(resp)
            # this copy operation should fail
            resp = self.s3obj.object_download(bucket_name=bucket_name_1, obj_name=obj_name_1,
                                              file_path=self.F_PATH)
            self.log.info(resp)
            # this get operation should fail
            self.s3obj.put_object(bucket_name=bucket_name_1, object_name=obj_name_1,
                                  file_path=self.F_PATH)
            self.s3obj.object_download(bucket_name=bucket_name_1, obj_name=obj_name_1,
                                       file_path=self.F_PATH_COPY)
            result = sys_util.validate_checksum(file_path_1=self.F_PATH,
                                                file_path_2=self.F_PATH_COPY)
            if result:
                assert True
            else:
                assert False
            # to do disable corruption
        except CTException as err:
            self.log.info("Test failed with %s", err)
