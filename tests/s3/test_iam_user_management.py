#!/usr/bin/python
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
#

"""CSM CLI IAM user TestSuite"""

import os
import logging
from time import perf_counter_ns
from multiprocessing import Process
import pytest
import time
from commons import constants as cons
from commons.helpers.health_helper import Health
from commons.helpers import node_helper
from commons.utils import assert_utils, system_utils
from commons.configmanager import config_utils
from commons import cortxlogging as log
from commons.params import TEST_DATA_FOLDER
from config import CMN_CFG
from config import CSM_CFG
from config.s3 import S3_CFG
from scripts.s3_bench import s3bench
from libs.s3 import S3H_OBJ, s3_test_lib
from libs.s3 import iam_test_lib
from commons.exceptions import CTException
from libs.s3.s3_restapi_test_lib import S3AuthServerRestAPI
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations


class TestIAMUserManagement:
    """IAM user Testsuite for CLI/Rest"""

    @classmethod
    def setup_class(cls):
        cls.log = logging.getLogger(__name__)
        cls.remote_path = cons.AUTHSERVER_CONFIG
        cls.backup_path = cls.remote_path + ".bak"
        cls.local_path = cons.LOCAL_COPY_PATH
        cls.nobj = node_helper.Node(hostname=CMN_CFG["nodes"][0]["hostname"],
                                    username=CMN_CFG["nodes"][0]["username"],
                                    password=CMN_CFG["nodes"][0]["password"])
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.rest_obj = S3AccountOperations()
        cls.auth_obj = S3AuthServerRestAPI()
        cls.s3_user = "s3user_{}"
        cls.iam_user = "iamuser_{}"
        cls.email = "{}@seagate.com"
        cls.s3_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.log.info("Setup s3 bench tool")
        cls.log.info("Check s3 bench tool installed.")
        cls.iam_test_obj = iam_test_lib.IamTestLib()
        res = system_utils.path_exists("/root/go/src/s3bench")
        if not res:
            res = s3bench.setup_s3bench()
            assert_utils.assert_true(res, res)
        cls.test_dir_path = os.path.join(
            TEST_DATA_FOLDER, "TestIAMUserManagement")
        if not system_utils.path_exists(cls.test_dir_path):
            system_utils.make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)

    def setup_method(self):
        """
        This function will be invoked prior to each test function in the module.
        It is performing below operations as pre-requisites.
            - Login to CORTX CLI as s3account user.
        """
        self.log.info("STARTED : Setup operations for test function")
        self.iam_password = CSM_CFG["CliConfig"]["iam_user"]["password"]
        self.acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        self.user_name = None
        self.s3acc_name = "{}_{}".format("cli_s3acc", int(perf_counter_ns()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.log.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.rest_obj.create_s3_account(acc_name=self.s3acc_name,
                                               email_id=self.s3acc_email, passwd=self.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]

        self.iam_test_obj = iam_test_lib.IamTestLib(access_key=access_key, secret_key=secret_key)

        self.log.info("Created s3 account")
        self.parallel_ios = None
        self.account_dict = dict()
        self.resources_dict = dict()
        self.account_dict[self.s3acc_name] = self.acc_password
        self.account_prefix = "acc-reset-passwd-{}"
        self.io_bucket_name = "io-bkt1-reset-{}".format(perf_counter_ns())
        self.object_name = "obj-reset-object-{}".format(perf_counter_ns())
        self.file_path = os.path.join(self.test_dir_path, self.object_name)
        self.auth_file_change = False
        self.del_iam_user = False

        self.user_name = "{0}{1}".format("iam_user", str(perf_counter_ns()))
        self.START_LOG_FORMAT = "##### Test started -  "
        self.END_LOG_FORMAT = "##### Test Ended -  "
        self.log.info("ENDED : Setup operations for test function")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Delete IAM users created in a s3account
            - Log out from CORTX CLI console.
        """
        self.log.info("STARTED : Teardown operations for test function")
        if system_utils.path_exists(self.file_path):
            system_utils.remove_file(self.file_path)
        if self.parallel_ios:
            if self.parallel_ios.is_alive():
                self.parallel_ios.join()
        self.log.info(
            "Deleting all buckets/objects created during TC execution")
        bkt_list = self.s3_obj.bucket_list()[1]
        if self.io_bucket_name in bkt_list:
            resp = self.s3_obj.delete_bucket(self.io_bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step cleanup resources.")
        for resource in self.resources_dict:
            if resource:
                resp = resource.delete_bucket(
                    self.resources_dict[resource], force=True)
                assert_utils.assert_true(resp[0], resp[1])
        for acc in self.account_dict:
            if self.del_iam_user:
                self.log.info("Deleting IAM user")
                resp = self.iam_test_obj.delete_user(user_name=self.user_name)
                assert_utils.assert_true(resp[0], resp[1])
            resp = self.rest_obj.delete_s3_account(acc_name=acc)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Deleted %s account successfully", acc)

        if self.auth_file_change:
            self.log.info("Restoring authserver.properties file")
            resp = self.nobj.make_remote_file_copy(path=self.backup_path,
                                                   backup_path=self.remote_path)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Restored authserver.properties file successfully")
            self.log.info("Restart s3 authserver")
            status = system_utils.run_remote_cmd(
                cmd="systemctl restart s3authserver",
                hostname=self.host,
                username=self.uname,
                password=self.passwd,
                read_lines=True)
            assert_utils.assert_true(status[0], "Service did not restart successfully")
            self.log.info("Restarted s3 authserver successfully")

        self.log.info("ENDED : Teardown operations for test function")

    def check_cluster_health(self):
        """Check the cluster health."""
        self.log.info(
            "Check cluster status, all services are running.")
        nodes = CMN_CFG["nodes"]
        self.log.info(nodes)
        for _, node in enumerate(nodes):
            health_obj = Health(hostname=node["hostname"],
                                username=node["username"],
                                password=node["password"])
            resp = health_obj.check_node_health()
            self.log.info(resp)
            assert_utils.assert_true(resp[0], resp[1])
            health_obj.disconnect()
        self.log.info("Checked cluster status, all services are running.")

    def s3_ios(self,
               bucket=None,
               log_file_prefix="parallel_io",
               duration="0h1m",
               obj_size="24Kb",
               **kwargs):
        """
        Perform io's for specific durations.

        1. Create bucket.
        2. perform io's for specified durations.
        3. Check executions successful.
        """
        kwargs.setdefault("num_clients", 2)
        kwargs.setdefault("num_sample", 5)
        kwargs.setdefault("obj_name_pref", "load_gen_")
        kwargs.setdefault("end_point", S3_CFG["s3_url"])
        self.log.info("STARTED: s3 io's operations.")
        bucket = bucket if bucket else self.io_bucket_name
        resp = self.s3_obj.create_bucket(bucket)
        assert_utils.assert_true(resp[0], resp[1])
        access_key, secret_key = S3H_OBJ.get_local_keys()
        resp = s3bench.s3bench(
            access_key,
            secret_key,
            bucket=bucket,
            end_point=kwargs["end_point"],
            num_clients=kwargs["num_clients"],
            num_sample=kwargs["num_sample"],
            obj_name_pref=kwargs["obj_name_pref"],
            obj_size=obj_size,
            duration=duration,
            log_file_prefix=log_file_prefix)
        self.log.info(resp)
        assert_utils.assert_true(
            os.path.exists(
                resp[1]),
            f"failed to generate log: {resp[1]}")
        self.log.info("ENDED: s3 io's operations.")

    def start_stop_validate_parallel_s3ios(
            self, ios=None, log_prefix=None, duration="0h1m"):
        """Start/stop parallel s3 io's and validate io's worked successfully."""
        if ios == "Start":
            self.parallel_ios = Process(
                target=self.s3_ios, args=(
                    self.io_bucket_name, log_prefix, duration))
            if not self.parallel_ios.is_alive():
                self.parallel_ios.start()
            self.log.info("Parallel IOs started: %s for duration: %s",
                          self.parallel_ios.is_alive(), duration)
        if ios == "Stop":
            if self.parallel_ios.is_alive():
                resp = self.s3_obj.object_list(self.io_bucket_name)
                self.log.info(resp)
                self.parallel_ios.join()
                self.log.info(
                    "Parallel IOs stopped: %s",
                    not self.parallel_ios.is_alive())
            if log_prefix:
                resp = system_utils.validate_s3bench_parallel_execution(s3bench.LOG_DIR, log_prefix)
                assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-23398")
    def test_23398_create_iam_user(self):
        """
        Test ` s3iamuser create and View <user_name>`

        Test An S3 account owner shall be able to Create and View IAM user details and
        check s3 resources are intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info("Step 1: Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_23398_ios",
                                                duration="0h1m")
        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_test_obj.create_user(user_name=self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1]['User']['UserName'], self.user_name)
        self.del_iam_user = True
        self.log.info("Created iam user with name %s", self.user_name)
        self.log.info("Step 4: Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_23398_ios")
        self.log.info("Step 5:. Check cluster status, all services are running after completing "
                      "test.")
        self.check_cluster_health()
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-23399")
    def test_23399_list_user(self):
        """
        Verify IAM user show command and secret key should not be displayed.

        TEST create IAM users and verify secret keys should not be displayed thereafter
        while listing users and s3 resources should be intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info("Step 1: Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_23399_ios",
                                                duration="0h1m")
        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_test_obj.create_user(user_name=self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1]['User']['UserName'], self.user_name)
        self.log.info("Created iam user with name %s", self.user_name)
        self.del_iam_user = True
        self.log.info("Step 4: Verifying list command is able to list all iam users")
        resp = self.iam_test_obj.list_users()
        user_list = [user["UserName"] for user in resp[1] if "iam_user" in user["UserName"]]
        assert_utils.assert_list_item(user_list, self.user_name)
        self.log.info("Step 5. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_23399_ios")
        self.log.info("Step 6:. Check cluster status, all services are running after completing "
                      "test.")
        self.check_cluster_health()
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-23400")
    def test_23400_create_access_key(self):
        """
        Create or regenerate access keys for IAM user through CLI

        TEST An S3 account owner shall be able to create or regenerate an access key for IAM users
        and s3 resources should be intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info("Step 1: Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_23400_ios",
                                                duration="0h1m")
        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_test_obj.create_user(user_name=self.user_name)
        assert_utils.assert_exact_string(resp[1]['User']['UserName'], self.user_name)
        self.log.info("Created iam user with name %s", self.user_name)
        self.del_iam_user = True
        self.log.info("Step 4: Creating access key for IAM user %s", self.user_name)
        create_access_key = self.iam_test_obj.create_access_key(self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        self.log.info("Created access key for IAM user %s", self.user_name)
        self.log.info("Step 5: Verify access key is created")
        resp = self.iam_test_obj.list_access_keys(self.user_name)
        access_keys = [i['AccessKeyId'] for i in resp[1]['AccessKeyMetadata']]
        assert_utils.assert_in(create_access_key[1]['AccessKey']['AccessKeyId'], access_keys)
        self.log.info("Verified access key is created")
        self.log.info("Step 6: Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_23400_ios")
        self.log.info("Step 7: Deleting access key of iam user")
        resp = self.iam_test_obj.delete_access_key(
            user_name=self.user_name,
            access_key_id=create_access_key[1]['AccessKey']['AccessKeyId'])
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 8: Check cluster status, all services are running after completing "
                      "test.")
        self.check_cluster_health()
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-23401")
    def test_23401_delete_iam_user(self):
        """
        Test that ` s3iamuser delete <iam_user_name>` must delete the given IAM user

        TEST An S3 account owner can delete IAM users and
        s3 resources should be intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info("Step 1: Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_23401_ios",
                                                duration="0h1m")
        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_test_obj.create_user(user_name=self.user_name)
        assert_utils.assert_exact_string(resp[1]['User']['UserName'], self.user_name)
        self.log.info("Created iam user with name %s", self.user_name)
        self.log.info("Step 4: Deleting iam user with name %s", self.user_name)
        resp = self.iam_test_obj.delete_user(self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_23401_ios")
        self.log.info("Step 6: Check cluster status, all services are running after completing "
                      "test.")
        self.check_cluster_health()
        self.log.info("Deleted iam user with name %s", self.user_name)
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-23402")
    def test_23402_check_access_key_count(self):
        """
        Verify IAM user can not create more than two access keys.

        TEST to create two access keys per IAM user and
        s3 resources should be intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info("Step 1: Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_23402_ios",
                                                duration="0h1m")
        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_test_obj.create_user(user_name=self.user_name)
        assert_utils.assert_exact_string(resp[1]['User']['UserName'], self.user_name)
        self.log.info("Created iam user with name %s", self.user_name)
        self.del_iam_user = True
        self.log.info("Step 4: Creating access key for IAM user %s", self.user_name)
        create_access_key = self.iam_test_obj.create_access_key(self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        resp = self.iam_test_obj.list_access_keys(self.user_name)
        access_keys = [i['AccessKeyId'] for i in resp[1]['AccessKeyMetadata']]
        assert_utils.assert_in(create_access_key[1]['AccessKey']['AccessKeyId'], access_keys)
        self.log.info("Created access key for IAM user %s", self.user_name)
        self.log.info("Step 5: Creating second access key for user %s", self.user_name)
        create_access_key1 = self.iam_test_obj.create_access_key(self.user_name)
        assert_utils.assert_true(create_access_key1[0], create_access_key1[1])
        resp = self.iam_test_obj.list_access_keys(self.user_name)
        access_keys = [i['AccessKeyId'] for i in resp[1]['AccessKeyMetadata']]
        assert_utils.assert_in(create_access_key1[1]['AccessKey']['AccessKeyId'], access_keys)
        self.log.info("Created second access key for IAM user %s", self.user_name)
        self.log.info("Step 6: Verify two access keys are present for IAM user %s", self.user_name)
        assert_utils.assert_equal(len(access_keys), 2)
        self.log.info("Verified two access keys are present for IAM user %s", self.user_name)
        self.log.info("Step 7: Verify IAM user can not have more than two access keys")
        self.log.info("Creating third access key for user %s", self.user_name)
        try:
            create_access_key2 = self.iam_test_obj.create_access_key(self.user_name)
            assert_utils.assert_false(create_access_key2[0], create_access_key2[1])
        except CTException as error:
            self.log.error("IAM user already has two access keys: %s", error)
            self.log.info("Verified IAM user can not have more than two access keys")
        self.log.info("Step 8: Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_23402_ios")
        self.log.info("Step 9: Deleting access keys associated with iam user")
        for key in access_keys:
            resp = self.iam_test_obj.delete_access_key(user_name=self.user_name,
                                                       access_key_id=key)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 10: Check cluster status, all services are running after completing "
                      "test.")
        self.check_cluster_health()
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-23463")
    def test_23463_crud_with_another_access_key(self):
        """
        Verify CRUD Operations with regenreated another access key

        TEST IAM users should be able to access and perform CRUD operations on resources
        with another access key and s3 resources should be intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info("Step 1: Check cluster status, all services are running before starting test")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(ios="Start", log_prefix="test_23463_ios",
                                                duration="0h1m")
        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_test_obj.create_user(user_name=self.user_name)
        assert_utils.assert_exact_string(resp[1]['User']['UserName'], self.user_name)
        self.log.info("Created iam user with name %s", self.user_name)
        self.del_iam_user = True

        self.log.info("Step 4: Creating access key for IAM user %s", self.user_name)
        create_access_key = self.iam_test_obj.create_access_key(self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        iam_access_key = create_access_key[1]['AccessKey']['AccessKeyId']
        self.log.info("Created access key for IAM user %s", self.user_name)
        self.log.info("Step 5: Verify access key is created")
        resp = self.iam_test_obj.list_access_keys(self.user_name)
        access_keys = [i['AccessKeyId'] for i in resp[1]['AccessKeyMetadata']]
        assert_utils.assert_in(create_access_key[1]['AccessKey']['AccessKeyId'], access_keys)
        self.log.info("Verified access key is created")
        self.log.info("Step 6: Deleting access key of IAM user %s", self.user_name)
        resp = self.iam_test_obj.delete_access_key(user_name=self.user_name,
                                                   access_key_id=iam_access_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Deleted access key of IAM user %s", self.user_name)
        self.log.info("Step 7: Verify access key is deleted for IAM user %s", self.user_name)
        resp = self.iam_test_obj.list_access_keys(self.user_name)
        access_keys = [i['AccessKeyId'] for i in resp[1]['AccessKeyMetadata']]
        assert_utils.assert_not_in(create_access_key[1]['AccessKey']['AccessKeyId'], access_keys)
        self.log.info("Verified access key is deleted for IAM user %s", self.user_name)

        self.log.info("Step 8: Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="test_23463_ios")
        self.log.info("Step 9: Check cluster status, all services are running after completing "
                      "test.")
        self.check_cluster_health()
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-22150")
    def test_22150(self):
        """use REST API call to create s3iamuser with special characters."""
        self.log.info("STARTED: use REST API call to create s3iamuser with special characters.")
        self.log.info("Step 1: Create Account.")
        self.acc_name = self.s3_user.format(perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.acc_name)
        resp = self.rest_obj.create_s3_account(self.acc_name, self.email_id, self.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]

        self.log.info("Step 2: create s3iamuser with special character using REST API call.")
        for schar in ["_", "-", "@"]:
            self.iam_user = "iamuser{}{}".format(schar, perf_counter_ns())
            resp = self.auth_obj.create_iam_user(
                self.iam_user, self.iam_password, access_key, secret_key)
            assert_utils.assert_true(resp[0], resp[1])
            resp = self.auth_obj.delete_iam_user(self.iam_user, access_key, secret_key)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Delete s3 account.")
        resp = self.rest_obj.delete_s3_account(self.acc_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: use REST API call to create s3iamuser with special characters.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-22148")
    def test_22148(self):
        """REST API to Update Login Profile without mentioning new Password for the s3iamuser."""
        self.log.info(
            "STARTED: Update Login Profile without mentioning new Password for the s3iamuser.")
        self.log.info("Step 1: Create Account.")
        self.acc_name = self.s3_user.format(perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.acc_name)
        resp = self.rest_obj.create_s3_account(self.acc_name, self.email_id, self.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("Step 2: create s3iamuser.")
        self.iam_user = "iamuser-{}".format(perf_counter_ns())
        resp = self.auth_obj.create_iam_user(
            self.iam_user, self.iam_password, access_key, secret_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: update password for user using REST API.")
        resp = self.auth_obj.update_iam_user(
            self.iam_user, access_key=secret_key, secret_key=access_key)
        assert_utils.assert_false(resp[0], resp[1])
        self.log.info("Step 4: Delete iam user.")
        resp = self.auth_obj.delete_iam_user(self.iam_user, access_key, secret_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Delete s3 account.")
        resp = self.rest_obj.delete_s3_account(self.acc_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Update Login Profile without mentioning new Password for the s3iamuser.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-27277")
    def test_27277(self):
        """use REST API call to perform CRUD operations on s3iamuser."""
        self.log.info("STARTED: use REST API call to perform CRUD operations on s3iamuser.")
        self.log.info("Step 1: Create s3 Account")
        self.acc_name = self.s3_user.format(perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.acc_name)
        resp = self.rest_obj.create_s3_account(self.acc_name, self.email_id, self.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("Step 2: Create s3iamuser using access/secret key using direct REST API call")
        self.iam_user = "iamuser-{}".format(perf_counter_ns())
        resp = self.auth_obj.create_iam_user(
            self.iam_user, self.iam_password, access_key, secret_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: list s3iamusers using access/secret key using direct REST API call.")
        resp = self.auth_obj.list_iam_users(access_key, secret_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: updateloginprofile for s3iamuser using rest-api call.")
        resp = self.auth_obj.update_iam_user(
            self.iam_user, self.acc_password, access_key, secret_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Delete s3iamuser using access/secret key using direct REST API call")
        resp = self.auth_obj.delete_iam_user(self.iam_user, access_key, secret_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Delete s3 Account")
        resp = self.rest_obj.delete_s3_account(self.acc_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: use REST API call to perform CRUD operations on s3iamuser.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-27278")
    def test_27278(self):
        """use REST API call to perform accesskey CRUD operations for s3iamuser."""
        self.log.info(
            "STARTED: use REST API call to perform accesskey CRUD operations for s3iamuser.")
        self.log.info("Step 1: Create s3 Account")
        self.acc_name = self.s3_user.format(perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.acc_name)
        resp = self.rest_obj.create_s3_account(self.acc_name, self.email_id, self.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("Step 2: Create s3iamuser using access/secret key using direct REST API call")
        self.iam_user = "iamuser-{}".format(perf_counter_ns())
        resp = self.auth_obj.create_iam_user(
            self.iam_user, self.iam_password, access_key, secret_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: Create 2 Accesskey/secret key for s3iamuser using REST API call.")
        iam_access_key = []
        for _ in range(2):
            resp = self.auth_obj.create_iam_accesskey(self.iam_user, access_key, secret_key)
            iam_access_key.append(resp[1]["AccessKeyId"])
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Now list 2 acceeskey/secret keys for s3iamuser using REST API call.")
        resp = self.auth_obj.list_iam_accesskey(self.iam_user, access_key, secret_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Update accesskey for s3iamuser.")
        resp = self.auth_obj.update_iam_accesskey(
            self.iam_user, iam_access_key[0], access_key, secret_key, status="Inactive")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Delete accesskey for s3iamuser.")
        resp = self.auth_obj.update_iam_accesskey(
            self.iam_user, iam_access_key[0], access_key, secret_key, status="Active")
        assert_utils.assert_true(resp[0], resp[1])
        for accesskeyid in iam_access_key:
            resp = self.auth_obj.delete_iam_accesskey(
                self.iam_user, accesskeyid, access_key, secret_key)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 7: Delete s3iamuser using access/secret key using direct REST API call")
        resp = self.auth_obj.delete_iam_user(self.iam_user, access_key, secret_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 8: Delete s3 Account")
        resp = self.rest_obj.delete_s3_account(self.acc_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: use REST API call to perform accesskey CRUD operations for s3iamuser.")

    @pytest.mark.skip("")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-21644")
    def test_21644(self):
        """use REST API call to create more than 2 Accesskeys for s3iamuser."""
        self.log.info("STARTED: use REST API call to create more than 2 Accesskeys for s3iamuser.")
        self.log.info("Step 1: Create Account.")
        self.acc_name = self.s3_user.format(perf_counter_ns())
        self.email_id = "{}@seagate.com".format(self.acc_name)
        resp = self.rest_obj.create_s3_account(self.acc_name, self.email_id, self.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]
        self.log.info("Step 2: create s3iamuser.")
        self.iam_user = "iamuser-{}".format(perf_counter_ns())
        resp = self.auth_obj.create_iam_user(
            self.iam_user, self.iam_password, access_key, secret_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 3: List 2 accesskeys/secrets for s3iamuser using REST API.")
        access_key_id = []
        for _ in range(2):
            resp = self.auth_obj.create_iam_accesskey(self.iam_user, access_key, secret_key)
            assert_utils.assert_true(resp[0], resp[1])
            access_key_id.append(resp[1]["AccessKeyId"])
        self.log.info("Step 4: Now create another accesskey/secretkey for same s3iamuser.")
        resp = self.auth_obj.create_iam_accesskey(self.iam_user, access_key, secret_key)
        assert_utils.assert_false(resp[0], resp[1])
        self.log.info("Step 5: Delete iam user.")
        for accesskeyid in access_key_id:
            resp = self.auth_obj.delete_iam_accesskey(
                self.iam_user, accesskeyid, access_key, secret_key)
            assert_utils.assert_true(resp[0], resp[1])
        resp = self.auth_obj.delete_iam_user(self.iam_user, access_key, secret_key)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6: Delete s3 account.")
        resp = self.rest_obj.delete_s3_account(self.acc_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: use REST API call to create more than 2 Accesskeys for s3iamuser.")

    @pytest.mark.skip("Need more validation")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-28776")
    def test_28776(self):
        """
        s3iamusers creation with different maxIAMUserLimit values
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        iam_users = []
        self.log.info("Step 1: Make copy of original authserver.properties file")
        resp = self.nobj.make_remote_file_copy(path=self.remote_path, backup_path=self.backup_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Edit authserver.properties file for user creation value set to 0")
        resp = self.nobj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        msg = f"copy_file_to_local failed: remote path: " \
              f"{self.remote_path}, local path: {self.local_path}"
        assert_utils.assert_true(resp, msg)
        prop_dict = config_utils.read_properties_file(self.local_path)
        if prop_dict:
            if prop_dict['maxIAMUserLimit'] != "0":
                prop_dict['maxIAMUserLimit'] = "0"
        resp = config_utils.write_properties_file(self.local_path, prop_dict)
        self.nobj.copy_file_to_remote(local_path=self.local_path, remote_path=self.remote_path)
        self.auth_file_change = True
        self.log.info("Step 3: Restart s3 authserver")
        status = system_utils.run_remote_cmd(
            cmd="systemctl restart s3authserver",
            hostname=self.host,
            username=self.uname,
            password=self.passwd,
            read_lines=True)
        assert_utils.assert_true(status[0], "Service did not restart successfully")
        self.log.info("Step 4: Trying to create one iam user")
        try:
            resp = self.iam_test_obj.create_user(user_name=self.user_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error("Can not create IAM users beyond maximum limit: %s", error)
        self.log.info("Step 5: Edit authserver.properties file for user creation value set to 6")
        resp = self.nobj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        msg = f"copy_file_to_local failed: remote path: " \
              f"{self.remote_path}, local path: {self.local_path}"
        assert_utils.assert_true(resp, msg)
        prop_dict = config_utils.read_properties_file(self.local_path)
        if prop_dict:
            prop_dict['maxIAMUserLimit'] = "6"
        resp = config_utils.write_properties_file(self.local_path, prop_dict)
        self.nobj.copy_file_to_remote(local_path=self.local_path, remote_path=self.remote_path)
        self.log.info("Step 6: Restart s3 authserver")
        status = system_utils.run_remote_cmd(
            cmd="systemctl restart s3authserver",
            hostname=self.host,
            username=self.uname,
            password=self.passwd,
            read_lines=True)
        assert_utils.assert_true(status[0], "Service did not restart successfully")
        self.log.info("Step 7: Creating 6 iam users.")
        for i in range(6):
            self.user_name = "{0}{1}-{2}".format("iam_user", str(time.time()), i)
            resp = self.iam_test_obj.create_user(user_name=self.user_name)
            assert_utils.assert_exact_string(resp[1]['User']['UserName'], self.user_name)
            iam_users.append(self.user_name)

        self.log.info("6 iam users creation successful")
        self.log.info("Step 8: Try creating one more iam user")
        try:
            self.user_name = "{0}{1}".format("iam_user", str(time.time()))
            resp = self.iam_test_obj.create_user(user_name=self.user_name)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error("Can not create IAM users beyond maximum limit: %s", error)
        self.log.info("Verified IAM user can not be created beyond maximum limit mentioned in"
                      " authserver.properties file")
        self.log.info("Step 9: Deleting all IAM users")
        for user in iam_users:
            resp = self.iam_test_obj.delete_user(user_name=user)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("####### Test Completed! #########")

    @pytest.mark.skip("Need more validation")
    @pytest.mark.s3_ops
    @pytest.mark.s3_iam_user_mgnt
    @pytest.mark.tags("TEST-28852")
    def test_28852(self):
        """s3accounts creation with different maxIAMAccountLimit values"""
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        s3_accounts = []
        resp, acc_list = self.rest_obj.list_s3_accounts()
        self.log.debug("Total s3 accounts present: %s", len(acc_list))
        if len(acc_list) > 993:
            assert_utils.assert_true(False, "Default value of maximum count of s3 accounts is 1000."
                                            " Test can't be continued.")
        self.log.info("Step 1: Make copy of original authserver.properties file")
        resp = self.nobj.make_remote_file_copy(path=self.remote_path, backup_path=self.backup_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Edit authserver.properties file for account creation value set to "
                      "%s", len(acc_list))
        resp = self.nobj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        msg = f"copy_file_to_local failed: remote path: " \
              f"{self.remote_path}, local path: {self.local_path}"
        assert_utils.assert_true(resp, msg)
        prop_dict = config_utils.read_properties_file(self.local_path)
        if prop_dict:
            prop_dict['maxAccountLimit'] = f"{len(acc_list)}"
        resp = config_utils.write_properties_file(self.local_path, prop_dict)
        self.nobj.copy_file_to_remote(local_path=self.local_path, remote_path=self.remote_path)
        self.auth_file_change = True
        self.log.info("Step 3: Restart s3 authserver")
        status = system_utils.run_remote_cmd(
            cmd="systemctl restart s3authserver",
            hostname=self.host,
            username=self.uname,
            password=self.passwd,
            read_lines=True)
        assert_utils.assert_true(status[0], "Service did not restart successfully")
        self.log.info("Step 4: Try creating one s3 account")
        try:
            self.acc_name = self.s3_user.format(perf_counter_ns())
            self.email_id = "{}@seagate.com".format(self.acc_name)
            resp = self.rest_obj.create_s3_account(self.acc_name, self.email_id,
                                                   self.acc_password)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error("Can not create s3 accounts beyond maximum limit: %s", error)
        self.log.info("Step 5: Edit authserver.properties file for account creation value set to "
                      "%s", len(acc_list) + 6)
        resp = self.nobj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        msg = f"copy_file_to_local failed: remote path: " \
              f"{self.remote_path}, local path: {self.local_path}"
        assert_utils.assert_true(resp, msg)
        prop_dict = config_utils.read_properties_file(self.local_path)
        if prop_dict:
            prop_dict['maxAccountLimit'] = f"{len(acc_list) + 6}"
        resp = config_utils.write_properties_file(self.local_path, prop_dict)
        self.nobj.copy_file_to_remote(local_path=self.local_path, remote_path=self.remote_path)
        self.log.info("Step 6: Restart s3 authserver")
        status = system_utils.run_remote_cmd(
            cmd="systemctl restart s3authserver",
            hostname=self.host,
            username=self.uname,
            password=self.passwd,
            read_lines=True)
        assert_utils.assert_true(status[0], "Service did not restart successfully")
        self.log.info("Step 7: Creating 6 s3 accounts with name %s")
        for i in range(6):
            self.acc_name = "{0}_{1}_{2}".format("cli_s3_acc", int(perf_counter_ns()), i)
            self.email_id = "{}@seagate.com".format(self.acc_name)
            resp = self.rest_obj.create_s3_account(self.acc_name, self.email_id,
                                                   self.acc_password)
            assert_utils.assert_true(resp[0], resp[1])
            s3_accounts.append(self.acc_name)
        self.log.info("6 s3 accounts creation successful")
        self.log.info("Step 8: Try creating one more s3 account")
        try:
            self.acc_name = "{0}_{1}".format("cli_s3_acc", int(perf_counter_ns()))
            self.email_id = "{}@seagate.com".format(self.acc_name)
            resp = self.rest_obj.create_s3_account(self.acc_name, self.email_id,
                                                   self.acc_password)
            assert_utils.assert_false(resp[0], resp[1])
        except CTException as error:
            self.log.error("Can not create s3 accounts beyond maximum limit: %s", error)
        self.log.info("Verified s3 accounts can not be created beyond maximum limit mentioned in"
                      " authserver.properties file")

        self.log.info("Step 9: Deleting all s3 accounts")
        for acc in s3_accounts:
            resp = self.rest_obj.delete_s3_account(acc_name=acc)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("####### Test Completed! #########")
