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

"""S3 Account User Management delete/view s3 account, create/regenerate access key test module."""

import logging
import os
import time
from http import HTTPStatus
from multiprocessing import Process
from time import perf_counter_ns

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from config.s3 import S3_CFG
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.s3 import S3H_OBJ
from libs.s3 import s3_test_lib
from libs.s3.csm_rest_cli_interface_lib import CSMAccountIntOperations
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI
from scripts.s3_bench import s3bench


# pylint: disable-msg=too-many-instance-attributes
class TestAccountUserMgmtDeleteAccountCreateAccessKey:
    """S3 Account User Management delete/view s3 account,create/regenerate access key test suite."""

    # pylint: disable-msg=too-many-statements
    @pytest.yield_fixture(autouse=True)
    def setup(self):
        """
        Function will be invoked test before and after yield part each test case execution.

        1. Create bucket name, object name, account name.
        2. Check cluster status, all services are running.
        """
        self.log = logging.getLogger(__name__)
        self.s3_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.log.info("STARTED: test setup.")
        self.parallel_ios = None
        self.account_dict = dict()
        self.resources_dict = dict()
        self.csm_user_list = list()
        self.log.info("Check s3 bench tool installed.")
        res = system_utils.path_exists(s3bench.S3_BENCH_PATH)
        assert_utils.assert_true(res, f"S3bench tools not installed: {s3bench.S3_BENCH_PATH}")
        self.test_dir_path = os.path.join(
            TEST_DATA_FOLDER, "TestAccountUserManagementDeleteAccount")
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.s3rc_obj = S3AccountOperations()
        self.csmrc_obj = CSMAccountIntOperations()
        self.s3acc_op_rest = S3AccountOperationsRestAPI()
        self.s3_accounts = RestS3user()
        self.account_prefix = "acc-delete-user-{}"
        self.csm_user = "csm-user-{}".format(time.perf_counter_ns())
        self.s3acc_name1 = "acc1-delete-user-{}".format(time.perf_counter_ns())
        self.s3acc_name2 = "acc2-delete-user-{}".format(time.perf_counter_ns())
        self.email_id = "{}@seagate.com"
        self.io_bucket_name = "io-bkt1-{}".format(perf_counter_ns())
        self.bucket_name1 = "bkt1-{}".format(perf_counter_ns())
        self.bucket_name2 = "bkt2-{}".format(perf_counter_ns())
        self.object_name = "obj1-{}".format(time.perf_counter_ns())
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.new_passwd = S3_CFG["CliConfig"]["iam_user"]["password"]
        self.csm_passwd = S3_CFG["CliConfig"]["csm_user"]["password"]
        self.file_path = os.path.join(self.test_dir_path, self.object_name)
        self.log.info("ENDED: test setup.")
        yield
        self.log.info("STARTED: test teardown.")
        if system_utils.path_exists(self.file_path):
            system_utils.remove_file(self.file_path)
        if self.parallel_ios:
            if self.parallel_ios.is_alive():
                self.parallel_ios.join()
        self.log.info("Deleting all buckets/objects created during TC execution")
        bkt_list = self.s3_obj.bucket_list()[1]
        if self.io_bucket_name in bkt_list:
            resp = self.s3_obj.delete_bucket(self.io_bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step cleanup resources.")
        for resource in self.resources_dict:
            if resource:
                resp = resource.delete_bucket(self.resources_dict[resource], force=True)
                assert_utils.assert_true(resp[0], resp[1])
        resp, accounts = self.s3rc_obj.list_s3_accounts()
        self.log.info("setup %s", accounts)
        for acc in self.account_dict:
            if acc in accounts:
                resp = self.s3rc_obj.delete_s3_account(acc)
                assert_utils.assert_true(resp[0], resp[1])
                self.log.info("Deleted %s account successfully", acc)
        for user in self.csm_user_list:
            self.csmrc_obj.delete_csm_account_rest_cli(user)
        del self.s3rc_obj
        del self.csmrc_obj
        del self.s3acc_op_rest
        del self.s3_accounts
        self.log.info("ENDED: test teardown.")

    def check_cluster_health(self):
        """Check the cluster health."""
        self.log.info("Check cluster status, all services are running.")
        nodes = CMN_CFG["nodes"]
        self.log.info(nodes)
        for _, node in enumerate(nodes):
            health_obj = Health(hostname=node["hostname"],
                                username=node["username"],
                                password=node["password"])
            resp = health_obj.check_node_health(resource_cleanup=True)
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
            end_point=S3_CFG["s3b_url"],
            num_clients=kwargs["num_clients"],
            num_sample=kwargs["num_sample"],
            obj_name_pref=kwargs["obj_name_pref"],
            obj_size=obj_size,
            duration=duration,
            log_file_prefix=log_file_prefix)
        self.log.info(resp)
        assert_utils.assert_true(os.path.exists(resp[1]), f"failed to generate log: {resp[1]}")
        self.log.info("ENDED: s3 io's operations.")

    def start_stop_validate_parallel_s3ios(
            self, ios=None, log_prefix=None, duration="0h1m"):
        """Start/stop parallel s3 io's and validate io's worked successfully."""
        if ios == "Start":
            self.parallel_ios = Process(
                target=self.s3_ios, args=(self.io_bucket_name, log_prefix, duration))
            if not self.parallel_ios.is_alive():
                self.parallel_ios.start()
            self.log.info("Parallel IOs started: %s for duration: %s",
                          self.parallel_ios.is_alive(), duration)
        if ios == "Stop":
            if self.parallel_ios.is_alive():
                resp = self.s3_obj.object_list(self.io_bucket_name)
                self.log.info(resp)
                self.parallel_ios.join()
                self.log.info("Parallel IOs stopped: %s", not self.parallel_ios.is_alive())
            if log_prefix:
                resp = system_utils.validate_s3bench_parallel_execution(
                    s3bench.LOG_DIR, log_prefix)
                assert_utils.assert_true(resp[0], resp[1])

    def create_s3_acc(
            self,
            account_name: str = None,
            email_id: str = None,
            password: str = None) -> tuple:
        """
        Function will create s3 accounts with specified account name and email-id.

        :param password: account password.
        :param str account_name: Name of account to be created.
        :param str email_id: Email id for account creation.
        :return tuple: It returns multiple values such as access_key,
        secret_key and s3 objects which required to perform further operations.
        :return tuple
        """
        self.log.info(
            "Step : Creating account with name %s and email_id %s", account_name, email_id)
        create_account = self.s3rc_obj.create_s3_account(account_name, email_id, password)
        assert_utils.assert_true(create_account[0], create_account[1])
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        self.account_dict[account_name] = password
        assert_utils.assert_equal(
            create_account[1]["account_name"],
            account_name,
            f"Failed to create account '{account_name}'")
        self.log.info("Step Successfully created the s3 account")
        s3_obj = s3_test_lib.S3TestLib(
            access_key,
            secret_key,
            endpoint_url=S3_CFG["s3_url"],
            s3_cert_path=S3_CFG["s3_cert_path"],
            region=S3_CFG["region"])
        response = (s3_obj, access_key, secret_key)
        return response

    def create_n_number_s3accounts(
            self,
            csm_user=None,
            csm_passwd=None,
            cnt=1) -> list:
        """
        Create n numbers of s3 accounts.

        :param csm_user: Account name of csm user.
        :param csm_passwd: Password of the csm user.
        :param cnt: s3 accounts count.
        :return: accounts list.
        """
        account_list = []
        for i in range(cnt):
            acc_name = "{}-{}".format(self.account_prefix.format(time.perf_counter_ns()), i)
            email_id = self.email_id.format(acc_name)
            if csm_user:
                resp = self.csmrc_obj.create_s3_using_csm_rest_cli(
                    acc_name, email_id, self.s3acc_passwd, csm_user, csm_passwd)
                assert_utils.assert_true(resp[0], resp[1])
                self.account_dict[acc_name] = resp[1]['password']
                assert_utils.assert_equal(
                    resp[1]["account_name"], acc_name, f"Failed to create account '{acc_name}'")
            else:
                self.create_s3_acc(acc_name, email_id, self.s3acc_passwd)
            account_list.append(acc_name)

        return account_list

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_acc_mgnt_key
    @pytest.mark.regression
    @pytest.mark.tags("TEST-23321")
    @CTFailOn(error_handler)
    def test_23321(self):
        """
        Delete s3 account user.

        Test delete s3 account user own resources using csm admin user and check s3 resources are
        intact while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test delete s3 account user own resources using csm admin user and check"
            " s3 resources are intact while S3 IO's are in progress.")
        self.log.info("Step 1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-23321_s3bench_ios", duration="0h1m")
        self.log.info("Step 2. Create s3account s3acc.")
        s3_test_obj = self.create_s3_acc(
            self.s3acc_name1, self.email_id.format(self.s3acc_name1), self.s3acc_passwd)[0]
        self.log.info("Step 3. Create bucket s3bkt in s3acc account.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        self.log.info("Step 4. Create and upload objects to above s3bkt.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(self.bucket_name1, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5. Delete s3 account user own resources using csm admin user.")
        resp = self.s3acc_op_rest.delete_s3_account(self.s3acc_name1)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_in(
            "Account cannot be deleted as it owns some resources", resp[1], resp[1])
        self.log.info("Step 6. list and check all resources are intact.")
        resp = s3_test_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name, resp[1], "Failed to list bucket.")
        self.log.info("Step 7. Delete all resources.")
        resp = s3_test_obj.delete_bucket(self.bucket_name1, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 8. Delete s3 account user using csm admin user.")
        resp = self.s3acc_op_rest.delete_s3_account(self.s3acc_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Account Deleted", resp[1], resp[1])
        del self.account_dict[self.s3acc_name1]
        del self.resources_dict[s3_test_obj]
        self.log.info("Step 9. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-23321_s3bench_ios")
        self.log.info(
            "ENDED: Test delete s3 account user own resources using csm admin user and check"
            " s3 resources are intact while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_acc_mgnt_key
    @pytest.mark.lr
    @pytest.mark.tags("TEST-23322")
    @CTFailOn(error_handler)
    def test_23322(self):
        """
        Delete s3 account user.

        Test delete s3 account user own resources using csm user having manage role and check s3
        resources are intact while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test delete s3 account user own resources using csm user having manage role"
            " and check s3 resources are intact while S3 IO's are in progress.")
        self.log.info("Step 1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-23322_s3bench_ios", duration="0h1m")
        self.log.info("Step 2. Create csm user having manage role.")
        csm_user = self.csm_user.format(time.perf_counter_ns())
        csm_user_mail = self.email_id.format(csm_user)
        resp = self.csmrc_obj.create_csm_account_rest_cli(
            csm_user, csm_user_mail, self.csm_passwd, role="manage")
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_list.append(csm_user)
        self.log.info("Step 3. Create s3account s3acc.")
        s3_test_obj = self.create_s3_acc(
            self.s3acc_name1, self.email_id.format(self.s3acc_name1), self.s3acc_passwd)[0]
        self.log.info("Step 4. Create bucket s3bkt in s3acc account.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        self.log.info("Step 5. Create and upload objects to above s3bkt.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(self.bucket_name1, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6. delete s3 account user using csm user having manage role.")
        resp = self.s3acc_op_rest.delete_s3_account(
            self.s3acc_name1,
            login_as={"username": csm_user, "password": self.csm_passwd})
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_in(
            "Account cannot be deleted as it owns some resources", resp[1], resp[1])
        self.log.info("Step 7. list and check all resources are intact.")
        resp = s3_test_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name, resp[1], "Failed to list bucket.")
        self.log.info("Step 8. Delete all resources.")
        resp = s3_test_obj.delete_bucket(self.bucket_name1, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        del self.resources_dict[s3_test_obj]
        self.log.info("Step 9. Delete s3 account user using csm admin user.")
        resp = self.s3acc_op_rest.delete_s3_account(self.s3acc_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Account Deleted", resp[1], resp[1])
        del self.account_dict[self.s3acc_name1]
        self.log.info("Step 10. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-23322_s3bench_ios")
        self.log.info(
            "ENDED: Test delete s3 account user own resources using csm user having manage role"
            " and check s3 resources are intact while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.lr
    @pytest.mark.s3_acc_mgnt_key
    @pytest.mark.tags("TEST-23323")
    @CTFailOn(error_handler)
    def test_23323(self):
        """
        Delete s3 account user.

        Test delete s3 account user own resources using csm user having monitor role and check s3
        resources are intact while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test delete s3 account user own resources using csm user having monitor"
            " role and check s3 resources are intact while S3 IO's are in progress.")
        self.log.info("Step 1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-23323_s3bench_ios", duration="0h1m")
        self.log.info("Step 2. Create csm user having monitor role.")
        csm_user = self.csm_user.format(time.perf_counter_ns())
        csm_user_mail = self.email_id.format(csm_user)
        resp = self.csmrc_obj.create_csm_account_rest_cli(
            csm_user, csm_user_mail, self.csm_passwd, role="monitor")
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_list.append(csm_user)
        self.log.info("Step 3. Create s3account s3acc.")
        s3_test_obj = self.create_s3_acc(
            self.s3acc_name1, self.email_id.format(self.s3acc_name1), self.s3acc_passwd)[0]
        self.log.info("Step 4. Create bucket s3bkt in s3acc account.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        self.log.info("Step 5. Create and upload objects to above s3bkt.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(self.bucket_name1, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6. delete s3 account user using csm user having monitor role.")
        resp = self.s3_accounts.delete_s3_account_user(
            self.s3acc_name1, login_as={"username": csm_user, "password": self.csm_passwd})
        assert_utils.assert_equals(resp.status_code, HTTPStatus.FORBIDDEN)
        self.log.info("Step 7. list and check all resources are intact.")
        resp = s3_test_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name, resp[1], "Failed to list bucket.")
        self.log.info("Step 8. Delete all resources.")
        resp = s3_test_obj.delete_bucket(self.bucket_name1, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        del self.resources_dict[s3_test_obj]
        self.log.info("Step 9. Delete s3 account user using csm admin user.")
        resp = self.s3acc_op_rest.delete_s3_account(self.s3acc_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in("Account Deleted", resp[1], resp[1])
        del self.account_dict[self.s3acc_name1]
        self.log.info("Step 10. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-23323_s3bench_ios")
        self.log.info(
            "ENDED: Test delete s3 account user own resources using csm user having monitor role"
            " and check s3 resources are intact while S3 IO's are in progress.")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_acc_mgnt_key
    @pytest.mark.tags("TEST-23324")
    @CTFailOn(error_handler)
    def test_23324(self):
        """
        Delete s3 account user.

        Test s3 account user is not able to delete other s3 account user and check resource intact
        for both account while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test s3 account user is not able to delete other s3 account user and check"
            " resource intact for both account while S3 IO's are in progress.")
        self.log.info("Step 1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-23324_s3bench_ios", duration="0h1m")
        self.log.info("Step 2. Create two s3account s3acc1, s3acc2.")
        s3_test_obj1 = self.create_s3_acc(
            self.s3acc_name1, self.email_id.format(self.s3acc_name1), self.s3acc_passwd)[0]
        s3_test_obj2 = self.create_s3_acc(
            self.s3acc_name2, self.email_id.format(self.s3acc_name2), self.s3acc_passwd)[0]
        self.log.info("Step 3. Create and upload objects to above s3bkt1, s3bkt2.")
        resp = s3_test_obj1.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj1] = self.bucket_name1
        resp = s3_test_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj2] = self.bucket_name2
        self.log.info("Step 4. Create and upload objects to above s3bkt1, s3bkt2.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj1.put_object(
            self.bucket_name1, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj2.put_object(self.bucket_name2, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5. delete s3 account user using other s3 account user.")
        resp = self.s3acc_op_rest.delete_s3_account(
            self.s3acc_name2,
            login_as={"username": self.s3acc_name1, "password": self.s3acc_passwd})
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_in("Access denied", resp[1], resp[1])
        self.log.info("Step 6. list and check all resources are intact.")
        resp = s3_test_obj1.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name, resp[1], "Failed to list bucket.")
        resp = s3_test_obj2.object_list(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name, resp[1], "Failed to list bucket.")
        self.log.info("Step 7. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-23324_s3bench_ios")
        self.log.info(
            "ENDED: Test s3 account user is not able to delete other s3 account user and check"
            " resource intact for both account while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.lr
    @pytest.mark.s3_acc_mgnt_key
    @pytest.mark.tags("TEST-23379")
    @CTFailOn(error_handler)
    def test_23379(self):
        """
        Delete s3 account user.

        Test delete n number of s3 account user using csm user having different role (admin,
        manage, monitor) while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test delete n number of s3 account user using csm user having different role "
            "(admin, manage, monitor) while S3 IO's are in progress.")
        self.log.info("Step 1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-23379_s3bench_ios", duration="0h5m")
        self.log.info("Step 2. Create N number s3account.")
        account_list = self.create_n_number_s3accounts(cnt=10)
        self.log.info("Step 3. Delete N number s3 account using csm admin user.")
        for name in account_list:
            resp = self.csmrc_obj.delete_s3_acc_using_csm_rest_cli(name)
            assert_utils.assert_true(resp[0], resp[1])
            del self.account_dict[name]
        self.log.info("Step 4. Create csm user having role manage.")
        csm_user = self.csm_user.format(time.perf_counter_ns())
        csm_user_mail = self.email_id.format(csm_user)
        resp = self.csmrc_obj.create_csm_account_rest_cli(
            csm_user, csm_user_mail, self.csm_passwd, role="manage")
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_list.append(csm_user)
        self.log.info("Step 5. Create N number s3account.")
        account_list = self.create_n_number_s3accounts(csm_user, self.csm_passwd, cnt=10)
        assert_utils.assert_equal(len(account_list), 10, "failed to create 10 accounts")
        self.log.info("Step 6. Delete N number s3 account using csm user having manage role.")
        for name in account_list:
            resp = self.csmrc_obj.delete_s3_acc_using_csm_rest_cli(
                name, csm_user=csm_user, csm_pwd=self.csm_passwd)
            assert_utils.assert_true(resp[0], resp[1])
            del self.account_dict[name]
        self.log.info("Step 7. Changes csm user role to monitor.")
        resp = self.csmrc_obj.edit_csm_user_rest_cli(
            csm_user=csm_user, csm_pwd=self.csm_passwd, role="monitor")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 8. Create N number s3account with non monitor user.")
        account_list = self.create_n_number_s3accounts(cnt=10)
        self.log.info("Step 9. Delete N number s3 account using csm user having monitor role.")
        for name in account_list:
            resp = self.s3_accounts.delete_s3_account_user(
                name, login_as={"username": csm_user, "password": self.csm_passwd})
            assert_utils.assert_equals(resp.status_code, HTTPStatus.FORBIDDEN)
        self.log.info("Step 10. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-23379_s3bench_ios")
        self.log.info(
            "ENDED: Test delete n number of s3 account user using csm user having different role "
            "(admin, manage, monitor) while S3 IO's are in progress.")

    @pytest.mark.skip(reason="EOS-22292: CSM APIs which requires S3 Account login are unsupported")
    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_acc_mgnt_key
    @pytest.mark.tags("TEST-23380")
    @CTFailOn(error_handler)
    def test_23380(self):
        """
        Delete s3 account user.

        Test delete s3 account user with it's own password and check resources intact
        while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test delete s3 account user with it's own password and check resources intact"
            " while S3 IO's are in progress.")
        self.log.info("Step 1: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-23380_s3bench_ios", duration="0h1m")
        self.log.info("Step 2: create s3 accounts.")
        s3_test_obj = self.create_s3_acc(
            self.s3acc_name1, self.email_id.format(
                self.s3acc_name1), self.s3acc_passwd)[0]
        self.log.info("Step 3: Create and upload objects to above s3bkt.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(self.bucket_name1, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4: Delete s3 account user with it's own password.")
        resp = self.s3acc_op_rest.delete_s3_account(
            self.s3acc_name1,
            login_as={"username": self.s3acc_name1, "password": self.s3acc_passwd})
        assert_utils.assert_false(resp[0], resp[1])
        self.log.info("Step 5: list and check all resources are intact.")
        resp = s3_test_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name, resp[1], "Failed to list bucket.")
        self.log.info("Step 6. Delete all resources.")
        resp = s3_test_obj.delete_bucket(self.bucket_name1, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        del self.resources_dict[s3_test_obj]
        self.log.info("Step 7. Delete s3 account user using it's own credentials.")
        resp = self.s3_accounts.delete_s3_account_user(
            self.s3acc_name1,
            login_as={"username": self.s3acc_name1, "password": self.s3acc_passwd})
        assert_utils.assert_equals(resp.status_code, HTTPStatus.OK)
        assert_utils.assert_in("Account Deleted", resp.json()["message"], resp)
        del self.account_dict[self.s3acc_name1]
        self.log.info("Step 8: Stop and validate S3 IOs")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-23380_s3bench_ios")
        self.log.info(
            "ENDED: Test delete s3 account user with it's own password and check resources intact"
            " while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.lr
    @pytest.mark.s3_acc_mgnt_key
    @pytest.mark.tags("TEST-23381")
    @CTFailOn(error_handler)
    def test_23381(self):
        """
        Delete s3 account user.

        Test an admin shall be able to view all s3 accounts created using csm user having different
        role (admin, manage, monitor) while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test an admin shall be able to view all s3 accounts created using csm user"
            " having different role (admin, manage, monitor) while S3 IO's are in progress.")
        self.log.info("Step 1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-23381_s3bench_ios", duration="0h5m")
        self.log.info("Step 2. Create N number s3account.")
        account_list = self.create_n_number_s3accounts(cnt=10)
        assert_utils.assert_equal(len(account_list), 10, "Failed to create s3 accounts.")
        self.log.info("Step 3. Create csm user having role manage.")
        csm_user = self.csm_user.format(time.perf_counter_ns())
        csm_user_mail = self.email_id.format(csm_user)
        resp = self.csmrc_obj.create_csm_account_rest_cli(
            csm_user, csm_user_mail, self.csm_passwd, role="manage")
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_list.append(csm_user)
        self.log.info("Step 4. Create N number s3account.")
        account_list = self.create_n_number_s3accounts(csm_user, self.csm_passwd, 10)
        assert_utils.assert_equal(len(account_list), 10, "failed to create 10 accounts")
        self.log.info(
            "Step 6. view s3 account user created with different roles using csm user"
            " having admin role.")
        resp = self.csmrc_obj.csm_user_show_s3_acc_rest_cli()
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-23381_s3bench_ios")
        self.log.info(
            "ENDED: Test an admin shall be able to view all s3 accounts created using csm user"
            " having different role (admin, manage, monitor) while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.lr
    @pytest.mark.s3_acc_mgnt_key
    @pytest.mark.tags("TEST-23382")
    @CTFailOn(error_handler)
    def test_23382(self):
        """
        Delete s3 account user.

        Test an S3 account owner shall be able to view the details of the S3 account
        while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test an S3 account owner shall be able to view the details of the S3 account"
            " while S3 IO's are in progress.")
        self.log.info("Step 1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-23382_s3bench_ios", duration="0h5m")
        self.log.info("Step 2. Create N number s3account.")
        account_list = self.create_n_number_s3accounts(cnt=10)
        assert_utils.assert_equal(len(account_list), 10, "Failed to create s3 accounts.")
        self.log.info("Step 3. view s3 account using csm admin user.")
        resp = self.csmrc_obj.csm_user_show_s3_acc_rest_cli()
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4. Create csm user having role manage.")
        csm_user = self.csm_user.format(time.perf_counter_ns())
        csm_user_mail = self.email_id.format(csm_user)
        resp = self.csmrc_obj.create_csm_account_rest_cli(
            csm_user, csm_user_mail, self.csm_passwd, role="manage")
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_list.append(csm_user)
        self.log.info("Step 5. Create N number s3account.")
        account_list = self.create_n_number_s3accounts(csm_user, self.csm_passwd, 10)
        assert_utils.assert_equal(len(account_list), 10, "failed to create 10 accounts")
        self.log.info("Step 6. View s3 account using csm user having manage role.")
        resp = self.csmrc_obj.csm_user_show_s3_acc_rest_cli(csm_user, self.csm_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 7. Changes csm user role to monitor.")
        resp = self.csmrc_obj.edit_csm_user_rest_cli(
            csm_user=csm_user, csm_pwd=self.csm_passwd, role="monitor")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 8. view s3 account using csm user having monitor role.")
        resp = self.csmrc_obj.csm_user_show_s3_acc_rest_cli(csm_user, self.csm_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 9. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-23382_s3bench_ios")
        self.log.info(
            "ENDED: Test an S3 account owner shall be able to view the details of the S3 account"
            " while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.lr
    @pytest.mark.s3_acc_mgnt_key
    @pytest.mark.tags("TEST-23395")
    @CTFailOn(error_handler)
    def test_23395(self):
        """
        Delete s3 account user.

        Test s3 account owner shall be able to create or regenerate an access key for the s3 account
         while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test s3 account owner shall be able to create or regenerate an access key"
            " for the s3 account while S3 IO's are in progress.")
        self.log.info("Step 1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-23395_s3bench_ios", duration="0h5m")
        self.log.info(
            "Step 2. Create N number s3account with csm user having different role "
            "(admin, manage, monitor).")
        account_list1 = self.create_n_number_s3accounts(cnt=10)
        assert_utils.assert_equal(len(account_list1), 10, "Failed to create s3 accounts.")
        self.log.info("Create csm user having role manage.")
        csm_user = self.csm_user.format(time.perf_counter_ns())
        csm_user_mail = self.email_id.format(csm_user)
        resp = self.csmrc_obj.create_csm_account_rest_cli(
            csm_user, csm_user_mail, self.csm_passwd, role="manage")
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_list.append(csm_user)
        self.log.info("Create N number s3account.")
        account_list2 = self.create_n_number_s3accounts(csm_user, self.csm_passwd, 10)
        assert_utils.assert_equal(len(account_list2), 10, "failed to create 10 accounts")
        self.log.info(
            "Step 3. S3 account owner shall be able to create or regenerate an access "
            "key for the s3 account.")
        for user in account_list1:
            resp = self.s3rc_obj.generate_s3_access_key(user, self.account_dict[user])
            assert_utils.assert_true(resp[0], resp[1])
        for user in account_list2:
            resp = self.s3rc_obj.generate_s3_access_key(user, self.account_dict[user])
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 4. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-23395_s3bench_ios")
        self.log.info(
            "ENDED: Test s3 account owner shall be able to create or regenerate an "
            "access key for the s3 account while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.s3_acc_mgnt_key
    @pytest.mark.tags("TEST-23396")
    @CTFailOn(error_handler)
    def test_23396(self):
        """
        Delete s3 account user.

        Test s3 account owner shall be able to regenerate an access key for the s3 account and
        check resources are intact with other access key while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test s3 account owner shall be able to regenerate an access key"
            " for the s3 account and check resources are intact with other access key"
            " while S3 IO's are in progress.")
        self.log.info("Step 1. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-23396_s3bench_ios", duration="0h5m")
        self.log.info("Step 2. Create s3account s3acc.")
        s3_test_obj = self.create_s3_acc(
            self.s3acc_name1, self.email_id.format(self.s3acc_name1), self.s3acc_passwd)[0]
        self.log.info("Step 3. Create bucket s3bkt in s3acc account.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.log.info("Step 4. Create and upload objects to above s3bkt.")
        resp = system_utils.create_file(self.file_path, count=2)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(self.bucket_name1, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 5. S3 account owner shall be able to create or regenerate an access key"
            " for the s3 account")
        resp = self.s3rc_obj.generate_s3_access_key(self.s3acc_name1, self.s3acc_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6. Check resources are intact with regenerated key.")
        s3_obj = s3_test_lib.S3TestLib(resp[1]["access_key"], resp[1]["secret_key"])
        bucket_list = s3_obj.bucket_list()
        assert_utils.assert_true(bucket_list[0], bucket_list[1])
        assert_utils.assert_in(self.bucket_name1, bucket_list[1], bucket_list)
        resp = s3_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name, resp[1], resp)
        self.log.info("Step 7. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(ios="Stop", log_prefix="TEST-23396_s3bench_ios")
        for bucket_name in bucket_list[1]:
            resp = s3_obj.delete_bucket(bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "ENDED: Test s3 account owner shall be able to regenerate an access key"
            " for the s3 account and check resources are intact with other access key"
            " while S3 IO's are in progress.")
