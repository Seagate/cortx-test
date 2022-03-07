#!/usr/bin/python
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
#
"""Test suite for s3 fs operations."""

import time
import logging
import pytest

from commons.constants import const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import system_utils
from commons.utils.system_utils import execute_cmd
from commons.utils.assert_utils import assert_true, assert_in
from config.s3 import S3_CFG
from config.s3 import S3_BLKBOX_CFG as S3FS_CNF
from libs.s3.s3_test_lib import S3TestLib
from libs.s3 import ACCESS_KEY, SECRET_KEY
from libs.s3.s3_blackbox_test_lib import S3FS


class TestS3fs:
    """Blackbox s3fs testsuite."""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup suite level operation.")
        cls.log.info("Check, configure and update s3fs config.")
        resp = system_utils.is_rpm_installed(const.S3FS)
        assert_true(resp[0], resp[1])
        cls.s3fs_obj = S3FS(access=ACCESS_KEY, secret=SECRET_KEY)
        cls.s3_test_obj = S3TestLib(access_key=ACCESS_KEY, secret_key=SECRET_KEY)
        res = execute_cmd(f"cat {S3_CFG['s3fs_path']}")
        if f"{ACCESS_KEY}:{SECRET_KEY}" != res[1]:
            cls.log.info("Setting access and secret key for s3fs.")
            resp = cls.s3fs_obj.configure_s3fs(ACCESS_KEY, SECRET_KEY)
            assert_true(resp, f"Failed to update keys in {S3_CFG['s3fs_path']}")
        resp = system_utils.path_exists(S3_CFG['s3fs_path'])
        assert_true(resp, "config path not exists: {}".format(S3_CFG['s3fs_path']))
        cls.log.info("ENDED: Setup suite level operation.")

    # pylint: disable=attribute-defined-outside-init
    def setup_method(self):
        """
        Function will be invoked before each test case execution.

        It will perform prerequisite test steps if any
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: setup test operations.")
        self.s3fs_cfg = S3FS_CNF["s3fs_cfg"]
        self.bucket_name = "s3fs-bkt-{}".format(time.perf_counter_ns())
        self.log.info("Bucket name: %s", self.bucket_name)
        self.s3fs_bucket_list = list()
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after each test case.

        It will perform all cleanup operations.
        This function will unmount the directories and delete it.
        It will delete buckets and objects uploaded to that bucket.
        It will also delete the local files.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info("unmount the bucket directory and remove it")
        dir_to_del = "".join([self.s3fs_cfg["dir_to_rm"], "*"])
        command = " ".join([self.s3fs_cfg["unmount_cmd"], dir_to_del])
        resp = execute_cmd(command)
        self.log.info(resp)
        command = " ".join([self.s3fs_cfg["rm_file_cmd"], dir_to_del])
        resp = execute_cmd(command)
        self.log.info(resp)
        self.log.info("unmounted the bucket directory and remove it")
        if self.s3fs_bucket_list:
            self.s3_test_obj.delete_multiple_buckets(self.s3fs_bucket_list)
            self.log.info("Removed all buckets: %s", self.s3fs_bucket_list)
        self.log.info("ENDED: Teardown Operations")

    def create_and_mount_bucket(self):
        """
        Method helps to create bucket and mount bucket using s3fs client.

        :return tuple: bucket_name & dir_name
        """
        bucket_name = self.s3fs_cfg["bucket_name"].format(time.perf_counter_ns())
        bucket_name, dir_name = self.s3fs_obj.create_and_mount_bucket(bucket_name)
        return bucket_name, dir_name

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7928")
    @CTFailOn(error_handler)
    def test_mount_bucket_2359(self):
        """Mount bucket using s3fs client."""
        self.log.info("STARTED: mount bucket using s3fs client")
        bucket_name, dir_name = self.create_and_mount_bucket()
        self.s3fs_bucket_list.append(bucket_name)
        self.log.info("ENDED: mount bucket using s3fs client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7929")
    @CTFailOn(error_handler)
    def test_umount_bucket_2360(self):
        """Umount bucket directory using s3fs client."""
        self.log.info("STARTED: umount bucket directory using s3fs client")
        bucket_name, dir_name = self.create_and_mount_bucket()
        self.log.info("Created Bucket Name is %s", bucket_name)
        self.s3fs_bucket_list.append(bucket_name)
        self.log.info("STEP: 1 umount the bucket directory")
        command = " ".join([self.s3fs_cfg["unmount_cmd"], dir_name])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 umounted the bucket directory")
        self.log.info("STEP: 2 List the mount directory present or not")
        resp = execute_cmd(self.s3fs_cfg["cmd_check_mount"].format(dir_name))
        assert_true(dir_name not in str(resp[1]), resp[1])
        self.log.info("STEP: 2 Listed the mount directory present or not")
        self.log.info("ENDED: umount bucket directory using s3fs client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7930")
    @CTFailOn(error_handler)
    def test_list_object_mount_bucket_2361(self):
        """List objects on Mount directory with mounted bucket using s3fs client."""
        self.log.info(
            "STARTED: list objects on Mount directory with mounted bucket using s3fs client")
        bucket_name, dir_name = self.create_and_mount_bucket()
        self.log.info("STEP: 1 create a file on mount directory")
        self.s3fs_bucket_list.append(bucket_name)
        file_name = self.s3fs_cfg["file_name"].format(int(time.perf_counter_ns()))
        file_pth = "/".join([dir_name, file_name])
        command = " ".join([self.s3fs_cfg["create_file_cmd"], file_pth])
        execute_cmd(command)
        self.log.info("STEP: 1 created a file on mount directory")
        self.log.info("STEP: 2 List the mount directory files and bucket files")
        command = " ".join([self.s3fs_cfg["ls_mnt_dir_cmd"], dir_name])
        resp = execute_cmd(command)
        assert_in(file_name, str(resp[1]), resp[1])
        resp = self.s3_test_obj.object_list(bucket_name)
        assert_in(file_name, str(resp[1]), resp[1])
        self.log.info("STEP: 2 Listed the mount directory files and bucket files")
        self.log.info(
            "ENDED: list objects on Mount directory with mounted bucket using s3fs client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7931")
    @CTFailOn(error_handler)
    def test_list_bucket_umount_dir_2362(self):
        """List objects where directory was umount and check bucket objects using s3fs client."""
        self.log.info(
            "STARTED: list objects where directory was umount and "
            "check bucket objects using s3fs client")
        bucket_name, dir_name = self.create_and_mount_bucket()
        self.log.info("Create a file on mount directory")
        self.s3fs_bucket_list.append(bucket_name)
        file_name = self.s3fs_cfg["file_name"].format(int(time.perf_counter_ns()))
        file_pth = "/".join([dir_name, file_name])
        command = " ".join([self.s3fs_cfg["create_file_cmd"], file_pth])
        execute_cmd(command)
        self.log.info("Created a file on mount directory")
        self.log.info("STEP: 1 umount the bucket directory")
        command = " ".join([self.s3fs_cfg["unmount_cmd"], dir_name])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        self.log.info("STEP: 1 umounted the bucket directory")
        self.log.info("STEP: 2 List the bucket files and not mount directory files")
        command = " ".join([self.s3fs_cfg["ls_mnt_dir_cmd"], dir_name])
        resp = execute_cmd(command)
        assert_true(file_name not in str(resp[1]), resp[1])
        resp = self.s3_test_obj.object_list(bucket_name)
        assert_in(file_name, str(resp[1]), resp[1])
        self.log.info("STEP: 2 Listed the bucket files and not mount directory files")
        self.log.info(
            "ENDED: list objects where directory was umount and "
            "check bucket objects using s3fs client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7932")
    @CTFailOn(error_handler)
    def test_delete_file_check_obj_2363(self):
        """Delete File from Mount dir and check object is present in bucket using s3fs client."""
        self.log.info(
            "STARTED: Delete File from Mount directory and "
            "check object is present in bucket using s3fs client")
        bucket_name, dir_name = self.create_and_mount_bucket()
        self.log.info("Create a file on mount directory")
        self.s3fs_bucket_list.append(bucket_name)
        file_name = self.s3fs_cfg["file_name"].format(int(time.perf_counter_ns()))
        file_pth = "/".join([dir_name, file_name])
        command = " ".join([self.s3fs_cfg["create_file_cmd"], file_pth])
        execute_cmd(command)
        self.log.info("Created a file on mount directory")
        self.log.info("STEP: 1 List the mount directory files and bucket files")
        command = " ".join([self.s3fs_cfg["ls_mnt_dir_cmd"], dir_name])
        resp = execute_cmd(command)
        assert_in(file_name, str(resp[1]), resp[1])
        resp = self.s3_test_obj.object_list(bucket_name)
        assert_in(file_name, str(resp[1]), resp[1])
        self.log.info("STEP: 1 Listed the mount directory files and bucket files")
        self.log.info("STEP: 2 Remove file from mount directory")
        command = " ".join([self.s3fs_cfg["rm_file_cmd"], file_pth])
        resp = execute_cmd(command)
        assert_true(resp[0], resp[1])
        self.log.info("STEP: 2 Removed file from mount directory")
        self.log.info(
            "STEP: 3 List bucket and check deleted file should not be visible in bucket")
        resp = self.s3_test_obj.object_list(bucket_name)
        assert_true(file_name not in str(resp[1]), resp[1])
        self.log.info(
            "STEP: 3 Listed bucket and check deleted file should not be visible in bucket")
        self.log.info(
            "ENDED: Delete File from Mount directory and "
            "check object is present in bucket using s3fs client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7935")
    @CTFailOn(error_handler)
    def test_create_subdir_2367(self):
        """Create sub directory under mount directory and list the bucket."""
        self.log.info(
            "STARTED: Create sub directory under mount directory and list the bucket")
        bucket_name, dir_name = self.create_and_mount_bucket()
        self.log.info("STEP: 1 Create sub directory")
        self.s3fs_bucket_list.append(bucket_name)
        new_dir_name = self.s3fs_cfg["new_dir_name"].format(int(time.perf_counter_ns()))
        file_pth = "/".join([dir_name, new_dir_name])
        command = " ".join([self.s3fs_cfg["make_dir_cmd"], file_pth])
        execute_cmd(command)
        self.log.info("STEP: 1 Created sub directory")
        self.log.info("STEP: 2 List sub directory and bucket files")
        command = " ".join([self.s3fs_cfg["ls_mnt_dir_cmd"], dir_name])
        resp = execute_cmd(command)
        assert_in(new_dir_name, str(resp[1]), resp[1])
        resp = self.s3_test_obj.object_list(bucket_name)
        assert_in(new_dir_name, str(resp[1]), resp[1])
        self.log.info("STEP: 2 Listed sub directory and bucket files")
        self.log.info(
            "ENDED: Create sub directory under mount directory and list the bucket")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7933")
    @CTFailOn(error_handler)
    def test_upload_large_file_2364(self):
        """Upload large file on mount dir and check its present in bucket using s3fs client."""
        self.log.info(
            "STARTED: upload large file on mount directory and "
            "check its present in bucket using s3fs client")
        bucket_name, dir_name = self.create_and_mount_bucket()
        self.s3fs_bucket_list.append(bucket_name)
        self.log.info("STEP: 1 upload large file")
        file_name = self.s3fs_cfg["file_name"].format(int(time.perf_counter_ns()))
        file_pth = "/".join([dir_name, file_name])
        command = " ".join([self.s3fs_cfg["dd_cmd"],
                            self.s3fs_cfg["input_file"].format(file_pth),
                            self.s3fs_cfg["count"].format(1024),
                            self.s3fs_cfg["block_size"].format(5242880)])
        execute_cmd(command)
        self.log.info("STEP: 1 uploaded large file")
        self.log.info("STEP: 2 List the mount directory files and bucket files")
        command = " ".join([self.s3fs_cfg["ls_mnt_dir_cmd"], dir_name])
        resp = execute_cmd(command)
        assert_in(file_name, str(resp[1]), resp[1])
        resp = self.s3_test_obj.object_list(bucket_name)
        assert_in(file_name, str(resp[1]), resp[1])
        self.log.info("STEP: 2 Listed the mount directory files and bucket files")
        self.log.info(
            "ENDED: upload large file on mount directory and "
            "check its present in bucket using s3fs client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7934")
    @CTFailOn(error_handler)
    def test_upload_file_2365(self):
        """Upload file in mount directory and check that object is present in bucket."""
        self.log.info(
            "STARTED: upload file in mount directory and check that object is present in bucket")
        bucket_name, dir_name = self.create_and_mount_bucket()
        self.s3fs_bucket_list.append(bucket_name)
        self.log.info("STEP: 1 create a file on mount directory")
        file_name = self.s3fs_cfg["file_name"].format(int(time.perf_counter_ns()))
        file_pth = "/".join([dir_name, file_name])
        command = " ".join([self.s3fs_cfg["create_file_cmd"], file_pth])
        execute_cmd(command)
        self.log.info("STEP: 1 created a file on mount directory")
        self.log.info("STEP: 2 List the mount directory files and bucket files")
        command = " ".join([self.s3fs_cfg["ls_mnt_dir_cmd"], dir_name])
        resp = execute_cmd(command)
        assert_in(file_name, str(resp[1]), resp[1])
        resp = self.s3_test_obj.object_list(bucket_name)
        assert_in(file_name, str(resp[1]), resp[1])
        self.log.info("STEP: 2 Listed the mount directory files and bucket files")
        self.log.info(
            "ENDED: upload file in mount directory and check that object is present in bucket")
