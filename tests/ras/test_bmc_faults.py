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

"""Test suite for server fru related tests"""

import os
import time
import random
import logging
import pytest
import pandas as pd
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health
from commons.helpers.controller_helper import ControllerLib
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons import constants as cons
from commons import commands as common_cmd
from commons.utils import assert_utils
from commons.alerts_simulator.generate_alert_lib import \
    GenerateAlertLib, AlertType
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.s3 import S3H_OBJ

LOGGER = logging.getLogger(__name__)


class TestServerFruAlerts:
    """SSPL Server FRU Test Suite."""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("Running setup_class")
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.node_cnt = len(CMN_CFG["nodes"])
        LOGGER.info("Total number of nodes in cluster: %s", cls.node_cnt)

        LOGGER.info("Randomly picking node to create fault")
        cls.test_node = random.randint(1, cls.node_cnt)

        LOGGER.info("Fault testing will be done on node: %s", cls.test_node)
        cls.host = CMN_CFG["nodes"][cls.test_node - 1]["host"]
        cls.uname = CMN_CFG["nodes"][cls.test_node - 1]["username"]
        cls.passwd = CMN_CFG["nodes"][cls.test_node - 1]["password"]
        cls.hostname = CMN_CFG["nodes"][cls.test_node - 1]["hostname"]

        cls.ras_test_obj = RASTestLib(host=cls.hostname, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.hostname, username=cls.uname,
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

        LOGGER.info("Creating objects for all the nodes in cluster")
        objs = cls.ras_test_obj.create_obj_for_nodes(ras_c=RASTestLib,
                                                     node_c=Node,
                                                     hlt_c=Health,
                                                     ctrl_c=ControllerLib)

        for i, key in enumerate(objs.keys()):
            globals()[f"srv{i+1}_hlt"] = objs[key]['hlt_obj']

        cls.md_device = RAS_VAL["raid_param"]["md0_path"]
        cls.server_psu_fault = False
        LOGGER.info("Successfully ran setup_class")

    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("Running setup_method")
        LOGGER.info("Check cluster health")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        self.starttime = time.time()
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

    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("Performing Teardown operation")
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
        self.node_obj.remove_file(
            filename=self.cm_cfg["file"]["sspl_log_file"])

        if self.start_msg_bus:
            LOGGER.info("Terminating the process read_message_bus.py")
            self.ras_test_obj.kill_remote_process("read_message_bus.py")
            files = [self.cm_cfg["file"]["alert_log_file"],
                     self.cm_cfg["file"]["extracted_alert_file"],
                     self.cm_cfg["file"]["screen_log"]]
            for file in files:
                LOGGER.info("Removing log file %s from the Node", file)
                self.node_obj.remove_file(filename=file)

        LOGGER.info("Restarting SSPL service")
        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[
                                                        self.sspl_resource_id])
        time.sleep(self.cm_cfg["sleep_val"])
        LOGGER.info("Check cluster health")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23728")
    @CTFailOn(error_handler)
    def test_bmc_ip_change_alerts_23728(self):
        """
        TEST-23606: Test verifies fault and fault resolved alert in message
        bus and CSM REST after disabling and enabling a node drive.
        """
        LOGGER.info("STARTED: Test alerts when BMC IP is changed.")
        LOGGER.info(
            "Step 1. Validate if BMC port is configured with correct IP.")
        bmc_ip = 
        self.log.info(f"Configured BMC IP on primary node: {bmc_ip}.")
        if not bmc_ip:
            self.error(f"BMC IP is not configured on primary node, {bmc_ip}.")
        self.log.info("Step 2. Validate if BMC IP is reachable or not.")
        status = FUTIL_OBJ.ping_ip(ip=bmc_ip)
        self.log.info(f"BMC IP pingable: {status}.")
        if not status:
            self.error(f"BMC IP '{bmc_ip}' is not reachable.")
        self.log.info(
            "Step 3: Configure a static IP which is not pingable to the BMC port.")
        ip_change_status = FAULT_OBJ.create_bmc_ip_change_fault()
        self.log.info(f"Create bmc ip change fault status: {ip_change_status}.")
        if not ip_change_status:
            self.df[string]['RAS'] = 'Fail'
