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
Note:
The pre-requisite of this testfile require the configuration changes in .s3cfg file.
Take the secret-key and access-key from "/root/.aws/credentials" and paste it to .s3cfg file.
This file has to be placed to the following directory of target machine
'/root/.s3cfg'
"""

import logging
import os
import time

import pytest

from commons import error_messages as errmsg
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from commons.utils.assert_utils import assert_in
from commons.utils.assert_utils import assert_not_in
from commons.utils.assert_utils import assert_true
from commons.utils.s3_utils import assert_s3_err_msg
from config import CMN_CFG
from config.s3 import S3_BLKBOX_CFG as S3CMD_CNF
from libs.s3 import SECRET_KEY, ACCESS_KEY
from libs.s3.s3_blackbox_test_lib import S3CMD
from libs.s3.s3_cmd_test_lib import S3CmdTestLib
from libs.s3.s3_test_lib import S3TestLib


# pylint: disable=too-many-instance-attributes
class TestS3cmdClient:
    """Blackbox s3cmd testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup suite level operation.")
        cls.log.info("Check, configure and update s3cmd config.")
        s3cmd_obj = S3CMD(ACCESS_KEY, SECRET_KEY)
        cls.log.info("Setting access and secret key & other options in s3cfg.")
        resp = s3cmd_obj.configure_s3cfg(ACCESS_KEY, SECRET_KEY)
        assert_true(resp, "Failed to update s3cfg.")
        cls.log.info("ENDED: Setup suite level operation.")

    def setup_method(self):
        """
        This function will be invoked before each test case execution
        It will perform prerequisite test steps if any
        """
        self.log.info("STARTED: Setup operations")
        self.s3cmd_test_obj = S3CmdTestLib()
        self.s3_test_obj = S3TestLib()
        self.root_path = os.path.join(
            os.getcwd(), TEST_DATA_FOLDER, "TestS3cmdClient")
        if not system_utils.path_exists(self.root_path):
            system_utils.make_dirs(self.root_path)
            self.log.info("Created path: %s", self.root_path)
        self.s3cmd_cfg = S3CMD_CNF["s3cmd_cfg"]
        self.file_path1 = os.path.join(self.root_path, "s3cmdtestfile{}.txt")
        self.file_path2 = os.path.join(self.root_path, "s3cmdtestfile{}.txt")
        self.bucket_name = self.s3cmd_cfg["bucket_name"].format(time.perf_counter_ns())
        self.s3cmd_bucket_list = []
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        This function will be invoked after each test case.
        It will perform all cleanup operations.
        This function will delete buckets and objects uploaded to that bucket.
        It will also delete the local files.
        """
        self.log.info("STARTED: Teardown operations")
        if self.s3cmd_bucket_list:
            self.log.info("Deleting buckets...")
            self.log.info(self.s3cmd_bucket_list)
            resp = self.s3_test_obj.delete_multiple_buckets(self.s3cmd_bucket_list)
            assert_true(resp[0], resp[1])
            self.log.info("Deleted buckets")
        for filepath in [self.file_path1, self.file_path2]:
            if system_utils.path_exists(filepath):
                system_utils.remove_file(filepath)
        self.log.info("ENDED: Teardown Operations")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7131")
    @CTFailOn(error_handler)
    def test_2309(self):
        """Create multiple bucket using s3cmd client."""
        self.log.info("STARTED: create multiple bucket using s3cmd client")
        for _ in range(2):
            bucket_name = self.s3cmd_cfg["bucket_name"].format(time.perf_counter_ns())
            bucket_url = self.s3cmd_cfg["bkt_path_format"].format(
                bucket_name)
            self.log.info("STEP: 1 Creating bucket %s", bucket_name)
            cmd_arguments = [bucket_url]
            command = self.s3cmd_test_obj.command_formatter(
                S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
            resp = system_utils.run_local_cmd(command, chk_stderr=True)
            assert_true(resp[0], resp[1])
            assert_in(
                self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(
                    resp[1]), resp[1])
            self.log.info("STEP: 1 Bucket was created %s", bucket_name)
            self.s3cmd_bucket_list.append(bucket_name)
        self.log.info("ENDED: create multiple bucket using s3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7155")
    @CTFailOn(error_handler)
    def test_2311(self):
        """Max no of buckets supported using s3cmd."""
        self.log.info("STARTED: max no of buckets supported using s3cmd")
        self.log.info("Step 1: Create max number of buckets using s3cmd.")
        for i in range(self.s3cmd_cfg["count_bkt"]):
            bucket_name = f"{self.s3cmd_cfg['bucket_name'].format(time.perf_counter_ns())}-{i}"
            bucket_url = self.s3cmd_cfg["bkt_path_format"].format(bucket_name)
            self.log.info("Creating bucket %s", bucket_name)
            cmd_arguments = [bucket_url, "-c /root/.s3cfg"]
            command = self.s3cmd_test_obj.command_formatter(
                S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
            resp = system_utils.run_local_cmd(command, chk_stderr=True)
            assert_true(resp[0], resp[1])
            assert_in(self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(resp[1]), resp[1])
            self.log.info("bucket was created %s", bucket_name)
            self.s3cmd_bucket_list.append(bucket_name)
        self.log.info("Step 2: check max number buckets get created.")
        status, output = system_utils.run_local_cmd("s3cmd ls -c /root/.s3cfg", chk_stderr=True)
        assert_true(status, output)
        bucket_list = output.split('\\n')
        assert_true(len(bucket_list) >= self.s3cmd_cfg["count_bkt"],
                    f"Failed to create max bucket using s3cmd: {len(bucket_list)}")
        self.log.info("Max buckets created successfully.")
        self.log.info("ENDED: max no of buckets supported using s3cmd")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7156")
    @CTFailOn(error_handler)
    def test_2312(self):
        """Delete empty bucket using s3cmd client."""
        self.log.info("STARTED: Delete empty bucket using s3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(
            self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["success_msg_crt"].format(
            bucket_url), str(resp[1]), resp[1])
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.log.info("STEP: 2 Deleting bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["remove_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["success_msg_del"].format(
            bucket_url), str(resp[1]), resp[1])
        if not resp[0]:
            self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 1 Bucket was deleted %s", self.bucket_name)
        self.log.info("ENDED: Delete empty bucket using s3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7157")
    @CTFailOn(error_handler)
    def test_2308(self):
        """Create bucket using s3cmd."""
        self.log.info("STARTED: create bucket using s3cmd")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(
            self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(
            self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Listing buckets")
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["list_bucket"], )
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        self.log.info(resp)
        assert_true(resp[0], resp[1])
        bucket_list = resp[1].split('\\n')
        found = False
        for bucket in bucket_list:
            if bucket_url in bucket:
                found = True
        assert_true(found)
        self.log.info("STEP: 2 Buckets listed")
        self.log.info("ENDED: create bucket using s3cmd")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7158")
    @CTFailOn(error_handler)
    def test_2313(self):
        """Delete multiple buckets using s3cmd client."""
        self.log.info("STARTED: Delete multiple buckets using s3cmd client")
        bucket_name_1 = self.s3cmd_cfg["bucket_name"].format(time.perf_counter_ns())
        bucket_url_1 = self.s3cmd_cfg["bkt_path_format"].format(
            bucket_name_1)
        self.log.info("STEP: 1 Creating bucket 1 %s", bucket_name_1)
        cmd_arguments = [bucket_url_1]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["success_msg_crt"].format(
            bucket_url_1), str(resp[1]), resp)
        self.log.info("STEP: 1 Created bucket 1 %s", bucket_name_1)
        bucket_name_2 = self.s3cmd_cfg["bucket_name"].format(time.perf_counter_ns())
        bucket_url_2 = self.s3cmd_cfg["bkt_path_format"].format(
            bucket_name_2)
        self.log.info("STEP: 1 Creating bucket 2 %s", bucket_name_2)
        cmd_arguments = [bucket_url_2]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["success_msg_crt"].format(
            bucket_url_2), str(resp[1]), resp)
        self.log.info("STEP: 1 Created bucket 2 %s", bucket_name_2)
        self.log.info("STEP: 2 Deleting multiple buckets")
        cmd_arguments = [bucket_url_1, bucket_url_2]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["remove_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        if not resp[0]:
            self.s3cmd_bucket_list.extend([bucket_name_1, bucket_name_2])
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["success_msg_del"].format(
            bucket_url_1), str(resp[1]), resp)
        assert_in(self.s3cmd_cfg["success_msg_del"].format(
            bucket_url_2), str(resp[1]), resp)
        self.log.info("STEP: 2 Multiple buckets deleted")
        self.log.info("ENDED: Delete multiple buckets using s3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7159")
    @CTFailOn(error_handler)
    def test_2326(self):
        """Create bucket with existing bucket name using s3cmd client."""
        self.log.info(
            "STARTED: Create bucket with existing bucket name using s3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(
            self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(
            self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Creating bucket with existing bucket name")
        try:
            command = self.s3cmd_test_obj.command_formatter(
                S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
            resp = system_utils.run_local_cmd(command, chk_stderr=True)
        except CTException as error:
            assert_s3_err_msg(errmsg.RGW_ERR_DUPLICATE_BKT_NAME,
                              errmsg.CORTX_ERR_DUPLICATE_BKT_NAME,
                              CMN_CFG["s3_engine"], error)
        self.log.info(
            "STEP: 2 Creating bucket failed with existing bucket name")
        self.log.info(
            "ENDED: Create bucket with existing bucket name using s3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7160")
    @CTFailOn(error_handler)
    def test_2310(self):
        """List buckets using s3cmd client."""
        self.log.info("STARTED: list buckets using s3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(
            self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(
            self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Listing buckets")
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["list_bucket"], )
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        self.log.info(resp)
        assert_true(resp[0], resp[1])
        bucket_list = resp[1].split('\\n')
        found = False
        for bucket in bucket_list:
            if bucket_url in bucket:
                found = True
        assert_true(found)
        self.log.info("STEP: 2 Buckets listed")
        self.log.info("ENDED: list buckets using s3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7161")
    @CTFailOn(error_handler)
    def test_2316(self):
        """Upload object using s3cmd client."""
        self.log.info("STARTED: upload object using s3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(
            self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(
            self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 File upload to bucket")
        filename = self.file_path1.format(int(time.perf_counter_ns()))
        system_utils.run_local_cmd(self.s3cmd_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("ENDED: upload object using s3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7162")
    @CTFailOn(error_handler)
    def test_2314(self):
        """Delete bucket which has objects using s3cmd client."""
        self.log.info(
            "STARTED: delete bucket which has objects using s3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(
            self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(
            self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 File upload to bucket")
        filename = self.file_path1.format(int(time.perf_counter_ns()))
        system_utils.run_local_cmd(self.s3cmd_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Delete bucket which has file in it")
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["remove_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_in(errmsg.S3_BKT_NOT_EMPTY_ERR, str(resp[1]), resp)
        self.log.info("STEP: 3 Delete bucket failed")
        self.log.info(
            "ENDED: delete bucket which has objects using s3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7163")
    @CTFailOn(error_handler)
    def test_2320(self):
        """Delete single object from bucket using s3cmd client."""
        self.log.info(
            "STARTED: delete single object from bucket using s3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(
            self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(
            self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Upload file to bucket")
        filename = self.file_path1.format(int(time.perf_counter_ns()))
        system_utils.run_local_cmd(self.s3cmd_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Delete single file")
        cmd_arguments = ["/".join([bucket_url, os.path.basename(filename)])]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["del_obj"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp)
        assert_in(
            self.s3cmd_cfg["delete_msg"].format(
                cmd_arguments[0]), str(resp[1]), resp)
        self.log.info("STEP: 3 Single file deleted")
        self.log.info(
            "ENDED: delete single object from bucket using s3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7164")
    @CTFailOn(error_handler)
    def test_2321(self):
        """Delete multiple objects from bucket using s3cmd client."""
        self.log.info("STARTED: delete multiple objects from bucket using s3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Files upload to bucket")
        filename = self.file_path1.format(int(time.perf_counter_ns()))
        system_utils.run_local_cmd(self.s3cmd_cfg["file_creation"].format(filename))
        filename1 = self.file_path2.format(int(time.perf_counter_ns()))
        system_utils.run_local_cmd(self.s3cmd_cfg["file_creation"].format(filename1))
        cmd_arguments = [filename, bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
        cmd_arguments = [filename1, bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 Files uploaded")
        self.log.info("STEP: 3 Delete multiple files from bucket")
        cmd_arguments = ["/".join([bucket_url, os.path.basename(filename)]),
                         "/".join([bucket_url, os.path.basename(filename1)])]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["del_obj"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp)
        assert_in(self.s3cmd_cfg["delete_msg"].format(cmd_arguments[0]), str(resp[1]), resp)
        assert_in(self.s3cmd_cfg["delete_msg"].format(cmd_arguments[1]), str(resp[1]), resp)
        self.log.info("STEP: 3 Multiple files deleted from bucket")
        self.log.info(
            "ENDED: delete multiple objects from bucket using s3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7165")
    @CTFailOn(error_handler)
    def test_2317(self):
        """List objects using S3cmd client."""
        self.log.info("STARTED: list objects using S3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(
            self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 File upload to bucket")
        filename = self.file_path1.format(time.perf_counter_ns())
        system_utils.run_local_cmd(self.s3cmd_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Listing object in bucket")
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["list_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        self.log.info(resp)
        assert_true(resp[0], resp[1])
        fileurl = "/".join([bucket_url, os.path.basename(filename)])
        self.log.info(fileurl)
        assert_in(fileurl, resp[1], resp[1])
        self.log.info("STEP: 3 Object listed in bucket")
        self.log.info("ENDED: list objects using S3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7552")
    @CTFailOn(error_handler)
    def test_2322(self):
        """Delete all objects from bucket using s3cmd client."""
        self.log.info(
            "STARTED: delete all objects from bucket using s3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Files upload to bucket")
        filename = self.file_path1.format(int(time.perf_counter_ns()))
        system_utils.run_local_cmd(self.s3cmd_cfg["file_creation"].format(filename))
        filename1 = self.file_path2.format(int(time.perf_counter_ns()))
        system_utils.run_local_cmd(self.s3cmd_cfg["file_creation"].format(filename1))
        cmd_arguments = [filename, bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
        cmd_arguments = [filename1, bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 Files uploaded")
        self.log.info("STEP: 3 Deleting all files from bucket")
        cmd_arguments = [self.s3cmd_cfg["force"],
                         self.s3cmd_cfg["recursive"],
                         bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["rm_bkt"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp)
        expected_substring = "/".join([bucket_url, os.path.basename(filename)])
        expected_substring1 = "/".join([bucket_url,
                                       os.path.basename(filename1)])
        for exp_str in [expected_substring, expected_substring1]:
            assert_in(self.s3cmd_cfg["delete_msg"].format(
                exp_str), str(resp[1]), resp)
        self.log.info("STEP: 3 All files deleted from bucket")
        self.log.info("STEP: 4 Listing object in bucket")
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["list_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        expected_substring = "/".join([bucket_url, os.path.basename(filename)])
        expected_substring1 = "/".join([bucket_url,
                                       os.path.basename(filename1)])
        for exp_str in [expected_substring, expected_substring1]:
            assert_not_in(self.s3cmd_cfg["delete_msg"].format(
                exp_str), str(resp[1]), resp)
        self.log.info("STEP: 5 Object listed in bucket")
        self.log.info("ENDED: delete all objects from bucket using s3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7553")
    @CTFailOn(error_handler)
    def test_2327(self):
        """Get various information about Buckets using s3cmd client."""
        self.log.info(
            "STARTED: Get various information about Buckets using s3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(
            self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Getting bucket information")
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, "info", cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(bucket_url, str(resp[1]), resp)
        for success_msg in self.s3cmd_cfg["success_msgs"]:
            assert_in(success_msg, str(resp[1]), resp)
        self.log.info("STEP: 2 Got bucket information")
        self.log.info("ENDED: Get various information about Buckets using s3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7551")
    @CTFailOn(error_handler)
    def test_2319(self):
        """Get file from bucket using S3cmd client."""
        self.log.info("STARTED: Get file from bucket using S3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 File upload to bucket")
        filename = self.file_path1.format(int(time.perf_counter_ns()))
        system_utils.run_local_cmd(self.s3cmd_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 4 Get file from bucket")
        cmd_arguments = ["/".join([bucket_url, os.path.basename(filename)]),
                         self.s3cmd_cfg["force"]]
        command = self.s3cmd_test_obj.command_formatter(S3CMD_CNF, self.s3cmd_cfg["get"],
                                                        cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        expected_substring = "/".join([bucket_url, os.path.basename(filename)])
        assert_in(f"download: '{expected_substring}'", str(resp[1]), resp)
        assert_in("done", str(resp[1]), resp)
        self.log.info("STEP: 4 Got file from bucket")
        self.log.info("ENDED: Get file from bucket using S3cmd client")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7549")
    @CTFailOn(error_handler)
    def test_2315(self):
        """Delete bucket forcefully which has objects using s3cmd client."""
        self.log.info(
            "STARTED: delete bucket forcefully which has objects using s3cmd client")
        bucket_url = self.s3cmd_cfg["bkt_path_format"].format(self.bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", self.bucket_name)
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", self.bucket_name)
        self.s3cmd_bucket_list.append(self.bucket_name)
        self.log.info("STEP: 2 Files upload to bucket")
        filename = self.file_path1.format(int(time.perf_counter_ns()))
        system_utils.run_local_cmd(self.s3cmd_cfg["file_creation"].format(filename))
        filename1 = self.file_path2.format(int(time.perf_counter_ns()))
        system_utils.run_local_cmd(self.s3cmd_cfg["file_creation"].format(filename1))
        cmd_arguments = [filename, bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
        cmd_arguments = [filename1, bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 Files uploaded")
        self.log.info("STEP: 3 Deleting bucket forcefully")
        cmd_arguments = [bucket_url, self.s3cmd_cfg["recursive"]]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["remove_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, flg=True)
        assert_true("WARNING" in str(resp[1]), resp[1])
        assert_in(self.s3cmd_cfg["success_msg_del"].format(bucket_url), str(resp[1]), resp[1])
        self.log.info("STEP: 3 Deleted bucket forcefully")
        self.s3cmd_bucket_list = []
        self.log.info("STEP: 4 Listing object in bucket")
        cmd_arguments = [bucket_url]
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["list_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_in(errmsg.NO_BUCKET_OBJ_ERR_KEY, str(resp[1]), resp[1])
        self.log.info("STEP: 5 Object listed in bucket")
        self.log.info("ENDED: delete bucket forcefully which has objects using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7550")
    @CTFailOn(error_handler)
    def test_2318(self):
        """List all objects in all buckets using s3cmd."""
        self.log.info("STARTED: list all objects in all buckets using s3cmd")
        obj_list = []
        for _ in range(2):
            bucket_name = self.s3cmd_cfg["bucket_name"].format(time.perf_counter_ns())
            bucket_url = self.s3cmd_cfg["bkt_path_format"].format(bucket_name)
            self.log.info("STEP: 1 Creating bucket %s", bucket_name)
            cmd_arguments = [bucket_url]
            command = self.s3cmd_test_obj.command_formatter(
                S3CMD_CNF, self.s3cmd_cfg["make_bucket"], cmd_arguments)
            resp = system_utils.run_local_cmd(command, chk_stderr=True)
            assert_true(resp[0], resp[1])
            assert_in(self.s3cmd_cfg["success_msg_crt"].format(bucket_url), str(resp[1]), resp)
            self.log.info("STEP: 1 Bucket was created %s", bucket_name)
            self.s3cmd_bucket_list.append(bucket_name)
            self.log.info("STEP: 2 File upload to bucket")
            filename = self.file_path1.format(int(time.perf_counter_ns()))
            system_utils.run_local_cmd(
                self.s3cmd_cfg["file_creation"].format(filename))
            cmd_arguments = [filename, bucket_url]
            command = self.s3cmd_test_obj.command_formatter(
                S3CMD_CNF, self.s3cmd_cfg["put_bucket"], cmd_arguments)
            resp = system_utils.run_local_cmd(command, chk_stderr=True)
            assert_true(resp[0], resp[1])
            assert_in(self.s3cmd_cfg["upload_msg"], str(resp[1]), resp)
            obj_list.append("/".join([bucket_url, os.path.basename(filename)]))
            self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Listing objects in all bucket")
        command = self.s3cmd_test_obj.command_formatter(
            S3CMD_CNF, self.s3cmd_cfg["list_all_buckets"])
        resp = system_utils.run_local_cmd(command, chk_stderr=True)
        assert_true(resp[0], resp[1])
        for obj in obj_list:
            assert_in(obj, str(resp[1]), resp)
        self.log.info("STEP: 3 Objects listed in all bucket")
        self.log.info("ENDED: list all objects in all buckets using s3cmd")
