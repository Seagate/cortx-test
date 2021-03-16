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

import logging
import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.utils.config_utils import read_yaml
from commons.utils.web_utils import http_head_request
from commons.utils.assert_utils import assert_equal, assert_true
from commons.utils.system_utils import path_exists, remove_file
from commons.helpers.node_helper import Node
from libs.s3 import S3H_OBJ, CM_CFG

AUTH_CFG = read_yaml("config/s3/test_authserver_healthcheck.yaml")[1]


class TestAuthServerHealthCheckAPI:
    """AuthServer HealthCheck API Test suite."""

    @classmethod
    def setup_class(cls):
        """
        Function will be invoked prior to each test case.

        It will perform all prerequisite test suite steps if any.
        """
        cls.log = logging.getLogger(__name__)
        cls.cm_cfg = AUTH_CFG["test_authserver_healthcheck"]
        cls.nodeobj = Node(hostname=CM_CFG["nodes"][1]["host"],
                           username=CM_CFG["nodes"][1]["username"],
                           password=CM_CFG["nodes"][1]["password"])

    def setup_method(self):
        """Function to perform the setup ops for each test."""
        self.log.info("Started: Performing setup operations")
        resp = self.nodeobj.path_exists(self.cm_cfg["remote_file"])
        assert_true(
            resp,
            f"Server path not exists: {self.cm_cfg['remote_file']}")
        self.log.info("Ended: performed setup operations")

    def teardown_method(self):
        """Function to perform the clean up for each test."""
        self.log.info("Started: Performing clean up operations")
        resp = self.toggle_auth_server_health_check(
            self.cm_cfg["remote_file"], self.cm_cfg["local_file"])
        self.log.info(resp)
        if path_exists(self.cm_cfg["local_file"]):
            remove_file(self.cm_cfg["local_file"])
        self.log.info("Ended: Performed clean up operations")

    def toggle_auth_server_health_check(self, fpath, lpath, status="enable"):
        """
        Function to toggle healthcheck status of the authserver.

        It will add or remove entry under backend s3-auth in haproxy.cfg
        :param str fpath: remote config file path
        :param str lpath: local config file path
        :param str status: enable | disable
        :return: tuple of tupple
        """
        resg = S3H_OBJ.copy_s3server_file(fpath, lpath)
        with open(lpath, "r+") as filep:
            data = filep.readlines()
            for i in range(len(data)):
                if "enable" in status:
                    update_value = "    option httpchk HEAD / HTTP/1.1\\r\\nHost:\\ localhost\n"
                else:
                    update_value = "    #option httpchk HEAD / HTTP/1.1\\r\\nHost:\\ localhost\n"

                if "    option httpchk HEAD / HTTP/1.1\\r\\nHost:\\ localhost\n" in data[i]:
                    data[i] = update_value
                elif "    #option httpchk HEAD / HTTP/1.1\\r\\nHost:\\ localhost\n" in data[i]:
                    data[i] = update_value
            with open(lpath, "w+") as nfp:
                for i in data:
                    nfp.write(i)
        self.nodeobj.copy_file_to_remote(lpath, fpath)
        resp = self.nodeobj.path_exists(fpath)

        return resg, resp

    @pytest.mark.s3
    @pytest.mark.tags('TEST-7577')
    @CTFailOn(error_handler)
    def test_authserver_response_on_health_check_enabled_1161(self):
        """Aauthserver response when health check is enabled."""
        self.log.info(
            "Started: Test authserver response when health check is enabled")
        test_cfg = AUTH_CFG["test_1161"]
        resp = self.toggle_auth_server_health_check(
            self.cm_cfg["remote_file"],
            self.cm_cfg["local_file"],
            status=test_cfg["status"])
        self.log.info(resp)
        resp = S3H_OBJ.restart_s3server_service(self.cm_cfg["service"])
        assert_true(resp[0], resp[1])
        resp = S3H_OBJ.get_authserver_log(path=self.cm_cfg["auth_log_path"])
        self.log.debug(resp)
        res = http_head_request(url=self.cm_cfg["head_urls"][0])
        assert_equal(test_cfg["status_code"], str(res.status_code))
        self.log.info(res)
        res = http_head_request(url=self.cm_cfg["head_urls"][1])
        assert_equal(test_cfg["status_code"], str(res.status_code))
        self.log.info(res)
        self.log.info(
            "Ended: Test authserver response when health check is enabled")

    @pytest.mark.s3
    @pytest.mark.tags('TEST-7578')
    @CTFailOn(error_handler)
    def test_authserver_response_on_health_check_disabled_1164(self):
        """Authserver response when health check is disabled."""
        self.log.info(
            "Started: Test authserver response when health check is disabled")
        test_cfg = AUTH_CFG["test_1164"]
        resp = self.toggle_auth_server_health_check(
            self.cm_cfg["remote_file"],
            self.cm_cfg["local_file"],
            status=test_cfg["status"])
        self.log.info(resp)
        resp = S3H_OBJ.restart_s3server_service(self.cm_cfg["service"])
        assert_true(resp[0], resp[1])
        resp = S3H_OBJ.get_authserver_log(path=self.cm_cfg["auth_log_path"])
        self.log.debug(resp)
        res = http_head_request(url=self.cm_cfg["head_urls"][0])
        assert_equal(test_cfg["status_code"], str(res.status_code))
        self.log.info(res)
        res = http_head_request(url=self.cm_cfg["head_urls"][1])
        assert_equal(test_cfg["status_code"], str(res.status_code))
        self.log.info(res)
        self.log.info(
            "Ended: Test authserver response when health check is disabled")
