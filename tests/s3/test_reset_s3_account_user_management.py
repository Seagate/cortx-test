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

"""Reset s3 Account User Management test module."""

import os
import time
from time import perf_counter_ns
from multiprocessing import Process

import logging
import pytest
from commons import commands
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.exceptions import CTException
from commons.errorcodes import error_handler
from commons.helpers.health_helper import Health
from commons.params import TEST_DATA_FOLDER
from config import CMN_CFG
from config import S3_CFG
from scripts.s3_bench import s3bench
from libs.s3 import S3H_OBJ
from libs.s3 import s3_test_lib
from libs.s3.cortxcli_test_lib import CortxCliTestLib

S3_OBJ = s3_test_lib.S3TestLib()


class TestResetAccountUserManagement:
    """Reset s3 Account User Management TestSuite."""

    @pytest.yield_fixture(autouse=True)
    def setup(self):
        """
        Function will be invoked test before and after yield part each test case execution.

        1. Create bucket name, object name, account name.
        2. Check cluster status, all services are running.
        """
        self.log = logging.getLogger(__name__)
        self.log.info("STARTED: test setup.")
        self.log.info("Setup s3 bench tool")
        res = s3bench.setup_s3bench()
        assert_utils.assert_true(res, res)
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "TestResetAccountUserManagement")
        if not system_utils.path_exists(self.test_dir_path):
            system_utils.make_dirs(self.test_dir_path)
            self.log.info("Created path: %s", self.test_dir_path)
        self.cortx_test_obj = CortxCliTestLib()
        self.account_prefix = "acc-resetaccount-{}"
        self.email_id = "{}@seagate.com"
        self.io_bucket_name = "iobkt1-reset-{}".format(perf_counter_ns())
        self.bucket_name1 = "bkt1-reset-{}".format(perf_counter_ns())
        self.bucket_name2 = "bkt2-reset-{}".format(perf_counter_ns())
        self.object_name = "obj-resetobject-{}".format(time.perf_counter_ns())
        self.s3acc_passwd = S3_CFG["CliConfig"]["s3_account"]["password"]
        self.file_path = os.path.join(self.test_dir_path, self.object_name)
        self.parallel_ios = None
        self.account_list = list()
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
        bkt_list = S3_OBJ.bucket_list()[1]
        if self.io_bucket_name in bkt_list:
            resp = S3_OBJ.delete_bucket(self.io_bucket_name, force=True)
            assert_utils.assert_true(resp[0], resp[1])
        accounts = self.cortx_test_obj.list_accounts_cortxcli()
        all_accounts = [acc["account_name"] for acc in accounts]
        self.log.info("setup %s", all_accounts)
        for acc in self.account_list:
            if acc in all_accounts:
                self.cortx_test_obj.delete_account_cortxcli(
                    account_name=acc, password=self.s3acc_passwd)
                self.log.info("Deleted %s account successfully", acc)
        del self.cortx_test_obj
        self.log.info("ENDED: test teardown.")

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
        kwargs.setdefault("obj_name_pref", "loadgen_")
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
        logflist = system_utils.list_dir(s3bench.LOG_DIR)
        log_path = None
        for filename in logflist:
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

    def create_s3cortxcli_acc(
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
            "Step : Creating account with name %s and email_id %s",
            account_name,
            email_id)
        create_account = self.cortx_test_obj.create_account_cortxcli(
            account_name, email_id, password)
        assert_utils.assert_true(create_account[0], create_account[1])
        access_key = create_account[1]["access_key"]
        secret_key = create_account[1]["secret_key"]
        self.account_list.append(account_name)
        self.log.info("Step Successfully created the s3iamcli account")
        s3_obj = s3_test_lib.S3TestLib(
            access_key,
            secret_key,
            endpoint_url=S3_CFG["s3_url"],
            s3_cert_path=S3_CFG["s3_cert_path"],
            region=S3_CFG["region"])
        response = (
            s3_obj,
            access_key,
            secret_key)

        return True, response

    @pytest.mark.s3_ops
    @pytest.mark.tags("TEST-22801")
    @CTFailOn(error_handler)
    def test_22801(self):
        """
        Reset s3 account password.

        Test s3 account user to reset it's own password and check resources intact while S3 IO's are in progress.
        """
        self.log.info("STARTED: Test s3 account user to reset it's own password and check resources intact while"
                      " S3 IO's are in progress.")
        self.log.info("Step 1: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("Step 2: start s3 IO's")
        self.start_stop_validate_parallel_s3ios(
            ios="Start", log_prefix="test_19842_ios", duration="0h1m")
        self.log.info("Step 3: create s3 accounts.")
        acc_name = self.account_prefix.format(time.perf_counter_ns())
        email = self.email_id.format(acc_name)
        s3_test_obj = self.create_s3cortxcli_acc(acc_name, email, self.s3acc_passwd)[0]
        resp = s3_test_obj.create_bucket(self.bucket_name1)
        assert_utils.assert_true(resp[1], resp[1])
        resp = system_utils.create_file(self.file_path, count=10)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.put_object(self.bucket_name1, self.object_name, self.file_path)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.cortx_test_obj.reset_s3account_password(acc_name, self.s3acc_passwd)
        assert_utils.assert_true(resp[0], resp[1])
        resp = s3_test_obj.object_list(self.bucket_name1)
        assert_utils.assert_true(resp[0], resp[1])
        assert_utils.assert_in(self.object_name, resp[0], f"Failed to list bucket.")
        resp = s3_test_obj.delete_bucket(self.bucket_name1, force=True)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 7: Stop and validate S3 IOs")
        self.start_stop_validate_parallel_s3ios(
            ios="Stop", log_prefix="test_19842_ios")
        self.log.info(
            "Step 8: Check cluster status, all services are running")
        self.check_cluster_health()
        self.log.info("ENDED: Test s3 account user to reset it's own password and check resources intact while"
                      " S3 IO's are in progress.")
