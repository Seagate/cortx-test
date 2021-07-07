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
F-23B : Data Durability test module.
"""

import os
import logging
import pytest
import secrets
from time import perf_counter_ns
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.params import TEST_DATA_FOLDER, VAR_LOG_SYS
from libs.s3 import CMN_CFG, S3_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3 import cortxcli_test_lib
from boto3.s3.transfer import TransferConfig


class TestDIDurability:
    """DI Durability Test suite."""

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
        self.s3_test_obj = S3TestLib()
        self.s3_mp_test_obj = S3MultipartTestLib()
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
            system_utils.remove_file(self.file_path)
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
        self.cli_obj.close_connection()
        self.hobj.disconnect()
        self.log.info("ENDED: Teardown operations")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
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

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
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
        for i in range(self.secure_range.randint(2, 8)):
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
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for file, binary_checksum in checksum_dict.items():
            resp = self.s3_test_obj.put_object(
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
        for i in range(self.secure_range.randint(2, 8)):
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
        resp = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        for file, binary_checksum in checksum_dict.items():
            resp = self.s3_test_obj.put_object(
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
        self.s3_test_obj.create_bucket_put_object(
            self.bucket_name, self.object_name, self.file_path, 40)
        self.log.info("Step 2: Verify checksum of a file across storage set.")
        # resp = verify_checsum_file_across_storage_set(self.file_path)
        # assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Test checksum validation of a file spread across "
            "storage set.")

    @pytest.mark.skip(reason="Feature is not in place hence marking skip.")
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
        self.s3_test_obj.create_bucket_put_object(
            self.bucket_name, self.object_name, self.file_path, self.file_size)
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
        res = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
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
        self.s3_test_obj.create_bucket_put_object(
            self.bucket_name, self.object_name, self.file_path, self.file_size)
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
        res = self.s3_mp_test_obj.get_byte_range_of_object(
            self.bucket_name, self.object_name, 2025, 9216)
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

    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-23688')
    @CTFailOn(error_handler)
    def test_23688(self):
        """
        Test to verify object integrity of large objects with the multipart threshold
        to value just lower the object size.
        """
        self.log.info(
            "STARTED: Test to verify object integrity of large objects with the multipart threshold"
            "to value just lower the object size.")
        resp_bkt = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(resp_bkt[0], resp_bkt[1])
        # Due to space constrain, using MB size obj in VM and GB size obj in HW
        if "VM" == CMN_CFG.get("setup_type"):
            file_size_count = 1  # used while creating file.i.e 1M* fileSizeCount
            gb_sz = 1024 ** 2  # used for setting MP threshold

        else:
            file_size_count = 1024  # used while creating file.i.e 1M* fileSizeCount
            gb_sz = 1024 ** 3  # used for setting MP threshold
        obj_upload_size_lst = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        obj_down_size_lst = [9, 19, 28, 38, 489, 58, 69, 78, 88, 99]
        for up_sz, dw_sz in zip(obj_upload_size_lst, obj_down_size_lst):
            self.log.info("Creating obj of size %s and calculating checksum for it",
                          up_sz * file_size_count)
            system_utils.create_file(self.file_path, up_sz * file_size_count)
            old_checksum = system_utils.get_file_checksum(self.file_path)
            self.log.info("Created obj of size %s and calculated checksum %s ",
                          up_sz * file_size_count, old_checksum[1])
            self.log.info("Setting default multipart threshold value")
            config = TransferConfig(multipart_threshold=1024 * 1024 * 8)
            self.log.info("Uploading an object into bucket")
            resp_upload = self.s3_test_obj.object_upload(
                self.bucket_name, self.object_name, self.file_path)
            assert_utils.assert_true(resp_upload[0], resp_upload[1])
            self.log.info("Uploaded an object %s into bucket %s", self.file_path, self.bucket_name)
            self.log.info("Removing uploaded object from a local path.")
            os.remove(self.file_path)
            self.log.info("Setting multipart threshold value to %s, less than uploaded obj size",
                          dw_sz * gb_sz)
            config = TransferConfig(multipart_threshold=dw_sz * gb_sz)
            self.download_obj_path = os.path.join(self.test_dir_path, "downloaded_obj")
            self.log.debug("Downloading obj from %s bucket at local path %s",
                           self.bucket_name, self.download_obj_path)
            resp_get_obj = self.s3_test_obj.object_download(
                self.bucket_name, self.object_name, self.download_obj_path, Config=config)
            assert_utils.assert_true(resp_get_obj[0], resp_get_obj[1])
            self.log.debug("Downloaded obj from %s bucket at local path %s",
                           self.bucket_name, self.download_obj_path)
            self.log.debug("Calculating checksum for the object downloaded and comparing with "
                           "uploaded obj checksum")
            new_checksum = system_utils.get_file_checksum(self.download_obj_path)
            self.log.debug("Calculated checksum for the object downloaded %s", new_checksum)
            assert_utils.assert_equal(new_checksum[1], old_checksum[1], "Incorrect checksum")
            os.remove(self.download_obj_path)
            self.log.debug("Validated uploaded and downloaded object checksum and removed "
                           "downloaded obj from local.")
        self.log.info(
            "ENDED: Test to verify object integrity of large objects with multipart threshold"
            "to value just lower the object size.")

    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-23689')
    @CTFailOn(error_handler)
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
        if "VM" == CMN_CFG.get("setup_type"):
            file_size_count = 1  # used while creating file.i.e 1M* fileSizeCount
            gb_sz = 1024 ** 2  # used for setting MP threshold

        else:
            file_size_count = 1024  # used while creating file.i.e 1M* fileSizeCount
            gb_sz = 1024 ** 3  # used for setting MP threshold
        obj_upload_size_lst = [9, 19, 28, 38, 49, 58, 68, 78, 88, 99]
        obj_down_size_lst = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for up_sz, dw_sz in zip(obj_upload_size_lst, obj_down_size_lst):
            self.log.info("Creating obj of size %s and calculating checksum for it",
                          up_sz * file_size_count)
            system_utils.create_file(self.file_path, up_sz * file_size_count)
            old_checksum = system_utils.get_file_checksum(self.file_path)
            self.log.info("Created obj of size %s and calculated checksum %s ",
                          up_sz * file_size_count, old_checksum[1])
            self.log.info("Setting default multipart threshold value")
            config = TransferConfig(multipart_threshold=1024 * 1024 * 8)
            self.log.info("Uploading an object into bucket")
            resp_upload = self.s3_test_obj.object_upload(
                self.bucket_name, self.object_name, self.file_path)
            assert_utils.assert_true(resp_upload[0], resp_upload[1])
            self.log.info("Uploaded an object %s into bucket %s", self.file_path, self.bucket_name)
            self.log.info("Removing uploaded object from a local path.")
            os.remove(self.file_path)
            self.log.info("Setting multipart threshold value to %s, greater than uploaded obj size",
                          dw_sz * gb_sz)
            config = TransferConfig(multipart_threshold=dw_sz * gb_sz)
            self.download_obj_path = os.path.join(self.test_dir_path, "downloaded_obj")
            self.log.debug("Downloading obj from %s bucket at local path %s",
                           self.bucket_name, self.download_obj_path)
            resp_get_obj = self.s3_test_obj.object_download(
                self.bucket_name, self.object_name, self.download_obj_path, Config=config)
            assert_utils.assert_true(resp_get_obj[0], resp_get_obj[1])
            self.log.debug("Downloaded obj from %s bucket at local path %s",
                           self.bucket_name, self.download_obj_path)
            self.log.debug("Calculating checksum for the object downloaded and comparing with "
                           "uploaded obj checksum")
            new_checksum = system_utils.get_file_checksum(self.download_obj_path)
            self.log.debug("Calculated checksum for the object downloaded %s", new_checksum)
            assert_utils.assert_equal(new_checksum[1], old_checksum[1], "Incorrect checksum")
            os.remove(self.download_obj_path)
        self.log.info(
            "ENDED: Test to verify object integrity of large objects with the multipart "
            "threshold to value greater than the object size.")
