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
from commons.helpers.health_helper import Health
from commons.utils import assert_utils, system_utils
from commons import cortxlogging as log
from commons.params import TEST_DATA_FOLDER
from config import CMN_CFG
from config import CSM_CFG
from config import S3_CFG
from scripts.s3_bench import s3bench
from libs.s3 import S3H_OBJ, s3_test_lib
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cortx_cli_s3access_keys import CortxCliS3AccessKeys
from libs.s3.cortxcli_test_lib import CortxCliTestLib


class TestIAMUserManagement:
    """IAM user Testsuite for CLI"""

    @classmethod
    def setup_class(cls):
        cls.log = logging.getLogger(__name__)
        cls.s3_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.log.info("Setup s3 bench tool")
        cls.log.info("Check s3 bench tool installed.")
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
        self.iam_obj = CortxCliIamUser()
        self.iam_obj.open_connection()
        self.s3acc_obj = CortxCliS3AccountOperations(
            session_obj=self.iam_obj.session_obj)
        self.access_key_obj = CortxCliS3AccessKeys(
            session_obj=self.iam_obj.session_obj)
        self.s3acc_name = "{}_{}".format("cli_s3acc", int(perf_counter_ns()))
        self.s3acc_email = "{}@seagate.com".format(self.s3acc_name)
        self.cli_test_obj = CortxCliTestLib()
        self.log.info("Creating s3 account with name %s", self.s3acc_name)
        resp = self.s3acc_obj.login_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.s3acc_obj.create_s3account_cortx_cli(
            account_name=self.s3acc_name,
            account_email=self.s3acc_email,
            password=self.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.s3acc_obj.logout_cortx_cli()
        self.log.info("Created s3 account")
        self.parallel_ios = None
        self.account_dict = dict()
        self.resources_dict = dict()
        self.account_prefix = "acc-reset-passwd-{}"
        self.io_bucket_name = "io-bkt1-reset-{}".format(perf_counter_ns())
        self.object_name = "obj-reset-object-{}".format(perf_counter_ns())
        self.file_path = os.path.join(self.test_dir_path, self.object_name)
        self.log.info("Login to CORTX CLI using s3 account")
        login = self.iam_obj.login_cortx_cli(
            username=self.s3acc_name, password=self.acc_password)
        assert_utils.assert_true(login[0], login[1])
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

        accounts = self.cli_test_obj.list_accounts_cortxcli()
        all_accounts = [acc["account_name"] for acc in accounts]
        self.log.info("setup %s", all_accounts)
        for acc in self.account_dict:
            if acc in all_accounts:
                self.cli_test_obj.login_cortx_cli(
                    username=acc, password=self.account_dict[acc])
                self.cli_test_obj.delete_iam_user(self.user_name)
                self.cli_test_obj.logout_cortx_cli()
                resp = self.cli_test_obj.delete_account_cortxcli(
                    account_name=acc, password=self.account_dict[acc])
                assert_utils.assert_true(resp[0], resp[1])
                self.log.info("Deleted %s account successfully", acc)
        del self.cli_test_obj
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
    @pytest.mark.tags("TEST-23398")
    def test_23398_create_iam_user(self):
        """
        Test ` s3iamuser create and View <user_name>`

        Test An S3 account owner shall be able to Create and View IAM user details and
        check s3 resources are intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_23398_ios", duration="0h1m")
        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.log.info("Created iam user with name %s", self.iam_password)
        self.log.info("Step 4. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_23398_ios")
        self.log.info(
            "Step 5. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-23399")
    def test_23399_list_user(self):
        """
        Verify IAM user show command and secret key should not be displayed.

        TEST create IAM users and verify secret keys should not be displayed thereafter
        while listing users and s3 resources should be intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_23399_ios", duration="0h1m")
        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Created iam user with name %s", self.user_name)
        self.log.info(
            "Step 4: Verifying show command is able to list user in all format(json,xml,table)")
        # show command with json format
        resp = self.iam_obj.list_iam_user(output_format="json")[1]["iam_users"]

        user_list = [user["user_name"]
                     for user in resp if "iam_user" in user["user_name"]]
        assert_utils.assert_list_item(user_list, self.user_name)

        # show command with xml format
        resp = self.iam_obj.list_iam_user(output_format="xml")[1]
        user_list = [each["iam_users"]["user_name"]
                     for each in resp if each.get("iam_users")]
        assert_utils.assert_list_item(user_list, self.user_name)
        self.log.info("Step 5. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_23399_ios")
        self.log.info(
            "Step 6. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info(
            "Verified show command is able to list user in all format(json,xml,table)")
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-23400")
    def test_23400_create_access_key(self):
        """
        Create or regenerate access keys for IAM user through CLI

        TEST An S3 account owner shall be able to create or regenerate an access key for IAM users
        and s3 resources should be intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_23400_ios", duration="0h1m")
        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.log.info("Created iam user with name %s", self.user_name)
        self.log.info("Step 4: Creating access key for IAM user %s", self.user_name)
        create_access_key = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        self.log.info("Created access key for IAM user %s", self.user_name)
        self.log.info("Step 5: Verify access key is created")
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert_utils.assert_in(create_access_key[1]["access_key"], access_keys)
        self.log.info("Verified access key is created")
        self.log.info("Step 6. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_23400_ios")
        self.log.info(
            "Step 7. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-23401")
    def test_23401_delete_iam_user(self):
        """
        Test that ` s3iamuser delete <iam_user_name>` must delete the given IAM user

        TEST An S3 account owner can delete IAM users and
        s3 resources should be intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_23401_ios", duration="0h1m")

        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.log.info("Created iam user with name %s", self.user_name)
        self.log.info("Deleting iam user with name %s", self.user_name)
        resp = self.iam_obj.delete_iam_user(self.user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.log.info("Step 4. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_23401_ios")
        self.log.info(
            "Step 5. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info("Deleted iam user with name %s", self.user_name)
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-23402")
    def test_23402_check_access_key_count(self):
        """
        Verify IAM user can not create more than two access keys.

        TEST to create two access keys per IAM user and
        s3 resources should be intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_23402_ios", duration="0h1m")
        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.log.info("Created iam user with name %s", self.iam_password)
        self.log.info("Step 4: Creating access key for IAM user %s", self.user_name)
        create_access_key = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        iam_access_key = create_access_key[1]["access_key"]
        self.log.info("Created access key for IAM user %s", self.user_name)
        self.log.info(
            "Step 5: Verify two access keys are present for IAM user %s",
            self.user_name)
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert_utils.assert_in(iam_access_key, access_keys)
        assert_utils.assert_equal(len(access_keys), 2)
        self.log.info(
            "Verified two access keys are present for IAM user %s",
            self.user_name)
        self.log.info(
            "Step 6: Verify IAM user can not have more than two access keys")
        resp = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "exceeded quota")
        self.log.info(resp)
        self.log.info(
            "Verified IAM user can not have more than two access keys")
        self.log.info("Step 7. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_23402_ios")
        self.log.info(
            "Step 8. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-23463")
    def test_23463_crud_with_another_access_key(self):
        """
        Verify CRUD Operations with regenreated another access key

        TEST IAM users should be able to access and perform CRUD operations on resources
        with another access key and s3 resources should be intact while S3 IO's are in progress.
        """
        self.log.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_23463_ios", duration="0h1m")
        self.log.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.log.info("Created iam user with name %s", self.iam_password)
        self.log.info("Step 4: Creating access key for IAM user %s", self.user_name)
        create_access_key = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        iam_access_key = create_access_key[1]["access_key"]
        self.log.info("Created access key for IAM user %s", self.user_name)
        self.log.info("Step 5: Verify access key is created")
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert_utils.assert_in(iam_access_key, access_keys)
        self.log.info("Verified access key is created")
        self.log.info("Step 6: Deleting access key of IAM user %s", self.user_name)
        resp = self.access_key_obj.delete_s3access_key(
            access_key=iam_access_key, user_name=self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Deleted access key of IAM user %s", self.user_name)
        self.log.info(
            "Step 7: Verify access key is deleted for IAM user %s",
            self.user_name)
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert_utils.assert_not_in(iam_access_key, access_keys)
        self.log.info(
            "Verified access key is deleted for IAM user %s",
            self.user_name)

        self.log.info("Step 8. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_23463_ios")
        self.log.info(
            "Step 9. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.log.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
