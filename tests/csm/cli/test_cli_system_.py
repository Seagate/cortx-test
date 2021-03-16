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
"""Test suite for system related operations"""

import logging
import time
import pytest
from commons.utils import assert_utils
from config import CMN_CFG
from commons.helpers import bmc_helper
from commons.helpers.node_helper import Node
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from libs.csm.cli.cortx_cli_system import CortxCliSystemtOperations
from libs.csm.cli.cortx_cli import CortxCli


class TestCliSystem:
    """CORTX CLI Test suite for system related operations"""

    @classmethod
    def setup_class(cls):
        """
        It will perform all prerequisite test suite steps if any.
            - Initialize few common variables
        """
        cls.LOGGER = logging.getLogger(__name__)
        cls.system_obj_node1 = CortxCliSystemtOperations()
        cls.system_obj_node2 = CortxCliSystemtOperations(
            host=CMN_CFG["nodes"][1]["host"],
            username=CMN_CFG["nodes"][1]["username"],
            password=CMN_CFG["nodes"][1]["password"])
        cls.bmc_obj_node2 = bmc_helper.Bmc(
            hostname=CMN_CFG["nodes"][1]["host"],
            username=CMN_CFG["nodes"][1]["username"],
            password=CMN_CFG["nodes"][1]["password"])
        cls.bmc_obj_node1 = bmc_helper.Bmc(
            hostname=CMN_CFG["nodes"][0]["host"],
            username=CMN_CFG["nodes"][0]["username"],
            password=CMN_CFG["nodes"][0]["password"])
        cls.node_stop = False
        cls.pri_node_logout = True
        cls.bmc_user = CMN_CFG["bmc"]["username"]
        cls.bmc_pwd = CMN_CFG["bmc"]["password"]
        cls.bmc_node1_ip = cls.bmc_obj_node1.get_bmc_ip()
        cls.node2_obj = CortxCli(
            host=CMN_CFG["nodes"][1]["host"],
            username=CMN_CFG["csm"]["csm_admin_user"]["username"],
            password=CMN_CFG["csm"]["csm_admin_user"]["password"])
        cls.node_helper_obj = Node(
            hostname=CMN_CFG["nodes"][1]["host"],
            username=CMN_CFG["nodes"][1]["username"],
            password=CMN_CFG["nodes"][1]["password"])

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        It is performing below operations as pre-requisites.
            - Login to CSMCLI as admin
        """
        self.LOGGER = logging.getLogger(__name__)
        self.LOGGER.info("STARTED: Setup Operations")
        self.node_stop = False
        self.pri_node_logout = True
        self.LOGGER.info("Logging into CSMCLI as admin...")
        login = self.system_obj_node1.login_cortx_cli()
        assert_utils.assert_equals(True, login[0], login[1])
        self.LOGGER.info("Logged into CSMCLI as admin successfully")
        self.LOGGER.info("ENDED: Setup Operations")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Start node if it is in stop status
            - Log out from CORTX CLI console.
        """
        self.node_helper_obj.send_systemctl_cmd("start", ["csm_agent"])
        if "Chassis Power is on" not in str(
            self.bmc_obj_node2.bmc_node_power_status(
                self.bmc_node1_ip,
                self.bmc_user,
                self.bmc_pwd)):
            self.LOGGER.info("Starting host from BMC console.")
            resp = self.bmc_obj_node2.bmc_node_power_on_off(
                self.bmc_node1_ip, self.bmc_user, self.bmc_pwd, "on")
            assert_utils.assert_equals(True, resp, resp)
            time.sleep(300)
        if self.pri_node_logout:
            self.LOGGER.info("Logging out from CSMCLI console...")
            self.system_obj_node1.logout_cortx_cli()
            self.LOGGER.info("Logged out from CSMCLI console successfully")
        if self.node_stop:
            cli_sys_ser = CortxCliSystemtOperations(
                session_obj=self.node2_obj.session_obj)
            self.csm_cli_login = cli_sys_ser.login_cortx_cli()
            assert_utils.assert_equals(
                True, self.csm_cli_login[0], self.csm_cli_login[1])
            resp = cli_sys_ser.start_node(self.node_stop)
            self.LOGGER.debug(f"Node services started: {resp}")
            assert_utils.assert_equals(True, resp[0], resp[1])
            cli_sys_ser.logout_cortx_cli()
            self.LOGGER.info("Logged out from CSMCLI console successfully")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-11742")
    @CTFailOn(error_handler)
    def test_7019_verify_node_status(self):
        """
        Test that user able to view the resource status using csmcli system status commands.
        """
        self.LOGGER.info(" Verifying system status using csmcli")
        resp = self.system_obj_node1.check_resource_status()
        assert_utils.assert_equals(True, resp[0], resp[1])
        table_resp = self.system_obj_node1.split_table_response(resp[1])
        assert_utils.assert_equals('True', table_resp[0][3], resp[1])
        assert_utils.assert_equals('True', table_resp[1][3], resp[1])
        self.LOGGER.info("Verified system status using csmcli")

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-12846")
    @CTFailOn(error_handler)
    def test_7018_node_operations(self):
        """
        Test that only root user is able to perform start,stop and shutdown options through csmcli.
        """
        self.LOGGER.info("Verifying system status using csmcli")
        resp = self.system_obj_node1.check_resource_status()
        assert_utils.assert_equals(True, resp[0], resp[1])
        table_resp = self.system_obj_node1.split_table_response(resp[1])
        assert_utils.assert_equals('True', table_resp[0][3], resp[1])
        assert_utils.assert_equals('True', table_resp[1][3], resp[1])
        self.LOGGER.info("Verified system status using csmcli")
        self.LOGGER.info("Stop primary node services from CSM")
        self.node_stop = "srvnode-1"
        resp = self.system_obj_node1.stop_node(self.node_stop)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.system_obj_node1.logout_cortx_cli()
        self.pri_node_logout = False
        self.LOGGER.info("Step 2: Stopped primary node services from CSM")
        time.sleep(120)
        self.LOGGER.info("Login to secondary node")
        self.csm_cli_login = self.system_obj_node2.login_cortx_cli()
        assert_utils.assert_equals(
            True, self.csm_cli_login[0], self.csm_cli_login[1])
        self.LOGGER.info("Logged into secondary node")
        self.LOGGER.info("Starting primary node through secondary node")
        resp = self.system_obj_node2.start_node(self.node_stop)
        time.sleep(150)
        self.node_helper_obj.send_systemctl_cmd("start", ["csm_agent"])
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.system_obj_node2.logout_cortx_cli()
        self.LOGGER.info("Started primary node through secondary node")
        self.node_stop = False
        self.LOGGER.info("Shutting down primary node")
        resp = self.system_obj_node1.login_cortx_cli()
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.node_stop = "srvnode-1"
        resp = self.system_obj_node1.shutdown_node(self.node_stop)
        time.sleep(300)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.pri_node_logout = False
        self.LOGGER.info("Shutdown down primary node")
        self.LOGGER.info("Starting node from BMC")
        if "Chassis Power is on" not in str(
            self.bmc_obj_node2.bmc_node_power_status(
                self.bmc_node1_ip,
                self.bmc_user,
                self.bmc_pwd)):
            self.LOGGER.info("Starting host from BMC console.")
            resp = self.bmc_obj_node2.bmc_node_power_on_off(
                self.bmc_node1_ip, self.bmc_user, self.bmc_pwd, "on")
            assert_utils.assert_equals(True, resp, resp)
            time.sleep(300)
        self.LOGGER.info("Started node from BMC")
        self.LOGGER.info(
            "Step 8: Starting primary node through secondary node")
        self.system_obj_node2.login_cortx_cli()
        resp = self.system_obj_node2.start_node(self.node_stop)
        time.sleep(150)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.LOGGER.info("Step 8: Started primary node through secondary node")
        self.system_obj_node2.logout_cortx_cli()
        self.node_stop = False

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-15860")
    @CTFailOn(error_handler)
    def test_7021_stop_node(self):
        """
        Test that user should able to Stop node resource using the system stop [resource_name] command.
        """
        self.LOGGER.info("Verifying system status using csmcli")
        resp = self.system_obj_node1.check_resource_status()
        assert_utils.assert_equals(True, resp[0], resp[1])
        table_resp = self.system_obj_node1.split_table_response(resp[1])
        assert_utils.assert_equals('True', table_resp[0][3], resp[1])
        assert_utils.assert_equals('True', table_resp[1][3], resp[1])
        self.LOGGER.info("Verified system status using csmcli")
        self.LOGGER.info("Stop primary node services from CSM")
        self.node_stop = "srvnode-1"
        resp = self.system_obj_node1.stop_node(self.node_stop)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.pri_node_logout = False
        self.LOGGER.info("Step 2: Stopped primary node services from CSM")
        time.sleep(120)
        self.LOGGER.info("Login to secondary node")
        resp = self.system_obj_node2.login_cortx_cli()
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.LOGGER.info("Logged into secondary node")
        self.LOGGER.info("Starting primary node through secondary node")
        resp = self.system_obj_node2.start_node(self.node_stop)
        time.sleep(150)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.LOGGER.info("Started primary node through secondary node")
        self.system_obj_node2.logout_cortx_cli()
        self.node_stop = False

    @pytest.mark.csm_cli
    @pytest.mark.tags("TEST-16213")
    @CTFailOn(error_handler)
    def test_7025_start_node(self):
        """
        Test that user is able to Start node resource using the system start [resource_name] command.
        """
        self.LOGGER.info("Verifying system status using csmcli")
        resp = self.system_obj_node1.check_resource_status()
        assert_utils.assert_equals(True, resp[0], resp[1])
        table_resp = self.system_obj_node1.split_table_response(resp[1])
        assert_utils.assert_equals('True', table_resp[0][3], resp[1])
        assert_utils.assert_equals('True', table_resp[1][3], resp[1])
        self.LOGGER.info("Verified system status using csmcli")
        self.LOGGER.info("Stop primary node services from CSM")
        self.node_stop = "srvnode-1"
        resp = self.system_obj_node1.stop_node(self.node_stop)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.pri_node_logout = False
        self.LOGGER.info("Step 2: Stopped primary node services from CSM")
        time.sleep(120)
        self.LOGGER.info("Login to secondary node")
        self.csm_cli_login = self.system_obj_node2.login_cortx_cli()
        assert_utils.assert_equals(
            True, self.csm_cli_login[0], self.csm_cli_login[1])
        self.LOGGER.info("Logged into secondary node")
        self.LOGGER.info("Starting primary node through secondary node")
        resp = self.system_obj_node2.start_node(self.node_stop)
        time.sleep(150)
        assert_utils.assert_equals(True, resp[0], resp[1])
        self.LOGGER.info("Started primary node through secondary node")
        self.system_obj_node2.logout_cortx_cli()
        self.node_stop = False
