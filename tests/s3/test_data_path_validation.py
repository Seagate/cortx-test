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

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.exceptions import CTException
from commons.configmanager import get_config_wrapper
from commons.helpers import s3_helper
from commons.utils.system_utils import remove_file
from commons.utils.assert_utils import assert_true, assert_in, assert_false
from commons.constants import const
from libs.s3 import S3H_OBJ, s3_test_lib, iam_test_lib, s3_acl_test_lib, s3_multipart_test_lib
from libs.s3 import LDAP_USERNAME, LDAP_PASSWD


USER_CONFIG = get_config_wrapper(fpath="config/s3/test_iam_user_login.yaml")

try:
    from scripts.s3_bench import s3bench as s3bench_obj
except BaseException as error:
    import site
    import sys
    site.addsitedir('scripts/')  # Always appends to end
    from s3_bench import s3bench as s3bench_obj

S3_OBJ = s3_test_lib.S3TestLib()
IAM_TEST_OBJ = iam_test_lib.IamTestLib()
ACL_OBJ = s3_acl_test_lib.S3AclTestLib()

data_path_cfg = read_yaml("config/s3/test_data_path_validate.yaml")[1]
common_cfg = read_yaml("config/common_config.yaml")[1]

class DataPathValidation(Test):
    """
    Data Path Test suite
    """


    @CTPLogformatter()
    def setUp(self):
        """
        This function will be invoked before each test case execution
        It will perform prerequisite test steps if any
        """

        self.log.info("STARTED: Setup operations")
        self.random_id = str(time.time())
        self.account_name = "{}{}".format(
            data_path_cfg["data_path"]["acc_name_prefix"],
            str(time.time()))
        self.email_id = "{}{}".format(
            self.account_name,
            data_path_cfg["data_path"]["email_suffix"])
        self.ldap_user = LDAP_USERNAME
        self.ldap_pwd = LDAP_PASSWD
        self.log_file = []
        self.nodes = common_cfg["nodes"]
        self.log.info("ENDED: Setup operations")

    def tearDown(self):
        """
        This function will be invoked after running each test case.
        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        """
        self.log.info("STARTED: Teardown operations")
        resp = S3_OBJ.bucket_list()
        pref_list = [
            each_bucket for each_bucket in resp[1] if each_bucket.startswith(
                data_path_cfg["data_path"]["bkt_name_prefix"])]
        for bucket in pref_list:
            ACL_OBJ.put_bucket_acl(
                bucket, acl=data_path_cfg["data_path"]["bkt_permission"])
        S3_OBJ.delete_multiple_buckets(pref_list)
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
        if os.path.exists(data_path_cfg["data_path"]["file_path"]):
            os.remove(data_path_cfg["data_path"]["file_path"])
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
        self.log.info(
            "Step 2: Creating a bucket with name : {}".format(bucket_name))
        res = S3_OBJ.create_bucket(bucket_name)
        self.assertIn(bucket_name, res[1], res[1])
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
        self.log.info("Step 3:Upload object of size : {}".format(test_conf["obj_size"]))
        cmd = "dd if=/dev/zero of={} bs={} count={}".format(data_path_cfg["data_path"]["file_path"],
                                                            bs,
                                                            test_conf["obj_size"])
        self.log.info(cmd)
        S3H_OBJ.run_cmd(cmd)
        res = S3_OBJ.put_object(bucket_name,
                                test_conf["object_name"],
                                data_path_cfg["data_path"]["file_path"])
        self.assertTrue(res[0], res[1])

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
        cmd = data_path_cfg["data_path"]["s3bench_cmd"].format(
            access_key,
            secret_key,
            bucket,
            data_path_cfg["data_path"]["endpoint"],
            data_path_cfg["data_path"]["clients"],
            data_path_cfg["data_path"]["samples"],
            test_conf["obj_prefix"],
            data_path_cfg["data_path"]["obj_size"])
        S3H_OBJ.run_cmd("cd {}".format(data_path_cfg["data_path"]["s3bench_path"]))
        resp = S3H_OBJ.run_cmd(cmd)
        self.log.debug(resp)
        self.assertIsNotNone(resp[0], resp)
        resp_split = resp[0].split("\n")
        resp_filtered = [i for i in resp_split if 'Number of Errors' in i]
        for response in resp_filtered:
            self.log.debug(response)
            self.assertEqual(int(response.split(":")[1].strip()), 0, response)


    def test_1696(self):
        """
        Validate Data-Path on fresh system with 1 byte object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 byte object size")
        test_conf = data_path_cfg["test_1696"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket)
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 byte object size")


    def test_1697(self):
        """
        Validate Data-Path on fresh system with 1 KB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 KB object size")
        test_conf = data_path_cfg["test_1697"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket)
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 KB object size")


    def test_1698(self):
        """
        Validate Data-Path on fresh system with 1 MB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 MB object size")
        test_conf = data_path_cfg["test_1698"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 MB object size")


    def test_1699(self):
        """
        Validate Data-Path on fresh system with 10 MB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 10 MB object size")
        test_conf = data_path_cfg["test_1699"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 10 MB object size")


    def test_1700(self):
        """
        Validate Data-Path on fresh system with 100 MB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 100 MB object size")
        test_conf = data_path_cfg["test_1700"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 100 MB object size")


    def test_1701(self):
        """
        Validate Data-Path on fresh system with 1 GB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 1 GB object size")
        test_conf = data_path_cfg["test_1701"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 1 GB object size")


    def test_1702(self):
        """
        Validate Data-Path on fresh system with 10 GB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on fresh system with 10 GB object size")
        test_conf = data_path_cfg["test_1702"]
        bucket = self.create_bucket(test_conf)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on fresh system with 10 GB object size")


    def test_1703(self):
        """
        Validate Data-Path on loaded system with 1 byte object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 byte object size")
        test_conf = data_path_cfg["test_1703"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket)
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 byte object size")


    def test_1704(self):
        """
        Validate Data-Path on loaded system with 1 KB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 KB object size")
        test_conf = data_path_cfg["test_1704"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket)
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 KB object size")


    def test_1705(self):
        """
        Validate Data-Path on loaded system with 1 MB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 MB object size")
        test_conf = data_path_cfg["test_1705"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 MB object size")


    def test_1706(self):
        """
        Validate Data-Path on loaded system with 10 MB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 10 MB object size")
        test_conf = data_path_cfg["test_1706"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 10 MB object size")


    def test_1707(self):
        """
        Validate Data-Path on loaded system with 100 MB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 100 MB object size")
        test_conf = data_path_cfg["test_1707"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 100 MB object size")


    def test_1708(self):
        """
        Validate Data-Path on loaded system with 1 GB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 1 GB object size")
        test_conf = data_path_cfg["test_1708"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 1 GB object size")


    def test_1709(self):
        """
        Validate Data-Path on loaded system with 10 GB object size
        :avocado: tags=data_path_validation
        """
        self.log.info(
            "STARTED: Validate Data-Path on loaded system with 10 GB object size")
        test_conf = data_path_cfg["test_1709"]
        bucket = self.create_bucket(test_conf)
        self.run_s3bench(test_conf, bucket)
        self.put_object(test_conf, bucket, test_conf["size_mb"])
        self.log.info(
            "ENDED: Validate Data-Path on loaded system with 10 GB object size")


    def test_1745(self):
        """
        Test gradual increase of concurrent client sessions with single client on single bucket
        :avocado: tags=data_path_validate
        """
        self.log.info("STARTED: Test gradual increase of concurrent client sessions"
                      " with single client on single bucket")
        test_cfg = data_path_cfg["test_1745"]
        bucket_name = "{}{}".format(
            test_cfg["bucket_name"], time.time())
        self.log.info(f"Step 1: Create bucket with name {bucket_name}.")
        resp = S3_OBJ.create_bucket(bucket_name)
        self.assertTrue(resp[0], resp[1])
        resp = S3_OBJ.bucket_list()
        self.assertIn(bucket_name, resp[1], resp[1])
        self.log.info(f"Step 1: Successfully created bucket.")
        self.log.info(f"Step 2: Start concurrent I/O with 100 client and gradually increase request.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for request_load in test_cfg["requests"]:
            self.log.info(f"I/O with {request_load} request")
            res = s3bench_obj.s3bench(
                access_key=access_key, secret_key=secret_key, bucket=bucket_name,
                end_point=data_path_cfg["data_path"]["endpoint"], num_clients=test_cfg["num_clients"],
                num_sample=request_load, obj_name_pref=test_cfg["obj_name"],
                obj_size=test_cfg["s3bench_obj_size"], skip_cleanup=test_cfg["skip_cleanup"],
                verbose=test_cfg["verbose"])
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(f"Step 2: Successfully performed concurrent I/O with 100 client and"
                      f"gradually increasing requests.")
        self.log.info("Step 3: checking system stability")
        res = S3H_OBJ.is_mero_online()
        self.assertTrue(res[0], res[1])
        cmd_msg = data_path_cfg["data_path"]["cmd_msg"]
        commands = const.CRASH_COMMANDS
        for node, cmd in zip(self.nodes, commands):
            res_cmd = S3H_OBJ.remote_execution(
                node, common_cfg["username"], common_cfg["password"], cmd)
            self.assertNotIn(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info("ENDED: Test gradual increase of concurrent client sessions"
                      " with single client on single bucket")


    def test_1746(self):
        """
        Test gradual increase of concurrent client sessions with multiple clients on single buckets
        :avocado: tags=data_path_validate
        """
        self.log.info("STARTED: Test gradual increase of concurrent client sessions"
                      " with multiple clients on single buckets")
        test_cfg = data_path_cfg["test_1746"]
        bucket_name = "{}{}".format(
            test_cfg["bucket_name"], time.time())
        self.log.info(f"Step 1: Create bucket with name {bucket_name}.")
        resp = S3_OBJ.create_bucket(bucket_name)
        self.assertTrue(resp[0], resp[1])
        resp = S3_OBJ.bucket_list()
        self.assertIn(bucket_name, resp[1], resp[1])
        self.log.info(f"Step 1: Successfully created bucket.")
        self.log.info(
            f"Step 2: Start concurrent I/O with multiple client increasing request on single bucket.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for client, request_load in zip(test_cfg["num_clients"], test_cfg["requests"]):
            res = s3bench_obj.s3bench(
                access_key=access_key, secret_key=secret_key, bucket=bucket_name,
                end_point=data_path_cfg["data_path"]["endpoint"], num_clients=client,
                num_sample=request_load, obj_name_pref=test_cfg["obj_name"],
                obj_size=test_cfg["s3bench_obj_size"], skip_cleanup=test_cfg["skip_cleanup"],
                verbose=test_cfg["verbose"])
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(
            f"Step 2: completed concurrent I/O with multiple client and increasing request on single bucket.")
        self.log.info("Step 3: checking system stability")
        res = S3H_OBJ.is_mero_online()
        self.assertTrue(res[0], res[1])
        cmd_msg = data_path_cfg["data_path"]["cmd_msg"]
        commands = const.CRASH_COMMANDS
        for node, cmd in zip(self.nodes, commands):
            res_cmd = S3H_OBJ.remote_execution(
                node, common_cfg["username"], common_cfg["password"], cmd)
            self.assertNotIn(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info("ENDED: Test gradual increase of concurrent client sessions"
                      " with multiple clients on single buckets")


    def test_1747(self):
        """
        Test gradual increase of concurrent client sessions with multiple clients on multiple buckets
        :avocado: tags=data_path_validate
        """
        self.log.info("STARTED: Test gradual increase of concurrent client sessions"
                      " with multiple clients on multiple buckets")
        test_cfg = data_path_cfg["test_1747"]
        self.log.info(f"Step 1: Creating {test_cfg['bkt_count']} buckets.")
        bkt_list = []
        for bkt in range(test_cfg["bkt_count"]):
            bucket_name = "{}{}".format(
                test_cfg["bucket_name"], time.time())
            resp = S3_OBJ.create_bucket(bucket_name)
            self.assertTrue(resp[0], resp[1])
            bkt_list.append(bucket_name)
        resp = S3_OBJ.bucket_list()
        self.assertIn(bkt_list[0], resp[1], resp[1])
        self.log.info(f"Step 1: Successfully created buckets: {bkt_list}.")
        self.log.info(
            f"Step 2: Start concurrent I/O with increasing client and request on multiple buckets.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for client, request_load, bkt in zip(test_cfg["num_clients"], test_cfg["requests"], bkt_list):
            res = s3bench_obj.s3bench(
                access_key=access_key, secret_key=secret_key, bucket=bkt,
                end_point=data_path_cfg["data_path"]["endpoint"], num_clients=client,
                num_sample=request_load, obj_name_pref=test_cfg["obj_name"],
                obj_size=test_cfg["s3bench_obj_size"], skip_cleanup=test_cfg["skip_cleanup"],
                verbose=test_cfg["verbose"])
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(
            f"Step 2: Completed concurrent I/O with increasing client and request on multiple buckets.")
        self.log.info("Step 3: checking system stability")
        res = S3H_OBJ.is_mero_online()
        self.assertTrue(res[0], res[1])
        cmd_msg = data_path_cfg["data_path"]["cmd_msg"]
        commands = const.CRASH_COMMANDS
        for node, cmd in zip(self.nodes, commands):
            res_cmd = S3H_OBJ.remote_execution(
                node, common_cfg["username"], common_cfg["password"], cmd)
            self.assertNotIn(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info("ENDED: Test gradual increase of concurrent client sessions"
                      " with multiple clients on multiple buckets")


    def test_1748(self):
        """
        Test burst I/O with single client on single bucket
        :avocado: tags=data_path_validate
        """
        self.log.info("STARTED: Test gradual increase of concurrent client sessions"
                      " with multiple clients on single buckets")
        test_cfg = data_path_cfg["test_1748"]
        self.log.info("Step 1: Create bucket.")
        bkt_list = []
        for bkt in range(test_cfg["bkt_count"]):
            bucket_name = "{}{}".format(
                test_cfg["bucket_name"], time.time())
            resp = S3_OBJ.create_bucket(bucket_name)
            self.assertTrue(resp[0], resp[1])
            bkt_list.append(bucket_name)
        resp = S3_OBJ.bucket_list()
        self.assertIn(bkt_list[0], resp[1], resp[1])
        self.log.info(f"Step 1: Successfully created bucket.")
        self.log.info(f"Step 2: Start concurrent I/O with increasing client and request.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        for client, request_load, bkt in zip(test_cfg["num_clients"], test_cfg["requests"], bkt_list):
            res = s3bench_obj.s3bench(
                access_key=access_key, secret_key=secret_key, bucket=bkt,
                end_point=data_path_cfg["data_path"]["endpoint"], num_clients=client,
                num_sample=request_load, obj_name_pref=test_cfg["obj_name"],
                obj_size=test_cfg["s3bench_obj_size"], skip_cleanup=test_cfg["skip_cleanup"],
                verbose=test_cfg["verbose"])
            self.log.debug(res)
            self.log_file.append(res[1])
        self.log.info(f"Step 2: Start concurrent I/O with increasing client and request.")
        self.log.info("Step 3: checking system stability")
        res = S3H_OBJ.is_mero_online()
        self.assertTrue(res[0], res[1])
        cmd_msg = data_path_cfg["data_path"]["cmd_msg"]
        commands = const.CRASH_COMMANDS
        for node, cmd in zip(self.nodes, commands):
            res_cmd = S3H_OBJ.remote_execution(
                node, common_cfg["username"], common_cfg["password"], cmd)
            self.assertNotIn(cmd_msg, res_cmd, res_cmd)
        self.log.info("Step 3: checked system stability")
        self.log.info("ENDED: Test gradual increase of concurrent client sessions"
                      " with multiple clients on single buckets")
