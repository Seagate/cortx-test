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

"""Data Durability test module."""

import os
import time
import logging
import secrets
from time import perf_counter_ns

import pytest
from commons.constants import const
from commons import commands as cmd
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.params import TEST_DATA_FOLDER
from libs.s3 import S3H_OBJ, CMN_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.iam_test_lib import IamTestLib
from libs.s3 import cortxcli_test_lib
from libs.s3 import S3_CFG

S3T_OBJ = S3TestLib()
IAMT_OBJ = IamTestLib()


class TestDataDurability:
    """Data Durability Test suite."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: setup test operations.")
        self.secure_range = secrets.SystemRandom()
        self.cli_obj = cortxcli_test_lib.CortxCliTestLib()
        self.log.info("STARTED: setup test operations.")
        self.account_name = "data_durability_acc{}".format(perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.account_name)
        self.bucket_name = "data-durability-bkt{}".format(perf_counter_ns())
        self.test_file = "data_durability{}.txt".format(perf_counter_ns())
        self.object_name = "obj_data_durability"
        self.sleep_time = 10
        self.file_size = 5
        self.host_ip = CMN_CFG["nodes"][0]["host"]
        self.uname = CMN_CFG["nodes"][0]["username"]
        self.passwd = CMN_CFG["nodes"][0]["password"]
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.test_dir_path = os.path.join(
            os.getcwd(), TEST_DATA_FOLDER, "TestDataDurability")
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
            system_utils.remove_file(self.file_path)
        self.log.info("Local file was deleted")
        self.log.info("Deleting all buckets/objects created during TC execution")
        resp = S3T_OBJ.bucket_list()
        if self.bucket_name in resp[1]:
            resp = S3T_OBJ.delete_bucket(self.bucket_name, force=True)
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
        self.cli_obj.close_connection()
        self.hobj.disconnect()
        self.log.info("ENDED: Teardown operations")

    def create_bkt_put_obj(self):
        """
        Function will create a bucket and uploads an object to it.

        also it will calculate checksum of file content
        :return str: Checksum of file content
        """
        self.log.info(
            "Step 1: Creating a file with name %s", (
                self.test_file))
        system_utils.create_file(self.file_path, self.file_size)
        self.log.info(
            "Step 1: Created a file with name %s", (
                self.test_file))
        self.log.info(
            "Step 2: Retrieving checksum of file %s", (
                self.test_file))
        resp1 = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp1[0], resp1[1])
        chksm_before_put_obj = resp1[1]
        self.log.info(
            "Step 2: Retrieved checksum of file %s", (
                self.test_file))
        self.log.info(
            "Step 3: Uploading a object to a bucket %s", (
                self.bucket_name))
        resp = S3T_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3T_OBJ.put_object(
            self.bucket_name,
            self.object_name,
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = S3T_OBJ.object_list(self.bucket_name)
        assert_utils.assert_in(
            self.object_name,
            resp[1],
            f"Failed to upload create {self.object_name}")
        self.log.info(
            "Step 3: Uploaded an object to a bucket %s", (
                self.bucket_name))
        return chksm_before_put_obj

    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-8005')
    @pytest.mark.parametrize("service", [const.S3AUTHSERVER])
    def test_no_data_loss_in_case_service_restart_4232(self, service):
        """Test NO data loss in case of service restart- s3authserver."""
        self.log.info(
            "STARTED: Test NO data loss in case of service restart- %s", service)
        restart_cmd = cmd.SYSTEM_CTL_RESTART_CMD.format(service)
        checksum_before_put_obj = self.create_bkt_put_obj()
        self.log.info(
            "Step 4: Restarting %s service",
            service)
        system_utils.run_remote_cmd(
            restart_cmd,
            self.host_ip,
            self.uname,
            self.passwd)
        time.sleep(self.sleep_time)
        resp = S3H_OBJ.get_s3server_service_status(
            service)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 4: Restarted %s service",
            service)
        self.log.info("Step 5: Verifying that data is accessible or not")
        resp = S3T_OBJ.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            self.object_name,
            resp[1],
            f"Failed to list object '{self.object_name}' after service restart.")
        self.log.info("Step 5: Verified that data is accessible")
        self.log.info(
            "Step 6: Removing file from client and downloading object")
        system_utils.remove_file(self.file_path)
        resp = S3T_OBJ.object_download(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Downloaded object from a bucket")
        self.log.info(
            "Step 7: Verifying checksum of downloaded file with old file should be same")
        resp = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        chksm_after_dwnld_obj = resp[1]
        assert_utils.assert_equal(
            checksum_before_put_obj,
            chksm_after_dwnld_obj)
        self.log.info(
            "Step 7: Verified checksum of downloaded file with old file")
        self.log.info(
            "ENDED: Test NO data loss in case of service restart- %s", service)

    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-8006')
    @CTFailOn(error_handler)
    def test_no_data_loss_in_case_haproxy_restart_4233(self):
        """Test NO data loss in case of service restart - haproxy."""
        self.test_no_data_loss_in_case_service_restart_4232(const.HAPROXY)

    @pytest.mark.skip(reason="Will be taken after F-45H.")
    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-8009')
    @CTFailOn(error_handler)
    def test_no_data_loss_in_case_account_cred_change_4238(self):
        """Test NO data loss in case of account credentials change."""
        self.log.info(
            "STARTED: Test NO data loss in case of account credentials change")
        self.log.info(
            "Step 1: Creating a file with name %s", (
                self.test_file))
        system_utils.create_file(self.file_path, self.file_size)
        self.log.info(
            "Step 1: Created a file with name %s", (
                self.test_file))
        self.log.info(
            "Step 2: Retrieving checksum of file %s", (
                self.test_file))
        resp1 = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp1[0], resp1[1])
        chksm_before_put_obj = resp1[1]
        self.log.info(
            "Step 2: Retrieved checksum of file %s", (
                self.test_file))
        self.log.info(
            "Step 3: Uploading a object to a bucket %s", (
                self.bucket_name))
        resp = self.cli_obj.create_account_cortxcli(self.account_name,
                                                    self.email_id,
                                                    self.s3acc_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        s3_test_obj = S3TestLib(
            access_key=access_key, secret_key=secret_key)
        resp = s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Uploaded an object to a bucket %s", (
                self.bucket_name))
        self.log.info(
            "Step 4: Changing credentials of an account %s", self.account_name)
        resp = IAMT_OBJ.reset_account_access_key_s3iamcli(self.account_name)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["AccessKeyId"]
        secret_key = resp[1]["SecretKey"]
        self.s3_account.append(self.account_name)
        s3_temp_obj = S3TestLib(
            access_key=access_key, secret_key=secret_key)
        self.log.info(
            "Step 4: Changed credentials of an account %s", self.account_name)
        self.log.info(
            "Step 5: Verifying that data is accessible with new set of credentials")
        resp = s3_temp_obj.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            self.object_name,
            resp[1],
            f"Failed to list object '{self.object_name}' after service restart.")
        self.log.info(
            "Step 5: Verified that data is accessible with new set of credentials")
        self.log.info(
            "Step 6: Removing file from client and downloading object")
        system_utils.remove_file(self.file_path)
        resp = s3_temp_obj.object_download(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Downloaded object from a bucket")
        self.log.info(
            "Step 7: Verifying checksum of downloaded file with old file should be same")
        resp = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        chksm_after_dwnld_obj = resp[1]
        assert_utils.assert_equal(chksm_before_put_obj, chksm_after_dwnld_obj)
        self.log.info(
            "Step 7: Verified checksum of downloaded file with old file")
        # Cleanup activity
        resp = s3_temp_obj.delete_bucket(self.bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Test NO data loss in case of account credentials change")

    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-8004')
    @CTFailOn(error_handler)
    def test_no_data_loss_corruption_in_case_s3server_restart_4231(self):
        """Test NO data loss or corruption in case of service restart - s3server."""
        self.log.info(
            "STARTED: Test NO data loss or corruption in case of service restart - s3server")
        checksum_before_put_obj = self.create_bkt_put_obj()
        self.log.info("Step 4: Restart s3server instances")
        resp = S3H_OBJ.restart_s3server_processes(
            self.host_ip, self.uname, self.passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Restart s3server instances")
        self.log.info("Step 5: Verifying that data is accessible or not")
        resp = S3T_OBJ.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            self.object_name,
            resp[1],
            f"Failed to list object '{self.object_name}' after service restart.")
        self.log.info("Step 5: Verified that data is accessible")
        self.log.info(
            "Step 6: Removing file from client and downloading object")
        system_utils.remove_file(self.file_path)
        resp = S3T_OBJ.object_download(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Downloaded object from a bucket")
        self.log.info(
            "Step 7: Verifying checksum of downloaded file with old file should be file")
        resp = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        chksm_after_dwnld_obj = resp[1]
        assert_utils.assert_equal(
            checksum_before_put_obj,
            chksm_after_dwnld_obj)
        self.log.info(
            "Step 7: Verified checksum of downloaded file with old file")
        self.log.info(
            "ENDED: Test NO data loss or corruption in case of service restart - s3server")

    @pytest.mark.skip(reason="Restarting cluster make avalanche effect.")
    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-8007')
    @CTFailOn(error_handler)
    def test_no_data_loss_in_case_motr_restart_4234(self):
        """Test NO data loss in case of service restart - motr."""
        self.log.info(
            "STARTED: Test NO data loss in case of service restart - motr")
        checksum_before_put_obj = self.create_bkt_put_obj()
        self.log.info("Step 4: Restarting motr service")
        resp = self.hobj.pcs_restart_cluster()
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Restarted motr service")
        self.log.info("Step 5: Verifying that data is accessible or not")
        resp = S3T_OBJ.object_list(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            self.object_name,
            resp[1],
            f"Failed to list object '{self.object_name}' after service restart.")
        self.log.info("Step 5: Verified that data is accessible")
        self.log.info(
            "Step 6: Removing file from client and downloading object")
        system_utils.remove_file(self.file_path)
        resp = S3T_OBJ.object_download(
            self.bucket_name, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Downloaded object from a bucket")
        self.log.info(
            "Step 7: Verifying checksum of downloaded file with old file should be file")
        resp = system_utils.get_file_checksum(self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        chksm_after_dwnld_obj = resp[1]
        assert_utils.assert_equal(
            checksum_before_put_obj,
            chksm_after_dwnld_obj)
        self.log.info(
            "Step 7: Verified checksum of downloaded file with old file")
        self.log.info(
            "ENDED: Test NO data loss in case of service restart - motr")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22483')
    @CTFailOn(error_handler)
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
    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22492')
    @CTFailOn(error_handler)
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
        for i in range(self.secure_range.randint(2,8)):
            file_path = os.path.join(self.test_dir_path, f"file{i}.txt")
            system_utils.create_file(file_path, self.file_size)
            self.file_lst.append(file_path)
        resp = S3T_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for obj in self.file_lst:
            resp = S3T_OBJ.put_object(
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
            resp = S3T_OBJ.get_object(
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
    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22493')
    @CTFailOn(error_handler)
    def test_verify_range_read_corrupt_metadata_at_motr_lvl_22493(self):
        """
        Corrupt metadata of an object at Motr level and verify range read(Get).
        """
        self.log.info(
            "STARTED: Corrupt metadata of an object at Motr level and verify "
            "range read (Get).")
        self.log.info("Step 1: Create a bucket and upload object into a "
                      "bucket.")
        self.create_bkt_put_obj()
        self.log.info("Step 1: Successfully put an obj into created bucket.")
        self.log.info("Step 2: Corrupt metadata of an object at Motr level")
        # resp = corrupt_metadat_of_an_obj(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Metadata of an obj corrupted at Motr level successfully ")
        self.log.info(
            "Step 3: Verify range read (get) of an object whose metadata "
            "is corrupted")
        resp = S3T_OBJ.get_object(
            self.bucket_name, self.object_name)
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

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22497')
    @CTFailOn(error_handler)
    def test_object_data_integrity_while_upload_using_correct_checksum_22497(
            self):
        """
        Test to verify object integrity during the the upload with correct
        checksum.
        """
        self.log.info(
            "STARTED: Test to verify object integrity during the the upload "
            "with correct checksum.")
        self.log.info("Step 1: Create N objects of size 10 MB")
        self.file_lst = []
        for i in range(self.secure_range.randint(2,8)):
            file_path = os.path.join(self.test_dir_path, f"file{i}.txt")
            system_utils.create_file(file_path, 10)
            self.file_lst.append(file_path)
        self.log.info(
            "Step 1: Created %s objects of size 10 MB", len(self.file_lst))
        self.log.info("Step 2: Calculate MD5checksum (base64-encoded MD5 "
                      "checksum ) for all obj")
        checksum_dict = {}
        for file in self.file_lst:
            checksum_dict[file] = system_utils.calculate_checksum(file)
        self.log.info("Step 2: Calculate MD5checksum ("
                      "base64-encoded MD5 checksum ) for all obj")
        self.log.info(
            "Step 3: Put objects into a bucket with a calculated checksum"
            " pass in content-md5 field")
        resp = S3T_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for file, binary_checksum in checksum_dict.items():
            resp = S3T_OBJ.put_object(
                bucket_name=self.bucket_name, object_name=file, file_path=file,
                content_md5=binary_checksum)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 3: Put objects into a bucket with calculated checksum pass"
            " in content-md5 field")
        self.log.info(
            "ENDED: Test to verify object integrity during the upload "
            "with correct checksum.")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22498')
    @CTFailOn(error_handler)
    def test_object_di_while_upload_using_incorrect_checksum_22498(self):
        """
        Test to verify object integrity during the upload with different
        checksum.
        """
        self.log.info(
            "STARTED: Test to verify object integrity during the upload with "
            "different checksum.")
        self.log.info("Step 1: Create N objects of size 10MB")
        self.file_lst = []
        for i in range(self.secure_range.randint(2,8)):
            file_path = os.path.join(self.test_dir_path, f"file{i}.txt")
            system_utils.create_file(file_path, 10)
            self.file_lst.append(file_path)
        self.log.info(
            "Step 1: Created %s object of size 10MB", len(self.file_lst))
        self.log.info("Step 2: Calculate MD5checksum (base64-encoded MD5 "
                      "checksum ) for all obj")
        checksum_dict = {}
        for file in self.file_lst:
            checksum_dict[file] = system_utils.calculate_checksum(file)
        self.log.info(
            "Step 2: Calculate MD5checksum (base64-encoded MD5 checksum ) for "
            "all obj")
        self.log.info(
            "Step 3: Put objects into bucket with different calculated "
            "checksum pass in content-md5 field")
        resp = S3T_OBJ.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for file, binary_checksum in checksum_dict.items():
            resp = S3T_OBJ.put_object(
                bucket_name=self.bucket_name, object_name=file, file_path=file,
                content_md5=binary_checksum)
            assert_utils.assert_false(resp[0], resp[1])
        self.log.info(
            "Step 3: Failed to put objects into bucket with different "
            "calculated checksum")
        self.log.info(
            "ENDED: Test to verify object integrity during the upload with "
            "different checksum.")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22501')
    @CTFailOn(error_handler)
    def test_checksum_validation_file_spread_across_storage_22501(self):
        """
        Test checksum validation of a file spread across storage set .
        """
        self.log.info(
            "STARTED: Test checksum validation of a file spread across "
            "storage set .")
        self.log.info(
            "Step 1: Create a bucket and put and mid-large size object.")
        self.file_size = 40
        self.create_bkt_put_obj()
        self.log.info("Step 2: Verify checksum of a file across storage set.")
        # resp = verify_checsum_file_across_storage_set(self.file_path)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Test checksum validation of a file spread across "
            "storage set.")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22909')
    @CTFailOn(error_handler)
    def test_corrupt_data_blocks_obj_motr_verify_read_22909(self):
        """
        Corrupt data blocks of an object at Motr level and verify read (Get).
        """
        self.log.info(
            "STARTED: Corrupt data blocks of an object at Motr level and "
            "verify read (Get).")
        self.log.info(
            "Step 1: Create a bucket and upload object into a bucket.")
        self.create_bkt_put_obj()
        self.log.info(
            "Step 1: Created a bucket and upload object into a bucket.")
        self.log.info(
            "Step 2: Corrupt data blocks of an object at motr level.")
        # resp = corrupt_data_block_of_an_obj(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Corrupt data blocks of an object at motr level.")
        self.log.info(
            "Step 3: Verify read (Get) of an object whose metadata is "
            "corrupted.")
        res = S3T_OBJ.get_object(self.bucket_name, self.object_name)
        assert_utils.assert_false(res[0], res)
        self.log.info(
            "Step 3: Verified read (Get) of an object whose metadata is "
            "corrupted.")
        self.log.info(
            "Step 4: Check for expected errors in logs or notification.")
        # resp = get_motr_s3_logs()
        # assert_utils.assert_equal(resp[1], "error pattern", resp[1])
        self.log.info(
            "Step 4: Checked expected errors in logs or notification.")
        self.log.info(
            "ENDED: Corrupt data blocks of an object at Motr level and verify "
            "read (Get).")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
    @pytest.mark.s3_ops
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22910')
    @CTFailOn(error_handler)
    def test_corrupt_data_blocks_obj_motr_verify_range_read_22910(self):
        """
        Corrupt data blocks of an object at Motr level and verify range read.
        """
        self.log.info(
            "STARTED: Corrupt data blocks of an object at Motr level and "
            "verify range read (Get.")
        self.log.info(
            "Step 1: Create a bucket and upload object into a bucket.")
        self.create_bkt_put_obj()
        self.log.info(
            "Step 1: Created a bucket and upload object into a bucket.")
        self.log.info(
            "Step 2: Corrupt data blocks of an object at motr level.")
        # resp = corrupt_data_block_of_an_obj(object)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 2: Corrupted data blocks of an object at motr level.")
        self.log.info(
            "Step 3: Verify range read (Get) of an object whose metadata"
            " is corrupted.")
        res = S3T_OBJ.get_object(self.bucket_name, self.object_name)
        assert_utils.assert_false(res[0], res)
        self.log.info(
            "Step 3: Verified range read (Get) of an object whose metadata"
            " is corrupted.")
        self.log.info(
            "Step 4: Check for expected errors in logs or notification.")
        # resp = get_motr_s3_logs()
        # assert_utils.assert_equal(resp[1], "error pattern", resp[1])
        self.log.info(
            "Step 4: Checked for expected errors in logs or notification.")
        self.log.info(
            "ENDED: Corrupt data blocks of an object at Motr level and "
            "verify range read (Get.")
