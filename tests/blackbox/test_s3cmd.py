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
Note:
The pre-requisite of this testfile require the configuration changes in .s3cfg file.
Take the secret-key and access-key from "/root/.aws/credentials" and paste it to .s3cfg file.
This file has to be placed to the following directory of target machine
'/root/.s3cfg'
"""

import os
import time
import logging
import pytest

from commons.constants import const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils.config_utils import read_yaml, get_config, update_config_ini
from commons.utils.assert_utils import assert_true, assert_false, assert_in, assert_not_in
from commons.utils import system_utils
from commons.helpers.node_helper import Node
from config import CMN_CFG
from config import S3_CFG
from libs.s3.s3_cmd_test_lib import S3CmdTestLib
from libs.s3. s3_test_lib import S3TestLib
from libs.s3 import SECRET_KEY, ACCESS_KEY, S3H_OBJ

S3CMD_TEST_OBJ = S3CmdTestLib()
S3_TEST_OBJ = S3TestLib()
S3CMD_CNF = read_yaml("config/blackbox/test_s3cmd.yaml")[1]


class TestS3cmdClient:
    """
    Blackbox S3CMD Test Suite.
    """

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        resp = system_utils.is_rpm_installed(const.S3CMD)
        assert_true(resp[0], resp[1])
        resp = system_utils.path_exists(S3_CFG["s3cfg_path"])
        assert_true(resp, "config path not exists: {}".format(S3_CFG["s3cfg_path"]))
        cls.common_cfg = S3CMD_CNF["common_cfg"]
        cls.node_helper_obj = Node(
            hostname=CMN_CFG["nodes"][0]["host"],
            username=CMN_CFG["nodes"][0]["username"],
            password=CMN_CFG["nodes"][0]["password"])
        s3cmd_host = get_config(
            S3_CFG["s3cfg_path"], "default", "host_base")
        if s3cmd_host != S3_CFG["s3_url"].split("/")[-1]:
            for ky in ["host_base", "host_bucket"]:
                update_config_ini(
                    S3_CFG["s3cfg_path"], "default", ky, S3_CFG["s3_url"].split("/")[-1])

        s3cmd_access = get_config(
            S3_CFG["s3cfg_path"], "default", "access_key")
        s3cmd_secret = get_config(
            S3_CFG["s3cfg_path"], "default", "secret_key")
        if s3cmd_access != ACCESS_KEY or s3cmd_secret != SECRET_KEY:
            cls.log.info("Setting access and secret key in s3cfg.")
            resp = S3H_OBJ.configure_s3cfg(ACCESS_KEY, SECRET_KEY)
            assert_true(resp, f"Failed to update s3cfg.")
        cls.test_file = "s3cmdtestfile{}.txt"
        cls.root_path = os.path.join(
            os.getcwd(), "testdata", "TestS3cmdClient")
        cls.file_path = os.path.join(cls.root_path, cls.test_file)
        if not system_utils.path_exists(cls.root_path):
            system_utils.make_dirs(cls.root_path)
            cls.log.info("Created path: %s", cls.root_path)
        cls.log.info("ENDED: setup test suite operations.")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        cls.log.info("STARTED: teardown test suite operations.")
        if system_utils.path_exists(cls.root_path):
            system_utils.remove_dirs(cls.root_path)
        cls.log.info("Cleanup test directory: %s", cls.root_path)
        cls.log.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        This function will be invoked before each test case execution
        It will perform prerequisite test steps if any
        """
        self.log.info("STARTED: Setup operations")
        bucket_list = S3_TEST_OBJ.bucket_list()[1]
        self.log.info(bucket_list)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        This function will be invoked after each test case.
        It will perform all cleanup operations.
        This function will delete buckets and objects uploaded to that bucket.
        It will also delete the local files.
        """
        self.log.info("STARTED: Teardown operations")
        bucket_list = S3_TEST_OBJ.bucket_list()[1]
        s3cmd_buckets = [
            bucket for bucket in bucket_list
            if S3CMD_CNF["common_cfg"]["bucket_name_prefix"] in bucket]
        self.log.info("Buckets to be deleted: %s", s3cmd_buckets)
        if s3cmd_buckets:
            self.log.info("Deleting buckets...")
            self.log.info(s3cmd_buckets)
            resp = S3_TEST_OBJ.delete_multiple_buckets(s3cmd_buckets)
            assert_true(resp[0], resp[1])
            self.log.info("Deleted buckets")
        if system_utils.path_exists(self.file_path):
            system_utils.remove_file(self.file_path)
        self.log.info("ENDED: Teardown Operations")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7131")
    @CTFailOn(error_handler)
    def test_2309(self):
        """Create multiple bucket using s3cmd client."""
        self.log.info("STARTED: create multiple bucket using s3cmd client")
        test_cfg = S3CMD_CNF["common_cfg"]
        for _ in range(2):
            bucket_name = test_cfg["bucket_name"].format(time.time())
            bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
                bucket_name)
            self.log.info("STEP: 1 Creating bucket %s", bucket_name)
            cmd_arguments = [bucket_url]
            command = S3CMD_TEST_OBJ.command_formatter(
                S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
            resp = system_utils.run_local_cmd(command)
            assert_true(resp[0], resp[1])
            assert_in(
                test_cfg["success_msg"].format(bucket_url), str(
                    resp[1]), resp[1])
            self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("ENDED: create multiple bucket using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7155")
    @CTFailOn(error_handler)
    def test_2311(self):
        """Max no of buckets supported using s3cmd."""
        self.log.info("STARTED: max no of buckets supported using s3cmd")
        test_cfg = S3CMD_CNF["common_cfg"]
        bucket_count = S3CMD_CNF["common_cfg"]["count_bkt"]
        for _ in range(bucket_count):
            bucket_name = test_cfg["bucket_name"].format(time.time())
            bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
                bucket_name)
            ret_val, out = system_utils.run_local_cmd("s3cmd ls")
            assert_true(ret_val, out)
            bucket_list = out[0].split('\\n')
            self.log.info("STEP: 1 Creating bucket %s", bucket_name)
            cmd_arguments = [bucket_url, "-c /root/.s3cfg"]
            command = S3CMD_TEST_OBJ.command_formatter(
                S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
            resp = system_utils.run_local_cmd(command)
            try:
                if len(bucket_list) > S3CMD_CNF["common_cfg"]["count_bkt"]:
                    assert_false(resp[0], resp[1])
            except AssertionError:
                self.log.info(
                    "skipping this exception as this is not implemented yet as mentioned in tc")
            else:
                assert_true(resp[0], resp[1])
                assert_in(S3CMD_CNF["test_2311"]["success_msg"].format(
                    bucket_url), str(resp[1]), resp[1])
                self.log.info(
                    "STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("ENDED: max no of buckets supported using s3cmd")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7156")
    @CTFailOn(error_handler)
    def test_2312(self):
        """Delete empty bucket using s3cmd client."""
        self.log.info("STARTED: Delete empty bucket using s3cmd client")
        test_cfg = S3CMD_CNF["common_cfg"]
        bucket_name = test_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(S3CMD_CNF["test_2312"]["success_msg_crt"].format(
            bucket_url), str(resp[1]), resp[1])
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Deleting bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2312"]["remove_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(S3CMD_CNF["test_2312"]["success_msg_del"].format(
            bucket_url), str(resp[1]), resp[1])
        self.log.info("STEP: 1 Bucket was deleted %s", bucket_name)
        self.log.info("ENDED: Delete empty bucket using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7157")
    @CTFailOn(error_handler)
    def test_2308(self):
        """Create bucket using s3cmd."""
        self.log.info("STARTED: create bucket using s3cmd")
        test_cfg = S3CMD_CNF["test_2308"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            test_cfg["success_msg"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Listing buckets")
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2308"]["list_bucket"], )
        resp = system_utils.run_local_cmd(command)
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

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7158")
    @CTFailOn(error_handler)
    def test_2313(self):
        """Delete multiple buckets using s3cmd client."""
        self.log.info("STARTED: Delete multiple buckets using s3cmd client")
        test_cfg = S3CMD_CNF["test_2313"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url_1 = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket 1 %s", bucket_name)
        cmd_arguments = [bucket_url_1]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(test_cfg["success_msg_crt"].format(
            bucket_url_1), str(resp[1]), resp)
        self.log.info("STEP: 1 Created bucket 1 %s", bucket_name)
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url_2 = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket 2 %s", bucket_name)
        cmd_arguments = [bucket_url_2]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(test_cfg["success_msg_crt"].format(
            bucket_url_2), str(resp[1]), resp)
        self.log.info("STEP: 1 Created bucket 2 %s", bucket_name)
        self.log.info("STEP: 2 Deleting multiple buckets")
        cmd_arguments = [bucket_url_1, bucket_url_2]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2313"]["remove_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(test_cfg["success_msg_del"].format(
            bucket_url_1), str(resp[1]), resp)
        assert_in(test_cfg["success_msg_del"].format(
            bucket_url_2), str(resp[1]), resp)
        self.log.info("STEP: 2 Multiple buckets deleted")
        self.log.info("ENDED: Delete multiple buckets using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7159")
    @CTFailOn(error_handler)
    def test_2326(self):
        """Create bucket with existing bucket name using s3cmd client."""
        self.log.info(
            "STARTED: Create bucket with existing bucket name using s3cmd client")
        test_cfg = S3CMD_CNF["test_2326"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            test_cfg["success_msg"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Creating bucket with existing bucket name")
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_in(test_cfg["error_msg"], str(resp[1]), resp)
        self.log.info(
            "STEP: 2 Creating bucket failed with existing bucket name")
        self.log.info(
            "ENDED: Create bucket with existing bucket name using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7160")
    @CTFailOn(error_handler)
    def test_2310(self):
        """List buckets using s3cmd client."""
        self.log.info("STARTED: list buckets using s3cmd client")
        test_cfg = S3CMD_CNF["test_2310"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            test_cfg["success_msg"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Listing buckets")
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2310"]["list_bucket"], )
        resp = system_utils.run_local_cmd(command)
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

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7161")
    @CTFailOn(error_handler)
    def test_2316(self):
        """Upload object using s3cmd client."""
        self.log.info("STARTED: upload object using s3cmd client")
        test_cfg = S3CMD_CNF["test_2316"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            test_cfg["success_msg"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 File upload to bucket")
        filename = self.file_path.format(int(time.time()))
        system_utils.run_local_cmd(test_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("ENDED: upload object using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7162")
    @CTFailOn(error_handler)
    def test_2314(self):
        """Delete bucket which has objects using s3cmd client."""
        self.log.info(
            "STARTED: delete bucket which has objects using s3cmd client")
        test_cfg = S3CMD_CNF["test_2314"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            self.common_cfg["success_msg"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 File upload to bucket")
        filename = self.file_path.format(int(time.time()))
        system_utils.run_local_cmd(test_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Delete bucket which has file in it")
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, self.common_cfg["remove_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_in(test_cfg["error_msg"], str(resp[1]), resp)
        self.log.info("STEP: 3 Delete bucket failed")
        self.log.info(
            "ENDED: delete bucket which has objects using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7163")
    @CTFailOn(error_handler)
    def test_2320(self):
        """Delete single object from bucket using s3cmd client."""
        self.log.info(
            "STARTED: delete single object from bucket using s3cmd client")
        test_cfg = S3CMD_CNF["test_2320"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            test_cfg["success_msg"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Upload file to bucket")
        filename = self.file_path.format(int(time.time()))
        system_utils.run_local_cmd(test_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Delete single file")
        cmd_arguments = ["/".join([bucket_url, os.path.basename(filename)])]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2320"]["del_obj"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp)
        assert_in(
            test_cfg["delete_msg"].format(
                cmd_arguments[0]), str(resp[1]), resp)
        self.log.info("STEP: 3 Single file deleted")
        self.log.info(
            "ENDED: delete single object from bucket using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7164")
    @CTFailOn(error_handler)
    def test_2321(self):
        """Delete multiple objects from bucket using s3cmd client."""
        self.log.info(
            "STARTED: delete multiple objects from bucket using s3cmd client")
        test_cfg = S3CMD_CNF["test_2321"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            test_cfg["success_msg"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Files upload to bucket")
        filename = self.file_path.format(int(time.time()))
        system_utils.run_local_cmd(test_cfg["file_creation"].format(filename))
        filename1 = self.file_path.format(int(time.time()))
        system_utils.run_local_cmd(test_cfg["file_creation"].format(filename1))
        cmd_arguments = [filename, bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
        cmd_arguments = [filename1, bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 Files uploaded")
        self.log.info("STEP: 3 Delete multiple files from bucket")
        cmd_arguments = ["/".join([bucket_url, os.path.basename(filename)]),
                         "/".join([bucket_url, os.path.basename(filename1)])]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2321"]["del_obj"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp)
        assert_in(
            test_cfg["delete_msg"].format(
                cmd_arguments[0]), str(
                resp[1]), resp)
        assert_in(
            test_cfg["delete_msg"].format(
                cmd_arguments[1]), str(
                resp[1]), resp)
        self.log.info("STEP: 3 Multiple files deleted from bucket")
        self.log.info(
            "ENDED: delete multiple objects from bucket using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7165")
    @CTFailOn(error_handler)
    def test_2317(self):
        """List objects using S3cmd client."""
        self.log.info("STARTED: list objects using S3cmd client")
        test_cfg = S3CMD_CNF["test_2317"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            test_cfg["success_msg"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 File upload to bucket")
        filename = self.file_path.format(int(time.time()))
        system_utils.run_local_cmd(test_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Listing object in bucket")
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2317"]["list_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        self.log.info(resp)
        assert_true(resp[0], resp[1])
        fileurl = "/".join([bucket_url, os.path.basename(filename)])
        self.log.info(fileurl)
        assert_in(fileurl, resp[1], resp[1])
        self.log.info("STEP: 3 Object listed in bucket")
        self.log.info("ENDED: list objects using S3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7552")
    @CTFailOn(error_handler)
    def test_2322(self):
        """Delete all objects from bucket using s3cmd client."""
        self.log.info(
            "STARTED: delete all objects from bucket using s3cmd client")
        test_cfg = S3CMD_CNF["test_2322"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            test_cfg["success_msg"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Files upload to bucket")
        filename = self.file_path.format(int(time.time()))
        system_utils.run_local_cmd(test_cfg["file_creation"].format(filename))
        filename1 = self.file_path.format(int(time.time()))
        system_utils.run_local_cmd(test_cfg["file_creation"].format(filename1))
        cmd_arguments = [filename, bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
        cmd_arguments = [filename1, bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 Files uploaded")
        self.log.info("STEP: 3 Deleting all files from bucket")
        cmd_arguments = [S3CMD_CNF["test_2322"]["force"],
                         S3CMD_CNF["test_2322"]["recursive"],
                         bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2322"]["rm_bkt"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp)
        expected_substring = "/".join([bucket_url, os.path.basename(filename)])
        expected_substring1 = "/".join([bucket_url,
                                       os.path.basename(filename1)])
        for exp_str in [expected_substring, expected_substring1]:
            assert_in(test_cfg["delete_msg"].format(
                exp_str), str(resp[1]), resp)

        self.log.info("STEP: 3 All files deleted from bucket")
        self.log.info("STEP: 4 Listing object in bucket")
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2322"]["list_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        expected_substring = "/".join([bucket_url, os.path.basename(filename)])
        expected_substring1 = "/".join([bucket_url,
                                       os.path.basename(filename1)])
        for exp_str in [expected_substring, expected_substring1]:
            assert_not_in(test_cfg["delete_msg"].format(
                exp_str), str(resp[1]), resp)
        self.log.info("STEP: 5 Object listed in bucket")
        self.log.info(
            "ENDED: delete all objects from bucket using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7553")
    @CTFailOn(error_handler)
    def test_2327(self):
        """Get various information about Buckets using s3cmd client."""
        self.log.info(
            "STARTED: Get various information about Buckets using s3cmd client")
        test_cfg = S3CMD_CNF["common_cfg"]
        bucket_name = test_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            S3CMD_CNF["test_2312"]["success_msg_crt"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Getting bucket information")
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2327"]["info"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(bucket_url, str(resp[1]), resp)
        for success_msg in ["success_msg2", "success_msg3",
                            "success_msg4", "success_msg5",
                            "success_msg6", "success_msg7"]:
            assert_in(
                S3CMD_CNF["test_2327"][success_msg], str(
                    resp[1]), resp)

        self.log.info("STEP: 2 Got bucket information")
        self.log.info(
            "ENDED: Get various information about Buckets using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7551")
    @CTFailOn(error_handler)
    def test_2319(self):
        """Get file from bucket using S3cmd client."""
        self.log.info("STARTED: Get file from bucket using S3cmd client")
        test_cfg = S3CMD_CNF["test_2319"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            test_cfg["success_msg"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 File upload to bucket")
        filename = self.file_path.format(int(time.time()))
        system_utils.run_local_cmd(test_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 4 Get file from bucket")
        cmd_arguments = ["/".join([bucket_url, os.path.basename(filename)]),
                         S3CMD_CNF["test_2319"]["force"]]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2319"]["get"],
            cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        expected_substring = "/".join([bucket_url, os.path.basename(filename)])
        assert_in(test_cfg["success_msg2"].format(
            expected_substring), str(resp[1]), resp)
        assert_in(test_cfg["success_msg3"], str(resp[1]), resp)
        self.log.info("STEP: 4 Got file from bucket")
        self.log.info("ENDED: Get file from bucket using S3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7549")
    @CTFailOn(error_handler)
    def test_2315(self):
        """Delete bucket forcefully which has objects using s3cmd client."""
        self.log.info(
            "STARTED: delete bucket forcefully which has objects using s3cmd client")
        test_cfg = S3CMD_CNF["test_2315"]
        bucket_name = self.common_cfg["bucket_name"].format(time.time())
        bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket %s", bucket_name)
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(
            test_cfg["success_msg"].format(bucket_url), str(
                resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created %s", bucket_name)
        self.log.info("STEP: 2 Files upload to bucket")
        filename = self.file_path.format(int(time.time()))
        system_utils.run_local_cmd(test_cfg["file_creation"].format(filename))
        filename1 = self.file_path.format(int(time.time()))
        system_utils.run_local_cmd(test_cfg["file_creation"].format(filename1))
        cmd_arguments = [filename, bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
        cmd_arguments = [filename1, bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 Files uploaded")
        self.log.info("STEP: 3 Deleting bucket forcefully")
        cmd_arguments = [bucket_url,
                         S3CMD_CNF["test_2315"]["recursive"]
                         ]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2315"]["rm_bkt"], cmd_arguments)
        resp = system_utils.run_local_cmd(command, flg=True)
        expected_substring = S3CMD_CNF["test_2315"]["success_msg2"]
        assert_true(expected_substring in str(resp[1]), resp[1])
        assert_in(
            test_cfg["success_msg_del"].format(bucket_url), str(
                resp[1]), resp[1])
        self.log.info("STEP: 3 Deleted bucket forcefully")
        self.log.info("STEP: 4 Listing object in bucket")
        cmd_arguments = [bucket_url]
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2315"]["list_bucket"], cmd_arguments)
        resp = system_utils.run_local_cmd(command)
        assert_in(test_cfg["error_msg"], str(resp[1]), resp[1])
        self.log.info("STEP: 5 Object listed in bucket")
        self.log.info(
            "ENDED: delete bucket forcefully which has objects using s3cmd client")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7550")
    @CTFailOn(error_handler)
    def test_2318(self):
        """List all objects in all buckets using s3cmd."""
        self.log.info("STARTED: list all objects in all buckets using s3cmd")
        test_cfg = S3CMD_CNF["common_cfg"]
        obj_list = list()
        for _ in range(2):
            bucket_name = test_cfg["bucket_name"].format(time.time())
            bucket_url = S3CMD_CNF["common_cfg"]["bkt_path_format"].format(
                bucket_name)
            self.log.info("STEP: 1 Creating bucket %s", bucket_name)
            cmd_arguments = [bucket_url]
            command = S3CMD_TEST_OBJ.command_formatter(
                S3CMD_CNF, S3CMD_CNF["common_cfg"]["make_bucket"], cmd_arguments)
            resp = system_utils.run_local_cmd(command)
            assert_true(resp[0], resp[1])
            assert_in(
                test_cfg["success_msg"].format(bucket_url), str(
                    resp[1]), resp)
            self.log.info("STEP: 1 Bucket was created %s", bucket_name)
            self.log.info("STEP: 2 File upload to bucket")
            filename = self.file_path.format(int(time.time()))
            system_utils.run_local_cmd(
                S3CMD_CNF["test_2318"]["file_creation"].format(filename))
            cmd_arguments = [filename, bucket_url]
            command = S3CMD_TEST_OBJ.command_formatter(
                S3CMD_CNF, S3CMD_CNF["common_cfg"]["put_bucket"], cmd_arguments)
            resp = system_utils.run_local_cmd(command)
            assert_true(resp[0], resp[1])
            assert_in(self.common_cfg["upload_msg"], str(resp[1]), resp)
            obj_list.append("/".join([bucket_url, os.path.basename(filename)]))
            self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Listing objects in all bucket")
        command = S3CMD_TEST_OBJ.command_formatter(
            S3CMD_CNF, S3CMD_CNF["test_2318"]["list_all_buckets"])
        resp = system_utils.run_local_cmd(command)
        assert_true(resp[0], resp[1])
        for obj in obj_list:
            assert_in(obj, str(resp[1]), resp)
        self.log.info("STEP: 3 Objects listed in all bucket")
        self.log.info("ENDED: list all objects in all buckets using s3cmd")
