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

"""Bucket Location Test Module."""

import os
import logging
import pytest

from commons.utils import assert_utils
from scripts.locust import locust_runner
from config import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY


class TestS3Load:
    """ S3 Load Testing suite"""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.log.info("STARTED: setup test suite operations.")
        cls.account_prefix = "locust-acc"
        cls.email_id = "@seagate.com"
        cls.account_name = None
        os.environ.setdefault("CA_CERT", S3_CFG["s3_cert_path"])
        cls.log.info("account prefix: %s, Bucket prefix:", cls.account_prefix)
        cls.log.info("ENDED: setup test suite operations.")

    @classmethod
    def teardown_class(cls):
        """
        Function will be invoked after completion of all test case.

        It will clean up resources which are getting created during test suite setup.
        """
        cls.log.info("STARTED: teardown test suite operations.")
        cls.log.info("ENDED: teardown test suite operations.")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        It will perform all prerequisite test steps if any.
        Initializing common variable which will be used in test and
        teardown for cleanup
        """
        self.log.info("STARTED: Setup operations.")
        self.host_url = S3_CFG["s3_url"]
        os.environ.setdefault("ENDPOINT_URL", self.host_url)
        self.account_name = self.account_prefix
        os.environ["AWS_ACCESS_KEY_ID"] = ACCESS_KEY
        os.environ["AWS_SECRET_ACCESS_KEY"] = SECRET_KEY
        self.log.info("ENDED: Setup operations.")

    def teardown_method(self):
        """
        This function will be invoked after each test case.
        It will perform all cleanup operations.
        This function will delete buckets and accounts created for tests.
        """
        self.log.info("STARTED: Teardown operations.")
        self.log.info("ENDED: Teardown operations.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-19533")
    def test_single_bkt_small_obj_max_session_19533(self):
        """
        Load test with single bucket, fixed small size objects and max supported concurrent sessions.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(1)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(102400)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21039")
    def test_single_bkt_small_obj_max_session_with_http_21039(self):
        """
        Load test with single bucket, fixed small size objects and max supported
        concurrent sessions using http endpoint.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(1)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(102400)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        if "https" in self.host_url:
            host_url = self.host_url.replace("https", "http")
        else:
            host_url = self.host_url
        res = locust_runner.run_locust(
            host=host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-19526")
    def test_small_obj_max_session_19526(self):
        """
        Load test with small size objects and max supported concurrent sessions.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(25000)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21195")
    def test_small_obj_max_session_with_http_21195(self):
        """
        Load test with small size objects and max supported concurrent sessions using http endpoint.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(25000)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        if "https" in self.host_url:
            host_url = self.host_url.replace("https", "http")
        else:
            host_url = self.host_url
        res = locust_runner.run_locust(
            host=host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-19534")
    def test_small_obj_multi_bkt_max_session_19534(self):
        """
        Load test with multiple buckets, small size objects and max supported concurrent sessions.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(100)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(25000)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21210")
    def test_small_obj_multi_bkt_max_session_with_http_21210(self):
        """
        Load test with multiple buckets, small size objects and max supported
        concurrent sessions using http endpoint.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(100)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(25000)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        if "https" in self.host_url:
            host_url = self.host_url.replace("https", "http")
        else:
            host_url = self.host_url
        res = locust_runner.run_locust(
            host=host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-19537")
    def test_small_obj_increase_session_19537(self):
        """
        Load test with small size objects and gradually increasing users per hr.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(50)
        os.environ["STEP_TIME"] = str(60)
        os.environ["STEP_LOAD"] = str(50)
        os.environ["SPAWN_RATE"] = str(3)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(10240)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile_step_users.py",
            users=10, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21211")
    def test_small_obj_increase_session_with_http_21211(self):
        """
        Load test with small size objects and gradually increasing users per hr using http endpoint.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(50)
        os.environ["STEP_TIME"] = str(60)
        os.environ["STEP_LOAD"] = str(50)
        os.environ["SPAWN_RATE"] = str(3)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(10240)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        if "https" in self.host_url:
            host_url = self.host_url.replace("https", "http")
        else:
            host_url = self.host_url
        res = locust_runner.run_locust(
            host=host_url, locust_file="scripts/locust/locustfile_step_users.py",
            users=10, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-19538")
    def test_small_obj_sudden_spike_session_19538(self):
        """
        Load test with small size objects and sudden spike in users count.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(10)
        os.environ["STEP_TIME"] = str(1800)
        os.environ["STEP_LOAD"] = str(150)
        os.environ["SPAWN_RATE"] = str(10)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(10240)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile_step_users.py",
            users=150, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21214")
    def test_small_obj_sudden_spike_session_with_http_21214(self):
        """
        Load test with small size objects and sudden spike in users count using http endpoint.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(10)
        os.environ["STEP_TIME"] = str(1800)
        os.environ["STEP_LOAD"] = str(150)
        os.environ["SPAWN_RATE"] = str(10)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(10240)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        if "https" in self.host_url:
            host_url = self.host_url.replace("https", "http")
        else:
            host_url = self.host_url
        res = locust_runner.run_locust(
            host=host_url, locust_file="scripts/locust/locustfile_step_users.py",
            users=10, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-19542")
    @pytest.mark.skip(reason="workload is not supported")
    def test_variable_obj_multi_bucket_19542(self):
        """
        Load test with variable sizes of objects with multiple buckets
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = str(26214400)
        os.environ["MAX_OBJECT_SIZE"] = str(524288000)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21227")
    @pytest.mark.skip(reason="workload is not supported")
    def test_small_obj_max_session_with_http_21227(self):
        """
        Load test with variable sizes of objects with multiple buckets using http endpoint.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = str(26214400)
        os.environ["MAX_OBJECT_SIZE"] = str(524288000)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        if "https" in self.host_url:
            host_url = self.host_url.replace("https", "http")
        else:
            host_url = self.host_url
        res = locust_runner.run_locust(
            host=host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-19539")
    @pytest.mark.skip(reason="workload is not supported")
    def test_large_obj_multi_bucket_max_session_19539(self):
        """
        Load test with larger object size with multiple buckets
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(419430400)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21228")
    @pytest.mark.skip(reason="workload is not supported")
    def test_large_obj_multi_bucket_max_session_session_with_http_21228(self):
        """
        Load test with medium size objects and max supported concurrent sessions using HTTP endpoint
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(419430400)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        if "https" in self.host_url:
            host_url = self.host_url.replace("https", "http")
        else:
            host_url = self.host_url
        res = locust_runner.run_locust(
            host=host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-19544")
    @pytest.mark.skip(reason="workload is not supported")
    def test_large_obj_single_bucket_max_session_19544(self):
        """
        Load test with larger object size with single bucket
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(1)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(1073741824)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21229")
    @pytest.mark.skip(reason="workload is not supported")
    def test_large_obj_single_bucket_max_session_with_http_21229(self):
        """
        Load test with larger object size with single bucket using HTTP endpoint
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(1)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(1073741824)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        if "https" in self.host_url:
            host_url = self.host_url.replace("https", "http")
        else:
            host_url = self.host_url
        res = locust_runner.run_locust(
            host=host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-19545")
    @pytest.mark.skip(reason="workload is not supported")
    def test_large_obj_multiple_buckets_19545(self):
        """
        Load test with larger object size with multiple buckets and constant number of users
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(1073741824)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21230")
    @pytest.mark.skip(reason="workload is not supported")
    def test_large_obj_multiple_buckets_with_http_21230(self):
        """
        Load test with larger object size with multiple buckets and constant number of users using HTTP endpoint
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(1073741824)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        if "https" in self.host_url:
            host_url = self.host_url.replace("https", "http")
        else:
            host_url = self.host_url
        res = locust_runner.run_locust(
            host=host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
        self.log.info("Validated locust log file.")
