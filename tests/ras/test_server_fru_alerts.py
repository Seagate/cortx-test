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

"""Test suite for storage enclosure fru related tests."""

import os
import time
import random
import logging
import pytest
import pandas as pd
from libs.ras.ras_test_lib import RASTestLib
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health
from commons.helpers.controller_helper import ControllerLib
from libs.s3 import S3H_OBJ
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons import constants as cons
from commons import commands as common_cmd
from commons.utils.assert_utils import *
from libs.csm.rest.csm_rest_alert import SystemAlerts
from commons.alerts_simulator.generate_alert_lib import \
     GenerateAlertLib, AlertType
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG

LOGGER = logging.getLogger(__name__)


class TestServerFruAlerts:
    """SSPL Server FRU Test Suite."""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("Running setup_class")
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.host = CMN_CFG["nodes"][0]["host"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.dg_failure = False

        cls.ras_test_obj = RASTestLib(host=cls.host, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                            password=cls.passwd)
        cls.health_obj = Health(hostname=cls.host, username=cls.uname,
                                password=cls.passwd)
        cls.controller_obj = ControllerLib(
            host=cls.host, h_user=cls.uname, h_pwd=cls.passwd,
            enclosure_ip=CMN_CFG["enclosure"]["primary_enclosure_ip"],
            enclosure_user=CMN_CFG["enclosure"]["enclosure_user"],
            enclosure_pwd=CMN_CFG["enclosure"]["enclosure_pwd"])

        cls.alert_api_obj = GenerateAlertLib()
        cls.csm_alert_obj = SystemAlerts(cls.node_obj)
        # Enable this flag for starting RMQ channel
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.s3obj = S3H_OBJ
        cls.alert_types = RAS_TEST_CFG["alert_types"]

        LOGGER.info("Successfully ran setup_class")

    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("Running setup_method")
        self.starttime = time.time()
        LOGGER.info("Retaining the original/default config")
        self.ras_test_obj.retain_config(self.cm_cfg["file"]["original_sspl_conf"],
                                        False)

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
            assert_true(resp, "Failed to start message bus channel")
            LOGGER.info(
                "Successfully started read_message_bus.py script on node")

        LOGGER.info("Change sspl log level to DEBUG")
        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "DEBUG"})
        resp = self.ras_test_obj.get_conf_store_vals(url=cons.SSPL_CFG_URL,
                                                     field=cons.CONF_SSPL_LOG_LEVEL)
        LOGGER.info("Now SSPL log level is: %s", resp)

        LOGGER.info("Restarting SSPL service")
        service = self.cm_cfg["service"]
        # services = [service["sspl_service"], service["kafka_service"],
        #             service["csm_web"], service["csm_agent"]]
        self.node_obj.send_systemctl_cmd(command="restart",
                                         services=[service["sspl_service"]],
                                         decode=True)
        time.sleep(self.cm_cfg["sleep_val"])

        # Revisit when R2 HW is available.
        # for svc in services:
        #     LOGGER.info("Checking status of %s service", svc)
        #     resp = self.s3obj.get_s3server_service_status(service=svc,
        #                                                   host=self.host,
        #                                                   user=self.uname,
        #                                                   pwd=self.passwd)
        #     assert resp[0], resp[1]
        #     LOGGER.info("%s service is active/running", svc)

        LOGGER.info("Starting collection of sspl.log")
        res = self.ras_test_obj.sspl_log_collect()
        assert_true(res[0], res[1])
        LOGGER.info("Started collection of sspl logs")

        LOGGER.info("Successfully performed Setup operations")

    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("Performing Teardown operation")
        self.ras_test_obj.retain_config(self.cm_cfg["file"]["original_sspl_conf"],
                                        True)

        LOGGER.info("Change sspl log level to INFO")
        self.ras_test_obj.set_conf_store_vals(
             url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "INFO"})
        resp = self.ras_test_obj.get_conf_store_vals(url=cons.SSPL_CFG_URL,
                                                     field=cons.CONF_SSPL_LOG_LEVEL)
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
        self.node_obj.remove_file(filename=self.cm_cfg["file"]["sspl_log_file"])

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
        service = self.cm_cfg["service"]
        self.node_obj.send_systemctl_cmd(command="restart",
                                         services=[service["sspl_service"]],
                                         decode=True)
        time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-23606")
    @CTFailOn(error_handler)
    def test_disable_enable_os_drive_23606(self):
        """
        TEST-23606: Test verifies fault and fault resolved alert in message
        bus and CSM REST after disabling and enabling a node drive.
        """
        LOGGER.info("STARTED: Test alerts for OS disk removal and insertion")

        common_cfg = RAS_VAL["ras_sspl_alert"]
        csm_error_msg = common_cfg["csm_error_msg"]
        test_cfg = RAS_TEST_CFG["TEST-23606"]

        LOGGER.info("Step 1: Getting details of drive to be removed")
        resp = self.ras_test_obj.get_node_drive_details()
        assert_true(resp[0], resp)

        drive_name = resp[1].split("/")[2]
        host_num = resp[2]
        drive_count = resp[3]
        LOGGER.info(f"Drive details:\nOS drive name: {drive_name} \n"
                    f"Host number: {host_num} \n"
                    f"OS Drive count: {drive_count} \n")


        LOGGER.info("Step 2: Disabling phy number %s", phy_num)
        resp = self.alert_api_obj.generate_alert(
            AlertType.DISK_DISABLE,
            input_parameters={"enclid": test_cfg["encl"],
                              "ctrl_name": test_cfg["ctrl"],
                              "phy_num": phy_num,
                              "operation": test_cfg["operation_fault"],
                              "exp_status": test_cfg["degraded_phy_status"],
                              "telnet_file": common_cfg["file"]["telnet_xml"]})
        assert_true(resp[0], resp[1])

        phy_stat = test_cfg["degraded_phy_status"]
        LOGGER.info("Step 2: Successfully put phy in %s state", phy_stat)

        if phy_num < 10:
            resource_id = "disk_00.0{}".format(phy_num)
        else:
            resource_id = "disk_00.{}".format(phy_num)
        time.sleep(common_cfg["sleep_val"])

        LOGGER.info("Step 3: Checking CSM REST API for alert")
        time.sleep(common_cfg["csm_alert_gen_delay"])
        resp_csm = self.csm_alert_obj.verify_csm_response(self.starttime,
                                                          test_cfg[
                                                              "alert_type"],
                                                          False,
                                                          test_cfg[
                                                              "resource_type"],
                                                          resource_id)

        LOGGER.info("Step 4: Clearing metadata of drive %s", phy_num)
        drive_num = f"0.{phy_num}"
        resp = self.controller_obj.clear_drive_metadata(drive_num=drive_num)
        assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Cleared %s drive metadata successfully", drive_num)

        LOGGER.info("Step 5: Again enabling phy number %s", phy_num)
        i = 0
        while i < test_cfg["retry"]:
            resp = self.alert_api_obj.generate_alert(
                AlertType.DISK_ENABLE,
                input_parameters={"enclid": test_cfg["encl"],
                                  "ctrl_name": test_cfg["ctrl"],
                                  "phy_num": phy_num,
                                  "operation": test_cfg[
                                      "operation_fault_resolved"],
                                  "exp_status": test_cfg["ok_phy_status"],
                                  "telnet_file": common_cfg["file"][
                                      "telnet_xml"]})

            phy_stat = test_cfg["ok_phy_status"]
            if resp[1] == phy_stat:
                break
            elif i == 1:
                assert phy_stat == resp[1], f"Step 4: Failed to put phy in " \
                                            f"{phy_stat} state"

        LOGGER.info("Step 5: Successfully put phy in %s state", phy_stat)

        if self.start_msg_bus:
            LOGGER.info("Step 6: Checking the generated alert logs")
            alert_list = [test_cfg["resource_type"], test_cfg["alert_type"],
                          resource_id]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            assert_true(resp[0], resp[1])
            LOGGER.info("Step 6: Checked generated alert logs")

        assert_true(resp_csm, csm_error_msg)
        LOGGER.info("Step 3: Successfully checked CSM REST API for alerts")

        LOGGER.info(
            "ENDED: Test Disabling a drive from disk group")
