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

"""Multipart Upload test module."""

import os
import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.system_utils import create_file
from commons.utils.system_utils import remove_file
from commons.utils.system_utils import run_local_cmd
from commons.utils.system_utils import path_exists
from commons.utils.system_utils import backup_or_restore_files
from commons.utils.system_utils import split_file
from commons.utils.system_utils import make_dirs
from commons.utils.system_utils import remove_dirs
from commons.utils import assert_utils
from commons.utils.s3_utils import assert_s3_err_msg
from commons.params import TEST_DATA_FOLDER
from commons import error_messages as errmsg
from commons.constants import S3_ENGINE_RGW
from config.s3 import S3_CFG
from config.s3 import MPART_CFG
from libs.s3.s3_test_lib import S3TestLib
from libs.s3.s3_multipart_test_lib import S3MultipartTestLib
from libs.s3 import CMN_CFG


# pylint: disable-msg=too-many-public-methods
class TestMultipartUpload:
    """Multipart Upload Test Suite."""

    @classmethod
    def setup_class(cls):
        """
         Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.s3_test_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.s3_mp_test_obj = S3MultipartTestLib(endpoint_url=S3_CFG["s3_url"])
        cls.aws_config_path = []
        cls.aws_config_path.append(S3_CFG["aws_config_path"])
        cls.actions = ["backup", "restore"]
        cls.test_file = "mp_obj"
        cls.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestMultipartUpload")
        cls.mp_obj_path = os.path.join(cls.test_dir_path, cls.test_file)
        cls.config_backup_path = os.path.join(
            cls.test_dir_path, "config_backup")
        cls.aws_set_cmd = "aws configure set"
        cls.aws_get_cmd = "aws configure get"
        if not path_exists(cls.test_dir_path):
            make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        cls.log.info("STARTED: teardown test suite operations.")
        if path_exists(cls.test_dir_path):
            remove_dirs(cls.test_dir_path)
        cls.log.info("Cleanup test directory: %s", cls.test_dir_path)
        cls.log.info("ENDED: teardown test suite operations.")

    # pylint: disable=attribute-defined-outside-init
    def setup_method(self):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test steps if any.
        """
        self.log.info("STARTED: Setup operations")
        self.random_time = int(time.time())
        self.bucket_name = "mp-bkt-{}".format(self.random_time)
        self.object_name = "mp-obj-{}".format(self.random_time)
        self.log.info(
            "Taking a backup of aws config file located at %s to %s...",
            self.aws_config_path, self.config_backup_path)
        resp = backup_or_restore_files(
            self.actions[0], self.config_backup_path, self.aws_config_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Taken a backup of aws config file located at %s to %s",
            self.aws_config_path, self.config_backup_path)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will clean up resources which are getting created during test case execution.
        This function will delete IAM accounts and users.
        """
        self.log.info("STARTED: Teardown operations")
        resp = self.s3_test_obj.bucket_list()
        pref_list = [
            each_bucket for each_bucket in resp[1] if each_bucket.startswith("mp-bkt")]
        if pref_list:
            resp = self.s3_test_obj.delete_multiple_buckets(pref_list)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Restoring aws config file from %s to %s...",
            self.config_backup_path,
            self.aws_config_path)
        resp = backup_or_restore_files(
            self.actions[1], self.config_backup_path, self.aws_config_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Restored aws config file from %s to %s",
            self.config_backup_path,
            self.aws_config_path)
        self.log.info("Deleting a backup file and directory...")
        if path_exists(self.config_backup_path):
            remove_dirs(self.config_backup_path)
        if path_exists(self.mp_obj_path):
            remove_file(self.mp_obj_path)
        self.log.info("Deleted a backup file and directory")
        self.log.info("ENDED: Teardown operations")

    def create_bucket_to_upload_parts(
            self,
            bucket_name,
            object_name,
            file_size,
            total_parts):
        """Create bucket, initiate multipart upload and upload parts."""
        self.log.info("Creating a bucket with name : %s", bucket_name)
        res = self.s3_test_obj.create_bucket(bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", bucket_name)
        self.log.info("Initiating multipart upload")
        res = self.s3_mp_test_obj.create_multipart_upload(
            bucket_name, object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info(
            "Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Uploading parts into bucket")
        res = self.s3_mp_test_obj.upload_parts(
            mpu_id,
            bucket_name,
            object_name,
            file_size,
            total_parts=total_parts,
            multipart_obj_path=self.mp_obj_path)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]), total_parts, res[1])
        parts = res[1]
        self.log.info("Uploaded parts into bucket: %s", parts)
        return mpu_id, parts

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.sanity
    @pytest.mark.tags('TEST-5588')
    @CTFailOn(error_handler)
    def test_multipart_upload_for_file_2061_2065_2066_2069(self):
        """
        Initiate Multipart upload for file of given size.

        Upload parts into bucket which are prepared in initiate multipart upload stage
        List the parts into bucket
        complete multipart upload.
        """
        self.log.info(
            "Initiate multipart upload, upload parts, list parts and complete multipart upload")
        mp_config = MPART_CFG["test_8660_8664_8665_8668"]
        res = self.create_bucket_to_upload_parts(
            self.bucket_name,
            self.object_name,
            mp_config["file_size"],
            mp_config["total_parts"])
        mpu_id, parts = res
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(
            mpu_id,
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  mp_config["total_parts"], res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Completing multipart upload")
        res = self.s3_mp_test_obj.complete_multipart_upload(
            mpu_id,
            parts,
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_in(self.object_name, res[1], res[1])
        self.log.info("Multipart upload completed")
        self.log.info(
            "Initiate multipart upload, upload parts, list parts and complete multipart upload")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5583')
    @CTFailOn(error_handler)
    def test_abort_multipart_upload_2070(self):
        """Abort Multipart upload."""
        self.log.info("Abort Multipart upload")
        mp_config = MPART_CFG["test_8669"]
        res = self.create_bucket_to_upload_parts(
            self.bucket_name,
            self.object_name,
            mp_config["file_size"],
            mp_config["total_parts"])
        mpu_id, parts = res
        self.log.info("Response: %s, %s", mpu_id, parts)
        self.log.info("Aborting multipart upload")
        res = self.s3_mp_test_obj.abort_multipart_upload(
            self.bucket_name,
            self.object_name,
            mpu_id)
        assert_utils.assert_true(res[0], res[1])
        res = self.s3_mp_test_obj.list_multipart_uploads(
            self.bucket_name)
        assert_utils.assert_not_in(mpu_id, res[1], res[1])
        self.log.info(
            "Aborted multipart upload with upload ID: %s", mpu_id)
        self.log.info("Abort Multipart upload")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5589')
    @CTFailOn(error_handler)
    def test_multipart_upload_file_1gb_to_10gb_2062(self):
        """
        Initiate Multipart upload for file of size of 1GB to 10GB having varying part size.

        i.e.Different part size.
        """
        self.log.info(
            "Initiate Multipart upload for file of size of 1GB to 10GB having varying part size")
        mp_config = MPART_CFG["test_8661"]
        self.log.info(
            "Creating a bucket with name : %s",
            self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info(
            "Created a bucket with name : %s", self.bucket_name)
        sp_file = split_file(
            self.mp_obj_path,
            mp_config["file_size"],
            mp_config["total_parts"],
            random_part_size=True)
        self.log.info("Initiating multipart upload")
        res = self.s3_mp_test_obj.create_multipart_upload(
            self.bucket_name, sp_file[0]["Output"])
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info(
            "Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Clean up splited file parts")
        for file in sp_file:
            remove_file(file["Output"])
        self.log.info("File clean up completed")
        self.log.info(
            "Initiate Multipart upload for file of size of 1GB to 10GB having varying part size")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5590')
    @CTFailOn(error_handler)
    def test_multipart_upliad_large_file_with_metadata_2063(self):
        """Initiate Multipart upload for large file with meta data."""
        self.log.info(
            "Initiate Multipart upload for large file with meta data")
        self.log.info(
            "Creating a bucket with name : %s",
            self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info(
            "Created a bucket with name : %s", self.bucket_name)
        self.log.info("Initiating multipart upload")
        res = self.s3_mp_test_obj.create_multipart_upload(
            self.bucket_name,
            self.object_name,
            "user_id",
            "1111")
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info(
            "Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info(
            "Initiate Multipart upload for large file with meta data")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.regression
    @pytest.mark.tags('TEST-5599')
    @CTFailOn(error_handler)
    def test_verify_max_no_parts_listed_using_part_command_2067(self):
        """Verify max no. of parts being listed by using List part command."""
        self.log.info(
            "Verify max no. of parts being listed by using List part command")
        mp_config = MPART_CFG["test_8666"]
        res = self.create_bucket_to_upload_parts(
            self.bucket_name,
            self.object_name,
            mp_config["file_size"],
            mp_config["total_parts"])
        mpu_id, parts = res
        self.log.info("Response: %s, %s", mpu_id, parts)
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(
            mpu_id,
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  mp_config["max_parts"],
                                  res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info(
            "Verify max no. of parts being listed by using List part command")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5591')
    @CTFailOn(error_handler)
    def test_list_multipart_upload_2068(self):
        """List Multipart uploads."""
        self.log.info("List Multipart uploads")
        self.log.info(
            "Creating a bucket with name : %s",
            self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info(
            "Created a bucket with name : %s", self.bucket_name)
        self.log.info("Initiating multipart upload")
        res = self.s3_mp_test_obj.create_multipart_upload(
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info(
            "Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Listing multipart uploads")
        res = self.s3_mp_test_obj.list_multipart_uploads(self.bucket_name)
        assert_utils.assert_in(mpu_id, str(res[1]), res[1])
        self.log.info(
            "Listed multipart uploads: %s",
            res[1]["Uploads"])
        self.log.info("List Multipart uploads")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.regression
    @pytest.mark.tags('TEST-5597')
    @CTFailOn(error_handler)
    def test_multipart_upload_through_configuration_file_2071(self):
        """Multipart upload through configuration file. (Automatic multipart upload)."""
        self.log.info(
            "Multipart upload through configuration file.(Automatic multipart upload)")
        mp_config = MPART_CFG["test_8670"]
        self.log.info(
            "Configuring AWS S3 CLI custom settings for multipart upload ")
        mp_s3_config_list = list(
            zip(mp_config["s3_configs"], mp_config["multipart_s3_config_values"]))
        default_s3_config_list = list(
            zip(mp_config["s3_configs"], mp_config["default_s3_config_values"]))
        self.log.info("Setting aws s3 configurations for multipart upload")
        for cfg, value in mp_s3_config_list:
            run_local_cmd("{0} {1} {2}".format(self.aws_set_cmd, cfg, value))
            res = run_local_cmd("{0} {1}".format(self.aws_get_cmd, cfg))
            assert_utils.assert_in(value, str(res))
        self.log.info("Applied aws s3 configurations for multipart upload")
        self.log.info(
            "Creating a bucket with name : %s",
            self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info(
            "Created a bucket with name : %s",
            self.bucket_name)
        self.log.info("Creating and uploading a file:%s ",
                      self.mp_obj_path)
        res = create_file(
            self.mp_obj_path,
            mp_config["file_size"])
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_true(
            path_exists(
                self.mp_obj_path))
        res = self.s3_test_obj.object_upload(
            self.bucket_name,
            self.object_name,
            self.mp_obj_path)
        assert_utils.assert_true(res[0], res[1])
        self.log.info(
            "Uploaded an object %s to the bucket %s",
            self.object_name,
            self.bucket_name)
        self.log.info("Setting aws s3 configurations to default")
        for cfg, value in default_s3_config_list:
            run_local_cmd("{0} {1} {2}".format(self.aws_set_cmd, cfg, value))
            res = run_local_cmd("{0} {1}".format(self.aws_get_cmd, cfg))
            assert_utils.assert_in(value, str(res))
        self.log.info("Applied default aws s3 configurations")
        self.log.info(
            "Multipart upload through configuration file.(Automatic multipart upload)")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5584')
    @CTFailOn(error_handler)
    def test_abort_multipart_upload_from_client2_started_from_client1_2073(
            self):
        """Abort multipart upload from client 2 if upload has started from client 1."""
        self.log.info(
            "Abort multipart upload from client 2 if upload has started from client 1")
        mp_config = MPART_CFG["test_8672"]
        self.log.info("Creating another s3_client instance for client 2")
        s3_mp_test_obj_client2 = S3MultipartTestLib()
        self.log.info("Created another s3_client instance for client 2")
        res = self.create_bucket_to_upload_parts(
            self.bucket_name,
            self.object_name,
            mp_config["file_size"],
            mp_config["total_parts"])
        mpu_id, parts = res
        self.log.info("response: %s, %s", mpu_id, parts)
        self.log.info("Aborting multipart upload")
        res = s3_mp_test_obj_client2.abort_multipart_upload(
            self.bucket_name,
            self.object_name,
            mpu_id)
        assert_utils.assert_true(res[0], res[1])
        self.log.info(
            "Aborted multipart upload with upload ID: %s", mpu_id)
        self.log.info(
            "Abort multipart upload from client 2 if upload has started from client 1")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5598')
    @CTFailOn(error_handler)
    def test_large_object_multipart_upload_2075(self):
        """
        Large object multipart upload.

        Start a large object multipart upload and check if the parts can be seen
        from other client and if they can be accessed.
        """
        self.log.info(
            "start a large object multipart upload and check if the parts can be"
            " seen from other client and if they can be accessed")
        mp_config = MPART_CFG["test_8674"]
        self.log.info("Creating another s3_client instance for client 2")
        s3_mp_test_obj_client2 = S3MultipartTestLib()
        self.log.info("Created another s3_client instance for client 2")
        res = self.create_bucket_to_upload_parts(
            self.bucket_name,
            self.object_name,
            mp_config["file_size"],
            mp_config["total_parts"])
        mpu_id, parts = res
        self.log.info("response: %s, %s", mpu_id, parts)
        self.log.info("Listing multipart uploads")
        res = s3_mp_test_obj_client2.list_multipart_uploads(
            self.bucket_name)
        assert_utils.assert_in(mpu_id, str(res[1]), res[1])
        self.log.info(
            "Listed multipart uploads: %s",
            res[1]["Uploads"])
        self.log.info(
            "start a large object multipart upload and check if the parts can be"
            " seen from other client and if they can be accessed")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5586')
    @CTFailOn(error_handler)
    def test_multiprt_upload_having_more_than_10000_parts_2294(self):
        """Create multipart upload having more than 10,000 parts."""
        self.log.info("Create multipart upload having more than 10,000 parts")
        mp_config = MPART_CFG["test_8922"]
        self.log.info("Creating a bucket with name : %s", self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info("Created a bucket with name : %s", self.bucket_name)
        self.log.info("Initiating multipart upload")
        res = self.s3_mp_test_obj.create_multipart_upload(
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info("Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info("Uploading parts into bucket")
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            resp = self.s3_mp_test_obj.upload_parts(
                mpu_id,
                self.bucket_name,
                self.object_name,
                mp_config["file_size"],
                total_parts=mp_config["total_parts"],
                multipart_obj_path=self.mp_obj_path)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Uploaded more than 10000 parts")
        else:
            try:
                resp = self.s3_mp_test_obj.upload_parts(
                    mpu_id,
                    self.bucket_name,
                    self.object_name,
                    mp_config["file_size"],
                    total_parts=mp_config["total_parts"],
                    multipart_obj_path=self.mp_obj_path)
                assert_utils.assert_false(resp[0], resp[1])
            except CTException as error:
                self.log.error(error.message)
                assert_utils.assert_in(errmsg.S3_MULTIPART_INVALID_PART_ERR, error.message,
                                       error.message)
            self.log.info("Verified that cannot upload more than 10000 parts")
        self.log.info("Create multipart upload having more than 10,000 parts")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5594')
    @CTFailOn(error_handler)
    def test_multipart_upload_all_parts_less_than_5mb_2296(self):
        """Multipart upload - create all parts less than 5 MB size, last part can be > 5 MB."""
        self.log.info(
            "Multipart upload - create all parts less than 5 MB size, last part can be > 5 MB")
        mp_config = MPART_CFG["test_8924"]
        res = self.create_bucket_to_upload_parts(
            self.bucket_name,
            self.object_name,
            mp_config["file_size"],
            mp_config["total_parts"])
        mpu_id, parts = res
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(
            mpu_id,
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(len(res[1]["Parts"]),
                                  mp_config["total_parts"],
                                  res[1])
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Completing multipart upload")
        try:
            resp = self.s3_mp_test_obj.complete_multipart_upload(
                mpu_id,
                parts,
                self.bucket_name,
                self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error.message)
            assert_utils.assert_in(errmsg.S3_MULTIPART_LIST_PART_LESS_ERR, error.message,
                                   error.message)
        res = self.s3_test_obj.object_list(self.bucket_name)
        assert_utils.assert_not_in(self.object_name, res[1], res[1])
        self.log.info("Cannot complete multipart upload")
        self.log.info(
            "Multipart upload - create all parts less than 5 MB size, "
            "last part can be > 5 MB")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5596')
    @CTFailOn(error_handler)
    def test_multipart_upload_part_number_should_be_in_range_1_to_10k_2295(
            self):
        """Multipart Upload Part numbers should be in range of 1 to 10,000."""
        self.log.info("Multipart Upload Part numbers should be in range of 1 to 10,000")
        mp_config = MPART_CFG["test_8923"]
        res = self.create_bucket_to_upload_parts(
            self.bucket_name,
            self.object_name,
            mp_config["file_size"],
            mp_config["total_parts"])
        mpu_id, _ = res
        self.log.info("Multipart Upload Part numbers should be in range of 1 to 10,000")
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(
            mpu_id,
            self.bucket_name,
            self.object_name)
        part_list = res[1]["Parts"]
        assert_utils.assert_equal(
            len(part_list), mp_config["max_list_parts"],
            "Listed {0} parts, Expected {1} parts".format(
                len(part_list), mp_config["max_list_parts"]))
        max_part_number = mp_config["total_parts"]
        part_numbers = list(range(1, max_part_number + 1))
        for part in part_list:
            assert_utils.assert_in(
                part["PartNumber"], part_numbers,
                f"Below listed part is outside of range 1 to {max_part_number}\n {part}")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5595')
    @CTFailOn(error_handler)
    def test_multipart_upload_few_part_more_than_5gb_2297(self):
        """Multipart upload - create few parts more than 5 GB size."""
        self.log.info("Multipart upload - create few parts more than 5 GB size")
        mp_config = MPART_CFG["test_2297"]
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
            assert_utils.assert_in(errmsg.S3_MULTIPART_LIST_PART_LARGE_ERR, error.message,
                                   error.message)
        self.log.info("Listing parts of multipart upload")
        res = self.s3_mp_test_obj.list_parts(mpu_id, self.bucket_name, self.object_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_not_equal(len(res[1].get("Parts", [])), mp_config["total_parts"], res)
        self.log.info("Listed parts of multipart upload: %s", res[1])
        self.log.info("Multipart upload - create few parts more than 5 GB size")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5587')
    @CTFailOn(error_handler)
    def test_create_upto_1k_multipart_uploads_2298(self):
        """Create up to 1000 Multipart uploads."""
        self.log.info("Create up to 1000 Multipart uploads")
        mp_config = MPART_CFG["test_8926"]
        self.log.info(
            "Creating a bucket with name : %s",
            self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info(
            "Created a bucket with name : %s",
            self.bucket_name)
        obj_dict = dict()
        for count in range(mp_config["total_mp_uploads"]):
            object_name = "{0}-{1}".format(self.object_name, count)
            self.log.info("Initiating multipart upload")
            res = self.s3_mp_test_obj.create_multipart_upload(
                self.bucket_name,
                object_name)
            assert_utils.assert_true(res[0], res[1])
            mpu_id = res[1]["UploadId"]
            self.log.info(
                "Multipart Upload initiated with mpu_id %s", mpu_id)
            self.log.info("Uploading parts into bucket")
            res = self.s3_mp_test_obj.upload_parts(
                mpu_id,
                self.bucket_name,
                object_name,
                mp_config["file_size"],
                total_parts=mp_config["total_parts"],
                multipart_obj_path=self.mp_obj_path)
            assert_utils.assert_true(res[0], res[1])
            parts = res[1]
            self.log.info("Uploaded parts into bucket: %s", parts)
            self.log.info("Listing parts of multipart upload")
            res = self.s3_mp_test_obj.list_parts(
                mpu_id,
                self.bucket_name,
                object_name)
            assert_utils.assert_true(res[0], res[1])
            assert_utils.assert_equal(len(res[1]["Parts"]),
                                      mp_config["total_parts"], res[1])
            self.log.info(
                "Listed parts of multipart upload: %s",
                res[1])
            obj_dict[object_name] = [mpu_id, parts]
        self.log.info("Completing multipart uploads")
        for obj in obj_dict:
            res = self.s3_mp_test_obj.complete_multipart_upload(
                obj_dict[obj][0],
                obj_dict[obj][1],
                self.bucket_name,
                obj)
            assert_utils.assert_true(res[0], res[1])
            res = self.s3_test_obj.object_list(self.bucket_name)
            assert_utils.assert_in(obj, res[1], res[1])
        self.log.info("Multipart upload completed")
        self.log.info("Create up to 1000 Multipart uploads")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.regression
    @pytest.mark.tags('TEST-5585')
    @CTFailOn(error_handler)
    def test_create_more_than_1k_multipart_uploads_2299(self):
        """Create more than 1000 Multipart uploads."""
        self.log.info("Create more than 1000 Multipart uploads")
        mp_config = MPART_CFG["test_8927"]
        self.log.info(
            "Creating a bucket with name : %s",
            self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info(
            "Created a bucket with name : %s",
            self.bucket_name)
        obj_dict = dict()
        for count in range(mp_config["total_mp_uploads"]):
            object_name = "{0}-{1}".format(self.object_name, count)
            self.log.info("Initiating multipart upload")
            res = self.s3_mp_test_obj.create_multipart_upload(
                self.bucket_name,
                object_name)
            assert_utils.assert_true(res[0], res[1])
            mpu_id = res[1]["UploadId"]
            self.log.info(
                "Multipart Upload initiated with mpu_id %s", mpu_id)
            self.log.info("Uploading parts into bucket")
            res = self.s3_mp_test_obj.upload_parts(
                mpu_id,
                self.bucket_name,
                object_name,
                mp_config["file_size"],
                total_parts=mp_config["total_parts"],
                multipart_obj_path=self.mp_obj_path)
            assert_utils.assert_true(res[0], res[1])
            parts = res[1]
            self.log.info("Uploaded parts into bucket: %s", parts)
            self.log.info("Listing parts of multipart upload")
            res = self.s3_mp_test_obj.list_parts(
                mpu_id,
                self.bucket_name,
                object_name)
            assert_utils.assert_true(res[0], res[1])
            assert_utils.assert_equal(len(res[1]["Parts"]),
                                      mp_config["total_parts"], res[1])
            self.log.info(
                "Listed parts of multipart upload: %s",
                res[1])
            obj_dict[object_name] = [mpu_id, parts]
            self.log.info("Listing multipart uploads")
        res = self.s3_mp_test_obj.list_multipart_uploads(self.bucket_name)
        assert_utils.assert_equal(
            mp_config["max_uploads"], len(
                res[1]['Uploads']), res[1])
        self.log.info(
            "Listed multipart uploads: %s",
            res[1]["Uploads"])
        self.log.info("Cannot list more than 1000 multipart uploads")
        self.log.info("Create more than 1000 Multipart uploads")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5593')
    @CTFailOn(error_handler)
    def test_multipart_upload_varying_request_numbers_max_concurrent_requests_2300(
            self):
        """Multipart upload - by varying request numbers max_concurrent_requests."""
        self.log.info(
            "Multipart upload - by varying request numbers max_concurrent_requests")
        mp_config = MPART_CFG["test_8928"]
        self.log.info(
            "Configuring AWS S3 CLI custom settings for multipart upload ")
        self.log.info("Setting max_concurrent_requests for multipart upload")
        run_local_cmd(
            "{0} {1} {2}".format(
                self.aws_set_cmd,
                mp_config["s3_configs"],
                mp_config["max_concurrent_requests"]))
        res = run_local_cmd(
            "{0} {1}".format(
                self.aws_get_cmd,
                mp_config["s3_configs"]))
        assert_utils.assert_in(mp_config["max_concurrent_requests"], str(res))
        self.log.info("Applied max_concurrent_requests for multipart upload")
        self.log.info(
            "Creating a bucket with name : %s",
            self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info(
            "Created a bucket with name : %s",
            self.bucket_name)
        self.log.info("Creating and uploading a file:%s ",
                      self.mp_obj_path)
        res = create_file(
            self.mp_obj_path,
            mp_config["file_size"])
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_true(
            path_exists(
                self.mp_obj_path))
        res = self.s3_test_obj.object_upload(
            self.bucket_name,
            self.object_name,
            self.mp_obj_path)
        assert_utils.assert_true(res[0], res[1])
        self.log.info(
            "Uploaded an object%s to the bucket%s",
            self.object_name,
            self.bucket_name)
        self.log.info("Setting max_concurrent_requests to default")
        run_local_cmd(
            "{0} {1} {2}".format(
                self.aws_set_cmd,
                mp_config["s3_configs"],
                mp_config["default_max_concurrent_requests"]))
        res = run_local_cmd(
            "{0} {1}".format(
                self.aws_get_cmd,
                mp_config["s3_configs"]))
        assert_utils.assert_in(
            mp_config["default_max_concurrent_requests"], str(res))
        self.log.info("Applied default max_concurrent_requests")
        self.log.info(
            "Multipart upload - by varying request numbers max_concurrent_requests")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-5592')
    @CTFailOn(error_handler)
    def test_multipart_upload_varying_multipart_threshold_2301(self):
        """Multipart upload - by varying multipart_threshold."""
        self.log.info("Multipart upload - by varying multipart_threshold")
        mp_config = MPART_CFG["test_8929"]
        self.log.info(
            "Configuring AWS S3 CLI custom settings for multipart upload ")
        self.log.info("Setting multipart_threshold for multipart upload")
        run_local_cmd(
            "{0} {1} {2}".format(
                self.aws_set_cmd,
                mp_config["s3_configs"],
                mp_config["multipart_threshold"]))
        res = run_local_cmd(
            "{0} {1}".format(
                self.aws_get_cmd,
                mp_config["s3_configs"]))
        assert_utils.assert_in(mp_config["multipart_threshold"], str(res))
        self.log.info("Applied multipart_threshold for multipart upload")
        self.log.info(
            "Creating a bucket with name : %s",
            self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info(
            "Created a bucket with name : %s",
            self.bucket_name)
        self.log.info("Creating and uploading a file:%s ",
                      self.mp_obj_path)
        res = create_file(
            self.mp_obj_path,
            mp_config["file_size"])
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_true(
            path_exists(
                self.mp_obj_path))
        res = self.s3_test_obj.object_upload(
            self.bucket_name,
            self.object_name,
            self.mp_obj_path)
        assert_utils.assert_true(res[0], res[1])
        self.log.info(
            "Uploaded an object %s to the bucket %s",
            self.object_name,
            self.bucket_name)
        self.log.info("Setting multipart_threshold to default")
        run_local_cmd(
            "{0} {1} {2}".format(
                self.aws_set_cmd,
                mp_config["s3_configs"],
                mp_config["default_multipart_threshold"]))
        res = run_local_cmd(
            "{0} {1}".format(
                self.aws_get_cmd,
                mp_config["s3_configs"]))
        assert_utils.assert_in(
            mp_config["default_multipart_threshold"], str(res), res)
        self.log.info("Applied default multipart_threshold")
        self.log.info("Multipart upload - by varying multipart_threshold")

    @pytest.mark.s3_ops
    @pytest.mark.s3_multipart_ops
    @pytest.mark.tags('TEST-8723')
    @CTFailOn(error_handler)
    def test_multipart_upload_with_invalid_json_input_631(self):
        """Multipart upload with invalid json input."""
        self.log.info("STARTED: Test Multipart upload with invalid json input")
        mp_config = MPART_CFG["test_631"]
        self.log.info(
            "Step 1: Creating a bucket with name : %s",
            self.bucket_name)
        res = self.s3_test_obj.create_bucket(self.bucket_name)
        assert_utils.assert_true(res[0], res[1])
        assert_utils.assert_equal(res[1], self.bucket_name, res[1])
        self.log.info(
            "Step 1: Created a bucket with name : %s",
            self.bucket_name)
        self.log.info("Step 2: Initiating multipart upload")
        res = self.s3_mp_test_obj.create_multipart_upload(
            self.bucket_name,
            self.object_name)
        assert_utils.assert_true(res[0], res[1])
        mpu_id = res[1]["UploadId"]
        self.log.info(
            "Step 2: Multipart Upload initiated with mpu_id %s", mpu_id)
        self.log.info(
            "Step 3: Create wrong json for input as multipart-upload")
        wrong_json = mp_config["wrong_json"]
        self.log.info(
            "Step 3: Created wrong json for input as multipart-upload %s",
            wrong_json)
        self.log.info(
            "Step 4: Complete the multipart with input of wrong json/etag")
        try:
            resp = self.s3_mp_test_obj.complete_multipart_upload(
                mpu_id,
                wrong_json,
                self.bucket_name,
                self.object_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error(error)
            assert_s3_err_msg(errmsg.RGW_ERR_WRONG_JSON, errmsg.CORTX_ERR_WRONG_JSON,
                              CMN_CFG["s3_engine"], error)
            self.log.info(
                "Step 4: Failed to complete the multipart with input of wrong json/etag")
        self.log.info("ENDED: Test Multipart upload with invalid json input")
