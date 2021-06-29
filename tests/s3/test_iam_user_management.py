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
import time
import logging
import pytest
from multiprocessing import Process
from commons.helpers.health_helper import Health
from commons.utils import assert_utils, system_utils
from commons.helpers import node_helper
from commons import cortxlogging as log
from config import CMN_CFG
from config import CSM_CFG
from config import S3_CFG
from scripts.s3_bench import s3bench
from libs.s3 import S3H_OBJ, s3_test_lib
from libs.csm.cli.cortxcli_iam_user import CortxCliIamUser
from libs.csm.cli.cortx_cli_s3_accounts import CortxCliS3AccountOperations
from libs.csm.cli.cortx_cli_s3access_keys import CortxCliS3AccessKeys

S3_OBJ = s3_test_lib.S3TestLib()


class TestIAMUserManagement:
    """IAM user Testsuite for CLI"""

    @classmethod
    def setup_class(cls):
        """
        It will perform all prerequisite test suite steps if any.
            - Initialize few common variables
            - Creating s3 account to perform IAM test cases
        """
        cls.logger = logging.getLogger(__name__)
        cls.logger.info("STARTED : Setup operations for test suit")
        cls.iam_password = CSM_CFG["CliConfig"]["iam_user"]["password"]
        cls.acc_password = CSM_CFG["CliConfig"]["s3_account"]["password"]
        cls.user_name = None
        cls.iam_obj = CortxCliIamUser()
        cls.iam_obj.open_connection()
        cls.node_helper_obj = node_helper.Node(
            hostname=CMN_CFG["csm"]["mgmt_vip"],
            username=CMN_CFG["csm"]["csm_admin_user"]["username"],
            password=CMN_CFG["csm"]["csm_admin_user"]["password"])
        cls.s3acc_obj = CortxCliS3AccountOperations(
            session_obj=cls.iam_obj.session_obj)
        cls.access_key_obj = CortxCliS3AccessKeys(
            session_obj=cls.iam_obj.session_obj)
        cls.s3acc_name = "{}_{}".format("cli_s3acc", int(time.time()))
        cls.s3acc_email = "{}@seagate.com".format(cls.s3acc_name)
        cls.logger.info("Creating s3 account with name %s", cls.s3acc_name)
        resp = cls.s3acc_obj.login_cortx_cli()
        assert_utils.assert_true(resp[0], resp[1])
        resp = cls.s3acc_obj.create_s3account_cortx_cli(
            account_name=cls.s3acc_name,
            account_email=cls.s3acc_email,
            password=cls.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        cls.s3acc_obj.logout_cortx_cli()
        cls.logger.info("Created s3 account")
        cls.START_LOG_FORMAT = "##### Test started -  "
        cls.END_LOG_FORMAT = "##### Test Ended -  "

    def setup_method(self):
        """
        This function will be invoked prior to each test function in the module.
        It is performing below operations as pre-requisites.
            - Login to CORTX CLI as s3account user.
        """
        self.logger.info("STARTED : Setup operations for test function")
        self.logger.info("Login to CORTX CLI using s3 account")
        login = self.iam_obj.login_cortx_cli(
            username=self.s3acc_name, password=self.acc_password)
        assert_utils.assert_true(login[0], login[1])
        self.user_name = "{0}{1}".format("iam_user", str(int(time.time())))
        self.logger.info("ENDED : Setup operations for test function")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Delete IAM users created in a s3account
            - Log out from CORTX CLI console.
        """
        self.logger.info("STARTED : Teardown operations for test function")
        resp = self.iam_obj.list_iam_user(output_format="json")
        if resp[0]:
            resp = resp[1]["iam_users"]
            user_del_list = [user["user_name"]
                             for user in resp if "iam_user" in user["user_name"]]
            for each_user in user_del_list:
                self.logger.info(
                    "Deleting IAM user %s", each_user)
                resp = self.iam_obj.delete_iam_user(each_user)
                assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
                self.logger.info(
                    "Deleted IAM user %s", each_user)
        self.iam_obj.logout_cortx_cli()
        self.logger.info("ENDED : Teardown operations for test function")

    def teardown_class(cls):
        """
        This function will be invoked after test suit.
        It is performing below operations as pre-requisites.
            - Deleting S3 account
            - Logout from cortxcli
        """
        cls.logger.info("Deleting s3 account %s", cls.s3acc_name)
        resp = cls.s3acc_obj.login_cortx_cli(
            username=cls.s3acc_name, password=cls.acc_password)
        assert_utils.assert_true(resp[0], resp[1])
        resp = cls.s3acc_obj.delete_s3account_cortx_cli(
            account_name=cls.s3acc_name)
        assert_utils.assert_true(resp[0], resp[1])
        cls.s3acc_obj.logout_cortx_cli()
        cls.iam_obj.close_connection()
        cls.logger.info("Deleted s3 account %s", cls.s3acc_name)

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
        resp = S3_OBJ.create_bucket(bucket)
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

    def validate_parallel_execution(self, log_prefix=None):
        """Check parallel execution failure."""
        self.log.info("S3 parallel ios log validation started.")
        log_file_list = system_utils.list_dir(s3bench.LOG_DIR)
        log_path = None
        for filename in log_file_list:
            if filename.startswith(log_prefix):
                log_path = os.path.join(s3bench.LOG_DIR, filename)
        self.log.info("IO log path: %s", log_path)
        assert_utils.assert_is_not_none(
            log_path, "failed to generate logs for parallel S3 IO.")
        lines = open(log_path).readlines()
        resp_filtered = [
            line for line in lines if 'Errors Count:' in line and "reportFormat" not in line]
        self.log.info("'Error count' filtered list: %s", resp_filtered)
        for response in resp_filtered:
            assert_utils.assert_equal(
                int(response.split(":")[1].strip()), 0, response)
        self.log.info("Observed no Error count in io log.")
        error_kws = ["with error ", "panic", "status code", "exit status 2"]
        for error in error_kws:
            assert_utils.assert_not_equal(
                error, ",".join(lines), f"{error} Found in S3Bench Run.")
        self.log.info("Observed no Error keyword '%s' in io log.", error_kws)
        system_utils.remove_file(log_path)
        self.log.info("S3 parallel ios log validation completed.")

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
                resp = S3_OBJ.object_list(self.io_bucket_name)
                self.log.info(resp)
                self.parallel_ios.join()
                self.log.info(
                    "Parallel IOs stopped: %s",
                    not self.parallel_ios.is_alive())
            if log_prefix:
                self.validate_parallel_execution(log_prefix)


    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-23398")
    def test_23398_create_iam_user(self):
        """
        Test that ` s3iamuser create <user_name>` with
        correct username and password should create new IAM user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_23398_ios", duration="0h1m")
        self.logger.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.iam_password)
        self.log.info("Step 4. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_22794_ios")
        self.log.info(
            "Step 5. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())


    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-23399")
    def test_23399_list_user(self):
        """
        Initiating the test case to verify IAM user show command and secret key should not
        be displayed.
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_23401_ios", duration="0h1m")
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(
            user_name=self.user_name,
            password=self.iam_password,
            confirm_password=self.iam_password)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Created iam user with name %s", self.user_name)
        self.logger.info(
            "Verifying show command is able to list user in all format(json,xml,table)")
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
        self.log.info("Step 4. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_22794_ios")
        self.log.info(
            "Step 5. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.logger.info(
            "Verified show command is able to list user in all format(json,xml,table)")
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())


    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-23400")
    def test_23400_create_access_key(self):
        """
        Create access keys for IAM user through CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_23400_ios", duration="0h1m")
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.user_name)
        self.logger.info("Creating access key for IAM user %s", self.user_name)
        create_access_key = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        self.logger.info("Created access key for IAM user %s", self.user_name)
        self.logger.info("Verify access key is created")
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert create_access_key[1]["access_key"] in access_keys
        self.logger.info("Verified access key is created")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_23400_ios")
        self.log.info(
            "Step 5. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.release_regression
    @pytest.mark.tags("TEST-23401")
    def test_23401_delete_iam_user(self):
        """
        Test that ` s3iamuser delete <iam_user_name>` must delete the given IAM user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_23401_ios", duration="0h1m")

        self.logger.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.user_name)
        self.logger.info("Deleting iam user with name %s", self.user_name)
        resp = self.iam_obj.delete_iam_user(self.user_name)
        assert_utils.assert_exact_string(resp[1], "IAM User Deleted")
        self.log.info("Step 4. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_22794_ios")
        self.log.info(
            "Step 5. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.logger.info("Deleted iam user with name %s", self.user_name)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-23402")
    def test_23402_check_access_key_count(self):
        """
        Verify IAM user can not create more than two access keys
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        self.check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_23398_ios", duration="0h1m")
        access_key_status = "Inactive"
        self.logger.info("Step 3: Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.iam_password)
        self.logger.info("Creating access key for IAM user %s", self.user_name)
        create_access_key = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        iam_access_key = create_access_key[1]["access_key"]
        self.logger.info("Created access key for IAM user %s", self.user_name)
        self.logger.info(
            "Verify two access keys are present for IAM user %s",
            self.user_name)
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert iam_access_key in access_keys
        assert len(access_keys) == 2
        self.logger.info(
            "Verified two access keys are present for IAM user %s",
            self.user_name)
        self.logger.info(
            "Verify IAM user can not have more than two access keys")
        resp = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_exact_string(resp[1], "exceeded quota")
        self.logger.info(resp)
        self.logger.info(
            "Verified IAM user can not have more than two access keys")
        self.log.info("Step 4. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_22794_ios")
        self.log.info(
            "Step 5. Check cluster status, all services are running after completing test.")
        self.check_cluster_health()
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())


    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-23463")
    def test_23463_delete_access_key(self):
        """
        Verify delete access key for IAM user
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.iam_password)
        self.logger.info("Creating access key for IAM user %s", self.user_name)
        create_access_key = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        iam_access_key = create_access_key[1]["access_key"]
        self.logger.info("Created access key for IAM user %s", self.user_name)
        self.logger.info("Verify access key is created")
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert iam_access_key in access_keys
        self.logger.info("Verified access key is created")
        self.logger.info("Deleting access key of IAM user %s", self.user_name)
        resp = self.access_key_obj.delete_s3access_key(
            access_key=iam_access_key, user_name=self.user_name)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info("Deleted access key of IAM user %s", self.user_name)
        self.logger.info(
            "Verify access key is deleted for IAM user %s",
            self.user_name)
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert iam_access_key not in access_keys
        self.logger.info(
            "Verified access key is deleted for IAM user %s",
            self.user_name)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-23463")
    def test_23463_update_access_key_status(self):
        """
        Update status of access for IAM user through CLI
        """
        self.logger.info("%s %s", self.START_LOG_FORMAT, log.get_frame())
        access_key_status = "Inactive"
        self.logger.info("Creating iam user with name %s", self.user_name)
        resp = self.iam_obj.create_iam_user(user_name=self.user_name,
                                            password=self.iam_password,
                                            confirm_password=self.iam_password)
        assert_utils.assert_exact_string(resp[1], self.user_name)
        self.logger.info("Created iam user with name %s", self.iam_password)
        self.logger.info("Creating access key for IAM user %s", self.user_name)
        create_access_key = self.access_key_obj.create_s3_iam_access_key(
            user_name=self.user_name)
        assert_utils.assert_true(create_access_key[0], create_access_key[1])
        iam_access_key = create_access_key[1]["access_key"]
        self.logger.info("Created access key for IAM user %s", self.user_name)
        self.logger.info("Verify access key is created")
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        access_keys = [i["access_key_id"] for i in resp["access_keys"]]
        assert iam_access_key in access_keys
        self.logger.info("Verified access key is created")
        self.logger.info(
            "Updating status of access key of user %s",
            self.user_name)
        resp = self.access_key_obj.update_s3access_key(
            access_key=iam_access_key,
            user_name=self.user_name,
            status=access_key_status)
        assert_utils.assert_true(resp[0], resp[1])
        self.logger.info(
            "Updated status of access key of user %s",
            self.user_name)
        self.logger.info(
            "Verify status is updated for access key %s",
            iam_access_key)
        resp = self.access_key_obj.show_s3access_key(user_name=self.user_name)
        updated_status = [i["status"] for i in resp["access_keys"]
                          if iam_access_key == i["access_key_id"]]
        assert_utils.assert_equals(updated_status[0], access_key_status, resp)
        self.logger.info(
            "Verified status is updated for access key %s",
            iam_access_key)
        self.logger.info("%s %s", self.END_LOG_FORMAT, log.get_frame())
