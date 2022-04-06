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
"""Test suite for awscli s3api operations."""

import os
import time
import json
import logging
import pytest

from commons.constants import S3_ENGINE_RGW
from commons.params import TEST_DATA_FOLDER
from commons import commands
from commons.ct_fail_on import CTFailOn
from commons.exceptions import CTException
from commons.errorcodes import error_handler
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils.s3_utils import assert_s3_err_msg
from commons import error_messages as errmsg
from config.s3 import S3_CFG
from config import CMN_CFG
from libs.s3.s3_test_lib import S3TestLib


class TestAwsCliS3Api:
    """Blackbox AWS CLI S3API Testsuite."""

    # pylint: disable=attribute-defined-outside-init, too-many-instance-attributes
    def setup_method(self):
        """
        Setup all the states required for execution of each test case in this test suite.

        It is performing below operations as pre-requisites
            - Initializes common variables
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED : Setup operations at test suit level")
        self.s3t_obj = S3TestLib()
        assert_utils.assert_true(system_utils.path_exists(S3_CFG["aws_config_path"]),
                                 "config path not exists: {}".format(S3_CFG["aws_config_path"]))
        self.log.info("ENDED : Setup operations at test suit level")
        self.bucket_name = "{}{}".format("blackboxs3bkt", time.perf_counter_ns())
        self.object_name = "{}{}".format("blackboxs3obj", time.perf_counter_ns())
        self.file_name = "{}{}".format("blackboxs3file", time.perf_counter_ns())
        self.test_dir_path = os.path.join(os.getcwd(), TEST_DATA_FOLDER, "TestAwsCliS3Api")
        if not os.path.exists(self.test_dir_path):
            os.makedirs(self.test_dir_path)
        self.file_path = os.path.join(self.test_dir_path, self.file_name)
        self.log.info("Created path: %s", self.test_dir_path)
        self.log.info("Test file path: %s", self.file_path)
        self.downloaded_file = "{}{}".format("get_blackboxs3obj", time.perf_counter_ns())
        self.downloaded_file_path = os.path.join(self.test_dir_path, self.downloaded_file)
        self.buckets_list = list()
        self.aws_buckets_list = list()
        self.log.info("ENDED : Setup operations at test function level")

    def teardown_method(self):
        """
        Teardown any state that was previously setup with a setup_method.

        It is performing below operations as pre-requisites
            - Deletes bucket created during test execution
            - Remove local files created during test execution
        """
        self.log.info("STARTED : Teardown operations at test function level")
        self.log.info(self.buckets_list)
        for bucket_name in self.buckets_list:
            resp = self.s3t_obj.delete_bucket_awscli(bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        if system_utils.path_exists(self.file_path):
            system_utils.remove_file(self.file_path)
        if system_utils.path_exists(self.downloaded_file_path):
            system_utils.remove_file(self.downloaded_file_path)
        self.log.info("ENDED : Teardown operations at test function level")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7113")
    @CTFailOn(error_handler)
    def test_create_single_bucket_2328(self):
        """create single bucket using aws cli."""
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.buckets_list.append(self.bucket_name)
        self.log.info("Successfully create single bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7114")
    @CTFailOn(error_handler)
    def test_create_multiple_bucket_2329(self):
        """Create multiple buckets using aws cli."""
        for i in range(2):
            bucket_name = "-".join([self.bucket_name, str(i)])
            self.buckets_list.append(bucket_name)
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=' '.join(self.buckets_list))
        if not resp[0]:
            self.buckets_list = list()
        assert_utils.assert_false(resp[0], resp[1])
        self.log.info("Failed to create multiple buckets at a time using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7115")
    @CTFailOn(error_handler)
    def test_list_buckets_2330(self):
        """list buckets using aws cli."""
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.buckets_list.append(self.bucket_name)
        cmd = commands.CMD_AWSCLI_LIST_BUCKETS + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.bucket_name)
        self.log.info("Successfully listed buckets using awscli")

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7116")
    @CTFailOn(error_handler)
    def test_create_max_buckets_2331(self):
        """max no(1000) of buckets supported using aws cli."""
        self.log.info("Step 1 : Delete all existing buckets for the user")
        resp = self.s3t_obj.delete_all_buckets()
        self.log.info(resp)
        assert resp[0], resp[1]
        self.log.info("Step 2 : Start creating buckets:")
        for i in range(1000):
            bucket_name = "blackboxs3bkt-{}-{}".format(i, time.perf_counter_ns())
            resp = self.s3t_obj.create_bucket_awscli(bucket_name=bucket_name)
            assert_utils.assert_true(resp[0], resp[1])
            self.buckets_list.append(bucket_name)
        self.log.info("Successfully created max no. of buckets using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7117")
    @CTFailOn(error_handler)
    def test_delete_empty_bucket_2332(self):
        """delete empty bucket using aws cli."""
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3t_obj.delete_bucket_awscli(bucket_name=self.bucket_name)
        if not resp[0]:
            self.buckets_list.append(self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Successfully deleted empty bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7118")
    @CTFailOn(error_handler)
    def test_delete_non_empty_bucket_2333(self):
        """delete bucket which has objects using aws cli."""
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.buckets_list.append(self.bucket_name)
        file_status, output = system_utils.create_file(fpath=self.file_path, count=1)
        if file_status:
            cmd = commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path, self.bucket_name, self.object_name) + self.s3t_obj.cmd_endpoint
            resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
            assert_utils.assert_true(resp[0], resp[1])
        else:
            self.log.info("File is not created because: %s ", output)
        resp = self.s3t_obj.delete_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], errmsg.S3_BKT_NOT_EMPTY_ERR)
        self.buckets_list = list()
        self.log.info("Failed to delete bucket having objects in it")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7119")
    @CTFailOn(error_handler)
    def test_head_bucket_2334(self):
        """Verify HEAD bucket using aws client."""
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list.append(self.bucket_name)
        cmd = commands.CMD_AWSCLI_HEAD_BUCKET.format(self.bucket_name) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Successfully verified head bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7120")
    @CTFailOn(error_handler)
    def test_bucket_location_2335(self):
        """Verification of bucket location using aws."""
        if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
            location = '"LocationConstraint": "default"'
        else:
            location = '"LocationConstraint": "US"'
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list.append(self.bucket_name)
        cmd = commands.CMD_AWSCLI_GET_BUCKET_LOCATION.format(self.bucket_name) \
            + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], location)
        self.log.info("Successfully verified bucket location using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7121")
    @CTFailOn(error_handler)
    def test_create_duplicate_bucket_2336(self):
        """create bucket using existing bucket name using aws cli."""
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list.append(self.bucket_name)
        try:
            resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            assert_s3_err_msg(errmsg.RGW_ERR_DUPLICATE_BKT_NAME,
                              errmsg.CORTX_ERR_DUPLICATE_BKT_NAME,
                              CMN_CFG["s3_engine"], error)
        self.log.info("Failed to create bucket using existing bucket name")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7122")
    @CTFailOn(error_handler)
    def test_delete_bucket_forcefully_2337(self):
        """Delete bucket forcefully which has objects using aws cli."""
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list.append(self.bucket_name)
        status, output = system_utils.create_file(fpath=self.file_path, count=1)
        if status:
            cmd = commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path, self.bucket_name, self.object_name) + self.s3t_obj.cmd_endpoint
            resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
            assert_utils.assert_true(resp[0], resp[1])
        else:
            self.log.info("file is not created because: %s", output)
        resp = self.s3t_obj.delete_bucket_awscli(bucket_name=self.bucket_name, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list = list()
        self.log.info("Successfully deleted bucket having objects in it")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7123")
    @CTFailOn(error_handler)
    def test_list_objects_2338(self):
        """list objects in bucket using AWS."""
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list.append(self.bucket_name)
        file_status, output = system_utils.create_file(fpath=self.file_path, count=1)
        if file_status:
            cmd = commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path, self.bucket_name, self.object_name) + self.s3t_obj.cmd_endpoint
            resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
            assert_utils.assert_true(resp[0], resp[1])
        else:
            self.log.info("File is not created because: %s", output)
        cmd = commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)
        self.log.info("Successfully listed objects from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7124")
    @CTFailOn(error_handler)
    def test_delete_single_object_2339(self):
        """delete single object using aws cli."""
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list.append(self.bucket_name)
        file_status, output = system_utils.create_file(fpath=self.file_path, count=1)
        if file_status:
            cmd = commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path, self.bucket_name, self.object_name) + self.s3t_obj.cmd_endpoint
            resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
            assert_utils.assert_true(resp[0], resp[1])
        else:
            self.log.info("File is not created because: %s", output)
        cmd = commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_exact_string(resp[1], self.object_name)
        cmd = commands.CMD_AWSCLI_REMOVE_OBJECTS.format(self.bucket_name, self.object_name) \
            + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)
        self.log.info("Successfully deleted object from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7125")
    @CTFailOn(error_handler)
    def test_delete_multiple_objects_2340(self):
        """delete multiple object using aws cli."""
        object_list = list()
        object_count = 3
        file_status, output = system_utils.create_file(fpath=self.file_path, count=1)
        assert_utils.assert_true(file_status, output)
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list.append(self.bucket_name)
        for i in range(object_count):
            object_name = "".join([self.file_name, str(i)])
            cmd = commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path, self.bucket_name, object_name) + self.s3t_obj.cmd_endpoint
            resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
            assert_utils.assert_true(resp[0], resp[1])
            cmd = commands.CMD_AWSCLI_LIST_OBJECTS.format(
                self.bucket_name) + self.s3t_obj.cmd_endpoint
            resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
            assert_utils.assert_exact_string(resp[1], object_name)
            object_list.append(object_name)
        delete_objs_cmd = commands.CMD_AWSCLI_REMOVE_OBJECTS.format(self.bucket_name, "")
        delete_objs_cmd = " ".join([delete_objs_cmd,
                                    commands.CMD_AWSCLI_RECURSIVE_FLAG,
                                    commands.CMD_AWSCLI_EXCLUDE_FLAG.format("*"),
                                    commands.CMD_AWSCLI_INCLUDE_FLAG.format(object_list[0]),
                                    commands.CMD_AWSCLI_INCLUDE_FLAG.format(object_list[1]),
                                    ])
        delete_objs_cmd = delete_objs_cmd + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=delete_objs_cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], object_list[0])
        assert_utils.assert_exact_string(resp[1], object_list[1])
        self.log.info("Successfully deleted multiple objects from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7126")
    @CTFailOn(error_handler)
    def test_delete_all_objects_2341(self):
        """delete max no of objects using aws cli."""
        object_list = list()
        object_count = 3
        file_status, output = system_utils.create_file(fpath=self.file_path, count=1)
        assert_utils.assert_true(file_status, output)
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list.append(self.bucket_name)
        for i in range(object_count):
            self.object_name = "".join([self.file_name, str(i)])
            cmd = commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path, self.bucket_name, self.object_name) + self.s3t_obj.cmd_endpoint
            resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
            assert_utils.assert_true(resp[0], resp[1])
            cmd = commands.CMD_AWSCLI_LIST_OBJECTS.format(
                self.bucket_name) + self.s3t_obj.cmd_endpoint
            resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
            assert_utils.assert_exact_string(resp[1], self.object_name)
            object_list.append(self.object_name)
        delete_objs_cmd = " ".join([commands.CMD_AWSCLI_REMOVE_OBJECTS.format(
            self.bucket_name, ""), commands.CMD_AWSCLI_RECURSIVE_FLAG])
        delete_objs_cmd = delete_objs_cmd + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=delete_objs_cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        for obj in object_list:
            assert_utils.assert_exact_string(resp[1], obj)
        self.log.info("Successfully deleted all objects from bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7127")
    @CTFailOn(error_handler)
    def test_multipart_upload_2342(self):
        """update object of large size of(10gb) using aws cli. No of parts is 20."""
        split_parts = system_utils.split_file(self.file_path, 10000, 20)
        mpu_parts_list = [part["Output"] for part in split_parts]
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list.append(self.bucket_name)
        self.log.info("Creating Multipart upload")
        cmd = commands.CMD_AWSCLI_CREATE_MULTIPART_UPLOAD.format(
            self.bucket_name, self.object_name) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        mpu_upload_id = resp[1][resp[1].find("{"):resp[1].rfind("}") + 1]
        mpu_upload_id = json.loads(mpu_upload_id.replace("\\n", ""))["UploadId"]
        self.log.info("Listing Multipart uploads")
        cmd = commands.CMD_AWSCLI_LIST_MULTIPART_UPLOADS.format(
            self.bucket_name) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], mpu_upload_id)
        self.log.info("Uploading parts to bucket")
        for i in range(20):
            cmd = commands.CMD_AWSCLI_UPLOAD_PARTS.format(self.bucket_name, self.object_name, i + 1,
                                                          mpu_parts_list[i],
                                                          mpu_upload_id) + self.s3t_obj.cmd_endpoint
            upload_parts = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
            assert_utils.assert_true(upload_parts[0], upload_parts[1])
        self.log.info("Listing uploaded parts")
        cmd = commands.CMD_AWSCLI_LIST_PARTS.format(
            self.bucket_name, self.object_name, mpu_upload_id) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        parts_str = resp[1][resp[1].find("{"):resp[1].rfind("}") + 1]
        self.log.info(parts_str.replace("\\n", "").replace("\\\\", "\\"))
        list_parts = json.loads(parts_str.replace("\\n", "").replace("\\\\", "\\"))["Parts"]
        part_data = dict()
        part_data["Parts"] = list()
        for i in range(20):
            part_data["Parts"].append(
                {"PartNumber": list_parts[i]["PartNumber"], "ETag": list_parts[i]["ETag"]})
        self.log.info("Creating json file for multipart upload")
        json_file = "parts.json"
        with open(json_file, "w") as file:
            json.dump(part_data, file)
        self.log.info("Completing multipart upload")
        cmd = commands.CMD_AWSCLI_COMPLETE_MULTIPART.format(
            json_file,
            self.bucket_name,
            self.object_name,
            mpu_upload_id) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        cmd = commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_exact_string(resp[1], self.object_name)
        system_utils.remove_file(json_file)
        for part in mpu_parts_list:
            system_utils.remove_file(part)
        self.log.info("Successfully completed multipart upload of a large file")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7128")
    @CTFailOn(error_handler)
    def test_copy_object_to_bucket_2343(self):
        """copy object from bucket using aws cli."""
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list.append(self.bucket_name)
        file_status, output = system_utils.create_file(fpath=self.file_path, count=1)
        if file_status:
            cmd = commands.CMD_AWSCLI_PUT_OBJECT.format(
                self.file_path, self.bucket_name, self.object_name) + self.s3t_obj.cmd_endpoint
            resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
            assert_utils.assert_true(resp[0], resp[1])
        else:
            self.log.info("File is not created because: %s", output)
        cmd = commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)
        self.log.info("Successfully copied objects to bucket using awscli")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-7130")
    @CTFailOn(error_handler)
    def test_download_object_from_bucket_2344(self):
        """download an object using aws cli."""
        resp = self.s3t_obj.create_bucket_awscli(bucket_name=self.bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.aws_buckets_list.append(self.bucket_name)
        file_status, output = system_utils.create_file(fpath=self.file_path, count=1)
        assert_utils.assert_true(file_status, output)
        before_checksum = system_utils.calculate_checksum(self.file_path)
        self.log.info("File path: %s, before_checksum: %s", self.file_path, before_checksum)
        self.log.info("Uploading objects to bucket using awscli")
        cmd = commands.CMD_AWSCLI_PUT_OBJECT.format(self.file_path, self.bucket_name,
                                                    self.object_name) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        cmd = commands.CMD_AWSCLI_LIST_OBJECTS.format(self.bucket_name) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], self.object_name)
        self.log.info("Downloading object from bucket using awscli")
        cmd = commands.CMD_AWSCLI_DOWNLOAD_OBJECT.format(
            self.bucket_name,
            self.object_name,
            self.downloaded_file_path) + self.s3t_obj.cmd_endpoint
        resp = system_utils.run_local_cmd(cmd=cmd, chk_stderr=True)
        assert_utils.assert_true(resp[0], resp[1])
        download_checksum = system_utils.calculate_checksum(self.downloaded_file_path)
        self.log.info("File path: %s, before_checksum: %s", self.downloaded_file_path,
                      before_checksum)
        assert_utils.assert_equals(
            before_checksum,
            download_checksum,
            f"Downloaded file is not same as uploaded: {before_checksum}, {download_checksum}")
        system_utils.remove_file(self.downloaded_file_path)
        self.log.info("Successfully downloaded object from bucket using awscli")
