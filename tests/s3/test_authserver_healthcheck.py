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

"""AuthServer HealthCheck API test module."""

import os
import logging
import pytest

from commons.constants import const
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils.config_utils import read_yaml
from commons.utils.web_utils import http_head_request
from commons.utils.assert_utils import assert_equal, assert_true
from commons.utils.system_utils import path_exists, remove_file, make_dirs
from commons.helpers.node_helper import Node
from libs.s3 import S3H_OBJ, CM_CFG, S3_CFG


class TestAuthServerHealthCheckAPI:
    """AuthServer HealthCheck API Test suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.nobj = Node(hostname=CM_CFG["nodes"][0]["host"],
                        username=CM_CFG["nodes"][0]["username"],
                        password=CM_CFG["nodes"][0]["password"])
        cls.service = "haproxy"
        cls.remote_path = const.CFG_FILES[0]
        cls.auth_log_path = const.AUTHSERVER_LOG_PATH
        cls.test_dir_path = os.path.join(os.getcwd(), "testdata", "AuthServerHealthCheck")
        cls.local_file = os.path.join(cls.test_dir_path, "haproxy.cfg")
        if not path_exists(cls.test_dir_path):
            make_dirs(cls.test_dir_path)
            cls.log.info("Created path: %s", cls.test_dir_path)

    def setup_method(self):
        """Function to perform the setup ops for each test."""
        self.log.info("Started: Performing setup operations")
        resp = self.nobj.path_exists(self.remote_path)
        self.log.info(resp)
        assert_true(
            resp,
            f"Server path not exists: {self.remote_path}")
        self.log.info("Ended: performed setup operations")

    def teardown_method(self):
        """Function to perform the clean up for each test."""
        self.log.info("Started: Performing clean up operations")
        resp = self.nobj.update_auth_server_health_check_status(
            self.remote_path, self.local_file)
        self.log.info(resp)
        self.log.info("Removing local files")
        if path_exists(self.local_file):
            remove_file(self.local_file)
        self.log.info("Ended: Performed clean up operations")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-7577')
    @CTFailOn(error_handler)
    def test_authserver_response_on_health_check_enabled_1161(self):
        """Aauthserver response when health check is enabled."""
        self.log.info(
            "Started: Test authserver response when health check is enabled")
        resp = self.nobj.update_auth_server_health_check_status(
            self.remote_path, self.local_file, status="enable")
        self.log.info(resp)
        assert_true(resp, f"Failed to toggle healthcheck status of the authserver: {resp}")
        resp = S3H_OBJ.restart_s3server_service(self.service)
        assert_true(resp[0], resp[1])
        resp = self.nobj.get_authserver_log(path=self.auth_log_path)
        self.log.debug(resp)
        for _ in range(2):
            res = http_head_request(url=S3_CFG["head_urls"])
            self.log.info(res)
            assert_equal("200", str(res.status_code))
        self.log.info(
            "Ended: Test authserver response when health check is enabled")

    @pytest.mark.s3_ops
    @pytest.mark.tags('TEST-7578')
    @CTFailOn(error_handler)
    def test_authserver_response_on_health_check_disabled_1164(self):
        """Authserver response when health check is disabled."""
        self.log.info(
            "Started: Test authserver response when health check is disabled")
        resp = self.nobj.update_auth_server_health_check_status(
            self.remote_path, self.local_file, status="disable")
        self.log.info(resp)
        assert_true(resp, f"Failed to toggle healthcheck status of the authserver: {resp}")
        resp = S3H_OBJ.restart_s3server_service(self.service)
        assert_true(resp[0], resp[1])
        resp = self.nobj.get_authserver_log(path=self.auth_log_path)
        self.log.debug(resp)
        for _ in range(2):
            res = http_head_request(url=S3_CFG["head_urls"])
            self.log.info(res)
            assert_equal("200", str(res.status_code))
        self.log.info(
            "Ended: Test authserver response when health check is disabled")
