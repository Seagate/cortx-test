# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""DOS Scalability Test Module."""

import os
import time
import logging
import pytest
from commons import commands
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils import system_utils
from commons.utils.system_utils import remove_file, run_remote_cmd
from commons.utils.assert_utils import assert_true, assert_not_in
from commons.helpers.health_helper import Health
from scripts.s3_bench import s3bench as s3b_obj
from config import CMN_CFG as CM_CFG
from config.s3 import S3_CFG
from libs.s3 import S3H_OBJ
from libs.s3.s3_test_lib import S3TestLib


class TestDosScalability:
    """DOS Scalability Test suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.bkt_name_prefix = "scalable-test"
        cls.obj_name_prefix = "scalable-obj"
        cls.cmd_msg = "core."
        cls.random_id = str(time.time())
        cls.log_file = []
        cls.host = CM_CFG["nodes"][0]["host"]
        cls.username = CM_CFG["nodes"][0]["username"]
        cls.password = CM_CFG["nodes"][0]["password"]
        cls.hobj = Health(hostname=cls.host,
                          username=cls.username,
                          password=cls.password)
        cls.s3_obj = S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.log.info("Step: Install and setup s3bench on client.")
        res = s3b_obj.setup_s3bench()
        assert_true(res, res)
        cls.log.info("Step: Successfully installed S3bench tool: %s.", res)
        cls.log.info("ENDED: setup test suite operations.")

    def setup_method(self):
        """
        Function will be invoked before each test case execution.

        It will perform prerequisite test steps if any.
        Define few variable, will be used while executing test and for cleanup.
        """
        self.log.info("STARTED: Setup operations")
        self.log.info("Step: hctl status should show all services as STARTED")
        self.bucket_name = "scalable-test-dos-{}".format(str(time.time()))
        self.obj_name = "scalable-obj-dos-{}".format(str(time.time()))
        status, resp = S3H_OBJ.check_s3services_online()
        assert_true(status, resp)
        self.log.info("Step: Successfully checked hctl status show all services as STARTED")
        self.log.info(self.random_id)
        self.log.info("ENDED: Setup operations")

    def teardown_method(self):
        """
        Function will be invoked after running each test case.

        It will clean all resources which are getting created during
        test execution such as S3 buckets and the objects present into that bucket.
        Also removing local file created during execution.
        """
        self.log.info("STARTED: Teardown operations")
        self.log.info("Deleting all buckets/objects created during TC execution")
        bucket_list = self.s3_obj.bucket_list()[1]
        pref_list = [
            each_bucket for each_bucket in bucket_list if each_bucket.startswith(
                self.bkt_name_prefix)]
        if pref_list:
            self.s3_obj.delete_multiple_buckets(pref_list)
        self.log.info("All the buckets/objects deleted successfully")
        self.log.info("ENDED: Teardown Operations")

    @pytest.mark.s3_ops
    @pytest.mark.s3_scalability
    @pytest.mark.tags('TEST-8724')
    @pytest.mark.parametrize("num_clients, num_sample, obj_size", [(400, 1000, "1Mb")])
    # @CTFailOn(error_handler)
    def test_400_constant_s3_operations_5336(self, num_clients, num_sample,
                                             obj_size):
        """Test constant 400 S3 operations using s3bench."""
        self.log.info("STARTED: Test constant 400 S3 operations using s3bench.")
        self.log.info("Step 1: Check done in setup: S3 services up and running, Install and "
                      "Configure S3bench tool and validate")
        self.log.info("Step 2: Perform with %s constant s3 operations.", num_clients)
        access_key, secret_key = S3H_OBJ.get_local_keys()
        self.log.info("Creating bucket %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert_true(res[0], res[1])
        self.log.info("Successfully created the bucket")
        for _ in range(5):
            res = s3b_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=self.bucket_name,
                end_point=S3_CFG['s3b_url'],
                num_clients=num_clients,
                num_sample=num_sample,
                obj_name_pref=self.obj_name,
                obj_size=obj_size,
                skip_cleanup=True,
                log_file_prefix="TEST-5336")
            self.log.debug(res)
            self.log_file.append(res[1])
            resp = system_utils.validate_s3bench_parallel_execution(
                     log_dir=s3b_obj.LOG_DIR, log_prefix="TEST-5336")
            assert_true(resp[0], resp[1])
        self.log.info("Step 2: Successfully performed with %s constant s3 operations.", 400)
        self.log.info("Step 3: check any crashes happened and core logs for motr")
        for cmd in commands.CRASH_COMMANDS:
            res_cmd = run_remote_cmd(
                cmd,
                self.host,
                self.username,
                self.password)
            assert_not_in(self.cmd_msg, str(res_cmd), res_cmd)
        self.log.info("Step 3: Successfully checked no crashes happened and core logs for motr")
        self.log.info("ENDED: Test constant 400 S3 operations using s3bench.")

    @pytest.mark.s3_ops
    @pytest.mark.s3_scalability
    @pytest.mark.tags('TEST-9657')
    @pytest.mark.parametrize("num_clients, num_sample, obj_size", [(300, 1000, "1Mb")])
    # @CTFailOn(error_handler)
    def test_300_constant_s3_operations_5337(self, num_clients, num_sample,
                                             obj_size):
        """Test constant 300 S3 operations using s3bench."""
        self.log.info("STARTED: Test constant 300 S3 operations using s3bench")
        self.log.info("Step 1: Check done in setup: S3 services up and running, Install and "
                      "Configure S3bench tool and validate")
        self.log.info("Step 2: Perform with %s constant s3 operations.", num_clients)
        access_key, secret_key = S3H_OBJ.get_local_keys()
        self.log.info("Creating bucket %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert_true(res[0], res[1])
        self.log.info("Successfully created the bucket")
        for _ in range(5):
            res = s3b_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=self.bucket_name,
                end_point=S3_CFG['s3b_url'],
                num_clients=num_clients,
                num_sample=num_sample,
                obj_name_pref=self.obj_name,
                obj_size=obj_size,
                skip_cleanup=True,
                log_file_prefix="TEST-5337")
            self.log.debug(res)
            self.log_file.append(res[1])
            resp = system_utils.validate_s3bench_parallel_execution(
                log_dir=s3b_obj.LOG_DIR, log_prefix="TEST-5337")
            assert_true(resp[0], resp[1])
        self.log.info("Step 2: Successfully performed with %s constant s3 operations.", 300)
        self.log.info("Step 3: check any crashes happened and core logs for motr")
        for cmd in commands.CRASH_COMMANDS:
            res_cmd = run_remote_cmd(
                cmd,
                self.host,
                self.username,
                self.password)
            assert_not_in(self.cmd_msg, str(res_cmd), res_cmd)
        self.log.info("Step 3: Successfully checked no crashes happened and core logs for motr")
        self.log.info("ENDED: Test constant 300 S3 operations using s3bench")

    @pytest.mark.s3_ops
    @pytest.mark.s3_scalability
    @pytest.mark.tags('TEST-9658')
    @pytest.mark.parametrize("num_clients, num_sample, obj_size", [(1000, 1000, "1Mb")])
    # @CTFailOn(error_handler)
    def test_1000_constant_s3_operations_5338(self, num_clients, num_sample,
                                              obj_size):
        """Test constant 1000 S3 operations using s3bench."""
        self.log.info("STARTED: Test constant 1000 S3 operations using s3bench")
        self.log.info("Step 1: Check done in setup: S3 services up and running, Install and "
                      "Configure S3bench tool and validate")
        self.log.info("Step 2: Perform with %s constant s3 operations.", num_clients)
        access_key, secret_key = S3H_OBJ.get_local_keys()
        self.log.info("Creating bucket %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert_true(res[0], res[1])
        self.log.info("Successfully created the bucket")
        for _ in range(5):
            res = s3b_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=self.bucket_name,
                end_point=S3_CFG['s3b_url'],
                num_clients=num_clients,
                num_sample=num_sample,
                obj_name_pref=self.obj_name,
                obj_size=obj_size,
                skip_cleanup=True,
                log_file_prefix="TEST-5338")
            self.log.debug(res)
            self.log_file.append(res[1])
            resp = system_utils.validate_s3bench_parallel_execution(
                log_dir=s3b_obj.LOG_DIR, log_prefix="TEST-5338")
            assert_true(resp[0], resp[1])
        self.log.info("Step 2: Successfully performed with %s constant s3 operations.", 1000)
        self.log.info("Step 3: check any crashes happened and core logs for motr")
        for cmd in commands.CRASH_COMMANDS:
            res_cmd = run_remote_cmd(
                cmd,
                self.host,
                self.username,
                self.password)
            assert_not_in(self.cmd_msg, str(res_cmd), res_cmd)
        self.log.info("Step 3: Successfully checked no crashes happened and core logs for motr")
        self.log.info("ENDED: Test constant 1000 S3 operations using s3bench")

    @pytest.mark.s3_ops
    @pytest.mark.s3_scalability
    @pytest.mark.tags('TEST-9659')
    @pytest.mark.parametrize("nclients, obj_size", [([1000, 1200, 1500], "1Mb")])
    # @CTFailOn(error_handler)
    def test_growing_s3_operations_5340(self, obj_size, nclients):
        """Test growing S3 operations using s3bench from 1000 to 1200 then to 1500."""
        self.log.info("STARTED: Test growing S3 operations using s3bench from 1000 to 1200 then to "
                      "1500")
        self.log.info("Step 1: Check done in setup: S3 services up and running, Install and "
                      "Configure S3bench tool and validate")
        self.log.info("Step 2: Perform with n constant s3 operations.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        self.log.info("Creating bucket %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert_true(res[0], res[1])
        self.log.info("Successfully created the bucket")
        count = 0
        for client in nclients:
            repetation = 5
            if count % 2 != 0:
                repetation = 1
            for _ in range(repetation):
                res = s3b_obj.s3bench(
                    access_key=access_key,
                    secret_key=secret_key,
                    bucket=self.bucket_name,
                    end_point=S3_CFG['s3b_url'],
                    num_clients=client,
                    num_sample=client,
                    obj_name_pref=self.obj_name,
                    obj_size=obj_size,
                    skip_cleanup=True,
                    log_file_prefix="TEST-5340")
                self.log.debug(res)
                self.log_file.append(res[1])
                resp = system_utils.validate_s3bench_parallel_execution(
                    log_dir=s3b_obj.LOG_DIR, log_prefix="TEST-5340")
                assert_true(resp[0], resp[1])
            count = count + 1
        self.log.info("Step 2: Successfully performed with n constant s3 operations.")
        self.log.info("Step 3: check any crashes happened and core logs for motr")
        for cmd in commands.CRASH_COMMANDS:
            res_cmd = run_remote_cmd(
                cmd,
                self.host,
                self.username,
                self.password)
            assert_not_in(self.cmd_msg, str(res_cmd), res_cmd)
        self.log.info("Step 3: Successfully checked no crashes happened and core logs for motr")
        self.log.info("ENDED: Test growing S3 operations using s3bench from 1000 to 1200 then to "
                      "1500")

    @pytest.mark.s3_ops
    @pytest.mark.s3_scalability
    @pytest.mark.tags('TEST-9660')
    @pytest.mark.parametrize("obj_size, nclients", [("1Mb", [1000, 1500, 1000, 1500])])
    # @CTFailOn(error_handler)
    def test_growing_s3_operations_5341(self, obj_size, nclients):
        """
        Growing S3 operations.

        Growing S3 operations using s3bench from 1000 to 1500 then back to 1000 then to 1500 again.
        """
        self.log.info("STARTED: Test growing S3 operations using s3bench from 1000 to 1500 then "
                      "back to 1000 then to 1500 again")
        self.log.info("Step 1: Check done in setup: S3 services up and running, Install and "
                      "Configure S3bench tool and validate")
        self.log.info("Step 2: Perform with n constant s3 operations.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        self.log.info("Creating bucket %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert_true(res[0], res[1])
        self.log.info("Successfully created the bucket")
        for client in nclients:
            res = s3b_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=self.bucket_name,
                end_point=S3_CFG['s3b_url'],
                num_clients=client,
                num_sample=client,
                obj_name_pref=self.obj_name,
                obj_size=obj_size,
                skip_cleanup=True,
                log_file_prefix="TEST-5341")
            self.log.debug(res)
            self.log_file.append(res[1])
            resp = system_utils.validate_s3bench_parallel_execution(
                log_dir=s3b_obj.LOG_DIR, log_prefix="TEST-5341")
            assert_true(resp[0], resp[1])
        self.log.info("Step 2: Successfully performed with n constant s3 operations.")
        self.log.info("Step 3: check any crashes happened and core logs for motr")
        for cmd in commands.CRASH_COMMANDS:
            res_cmd = run_remote_cmd(
                cmd,
                self.host,
                self.username,
                self.password)
            assert_not_in(self.cmd_msg, str(res_cmd), res_cmd)
        self.log.info("Step 3: Successfully checked no crashes happened and core logs for motr")
        self.log.info("ENDED: Test growing S3 operations using s3bench from 1000 to 1500 then "
                      "back to 1000 then to 1500 again")

    @pytest.mark.skip("Need to validate on HW")
    @pytest.mark.s3_ops
    @pytest.mark.s3_scalability
    @pytest.mark.tags('TEST-8725')
    @pytest.mark.parametrize("num_clients, num_sample, obj_size", [(100, 1000000, "1Kb")])
    # # @CTFailOn(error_handler)
    def test_scaling_obj_20billion_size_1bytes_5308(self, num_clients,
                                                    num_sample, obj_size):
        """Verify scaling of number of objects upto 20 billion with minimum object size i.e 1B."""
        self.log.info("STARTED: Test To Verify scaling of number of objects upto 20 billion with "
                      "minimum object size i.e 1B.")
        self.log.info("Step 1: Check done in setup: S3 services up and running, Install and "
                      "Configure S3bench tool and validate")
        self.log.info("Step 2: Executed s3bench run with objects upto 20billion and obj size 1B.")
        access_key, secret_key = S3H_OBJ.get_local_keys()
        self.log.info("Creating bucket %s", self.bucket_name)
        res = self.s3_obj.create_bucket(self.bucket_name)
        assert_true(res[0], res[1])
        self.log.info("Successfully created the bucket")
        for _ in range(20000):
            res = s3b_obj.s3bench(
                access_key=access_key,
                secret_key=secret_key,
                bucket=self.bucket_name,
                end_point=S3_CFG['s3b_url'],
                num_clients=num_clients,
                num_sample=num_sample,
                obj_name_pref=self.obj_name,
                obj_size=obj_size,
                skip_cleanup=True,
                log_file_prefix="TEST-5308")
            self.log.debug(res)
            self.log_file.append(res[1])
            resp = system_utils.validate_s3bench_parallel_execution(
                log_dir=s3b_obj.LOG_DIR, log_prefix="TEST-5308")
            assert_true(resp[0], resp[1])
        res = self.hobj.is_motr_online()
        assert_true(res, res)
        self.log.info("Step 2: Executed s3bench run with objects upto 20billion and obj size 1B and"
                      " checking stack status.")
        self.log.info("ENDED: Test To Verify scaling of number of objects upto 20 billion with "
                      "minimum object size i.e 1B ")
