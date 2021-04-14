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
from libs.s3 import S3_CFG, ACCESS_KEY, SECRET_KEY


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

    @pytest.mark.tags("EOS-19526")
    def test_small_obj_max_session_19526(self):
        """
        Load test with small size objects and max supported concurrent sessions.
        """
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(30)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(25000)
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")

    @pytest.mark.tags("EOS-19533")
    def test_small_obj_max_session_19533(self):
        """
        Load test with single bucket, fixed small size objects and max supported concurrent sessions.
        """
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(1)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(102400)
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")

    @pytest.mark.tags("EOS-19534")
    def test_small_obj_max_session_19534(self):
        """
        Load test with multiple buckets, small size objects and max supported concurrent sessions.
        """
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(100)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(25000)
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile.py",
            users=30, duration="15m")
        self.log.info(res)
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")

    @pytest.mark.tags("EOS-19537")
    def test_small_obj_max_session_19537(self):
        """
        Load test with small size objects and gradually increasing users per hr.
        """
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(50)
        os.environ["STEP_TIME"] = str(60)
        os.environ["STEP_LOAD"] = str(50)
        os.environ["SPAWN_RATE"] = str(3)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(10240)
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile_step_users.py",
            users=10, duration="15m")
        self.log.info(res)
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")

    @pytest.mark.tags("EOS-19538")
    def test_small_obj_max_session_19538(self):
        """
        Load test with small size objects and sudden spike in users count.
        locust_runner scripts/locust/locustfile.py --u 300 --t 12h
        :return:
        """
        os.environ["MAX_POOL_CONNECTIONS"] = str(100)
        os.environ["BUCKET_COUNT"] = str(10)
        os.environ["STEP_TIME"] = str(1800)
        os.environ["STEP_LOAD"] = str(150)
        os.environ["SPAWN_RATE"] = str(10)
        os.environ["MIN_OBJECT_SIZE"] = os.environ["MAX_OBJECT_SIZE"] = str(10240)
        res = locust_runner.run_locust(
            host=self.host_url, locust_file="scripts/locust/locustfile_step_users.py",
            users=150, duration="15m")
        self.log.info(res)
        log_file = res[1]["log-file"]
        if os.path.exists(log_file):
            res = locust_runner.check_log_file(log_file, error="InternalError")
            assert_utils.assert_false(res, "Few IO failed due to some reason")
