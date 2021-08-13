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

import time
import os
import logging
import re
import pytest
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG, S3_CFG, S3_OBJ_TST
from commons.constants import SwAlerts as const
from commons import constants as cons
from commons import cortxlogging
from commons.utils.config_utils import read_properties_file
from commons.utils.assert_utils import *
from commons.utils.system_utils import create_file, path_exists, make_dirs
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.ras.sw_alerts import SoftwareAlert
from libs.s3 import s3_test_lib
LOGGER = logging.getLogger(__name__)


class TestServerOS:
    """3rd party service monitoring test suite."""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("Running setup_class...")
        cls.s3_test_obj = s3_test_lib.S3TestLib(endpoint_url=S3_CFG["s3_url"])
        cls.bkt_name_prefix = "serverOS"
        cls.obj_name_prefix = "serverOS"
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.cfg = RAS_VAL["ras_sspl_alert"]
        cls.changed_level = False
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.sw_alert_obj = SoftwareAlert(cls.host, cls.uname, cls.passwd)
        cls.ras_test_obj = RASTestLib(
            host=cls.host,
            username=cls.uname,
            password=cls.passwd)
        cls.csm_alert_obj = SystemAlerts(cls.sw_alert_obj.node_utils)
        cls.default_cpu_usage = False
        cls.default_mem_usage = False
        cls.default_disk_usage = False
        cls.default_cpu_fault = False
        cls.starttime = time.time()
        cls.sw_alert_objs = []
        for i in range(len(CMN_CFG["nodes"])):
            host = CMN_CFG["nodes"][i]["hostname"]
            uname = CMN_CFG["nodes"][i]["username"]
            passwd = CMN_CFG["nodes"][i]["password"]
            cls.sw_alert_objs.append(SoftwareAlert(host, uname, passwd))
        LOGGER.info("Completed setup_class.")

    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("Running setup_method...")
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

        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "DEBUG"})
        resp = self.ras_test_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL,
            field=cons.CONF_SSPL_LOG_LEVEL)
        LOGGER.info("Now SSPL log level is: %s", resp)

        LOGGER.info("Restarting sspl service")
        resp = self.sw_alert_obj.health_obj.restart_pcs_resource(self.cm_cfg["sspl_resource_id"])
        assert resp, "Failed to restart sspl-ll"
        time.sleep(self.cm_cfg["sspl_timeout"])
        LOGGER.info("Verifying the status of sspl service is online")

        self.starttime = time.time()
        if self.start_msg_bus:
            LOGGER.info("Running read_message_bus.py script on node")
            resp = self.sw_alert_obj.start_message_bus_reader_cmd()
            assert resp, "Failed to start message bus reader"
            LOGGER.info("Successfully started read_message_bus.py script on node")

        LOGGER.info("Starting collection of sspl.log")
        res = self.ras_test_obj.sspl_log_collect()
        assert res[0], res[1]
        LOGGER.info("Started collection of sspl logs")
        self.default_cpu_usage = False
        self.default_mem_usage = False
        self.default_disk_usage = False
        LOGGER.info("Completed setup_method.")

    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("Performing Teardown operation")

        LOGGER.info("Terminating the process of reading sspl.log")
        self.ras_test_obj.kill_remote_process("/sspl/sspl.log")

        LOGGER.debug("Copying contents of sspl.log")
        read_resp = self.sw_alert_obj.node_utils.read_file(
            filename=self.cm_cfg["file"]["sspl_log_file"],
            local_path=self.cm_cfg["file"]["sspl_log_file"])
        LOGGER.debug("======================================================")
        LOGGER.debug(read_resp)
        LOGGER.debug("======================================================")

        LOGGER.info("Removing file %s", self.cm_cfg["file"]["sspl_log_file"])
        try:
            self.sw_alert_obj.node_utils.remove_file(
                filename=self.cm_cfg["file"]["sspl_log_file"])
            if self.start_msg_bus:
                LOGGER.info("Terminating the process read_message_bus.py")
                self.ras_test_obj.kill_remote_process("read_message_bus.py")
                files = [self.cm_cfg["file"]["alert_log_file"],
                         self.cm_cfg["file"]["extracted_alert_file"],
                         self.cm_cfg["file"]["screen_log"]]
                for file in files:
                    LOGGER.info("Removing log file %s from the Node", file)
                    self.sw_alert_obj.node_utils.remove_file(filename=file)
        except FileNotFoundError as error:
            LOGGER.warning(error)
        LOGGER.info("Successfully performed Teardown operation")

        LOGGER.info("Change sspl log level to INFO")
        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "INFO"})
        resp = self.ras_test_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_SSPL_LOG_LEVEL)
        LOGGER.info("Now SSPL log level is: %s", resp)

        LOGGER.info("Restarting sspl service")
        resp = self.sw_alert_obj.health_obj.restart_pcs_resource(
            self.cm_cfg["sspl_resource_id"])
        assert resp, "Failed to restart sspl-ll"
        time.sleep(self.cm_cfg["sspl_timeout"])
        LOGGER.info("Verifying the status of sspl service is online")

        if self.default_cpu_usage:
            LOGGER.info("Updating default CPU usage threshold value")
            resp = self.sw_alert_obj.resolv_cpu_usage_fault_thresh(
                self.default_cpu_usage)
            assert resp[0], resp[1]

        if self.default_mem_usage:
            LOGGER.info("Updating default Memory usage threshold value")
            resp = self.sw_alert_obj.resolv_mem_usage_fault(
                self.default_mem_usage)
            assert resp[0], resp[1]

        if self.default_disk_usage:
            LOGGER.info("Updating default Memory usage threshold value")
            resp = self.sw_alert_obj.resolv_disk_usage_fault(
                self.default_disk_usage)
            assert resp[0], resp[1]

        if self.default_cpu_fault:
            LOGGER.info("Step 4: Resolving CPU fault.")
            resp = self.sw_alert_obj.resolv_cpu_fault(self.default_cpu_fault)
            assert resp[0], resp[1]

    @pytest.mark.tags("TEST-21587")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_21587_cpu_usage_threshold(self):
        """Test to validate OS server alert generation and check for fault resolved (CPU Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21587"]

        self.default_cpu_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_CPU_USAGE)
        LOGGER.info("Step 1: Generate CPU usage fault.")
        resp = self.sw_alert_obj.gen_cpu_usage_fault_thres(
            test_cfg["delta_cpu_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 1: CPU usage fault is created successfully.")

        LOGGER.info(
            "Step 2: Keep the CPU usage above threshold for %s seconds",
            self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 2: CPU usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info("Step 3: Checking CPU usage fault alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Successfully verified CPU usage fault alert on CSM REST API")

        self.starttime = time.time()
        LOGGER.info("Step 4: Resolving CPU usage fault.")
        LOGGER.info("Updating default CPU usage threshold value")
        resp = self.sw_alert_obj.resolv_cpu_usage_fault_thresh(
            self.default_cpu_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 4: CPU usage fault is resolved.")
        self.default_cpu_usage = False

        LOGGER.info(
            "Step 5: Keep the CPU usage below threshold for %s seconds",
            self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: CPU usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info(
            "Step 6: Checking CPU usage resolved alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 6: Successfully verified CPU usage alert on CSM REST API")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21588")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_21588_memory_usage_threshold(self):
        """Test to validate OS server alert generation and check for fault resolved (CPU Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21588"]

        self.default_mem_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_MEM_USAGE)
        LOGGER.info("Step 1: Generate memory usage fault.")
        resp = self.sw_alert_obj.gen_mem_usage_fault(
            test_cfg["delta_mem_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Memory usage fault is created successfully.")

        LOGGER.info(
            "Step 2: Keep the Memory usage above threshold for %s seconds",
            self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 2: Memory usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info(
            "Step 3: Checking Memory usage fault alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Successfully verified Memory usage fault alert on CSM REST API")

        self.starttime = time.time()
        LOGGER.info("Step 4: Resolving Memory usage fault.")
        LOGGER.info("Updating default Memory usage threshold value")
        resp = self.sw_alert_obj.resolv_mem_usage_fault(self.default_mem_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Memory usage fault is resolved.")
        self.default_mem_usage = False

        LOGGER.info(
            "Step 5: Keep the memory usage below threshold for %s seconds",
            self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: Memory usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info(
            "Step 6: Checking Memory usage resolved alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 6: Successfully verified Memory usage alert on CSM REST API")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21586")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_21587_disk_usage_threshold(self):
        """Test to validate OS server alert generation and check for fault resolved (Disk Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21586"]

        self.default_disk_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_DISK_USAGE)
        LOGGER.info("Step 1: Generate memory usage fault.")
        resp = self.sw_alert_obj.gen_disk_usage_fault(
            test_cfg["delta_disk_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 1: Memory usage fault is created successfully.")

        LOGGER.info(
            "Step 2: Keep the Memory usage above threshold for %s seconds",
            self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 2: Memory usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info(
            "Step 3: Checking Memory usage fault alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Successfully verified Memory usage fault alert on CSM REST API")

        self.starttime = time.time()
        LOGGER.info("Step 4: Resolving Memory usage fault.")
        LOGGER.info("Updating default Memory usage threshold value")
        resp = self.sw_alert_obj.resolv_disk_usage_fault(
            self.default_disk_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 4: Memory usage fault is resolved.")
        self.default_mem_usage = False

        LOGGER.info("Step 5: Keep the memory usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info(
            "Step 5: Keep the memory usage below threshold for %s seconds",
            self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: Memory usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info("Step 6: Checking Memory usage resolved alerts on CSM REST API")

        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]

        LOGGER.info(
            "Step 6: Successfully verified Memory usage alert on CSM REST API")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-23045")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_23045_cpu_fault(self):
        """Test CPU fault and fault resolved alert.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_23045"]
        self.default_cpu_fault = test_cfg["faulty_cpu_id"]
        LOGGER.info("Step 1: Generate CPU fault.")
        resp = self.sw_alert_obj.gen_cpu_fault(test_cfg["faulty_cpu_id"])
        assert resp[0], resp[1]
        LOGGER.info("Step 1: CPU fault is created successfully.")

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info("Step 3: Checking CPU fault alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Successfully verified Memory usage fault alert on CSM REST API")

        self.starttime = time.time()
        LOGGER.info("Step 4: Resolving CPU fault.")
        resp = self.sw_alert_obj.resolv_cpu_fault(test_cfg["faulty_cpu_id"])
        assert resp[0], resp[1]
        LOGGER.info("Step 4: CPU fault is resolved.")
        self.default_cpu_fault = False

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info(
            "Step 6: Checking CPU fault resolved alerts on CSM REST API")

        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]

        LOGGER.info(
            "Step 6: Successfully verified CPU fault resolved alert on CSM REST API")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-22786")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_22786_memory_usage(self):
        """
        Test Scenario :
        1. Increasing memory usage gradually on each node
        (used stress tool for increasing memory usage)
        2. Verify memory usage should be greater than threshold value
        (Verify threshold value from /etc/sspl.conf file)
        3. Verify memory usage fault alert after increasing memory usage
        (verify alert using CSM rest and SSPL)
        4. Wait for timespan and check memory usage alerts are resolved on SSPl and CSM rest
        (consider timespan (-t parameter) from CMD_INCREASE_MEMORY command)

        Test objective:
        Verify memory usage fault and fault resolved alert should be present
        after increasing and decreasing memory usage
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        start_time = time.time()
        cpu_usage = read_properties_file(
            "/etc/sspl.conf")["cpu_usage_threshold"]
        test_cfg = RAS_TEST_CFG["test_22786"]
        cmn_cfg = RAS_TEST_CFG["common_cfg"]
        for obj in self.sw_alert_objs:
            LOGGER.info(
                "Step 1: Checking available memory usage and convert it to GB")
            resp = obj.get_available_memory_usage()
            LOGGER.info("Available memory : %s", resp)
            LOGGER.info("Step 1: Calculated available memory usage in GB")
            LOGGER.info("Step 2: Installing stress tool on the system")
            resp = obj.install_tool("stress")
            LOGGER.info(resp)
            LOGGER.info("Step 2: Installed stress tool on the system")
            flag = False
            while not flag:

                LOGGER.info(
                    "Step 3: Increasing the memory utilization in the factor of GB")
                resp = obj.increase_memory(
                    vm_count=test_cfg["vm_count"],
                    memory_size=test_cfg["memory_size"],
                    timespan=test_cfg["timespan"])
                LOGGER.info(resp)
                LOGGER.info(
                    "Step 3: Increased the memory utilization in the factor of GB")
                LOGGER.info("Step 4: Verifying memory utilization on %s node", obj.host)
                if float(obj.check_memory_utilization().strip()) >= int(cpu_usage):
                    flag = True
                    break
                LOGGER.info("Step 4: Verified memory utilization on %s node", obj.host)
        if self.start_msg_bus:
            LOGGER.info("Step 5: Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Step 5: Verified the generated alert on the SSPL")
        LOGGER.info("Step 6: Checking CPU fault alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            start_time,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 6: Successfully verified Memory usage fault alert on CSM REST API")
        starttime = time.time()
        LOGGER.info("Resolving CPU fault.")
        resp = self.sw_alert_obj.resolv_cpu_fault(cmn_cfg["faulty_cpu_id"])
        assert resp[0], resp[1]
        LOGGER.info("CPU fault is resolved.")
        self.default_cpu_fault = False
        if self.start_msg_bus:
            LOGGER.info("Step 7: Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Step 7: Verified the generated alert on the SSPL")
        LOGGER.info(
            "Step 8: Checking CPU fault resolved alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]

        LOGGER.info(
            "Step 8: Successfully verified CPU fault resolved alert on CSM REST API")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-22787")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_22787_cpu_usage(self):
        """
        TEST cpu usage fault and fault resolved alert with gradual
        increase in CPU usage on each node of the cluster sequentially.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        start_time = time.time()
        test_cfg = RAS_TEST_CFG["test_22787"]
        cmn_cfg = RAS_TEST_CFG["common_cfg"]
        for obj in self.sw_alert_objs:
            LOGGER.info("Step 1: Getting CPU count")
            cpu_cnt = obj.get_available_cpus()
            LOGGER.info("Available CPU count : %s", cpu_cnt)
            LOGGER.info("Step 1: Calculated available CPU count")
            LOGGER.info("Initiating blocking process on each cpu")
            for i in range(len(cpu_cnt)):
                flag = False
                while not flag:
                    LOGGER.info("Step 2: Initiating blocking process")
                    obj.initiate_blocking_process()
                    LOGGER.info("Step 2: Initiated blocking process")
                    LOGGER.info("Step 3: Calculate CPU utilization")
                    resp = obj.get_cpu_utilization(interval=test_cfg["interval"])
                    if float(resp.decode('utf-8').strip()) >= 100:
                        flag = True
                        break
                    LOGGER.info("Step 3: Calculated CPU utilization")
            if self.start_msg_bus:
                LOGGER.info("Step 4: Checking the generated alert on SSPL")
                alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
                resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 4: Verified the generated alert on the SSPL")

            LOGGER.info("Step 5: Checking CPU usage fault alerts on CSM REST API")
            resp = self.csm_alert_obj.wait_for_alert(self.cfg["csm_alert_gen_delay"],
                                                     start_time, const.AlertType.FAULT, False,
                                                     test_cfg["resource_type"])
            assert resp[0], resp[1]
            LOGGER.info("Step 5: Successfully verified CPU usage fault alert on CSM REST API")

            LOGGER.info("Fetching PID's for yes command")
            resp = obj.get_command_pid("yes")
            process_id = re.findall(r'(\d+) \?', resp.decode('utf-8').strip())
            LOGGER.info("Collected PID's for yes command")
            LOGGER.info("Step 6: Killing the process one by one")
            for i in process_id:
                resp = obj.kill_process(i)
            LOGGER.info("Step 6: Processes are killed by one by one")
            LOGGER.info("Step 7: Verify memory utilization is decreasing")
            resp = obj.get_cpu_utilization(interval=test_cfg["interval"])
            assert float(resp.decode('utf-8').strip()) < 100
            LOGGER.info("Step 7: Verified memory utilization is decreasing")
            starttime = time.time()
            LOGGER.info("Step 8: Resolving CPU fault.")
            resp = self.sw_alert_obj.resolv_cpu_fault(cmn_cfg["faulty_cpu_id"])
            assert resp[0], resp[1]
            LOGGER.info("Step 8: CPU fault is resolved.")
            self.default_cpu_fault = False
            if self.start_msg_bus:
                LOGGER.info("Step 9: Checking the generated alert on SSPL")
                alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 9: Verified the generated alert on the SSPL")

            LOGGER.info(
                "Step 10: Checking CPU fault resolved alerts on CSM REST API")

            resp = self.csm_alert_obj.wait_for_alert(
                self.cfg["csm_alert_gen_delay"],
                starttime,
                const.AlertType.RESOLVED,
                True,
                test_cfg["resource_type"])
            assert resp[0], resp[1]

            LOGGER.info(
                "Step 10: Successfully verified CPU fault resolved alert on CSM REST API")

        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-22844")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_22844_cpu_usage_parallel(self):
        """
        TEST cpu usage fault and fault resolved alert with gradual
        increase in CPU usage on each node of the cluster sequentially.
        TEST cpu usage fault and fault resolved alert with gradual
        increase in CPU usage on each node of the cluster parallelly.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        start_time = time.time()
        test_cfg = RAS_TEST_CFG["test_22787"]
        cmn_cfg = RAS_TEST_CFG["common_cfg"]
        for obj in self.sw_alert_objs:
            LOGGER.info("Step 1: Getting CPU count")
            cpu_cnt = obj.get_available_cpus()
            LOGGER.info("Available CPU count : %s", cpu_cnt)
            LOGGER.info("Step 1: Calculated available CPU count")
            LOGGER.info("Initiating blocking process on each cpu")
            for i in range(len(cpu_cnt)):
                flag = False
                while not flag:
                    LOGGER.info("Step 2: Initiating blocking process parallelly")
                    obj.start_cpu_increase_parallel()
                    LOGGER.info("Step 2: Initiated blocking process parallelly")
                    LOGGER.info("Step 3: Calculate CPU utilization")
                    resp = obj.get_cpu_utilization(interval=test_cfg["interval"])
                    if float(resp.decode('utf-8').strip()) >= 100:
                        flag = True
                        break
                    LOGGER.info("Step 3: Calculated CPU utilization")

            if self.start_msg_bus:
                LOGGER.info("Step 4: Checking the generated alert on SSPL")
                alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
                resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 4: Verified the generated alert on the SSPL")

            LOGGER.info("Step 5: Checking CPU usage fault alerts on CSM REST API")
            resp = self.csm_alert_obj.wait_for_alert(self.cfg["csm_alert_gen_delay"],
                                                     start_time, const.AlertType.FAULT, False,
                                                     test_cfg["resource_type"])
            assert resp[0], resp[1]
            LOGGER.info("Step 5: Successfully verified CPU usage fault alert on CSM REST API")

            LOGGER.info("Fetching PID's for yes command")
            resp = obj.get_command_pid("yes")
            process_id = re.findall(r'(\d+) \?', resp.decode('utf-8').strip())
            LOGGER.info("Collected PID's for yes command")
            LOGGER.info("Step 6: Killing the yes process one by one")
            for i in process_id:
                resp = obj.kill_process(i)
            LOGGER.info("Step 6: Processes are killed by one by one")
            LOGGER.info("Step 7: Verify memory utilization is decreasing")
            resp = obj.get_cpu_utilization(interval=test_cfg["interval"])
            assert float(resp.decode('utf-8').strip()) < 100
            LOGGER.info("Step 7: Verified memory utilization is decreasing")
            starttime = time.time()
            LOGGER.info("Resolving CPU fault.")
            resp = self.sw_alert_obj.resolv_cpu_fault(cmn_cfg["faulty_cpu_id"])
            assert resp[0], resp[1]
            LOGGER.info("CPU fault is resolved.")
            self.default_cpu_fault = False
            if self.start_msg_bus:
                LOGGER.info("Step 8: Checking the generated alert on SSPL")
                alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 8: Verified the generated alert on the SSPL")
            LOGGER.info(
                "Step 9: Checking CPU fault resolved alerts on CSM REST API")
            resp = self.csm_alert_obj.wait_for_alert(
                self.cfg["csm_alert_gen_delay"],
                starttime,
                const.AlertType.RESOLVED,
                True,
                test_cfg["resource_type"])
            assert resp[0], resp[1]
            LOGGER.info(
                "Step 9: Successfully verified CPU fault resolved alert on CSM REST API")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-22891")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_22891_load_test(self):
        """
        Load testing with high memory usage, CPU usage,
         disk usage are above threshold and CPU faults.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        cpu_usage = read_properties_file(
            "/etc/sspl.conf")["cpu_usage_threshold"]
        disk_usage = read_properties_file(
            "/etc/sspl.conf")["disk_usage_threshold"]
        start_time = time.time()
        test_cfg = RAS_TEST_CFG["test_22891"]
        cmn_cfg = RAS_TEST_CFG["common_cfg"]
        LOGGER.info("Getting CPU count")
        cpu_cnt = self.sw_alert_obj.get_available_cpus()
        assert len(cpu_cnt) > 0
        LOGGER.info("Available CPU count : %s", cpu_cnt)
        # Increase the CPU usage above threshold value
        flag = False
        while not flag:
            LOGGER.info("Initiating blocking process")
            self.sw_alert_obj.initiate_blocking_process()
            LOGGER.info("Initiated blocking process")
            LOGGER.info("Calculate CPU utilization")
            resp = self.sw_alert_obj.get_cpu_utilization(interval=test_cfg["interval"])
            if float(resp.decode('utf-8').strip()) >= int(cpu_usage):
                flag = True
                break
            LOGGER.info("Calculated CPU utilization")
        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL for CPU usage")
            alert_list = [test_cfg["resource_cpu_usage"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL for CPU usage")

        LOGGER.info("Checking CPU usage fault alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(self.cfg["csm_alert_gen_delay"],
                                                 start_time, const.AlertType.FAULT, False,
                                                 test_cfg["resource_cpu_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Successfully verified CPU usage fault alert on CSM REST API")

        # Increase the memory usage above threshold using stress tool.
        LOGGER.info("Installing stress tool on the system")
        resp = self.sw_alert_obj.install_tool("stress")
        LOGGER.info(resp)
        LOGGER.info("Installed stress tool on the system")
        memory_flag = False
        while not memory_flag:
            LOGGER.info(
                "Increasing the memory utilization in the factor of GB")
            resp = self.sw_alert_obj.increase_memory(
                vm_count=test_cfg["vm_count"],
                memory_size=test_cfg["memory_size"],
                timespan=test_cfg["timespan"])
            LOGGER.info(resp)
            LOGGER.info(
                "Increased the memory utilization in the factor of GB")
            LOGGER.info("Checking memory utilization")
            if float(self.sw_alert_obj.check_memory_utilization().strip()) >= int(cpu_usage):
                memory_flag = True
                break
            LOGGER.info("Verified memory utilization")
        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL for memory usage")
            alert_list = [test_cfg["resource_memory_usage"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL for memory usage")
        LOGGER.info("Checking CPU usage fault alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(self.cfg["csm_alert_gen_delay"],
                                                 start_time, const.AlertType.FAULT, False,
                                                 test_cfg["resource_memory_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Successfully verified CPU usage fault alert on CSM REST API")

        # Verifying CPU faults are reported when CPU is offline
        LOGGER.info("Generate CPU fault.")
        resp = self.sw_alert_obj.gen_cpu_fault(cmn_cfg["faulty_cpu_id"])
        assert resp[0], resp[1]
        LOGGER.info("CPU fault is created successfully.")
        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL for CPU fault")
            alert_list = [test_cfg["resource_cpu_fault"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL for CPU fault")
        LOGGER.info("Checking CPU fault alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(self.cfg["csm_alert_gen_delay"],
                                                 start_time, const.AlertType.FAULT, False,
                                                 test_cfg["resource_cpu_fault"])
        assert resp[0], resp[1]
        LOGGER.info("Successfully verified Memory usage fault alert on CSM REST API")

        # Increasing disk usage above threshold by performing IO operations
        LOGGER.info("Increasing disk usage by performing IO operations")
        obj_name = "{0}{1}".format(
            self.obj_name_prefix, time.perf_counter_ns())
        folder_path_prefix = "{0}{1}".format(
            "test_data", time.perf_counter_ns())
        folder_path = os.path.join(os.getcwd(), folder_path_prefix)
        file_name = "{0}{1}".format("obj_workflow", time.perf_counter_ns())
        file_path = os.path.join(folder_path, file_name)
        if not path_exists(folder_path):
            resp = make_dirs(folder_path)
            LOGGER.info("Created path: %s", resp)
        disk_flag = False
        while not disk_flag:
            bucket_name = "{0}{1}".format(
                self.bkt_name_prefix, time.perf_counter_ns())
            LOGGER.info(
                "Creating a bucket with name %s", bucket_name)
            resp = self.s3_test_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[0]
            LOGGER.info(
                "Created a bucket with name %s", bucket_name)
            create_file(
                file_path,
                S3_OBJ_TST["s3_object"]["mb_count"])
            LOGGER.info(
                "Uploading an object %s to a bucket %s",
                obj_name,
                bucket_name)
            resp = self.s3_test_obj.put_object(
                bucket_name,
                obj_name,
                file_path)
            assert resp[0], resp[1]
            LOGGER.info("Uploaded an object to a bucket")
            LOGGER.info("Calculating disk usage")
            resp = self.sw_alert_obj.node_utils.disk_usage_python_interpreter_cmd("/")
            if float(resp[1].decode().strip()) > int(disk_usage):
                disk_flag = True
                break
            LOGGER.info("Calculated disk usage")
        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL for disk space")
            alert_list = [test_cfg["resource_disk_space"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL for disk space")

        LOGGER.info("Checking Memory usage fault alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(self.cfg["csm_alert_gen_delay"],
                                                 self.starttime, const.AlertType.FAULT, False,
                                                 test_cfg["resource_disk_space"])
        assert resp[0], resp[1]
        LOGGER.info("Successfully verified Memory usage fault alert on CSM REST API")

        # Verifying CPU fault resolved by bringing CPU online
        self.starttime = time.time()
        LOGGER.info("Resolving CPU fault.")
        resp = self.sw_alert_obj.resolv_cpu_fault(cmn_cfg["faulty_cpu_id"])
        assert resp[0], resp[1]
        LOGGER.info("CPU fault is resolved.")
        self.default_cpu_fault = False

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_cpu_fault"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info("Checking CPU fault resolved alerts on CSM REST API")

        resp = self.csm_alert_obj.wait_for_alert(self.cfg["csm_alert_gen_delay"],
                                                 self.starttime, const.AlertType.RESOLVED, True,
                                                 test_cfg["resource_cpu_fault"])
        assert resp[0], resp[1]
        LOGGER.info("Successfully verified CPU fault resolved alert on CSM REST API")

        # Verifying CPU usage fault resolved by killing all yes processes
        self.ras_test_obj.kill_remote_process("yes")
        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL for CPU usage")
            alert_list = [test_cfg["resource_cpu_usage"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL for CPU usage")
        LOGGER.info("Checking CPU fault resolved alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_cpu_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Successfully verified CPU fault resolved alert on CSM REST API")

        # Verifying memory usage fault resolved
        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL for memory usage")
            alert_list = [test_cfg["resource_memory_usage"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL for memory usage")
        LOGGER.info("Checking CPU fault resolved alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_memory_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Successfully verified CPU fault resolved alert on CSM REST API")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)
