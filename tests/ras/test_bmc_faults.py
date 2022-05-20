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

"""Test suite for BMC IP related tests"""

import ast
import logging
import os
import random
import time

import pytest

from commons import constants as cons
from commons.alerts_simulator.generate_alert_lib import AlertType
from commons.alerts_simulator.generate_alert_lib import GenerateAlertLib
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.bmc_helper import Bmc
from commons.helpers.controller_helper import ControllerLib
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG
from config import RAS_TEST_CFG
from config import RAS_VAL
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.s3 import S3H_OBJ

LOGGER = logging.getLogger(__name__)


class TestBMCAlerts:
    """SSPL Server FRU Test Suite."""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("Running setup_class")
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.node_cnt = len(CMN_CFG["nodes"])
        LOGGER.info("Total number of nodes in cluster: %s", cls.node_cnt)

        LOGGER.info("Randomly picking node to create fault")
        cls.system_random = random.SystemRandom()
        cls.test_node = cls.system_random.randint(1, cls.node_cnt)

        LOGGER.info("Fault testing will be done on node: %s", cls.test_node)
        cls.host = CMN_CFG["nodes"][cls.test_node-1]["host"]
        cls.uname = CMN_CFG["nodes"][cls.test_node-1]["username"]
        cls.passwd = CMN_CFG["nodes"][cls.test_node-1]["password"]
        cls.hostname = CMN_CFG["nodes"][cls.test_node-1]["hostname"]
        cls.public_data_ip = CMN_CFG["nodes"][cls.test_node - 1][
            "public_data_ip"]
        cls.mgmt_ip = CMN_CFG["nodes"][cls.test_node - 1]["ip"]
        cls.setup_type = CMN_CFG['setup_type']
        cls.sspl_resource_id = cls.cm_cfg["sspl_resource_id"]

        cls.ras_test_obj = RASTestLib(host=cls.hostname, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.hostname, username=cls.uname,
                            password=cls.passwd)
        cls.bmc_obj = Bmc(hostname=cls.hostname, username=cls.uname,
                          password=cls.passwd)
        cls.health_obj = Health(hostname=cls.hostname, username=cls.uname,
                                password=cls.passwd)
        cls.controller_obj = ControllerLib(
            host=cls.hostname, h_user=cls.uname, h_pwd=cls.passwd,
            enclosure_ip=CMN_CFG["enclosure"]["primary_enclosure_ip"],
            enclosure_user=CMN_CFG["enclosure"]["enclosure_user"],
            enclosure_pwd=CMN_CFG["enclosure"]["enclosure_pwd"])

        cls.alert_api_obj = GenerateAlertLib()
        cls.csm_alert_obj = SystemAlerts(cls.node_obj)
        # Enable this flag for starting RMQ channel
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.s3obj = S3H_OBJ
        cls.alert_types = RAS_TEST_CFG["alert_types"]
        cls.sspl_resource_id = cls.cm_cfg["sspl_resource_id"]

        node_d = cls.health_obj.get_current_srvnode()
        cls.current_srvnode = node_d[cls.hostname.split('.')[0]] if \
            cls.hostname.split('.')[0] in node_d.keys() else assert_utils.assert_true(
            False, "Node name not found")

        resp = cls.ras_test_obj.get_nw_infc_names(node_num=cls.test_node - 1)
        cls.nw_interfaces = resp[1] if resp[0] else assert_utils.assert_true(
                                                    resp[0], "Failed to get "
                                                    "network interface names")
        cls.mgmt_device = cls.nw_interfaces["MGMT"]
        cls.public_data_device = cls.nw_interfaces["PUBLIC_DATA"]
        cls.private_data_device = cls.nw_interfaces["PRIVATE_DATA"]

        LOGGER.info("Creating objects for all the nodes in cluster")
        objs = cls.ras_test_obj.create_obj_for_nodes(ras_c=RASTestLib,
                                                     node_c=Node,
                                                     hlt_c=Health,
                                                     ctrl_c=ControllerLib,
                                                     bmc_c=Bmc)

        for i, key in enumerate(objs.keys()):
            globals()[f"srv{i+1}_hlt"] = objs[key]['hlt_obj']
            globals()[f"srv{i+1}_ras"] = objs[key]['ras_obj']
            globals()[f"srv{i+1}_nd"] = objs[key]['nd_obj']
            globals()[f"srv{i+1}_bmc"] = objs[key]['bmc_obj']

        cls.bmc_fault_flag = False
        cls.bmc_ip_change_fault = False

        cls.bmc_ip = cls.bmc_obj.get_bmc_ip()
        LOGGER.info("Successfully ran setup_class")

    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("Running setup_method")
        self.starttime = time.time()
        LOGGER.info("Check cluster health")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp)

        LOGGER.info("Retaining the original/default config")
        self.ras_test_obj.retain_config(
            self.cm_cfg["file"]["original_sspl_conf"], False)

        LOGGER.info("Performing Setup operations")

        LOGGER.info("Checking SSPL state file")
        res = self.ras_test_obj.get_sspl_state()
        if not res:
            LOGGER.info("SSPL not present updating same on server")
            response = self.ras_test_obj.check_status_file()
            assert response[0], response[1]
        LOGGER.info("Done Checking SSPL state file")

        if self.start_msg_bus:
            LOGGER.info("Running read_message_bus.py script on node")
            resp = self.ras_test_obj.start_message_bus_reader_cmd()
            assert_utils.assert_true(
                resp, "Failed to start message bus channel")
            LOGGER.info(
                "Successfully started read_message_bus.py script on node")

        LOGGER.info("Change sspl log level to DEBUG")
        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "DEBUG"})
        resp = self.ras_test_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_SSPL_LOG_LEVEL)
        LOGGER.info("Now SSPL log level is: %s", resp)

        LOGGER.info("Restarting SSPL service")
        service = self.cm_cfg["service"]
        services = [service["sspl_service"], service["kafka_service"]]
        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[
                                                        self.sspl_resource_id])
        time.sleep(self.cm_cfg["sleep_val"])

        for svc in services:
            LOGGER.info("Checking status of %s service", svc)
            resp = self.s3obj.get_s3server_service_status(service=svc,
                                                          host=self.hostname,
                                                          user=self.uname,
                                                          pwd=self.passwd)
            assert resp[0], resp[1]
            LOGGER.info("%s service is active/running", svc)

        LOGGER.info("Starting collection of sspl.log")
        res = self.ras_test_obj.sspl_log_collect()
        assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Started collection of sspl logs")

        LOGGER.info("Successfully performed Setup operations")

    # pylint: disable=too-many-statements
    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("Performing Teardown operation")
        network_fault_params = RAS_TEST_CFG["nw_port_fault"]
        if self.bmc_fault_flag:
            LOGGER.info("Resolving BMC IP port Fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_PORT_FAULT_RESOLVED,
                host_details={'host': self.public_data_ip,
                              'host_user': self.uname,
                              'host_password': self.passwd},
                input_parameters={'device': self.mgmt_device})

            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"{network_fault_params['error_msg']} up")

        if self.bmc_ip_change_fault:
            LOGGER.info("Resolving fault...")
            LOGGER.info("Revert the BMC IP change to %s", self.bmc_ip)
            resp = self.alert_api_obj.generate_alert(
                AlertType.BMC_CHANGE_FAULT_RESOLVE,
                host_details={"host": self.hostname, "host_user": self.uname,
                              "host_password": self.passwd},
                input_parameters={"bmc_ip": self.bmc_ip})
            LOGGER.debug("Response: %s", resp)
            assert_utils.assert_true(resp[0],
                                     "Failed to revert the bmc ip change")
            LOGGER.info("Successfully reverted the BMC IP change")

            LOGGER.info("Validate if BMC IP is reachable or not.")
            status = system_utils.check_ping(host=self.bmc_ip)
            assert_utils.assert_true(status,
                                     f"BMC ip {self.bmc_ip} is not reachable")
            LOGGER.info("BMC IP is reachable: %s", status)

        self.ras_test_obj.retain_config(
            self.cm_cfg["file"]["original_sspl_conf"], True)

        LOGGER.info("Change sspl log level to INFO")
        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "INFO"})
        resp = self.ras_test_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_SSPL_LOG_LEVEL)
        LOGGER.info("Now SSPL log level is: %s", resp)

        if os.path.exists(self.cm_cfg["file"]["telnet_xml"]):
            LOGGER.info("Remove telnet file")
            os.remove(self.cm_cfg["file"]["telnet_xml"])

        if self.node_obj.path_exists(
                RAS_VAL["ras_sspl_alert"]["file"]["disk_usage_temp_file"]):
            LOGGER.info("Remove temp disk usage file")
            self.node_obj.remove_file(
                filename=RAS_VAL["ras_sspl_alert"]["file"]
                ["disk_usage_temp_file"])

        LOGGER.info("Terminating the process of reading sspl.log")
        self.ras_test_obj.kill_remote_process("/sspl/sspl.log")

        LOGGER.debug("Copying contents of sspl.log")
        read_resp = self.node_obj.read_file(
            filename=self.cm_cfg["file"]["sspl_log_file"],
            local_path=self.cm_cfg["file"]["sspl_log_file"])
        LOGGER.debug(
            "======================================================")
        LOGGER.debug(read_resp)
        LOGGER.debug(
            "======================================================")

        LOGGER.info(
            "Removing file %s", self.cm_cfg["file"]["sspl_log_file"])
        self.node_obj.remove_remote_file(
            filename=self.cm_cfg["file"]["sspl_log_file"])

        if self.start_msg_bus:
            LOGGER.info("Terminating the process read_message_bus.py")
            self.ras_test_obj.kill_remote_process("read_message_bus.py")
            files = [self.cm_cfg["file"]["alert_log_file"],
                     self.cm_cfg["file"]["extracted_alert_file"],
                     self.cm_cfg["file"]["screen_log"]]
            for file in files:
                LOGGER.info("Removing log file %s from the Node", file)
                self.node_obj.remove_remote_file(filename=file)

        LOGGER.info("Restarting SSPL service")
        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[
                                                        self.sspl_resource_id])
        time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("Check cluster health")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp)

        LOGGER.info("Successfully performed Teardown operation")

    # pylint: disable=too-many-statements
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23728")
    @CTFailOn(error_handler)
    def test_bmc_ip_change_alerts_23728(self):
        """
        TEST-23606: Test verifies fault and fault resolved alert in message
        bus and CSM REST after disabling and enabling a node drive.
        """
        test_cfg = RAS_TEST_CFG["test_23728"]
        LOGGER.info("STARTED: Test alerts when BMC IP is changed.")
        LOGGER.info(
            "Step 1. Validate if BMC port is configured with correct IP.")
        if not self.bmc_ip:
            assert_utils.assert_true(False, "BMC IP is not configured on "
                                            f"node {self.hostname}")
        LOGGER.info("Step 1: BMC IP is configured for node %s: %s",
                    self.hostname, self.bmc_ip)

        LOGGER.info("Step 2. Validate if BMC IP is reachable or not.")
        status = system_utils.check_ping(host=self.bmc_ip)
        assert_utils.assert_true(status, f"BMC ip {self.bmc_ip} is not "
                                         "reachable")
        LOGGER.info("Step 2: BMC IP is pinging: %s", status)

        # TODO: Start CRUD operations in one thread
        # TODO: Start IOs in one thread
        # TODO: Start random alert generation in one thread

        inv_bmc_ip = test_cfg["inv_bmc_ip"]
        LOGGER.info("Step 3: Checking if %s is not pinging", inv_bmc_ip)
        status = system_utils.check_ping(host=inv_bmc_ip)
        assert_utils.assert_false(status, f"{inv_bmc_ip} is valid pinging ip "
                                          "Please select non-pinging valid ip")
        LOGGER.info("Step 3: Selected IP is not pinging: %s", status)

        LOGGER.info("Step 4: Configure a IP %s as BMC IP", inv_bmc_ip)
        resp = self.alert_api_obj.generate_alert(
            AlertType.BMC_CHANGE_FAULT,
            host_details={"host": self.hostname, "host_user": self.uname,
                          "host_password": self.passwd},
            input_parameters={"bmc_ip": inv_bmc_ip})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], "Failed to change the bmc ip to "
                                          "valid non-pinging ip")
        LOGGER.info("Step 4: Successfully changed bmc ip to valid non-pinging "
                    "ip")
        self.bmc_ip_change_fault = True

        time.sleep(self.cm_cfg["sleep_val"])
        LOGGER.info("Check health of node %s", self.test_node)
        resp = ast.literal_eval(f"srv{self.test_node}_hlt.check_node_health()")
        assert_utils.assert_true(resp[0], resp[1])

        if self.start_msg_bus:
            LOGGER.info("Step 5: Verifying alert logs for fault alert ")
            alert_list = [test_cfg["resource_type"], self.alert_types[
                "fault"], test_cfg["resource_id_monitor"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            assert_utils.assert_true(resp[0], "Expected alert not found. "
                                              f"Error: {resp[1]}")
            LOGGER.info("Step 5: Checked generated alert logs. Response: "
                        "%s", resp)

        LOGGER.info("Step 6: Checking CSM REST API for alert")
        resp_csm = self.csm_alert_obj.verify_csm_response(
            self.starttime, self.alert_types["fault"], False,
            test_cfg["resource_type"], test_cfg["resource_id_csm"])

        assert_utils.assert_true(resp_csm, "Expected alert not found. "
                                           f"Error: {test_cfg['csm_error_msg']}")
        LOGGER.info("Step 6: Successfully checked CSM REST API for "
                    "fault alert. Response: %s", resp_csm)

        LOGGER.info("Resolving fault...")
        LOGGER.info("Step 7: Revert the BMC IP change to %s", self.bmc_ip)
        resp = self.alert_api_obj.generate_alert(
            AlertType.BMC_CHANGE_FAULT_RESOLVE,
            host_details={"host": self.hostname, "host_user": self.uname,
                          "host_password": self.passwd},
            input_parameters={"bmc_ip": self.bmc_ip})
        LOGGER.debug("Response: %s", resp)
        assert_utils.assert_true(resp[0], "Failed to revert the bmc ip change")
        LOGGER.info("Step 7: Successfully reverted the BMC IP change")
        self.bmc_ip_change_fault = False

        time.sleep(self.cm_cfg["sleep_val"])
        LOGGER.info("Check health of node %s", self.test_node)
        resp = ast.literal_eval(f"srv{self.test_node}_hlt.check_node_health()")
        assert_utils.assert_true(resp[0], resp[1])

        if self.start_msg_bus:
            LOGGER.info("Step 8: Verifying alert logs for fault alert ")
            alert_list = [test_cfg["resource_type"], self.alert_types[
                "resolved"], test_cfg["resource_id_monitor"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            assert_utils.assert_true(resp[0], "Expected alert not found. "
                                              f"Error: {resp[1]}")
            LOGGER.info("Step 8: Checked generated alert logs. Response: "
                        "%s", resp)

        LOGGER.info("Step 9: Checking CSM REST API for alert")
        resp_csm = self.csm_alert_obj.verify_csm_response(
            self.starttime, self.alert_types["resolved"], True,
            test_cfg["resource_type"], test_cfg["resource_id_csm"])

        assert_utils.assert_true(resp_csm, "Expected alert not found. "
                                           f"Error: {test_cfg['csm_error_msg']}")
        LOGGER.info("Step 9: Successfully checked CSM REST API for "
                    "fault resolved alert. Response: %s", resp_csm)

        LOGGER.info("Step 10: Validate if BMC IP is reachable or not.")
        status = system_utils.check_ping(host=self.bmc_ip)
        assert_utils.assert_true(status, f"BMC ip {self.bmc_ip} is not "
                                         "reachable")
        LOGGER.info("Step 10: BMC IP is reachable: %s,", status)

        # TODO: Check status of CRUD operations
        # TODO: Check status of IOs
        # TODO: Check status of random alert generation

        LOGGER.info("ENDED: Test alerts when BMC IP is changed.")

    # pylint: disable=too-many-statements
    @pytest.mark.tags("TEST-23729")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_bmc_ip_port_fault_23729(self):
        """
        TEST-23729: Automate BMC IP port fault and fault-resolved scenarios by
        making respective network interface down and up.
        """
        LOGGER.info("STARTED: Verifying BMC IP port fault and "
                    "fault-resolved scenarios")

        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_port_fault"]
        host_details = {'host': self.public_data_ip, 'host_user': self.uname,
                        'host_password': self.passwd}

        ras_test_obj = RASTestLib(host=host_details["host"],
                                  username=host_details["host_user"],
                                  password=host_details["host_password"])
        health_obj = Health(hostname=host_details["host"],
                            username=host_details["host_user"],
                            password=host_details["host_password"])

        # TODO: Start CRUD operations in one thread
        # TODO: Start IOs in one thread
        # TODO: Start random alert generation in one thread

        LOGGER.info("Step 1: Generating BMC IP port faults")
        LOGGER.info("Step 1.1: Creating fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_PORT_FAULT,
            host_details=host_details,
            input_parameters={'device': self.mgmt_device})
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"{network_fault_params['error_msg']} down")
        self.bmc_fault_flag = True
        LOGGER.info("Step 1.1: Successfully created BMC IP port fault on %s",
                    self.hostname)

        wait_time = self.system_random.randint(common_params["min_wait_time"],
                                               common_params["max_wait_time"])

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 1.2: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_types["fault"],
                          network_fault_params["resource_id_monitor"].format(
                              "ebmc0")]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)

            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 1.2: Successfully checked generated alerts")

        if self.setup_type != "VM":
            LOGGER.info("Step 1.3: Validating csm alert response")
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime, self.alert_types["fault"],
                False, network_fault_params["resource_type"],
                network_fault_params["resource_id_csm"].format("ebmc0"))
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp, "Failed to get alert in CSM REST")
            LOGGER.info("Step 1.3: Successfully Validated csm alert response")

        LOGGER.info("Checking health of cluster")
        resp = health_obj.check_node_health()
        LOGGER.info("Response: %s", resp)
        # TODO: Revisit when information of expected response is available

        LOGGER.info("Step 2: Resolving fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_PORT_FAULT_RESOLVED,
            host_details=host_details,
            input_parameters={'device': self.mgmt_device})
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"{network_fault_params['error_msg']} up")
        self.mgmt_fault_flag = False
        LOGGER.info("Step 2: Successfully resolved BMC IP port fault on %s", self.hostname)

        wait_time = common_params["min_wait_time"]

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 2.1: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_types["resolved"],
                          network_fault_params["resource_id_monitor"].format(
                              "ebmc0")]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 2.1: Successfully checked generated alerts")

        if self.setup_type != "VM":
            LOGGER.info(
                "Step 2.2: Validating csm alert response after resolving fault")

            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime,
                self.alert_types["resolved"],
                True, network_fault_params["resource_type"],
                network_fault_params["resource_id_csm"].format("ebmc0"))
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp, "Failed to get alert in CSM REST")
            LOGGER.info(
                "Step 2.2: Successfully validated csm alert response after "
                "resolving fault")

        # TODO: Check status of CRUD operations
        # TODO: Check status of IOs
        # TODO: Check status of random alert generation

        LOGGER.info("ENDED: Verifying BMC IP port fault and fault-resolved "
                    "scenarios")
