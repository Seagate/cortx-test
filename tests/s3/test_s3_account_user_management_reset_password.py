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

"""Account user management reset password test module."""

import logging
import os
import time
from multiprocessing import Process
from time import perf_counter_ns

import pytest
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.params import TEST_DATA_FOLDER
from commons.utils import assert_utils
from commons.utils import system_utils
from config import S3_CFG
from libs.s3 import S3H_OBJ
from libs.s3 import s3_test_lib
from libs.s3.cortxcli_test_lib import CSMAccountOperations
from libs.s3.cortxcli_test_lib import CortxCliTestLib
from libs.s3.s3_rest_cli_interface_lib import S3AccountOperations
from libs.s3.s3_restapi_test_lib import S3AuthServerRestAPI
from libs.s3.s3_common_test_lib import get_ldap_creds
from libs.s3.s3_common_test_lib import check_cluster_health
from libs.s3.s3_common_test_lib import create_s3_acc
from scripts.s3_bench import s3bench


class TestAccountUserManagementResetPassword:
    """Account user management reset password TestSuite."""

    @pytest.yield_fixture(autouse=True)
    def setup(self):
        """
        Function will be invoked test before and after yield part each test case execution.

        1. Create bucket name, object name, account name.
        2. Check cluster status, all services are running.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: test setup.")
        self.s3_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        self.parallel_ios = None
        self.account_dict = dict()
        self.resources_dict = dict()
        self.csm_user_list = list()
        self.log.info("Check s3 bench tool installed.")
        res = system_utils.path_exists(s3bench.S3_BENCH_PATH)
        assert_utils.assert_true(
            res, f"S3bench tools not installed: {s3bench.S3_BENCH_PATH}")
        self.test_dir_path = os.path.join(
            TEST_DATA_FOLDER, "TestAccountUserManagementResetPassword")
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.cli_test_obj = CortxCliTestLib()
        self.csm_obj = CSMAccountOperations()
        self.rest_obj = S3AccountOperations()
        self.s3auth_obj = S3AuthServerRestAPI()
        self.account_prefix = "acc-reset-passwd-{}"
        self.csm_user = "csm-user-{}".format(time.perf_counter_ns())
        self.s3acc_name1 = "acc1-reset-passwd-{}".format(
            time.perf_counter_ns())
        self.s3acc_name2 = "acc2-reset-passwd-{}".format(
            time.perf_counter_ns())
        self.email_id = "{}@seagate.com"
        self.io_bucket_name = "io-bkt1-reset-{}".format(perf_counter_ns())
        self.bucket_name1 = "bkt1-reset-{}".format(perf_counter_ns())
        self.bucket_name2 = "bkt2-reset-{}".format(perf_counter_ns())
        self.object_name = "obj-reset-object-{}".format(time.perf_counter_ns())
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
            resp = self.rest_obj.delete_s3_account(acc)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Deleted %s account successfully", acc)
        for user in self.csm_user_list:
            resp = self.csm_obj.csm_user_delete(user)
            assert_utils.assert_true(resp[0], resp[1])
        del self.cli_test_obj
        del self.csm_obj
        self.log.info("ENDED: test teardown.")

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
                resp = system_utils.validate_s3bench_parallel_execution(
                    s3bench.LOG_DIR, log_prefix)
                assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22793")
    @CTFailOn(error_handler)
    def test_22793(self):
        """
        Reset s3 account password.

        Test s3 account user is not able to reset password of other s3 account user and create
        resources for both account while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test s3 account user is not able to reset password of other s3 account user"
            " and create resources for both account while S3 IO's are in progress.")
        self.log.info(
            "Step 1: Check cluster status, all services are running before starting test.")
        check_cluster_health()
        self.log.info("Step 2: Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-22793_s3bench_ios", duration="0h1m")
        self.log.info("Step 3: Create two s3account s3acc1, s3acc2.")
        s3_test_obj1 = create_s3_acc(
            self.s3acc_name1, self.email_id.format(
                self.s3acc_name1), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        s3_test_obj2 = create_s3_acc(
            self.s3acc_name2, self.email_id.format(
                self.s3acc_name2), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name2] = self.s3acc_passwd
        self.log.info("Step 4: Reset s3 account password using other s3 account user.")
        resp = self.csm_obj.reset_s3acc_password(
            self.s3acc_name1,
            self.s3acc_passwd,
            self.s3acc_name2,
            self.new_passwd)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_in(
            "Access denied. Cannot modify another S3 account.",
            resp[1],
            resp[1])
        self.log.info(
            "Step 5: Create bucket s3bkt1, s3bkt2 in s3acc1, s3acc2 account.")
        resp = s3_test_obj1.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj1] = self.bucket_name1
        resp = s3_test_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj2] = self.bucket_name2
        self.log.info("Step 6: Create and upload objects to above s3bkt1, s3bkt2.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj1.put_object(
            self.bucket_name1, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj2.put_object(
            self.bucket_name2, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 7: Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-22793_s3bench_ios")
        self.log.info(
            "Step 8: Check cluster status, all services are running after completing test.")
        check_cluster_health()
        self.log.info(
            "ENDED: Test s3 account user is not able to reset password of other s3 account user"
            " and create resources for both account while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22794")
    @CTFailOn(error_handler)
    def test_22794(self):
        """
        Reset s3 account password.

        Test reset s3 account password using csm user having monitor role and create resources while
        S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test reset s3 account password using csm user having monitor role and "
            "create resources while S3 IO's are in progress.")
        self.log.info(
            "Step 1. Check cluster status, all services are running before starting test.")
        check_cluster_health()
        self.log.info("Step 2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-22794_s3bench_ios", duration="0h1m")
        self.log.info("Step 3. Create csm user having monitor role.")
        csm_user = self.csm_user.format(time.perf_counter_ns())
        csm_user_mail = self.email_id.format(csm_user)
        resp = self.csm_obj.csm_user_create(
            csm_user, csm_user_mail, self.csm_passwd, role="monitor")
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_list.append(csm_user)
        self.log.info("Step 4. Create s3account s3acc.")
        s3_test_obj = create_s3_acc(
            self.s3acc_name1, self.email_id.format(
                self.s3acc_name1), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        self.log.info("Step 5. Reset s3 account password using csm user having monitor role.")
        resp = self.csm_obj.reset_s3acc_password(
            csm_user, self.csm_passwd, self.s3acc_name1, self.new_passwd)
        assert_utils.assert_false(resp[0], resp[1])
        self.log.info("Step 6. Create bucket s3bkt in s3acc account.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        self.log.info("Step 7. Create and upload objects to above s3bkt.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(
            self.bucket_name1,
            self.object_name,
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 8. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-22794_s3bench_ios")
        self.log.info(
            "Step 9. Check cluster status, all services are running after completing test.")
        check_cluster_health()
        self.log.info(
            "ENDED: Test reset s3 account password using csm user having monitor role and "
            "create resources while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22795")
    @CTFailOn(error_handler)
    def test_22795(self):
        """
        Reset s3 account password.

        Test reset s3 account password using csm user having manage role and create resources
        while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test reset s3 account password using csm user having manage role and "
            "create resources while S3 IO's are in progress.")
        self.log.info(
            "Step 1. Check cluster status, all services are running before starting test.")
        check_cluster_health()
        self.log.info("Step 2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-22795_s3bench_ios", duration="0h1m")
        self.log.info("Step 3. Create csm user having manage role.")
        csm_user = self.csm_user.format(time.perf_counter_ns())
        csm_user_mail = self.email_id.format(csm_user)
        resp = self.csm_obj.csm_user_create(
            csm_user, csm_user_mail, self.csm_passwd, role="manage")
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_list.append(csm_user)
        self.log.info("Step 4. Create s3account s3acc.")
        s3_test_obj = create_s3_acc(
            self.s3acc_name1, self.email_id.format(
                self.s3acc_name1), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        self.log.info("Step 5. Reset s3 account password using csm user having manage role.")
        resp = self.csm_obj.reset_s3acc_password(
            csm_user, self.csm_passwd, self.s3acc_name1, self.new_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.account_dict[self.s3acc_name1] = self.new_passwd
        self.log.info("Step 6. Create bucket s3bkt in s3acc account.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        self.log.info("Step 7. Create and upload objects to above s3bkt.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(
            self.bucket_name1,
            self.object_name,
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 8. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-22795_s3bench_ios")
        self.log.info(
            "Step 9. Check cluster status, all services are running after completing test.")
        check_cluster_health()
        self.log.info(
            "ENDED: Test reset s3 account password using csm user having manage role and "
            "create resources while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22796")
    @CTFailOn(error_handler)
    def test_22796(self):
        """
        Reset s3 account password.

        Test s3 account user to reset it's own password and create s3 resources while S3 IO's
         are in progress.
        """
        self.log.info(
            "STARTED: Test s3 account user to reset it's own password and create s3 resources while"
            " S3 IO's are in progress.")
        self.log.info(
            "Step 1. Check cluster status, all services are running before starting test.")
        check_cluster_health()
        self.log.info("Step 2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-22796_s3bench_ios", duration="0h1m")
        self.log.info("Step 3. Create s3account s3acc.")
        s3_test_obj = create_s3_acc(
            self.s3acc_name1, self.email_id.format(
                self.s3acc_name1), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        self.log.info("Step 4. Reset s3 account user with it's own password.")
        resp = self.csm_obj.reset_s3acc_own_password(
            self.s3acc_name1, self.s3acc_passwd, self.new_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.account_dict[self.s3acc_name1] = self.new_passwd
        self.log.info("Step 5. Create bucket s3bkt in s3acc account.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        self.log.info("Step 6. Create and upload objects to above s3bkt.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(
            self.bucket_name1,
            self.object_name,
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 7. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-22796_s3bench_ios")
        self.log.info(
            "Step 8. Check cluster status, all services are running after completing test.")
        check_cluster_health()
        self.log.info(
            "ENDED: Test s3 account user to reset it's own password and create s3 resources while"
            " S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22797")
    @CTFailOn(error_handler)
    def test_22797(self):
        """
        Reset s3 account password.

        Test reset s3 account password using csm admin user and create s3 resources while S3 IO's
         are in progress.
        """
        self.log.info(
            "STARTED: Test reset s3 account password using csm admin user and create s3 resources"
            " while S3 IO's are in progress.")
        self.log.info(
            "Step 1. Check cluster status, all services are running before starting test.")
        check_cluster_health()
        self.log.info("Step 2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-22797_s3bench_ios", duration="0h1m")
        self.log.info("Step 3. Create s3account s3acc.")
        s3_test_obj = create_s3_acc(
            self.s3acc_name1, self.email_id.format(
                self.s3acc_name1), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        resp = self.csm_obj.reset_s3acc_password(
            acc_name=self.s3acc_name1, new_password=self.new_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.account_dict[self.s3acc_name1] = self.new_passwd
        self.log.info("Step 5. Create bucket s3bkt in s3acc account.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        self.log.info("Step 6. Create and upload objects to above s3bkt.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(
            self.bucket_name1,
            self.object_name,
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 7. list and check all resources are intact.")
        bkt_list = s3_test_obj.object_list(self.bucket_name1)[1]
        assert_utils.assert_in(
            self.object_name,
            bkt_list,
            f"{self.object_name} not exists in {bkt_list}")
        self.log.info("Step 8. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-22797_s3bench_ios")
        self.log.info(
            "Step 9. Check cluster status, all services are running after completing test.")
        check_cluster_health()
        self.log.info(
            "ENDED: Test reset s3 account password using csm admin user and create s3 resources"
            " while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22798")
    @CTFailOn(error_handler)
    def test_22798(self):
        """
        Reset s3 account password.

        Test s3 account user is not able to reset password of other s3 account user and check
        resource intact for both account while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test s3 account user is not able to reset password of other s3 account user"
            " and check resource intact for both account while S3 IO's are in progress.")
        self.log.info(
            "Step 1. Check cluster status, all services are running before starting test.")
        check_cluster_health()
        self.log.info("Step 2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-22798_s3bench_ios", duration="0h1m")
        self.log.info("Step 3. Create two s3account s3acc1, s3acc2.")
        s3_test_obj1 = create_s3_acc(
            self.s3acc_name1, self.email_id.format(
                self.s3acc_name1), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        s3_test_obj2 = create_s3_acc(
            self.s3acc_name2, self.email_id.format(
                self.s3acc_name2), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name2] = self.s3acc_passwd
        self.log.info("Step 4. Create and upload objects to above s3bkt1, s3bkt2.")
        resp = s3_test_obj1.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj1] = self.bucket_name1
        resp = s3_test_obj2.create_bucket(self.bucket_name2)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj2] = self.bucket_name2
        self.log.info("Step 5. Create and upload objects to above s3bkt1, s3bkt2.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj1.put_object(
            self.bucket_name1, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj2.put_object(
            self.bucket_name2, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 6. Reset s3 account password using other s3 account user.")
        resp = self.csm_obj.reset_s3acc_password(
            self.s3acc_name1,
            self.s3acc_passwd,
            self.s3acc_name2,
            self.new_passwd)
        assert_utils.assert_false(resp[0], resp[1])
        assert_utils.assert_in(
            "Access denied. Cannot modify another S3 account.",
            resp[1],
            resp[1])
        self.log.info("Step 7. list and check all resources are intact.")
        resp = s3_test_obj1.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            self.object_name,
            resp[1],
            "Failed to list bucket.")
        resp = s3_test_obj2.object_list(self.bucket_name2)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            self.object_name,
            resp[1],
            "Failed to list bucket.")
        self.log.info("Step 8. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-22798_s3bench_ios")
        self.log.info(
            "Step 9. Check cluster status, all services are running after completing test.")
        check_cluster_health()
        self.log.info(
            "ENDED: Test s3 account user is not able to reset password of other s3 account user and"
            " check resource intact for both account while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22799")
    @CTFailOn(error_handler)
    def test_22799(self):
        """
        Reset s3 account password.

        Test reset s3 account password using csm user having monitor role and check resource intact
        while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test reset s3 account password using csm user having monitor role and check"
            " resource intact while S3 IO's are in progress.")
        self.log.info(
            "Step 1. Check cluster status, all services are running before starting test.")
        check_cluster_health()
        self.log.info("Step 2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-22799_s3bench_ios", duration="0h1m")
        self.log.info("Step 3. Create csm user having monitor role.")
        csm_user = self.csm_user.format(time.perf_counter_ns())
        csm_user_mail = self.email_id.format(csm_user)
        resp = self.csm_obj.csm_user_create(
            csm_user, csm_user_mail, self.csm_passwd, role="monitor")
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_list.append(csm_user)
        self.log.info("Step 4. Create s3account s3acc.")
        s3_test_obj = create_s3_acc(
            self.s3acc_name1, self.email_id.format(
                self.s3acc_name1), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        self.log.info("Step 5. Create bucket s3bkt in s3acc account.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        self.log.info("Step 6. Create and upload objects to above s3bkt.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(
            self.bucket_name1,
            self.object_name,
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 7. Reset s3 account password using csm user having monitor role.")
        resp = self.csm_obj.reset_s3acc_password(
            csm_user, self.csm_passwd, self.s3acc_name1, self.new_passwd)
        assert_utils.assert_false(resp[0], resp[1])
        self.log.info("Step 7. list and check all resources are intact.")
        resp = s3_test_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            self.object_name,
            resp[1],
            "Failed to list bucket.")
        self.log.info("Step 8. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-22799_s3bench_ios")
        self.log.info(
            "Step 9. Check cluster status, all services are running after completing test.")
        check_cluster_health()
        self.log.info(
            "ENDED: Test reset s3 account password using csm user having monitor role and check"
            " resource intact while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22800")
    @CTFailOn(error_handler)
    def test_22800(self):
        """
        Reset s3 account password.

        Test reset s3 account password using csm user having manage role and check resource intact
         while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test reset s3 account password using csm user having manage role and check"
            " resource intact while S3 IO's are in progress.")
        self.log.info(
            "Step 1. Check cluster status, all services are running before starting test.")
        check_cluster_health()
        self.log.info("Step 2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-22800_s3bench_ios", duration="0h1m")
        self.log.info("Step 3. Create csm user having manage role.")
        csm_user = self.csm_user.format(time.perf_counter_ns())
        csm_user_mail = self.email_id.format(csm_user)
        resp = self.csm_obj.csm_user_create(
            csm_user, csm_user_mail, self.csm_passwd, role="manage")
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_list.append(csm_user)
        self.log.info("Step 4. Create s3account s3acc.")
        s3_test_obj = create_s3_acc(
            self.s3acc_name1, self.email_id.format(
                self.s3acc_name1), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        self.log.info("Step 5. Create bucket s3bkt in s3acc account.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        self.log.info("Step 6. Create and upload objects to above s3bkt.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(
            self.bucket_name1,
            self.object_name,
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 7. Reset s3 account password using csm user having manage role.")
        resp = self.csm_obj.reset_s3acc_password(
            csm_user, self.csm_passwd, self.s3acc_name1, self.new_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.account_dict[self.s3acc_name1] = self.new_passwd
        self.log.info("Step 7. list and check all resources are intact.")
        resp = s3_test_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            self.object_name,
            resp[1],
            "Failed to list bucket.")
        self.log.info("Step 8. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-22800_s3bench_ios")
        self.log.info(
            "Step 9. Check cluster status, all services are running after completing test.")
        check_cluster_health()
        self.log.info(
            "ENDED: Test reset s3 account password using csm user having manage role and check"
            " resource intact while S3 IO's are in progress.	")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22801")
    @CTFailOn(error_handler)
    def test_22801(self):
        """
        Reset s3 account password.

        Test s3 account user to reset it's own password and check resources intact while S3 IO's
         are in progress.
        """
        self.log.info(
            "STARTED: Test s3 account user to reset it's own password and check resources intact"
            " while S3 IO's are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-22801_s3bench_ios", duration="0h1m")
        self.log.info("Step 3: create s3 accounts.")
        s3_test_obj = create_s3_acc(
            self.s3acc_name1, self.email_id.format(
                self.s3acc_name1), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        self.log.info("Step 4: Create and upload objects to above s3bkt.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(
            self.bucket_name1,
            self.object_name,
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 5: Reset s3 account user with it's own password.")
        resp = self.csm_obj.reset_s3acc_own_password(
            self.s3acc_name1, self.s3acc_passwd, self.new_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.account_dict[self.s3acc_name1] = self.new_passwd
        self.log.info("Step 6: list and check all resources are intact.")
        resp = s3_test_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            self.object_name,
            resp[1],
            "Failed to list bucket.")
        self.log.info("Step 7: Stop and validate S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-22801_s3bench_ios")
        self.log.info("Step 8: Check cluster status, all services are running")
        check_cluster_health()
        self.log.info(
            "ENDED: Test s3 account user to reset it's own password and check resources intact"
            " while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22802")
    @CTFailOn(error_handler)
    def test_22802(self):
        """
        Reset s3 account password.

        Test reset s3 account password using csm admin user and check s3 resource intact while
        S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test reset s3 account password using csm admin user and check s3 resource"
            " intact while S3 IO's are in progress.")
        self.log.info(
            "Step 1. Check cluster status, all services are running before starting test.")
        check_cluster_health()
        self.log.info("Step 2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-22802_s3bench_ios", duration="0h1m")
        self.log.info("Step 3. Create s3account s3acc.")
        s3_test_obj = create_s3_acc(
            self.s3acc_name1, self.email_id.format(
                self.s3acc_name1), self.s3acc_passwd)[0]
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        self.log.info("Step 4. Create bucket s3bkt in s3acc account.")
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        self.resources_dict[s3_test_obj] = self.bucket_name1
        self.log.info("Step 5. Create and upload objects to above s3bkt.")
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(
            self.bucket_name1,
            self.object_name,
            self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 6. Reset s3 account password using csm admin user.")
        resp = self.csm_obj.reset_s3acc_password(
            acc_name=self.s3acc_name1, new_password=self.new_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        self.account_dict[self.s3acc_name1] = self.new_passwd
        self.log.info("Step 7. list and check all resources are intact.")
        resp = s3_test_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(
            self.object_name,
            resp[1],
            "Failed to list bucket.")
        self.log.info("Step 8. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-22802_s3bench_ios")
        self.log.info(
            "Step 9. Check cluster status, all services are running after completing test.")
        check_cluster_health()
        self.log.info(
            "ENDED: Test reset s3 account password using csm admin user and check s3 resource "
            "intact while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22882")
    @CTFailOn(error_handler)
    def test_22882(self):
        """
        Reset s3 account password.

        Test reset n number of s3 account password using csm user having different role (admin,
        manage, monitor) while S3 IO's are in progress.
        """
        self.log.info(
            "STARTED: Test reset n number of s3 account password using csm user having different"
            " role (admin, manage, monitor) while S3 IO's are in progress.")
        self.log.info(
            "Step 1. Check cluster status, all services are running before starting test.")
        check_cluster_health()
        self.log.info("Step 2. Start S3 IO.")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="TEST-22882_s3bench_ios", duration="0h2m")
        self.log.info("Step 3. Create N number s3account.")
        account_list = []
        for i in range(10):
            acc_name = "{}{}".format(
                self.account_prefix.format(
                    time.perf_counter_ns()), i)
            email_id = self.email_id.format(acc_name)
            create_s3_acc(acc_name, email_id, self.s3acc_passwd)
            account_list.append(acc_name)
            self.account_dict[acc_name] = self.s3acc_passwd
        self.log.info(
            "Step 4. Reset N number s3 account password using csm admin user.")
        for name in account_list:
            resp = self.csm_obj.reset_s3acc_password(
                acc_name=name, new_password=self.new_passwd)
            assert_utils.assert_true(resp[0], resp[1])
            self.account_dict[name] = self.new_passwd
        self.log.info("Step 5. Create csm user having role manage.")
        csm_user = self.csm_user.format(time.perf_counter_ns())
        csm_user_mail = self.email_id.format(csm_user)
        resp = self.csm_obj.csm_user_create(
            csm_user, csm_user_mail, self.csm_passwd, role="manage")
        assert_utils.assert_true(resp[0], resp[1])
        self.csm_user_list.append(csm_user)
        self.log.info(
            "Step 6. Reset N number s3 account password using csm user having manage role.")
        for name in account_list:
            resp = self.csm_obj.reset_s3acc_password(
                csm_user, self.csm_passwd, name, self.s3acc_passwd)
            assert_utils.assert_true(resp[0], resp[1])
            self.account_dict[name] = self.s3acc_passwd
        self.log.info("Step 7. Changes csm user role to monitor.")
        resp = self.csm_obj.csm_user_update_role(
            csm_user, self.csm_passwd, role="monitor")
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(
            "Step 8. Reset N number s3 account password using csm user having monitor role.")
        for name in account_list:
            resp = self.csm_obj.reset_s3acc_password(
                csm_user, self.csm_passwd, name, self.new_passwd)
            assert_utils.assert_false(resp[0], resp[1])
        self.log.info("Step 9. Stop S3 IO & Validate logs.")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="TEST-22882_s3bench_ios")
        self.log.info(
            "Step 10. Check cluster status, all services are running after completing test.")
        check_cluster_health()
        self.log.info(
            "ENDED: Test reset n number of s3 account password using csm user having different role"
            " (admin, manage, monitor) while S3 IO's are in progress.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-21502")
    @CTFailOn(error_handler)
    def test_21502(self):
        """
        Reset s3 account password.

        Use REST API call Update Account Login Profile using access/secret key.
        """
        self.log.info(
            "STARTED: Use REST API call Update Account Login Profile using access/secret key.")
        self.log.info("Steps 1. Create Account & Login Profile.")
        response = create_s3_acc(
            self.s3acc_name1, self.email_id.format(self.s3acc_name1), self.s3acc_passwd)
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        access_key, secret_key = response[1], response[2]
        self.log.info("Step 2. Update Account Login Profile using access/secret key using direct "
                      "REST API call.")
        response = self.s3auth_obj.update_account_login_profile(
            self.s3acc_name1, self.new_passwd, access_key, secret_key)
        assert_utils.assert_true(response[0], response[1])
        self.log.info("Step 3. Check password updated by login with new password.")
        resp = self.s3auth_obj.custom_rest_login(self.s3acc_name1, self.new_passwd)
        assert_utils.assert_true(resp.ok, resp)
        self.log.info("Step 4. Check password updated by login with old password.")
        resp = self.s3auth_obj.custom_rest_login(self.s3acc_name1, self.s3acc_passwd)
        assert_utils.assert_false(resp.ok, resp)
        self.log.info(
            "ENDED: Use REST API call Update Account Login Profile using access/secret key.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-21514")
    @CTFailOn(error_handler)
    def test_21514(self):
        """
        Reset s3 account password.

        Use REST API call Update Account Login Profile using LDAP credentials.
        """
        self.log.info(
            "STARTED: Use REST API call Update Account Login Profile using LDAP credentials.")
        self.log.info("Steps 1. Create Account & Login Profile.")
        create_s3_acc(self.s3acc_name1, self.email_id.format(self.s3acc_name1), self.s3acc_passwd)
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        self.log.info("Get ldap credentials.")
        ldap_user, ldap_password = get_ldap_creds()
        self.log.info("Step 2. Update Account Login Profile using access/secret key using direct "
                      "REST API call.")
        response = self.s3auth_obj.update_account_login_profile(
            self.s3acc_name1, self.new_passwd, ldap_user, ldap_password)
        assert_utils.assert_true(response[0], response[1])
        self.log.info("Step 3. Check password updated by login with new password.")
        resp = self.s3auth_obj.custom_rest_login(self.s3acc_name1, self.new_passwd)
        assert_utils.assert_true(resp.ok, resp)
        self.log.info("Step 4. Check password updated by login with old password.")
        resp = self.s3auth_obj.custom_rest_login(self.s3acc_name1, self.s3acc_passwd)
        assert_utils.assert_false(resp.ok, resp)
        self.log.info(
            "ENDED: Use REST API call Update Account Login Profile using LDAP credentials.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-21517")
    @CTFailOn(error_handler)
    def test_21517(self):
        """
        Reset s3 account password.

        Use REST API call Update Account Login Profile using invalid credentials.
        """
        self.log.info(
            "STARTED: Use REST API call Update Account Login Profile using invalid credentials.")
        self.log.info("Steps 1. Create Account & Login Profile.")
        response = create_s3_acc(self.s3acc_name1, self.email_id.format(
            self.s3acc_name1), self.s3acc_passwd)
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        access_key, secret_key = response[1], response[2]
        self.log.info("Step 2. Update Account Login Profile using invalid Access Key and valid "
                      "Secret key credentials using direct REST API call.")
        response = self.s3auth_obj.update_account_login_profile(
            self.s3acc_name1, self.new_passwd, access_key[:-3], secret_key)
        assert_utils.assert_false(response[0], response[1])
        assert_utils.assert_in(
            "The AWS access key Id you provided does not exist in our records.",
            response[1],
            response[1])
        self.log.info("Step 3. Update Account Login Profile using Valid Access key and Invalid "
                      "Secret Key credentials using direct REST API call.")
        response = self.s3auth_obj.update_account_login_profile(
            self.s3acc_name1, self.new_passwd, access_key, secret_key[:-3])
        assert_utils.assert_false(response[0], response[1])
        assert_utils.assert_in(
            "The request signature we calculated does not match the signature you provided."
            " Check your AWS secret access key", response[1], response[1])
        self.log.info("Step 4. Update Account Login Profile using invalid access and invalid "
                      "secret key using direct REST API call.")
        response = self.s3auth_obj.update_account_login_profile(
            self.s3acc_name1, self.new_passwd, access_key[:-3], secret_key[:-3])
        assert_utils.assert_false(response[0], response[1])
        assert_utils.assert_in(
            "The AWS access key Id you provided does not exist in our records.",
            response[1],
            response[1])
        self.log.info("Step 5. Check impact of wrong api call by login with old password .")
        resp = self.s3auth_obj.custom_rest_login(self.s3acc_name1, self.s3acc_passwd)
        assert_utils.assert_true(resp.ok, resp)
        self.log.info(
            "ENDED: Use REST API call Update Account Login Profile using invalid credentials.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-21520")
    @CTFailOn(error_handler)
    def test_21520(self):
        """
        Reset s3 account password.

        Use REST API call to Update Account Login Profile without mentioning Account name.
        """
        self.log.info("STARTED: Use REST API call to Update Account Login Profile without "
                      "mentioning Account name.")
        self.log.info("Steps 1. Create Account & Login Profile.")
        response = create_s3_acc(
            self.s3acc_name1, self.email_id.format(self.s3acc_name1), self.s3acc_passwd)
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        access_key, secret_key = response[1], response[2]
        self.log.info("Step 2. Update Account Login Profile without specifying Account name using"
                      " direct REST API call.")
        response = self.s3auth_obj.update_account_login_profile(
            new_password=self.new_passwd, access_key=access_key, secret_key=secret_key)
        assert_utils.assert_false(response[0], response[1])
        assert_utils.assert_in("Please provide account name", response[1], response[1])
        self.log.info("Step 3. Check impact of wrong api call by login with old password .")
        resp = self.s3auth_obj.custom_rest_login(self.s3acc_name1, self.s3acc_passwd)
        assert_utils.assert_true(resp.ok, resp)
        self.log.info("ENDED: Use REST API call to Update Account Login Profile without "
                      "mentioning Account name.")

    @pytest.mark.parallel
    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-21521")
    @CTFailOn(error_handler)
    def test_21521(self):
        """
        Reset s3 account password.

        Use REST API call to Update Account Login Profile without mentioning new Password.
        """
        self.log.info("STARTED: Use REST API call to Update Account Login Profile without "
                      "mentioning new Password.")
        self.log.info("Steps 1. Create Account & Login Profile.")
        response = create_s3_acc(
            self.s3acc_name1, self.email_id.format(self.s3acc_name1), self.s3acc_passwd)
        self.account_dict[self.s3acc_name1] = self.s3acc_passwd
        access_key, secret_key = response[1], response[2]
        self.log.info("Step 2. Update Account Login Profile without specifying new Password "
                      "using direct REST API call.")
        response = self.s3auth_obj.update_account_login_profile(
            user_name=self.s3acc_name1, access_key=access_key, secret_key=secret_key)
        assert_utils.assert_false(response[0], response[1])
        assert_utils.assert_in("Please provide password", response[1], response[1])
        self.log.info("Step 3. Check impact of wrong api call by login with old password .")
        resp = self.s3auth_obj.custom_rest_login(self.s3acc_name1, self.s3acc_passwd)
        assert_utils.assert_true(resp.ok, resp)
        self.log.info("ENDED: Use REST API call to Update Account Login Profile without "
                      "mentioning new Password.")
