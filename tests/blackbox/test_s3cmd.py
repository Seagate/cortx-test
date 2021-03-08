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
from subprocess import Popen, PIPE
import time
import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.utils.config_utils import read_yaml, get_config
from commons.utils.assert_utils import  assert_true, assert_false, assert_in, assert_equal

from libs.s3 import s3_cmd_test_lib
from libs.s3 import s3_test_lib
from libs.s3 import SECRET_KEY,ACCESS_KEY, S3H_OBJ

s3cmd_test_obj = s3_cmd_test_lib.S3CmdTestLib()
s3_test_obj = s3_test_lib.S3TestLib()
s3_conf = read_yaml("config/s3/s3_config.yaml")[1]
s3cmd_cnf = read_yaml("config/blackbox/test_s3cmd.yaml")[1]
common_cfg = s3cmd_cnf["common_cfg"]
CM_CFG = read_yaml("config/common_config.yaml")[1]


class S3cmdClient():
    """Blackbox s3cmd testsuite"""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")


    @CTFailOn(error_handler)
    def setup_method(self):
        """
        This function will be invoked before each test case execution
        It will perform prerequisite test steps if any
        """
        self.log.info("STARTED: Setup operations")
        access, secret = ACCESS_KEY, SECRET_KEY,
        s3cmd_access = get_config(
            CM_CFG["s3cfg_path"], "default", "access_key")
        s3cmd_secret = get_config(
            CM_CFG["s3cfg_path"], "default", "secret_key")
        if s3cmd_access != access or s3cmd_secret != secret:
            self.log.info("Setting access and secret key in s3cfg.")
            S3H_OBJ.configure_s3cfg(access, secret)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        This function will be invoked after each test case.
        It will perform all cleanup operations.
        This function will delete buckets and objects uploaded to that bucket.
        It will also delete the local files.
        """
        self.log.info("STARTED: Teardown operations")
        bucket_list = s3_test_obj.bucket_list()[1]
        s3cmd_buckets = [
            bucket for bucket in bucket_list if s3cmd_cnf["common_cfg"]["bucket_name_prefix"] in bucket]
        self.log.info("Buckets to be deleted: {}".format(s3cmd_buckets))
        if s3cmd_buckets:
            self.log.info("Deleting buckets...")
            s3_test_obj.delete_multiple_buckets(s3cmd_buckets)
            self.log.info("Deleted buckets")
        file_list = os.listdir(os.getcwd())
        for file in file_list:
            if file.startswith(common_cfg["file_prefix"]):
                S3H_OBJ.remove_file(file)
        self.log.info("ENDED: Teardown Operations")

    def execute_command(self, cmd):
        """
        This function will execute the specified command and validate it's output.
        :param str cmd: Command to be executed.
        :return: (Boolean, Command Output)
        :rtype: tuple
        """
        self.log.info("Command : {0}".format(cmd))
        proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, encoding="utf-8")
        output = proc.communicate()
        self.log.debug("Output of command execution : {}".format(output))
        if proc.returncode != 0:
            return False, str(output)
        else:
            return True, output

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2309(self):
        """
        create multiple bucket using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info("STARTED: create multiple bucket using s3cmd client")
        test_cfg = s3cmd_cnf["common_cfg"]
        for i in range(2):
            bucket_name = test_cfg["bucket_name"].format(time.time())
            bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
                bucket_name)
            self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
            cmd_arguments = [bucket_url]
            command = s3cmd_test_obj.command_formatter(
                s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
            resp = self.execute_command(command)
            assert_true(resp[0], resp[1])
            self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp[1])
            self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("ENDED: create multiple bucket using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2311(self):
        """
        max no of buckets supported using s3cmd
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info("STARTED: max no of buckets supported using s3cmd")
        test_cfg = s3cmd_cnf["common_cfg"]
        bucket_count = s3cmd_cnf["common_cfg"]["count_bkt"]
        for i in range(bucket_count):
            bucket_name = test_cfg["bucket_name"].format(time.time())
            bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
                bucket_name)
            retVal, out = self.execute_command("s3cmd ls")
            assert_true(retVal, out)
            bucket_list = out[0].split('\n')
            self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
            cmd_arguments = [bucket_url, "-c /root/.s3cfg"]
            command = s3cmd_test_obj.command_formatter(
                s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
            resp = self.execute_command(command)
            try:
                if len(bucket_list) > s3cmd_cnf["common_cfg"]["count_bkt"]:
                    self.assertFalse(resp[0], resp[1])
            except:
                self.log.info("skipping this exception as this is not implemented yet as mentioned in tc")
            else:
                assert_true(resp[0], resp[1])
                self.assertIn(s3cmd_cnf["test_2311"]["success_msg"].format(bucket_url), str(resp[1]), resp[1])
                self.log.info(
                    "STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("ENDED: max no of buckets supported using s3cmd")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2312(self):
        """
        Delete empty bucket using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info("STARTED: Delete empty bucket using s3cmd client")
        test_cfg = s3cmd_cnf["common_cfg"]
        bucket_name = test_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(s3cmd_cnf["test_2312"]
                         ["success_msg_crt"].format(bucket_url), str(resp[1]), resp[1])
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 Deleting bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2312"]["remove_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(s3cmd_cnf["test_2312"]
                         ["success_msg_del"].format(bucket_url), str(resp[1]), resp[1])
        self.log.info("STEP: 1 Bucket was deleted {}".format(bucket_name))
        self.log.info("ENDED: Delete empty bucket using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2308(self):
        """
        create bucket using s3cmd
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info("STARTED: create bucket using s3cmd")
        test_cfg = s3cmd_cnf["test_2308"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 Listing buckets")
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2308"]["list_bucket"], )
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        bucket_list = resp[1][0].split('\n')
        found = False
        for bucket in bucket_list:
            if bucket_url in bucket:
                found = True
        assert_true(found)
        self.log.info("STEP: 2 Buckets listed")
        self.log.info("ENDED: create bucket using s3cmd")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2313(self):
        """
        Delete multiple buckets using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info("STARTED: Delete multiple buckets using s3cmd client")
        test_cfg = s3cmd_cnf["test_2313"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url_1 = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket 1 {}".format(bucket_name))
        cmd_arguments = [bucket_url_1]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg_crt"].format(bucket_url_1), str(resp[1]), resp)
        self.log.info("STEP: 1 Created bucket 1 {}".format(bucket_name))
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url_2 = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket 2 {}".format(bucket_name))
        cmd_arguments = [bucket_url_2]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg_crt"].format(bucket_url_2), str(resp[1]), resp)
        self.log.info("STEP: 1 Created bucket 2 {}".format(bucket_name))
        self.log.info("STEP: 2 Deleting multiple buckets")
        cmd_arguments = [bucket_url_1, bucket_url_2]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2313"]["remove_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg_del"].format(bucket_url_1), str(resp[1]), resp)
        self.assertIn(test_cfg["success_msg_del"].format(bucket_url_2), str(resp[1]), resp)
        self.log.info("STEP: 2 Multiple buckets deleted")
        self.log.info("ENDED: Delete multiple buckets using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2326(self):
        """
        Create bucket with existing bucket name using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info(
            "STARTED: Create bucket with existing bucket name using s3cmd client")
        test_cfg = s3cmd_cnf["test_2326"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 Creating bucket with existing bucket name")
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        self.assertIn(test_cfg["error_msg"], str(resp[1]), resp)
        self.log.info(
            "STEP: 2 Creating bucket failed with existing bucket name")
        self.log.info(
            "ENDED: Create bucket with existing bucket name using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2310(self):
        """
        list buckets using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info("STARTED: list buckets using s3cmd client")
        test_cfg = s3cmd_cnf["test_2310"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 Listing buckets")
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2310"]["list_bucket"], )
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        bucket_list = resp[1][0].split('\n')
        found = False
        for bucket in bucket_list:
            if bucket_url in bucket:
                found = True
        assert_true(found)
        self.log.info("STEP: 2 Buckets listed")
        self.log.info("ENDED: list buckets using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2316(self):
        """
        upload object using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info("STARTED: upload object using s3cmd client")
        test_cfg = s3cmd_cnf["test_2316"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 File upload to bucket")
        filename = common_cfg["file_name"].format(int(time.time()))
        self.execute_command(test_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("ENDED: upload object using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2314(self):
        """
        delete bucket which has objects using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info(
            "STARTED: delete bucket which has objects using s3cmd client")
        test_cfg = s3cmd_cnf["test_2314"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 File upload to bucket")
        filename = common_cfg["file_name"].format(int(time.time()))
        self.execute_command(test_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Delete bucket which has file in it")
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, common_cfg["remove_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        self.assertIn(test_cfg["error_msg"], str(resp[1]), resp)
        self.log.info("STEP: 3 Delete bucket failed")
        self.log.info(
            "ENDED: delete bucket which has objects using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2320(self):
        """
        delete single object from bucket using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info(
            "STARTED: delete single object from bucket using s3cmd client")
        test_cfg = s3cmd_cnf["test_2320"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 Upload file to bucket")
        filename = common_cfg["file_name"].format(int(time.time()))
        self.execute_command(test_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Delete single file")
        cmd_arguments = ["/".join([bucket_url, filename])]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2320"]["del_obj"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp)
        self.assertIn(test_cfg["delete_msg"].format(cmd_arguments[0]), str(resp[1]), resp)
        self.log.info("STEP: 3 Single file deleted")
        self.log.info(
            "ENDED: delete single object from bucket using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2321(self):
        """
        delete multiple objects from bucket using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info(
            "STARTED: delete multiple objects from bucket using s3cmd client")
        test_cfg = s3cmd_cnf["test_2321"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 Files upload to bucket")
        filename = common_cfg["file_name"].format(int(time.time()))
        self.execute_command(test_cfg["file_creation"].format(filename))
        filename1 = common_cfg["file_name"].format(int(time.time()))
        self.execute_command(test_cfg["file_creation"].format(filename1))
        cmd_arguments = [filename, bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
        cmd_arguments = [filename1, bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 Files uploaded")
        self.log.info("STEP: 3 Delete multiple files from bucket")
        cmd_arguments = ["/".join([bucket_url, filename]),
                         "/".join([bucket_url, filename1])]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2321"]["del_obj"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp)
        self.assertIn(test_cfg["delete_msg"].format(cmd_arguments[0]), str(resp[1]), resp)
        self.assertIn(test_cfg["delete_msg"].format(cmd_arguments[1]), str(resp[1]), resp)
        self.log.info("STEP: 3 Multiple files deleted from bucket")
        self.log.info(
            "ENDED: delete multiple objects from bucket using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2317(self):
        """
        list objects using S3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info("STARTED: list objects using S3cmd client")
        test_cfg = s3cmd_cnf["test_2317"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 File upload to bucket")
        filename = common_cfg["file_name"].format(int(time.time()))
        self.execute_command(test_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Listing object in bucket")
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2317"]["list_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        assert_true("/".join([bucket_url, filename]) in str(resp[1]))
        self.log.info("STEP: 3 Object listed in bucket")
        self.log.info("ENDED: list objects using S3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2322(self):
        """
        delete all objects from bucket using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info(
            "STARTED: delete all objects from bucket using s3cmd client")
        test_cfg = s3cmd_cnf["test_2322"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 Files upload to bucket")
        filename = common_cfg["file_name"].format(int(time.time()))
        self.execute_command(test_cfg["file_creation"].format(filename))
        filename1 = common_cfg["file_name"].format(int(time.time()))
        self.execute_command(test_cfg["file_creation"].format(filename1))
        cmd_arguments = [filename, bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
        cmd_arguments = [filename1, bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 Files uploaded")
        self.log.info("STEP: 3 Deleting all files from bucket")
        cmd_arguments = [s3cmd_cnf["test_2322"]["force"],
                         s3cmd_cnf["test_2322"]["recursive"],
                         bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2322"]["rm_bkt"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp)
        expected_substring = "/".join([bucket_url, filename])
        expected_substring1 = "/".join([bucket_url, filename1])
        self.assertIn(test_cfg["delete_msg"].format(expected_substring), str(resp[1]), resp)
        self.assertIn(test_cfg["delete_msg"].format(expected_substring1), str(resp[1]), resp)
        self.log.info("STEP: 3 All files deleted from bucket")
        self.log.info("STEP: 4 Listing object in bucket")
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2322"]["list_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertNotIn(test_cfg["delete_msg"].format(expected_substring), str(resp[1]), resp)
        self.assertNotIn(test_cfg["delete_msg"].format(expected_substring1), str(resp[1]), resp)
        self.log.info("STEP: 5 Object listed in bucket")
        self.log.info(
            "ENDED: delete all objects from bucket using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2327(self):
        """
        Get various information about Buckets using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info(
            "STARTED: Get various information about Buckets using s3cmd client")
        test_cfg = s3cmd_cnf["common_cfg"]
        bucket_name = test_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(s3cmd_cnf["test_2312"]
                         ["success_msg_crt"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 Getting bucket information")
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2327"]["info"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(bucket_url, str(resp[1]), resp)
        self.assertIn(s3cmd_cnf["test_2327"]["success_msg2"], str(resp[1]), resp)
        self.assertIn(s3cmd_cnf["test_2327"]["success_msg3"], str(resp[1]), resp)
        self.assertIn(s3cmd_cnf["test_2327"]["success_msg4"], str(resp[1]), resp)
        self.assertIn(s3cmd_cnf["test_2327"]["success_msg5"], str(resp[1]), resp)
        self.assertIn(s3cmd_cnf["test_2327"]["success_msg6"], str(resp[1]), resp)
        self.assertIn(s3cmd_cnf["test_2327"]["success_msg7"], str(resp[1]), resp)
        self.log.info("STEP: 2 Got bucket information")
        self.log.info(
            "ENDED: Get various information about Buckets using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2319(self):
        """
        Get file from bucket using S3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info("STARTED: Get file from bucket using S3cmd client")
        test_cfg = s3cmd_cnf["test_2319"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 File upload to bucket")
        filename = common_cfg["file_name"].format(int(time.time()))
        self.execute_command(test_cfg["file_creation"].format(filename))
        cmd_arguments = [filename, bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 4 Get file from bucket")
        cmd_arguments = ["/".join([bucket_url, filename]),
                         s3cmd_cnf["test_2319"]["force"]]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2319"]["get"],
            cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        expected_substring = "/".join([bucket_url, filename])
        self.assertIn(test_cfg["success_msg2"].format(expected_substring), str(resp[1]), resp)
        self.assertIn(test_cfg["success_msg3"], str(resp[1]), resp)
        self.log.info("STEP: 4 Got file from bucket")
        self.log.info("ENDED: Get file from bucket using S3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2315(self):
        """
        delete bucket forcefully which has objects using s3cmd client
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info(
            "STARTED: delete bucket forefully which has objects using s3cmd client")
        test_cfg = s3cmd_cnf["test_2315"]
        bucket_name = common_cfg["bucket_name"].format(time.time())
        bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
            bucket_name)
        self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
        self.log.info("STEP: 2 Files upload to bucket")
        filename = common_cfg["file_name"].format(int(time.time()))
        self.execute_command(test_cfg["file_creation"].format(filename))
        filename1 = common_cfg["file_name"].format(int(time.time()))
        self.execute_command(test_cfg["file_creation"].format(filename1))
        cmd_arguments = [filename, bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
        cmd_arguments = [filename1, bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
        self.log.info("STEP: 2 Files uploaded")
        self.log.info("STEP: 3 Deleting bucket forcefully")
        cmd_arguments = [bucket_url,
                         s3cmd_cnf["test_2315"]["recursive"]
                         ]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2315"]["rm_bkt"], cmd_arguments)
        resp = self.execute_command(command)
        expected_substring = s3cmd_cnf["test_2315"]["success_msg2"]
        assert_true(expected_substring in str(resp[1]), resp[1])
        self.assertIn(test_cfg["success_msg_del"].format(bucket_url), str(resp[1]), resp)
        self.log.info("STEP: 3 Deleted bucket forcefully")
        self.log.info("STEP: 4 Listing object in bucket")
        cmd_arguments = [bucket_url]
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2315"]["list_bucket"], cmd_arguments)
        resp = self.execute_command(command)
        self.assertIn(test_cfg["error_msg"], str(resp[1]), resp)
        self.log.info("STEP: 5 Object listed in bucket")
        self.log.info(
            "ENDED: delete bucket forefully which has objects using s3cmd client")

    @pytest.mark.s3
    @pytest.mark.tags("")
    @CTFailOn(error_handler)
    def test_2318(self):
        """
        list all objects in all buckets using s3cmd
        :avocado: tags=s3cmd_blackbox
        """
        self.log.info("STARTED: list all objects in all buckets using s3cmd")
        test_cfg = s3cmd_cnf["common_cfg"]
        obj_list = list()
        for i in range(2):
            bucket_name = test_cfg["bucket_name"].format(time.time())
            bucket_url = s3cmd_cnf["common_cfg"]["bkt_path_format"].format(
                bucket_name)
            self.log.info("STEP: 1 Creating bucket {}".format(bucket_name))
            cmd_arguments = [bucket_url]
            command = s3cmd_test_obj.command_formatter(
                s3cmd_cnf, s3cmd_cnf["common_cfg"]["make_bucket"], cmd_arguments)
            resp = self.execute_command(command)
            assert_true(resp[0], resp[1])
            self.assertIn(test_cfg["success_msg"].format(bucket_url), str(resp[1]), resp)
            self.log.info("STEP: 1 Bucket was created {}".format(bucket_name))
            self.log.info("STEP: 2 File upload to bucket")
            filename = common_cfg["file_name"].format(int(time.time()))
            self.execute_command(
                s3cmd_cnf["test_2318"]["file_creation"].format(filename))
            cmd_arguments = [filename, bucket_url]
            command = s3cmd_test_obj.command_formatter(
                s3cmd_cnf, s3cmd_cnf["common_cfg"]["put_bucket"], cmd_arguments)
            resp = self.execute_command(command)
            assert_true(resp[0], resp[1])
            self.assertIn(common_cfg["upload_msg"], str(resp[1]), resp)
            obj_list.append("/".join([bucket_url, filename]))
            self.log.info("STEP: 2 File uploaded")
        self.log.info("STEP: 3 Listing objects in all bucket")
        command = s3cmd_test_obj.command_formatter(
            s3cmd_cnf, s3cmd_cnf["test_2318"]["list_all_buckets"])
        resp = self.execute_command(command)
        assert_true(resp[0], resp[1])
        for obj in obj_list:
            self.assertIn(obj, str(resp[1]), resp)
        self.log.info("STEP: 3 Objects listed in all bucket")
        self.log.info("ENDED: list all objects in all buckets using s3cmd")
