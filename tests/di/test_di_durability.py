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

"""
F-23B : Data Durability/Integrity test module.
"""

import os
import logging
import pytest
import secrets
from time import perf_counter_ns
from boto3.s3.transfer import TransferConfig
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.helpers.health_helper import Health
from commons.params import TEST_DATA_FOLDER, VAR_LOG_SYS
from config import CMN_CFG
from libs.s3 import S3_CFG
from commons.constants import const, MB
from libs.di.di_error_detection_test_lib import DIErrorDetection
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3 import cortxcli_test_lib
from libs.di.di_feature_control import DIFeatureControl
from libs.di.data_generator import DataGenerator
from libs.di.fi_adapter import S3FailureInjection
from libs.s3.s3_cmd_test_lib import S3CmdTestLib


class TestDIDurability:
    """DI Durability Test suite."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """
        Yield fixture to setup pre requisites and teardown them.
        Part before yield will be invoked prior to each test case and
        part after yield will be invoked after test call i.e as teardown.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: Setup test operations.")
        self.secure_range = secrets.SystemRandom()
        # self.cli_obj = cortxcli_test_lib.CortxCliTestLib()
        self.s3_test_obj = S3TestLib()
        self.s3_mp_test_obj = S3MultipartTestLib()
        self.s3_cmd_test_obj = S3CmdTestLib()
        self.di_control = DIFeatureControl(cmn_cfg=CMN_CFG)
        self.data_gen = DataGenerator()
        self.di_err_lib = DIErrorDetection()
        self.fi_adapter = S3FailureInjection(cmn_cfg=CMN_CFG)
        self.account_name = "data_durability_acc{}".format(perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.account_name)
        self.bucket_name = "data-durability-bkt{}".format(perf_counter_ns())
        self.test_file = "data_durability{}.txt".format(perf_counter_ns())
        self.object_name = "obj_data_durability"
        self.config_section = "S3_SERVER_CONFIG"
        self.write_param = const.S3_DI_WRITE_CHECK
        self.read_param = const.S3_DI_READ_CHECK
        self.integrity_param = const.S3_METADATA_CHECK
        self.sleep_time = 10
        self.file_size = 5
        self.host_ip = CMN_CFG["nodes"][0]["host"]
        self.uname = CMN_CFG["nodes"][0]["username"]
        self.passwd = CMN_CFG["nodes"][0]["password"]
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.test_dir_path = os.path.join(
            VAR_LOG_SYS, TEST_DATA_FOLDER, "TestDataDurability")
        self.file_path = os.path.join(self.test_dir_path, self.test_file)
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.hobj = Health(
            hostname=self.host_ip,
            username=self.uname,
            password=self.passwd)
        self.acc_del = False
        self.s3_account = []
        self.log.info("ENDED: setup test operations.")
        yield
        self.log.info("STARTED: Teardown operations")
        self.log.info("Deleting the file created locally for object")
        if system_utils.path_exists(self.file_path):
            system_utils.remove_dirs(self.test_dir_path)
        self.log.info("Local file was deleted")
        self.log.info("Deleting all buckets/objects created during TC execution")
        resp = self.s3_test_obj.bucket_list()
        if self.bucket_name in resp[1]:
            resp = self.s3_test_obj.delete_bucket(self.bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("All the buckets/objects deleted successfully")
        self.log.info("Deleting the IAM accounts and users")
        self.log.debug(self.s3_account)
        if self.s3_account:
            for acc in self.s3_account:
                self.cli_obj = cortxcli_test_lib.CortxCliTestLib()
                resp = self.cli_obj.login_cortx_cli(
                    username=acc, password=self.s3acc_passwd)
                self.log.debug("Deleting %s account", acc)
                self.cli_obj.delete_all_iam_users()
                self.cli_obj.logout_cortx_cli()
                self.cli_obj.delete_account_cortxcli(
                    account_name=acc, password=self.s3acc_passwd)
                self.log.info("Deleted %s account successfully", acc)
        self.log.info("Deleted the IAM accounts and users")
        # self.cli_obj.close_connection()
        self.hobj.disconnect()
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip. ")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22483')
    def test_toggle_checksum_feature_with_no_data_loss_22483(self):
        """
        Enable / disable checksum feature (data and metadata check flags and
        combinations) and time to enable it (immediate effect). No I/O drops
        should be observed.
        """
        self.log.info(
            "STARTED: Enable / disable checksum feature (data and metadata "
            "check flags and combinations) and time to enable it "
            "(immediate effect). No I/O drops should be observed.")
        self.log.info("Step 1: Start IO in background")
        # start IO in background
        self.log.info("Step 1: IO started")
        self.log.info("Step 2: Disable checksum feature combination of data "
                      "and metadata check flags")
        # resp = toggle_checksum_feature("disable")
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Checksum feature disabled successfully ")
        self.log.info("Step 3: Verify checksum feature is disable and total "
                      "time taken")
        # resp = get_checksum_feature_status()
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: verified time taken to disable the feature")
        self.log.info("Step 4: Enabled checksum feature combination of data "
                      "and metadata check flags")
        # resp = toggle_checksum_feature("enable")
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Checksum feature enabled successfully ")
        self.log.info("Step 5: Verify checksum feature is enable and total"
                      " time taken")
        # resp = get_checksum_feature_status()
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: verified time taken to enable the feature")
        self.log.info("Step 6: Stop IO and Verify no IO failure/drop observed")
        # verify started IO in background, logs
        self.log.info("Step 6: IO stopped and verified no IO error")
        self.log.info(
            "ENDED: Enable / disable checksum feature (data and metadata "
            "check flags and combinations) and time to enable it "
            "(immediate effect). No I/O drops should be observed.")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22492')
    def test_verify_read_corrupt_metadata_at_motr_lvl_22492(self):
        """
        Corrupt metadata of an object at Motr level and verify read (Get).
        """
        self.log.info(
            "STARTED: Corrupt metadata of an object at Motr level and verify "
            "read (Get).")
        self.log.info("Step 1: Create a bucket and put N object into the "
                      "bucket")
        self.file_lst = []
        for i in range(self.secure_range.randint(2, 8)):
            file_path = os.path.join(self.test_dir_path, f"file{i}.txt")
            system_utils.create_file(file_path, self.file_size)
            self.file_lst.append(file_path)
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for obj in self.file_lst:
            resp = self.s3_test_obj.put_object(
                self.bucket_name, obj, obj)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 1: Successfully put N obj into created bucket.")
        self.log.info("Step 2: Corrupt metadata of an object at Motr level")
        # resp = corrupt_metadata_of_an_obj(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Metadata of an obj corrupted at Motr level "
                      "successfully ")
        self.log.info("Step 3: Verify Get/read of an object whose metadata is "
                      "corrupted")
        for obj in self.file_lst:
            resp = self.s3_test_obj.get_object(
                self.bucket_name, obj)
            assert_utils.assert_false(resp[0], resp[1])
        self.log.info("Step 3: Read(get) of an object failed with an error")
        self.log.info("Step 4: Check for expected errors in logs.")
        # resp = get_motr_logs()
        # assert_utils.assert_equal(resp[1], "error pattern", resp[1])
        self.log.info("Step 4: Successfully checked Motr logs")
        self.log.info(
            "ENDED: Corrupt metadata of an object at Motr level and verify "
            "read (Get).")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22493')
    def test_verify_range_read_corrupt_metadata_at_motr_lvl_22493(self):
        """
        Corrupt metadata of an object at Motr level and verify range read(Get).
        """
        self.log.info(
            "STARTED: Corrupt metadata of an object at Motr level and verify "
            "range read (Get).")
        self.log.info("Step 1: Create a bucket and upload object into a "
                      "bucket.")
        self.s3_test_obj.create_bucket_put_object(
            self.bucket_name, self.object_name, self.file_path, self.file_size)
        self.log.info("Step 1: Successfully put an obj into created bucket.")
        self.log.info("Step 2: Corrupt metadata of an object at Motr level")
        # resp = corrupt_metadat_of_an_obj(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Metadata of an obj corrupted at Motr level successfully ")
        self.log.info(
            "Step 3: Verify range read (get) of an object whose metadata "
            "is corrupted")
        resp = self.s3_mp_test_obj.get_byte_range_of_object(
            self.bucket_name, self.object_name, 1025, 8192)
        assert_utils.assert_false(resp[0], resp[1])
        self.log.info(
            "Step 3: Range Read (get) of an object failed with an error")
        self.log.info("Step 4: Check for expected errors in logs.")
        # resp = get_motr_logs()
        # assert_utils.assert_equal(resp[1], "error pattern", resp[1])
        self.log.info("Step 4: Successfully checked Motr logs")
        self.log.info(
            "ENDED: Corrupt metadata of an object at Motr level and verify "
            "range read (Get).")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22497')
    @CTFailOn(error_handler)
    def test_object_data_integrity_while_upload_using_correct_checksum_22497(self):
        """
        Test to verify object integrity during the the upload with correct
        checksum.
        file size == 64 KB - 32MB
        """
        self.log.info("STARTED: Test to verify object integrity during the the upload with "
                      "correct checksum.")
        self.log.debug("Checking setup status")
        config_res = self.di_err_lib.validate_default_config()
        if config_res[1]:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        file_sizes = [64*1024, 128*1024, 256*1024, 512*1024, 1024*1024, 2*1024*1024, 4*1024*1024,
                      8*1024*1024, 16*1024*1024, 32*1024*1024]
        for file_size in file_sizes:
            self.log.info("Step 1: Creating file and calculating checksum of size %s", file_size)
            location, csm = self.di_err_lib.get_file_and_csum(size=file_size,
                                                              data_folder_prefix=self.test_dir_path)
            self.log.debug("csm: %s", csm[1])
            try:
                self.s3_test_obj.create_bucket(self.bucket_name)
                self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                            object_name=self.object_name, file_path=location,
                                            content_md5=csm[1])
            except CTException as err:
                self.log.info("Put object failed with %s", err)
            try:
                self.s3_test_obj.object_download(bucket_name=self.bucket_name,
                                                 obj_name=self.object_name,
                                                 file_path=self.file_path)
                if system_utils.validate_checksum(file_path_1=location, file_path_2=self.file_path):
                    self.log.info("Checksum Validated")
                else:
                    assert False
            except CTException as err:
                self.log.info("Download object failed with %s", err)
                assert False
        self.log.info("ENDED: Test to verify object integrity during the upload with correct "
                      "checksum.")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22498')
    def test_object_di_while_upload_using_incorrect_checksum_22498(self):
        """
        Test to verify object integrity during the upload with different checksum.
        file size == 64 KB - 32MB
        """
        self.log.info("STARTED: Test to verify object integrity during the upload with different "
                      "checksum.")
        self.log.debug("Checking setup status")
        config_res = self.di_err_lib.validate_default_config()
        if config_res[1]:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        file_sizes = [64*1024, 128*1024, 256*1024, 512*1024, 1024*1024, 2*1024*1024, 4*1024*1024,
                      8*1024*1024, 16*1024*1024, 32*1024*1024]
        try:
            self.s3_test_obj.create_bucket(self.bucket_name)
        except CTException as err:
            self.log.info("Failed with %s", err)
            assert False
        for file_size in file_sizes:
            self.log.info("Step 1: Creating file and calculating checksum of size %s", file_size)
            location, csm = self.di_err_lib.get_file_and_csum(size=file_size,
                                                              data_folder_prefix=self.test_dir_path)
            self.log.debug("csm: %s", csm[1])
            self.log.info("Attempting to upload object with corrupted checksum from client")
            corrupted_csm = "DddddDdDdDddddddddddd=="
            try:
                self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                            object_name=self.object_name, file_path=location,
                                            content_md5=corrupted_csm)
            except CTException as err:
                self.log.info("Put object failed with %s", err)
                err_str = str(err)
                if "An error occurred (InvalidDigest) when calling the PutObject operation: " \
                   "The Content-MD5 you specified is not valid" in err_str:
                    self.log.info("Error string matched")
                else:
                    assert False
            self.log.info("ENDED: Test to verify object integrity during the upload with different "
                          "checksum.")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22909')
    def test_corrupt_data_blocks_obj_motr_verify_read_22909(self):
        """
        Corrupt data blocks of an object at Motr level and verify read (Get).
        """
        self.log.info(
            "STARTED: Corrupt data blocks of an object at Motr level and "
            "verify read (Get).")
        if self.di_err_lib.validate_default_config():
            pytest.skip()
        self.log.info("Step 1: Create a bucket.")
        self.s3_test_obj.create_bucket(self.bucket_name)
        self.log.info("Step 2: Create a corrupted file.")
        location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='z',
                                                         data_folder_prefix=self.test_dir_path)
        self.log.info("Step 2: created a corrupted file at location %s", location)
        self.log.info("Step 3: enable data corruption")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.log.info("Step 3: enabled data corruption")
        else:
            self.log.info("Step 3: failed to enable data corruption")
            assert False
        self.log.info("Step 4: Put object in a bucket.")
        self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                    object_name=self.object_name,
                                    file_path=location)
        self.log.info("Step 5: Verify get object.")
        resp = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
        assert_utils.assert_false(resp[0], resp)
        self.log.info(
            "Step 5: Verified read (Get) of an object whose metadata is "
            "corrupted.")
        self.log.info(
            "Step 6: Check for expected errors in logs or notification.")
        # resp = get_motr_s3_logs()
        # assert_utils.assert_equal(resp[1], "error pattern", resp[1])
        self.log.info(
            "Step 6: Checked expected errors in logs or notification.")
        self.log.info(
            "ENDED: Corrupt data blocks of an object at Motr level and verify "
            "read (Get).")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22910')
    def test_corrupt_data_blocks_obj_motr_verify_range_read_22910(self):
        """
        Corrupt data blocks of an object at Motr level and verify range read.
        """
        self.log.info(
            "STARTED: Corrupt data blocks of an object at Motr level and "
            "verify range read (Get.")
        if self.di_err_lib.validate_default_config():
            pytest.skip()
        self.log.info("Step 1: Create a bucket.")
        self.s3_test_obj.create_bucket(self.bucket_name)
        self.log.info("Step 2: Create a corrupted file.")
        location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='z',
                                                         data_folder_prefix=self.test_dir_path)
        self.log.info("Step 2: created a corrupted file at location %s", location)
        self.log.info("Step 3: enable data corruption")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.log.info("Step 3: enabled data corruption")
        else:
            self.log.info("Step 3: failed to enable data corruption")
            assert False
        self.log.info("Step 4: Put object in a bucket.")
        self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                    object_name=self.object_name,
                                    file_path=location)
        self.log.info(
            "Step 5: Verify range read (Get) of an object whose metadata"
            " is corrupted.")
        res = self.s3_mp_test_obj.get_byte_range_of_object(
            self.bucket_name, self.object_name, 2025, 9216)
        assert_utils.assert_false(res[0], res)
        self.log.info(
            "Step 5: Verified read (Get) of an object whose data is "
            "corrupted.")
        self.log.info(
            "Step 6: Check for expected errors in logs or notification.")
        # resp = get_motr_s3_logs()
        # assert_utils.assert_equal(resp[1], "error pattern", resp[1])
        self.log.info(
            "Step 6: Checked expected errors in logs or notification.")
        self.log.info(
            "ENDED: Corrupt data blocks of an object at Motr level and verify "
            "range read (Get).")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22913')
    def test_data_unit_checksum_validate_chcksum_error_22913(self):
        """
        Exercise Data unit checksum validation (Motr metadata extent corrupt) and validate
        checksum error detection by S3/Motr.
        """
        self.log.info(
            "STARTED: Exercise Data unit checksum validation (Motr metadata extent corrupt) and"
            "validate checksum error detection by S3/Motr")
        self.log.info(
            "Step 1: Create a bucket and upload latge size object into a bucket.")
        self.s3_test_obj.create_bucket_put_object(
            self.bucket_name, self.object_name, self.file_path, 50)
        self.log.info(
            "Step 1: Created a bucket and upload object into a bucket.")
        self.log.info(
            "Step 2: Corrupt Motr metadata extent of an object.")
        # resp = corrupt_metadata_extent_of_an_obj(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Corrupted Motr metadata extent of an object.")
        self.log.info(
            "Step 3: Verify Motr detects checksum error and push errors in logs file.")
        # res = check_motr_log()
        # assert_utils.assert_true(res[0], res)
        self.log.info(
            "Step 3: Verified Motr detects checksum error and push errors in logs file.")
        self.log.info(
            "Step 4: Verify get object failed due to checksum error.")
        resp = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
        assert_utils.assert_false(resp[0], resp)
        self.log.info(
            "Step 4: Get object failed due to checksum error.")
        self.log.info(
            "ENDED: Exercise Data unit checksum validation (Motr metadata extent corrupt) and"
            "validate checksum error detection by S3/Motr")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22914')
    def test_corrupt_data_blocks_obj_motr_verify_range_read_22914(self):
        """
        Data chunk checksum validation (Motr blocks data or metadata of data blocks) and validate
        checksum error detection by S3/Motr.
        """
        self.log.info("STARTED: Data chunk checksum validation (Motr blocks data or metadata of "
                      "data blocks) and validate checksum error detection by S3/Motr")
        self.log.debug("Checking setup status")
        config_res = self.di_err_lib.validate_default_config()
        if config_res[1]:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        self.log.info("Step 1: Create a corrupted file.")
        location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='z',
                                                         data_folder_prefix=self.test_dir_path)
        self.log.info("Step 1: created a corrupted file at location %s", location)
        self.log.info("Step 2: Enable data corruption")
        status = self.di_err_lib.enable_data_corruption_set_fault_injection()
        if status:
            self.log.info("Step 2: Enabled data corruption")
        else:
            assert False
        try:
            self.log.info("Step 3: Create bucket and upload object")
            self.s3_test_obj.create_bucket(bucket_name=self.bucket_name)
            self.s3_test_obj.put_object(bucket_name=self.bucket_name, object_name=self.object_name,
                                        file_path=location)
            self.s3_test_obj.object_download(file_path=self.file_path, obj_name=self.object_name,
                                             bucket_name=self.bucket_name)
        except CTException as err:
            self.log.info("Test failed with %s", err)
            # search for internal error, if not found assert False
        # to do verify with motr logs
        status = self.di_err_lib.disable_data_corruption_set_fault_injection()
        if status:
            self.log.info("Step 2: Disabled data corruption")
        else:
            assert False
        self.log.info("ENDED: Data chunk checksum validation (Motr blocks data or metadata of "
                      "data blocks) and validate checksum error detection by S3/Motr")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22915')
    def test_motr_panic_due_to_misconfig_verify_error_22915(self):
        """
        Create Motr panic by some misconfiguration in Motr and Verify S3 checksum error detection.
        """
        self.log.info(
            "STARTED: Create Motr panic by some misconfiguration in Motr and Verify S3 checksum"
            " error detection.")
        self.log.info(
            "Step 1: Create a bucket and upload object into a bucket.")
        # range
        self.s3_test_obj.create_bucket_put_object(
            self.bucket_name, self.object_name, self.file_path, self.file_size)
        self.log.info(
            "Step 1: Created a bucket and upload object into a bucket.")
        self.log.info(
            "Step 2: Create motr panic by doing some misconfiguration in motr cfg.")
        # resp = corrupt_data_block_of_an_obj(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Created motr panic by doing some misconfiguration in motr cfg.")
        self.log.info(
            "Step 3: Get an object.")
        res = self.s3_mp_test_obj.get_object(
            self.bucket_name, self.object_name)
        assert_utils.assert_false(res[0], res)
        self.log.info(
            "Step 3: Verified get object.")
        self.log.info(
            "Step 4: Check for expected errors in motr logs or notification.")
        # resp = get_motr_s3_logs()
        # assert_utils.assert_equal(resp[1], "error pattern", resp[1])
        self.log.info(
            "Step 4: Checked for expected errors in motr logs or notification.")
        self.log.info(
            "ENDED: Create Motr panic by some misconfiguration in Motr and Verify S3 checksum"
            " error detection.")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22916')
    def test_disable_checkum_validation_download_chunk_upload_22916(self):
        """
        With Checksum flag  Disabled, download of the chunk uploaded object should
        succeed ( 30 MB -100 MB).
        """
        self.log.info(
            "STARTED: With Checksum flag  Disabled, download of the chunk uploaded object should"
            "succeed ( 30 MB -100 MB).")
        self.log.info(
            "Step 1: Disable checksum verification flag.")
        # resp = corrupt_data_block_of_an_obj(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Disabled checksum flag successfully.")
        self.log.info(
            "Step 2: Create a bucket and upload object of size 200 MB into a bucket.")
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_equal(self.bucket_name, resp[1], resp)
        system_utils.create_file(self.file_path, 200)
        self.s3_test_obj.put_object(self.bucket_name, self.object_name)
        self.log.info(
            "Step 2: Created a bucket and upload object into a bucket.")
        self.log.info(
            "Step 3: Download chunk uploaded object.")
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        res = self.s3_mp_test_obj.object_download(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(res[0], res)
        self.log.info(
            "Step 3: Download chunk uploaded object is successful.")
        self.log.info(
            "ENDED: Corrupt data blocks of an object at Motr level and "
            "verify range read (Get.")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22926')
    def test_enable_validation_induce_corruption_detect_error_22926(self):
        """
        With Flag enabled, when data or metadata corruption induced, download of
        corrupted data should flag error.
        """
        self.log.info(
            "STARTED: With Flag enabled, when data or metadata corruption induced, download of"
            "corrupted data should flag error.")
        self.log.info(
            "Step 1: Enable checksum verification flag.")
        # resp = eanble_checksum_flag(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Enabled checksum flag successfully.")
        self.log.info(
            "Step 1: Create a bucket and upload object into a bucket.")
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for i in range(self.secure_range.randint(2, 8)):
            file_name = f"{self.file_path}{i}"
            system_utils.create_file(file_name, 20)
            resp = self.s3_test_obj.put_object(
                bucket_name=self.bucket_name, object_name=file_name, file_path=self.file_path)
            self.file_lst.append(file_name)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created a bucket and upload object into a bucket.")
        self.log.info("Step 2: Induce metadata or data corruption.")
        # resp = induce_metadata_corruption(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Induced metadata or data corruption.")
        self.log.info(
            "Step 3: Verify download corrupted object.")
        for i in self.file_lst:
            dest_name = f"{i}_download"
            res = self.s3_mp_test_obj.object_download(
                self.bucket_name, i, dest_name)
            self.log.debug(res)
            # assert_utils.assert_false(res[0], res)
        self.log.info(
            "Step 3: Download object failed with corruption error.")
        self.log.info(
            "ENDED: Corrupt data blocks of an object at Motr level and "
            "verify range read (Get.")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22930')
    @CTFailOn(error_handler)
    def test_disable_checksum_should_not_validate_file_no_error_22930(self):
        """
        Disabling of Checksum feature should not do any checksum validation even if data
        corrupted.
        """
        self.log.info("STARTED: Disabling of Checksum feature should not do any checksum "
                      "validation even if data corrupted")
        if self.di_err_lib.validate_disabled_config():
            self.log.debug("Skipping test as flags are not set as test requirement")
            pytest.skip()
        self.log.debug("Executing test as flags are set as test requirement")
        try:
            self.s3_test_obj.create_bucket(self.bucket_name)
            location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='f',
                                                             data_folder_prefix=self.test_dir_path)
            self.log.debug("Step 1: created a corrupted file at location %s", location)
            self.log.info("Step 2: Enable data corruption")
            status = self.di_err_lib.enable_data_corruption_set_fault_injection()
            if status:
                self.log.info("Step 2: Enabled data corruption")
            else:
                assert False
            self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                        object_name=self.object_name, file_path=location)
            self.s3_test_obj.object_download(file_path=self.file_path,
                                             bucket_name=self.bucket_name,
                                             obj_name=self.object_name)
            status = self.di_err_lib.disable_data_corruption_set_fault_injection()
            if status:
                self.log.info("Step 2: Disabled data corruption")
            else:
                assert False
        except CTException as err:
            self.log.info("Test failed with %s", err)
            assert False
        self.log.info("ENDED: Disabling of Checksum feature should not do any checksum validation "
                      "even if data corrupted")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22931')
    def test_checksum_validation_with_ha_22931(self):
        """
        Combine checksum feature with HA.
        a) Corrupt from a node and read with other nodes.
        """
        self.log.info(
            "STARTED: Combine checksum feature with HA, corrupt from a node and read with other"
            "nodes")
        self.log.info(
            "Step 1: Enable checksum verification flag.")
        # resp = enable_checksum_flag(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Enabled checksum flag successfully.")
        self.log.info(
            "Step 1: Create a bucket and upload object into a bucket.")
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for i in range(self.secure_range.randint(2, 8)):
            file_name = f"{self.file_path}{i}"
            system_utils.create_file(file_name, 20)
            resp = self.s3_test_obj.put_object(
                bucket_name=self.bucket_name, object_name=file_name, file_path=self.file_path)
            self.file_lst.append(file_name)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 1: Created a bucket and upload object into a bucket.")
        self.log.info(
            "Step 2: Corrupt data blocks of an object at motr level.")
        # resp = corrupt_an_obj(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Corrupted data blocks of an object at motr level.")
        self.log.info(
            "Step 3: Verify get object from another node")
        s3_node_obj = S3TestLib(endpoint_url=CMN_CFG["nodes"][1]["hostname"])
        for obj in self.file_lst:
            res = s3_node_obj.get_object(self.bucket_name, obj)
            assert_utils.assert_false(res[0], res)
        self.log.info(
            "Step 3: Verified get object from another node")
        self.log.info(
            "ENDED: Combine checksum feature with HA, corrupt from a node and read with other"
            "nodes")

    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-23688')
    def test_23688(self):
        """
        Test to verify object integrity of large objects with the multipart threshold
        to value just lower the object size.
        """
        self.log.info(
            "STARTED: Test to verify object integrity of "
            "large objects with the multipart threshold"
            "to value just lower the object size.")
        resp_bkt = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp_bkt[0], resp_bkt[1])
        # Due to space constrain, using MB size obj in VM and GB size obj in HW
        if CMN_CFG.get("setup_type") == "VM":
            base_limit = 500
            upper_limit = 5001
            step_limit = 500
            file_size_count = 1  # used while creating file.i.e 1M* fileSizeCount
            gb_sz = 1024 ** 2  # used for setting MP threshold

        else:
            base_limit = 10
            upper_limit = 101
            step_limit = 10
            file_size_count = 1024  # used while creating file.i.e 1M* fileSizeCount
            gb_sz = 1024 ** 3  # used for setting MP threshold
        for up_sz in range(base_limit, upper_limit, step_limit):
            self.log.info("Creating obj of size %s and calculating checksum for it",
                          up_sz * file_size_count)
            system_utils.create_file(self.file_path, up_sz * file_size_count)
            old_checksum = system_utils.calculate_checksum(self.file_path)
            self.log.info("Created obj of size %s and calculated checksum %s ",
                          up_sz * file_size_count, old_checksum[1])
            self.log.info("Uploading an object into bucket")
            resp_upload = self.s3_test_obj.object_upload(
                self.bucket_name, self.object_name, self.file_path)
            assert_utils.assert_true(resp_upload[0], resp_upload[1])
            self.log.info("Uploaded an object %s into bucket %s", self.file_path, self.bucket_name)
            self.log.info("Removing uploaded object from a local path.")
            os.remove(self.file_path)
            self.log.info("Setting multipart threshold value to %s, less than uploaded obj size",
                          (up_sz - 5) * gb_sz)
            config = TransferConfig(multipart_threshold=(up_sz - 5) * gb_sz)
            download_obj_path = os.path.join(self.test_dir_path, "downloaded_obj")
            self.log.debug("Downloading obj from %s bucket at local path %s",
                           self.bucket_name, download_obj_path)
            resp_get_obj = self.s3_test_obj.object_download(
                self.bucket_name, self.object_name, download_obj_path, Config=config)
            assert_utils.assert_true(resp_get_obj[0], resp_get_obj[1])
            self.log.debug("Downloaded obj from %s bucket at local path %s",
                           self.bucket_name, download_obj_path)
            self.log.debug("Calculating checksum for the object downloaded and comparing with "
                           "uploaded obj checksum")
            new_checksum = system_utils.calculate_checksum(download_obj_path)
            self.log.debug("Calculated checksum for the object downloaded %s", new_checksum)
            assert_utils.assert_equal(new_checksum[1], old_checksum[1], "Incorrect checksum")
            os.remove(download_obj_path)
            self.log.debug("Validated uploaded and downloaded object checksum and removed "
                           "downloaded obj from local.")
        self.log.info(
            "ENDED: Test to verify object integrity of large objects with multipart threshold"
            "to value just lower the object size.")

    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-23689')
    def test_23689(self):
        """
        Test to verify object integrity of large objects with the multipart threshold to value
        greater than the object size.
        """
        self.log.info(
            "STARTED: Test to verify object integrity of large objects with the multipart "
            "threshold to value greater than the object size.")
        resp_bkt = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp_bkt[0], resp_bkt[1])
        if CMN_CFG.get("setup_type") == "VM":
            base_limit = 500
            upper_limit = 5001
            step_limit = 500
            file_size_count = 1  # used while creating file.i.e 1M* fileSizeCount
            gb_sz = 1024 ** 2  # used for setting MP threshold

        else:
            base_limit = 10
            upper_limit = 101
            step_limit = 10
            file_size_count = 1024  # used while creating file.i.e 1M* fileSizeCount
            gb_sz = 1024 ** 3  # used for setting MP threshold
        for up_sz in range(base_limit, upper_limit, step_limit):
            self.log.info("Creating obj of size %s and calculating checksum for it",
                          (up_sz - 5) * file_size_count)
            system_utils.create_file(self.file_path, (up_sz - 5) * file_size_count)
            old_checksum = system_utils.calculate_checksum(self.file_path)
            self.log.info("Created obj of size %s and calculated checksum %s ",
                          (up_sz - 5) * file_size_count, old_checksum[1])
            self.log.info("Uploading an object into bucket")
            resp_upload = self.s3_test_obj.object_upload(
                self.bucket_name, self.object_name, self.file_path)
            assert_utils.assert_true(resp_upload[0], resp_upload[1])
            self.log.info("Uploaded an object %s into bucket %s", self.file_path, self.bucket_name)
            self.log.info("Removing uploaded object from a local path.")
            os.remove(self.file_path)
            self.log.info("Setting multipart threshold value to %s, "
                          "greater than uploaded obj size", up_sz * gb_sz)
            config = TransferConfig(multipart_threshold=up_sz * gb_sz)
            download_obj_path = os.path.join(self.test_dir_path, "downloaded_obj")
            self.log.debug("Downloading obj from %s bucket at local path %s",
                           self.bucket_name, download_obj_path)
            resp_get_obj = self.s3_test_obj.object_download(
                self.bucket_name, self.object_name, download_obj_path, Config=config)
            assert_utils.assert_true(resp_get_obj[0], resp_get_obj[1])
            self.log.debug("Downloaded obj from %s bucket at local path %s",
                           self.bucket_name, download_obj_path)
            self.log.debug("Calculating checksum for the object downloaded and comparing with "
                           "uploaded obj checksum")
            new_checksum = system_utils.calculate_checksum(download_obj_path)
            self.log.debug("Calculated checksum for the object downloaded %s", new_checksum)
            assert_utils.assert_equal(new_checksum[1], old_checksum[1], "Incorrect checksum")
            os.remove(download_obj_path)
        self.log.info(
            "ENDED: Test to verify object integrity of large objects with the multipart "
            "threshold to value greater than the object size.")

    @pytest.mark.skip("Not tested, hence marking skip")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29813')
    def test_29813(self):
        """
        Corrupt checksum of an object 256KB to 31 MB (at s3 checksum)
        and verify range read (Get).
        """
        self.log.info("STARTED: Corrupt checksum of an object 256KB to 31 MB (at s3 checksum) "
                      "and verify range read (Get).")
        self.log.debug("Checking setup status")
        # config_res = self.di_err_lib.validate_enabled_config()
        # if config_res[1]:
        #     self.log.debug("Skipping test as flags are not set to default")
        #     pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        # simulating checksum corruption with data corruption
        # to do enabling checksum feature
        self.log.info("Step 1: create a corrupted file")
        location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='f',
                                                         data_folder_prefix=self.test_dir_path)
        self.log.info("Step 1: created a corrupted file at location %s", location)
        self.log.info("Step 2: Enable data corruption")
        status = self.di_err_lib.enable_data_corruption_set_fault_injection()
        if status:
            self.log.info("Step 2: Enabled data corruption")
        else:
            assert False
        try:
            self.log.info("Step 3: Create bucket and upload object")
            self.s3_test_obj.create_bucket(bucket_name=self.bucket_name)
            self.s3_test_obj.put_object(bucket_name=self.bucket_name, object_name=self.object_name,
                                        file_path=location)
            # to do verify range read
            # self.s3_mp_test_obj.get_byte_range_of_object(bucket_name=self.bucket_name,
            #                                              my_key=self.object_name,
            #                                              start_byte=8888, stop_byte=9999)
            # self.s3_test_obj.object_download(file_path=self.file_path, obj_name=self.object_name,
            #                                  bucket_name=self.bucket_name)
        except CTException as err:
            self.log.info("Test failed with %s", err)
            # search for internal error, if not found assert False
        status = self.di_err_lib.disable_data_corruption_set_fault_injection()
        if status:
            self.log.info("Step 2: Disabled data corruption")
        else:
            assert False
        self.log.info("ENDED: Corrupt checksum of an object 256KB to 31 MB (at s3 checksum) "
                      "and verify range read (Get).")

    @pytest.mark.skip("Not tested, hence marking skip")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29812')
    def test_29812(self):
        """
        Corrupt checksum of an object 256KB to 31 MB (at s3 checksum) and verify read (Get).
        """
        self.log.info("STARTED: Corrupt checksum of an object 256KB to 31 MB "
                      "(at s3 checksum) and verify read (Get).")
        self.log.debug("Checking setup status")
        # config_res = self.di_err_lib.validate_enabled_config()
        # if config_res[1]:
        #     self.log.debug("Skipping test as flags are not set to default")
        #     pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        # simulating checksum corruption with data corruption
        # to do enabling checksum feature
        self.log.info("Step 1: create a corrupted file")
        location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='f',
                                                         data_folder_prefix=self.test_dir_path)
        self.log.info("Step 1: created a corrupted file at location %s", location)
        self.log.info("Step 2: Enable data corruption")
        status = self.di_err_lib.enable_data_corruption_set_fault_injection()
        if status:
            self.log.info("Step 2: Enabled data corruption")
        else:
            assert False
        try:
            self.log.info("Step 3: Create bucket and upload object")
            self.s3_test_obj.create_bucket(bucket_name=self.bucket_name)
            self.s3_test_obj.put_object(bucket_name=self.bucket_name, object_name=self.object_name,
                                        file_path=location)
            self.s3_test_obj.object_download(file_path=self.file_path, obj_name=self.object_name,
                                             bucket_name=self.bucket_name)
        except CTException as err:
            self.log.info("Test failed with %s", err)
            # search for internal error, if not found assert False
        status = self.di_err_lib.disable_data_corruption_set_fault_injection()
        if status:
            self.log.info("Step 2: Disabled data corruption")
        else:
            assert False
        self.log.info("ENDED: Corrupt checksum of an object 256KB to 31 MB "
                      "(at s3 checksum) and verify read (Get).")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29816')
    def test_29816(self):
        """
        S3 Put through AWS CLI and Corrupt checksum of an object 256KB to 31 MB (at s3 checksum)
        and verify read (Get).
        SZ <= Data Unit Sz
        """
        self.log.info("STARTED: S3 Put through AWS CLI and Corrupt checksum of an object"
                      "256KB to 31 MB (at s3 checksum) and verify read (Get).")
        self.log.debug("Checking setup status")
        config_res = self.di_err_lib.validate_default_config()
        if config_res[1]:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        # simulating checksum corruption with data corruption
        # to do enabling checksum feature
        self.log.info("Step 1: Create a corrupted file.")
        location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='z',
                                                         data_folder_prefix=self.test_dir_path)
        self.log.info("Step 1: Created a corrupted file at location %s", location)
        self.log.info("Step 2: Enable data corruption")
        status = self.di_err_lib.enable_data_corruption_set_fault_injection()
        if status:
            self.log.info("Step 2: Enabled data corruption")
        else:
            assert False
        self.log.info("Step 3: Upload a file using aws cli")
        self.s3_test_obj.create_bucket(self.bucket_name)
        self.s3_cmd_test_obj.upload_object_cli(bucket_name=self.bucket_name,
                                               object_name=self.object_name, file_path=location)
        try:
            self.s3_test_obj.object_download(bucket_name=self.bucket_name,
                                             obj_name=self.object_name, file_path=self.file_path)
        except CTException as err:
            self.log.info("Test failed with %s", err)
            # search for internal error, if not found assert False
        status = self.di_err_lib.disable_data_corruption_set_fault_injection()
        if status:
            self.log.info("Step 2: Disabled data corruption")
        else:
            assert False
        self.log.info("STARTED: S3 Put through AWS CLI and Corrupt checksum of an object"
                      "256KB to 31 MB (at s3 checksum) and verify read (Get).")

    @pytest.mark.skip(reason="Not tested hence marking skip.")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29817')
    def test_29817(self):
        """
        S3 Put through S3CMD and Corrupt checksum of an object 256KB to 31 MB (at s3 checksum)
        and verify read (Get).
        SZ <= Data Unit Sz

        """
        self.log.info("STARTED: S3 Put through S3CMD and Corrupt checksum of an object"
                      "256KB to 31 MB (at s3 checksum) and verify read (Get).")
        self.log.debug("Checking setup status")
        config_res = self.di_err_lib.validate_default_config()
        if config_res[1]:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        # simulating checksum corruption with data corruption
        # to do enabling checksum feature
        self.log.info("Step 1: Create a corrupted file.")
        location = self.di_err_lib.create_corrupted_file(size=1024 * 1024 * 5, first_byte='z',
                                                         data_folder_prefix=self.test_dir_path)
        self.log.info("Step 1: created a corrupted file at location %s", location)
        self.log.info("Step 2: Enable data corruption")
        status = self.di_err_lib.enable_data_corruption_set_fault_injection()
        if status:
            self.log.info("Step 2: Enabled data corruption")
        else:
            assert False
        self.log.info("Step 3: Upload a file using S3CMD")
        self.s3_test_obj.create_bucket(self.bucket_name)
        # to do put object using s3cmd
        try:
            self.s3_test_obj.object_download(bucket_name=self.bucket_name,
                                             obj_name=self.object_name, file_path=self.file_path)
        except CTException as err:
            self.log.info("Test failed with %s", err)
            # search for internal error, if not found assert False
        status = self.di_err_lib.disable_data_corruption_set_fault_injection()
        if status:
            self.log.info("Step 2: Disabled data corruption")
        else:
            assert False
        self.log.info("STARTED: S3 Put through S3CMD and Corrupt checksum of an object"
                      "256KB to 31 MB (at s3 checksum) and verify read (Get).")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22912')
    def test_22912(self):
        """
        Test to verify object integrity during the the upload with correct checksum.
        Specify checksum and checksum algorithm or ETAG during
        PUT(MD5 with and without digest, CRC ( check multi-part))
        """
        sz = 128 * MB
        self.log.info("STARTED TEST-22912: Test to verify object integrity "
                      "during the the upload with correct checksum.")
        # config_res = self.di_err_lib.validate_enabled_config()
        # if config_res[1]:
        #     self.log.debug("Skipping test as flags are not set to default")
        #     pytest.skip()
        self.log.info("Step 1: create a file")
        buff, csm = self.data_gen.generate(size=1024 * 1024 * 5,
                                           seed=self.data_gen.get_random_seed())
        location = self.data_gen.create_file_from_buf(fbuf=buff, name=self.file_path, size=sz)
        self.log.info("Step 1: created a file at location %s", location)
        self.log.info("Step 2: enable checksum feature")
        # to do enabling checksum feature
        self.log.info("Step 3: upload a file with incorrect checksum")
        self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                    object_name=self.object_name,
                                    file_path=location)
        dwn_file_name = os.path.split(self.file_path)[-1]
        dwn_file_dir = os.path.split(self.file_path)[0]
        dwn_file_path = os.path.join(dwn_file_dir, 'dwn' + dwn_file_name)
        self.s3_test_obj.object_download(file_path=dwn_file_path,
                                         obj_name=self.object_name,
                                         bucket_name=self.bucket_name)
        file_checksum = system_utils.calculate_checksum(dwn_file_path, binary_bz64=False)[1]
        assert_utils.assert_exact_string(csm, file_checksum, 'Checksum mismatch found')
        self.log.info("Step 4: verify download object passes without 5xx error code")
        self.log.info("ENDED TEST-22912")
