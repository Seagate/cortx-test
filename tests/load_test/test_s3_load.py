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

"""Bucket Location Test Module."""

import logging
import os
from datetime import datetime, timedelta

import pytest

from commons.constants import Sizes
from commons.utils import assert_utils
from config.s3 import S3_CFG
from libs.s3 import ACCESS_KEY, SECRET_KEY
from scripts.locust import locust_runner

error_strings = ["InternalError", "Gateway Timeout", "ServiceUnavailable", "ValueError",
                 "bad interpreter", "exceptions", "stderr", "error"]

INPUT_DURATION = "00:10:00"  # HH:MM:SS
duration_t = datetime.strptime(INPUT_DURATION, "%H:%M:%S")
delta = timedelta(hours=duration_t.hour, minutes=duration_t.minute, seconds=duration_t.second)
DURATION_S = int(delta.total_seconds())
DURATION = str(DURATION_S)+"s"


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
        cls.locust_file = "scripts/locust/locustfile.py"
        cls.locust_step_user_file = "scripts/locust/locustfile_step_users.py"

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
        os.environ["USE_SSL"] = "True" if S3_CFG["use_ssl"] else "False"
        os.environ["CA_CERT"] = S3_CFG["s3_cert_path"] if S3_CFG["validate_certs"] else "False"
        os.environ.setdefault("ENDPOINT_URL", self.host_url)
        self.log.info("USE_SSL %s, CA_CERT %s, ENDPOINT_URL %s",
                      os.getenv("USE_SSL"), os.getenv("CA_CERT"), self.host_url)
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

    @staticmethod
    def check_errors(log_file):
        """Check errors in logfile"""
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error_strings)
            assert_utils.assert_false(res, "Few IO failed due to some reason")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-19533")
    def test_single_bkt_small_obj_max_session_19533(self):
        """
        Load test with single bucket, fixed small size objects and max supported concurrent sessions
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(1)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(102400)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-19533", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
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
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(25*Sizes.KB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-19526", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
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
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(25*Sizes.KB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-19534", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
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
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(10*Sizes.KB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-19537", host=self.host_url,
                                       locust_file=self.locust_step_user_file,
                                       users=10, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
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
        os.environ["DURATION"] = str(DURATION_S)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(10*Sizes.KB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-19538", host=self.host_url,
                                       locust_file=self.locust_step_user_file,
                                       users=150, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21039")
    @pytest.mark.skip(reason="Retired test. Duplicate of TEST-19533, with http")
    def test_single_bkt_small_obj_max_session_with_http_21039(self):
        """
        Load test with single bucket, fixed small size objects and max supported
        concurrent sessions using http endpoint.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(1)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(100*Sizes.KB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-21039", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21195")
    @pytest.mark.skip(reason="Retired test. Duplicate of TEST-19526, with http")
    def test_small_obj_max_session_with_http_21195(self):
        """
        Load test with small size objects and max supported concurrent sessions using http endpoint.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(25*Sizes.KB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-21195", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21210")
    @pytest.mark.skip(reason="Retired test. Duplicate of TEST-19534, with http")
    def test_small_obj_multi_bkt_max_session_with_http_21210(self):
        """
        Load test with multiple buckets, small size objects and max supported
        concurrent sessions using http endpoint.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(100)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(25*Sizes.KB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-21210", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21211")
    @pytest.mark.skip(reason="Retired test. Duplicate of TEST-19537, with http")
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
        os.environ["DURATION"] = str(DURATION_S)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(10*Sizes.KB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-21211", host=self.host_url,
                                       locust_file=self.locust_step_user_file,
                                       users=10, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21214")
    @pytest.mark.skip(reason="Retired test. Duplicate of TEST-19538, with http")
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
        os.environ["DURATION"] = str(DURATION_S)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(10*Sizes.KB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-21214", host=self.host_url,
                                       locust_file=self.locust_step_user_file,
                                       users=10, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21227")
    @pytest.mark.skip(reason="Retired test. Duplicate of TEST-19542, with http")
    def test_small_obj_max_session_with_http_21227(self):
        """
        Load test with variable sizes of objects with multiple buckets using http endpoint.
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = str(25 * Sizes.MB)
        os.environ["MAX_OBJECT_SIZE"] = str(500 * Sizes.MB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-21227", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
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
        os.environ["MIN_OBJECT_SIZE"] = str(25*Sizes.MB)
        os.environ["MAX_OBJECT_SIZE"] = str(500*Sizes.MB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-19542", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
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
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(400*Sizes.MB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-19539", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21228")
    @pytest.mark.skip(reason="Retired test. Duplicate of TEST-19539, with http")
    def test_large_obj_multi_bucket_max_session_session_with_http_21228(self):
        """
        Load test with medium size objects and max supported concurrent sessions using HTTP endpoint
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(400*Sizes.MB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-21228", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
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
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(1*Sizes.GB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-19544", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21229")
    @pytest.mark.skip(reason="Retired test. Duplicate of TEST-19544, with http")
    def test_large_obj_single_bucket_max_session_with_http_21229(self):
        """
        Load test with larger object size with single bucket using HTTP endpoint
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(1)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(1*Sizes.GB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-21229", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
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
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(1*Sizes.GB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-19545", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
        self.log.info("Validated locust log file.")

    @pytest.mark.s3_io_load
    @pytest.mark.tags("TEST-21230")
    @pytest.mark.skip(reason="Retired test. Duplicate of TEST-19545, with http")
    def test_large_obj_multiple_buckets_with_http_21230(self):
        """
        Load test with larger object size with multiple buckets and constant number of users
        using HTTP endpoint
        """
        self.log.info("Setting up test configurations")
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(1*Sizes.GB)
        self.log.info("Configurations completed successfully.")
        self.log.info("Starting locust run.")
        res = locust_runner.run_locust(test_id="TEST-21230", host=self.host_url,
                                       locust_file=self.locust_file, users=30, duration=DURATION)
        self.log.info(res)
        self.log.info("Successfully executed locust run.")
        self.log.info("Checking locust log file.")
        log_file = res[1]["log-file"]
        self.check_errors(log_file)
        self.log.info("Validated locust log file.")
