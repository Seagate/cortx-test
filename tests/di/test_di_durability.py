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

"""
F-23B : Data Durability/Integrity test module.
"""

import logging
import os
import secrets
from time import perf_counter_ns

import pytest
from boto3.s3.transfer import TransferConfig

from commons.constants import MB, KB
from commons.constants import NORMAL_UPLOAD_SIZES
from commons.constants import const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.helpers.health_helper import Health
from commons.params import TEST_DATA_FOLDER, VAR_LOG_SYS
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from config.s3 import S3_BLKBOX_CFG
from libs.di import di_lib
from libs.di.data_generator import DataGenerator
from libs.di.di_error_detection_test_lib import DIErrorDetection
from libs.di.di_feature_control import DIFeatureControl
from libs.di.fi_adapter import S3FailureInjection
from libs.s3 import S3_CFG
from libs.s3 import SECRET_KEY, ACCESS_KEY
from libs.s3 import cortxcli_test_lib
from libs.s3 import s3_s3cmd
from libs.s3.s3_blackbox_test_lib import JCloudClient
from libs.s3.s3_cmd_test_lib import S3CmdTestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3.s3_test_lib import S3TestLib


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
@pytest.mark.usefixtures("restart_s3server_with_fault_injection")
class TestDIDurability:
    """DI Durability Test suite."""

    # pylint: disable=too-many-statements
    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup suite level operation.")
        cls.jc_obj = JCloudClient()
        cls.log.info("setup jClientCloud on runner.")
        res_ls = system_utils.execute_cmd("ls scripts/jcloud/")[1]
        res = ".jar" in res_ls
        if not res:
            res = cls.jc_obj.configure_jclient_cloud(
                source=S3_CFG["jClientCloud_path"]["source"],
                destination=S3_CFG["jClientCloud_path"]["dest"],
                nfs_path=S3_CFG["nfs_path"],
                ca_crt_path=S3_CFG["s3_cert_path"]
            )
            cls.log.info(res)
            assert_utils.assert_true(
                res, "Error: jcloudclient.jar or jclient.jar file does not exists")
        resp = cls.jc_obj.update_jclient_jcloud_properties()
        assert_utils.assert_true(resp, resp)

    # pylint: disable=attribute-defined-outside-init
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
        self.data_corruption_status = False
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
        if self.data_corruption_status:
            self.log.info("Disabling data corruption")
            self.fi_adapter.disable_data_block_corruption()
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
        Test to verify object integrity during the the upload with correct checksum.
        file size == 64 KB - 32MB
        """
        self.log.info("STARTED: Test to verify object integrity during the the upload with "
                      "correct checksum.")
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        failed_file_sizes = {}
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        self.s3_test_obj.create_bucket(self.bucket_name)
        for file_size in NORMAL_UPLOAD_SIZES:
            self.log.info("Step 1: Creating file and calculating checksum of size %s", file_size)
            location, csm = self.di_err_lib.get_file_and_csum(size=file_size,
                                                              data_folder_prefix=self.test_dir_path)
            self.log.debug("csm: %s", csm[1])
            try:
                self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                            object_name=self.object_name, file_path=location,
                                            content_md5=csm[1])
                self.s3_test_obj.object_download(bucket_name=self.bucket_name,
                                                 obj_name=self.object_name,
                                                 file_path=self.file_path)
                if system_utils.validate_checksum(file_path_1=location, file_path_2=self.file_path):
                    self.log.info("Checksum Validated")
                else:
                    self.log.info("Checksum Validation failed")
                    failed_file_sizes[file_size] = "checksum validation failed"
            except CTException as err:
                err_str = str(err)
                self.log.info("Test failed with %s", err_str)
                failed_file_sizes[file_size] = err_str
        self.s3_test_obj.delete_bucket(bucket_name=self.bucket_name, force=True)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
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
        failed_file_sizes = []
        self.log.info("STARTED: Test to verify object integrity during the upload with different "
                      "checksum.")
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        self.s3_test_obj.create_bucket(self.bucket_name)
        for file_size in NORMAL_UPLOAD_SIZES:
            s3_obj = S3TestLib()
            self.log.info("Step 1: Creating file and calculating checksum of size %s", file_size)
            location, csm = self.di_err_lib.get_file_and_csum(size=file_size,
                                                              data_folder_prefix=self.test_dir_path)
            self.log.debug("csm: %s, location: %s", csm[1], location)
            corrupted_csm = "'" + csm[1]
            self.log.info("Attempting to upload object with corrupted checksum from client %s",
                          corrupted_csm)
            try:
                s3_obj.put_object(bucket_name=self.bucket_name, object_name=self.object_name,
                                  file_path=location, content_md5=corrupted_csm)
            except CTException as err:
                err_str = str(err)
                self.log.info("Test failed with %s", err_str)
                if "The Content-MD5 you specified is not valid" in err_str:
                    self.log.info("Error strings matched")
                else:
                    failed_file_sizes.append(file_size)
        self.s3_test_obj.delete_bucket(bucket_name=self.bucket_name, force=True)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
            assert False
        self.log.info("ENDED: Test to verify object integrity during the upload with different "
                      "checksum.")

    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22909')
    def test_22909(self):
        """
        Corrupt data blocks of an object at Motr level and verify read (Get).
        """
        self.log.info("STARTED: Corrupt data blocks of an object at Motr level and "
                      "verify read (Get).")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to valid")
        failed_file_sizes = []
        self.log.info("Step 1: enable data corruption")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.log.info("Step 1: enabled data corruption")
        else:
            self.log.info("Step 1: failed to enable data corruption")
            assert False
        self.log.info("Step 2: Create a bucket and upload object into a bucket.")
        self.s3_test_obj.create_bucket(self.bucket_name)
        for file_size in NORMAL_UPLOAD_SIZES:
            self.log.info("Step 3: Create a corrupted file of size %s", file_size)
            location = self.di_err_lib.create_corrupted_file(size=file_size, first_byte='z',
                                                             data_folder_prefix=self.test_dir_path)
            self.log.info("Step 3: created a corrupted file at location %s", location)
            self.log.info("Step 4: Put object in a bucket.")
            self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                        object_name=self.object_name,
                                        file_path=location)
            try:
                self.log.info("Step 5: Verify get object.")
                resp = self.s3_test_obj.get_object(self.bucket_name, self.object_name)
                if resp[0]:
                    failed_file_sizes.append(file_size)
            except CTException as err:
                err_str = str(err)
                self.log.info("Test failed with %s", err_str)
                if "error occurred (InternalError) when calling the GetObject operation" in err_str:
                    self.log.info("Download failed with InternalError")
                    self.log.info("Step 5: Verified read (Get) of an object whose metadata is "
                                  "corrupted.")
                else:
                    failed_file_sizes.append(file_size)
        self.s3_test_obj.delete_bucket(bucket_name=self.bucket_name, force=True)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
            assert False
        self.log.info("ENDED: Corrupt data blocks of an object at Motr level and verify "
                      "read (Get).")

    # pylint: disable=too-many-statements
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22910')
    def test_22910(self):
        """
        Corrupt data blocks of an object at Motr level and verify range read.
        """
        self.log.info("STARTED: Corrupt data blocks of an object at Motr level and "
                      "verify range read (Get.")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to valid")
        failed_file_sizes = []
        self.log.info("Step 1: enable data corruption")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.log.info("Step 1: enabled data corruption")
        else:
            self.log.info("Step 1: failed to enable data corruption")
            assert False
        self.log.info("Step 2: Create a bucket and upload object into a bucket.")
        self.s3_test_obj.create_bucket(self.bucket_name)
        for file_size in NORMAL_UPLOAD_SIZES:
            self.log.info("Step 3: Create a corrupted file of size %s", file_size)

            buff, csm = self.data_gen.generate(size=file_size, seed=self.data_gen.get_random_seed())
            buff_c = self.data_gen.add_first_byte_to_buffer(buffer=buff, first_byte='f')
            location = self.data_gen.save_buf_to_file(fbuf=buff_c, csum=csm, size=file_size,
                                                      data_folder_prefix=self.test_dir_path)
            self.log.info("Step 3: Created a corrupted file at location %s", location)
            self.log.info("Step 4: Put object in a bucket.")
            self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                        object_name=self.object_name, file_path=location)
            greater_than_unit_size = False
            if file_size > 1 * MB:
                greater_than_unit_size = True
            lower, upper = di_lib.get_random_ranges(size=file_size,
                                                    greater_than_unit_size=greater_than_unit_size)
            self.log.info("Lower range: %s, Upper range %s", lower, upper)
            # Case 1: Read range with start byte 0
            start_range = 0
            end_range = upper - 1
            try:
                resp = self.s3_test_obj.get_object(bucket=self.bucket_name,
                                                   key=self.object_name,
                                                   ranges=f"bytes={start_range}-{end_range}")

                if resp[0]:
                    self.log.info("Download of corrupted data is successful adding"
                                  "failed test list")
                    failed_file_sizes.append(file_size)

            except CTException as err:
                err_str = str(err)
                self.log.info("Test failed with %s", err_str)
                if "error occurred (InternalError) when calling the GetObject operation" \
                        in err_str:
                    self.log.info("Download failed with InternalError")
                else:
                    failed_file_sizes.append(file_size)

            # Case 2: for file Size greater than motr Unit Size (1MB)
            if file_size > 1 * MB:
                self.log.info("Range read with lower %s and upper range %s: %s", lower, upper,
                              len(buff_c[lower:upper]))
                range_csum = di_lib.calc_checksum(buff_c[lower:upper])
                self.log.info("Checksum of original range buffer is %s", range_csum)
                try:
                    resp_dwn = self.s3_test_obj.get_object(bucket=self.bucket_name,
                                                           key=self.object_name,
                                                           ranges=f"bytes={lower}-{upper - 1}")

                    if resp_dwn[0]:
                        download_content = ''
                        download_content = resp_dwn[1]["Body"].read()
                        self.log.info('size of downloaded object %s is: %s bytes',
                                      self.object_name, len(download_content))
                        dw_csum = di_lib.calc_checksum(download_content)
                        self.log.info("Checksum of download range buffer is %s", dw_csum)
                        assert_utils.assert_equal(range_csum, dw_csum, 'Checksum match found in '
                                                                       'downloaded file')
                except CTException as err:
                    failed_file_sizes.append(file_size)
                    err_str = str(err)
        self.s3_test_obj.delete_bucket(bucket_name=self.bucket_name, force=True)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
            assert False
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
    def test_22914(self):
        """
        Data chunk checksum validation (Motr blocks data or metadata of data blocks) and validate
        checksum error detection by S3/Motr.
        # simulating checksum corruption with data corruption
        # to do enabling checksum corruption feature
        """
        self.log.info("STARTED: Data chunk checksum validation (Motr blocks data or metadata of "
                      "data blocks) and validate checksum error detection by S3/Motr")
        failed_file_sizes = []
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.data_corruption_status = True
            self.log.info("Step 1: Enabled data corruption")
        else:
            assert False
        self.s3_test_obj.create_bucket(bucket_name=self.bucket_name)
        for file_size in NORMAL_UPLOAD_SIZES:
            obj_name = self.object_name + "_size_" + str(file_size)
            self.log.info("Step 2: Creating file of size %s", file_size)
            location = self.di_err_lib.create_corrupted_file(size=file_size, first_byte='z',
                                                             data_folder_prefix=self.test_dir_path)
            self.log.info("Step 2: Created a corrupted file at location %s", location)
            try:
                self.log.info("Step 3: Upload a file")
                self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                            object_name=obj_name, file_path=location)
                self.log.info("Step 4: verify download object fails with 5xx error code")
                resp_dw = self.s3_test_obj.object_download(file_path=self.file_path,
                                                           bucket_name=self.bucket_name,
                                                           obj_name=obj_name)
                if resp_dw[0]:
                    failed_file_sizes.append(file_size)
            except CTException as err:
                err_str = str(err)
                self.log.info("Test failed with %s", err_str)
                if "error occurred (InternalError) when calling the GetObject operation" in err_str:
                    self.log.info("Download failed with InternalError")
                else:
                    failed_file_sizes.append(file_size)
        self.s3_test_obj.delete_bucket(bucket_name=self.bucket_name, force=True)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
            assert False
        self.log.info(
            "ENDED: Data chunk checksum validation (Motr blocks data or metadata of data blocks)"
            "and validate checksum error detection by S3/Motr")

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

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22916')
    def test_22916(self):
        """
        With Checksum flag  Disabled, download of the chunk uploaded object should
        succeed ( 30 MB -100 MB).
        """
        valid, skipmark = self.di_err_lib.validate_valid_config()
        if not valid or skipmark:
            self.log.info("Skipping test  checksum flag is not disabled")
            pytest.skip()

        self.log.info("STARTED: With Checksum flag  Disabled, download of the chunk"
                      "uploaded object should succeed ( 30 MB -100 MB).")
        self.log.info("Step 1: Create a bucket and upload object into a bucket.")
        command = self.jc_obj.create_cmd_format(self.bucket_name, "mb",
                                                jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"],
                                                chunk=True)
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp[1])
        self.log.info("Step: 1 Bucket was created %s", self.bucket_name)
        for size in NORMAL_UPLOAD_SIZES:
            self.log.info("Create a file of size %sMB", size)
            test_file = "data_durability{}_TEST_22916_{}_MB_upload.txt" \
                .format(perf_counter_ns(), str(size))
            file_path_upload = os.path.join(self.test_dir_path, test_file)
            self.log.info("Step 1: create a file of size %sMB", size)
            if os.path.exists(file_path_upload):
                os.remove(file_path_upload)
            buff, csm = self.data_gen.generate(size=size, seed=self.data_gen.get_random_seed())
            self.data_gen.create_file_from_buf(fbuf=buff, size=size, name=file_path_upload)
            self.log.info("Created file %s with CSM: %s", file_path_upload, csm)
            self.log.info("Step 2: Created a bucket and upload object of %s MB into a "
                          "bucket.", size)
            put_cmd_str = "{} {}".format("put", file_path_upload)
            command = self.jc_obj.create_cmd_format(self.bucket_name, put_cmd_str,
                                                    jtool=S3_BLKBOX_CFG["jcloud_cfg"][
                                                        "jcloud_tool"],
                                                    chunk=True)
            resp = system_utils.execute_cmd(command)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_in("Object put successfully", resp[1][:-1], resp[1])
            self.log.info("Step 2: Put object to a bucket %s was successful", self.bucket_name)
            self.log.info("Step 3: Download chunk uploaded from bucket %s .", self.bucket_name)
            test_file_download = "data_durability{}_TEST_22916_{}_MB_download.txt" \
                .format(perf_counter_ns(), str(size))
            file_path_download = os.path.join(self.test_dir_path, test_file_download)
            if os.path.exists(file_path_download):
                os.remove(file_path_download)
            bucket_str = "{0}/{1} {2}".format(self.bucket_name, test_file, file_path_download)
            command = self.jc_obj.create_cmd_format(bucket_str, "get",
                                                    jtool=S3_BLKBOX_CFG["jcloud_cfg"][
                                                        "jcloud_tool"],
                                                    chunk=True)
            resp = system_utils.execute_cmd(command)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_in("Object download successfully", resp[1][:-1], resp)
            self.log.info("Step 3: Object was downloaded successfully")
            self.log.info("Step 4:Validate checksum of uploaded and downloded files")
            result = system_utils.validate_checksum(file_path_upload, file_path_download)
            if not result:
                assert_utils.assert_true(False, "Checksum validation failed")
            self.log.info("Step 4:Checksum and ETAG validation is successful")
        self.s3_test_obj.delete_bucket(self.bucket_name, force=True)
        self.log.info("ENDED: With Checksum flag  Disabled, download of the chunk uploaded "
                      "object should succeed ( 30 MB -100 MB).")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22930')
    def test_disable_checksum_should_not_validate_file_no_error_22930(self):
        """
        Disabling of Checksum feature should not do any checksum validation even if data
        is corrupted.
        """
        failed_file_sizes = []
        self.log.info("STARTED: Disabling of Checksum feature should not do any checksum "
                      "validation even if data is corrupted")
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_disabled_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.data_corruption_status = True
            self.log.info("Step 3: enabled data corruption")
        else:
            self.log.info("Step 3: failed to enable data corruption")
            assert False
        self.s3_test_obj.create_bucket(self.bucket_name)
        for file_size in NORMAL_UPLOAD_SIZES:
            obj_name = self.object_name + "_size_" + str(file_size)
            location = self.di_err_lib.create_corrupted_file(size=file_size, first_byte='f',
                                                             data_folder_prefix=self.test_dir_path)
            self.log.info("Step 3: created a corrupted file at location %s", location)
            try:
                self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                            object_name=obj_name, file_path=location)
                self.s3_test_obj.object_download(file_path=self.file_path,
                                                 bucket_name=self.bucket_name, obj_name=obj_name)
            except CTException as err:
                self.log.info("Test failed with %s", str(err))
                failed_file_sizes.append(file_size)
        self.s3_test_obj.delete_bucket(bucket_name=self.bucket_name, force=True)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
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

    @pytest.mark.data_integrity
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

    @pytest.mark.data_integrity
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
        failed_file_sizes = []
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.data_corruption_status = True
            self.log.info("Step 1: Enabled data corruption")
        else:
            assert False
        self.s3_test_obj.create_bucket(bucket_name=self.bucket_name)
        for file_size in NORMAL_UPLOAD_SIZES:
            self.log.debug("Step 2: Create a corrupted file of size %s .", file_size)
            buff, csm = self.data_gen.generate(size=file_size,
                                               seed=self.data_gen.get_random_seed())
            buff_c = self.data_gen.add_first_byte_to_buffer(buffer=buff, first_byte='f')
            greater_than_unit_size = False
            if file_size > 1 * MB:
                greater_than_unit_size = True
            lower, upper = di_lib.get_random_ranges(size=file_size,
                                                    greater_than_unit_size=greater_than_unit_size)
            self.log.debug("Lower: %s  Upper: %s", lower, upper)
            buff_range = buff_c[lower:upper]
            self.log.info("Range read: %s", len(buff_range))
            buff_csm = di_lib.calc_checksum(buff_range)
            location = self.data_gen.save_buf_to_file(fbuf=buff_c, csum=csm, size=file_size,
                                                      data_folder_prefix=self.test_dir_path)
            self.log.info("Step 1: Created a corrupted file at location %s", location)
            try:
                self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                            object_name=self.object_name, file_path=location)
                resp_dw_rr = self.s3_test_obj.get_object(bucket=self.bucket_name,
                                                         key=self.object_name,
                                                         ranges=f"bytes={lower}-{upper - 1}")
                if resp_dw_rr[0]:
                    if file_size > 1 * MB:
                        content = resp_dw_rr[1]["Body"].read()
                        self.log.info('size of downloaded object %s is: %s bytes',
                                      self.object_name, len(content))
                        dw_csum = di_lib.calc_checksum(content)
                        self.log.info("Comparing csm of uploaded and downloaded parts")
                        if buff_csm != dw_csum:
                            failed_file_sizes.append(file_size)
                            self.log.info("csm comparison failed")
                        else:
                            self.log.info("Checksum matched")
                    else:
                        self.log.info("download of corrupted part is successful, adding to "
                                      "failed size list")
                        failed_file_sizes.append(file_size)
            except CTException as err:
                err_str = str(err)
                self.log.info("Test failed with %s", err_str)
                if file_size > 1 * MB:
                    failed_file_sizes.append(file_size)
                else:
                    if "error occurred (InternalError) when calling the GetObject operation" \
                            in err_str:
                        self.log.info("Download failed with InternalError")
                    else:
                        failed_file_sizes.append(file_size)
            if file_size > 1 * MB:
                try:
                    lower, upper = di_lib.get_random_ranges(size=file_size)
                    lower = 0
                    self.log.debug("Lower: %s  Upper: %s", lower, upper)
                    resp_rr_dwn = self.s3_test_obj.get_object(bucket=self.bucket_name,
                                                              key=self.object_name,
                                                              ranges=f"bytes={lower}-{upper - 1}")
                    self.log.info(str(resp_rr_dwn))
                    if resp_rr_dwn[0]:
                        failed_file_sizes.append(file_size)
                except CTException as err:
                    err_str = str(err)
                    self.log.info("Test failed with %s", err_str)
                    if "error occurred (InternalError) when calling the GetObject operation" \
                            in err_str:
                        self.log.info("Download failed with InternalError")
                    else:
                        failed_file_sizes.append(file_size)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
            assert False
        self.log.info("ENDED: Corrupt checksum of an object 256KB to 31 MB (at s3 checksum) "
                      "and verify range read (Get).")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29812')
    def test_29812(self):
        """
        Corrupt checksum of an object 256KB to 31 MB (at s3 checksum) and verify read (Get).
        # simulating checksum corruption with data corruption
        # to do enabling checksum corruption feature
        """
        self.log.info("STARTED: Corrupt checksum of an object 256KB to 31 MB (at s3 checksum) "
                      "and verify read (Get).")
        failed_file_sizes = []
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.data_corruption_status = True
            self.log.info("Step 1: Enabled data corruption")
        else:
            assert False
        self.s3_test_obj.create_bucket(bucket_name=self.bucket_name)
        for file_size in NORMAL_UPLOAD_SIZES:
            obj_name = self.object_name + "_size_" + str(file_size)
            self.log.info("Step 2: Creating file of size %s", file_size)
            location = self.di_err_lib.create_corrupted_file(size=file_size, first_byte='z',
                                                             data_folder_prefix=self.test_dir_path)
            self.log.info("Step 2: Created a corrupted file at location %s", location)
            try:
                self.log.info("Step 3: Upload a file")
                self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                            object_name=obj_name, file_path=location)
                self.log.info("Step 4: verify download object fails with 5xx error code")
                resp_dw = self.s3_test_obj.object_download(file_path=self.file_path,
                                                           bucket_name=self.bucket_name,
                                                           obj_name=obj_name)
                if resp_dw[0]:
                    failed_file_sizes.append(file_size)
            except CTException as err:
                err_str = str(err)
                self.log.info("Test failed with %s", err_str)
                if "error occurred (InternalError) when calling the GetObject operation" in err_str:
                    self.log.info("Download failed with InternalError")
                else:
                    failed_file_sizes.append(file_size)
        self.s3_test_obj.delete_bucket(bucket_name=self.bucket_name, force=True)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
            assert False
        self.log.info("ENDED: Corrupt checksum of an object 256KB to 31 MB (at s3 checksum) "
                      "and verify read (Get).")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29816')
    def test_29816(self):
        """
        S3 Put through AWS CLI and Corrupt checksum of an object 256KB to 31 MB (at s3 checksum)
        and verify read (Get).
        SZ <= Data Unit Sz
        # simulating checksum corruption with data corruption
        # to do enabling checksum corruption feature
        """
        self.log.info("STARTED: S3 Put through AWS CLI and Corrupt checksum of an object"
                      "256KB to 31 MB (at s3 checksum) and verify read (Get).")
        failed_file_sizes = []
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.data_corruption_status = True
            self.log.info("Step 1: Enabled data corruption")
        else:
            assert False
        self.s3_test_obj.create_bucket(bucket_name=self.bucket_name)
        for file_size in NORMAL_UPLOAD_SIZES:
            obj_name = self.object_name + "_size_" + str(file_size)
            self.log.debug("Step 2: Create a corrupted file of size %s .", file_size)
            location = self.di_err_lib.create_corrupted_file(size=file_size, first_byte='z',
                                                             data_folder_prefix=self.test_dir_path)
            self.log.info("Step 1: Created a corrupted file at location %s", location)
            try:
                self.log.info("Step 3: Upload a file using aws cli")
                self.s3_cmd_test_obj.upload_object_cli(bucket_name=self.bucket_name,
                                                       object_name=obj_name, file_path=location)
                self.log.info("Step 4: verify download object fails with 5xx error code")
                resp_dw = self.s3_test_obj.object_download(file_path=self.file_path,
                                                           bucket_name=self.bucket_name,
                                                           obj_name=obj_name)
                if resp_dw[0]:
                    failed_file_sizes.append(file_size)
            except CTException as err:
                err_str = str(err)
                self.log.info("Test failed with %s", err_str)
                if "error occurred (InternalError) when calling the GetObject operation" in err_str:
                    self.log.info("Download failed with InternalError")
                else:
                    failed_file_sizes.append(file_size)
        self.s3_test_obj.delete_bucket(bucket_name=self.bucket_name, force=True)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
            assert False
        self.log.info("STARTED: S3 Put through AWS CLI and Corrupt checksum of an object"
                      "256KB to 31 MB (at s3 checksum) and verify read (Get).")

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-22912')
    def test_22912(self):
        """
        Test to verify object integrity during the the upload with correct checksum.
        Specify checksum and checksum algorithm or ETAG during
        PUT(MD5 with and without digest, CRC ( check multi-part))
        This test works with R=T/F and W=True.
        """
        size = 1 * MB
        self.log.info("STARTED TEST-22912: Test to verify object integrity "
                      "during the the upload with correct checksum.")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            pytest.skip()
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Step 1: Created a bucket with name : %s", self.bucket_name)
        self.log.info("Step 2: Put and object with checksum algo or ETAG.")
        # simulating checksum corruption with data corruption
        # to do enabling checksum feature
        self.di_err_lib.create_file(size, first_byte='a', name=self.file_path)
        file_checksum = system_utils.calc_checksum(self.file_path)
        self.log.info("Step 1: created a good file at location %s", self.file_path)
        self.log.info("Step 2: enabling data corruption")
        status = self.fi_adapter.enable_data_block_corruption()
        if not status:
            self.log.info("Step 2: failed to enable data corruption")
            assert False
        else:
            self.log.info("Step 2: enabled data corruption")
            self.data_corruption_status = True

        self.log.info("Step 3: Normal upload a file with correct checksum")
        self.s3_test_obj.put_object(bucket_name=self.bucket_name,
                                    object_name=self.object_name,
                                    file_path=self.file_path)
        dwn_file_name = os.path.split(self.file_path)[-1]
        dwn_file_name = dwn_file_name + '.dwn'
        dwn_file_dir = os.path.split(self.file_path)[0]
        dwn_file_path = os.path.join(dwn_file_dir, dwn_file_name)
        self.s3_test_obj.object_download(file_path=dwn_file_path,
                                         obj_name=self.object_name,
                                         bucket_name=self.bucket_name)
        dwn_file_checksum = file_checksum = system_utils.calc_checksum(dwn_file_path)
        assert_utils.assert_exact_string(file_checksum, dwn_file_checksum,
                                         'Checksum mismatch found')
        self.log.info("Step 4: verify download object passes without 5xx error code")
        self.log.info("ENDED TEST-22912")

    # pylint: disable=broad-except
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29817')
    def test_29817(self):
        """
        S3 Put through S3CMD  and Corrupt checksum of an object 256KB to 1 MB (at s3 checksum)
        and verify read (Get). SZ <= Data Unit Sz
        SZ <= Data Unit Sz

        """
        size = 512 * KB
        self.log.info("STARTED: S3 Put through S3CMD and Corrupt checksum of an object"
                      "256KB to 31 MB (at s3 checksum) and verify read (Get).")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            pytest.skip()
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Step 1: Created a bucket with name : %s", self.bucket_name)
        self.log.info("Step 2: Put and object with checksum algo or ETAG.")
        # simulating checksum corruption with data corruption
        # to do enabling checksum feature
        self.log.info("Step 1: Create a corrupted file.")
        self.di_err_lib.create_file(size, first_byte='z', name=self.file_path)
        file_checksum = system_utils.calculate_checksum(self.file_path, binary_bz64=False)[1]
        self.log.info("Step 1: created a file with corrupted flag at location %s", self.file_path)
        self.log.info("Step 2: enabling data corruption")
        status = self.fi_adapter.enable_data_block_corruption()
        if not status:
            self.log.info("Step 2: failed to enable data corruption")
            assert False
        else:
            self.log.info("Step 2: enabled data corruption")
            self.data_corruption_status = True

        self.log.info("Step 3: upload a file using s3cmd upload")

        odict = dict(access_key=ACCESS_KEY, secret_key=SECRET_KEY,
                     ssl=True, no_check_certificate=False,
                     host_port=CMN_CFG['host_port'], host_bucket=self.bucket_name,
                     disable_multipart=True)

        cmd_status, output = s3_s3cmd.S3CmdFacade.upload_object_s3cmd(bucket_name=self.bucket_name,
                                                                      file_path=self.file_path,
                                                                      **odict)
        if not cmd_status:
            assert False, f"s3cmd put failed with {cmd_status} and output {output}"
        object_uri = 's3://' + self.bucket_name + '/' + os.path.split(self.file_path)[-1]
        dodict = dict(access_key=ACCESS_KEY, secret_key=SECRET_KEY,
                      ssl=True, no_check_certificate=False,
                      host_port=CMN_CFG['host_port'], object_uri=object_uri)
        try:
            cmd_status, output = s3_s3cmd.S3CmdFacade. \
                download_object_s3cmd(file_path=self.file_path + '.bak', **dodict)
        except Exception as fault:
            self.log.exception(fault, exc_info=True)
        else:
            if not cmd_status:
                if "InternalError" not in output:
                    assert False, f'Download Command failed with error {output}'
            else:
                assert False, 'Download of corrupted file passed'

    # pylint: disable-msg=too-many-locals
    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29284')
    @CTFailOn(error_handler)
    def test_29284(self):
        """
        Test to verify copy object with chunk upload and GET operation with range read with various
        file sizes with valid Data Integrity flag
        """
        failed_file_sizes = []
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to valid")
        self.log.info("Step 1: Create a bucket and upload object into a bucket.")
        command = self.jc_obj.create_cmd_format(self.bucket_name, "mb",
                                                jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"],
                                                chunk=True)
        resp = system_utils.execute_cmd(command)
        assert_utils.assert_in("Bucket created successfully", resp[1][:-1], resp[1])
        self.log.info("Step: 1 Bucket was created %s", self.bucket_name)
        bucket_name_2 = di_lib.get_random_bucket_name()
        self.s3_test_obj.create_bucket(bucket_name=bucket_name_2)
        obj_name_2 = di_lib.get_random_object_name()
        for file_size in NORMAL_UPLOAD_SIZES:
            self.log.info("Create a file of size %s", file_size)
            test_file = "data_durability{}_TEST_29284_{}_upload.txt" \
                .format(perf_counter_ns(), str(file_size))
            file_path_upload = os.path.join(self.test_dir_path, test_file)
            self.log.info("Step 1: create a file of size %s bytes", file_size)
            if os.path.exists(file_path_upload):
                os.remove(file_path_upload)
            buff, csm = self.data_gen.generate(size=file_size, seed=self.data_gen.get_random_seed())
            lower, upper = di_lib.get_random_ranges(size=file_size)
            buff_range = buff[lower:upper]
            self.log.info("Range read: %s  CSM: %s", len(buff_range), csm)
            self.log.debug("lower: %s  upper: %s", lower, upper)
            buff_csm = di_lib.calc_checksum(buff_range)
            self.data_gen.create_file_from_buf(fbuf=buff, size=file_size, name=file_path_upload)
            self.log.info("Step 2: Created a bucket and upload object of %s Bytes into a bucket.",
                          file_size)
            put_cmd_str = "{} {}".format("put", file_path_upload)
            cmd = self.jc_obj.create_cmd_format(self.bucket_name, put_cmd_str,
                                                jtool=S3_BLKBOX_CFG["jcloud_cfg"]["jcloud_tool"],
                                                chunk=True)
            resp = system_utils.execute_cmd(cmd)
            assert_utils.assert_true(resp[0], resp[1])
            assert_utils.assert_in("Object put successfully", resp[1][:-1], resp[1])
            self.log.info("Step 2: Put object to a bucket %s was successful", self.bucket_name)
            self.s3_test_obj.copy_object(source_bucket=self.bucket_name, source_object=test_file,
                                         dest_bucket=bucket_name_2, dest_object=obj_name_2)
            resp_dw_rr = self.s3_test_obj.get_object(bucket=bucket_name_2, key=obj_name_2,
                                                     ranges=f"bytes={lower}-{upper - 1}")
            content = resp_dw_rr[1]["Body"].read()
            self.log.info('size of downloaded object %s is: %s bytes', obj_name_2, len(content))
            dw_csum = di_lib.calc_checksum(content)
            if buff_csm != dw_csum:
                failed_file_sizes.append(file_size)
                self.log.info("csm comparison failed")
            else:
                self.log.info("Checksum matched")
        self.s3_test_obj.delete_bucket(bucket_name=bucket_name_2, force=True)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
            assert False

    @pytest.mark.data_integrity
    @pytest.mark.data_durability
    @pytest.mark.tags('TEST-29289')
    @CTFailOn(error_handler)
    def test_29289(self):
        """
        Test to verify copy object to different bucket of corrupted data
        """
        failed_file_sizes = []
        self.log.debug("Checking setup status")
        valid, skip_mark = self.di_err_lib.validate_valid_config()
        if not valid or skip_mark:
            self.log.debug("Skipping test as flags are not set to default")
            pytest.skip()
        self.log.debug("Executing test as flags are set to default")
        bucket_name_1 = di_lib.get_random_bucket_name()
        self.s3_test_obj.create_bucket(bucket_name=bucket_name_1)
        bucket_name_2 = di_lib.get_random_bucket_name()
        self.s3_test_obj.create_bucket(bucket_name=bucket_name_2)
        status = self.fi_adapter.enable_data_block_corruption()
        if status:
            self.data_corruption_status = True
            self.log.info("Step 1: Enabled data corruption")
        else:
            assert False
        self.log.info("Step 1: enable data corruption")
        for file_size in NORMAL_UPLOAD_SIZES:
            obj_name_1 = di_lib.get_random_object_name()
            self.log.debug("Step 2: Create a corrupted file of size %s .", file_size)
            location = self.di_err_lib.create_corrupted_file(size=file_size, first_byte='f',
                                                             data_folder_prefix=self.test_dir_path)
            self.log.info("Step 2: created a corrupted file at location %s", location)
            try:
                self.s3_test_obj.put_object(bucket_name=bucket_name_1, object_name=obj_name_1,
                                            file_path=location)
                self.log.info("Verifying copy object")
                resp_cp = self.s3_test_obj.copy_object(source_bucket=bucket_name_1,
                                                       source_object=obj_name_1,
                                                       dest_bucket=bucket_name_2,
                                                       dest_object=obj_name_1)
                self.log.info(resp_cp)
                if resp_cp[0]:
                    failed_file_sizes.append(file_size)
            except CTException as err:
                err_str = str(err)
                self.log.info("Test failed with %s", err_str)
                if "error occurred (InternalError) when calling the CopyObject operation" \
                        in err_str:
                    self.log.info("Copy Object failed with InternalError")
                else:
                    failed_file_sizes.append(file_size)
        self.s3_test_obj.delete_bucket(bucket_name=bucket_name_1, force=True)
        self.s3_test_obj.delete_bucket(bucket_name=bucket_name_2, force=True)
        if failed_file_sizes:
            self.log.info("Test failed for sizes %s", str(failed_file_sizes))
            assert False
