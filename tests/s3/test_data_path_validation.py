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

"""Data Path validation tests module"""

import time
import os
import logging
import pytest

from commons.constants import const
from commons.commands import CMD_S3BENCH
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils.config_utils import read_yaml
from commons.utils import system_utils
from commons.utils.system_utils import remove_file
from commons.utils.system_utils import run_remote_cmd
from commons.utils.system_utils import run_local_cmd
from commons.utils.assert_utils import assert_true
from commons.utils.assert_utils import assert_in
from commons.utils.assert_utils import assert_equal
from commons.utils.assert_utils import assert_is_not_none
from commons.utils.assert_utils import assert_not_in
from commons.helpers.health_helper import Health
from libs.s3 import CM_CFG
from libs.s3 import S3H_OBJ, S3_CFG
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD
from libs.s3.iam_test_lib import IamTestLib
from libs.s3.s3_acl_test_lib import S3AclTestLib
from libs.s3.s3_test_lib import S3TestLib
from scripts.s3_bench import s3bench as s3bench_obj
from config import S3_DATA_CMN_CONFIG

IAM_TEST_OBJ = IamTestLib()
ACL_OBJ = S3AclTestLib()
S3_OBJ = S3TestLib()


class TestDataPathValidation:
    """Data Path Test suite."""

    @classmethod
    def setup_class(cls):
        """
        Summary: Function will be invoked prior to each test case.

        Description: It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        teardown for cleanup
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: Setup operations")
        cls.ldap_user = LDAP_USERNAME
        cls.ldap_pwd = LDAP_PASSWD
        cls.bkt_name_prefix = "dpv"
        cls.bkt_permission = "private"
        cls.cmd_msg = "core."
        cls.acc_name_prefix = "dpv-acc"
        cls.email_suffix = "@seagate.com"
        cls.account_name = "{}{}".format(cls.acc_name_prefix, str(time.time()))
        cls.email_id = "{}{}".format(cls.account_name, cls.email_suffix)
        cls.nodes = CM_CFG["nodes"]
        cls.host = CM_CFG["nodes"][0]["host"]
        cls.uname = CM_CFG["nodes"][0]["username"]
        cls.passwd = CM_CFG["nodes"][0]["password"]
        cls.health_obj = Health(hostname=cls.host, username=cls.uname,
                                password=cls.passwd)
        cls.test_file = "bkt-dp.txt"
        cls.test_dir_path = os.path.join(
            os.getcwd(), "testdata", "TestDataPathValidation")
        cls.file_path = os.path.join(cls.test_dir_path, cls.test_file)
        if not system_utils.path_exists(cls.test_dir_path):
            system_utils.make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)
        cls.log.info("Test file path: %s", cls.file_path)
        cls.log.info(
            "Step : Install and Configure S3bench tool and validate the testcase.")
        res = s3bench_obj.setup_s3bench()
        assert_true(res, res)
        cls.log.info("ENDED: Setup operations")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        cls.log.info("STARTED: teardown test suite operations.")
        if system_utils.path_exists(cls.test_dir_path):
            system_utils.remove_dirs(cls.test_dir_path)
        cls.log.info("Cleanup test directory: %s", cls.test_dir_path)
        cls.log.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        Summary: This function will be invoked before each test case execution

        Description: It will perform prerequisite test steps if any
        """
        self.log.info("STARTED: Setup operations")
        self.random_id = str(time.time())
        self.bucket_name = "dpv-bkt{}".format(self.random_id)
        self.object_name = self.obj_prefix = "dpv-obj{}".format(self.random_id)
        self.log_file = []
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.cleanup_dir(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Summary: This function will be invoked after running each test case.

        Description: It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        self.log.info("STARTED: Teardown operations")
        resp = S3_OBJ.bucket_list()
        pref_list = [
            each_bucket for each_bucket in resp[1] if each_bucket.startswith(
                self.bkt_name_prefix)]
        for bucket in pref_list:
            ACL_OBJ.put_bucket_acl(
                bucket, acl=self.bkt_permission)
        if pref_list:
            resp = S3_OBJ.delete_multiple_buckets(pref_list)
            assert_true(resp[0], resp[1])
        self.log.info("Deleting files created during execution")
        for file in self.log_file:
            if os.path.exists(file):
                remove_file(file)
        if os.path.exists(self.file_path):
            os.remove(self.file_path)
        self.log.info("Created files deleted")
        self.log.info("ENDED: Teardown operations")

    def create_bucket(self, bkt_name):
        """
        create a new bucket
        :param bkt_name: bucket ame
        :type test_conf: dict
        :return: bucket_name
        """
        self.log.info("Step 1: Prepare fresh setup with EES/EOS stack")
        self.log.info("Step 2: Creating a bucket with name : %s", bkt_name)
        res = S3_OBJ.create_bucket(bkt_name)
        assert_true(res[0], res)
        assert_in(bkt_name, res[1], res)

        return bkt_name

    def put_object(self, object_name, bucket_name, obj_size, bs="1M"):
        """
        upload a given size object in already created bucket
        :param obj_size: object size
        :param object_name: NAme of object
        :param bucket_name: bucket in which object need to be uploaded
        :type bucket_name: str
        :return: None
        """
        self.log.info("Upload object of size : %s", obj_size)
        resp = system_utils.create_file(
            fpath=self.file_path,
            count=obj_size,
            b_size=bs)
        self.log.info(resp)
        assert_true(resp[0], resp[1])
        res = S3_OBJ.put_object(bucket_name,
                                object_name,
                                self.file_path)
        assert_true(res[0], res[1])

    def run_s3bench(self, obj_prefix, bucket):
        """
        concurrent users operations using S3bench
        yum install go
        go get github.com/igneous-systems/s3bench
        git clone https://github.com/igneous-systems/s3bench at /root/go/src/
        :param obj_prefix: object prefix
        :param bucket: already created bucket name
        :type bucket: str
        :return: None
        """
        self.log.info("concurrent users TC using S3bench")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        cmd = CMD_S3BENCH.format(
            access_key,
            secret_key,
            bucket,
            S3_CFG["s3_url"],
            100,
            100,
            obj_prefix,
            "4Kb")
        resp = run_local_cmd(cmd)
        self.log.debug(resp)
        assert_true(resp[0], resp[1])
        assert_is_not_none(resp[1], resp)
        resp_split = resp[1].split("\\n")
        resp_filtered = [i for i in resp_split if 'Number of Errors' in i]
        for response in resp_filtered:
            self.log.debug(response)
            assert_equal(int(response.split(":")[1].strip()), 0, response)

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8735')
    @pytest.mark.parametrize("obj_size", 1)
    @CTFailOn(error_handler)
    def test_1696(self, obj_size):
        """Validate Data-Path on fresh system with 1 byte object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 byte object size")
        bucket = self.create_bucket(self.bucket_name)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size)
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 byte object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8736')
    @pytest.mark.parametrize("obj_size", 1000)
    @CTFailOn(error_handler)
    def test_1697(self, obj_size):
        """Validate Data-Path on fresh system with 1 KB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 KB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size)
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 KB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8737')
    @pytest.mark.parametrize("obj_size", 1)
    @CTFailOn(error_handler)
    def test_1698(self, obj_size):
        """Validate Data-Path on fresh system with 1 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 MB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, bs="1M")
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 MB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8738')
    @pytest.mark.parametrize("obj_size", 10)
    @CTFailOn(error_handler)
    def test_1699(self, obj_size):
        """Validate Data-Path on fresh system with 10 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 10 MB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, bs="1M")
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 10 MB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8739')
    @pytest.mark.parametrize("obj_size", 100)
    @CTFailOn(error_handler)
    def test_1700(self, obj_size):
        """Validate Data-Path on fresh system with 100 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 100 MB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, bs="1M")
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 100 MB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8740')
    @pytest.mark.parametrize("obj_size", 1000)
    @CTFailOn(error_handler)
    def test_1701(self, obj_size):
        """Validate Data-Path on fresh system with 1 GB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 GB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, bs="1M")
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 GB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8741')
    @pytest.mark.parametrize("obj_size", 10000)
    @CTFailOn(error_handler)
    def test_1702(self, obj_size):
        """Validate Data-Path on fresh system with 10 GB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 10 GB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, bs="1M")
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 10 GB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8742')
    @CTFailOn(error_handler)
    def test_1703(self):
        """Validate Data-Path on loaded system with 1 byte object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 byte object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.run_s3bench(self.obj_prefix, bucket)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=1)
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 byte object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8743')
    @pytest.mark.parametrize("obj_size", 1)
    @CTFailOn(error_handler)
    def test_1704(self, obj_size):
        """Validate Data-Path on loaded system with 1 KB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 KB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.run_s3bench(self.obj_prefix, bucket)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size)
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 KB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8744')
    @pytest.mark.parametrize("obj_size", 1)
    @CTFailOn(error_handler)
    def test_1705(self, obj_size):
        """Validate Data-Path on loaded system with 1 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 MB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.run_s3bench(self.obj_prefix, bucket)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, bs="1M")
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 MB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8745')
    @pytest.mark.parametrize("obj_size", 10)
    @CTFailOn(error_handler)
    def test_1706(self, obj_size):
        """Validate Data-Path on loaded system with 10 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 10 MB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.run_s3bench(self.obj_prefix, bucket)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, bs="1M")
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 10 MB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8746')
    @pytest.mark.parametrize("obj_size", 100)
    @CTFailOn(error_handler)
    def test_1707(self, obj_size):
        """Validate Data-Path on loaded system with 100 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 100 MB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.run_s3bench(self.obj_prefix, bucket)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, bs="1M")
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 100 MB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8729')
    @pytest.mark.parametrize("obj_size", 1000)
    @CTFailOn(error_handler)
    def test_1708(self, obj_size):
        """Validate Data-Path on loaded system with 1 GB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 GB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.run_s3bench(self.obj_prefix, bucket)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, bs="1M")
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 GB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8730')
    @pytest.mark.parametrize("obj_size", 10000)
    @CTFailOn(error_handler)
    def test_1709(self, obj_size):
        """Validate Data-Path on loaded system with 10 GB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 10 GB object size")
        bucket = self.create_bucket(bkt_name=self.bucket_name)
        self.run_s3bench(self.obj_prefix, bucket)
        self.put_object(object_name=self.object_name, bucket_name=bucket,
                        obj_size=obj_size, bs="1M")
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 10 GB object size")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8731')
    @pytest.mark.parametrize("obj_size", 8388608)
    @CTFailOn(error_handler)
    def test_1745(self, obj_size):
        """Test gradual increase of concurrent client sessions with single client on single bucket."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with single client on single bucket")
        self.log.info("Step 1: Create bucket with name %s.", self.bucket_name)
        resp = S3_OBJ.create_bucket(self.bucket_name)
        assert_true(resp[0], resp[1])
        resp = S3_OBJ.bucket_list()
        assert_in(self.bucket_name, resp[1], resp[1])
        self.log.info("Step 1: Successfully created bucket.")
        self.log.info(
            "Step 2: Start concurrent I/O with 100 client and "
            "gradually increase request.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for request_load in S3_DATA_CMN_CONFIG["test_1745"]["requests"]:
            self.log.info("I/O with %s request", request_load)
            res = s3bench_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=self.bucket_name,
                end_point=S3_CFG["s3_url"],
                num_clients=1,
                num_sample=request_load,
                obj_name_pref=self.object_name,
                obj_size=obj_size,
                skip_cleanup=True,
                verbose=True)
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(
            "Step 2: Successfully performed concurrent I/O with 100 client and"
            "gradually increasing requests.")
        self.log.info("Step 3: checking system stability")
        res = self.health_obj.is_motr_online()
        assert_true(res, f"Failed to check is_motr_online: resp: {res}")
        cmd_msg = self.cmd_msg
        for cmd in const.CRASH_COMMANDS[0]:
            for nid in range(len(self.nodes)):
                res_cmd = run_remote_cmd(cmd,
                                         CM_CFG["nodes"][nid]["host"],
                                         CM_CFG["nodes"][nid]["username"],
                                         CM_CFG["nodes"][nid]["password"])
                assert_not_in(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with single client on single bucket")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8732')
    @pytest.mark.parametrize("obj_size", 8388608)
    @CTFailOn(error_handler)
    def test_1746(self, obj_size):
        """Test gradual increase of concurrent client sessions with multiple clients on single buckets."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")
        self.log.info("Step 1: Create bucket with name %s.", self.bucket_name)
        resp = S3_OBJ.create_bucket(self.bucket_name)
        assert_true(resp[0], resp[1])
        resp = S3_OBJ.bucket_list()
        assert_in(self.bucket_name, resp[1], resp[1])
        self.log.info("Step 1: Successfully created bucket.")
        self.log.info(
            "Step 2: Start concurrent I/O with multiple client increasing "
            "request on single bucket.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for client, request_load in zip(
                S3_DATA_CMN_CONFIG["test_1746"]["num_clients"],
                S3_DATA_CMN_CONFIG["test_1746"]["requests"]):
            res = s3bench_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=self.bucket_name,
                end_point=S3_CFG["s3_url"],
                num_clients=client,
                num_sample=request_load,
                obj_name_pref=self.object_name,
                obj_size=obj_size,
                skip_cleanup=True,
                verbose=True)
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(
            "Step 2: completed concurrent I/O with multiple client and increasing"
            " request on single bucket.")
        self.log.info("Step 3: checking system stability")
        res = self.health_obj.is_motr_online()
        assert_true(res, f"Failed to check is_motr_online: resp: {res}")
        cmd_msg = self.cmd_msg
        self.log.info("Crash commands: %s", const.CRASH_COMMANDS[0])
        for cmd in const.CRASH_COMMANDS[0]:
            self.log.info(cmd)
            for nid in range(len(self.nodes)):
                res_cmd = run_remote_cmd(cmd,
                                         CM_CFG["nodes"][nid]["host"],
                                         CM_CFG["nodes"][nid]["username"],
                                         CM_CFG["nodes"][nid]["password"])
                assert_not_in(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8733')
    @pytest.mark.parametrize("obj_size", 8388608)
    @CTFailOn(error_handler)
    def test_1747(self, obj_size):
        """Test gradual increase of concurrent client sessions with multiple clients on multiple buckets."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with multiple clients on multiple buckets")
        self.log.info("Step 1: Creating %s buckets.", 5)
        bkt_list = []
        for bkt in range(5):
            bucket_name = "{}{}".format(self.bkt_name_prefix, time.time())
            resp = S3_OBJ.create_bucket(bucket_name)
            assert_true(resp[0], resp[1])
            bkt_list.append(bucket_name)
        resp = S3_OBJ.bucket_list()
        assert_in(bkt_list[0], resp[1], resp[1])
        self.log.info("Step 1: Successfully created buckets: %s.", bkt_list)
        self.log.info(
            "Step 2: Start concurrent I/O with increasing client and "
            "request on multiple buckets.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for client, request_load, bkt in zip(
                S3_DATA_CMN_CONFIG["test_1747"]["num_clients"],
                S3_DATA_CMN_CONFIG["test_1747"]["requests"], bkt_list):
            res = s3bench_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=bkt,
                end_point=S3_CFG["s3_url"],
                num_clients=client,
                num_sample=request_load,
                obj_name_pref=self.object_name,
                obj_size=obj_size,
                skip_cleanup=True,
                verbose=True)
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(
            "Step 2: Completed concurrent I/O with increasing client and"
            " request on multiple buckets.")
        self.log.info("Step 3: checking system stability")
        res = self.health_obj.is_motr_online()
        assert_true(res, f"Failed to check is_motr_online: resp: {res}")
        cmd_msg = self.cmd_msg
        for cmd in const.CRASH_COMMANDS[0]:
            for nid in range(len(self.nodes)):
                res_cmd = run_remote_cmd(cmd,
                                         CM_CFG["nodes"][nid]["host"],
                                         CM_CFG["nodes"][nid]["username"],
                                         CM_CFG["nodes"][nid]["password"])
                assert_not_in(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with multiple clients on multiple buckets")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-8734')
    @pytest.mark.parametrize("obj_size", 8388608)
    @CTFailOn(error_handler)
    def test_1748(self, obj_size):
        """Test burst I/O with single client on single bucket."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")
        self.log.info("Step 1: Create bucket.")
        bkt_list = []
        for bkt in range(2):
            bucket_name = "{}{}".format(self.bkt_name_prefix, time.time())
            resp = S3_OBJ.create_bucket(bucket_name)
            assert_true(resp[0], resp[1])
            bkt_list.append(bucket_name)
        resp = S3_OBJ.bucket_list()
        assert_in(bkt_list[0], resp[1], resp[1])
        self.log.info("Step 1: Successfully created bucket.")
        self.log.info(
            "Step 2: Start concurrent I/O with increasing client and request.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for client, request_load, bkt in zip(
                S3_DATA_CMN_CONFIG["test_1748"]["num_clients"],
                S3_DATA_CMN_CONFIG["test_1748"]["requests"], bkt_list):
            res = s3bench_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=bkt,
                end_point=S3_CFG["s3_url"],
                num_clients=client,
                num_sample=request_load,
                obj_name_pref=self.object_name,
                obj_size=obj_size,
                skip_cleanup=True,
                verbose=True)
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(
            "Step 2: Start concurrent I/O with increasing client and request.")
        self.log.info("Step 3: checking system stability")
        res = self.health_obj.is_motr_online()
        assert_true(res, f"Failed to check is_motr_online: resp: {res}")
        cmd_msg = self.cmd_msg
        for cmd in const.CRASH_COMMANDS[0]:
            for nid in range(len(self.nodes)):
                res_cmd = run_remote_cmd(cmd,
                                         CM_CFG["nodes"][nid]["host"],
                                         CM_CFG["nodes"][nid]["username"],
                                         CM_CFG["nodes"][nid]["password"])
                assert_not_in(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")
