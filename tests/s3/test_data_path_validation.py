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
from libs.s3 import S3H_OBJ
from libs.s3 import CM_CFG
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD
from libs.s3.iam_test_lib import IamTestLib
from libs.s3.s3_acl_test_lib import S3AclTestLib
from commons.constants import const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import remove_file
from commons.utils.system_utils import run_remote_cmd
from commons.utils.system_utils import run_local_cmd
from commons.utils.assert_utils import assert_true
from commons.utils.assert_utils import assert_in
from commons.utils.assert_utils import assert_equal
from commons.utils.assert_utils import assert_is_not_none
from commons.utils.assert_utils import assert_not_in
from commons.helpers.health_helper import Health
from scripts.s3_bench import s3bench as s3bench_obj

IAM_TEST_OBJ = IamTestLib()
ACL_OBJ = S3AclTestLib()
S3_HEALTH = Health
DATA_PATH_CFG = read_yaml("config/s3/test_data_path_validate.yaml")[1]


class TestDataPathValidation():
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
        cls.account_name = "{}{}".format(
            DATA_PATH_CFG["data_path"]["acc_name_prefix"],
            str(time.time()))
        cls.email_id = "{}{}".format(
            cls.account_name,
            DATA_PATH_CFG["data_path"]["email_suffix"])
        cls.nodes = CM_CFG["nodes"]
        cls.log.info("ENDED: Setup operations")

    def setup_method(self):
        """
        Summary: This function will be invoked before each test case execution

        Description: It will perform prerequisite test steps if any
        """
        self.log.info("STARTED: Setup operations")
        self.random_id = str(time.time())
        self.log_file = []
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Summary: This function will be invoked after running each test case.

        Description: It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        self.log.info("STARTED: Teardown operations")
        resp = S3H_OBJ.bucket_list()
        pref_list = [
            each_bucket for each_bucket in resp[1] if each_bucket.startswith(
                DATA_PATH_CFG["data_path"]["bkt_name_prefix"])]
        for bucket in pref_list:
            ACL_OBJ.put_bucket_acl(
                bucket, acl=DATA_PATH_CFG["data_path"]["bkt_permission"])
        S3H_OBJ.delete_multiple_buckets(pref_list)
        self.log.info("Deleting IAM accounts")
        acc_list = IAM_TEST_OBJ.list_accounts_s3iamcli(
            self.ldap_user, self.ldap_pwd)[1]
        self.log.info(acc_list)
        all_acc = [acc["AccountName"]
                   for acc in acc_list if self.account_name in acc["AccountName"]]
        self.log.info(all_acc)
        for acc_name in all_acc:
            IAM_TEST_OBJ.reset_access_key_and_delete_account_s3iamcli(acc_name)
        self.log.info("Deleted IAM accounts successfully")
        self.log.info("Deleting files created during execution")
        for file in self.log_file:
            if os.path.exists(file):
                remove_file(file)
        if os.path.exists(DATA_PATH_CFG["data_path"]["file_path"]):
            os.remove(DATA_PATH_CFG["data_path"]["file_path"])
        self.log.info("Created files deleted")
        self.log.info("ENDED: Teardown operations")

    def create_bucket(self, test_conf):
        """
        create a new bucket
        :param test_conf: test config
        :type test_conf: dict
        :return: bucket_name
        """
        self.log.info("Step 1: Prepare fresh setup with EES/EOS stack")
        bucket_name = "{}{}".format(test_conf["bucket_name"],
                                    str(int(time.time())))
        self.log.info("Step 2: Creating a bucket with name : %s", bucket_name)
        res = S3H_OBJ.create_bucket(bucket_name)
        assert_in(bucket_name, res[1], res[1])
        return bucket_name

    def put_object(self, test_conf, bucket_name, bs=1):
        """
        upload a given size object in already created bucket
        :param test_conf: test config
        :type test_conf: dict
        :param bs: byte size
        :type bs: int
        :param bucket_name: bucket in which object need to be uploaded
        :type bucket_name: str
        :return: None
        """
        self.log.info(
            "Step 3:Upload object of size : %d", test_conf["obj_size"])
        cmd = "dd if=/dev/zero of={} bs={} count={}".format(
            DATA_PATH_CFG["data_path"]["file_path"], bs, test_conf["obj_size"])
        self.log.info(cmd)
        run_local_cmd(cmd)
        res = S3H_OBJ.put_object(bucket_name,
                                test_conf["object_name"],
                                DATA_PATH_CFG["data_path"]["file_path"])
        assert_true(res[0], res[1])

    def run_s3bench(self, test_conf, bucket):
        """
        concurrent users operations using S3bench
        yum install go
        go get github.com/igneous-systems/s3bench
        git clone https://github.com/igneous-systems/s3bench at /root/go/src/
        :param test_conf: test config
        :type test_conf: dict
        :param bucket: already created bucket name
        :type bucket: str
        :return: None
        """
        self.log.info("concurrent users TC using S3bench")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        cmd = DATA_PATH_CFG["data_path"]["s3bench_cmd"].format(
            access_key,
            secret_key,
            bucket,
            DATA_PATH_CFG["data_path"]["endpoint"],
            DATA_PATH_CFG["data_path"]["clients"],
            DATA_PATH_CFG["data_path"]["samples"],
            test_conf["obj_prefix"],
            DATA_PATH_CFG["data_path"]["obj_size"])
        run_local_cmd(
            "cd {}".format(
                DATA_PATH_CFG["data_path"]["s3bench_path"]))
        resp = run_local_cmd(cmd)
        self.log.debug(resp)
        assert_is_not_none(resp[0], resp)
        resp_split = resp[0].split("\n")
        resp_filtered = [i for i in resp_split if 'Number of Errors' in i]
        for response in resp_filtered:
            self.log.debug(response)
            assert_equal(int(response.split(":")[1].strip()), 0, response)

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8735')
    @CTFailOn(error_handler)
    def test_1696(self):
        """Validate Data-Path on fresh system with 1 byte object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 byte object size")
        test_conf = DATA_PATH_CFG["test_1696"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket)
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 byte object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8736')
    @CTFailOn(error_handler)
    def test_1697(self):
        """Validate Data-Path on fresh system with 1 KB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 KB object size")
        test_conf = DATA_PATH_CFG["test_1697"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket)
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 KB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8737')
    @CTFailOn(error_handler)
    def test_1698(self):
        """Validate Data-Path on fresh system with 1 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 MB object size")
        test_conf = DATA_PATH_CFG["test_1698"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 MB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8738')
    @CTFailOn(error_handler)
    def test_1699(self):
        """Validate Data-Path on fresh system with 10 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 10 MB object size")
        test_conf = DATA_PATH_CFG["test_1699"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 10 MB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8739')
    @CTFailOn(error_handler)
    def test_1700(self):
        """Validate Data-Path on fresh system with 100 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 100 MB object size")
        test_conf = DATA_PATH_CFG["test_1700"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 100 MB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8740')
    @CTFailOn(error_handler)
    def test_1701(self):
        """Validate Data-Path on fresh system with 1 GB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 GB object size")
        test_conf = DATA_PATH_CFG["test_1701"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 GB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8741')
    @CTFailOn(error_handler)
    def test_1702(self):
        """Validate Data-Path on fresh system with 10 GB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 10 GB object size")
        test_conf = DATA_PATH_CFG["test_1702"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 10 GB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8742')
    @CTFailOn(error_handler)
    def test_1703(self):
        """Validate Data-Path on loaded system with 1 byte object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 byte object size")
        test_conf = DATA_PATH_CFG["test_1703"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket)
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 byte object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8743')
    @CTFailOn(error_handler)
    def test_1704(self):
        """Validate Data-Path on loaded system with 1 KB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 KB object size")
        test_conf = DATA_PATH_CFG["test_1704"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket)
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 KB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8744')
    @CTFailOn(error_handler)
    def test_1705(self):
        """Validate Data-Path on loaded system with 1 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 MB object size")
        test_conf = DATA_PATH_CFG["test_1705"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 MB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8745')
    @CTFailOn(error_handler)
    def test_1706(self):
        """Validate Data-Path on loaded system with 10 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 10 MB object size")
        test_conf = DATA_PATH_CFG["test_1706"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 10 MB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8746')
    @CTFailOn(error_handler)
    def test_1707(self):
        """Validate Data-Path on loaded system with 100 MB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 100 MB object size")
        test_conf = DATA_PATH_CFG["test_1707"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 100 MB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8729')
    @CTFailOn(error_handler)
    def test_1708(self):
        """Validate Data-Path on loaded system with 1 GB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 GB object size")
        test_conf = DATA_PATH_CFG["test_1708"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 GB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8730')
    @CTFailOn(error_handler)
    def test_1709(self):
        """Validate Data-Path on loaded system with 10 GB object size."""
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 10 GB object size")
        test_conf = DATA_PATH_CFG["test_1709"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 10 GB object size")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8731')
    @CTFailOn(error_handler)
    def test_1745(self):
        """Test gradual increase of concurrent client sessions with single client on single bucket."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with single client on single bucket")
        test_cfg = DATA_PATH_CFG["test_1745"]
        bucket_name = "{}{}".format(
            test_cfg["bucket_name"], time.time())
        self.log.info("Step 1: Create bucket with name %s.", bucket_name)
        resp = S3H_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        resp = S3H_OBJ.bucket_list()
        assert_in(bucket_name, resp[1], resp[1])
        self.log.info("Step 1: Successfully created bucket.")
        self.log.info(
            "Step 2: Start concurrent I/O with 100 client and "
            "gradually increase request.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for request_load in test_cfg["requests"]:
            self.log.info("I/O with %s request",request_load)
            res = s3bench_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=bucket_name,
                end_point=DATA_PATH_CFG["data_path"]["endpoint"],
                num_clients=test_cfg["num_clients"],
                num_sample=request_load,
                obj_name_pref=test_cfg["obj_name"],
                obj_size=test_cfg["s3bench_obj_size"],
                skip_cleanup=test_cfg["skip_cleanup"],
                verbose=test_cfg["verbose"])
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(
            "Step 2: Successfully performed concurrent I/O with 100 client and"
            "gradually increasing requests.")
        self.log.info("Step 3: checking system stability")
        res = S3_HEALTH.is_motr_online()
        assert_true(res[0], res[1])
        cmd_msg = DATA_PATH_CFG["data_path"]["cmd_msg"]
        commands = const.CRASH_COMMANDS
        for node, cmd in zip(self.nodes, commands):
            res_cmd = run_remote_cmd(cmd,
                                     node,
                                     CM_CFG["nodes"][node]["username"],
                                     CM_CFG["nodes"][node]["password"])
            assert_not_in(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with single client on single bucket")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8732')
    @CTFailOn(error_handler)
    def test_1746(self):
        """Test gradual increase of concurrent client sessions with multiple clients on single buckets."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")
        test_cfg = DATA_PATH_CFG["test_1746"]
        bucket_name = "{}{}".format(
            test_cfg["bucket_name"], time.time())
        self.log.info("Step 1: Create bucket with name %s.", bucket_name)
        resp = S3H_OBJ.create_bucket(bucket_name)
        assert_true(resp[0], resp[1])
        resp = S3H_OBJ.bucket_list()
        assert_in(bucket_name, resp[1], resp[1])
        self.log.info("Step 1: Successfully created bucket.")
        self.log.info(
            "Step 2: Start concurrent I/O with multiple client increasing "
            "request on single bucket.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for client, request_load in zip(
                test_cfg["num_clients"], test_cfg["requests"]):
            res = s3bench_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=bucket_name,
                end_point=DATA_PATH_CFG["data_path"]["endpoint"],
                num_clients=client,
                num_sample=request_load,
                obj_name_pref=test_cfg["obj_name"],
                obj_size=test_cfg["s3bench_obj_size"],
                skip_cleanup=test_cfg["skip_cleanup"],
                verbose=test_cfg["verbose"])
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(
            "Step 2: completed concurrent I/O with multiple client and increasing"
            " request on single bucket.")
        self.log.info("Step 3: checking system stability")
        res = S3H_OBJ.is_mero_online()
        assert_true(res[0], res[1])
        cmd_msg = DATA_PATH_CFG["data_path"]["cmd_msg"]
        commands = const.CRASH_COMMANDS
        for node, cmd in zip(self.nodes, commands):
            res_cmd = run_remote_cmd(cmd,
                                     node,
                                     CM_CFG["nodes"][node]["username"],
                                     CM_CFG["nodes"][node]["password"])
            assert_not_in(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8733')
    @CTFailOn(error_handler)
    def test_1747(self):
        """Test gradual increase of concurrent client sessions with multiple clients on multiple buckets."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with multiple clients on multiple buckets")
        test_cfg = DATA_PATH_CFG["test_1747"]
        self.log.info("Step 1: Creating %s buckets.", test_cfg['bkt_count'])
        bkt_list = []
        for bkt in range(test_cfg["bkt_count"]):
            bucket_name = "{}{}".format(
                test_cfg["bucket_name"], time.time())
            resp = S3H_OBJ.create_bucket(bucket_name)
            assert_true(resp[0], resp[1])
            bkt_list.append(bucket_name)
        resp = S3H_OBJ.bucket_list()
        assert_in(bkt_list[0], resp[1], resp[1])
        self.log.info("Step 1: Successfully created buckets: %s.", bkt_list)
        self.log.info(
            "Step 2: Start concurrent I/O with increasing client and "
            "request on multiple buckets.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for client, request_load, bkt in zip(
                test_cfg["num_clients"], test_cfg["requests"], bkt_list):
            res = s3bench_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=bkt,
                end_point=DATA_PATH_CFG["data_path"]["endpoint"],
                num_clients=client,
                num_sample=request_load,
                obj_name_pref=test_cfg["obj_name"],
                obj_size=test_cfg["s3bench_obj_size"],
                skip_cleanup=test_cfg["skip_cleanup"],
                verbose=test_cfg["verbose"])
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(
            "Step 2: Completed concurrent I/O with increasing client and"
            " request on multiple buckets.")
        self.log.info("Step 3: checking system stability")
        res = S3H_OBJ.is_mero_online()
        assert_true(res[0], res[1])
        cmd_msg = DATA_PATH_CFG["data_path"]["cmd_msg"]
        commands = const.CRASH_COMMANDS
        for node, cmd in zip(self.nodes, commands):
            res_cmd = run_remote_cmd(cmd,
                                     node,
                                     CM_CFG["nodes"][node]["username"],
                                     CM_CFG["nodes"][node]["password"])
            assert_not_in(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with multiple clients on multiple buckets")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-8734')
    @CTFailOn(error_handler)
    def test_1748(self):
        """Test burst I/O with single client on single bucket."""
        self.log.info(
            "STARTED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")
        test_cfg = DATA_PATH_CFG["test_1748"]
        self.log.info("Step 1: Create bucket.")
        bkt_list = []
        for bkt in range(test_cfg["bkt_count"]):
            bucket_name = "{}{}".format(
                test_cfg["bucket_name"], time.time())
            resp = S3H_OBJ.create_bucket(bucket_name)
            assert_true(resp[0], resp[1])
            bkt_list.append(bucket_name)
        resp = S3H_OBJ.bucket_list()
        assert_in(bkt_list[0], resp[1], resp[1])
        self.log.info("Step 1: Successfully created bucket.")
        self.log.info(
            "Step 2: Start concurrent I/O with increasing client and request.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for client, request_load, bkt in zip(
                test_cfg["num_clients"], test_cfg["requests"], bkt_list):
            res = s3bench_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=bkt,
                end_point=DATA_PATH_CFG["data_path"]["endpoint"],
                num_clients=client,
                num_sample=request_load,
                obj_name_pref=test_cfg["obj_name"],
                obj_size=test_cfg["s3bench_obj_size"],
                skip_cleanup=test_cfg["skip_cleanup"],
                verbose=test_cfg["verbose"])
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(
            "Step 2: Start concurrent I/O with increasing client and request.")
        self.log.info("Step 3: checking system stability")
        res = S3H_OBJ.is_mero_online()
        assert_true(res[0], res[1])
        cmd_msg = DATA_PATH_CFG["data_path"]["cmd_msg"]
        commands = const.CRASH_COMMANDS
        for node, cmd in zip(self.nodes, commands):
            res_cmd = run_remote_cmd(cmd,
                                     node,
                                     CM_CFG["nodes"][node]["username"],
                                     CM_CFG["nodes"][node]["password"])
            assert_not_in(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info(
            "ENDED: Test gradual increase of concurrent client sessions"
            " with multiple clients on single buckets")
