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

"""SSPL test cases: Primary Node."""

import os
import time
import random
import logging
import pytest
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health
from commons.constants import LOG_STORE_PATH
from commons.constants import SwAlerts as const
from commons import commands as common_cmd
from commons import cortxlogging
from commons.utils.assert_utils import *
from libs.s3 import S3H_OBJ
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.ras.sw_alerts import SoftwareAlert
from commons.alerts_simulator.generate_alert_lib import GenerateAlertLib, AlertType
LOGGER = logging.getLogger(__name__)


class Test3PSvcMonitoring:
    """3rd party service monitoring test suite."""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("Running setup_class")
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.sspl_stop = cls.changed_level = cls.selinux_enabled = False

        cls.ras_test_obj = RASTestLib(host=cls.host, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                            password=cls.passwd)
        cls.csm_alert_obj = SystemAlerts(cls.node_obj)
        cls.alert_api_obj = GenerateAlertLib()
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.sw_alert_obj = SoftwareAlert(cls.host, cls.uname, cls.passwd)
        cls.cfg = RAS_VAL["ras_sspl_alert"]
        LOGGER.info("Completed setup_class")

    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("Running setup_method")
        services = self.cm_cfg["service"]
        sspl_svc = services["sspl_service"]

        LOGGER.info("Check SSPL status")
        res = self.sw_alert_obj.get_svc_status([sspl_svc])[sspl_svc]
        LOGGER.info("SSPL status response %s : ", res)
        assert res["state"] == "active", "SSPL is not in active state"

        LOGGER.info("Check CSM Web status")
        res = self.sw_alert_obj.get_svc_status(["csm_web"])["csm_web"]
        LOGGER.info("CSM web status response %s : ", res)
        assert res["state"] == "active", "CSM web is not in active state"

        LOGGER.info("Check CSM Agent status")
        res = self.sw_alert_obj.get_svc_status(["csm_agent"])["csm_agent"]
        LOGGER.info("CSM Agent status response %s : ", res)
        assert res["state"] == "active", "CSM Agent is not in active state"

        LOGGER.info("Check Kafka status")
        res = self.sw_alert_obj.get_svc_status(["kafka"])["kafka"]
        LOGGER.info("Kafka status response %s : ", res)
        assert res["state"] == "active", "Kafka is not in active state"

        LOGGER.info("Check that all the 3rd party services are enabled.")
        resp = self.sw_alert_obj.get_disabled_svcs(self.external_svcs)
        assert resp == [], f"{resp} are in disabled state"
        LOGGER.info("All 3rd party services are enabled.")

        LOGGER.info("Check that all the 3rd party services are active")
        resp = self.sw_alert_obj.get_inactive_svcs(self.external_svcs)
        assert resp == [], f"{resp} are in inactive state"
        LOGGER.info("All 3rd party services are in active state.")

        self.starttime = time.time()
        if self.start_msg_bus:
            LOGGER.info("Running read_message_bus.py script on node")
            resp = self.ras_test_obj.start_message_bus_reader_cmd()
            assert_true(resp, "Failed to start message bus reader")
            LOGGER.info("Successfully started read_message_bus.py script on node")

        LOGGER.info("Starting collection of sspl.log")
        res = self.ras_test_obj.sspl_log_collect()
        assert_true(res[0], res[1])
        LOGGER.info("Started collection of sspl logs")
        LOGGER.info("Successfully performed Setup operations")

    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("Performing Teardown operation")

        if self.changed_level:
            kv_store_path = LOG_STORE_PATH
            common_cfg =self.cfg["sspl_config"]
            res = self.ras_test_obj.update_threshold_values(
                kv_store_path, common_cfg["sspl_log_level_key"],
                common_cfg["sspl_log_dval"],
                update=True)
            assert res, "Failed to change sspl logging level"

        LOGGER.info("Terminating the process of reading sspl.log")
        self.ras_test_obj.kill_remote_process("/sspl/sspl.log")

        LOGGER.debug("Copying contents of sspl.log")
        read_resp = self.node_obj.read_file(
            filename=self.cm_cfg["file"]["sspl_log_file"],
            local_path=self.cm_cfg["file"]["sspl_log_file"])
        LOGGER.debug("======================================================")
        LOGGER.debug(read_resp)
        LOGGER.debug("======================================================")

        LOGGER.info("Removing file %s", self.cm_cfg["file"]["sspl_log_file"])
        try:
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
        except FileNotFoundError as error:
            LOGGER.warning(error)
        LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.tags("TEST-21587")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_21587_cpu_usage_threshold(self):
        """Test to validate OS server alert generation and check for fault resolved (CPU Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_4354"]

        LOGGER.info("Step 1: Generate CPU usage fault.")
        resp = self.alert_api_obj.generate_alert(AlertType.CPU_USAGE_ALERT, 
            input_parameters={"delta_cpu_usage": test_cfg["delta_cpu_usage"]})
        assert resp[0], resp[1]
        LOGGER.info("Step 1: CPU usage fault is created successfully.")
        self.default_cpu_usage = False
        
        LOGGER.info("Step 2: Keep the CPU usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 2: CPU usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], test_cfg["alert_type"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            assert resp[0] is False, resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info("Step 3: Checking CPU usage alerts on CSM REST API")
        time_lapsed = 0
        resp = False
        while(time_lapsed < self.cfg["csm_alert_gen_delay"] or resp):
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime, test_cfg["alert_type"], False, test_cfg["resource_type"])
            time.sleep(1)
            time_lapsed = time_lapsed + 1
        assert resp, self.cfg["csm_error_msg"]
        LOGGER.info("Step 3: Successfully verified CPU usage alert on CSM REST API")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21588")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_21588_memory_usage_threshold(self):
        """Test to validate OS server alert generation and check for fault resolved (CPU Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        
        test_cfg = RAS_TEST_CFG["test_4355"]

        LOGGER.info("Step 1: Simulate memory usage fault.")
        resp = self.alert_api_obj.generate_alert(AlertType.MEM_USAGE_ALERT,
            input_parameters={"delta_mem_usage": test_cfg["delta_mem_usage"]})
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Memory usage fault is simulated.")
        self.default_mem_usage = False

        LOGGER.info("Step 2: Keep the CPU usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 2: CPU usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], test_cfg["alert_type"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            assert resp[0] is False, resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info("Step 3: Check memory usage fault alert on CSM REST")
        time_lapsed = 0
        resp = False
        while(time_lapsed < self.cfg["csm_alert_gen_delay"] or resp):
            resp = self.csm_alert_obj.verify_csm_response(
                self.starttime, test_cfg["alert_type"], False, test_cfg["resource_type"])
            time.sleep(1)
            time_lapsed = time_lapsed + 1
        assert resp, self.cfg["csm_error_msg"]
        LOGGER.info("Step 3: Successfully verified memory usage alert on CSM REST ")

    @pytest.mark.tags("TEST-21586")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_21587_disk_usage_threshold(self):
        """Test to validate OS server alert generation and check for fault resolved (CPU Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_3005"]

        LOGGER.info("Step 1: Simulate Disk usage fault")
        resp = self.alert_api_obj.generate_alert(AlertType.DISK_FAULT_NO_ALERT, input_parameters={
            "du_val": test_cfg["du_val"], "fault": False, "fault_resolved": False})
        assert resp[0] is False
        LOGGER.info("Step 1: Successfully simulated Disk usage fault")
        self.default_disk_usage = False

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], test_cfg["alert_type"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            assert resp[0] is False, resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info("Step 2: Keep the disk usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 2: disk usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("Step 3: Check disk usage fault alert on CSM REST")
        time_lapsed = 0
        resp = False
        while(time_lapsed < self.cfg["csm_alert_gen_delay"] or resp):
            resp = self.csm_alert_obj.verify_csm_response(
            self.starttime, test_cfg["alert_type"], False, test_cfg["resource_type"])
            time.sleep(1)
            time_lapsed = time_lapsed + 1
        assert resp, self.cfg["csm_error_msg"]
        LOGGER.info("Step 3: Successfully verified disk usage alert on CSM REST ")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

