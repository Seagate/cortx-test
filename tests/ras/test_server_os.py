#!/usr/bin/python # pylint: disable=C0302
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

"""SSPL test cases: Primary Node."""

import logging
import os
import re
import time

import pytest

from commons import constants as cons
from commons import cortxlogging
from commons.alerts_simulator.generate_alert_lib import AlertType
from commons.alerts_simulator.generate_alert_lib import GenerateAlertLib
from commons.constants import SwAlerts as const
from commons.utils import config_utils
from commons.utils.system_utils import create_file
from commons.utils.system_utils import make_dirs
from commons.utils.system_utils import path_exists
from config import CMN_CFG
from config import RAS_TEST_CFG
from config import RAS_VAL
from config.s3 import S3_CFG
from config.s3 import S3_OBJ_TST
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
        LOGGER.info("\n%s Running setup_class %s", "*" * 50, "*" * 50)
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
        cls.alert_api_obj = GenerateAlertLib()
        cls.default_cpu_usage = False
        cls.default_mem_usage = False
        cls.default_disk_usage = False
        cls.default_cpu_fault = False
        cls.node_reboot = False
        cls.integrity_fault = False
        cls.starttime = time.time()
        cls.sw_alert_objs = []
        for i in range(len(CMN_CFG["nodes"])):
            host = CMN_CFG["nodes"][i]["hostname"]
            uname = CMN_CFG["nodes"][i]["username"]
            passwd = CMN_CFG["nodes"][i]["password"]
            cls.sw_alert_objs.append(SoftwareAlert(host, uname, passwd))
        LOGGER.info("\n%s Completed setup_class %s", "*" * 50, "*" * 50)

    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("\n%s Running setup_method %s", "*" * 50, "*" * 50)
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
        self.node_reboot = False
        LOGGER.info("\n%s Completed setup_method. %s\n", "*" * 50, "*" * 50)

        self.integrity_fault = False
        LOGGER.info("Completed setup_method.")

    # pylint: disable=too-many-statements
    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("\n%s Performing Teardown operation %s", "*" * 50, "*" * 50)

        LOGGER.info("Terminating the process of reading sspl.log")
        if not self.node_reboot:
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
        except Exception as error:
            LOGGER.warning(error)

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
            LOGGER.info("\nStep 4: Resolving CPU fault.")
            resp = self.sw_alert_obj.resolv_cpu_fault(self.default_cpu_fault)
            assert resp[0], resp[1]
        LOGGER.info("\n%s Successfully performed Teardown operation %s\n", "*" * 50, "*" * 50)

        if self.integrity_fault:
            LOGGER.info("Step 4: Resolve RAID integrity fault")
            resp = self.alert_api_obj.generate_alert(AlertType.RAID_INTEGRITY_RESOLVED)
            assert resp[0], resp[1]
            LOGGER.info("Step 4: Resolved RAID integrity fault.")

    @pytest.mark.tags("TEST-21587")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_21587_cpu_usage_threshold(self):
        """Test to validate OS server alert generation and check for fault resolved (CPU Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        LOGGER.info("\nStep 1: Generate CPU usage fault.")
        test_cfg = RAS_TEST_CFG["test_21587"]
        self.default_cpu_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_CPU_USAGE)
        resp = self.sw_alert_obj.gen_cpu_usage_fault_thres(
            test_cfg["delta_cpu_usage"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 1: CPU usage fault is created successfully.\n")

        LOGGER.info("\nStep 2: Keep the CPU usage above threshold for %s seconds.",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 2: CPU usage was above threshold for %s seconds.\n",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL. ")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL.\n")

        LOGGER.info("\nStep 3: Checking CPU usage fault alerts on CSM REST API ")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "\nStep 3: Successfully verified CPU usage fault alert on CSM REST API. \n")

        self.starttime = time.time()
        LOGGER.info("\nStep 4: Resolving CPU usage fault. ")
        LOGGER.info("Updating default CPU usage threshold value")
        resp = self.sw_alert_obj.resolv_cpu_usage_fault_thresh(
            self.default_cpu_usage)
        assert resp[0], resp[1]
        LOGGER.info("\nStep 4: CPU usage fault is resolved.\n")
        self.default_cpu_usage = False

        LOGGER.info(
            "\nStep 5: Keep the CPU usage below threshold for %s seconds",
            self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 5: CPU usage was below threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL. ")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL. \n")

        LOGGER.info(
            "\nStep 6: Checking CPU usage resolved alerts on CSM REST API. ")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "\nStep 6: Successfully verified CPU usage alert on CSM REST API. \n")
        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    @pytest.mark.tags("TEST-21588")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_21588_memory_usage_threshold(self):
        """Test to validate OS server alert generation and check for fault resolved (CPU Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        test_cfg = RAS_TEST_CFG["test_21588"]

        self.default_mem_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_MEM_USAGE)
        LOGGER.info("\nStep 1: Generate memory usage fault.")
        resp = self.sw_alert_obj.gen_mem_usage_fault(
            test_cfg["delta_mem_usage"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 1: Memory usage fault is created successfully.\n")

        LOGGER.info(
            "\nStep 2: Keep the Memory usage above threshold for %s seconds",
            self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 2: Memory usage was above threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL\n")

        LOGGER.info(
            "\nStep 3: Checking Memory usage fault alerts on CSM REST API\n")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "\nStep 3: Successfully verified Memory usage fault alert on CSM REST API\n")

        self.starttime = time.time()
        LOGGER.info("\nStep 4: Resolving Memory usage fault.")
        LOGGER.info("Updating default Memory usage threshold value")
        resp = self.sw_alert_obj.resolv_mem_usage_fault(self.default_mem_usage)
        assert resp[0], resp[1]
        LOGGER.info("\nStep 4: Memory usage fault is resolved.\n")
        self.default_mem_usage = False

        LOGGER.info(
            "\nStep 5: Keep the memory usage below threshold for %s seconds",
            self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 5: Memory usage was below threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL\n")

        LOGGER.info(
            "\nStep 6: Checking Memory usage resolved alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "\nStep 6: Successfully verified Memory usage alert on CSM REST API\n")
        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    @pytest.mark.tags("TEST-21586")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_21586_disk_usage_threshold(self):
        """Test to validate OS server alert generation and check for fault resolved (Disk Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        test_cfg = RAS_TEST_CFG["test_21586"]

        self.default_disk_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_DISK_USAGE)
        LOGGER.info("\nStep 1: Generate disk usage fault.")
        resp = self.sw_alert_obj.gen_disk_usage_fault(
            test_cfg["delta_disk_usage"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 1: Disk usage fault is created successfully.\n")

        LOGGER.info(
            "\nStep 2: Keep the Disk usage above threshold for %s seconds",
            self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 2: Disk usage was above threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL\n")

        LOGGER.info(
            "\nStep 3: Checking Disk usage fault alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 3: Successfully verified Disk usage fault alert on CSM REST API\n")

        self.starttime = time.time()
        LOGGER.info("\nStep 4: Resolving Disk usage fault.")
        LOGGER.info("Updating default Disk usage threshold value")
        resp = self.sw_alert_obj.resolv_disk_usage_fault(
            self.default_disk_usage)
        assert resp[0], resp[1]
        LOGGER.info("\nStep 4: Disk usage fault is resolved.\n")
        self.default_mem_usage = False

        LOGGER.info("\nStep 5: Keep the Disk usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 5: Disk usage was below threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL\n")

        LOGGER.info("\nStep 6: Checking Disk usage resolved alerts on CSM REST API")

        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]

        LOGGER.info(
            "\nStep 6: Successfully verified Disk usage alert on CSM REST API\n")
        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    @pytest.mark.skip("CPU faults brings down motr - EOS-21174")
    @pytest.mark.tags("TEST-23045")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_23045_cpu_fault(self):
        """Test CPU fault and fault resolved alert.

        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        LOGGER.info("\nStep 1: Generate CPU fault.")
        test_cfg = RAS_TEST_CFG["test_23045"]
        self.default_cpu_fault = test_cfg["faulty_cpu_id"]
        resp = self.sw_alert_obj.gen_cpu_fault(test_cfg["faulty_cpu_id"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 1: CPU fault is created successfully.\n")

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL\n")

        LOGGER.info("\nStep 3: Checking CPU fault alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "\nStep 3: Successfully verified Memory usage fault alert on CSM REST API\n")

        self.starttime = time.time()
        LOGGER.info("\nStep 4: Resolving CPU fault.")
        resp = self.sw_alert_obj.resolv_cpu_fault(test_cfg["faulty_cpu_id"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 4: CPU fault is resolved.\n")
        self.default_cpu_fault = False

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL\n")

        LOGGER.info(
            "\nStep 6: Checking CPU fault resolved alerts on CSM REST API\n")

        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            self.starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]

        LOGGER.info(
            "\nStep 6: Successfully verified CPU fault resolved alert on CSM REST API\n")
        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    # pylint: disable=too-many-statements
    @pytest.mark.tags("TEST-22786")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_22786_memory_usage_stress(self):
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
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        start_time = time.time()
        mem_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_MEM_USAGE)
        test_cfg = RAS_TEST_CFG["test_22786"]
        for obj in self.sw_alert_objs:
            LOGGER.info("\nStep 1: Checking available memory usage and convert it to GB")
            resp = obj.get_available_memory_usage()
            LOGGER.info("Available memory : %s", resp)
            LOGGER.info("\nStep 1: Calculated available memory usage in GB\n")

            LOGGER.info("\nStep 2: Installing stress tool on the system")
            resp = obj.node_utils.execute_cmd(cmd="yum install stress")
            LOGGER.info(resp)
            LOGGER.info("\nStep 2: Installed stress tool on the system\n")

            flag = False
            while not flag:
                LOGGER.info(
                    "\nStep 3: Increasing the memory utilization in the factor of GB")
                resp = obj.increase_memory(
                    vm_count=test_cfg["vm_count"],
                    memory_size=test_cfg["memory_size"],
                    timespan=test_cfg["timespan"])
                LOGGER.info(resp)
                LOGGER.info(
                    "\nStep 3: Increased the memory utilization in the factor of GB\n")

                LOGGER.info("\nStep 4: Verifying memory utilization on %s node", obj.host)
                if float(obj.check_memory_utilization().strip()) >= float(mem_usage):
                    flag = True
                    break
                LOGGER.info("\nStep 4: Verified memory utilization on %s node\n", obj.host)

        LOGGER.info("\nStep 2: Keep the Memory usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 2: Memory usage was above threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nStep 5: Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nStep 5: Verified the generated alert on the SSPL\n")

        LOGGER.info("\nStep 6: Checking memory usage alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            start_time,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "\nStep 6: Successfully verified Memory usage fault alert on CSM REST API\n")
        time_sec = config_utils.convert_to_seconds(test_cfg["timespan"])

        LOGGER.info("\nStep 7: Keep the Memory usage above threshold for %s seconds", time_sec)
        time.sleep(time_sec)

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL\n")

        LOGGER.info(
            "\nStep 8: Checking Memory usage resolved alerts on CSM REST API")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            start_time,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]

        LOGGER.info(
            "\nStep 8: Successfully verified Memory usage resolved alert on CSM REST API\n")
        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    # pylint: disable=too-many-statements
    @pytest.mark.tags("TEST-22787")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_22787_cpu_usage(self):
        """
        TEST cpu usage fault and fault resolved alert with gradual
        increase in CPU usage on each node of the cluster sequentially.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        start_time = time.time()
        test_cfg = RAS_TEST_CFG["test_22787"]
        for obj in self.sw_alert_objs:
            LOGGER.info("[STARTED] : Testing for node : %s", obj.host)
            LOGGER.info("\nStep 1: Getting CPU count")
            cpu_cnt = obj.get_available_cpus()
            LOGGER.info("Available CPU count : %s", cpu_cnt)
            LOGGER.info("\nStep 1: Calculated available CPU count\n")
            LOGGER.info("Initiating blocking process on each cpu")
            for i in range(len(cpu_cnt)):
                flag = False
                while not flag:
                    LOGGER.info("\nStep 2.%s: Initiating blocking process", i)
                    obj.initiate_blocking_process()
                    LOGGER.info("\nStep 2.%s: Initiated blocking process\n", i)
                    LOGGER.info("\nStep 3.%s: Calculate CPU utilization", i)
                    resp = obj.get_cpu_utilization(test_cfg["interval"])
                    if float(resp.decode('utf-8').strip()) >= 100:
                        flag = True
                        break
                    LOGGER.info("\nStep 3.%s: Calculated CPU utilization\n", i)
            if self.start_msg_bus:
                LOGGER.info("\nStep 4: Checking the generated alert on SSPL")
                alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
                resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("\nStep 4: Verified the generated alert on the SSPL\n")

            LOGGER.info("\nStep 5: Checking CPU usage fault alerts on CSM REST API")
            resp = self.csm_alert_obj.wait_for_alert(self.cfg["csm_alert_gen_delay"],
                                                     start_time, const.AlertType.FAULT, False,
                                                     test_cfg["resource_type"])
            assert resp[0], resp[1]
            LOGGER.info("\nStep 5: Successfully verified CPU usage fault alert on CSM REST API\n")

            LOGGER.info("Fetching PID's for yes command")
            resp = obj.get_command_pid("yes")
            process_id = re.findall(r'(\d+) \?', resp.decode('utf-8').strip())
            LOGGER.info("Collected PID's for yes command")
            LOGGER.info("\nStep 6: Killing the process one by one")
            for i in process_id:
                resp = obj.kill_process(i)
            LOGGER.info("\nStep 6: Processes are killed by one by one\n")
            LOGGER.info("\nStep 7: Verify CPU utilization is decreasing")
            resp = obj.get_cpu_utilization(interval=test_cfg["interval"])
            assert float(resp.decode('utf-8').strip()) < 100
            LOGGER.info("\nStep 7: Verified CPU utilization is decreasing\n")
            starttime = time.time()
            if self.start_msg_bus:
                LOGGER.info("\nStep 9: Checking the generated alert on SSPL")
                alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("\nStep 9: Verified the generated alert on the SSPL\n")

            LOGGER.info(
                "\nStep 10: Checking CPU usage fault resolved alerts on CSM REST API")
            resp = self.csm_alert_obj.wait_for_alert(
                self.cfg["csm_alert_gen_delay"],
                starttime,
                const.AlertType.RESOLVED,
                True,
                test_cfg["resource_type"])
            assert resp[0], resp[1]

            LOGGER.info(
                "\nStep 10: Successfully verified CPU fault resolved alert on CSM REST API\n")
            LOGGER.info("[COMPLETED] : Testing for node : %s", obj.host)
        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    # pylint: disable=too-many-statements
    @pytest.mark.tags("TEST-22844")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_22844_cpu_usage_parallel(self):
        """
        TEST cpu usage fault and fault resolved alert with gradual
        increase in CPU usage on each node of the cluster parallelly.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        start_time = time.time()
        test_cfg = RAS_TEST_CFG["test_22787"]
        for obj in self.sw_alert_objs:
            LOGGER.info("[STARTED] : Testing for node : %s", obj.host)
            LOGGER.info("\nStep 1: Getting CPU count")
            cpu_cnt = obj.get_available_cpus()
            LOGGER.info("Available CPU count : %s", cpu_cnt)
            LOGGER.info("\nStep 1: Calculated available CPU count")
            LOGGER.info("Initiating blocking process on each cpu")
            for i in range(len(cpu_cnt)):
                flag = False
                while not flag:
                    LOGGER.info("\nStep 2.%s: Initiating blocking process parallelly", i)
                    obj.start_cpu_increase_parallel()
                    LOGGER.info("\nStep 2.%s: Initiated blocking process parallelly", i)
                    LOGGER.info("\nStep 3.%s: Calculate CPU utilization", i)
                    resp = obj.get_cpu_utilization(interval=test_cfg["interval"])
                    if float(resp.decode('utf-8').strip()) >= 100:
                        flag = True
                        break
                    LOGGER.info("\nStep 3.%s: Calculated CPU utilization", i)

            if self.start_msg_bus:
                LOGGER.info("\nStep 4: Checking the generated alert on SSPL")
                alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
                resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("\nStep 4: Verified the generated alert on the SSPL")

            LOGGER.info("\nStep 5: Checking CPU usage fault alerts on CSM REST API")
            resp = self.csm_alert_obj.wait_for_alert(self.cfg["csm_alert_gen_delay"],
                                                     start_time, const.AlertType.FAULT, False,
                                                     test_cfg["resource_type"])
            assert resp[0], resp[1]
            LOGGER.info("\nStep 5: Successfully verified CPU usage fault alert on CSM REST API")

            starttime = time.time()
            LOGGER.info("Fetching PID's for yes command")
            resp = obj.get_command_pid("yes")
            process_id = re.findall(r'(\d+) \?', resp.decode('utf-8').strip())
            LOGGER.info("Collected PID's for yes command")
            LOGGER.info("\nStep 6: Killing the yes process one by one")
            for i in process_id:
                resp = obj.kill_process(i)
            LOGGER.info("\nStep 6: Processes are killed by one by one")
            LOGGER.info("\nStep 7: Verify memory utilization is decreasing")
            resp = obj.get_cpu_utilization(interval=test_cfg["interval"])
            assert float(resp.decode('utf-8').strip()) < 100
            LOGGER.info("\nStep 7: Verified memory utilization is decreasing")

            if self.start_msg_bus:
                LOGGER.info("\nStep 8: Checking the generated alert on SSPL")
                alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("\nStep 8: Verified the generated alert on the SSPL")
            LOGGER.info(
                "\nStep 9: Checking CPU fault resolved alerts on CSM REST API")
            resp = self.csm_alert_obj.wait_for_alert(
                self.cfg["csm_alert_gen_delay"],
                starttime,
                const.AlertType.RESOLVED,
                True,
                test_cfg["resource_type"])
            assert resp[0], resp[1]
            LOGGER.info(
                "\nStep 9: Successfully verified CPU fault resolved alert on CSM REST API")
            LOGGER.info("[COMPLETED] : Testing for node : %s", obj.host)
        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    @pytest.mark.tags("TEST-22716")
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_22716_disk_usage_thres_with_persistence_cache(self):
        """Test to validate OS server alert generation and check for fault resolved (Disk Usage)
           with persistence cache (service disable/enable)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        test_cfg = RAS_TEST_CFG["test_21586"]
        LOGGER.info("\nStep 1: Generate disk usage fault.")
        starttime = time.time()
        self.default_disk_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_DISK_USAGE)
        if self.default_disk_usage == 'False':
            self.default_disk_usage = 80
        resp = self.sw_alert_obj.gen_disk_usage_fault_with_persistence_cache(
            test_cfg["delta_disk_usage"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 1: Disk usage fault is created successfully.\n")

        LOGGER.info("\nStep 2: Keep the Disk usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 2: Disk usage was above threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL")

        LOGGER.info("\nStep 3: Checking if disk usage fault is present in new alerts")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 3: Successfully verified Disk usage fault with persistent cache\n")

        starttime = time.time()
        LOGGER.info("\nStep 4: Resolving Disk usage fault.")
        LOGGER.info("Updating default Disk usage threshold value")
        resp = self.sw_alert_obj.resolv_disk_usage_fault_with_persistence_cache(
            self.default_disk_usage)
        assert resp[0], resp[1]
        LOGGER.info("\nStep 4: Disk usage fault is resolved.\n")
        self.default_disk_usage = False

        LOGGER.info("\nStep 5: Keep the Disk usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 5: Disk usage was below threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL")

        LOGGER.info("\nStep 6: Checking Disk usage resolved alerts on CSM GUI")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 6: Successfully verified Disk usage resolved with persistent cache on"
                    " CSM\n")
        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    @pytest.mark.tags("TEST-22717")
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_22717_cpu_usage_thresh_with_persistence_cache(self):
        """Test to validate OS server alert generation and check for fault resolved (CPU Usage)
           with persistence cache (service disable/enable)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        LOGGER.info("\nStep 1: Generate CPU usage fault.")
        test_cfg = RAS_TEST_CFG["test_21587"]
        starttime = time.time()
        self.default_cpu_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_CPU_USAGE)
        resp = self.sw_alert_obj.gen_cpu_usage_fault_with_persistence_cache(
            test_cfg["delta_cpu_usage"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 1: CPU usage fault is created successfully.\n")

        LOGGER.info("\nStep 2: Keep the CPU usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 2: CPU usage was above threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])
        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL")

        LOGGER.info("\nStep 3: Checking if CPU usage alert is present in new alerts")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 3: Verified CPU usage alert is present in new alerts\n")

        starttime = time.time()
        LOGGER.info("\nStep 4: Resolving CPU usage fault.")
        LOGGER.info("Updating default CPU usage threshold value")
        resp = self.sw_alert_obj.resolv_cpu_usage_fault_with_persistence_cache(
            self.default_cpu_usage)
        assert resp[0], resp[1]
        LOGGER.info("\nStep 4: CPU usage fault is resolved.\n")
        self.default_cpu_usage = False

        LOGGER.info("\nStep 5: Keep the CPU usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 5: CPU usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL")

        LOGGER.info("\nStep 6: Checking if CPU usage resolved is present in new alerts")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 6: Verified CPU usage resolved is present in new alerts\n")

        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    @pytest.mark.tags("TEST-22720")
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_22720_memory_usage_thresh_with_persistence_cache(self):
        """Test to validate OS server alert generation and check for fault resolved (Memory Usage)
           with persistence cache (service disable/enable)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        LOGGER.info("\nStep 1: Generate memory usage fault.")
        test_cfg = RAS_TEST_CFG["test_21588"]
        starttime = time.time()
        self.default_mem_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_MEM_USAGE)
        resp = self.sw_alert_obj.gen_mem_usage_fault_with_persistence_cache(
            test_cfg["delta_mem_usage"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 1: Memory usage fault is created successfully.\n")

        LOGGER.info("\nStep 2: Keep the Memory usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 2: Memory usage was above threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.FAULT]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL")

        LOGGER.info("\nStep 3: Checking if memory usage alert is present in new alerts")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 3: Verified memory usage alert is present in new alerts\n")

        starttime = time.time()
        LOGGER.info("\nStep 4: Resolving Memory usage fault.")
        LOGGER.info("Updating default Memory usage threshold value")
        resp = self.sw_alert_obj.resolv_mem_usage_fault_with_persistence_cache(
            self.default_mem_usage)
        assert resp[0], resp[1]
        LOGGER.info("\nStep 4: Memory usage fault is resolved.\n")
        self.default_mem_usage = False

        LOGGER.info("\nStep 5: Keep the memory usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 5: Memory usage was below threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        if self.start_msg_bus:
            LOGGER.info("\nChecking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(
                string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("\nVerified the generated alert on the SSPL")

        LOGGER.info("\nStep 6: Checking if memory usage resolved is present in new alerts")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 6: Verified memory usage resolved is present in new alerts\n")

        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    @pytest.mark.tags("TEST-22718")
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_22718_cpu_usage_threshold_node_reboot(self):
        """System Test to validate OS server alert generation and check for fault resolved CPU Usage
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        LOGGER.info("\nStep 1: Generate CPU usage fault.")
        starttime = time.time()
        test_cfg = RAS_TEST_CFG["test_21587"]
        self.default_cpu_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_CPU_USAGE)
        resp = self.sw_alert_obj.gen_cpu_usage_fault_thres_restart_node(test_cfg["delta_cpu_usage"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 1: CPU usage fault is created successfully.\n")
        self.node_reboot = True
        LOGGER.info("\nStep 2: Keep the CPU usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 2: CPU usage was above threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("\nStep 3: Checking if cpu fault is present in new alerts")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 3: Verified cpu fault is present in new alerts\n")

        starttime = time.time()
        LOGGER.info("\nStep 4: Resolving CPU usage fault.")
        LOGGER.info("Updating default CPU usage threshold value")
        resp = self.sw_alert_obj.resolv_cpu_usage_fault_thresh_restart_node(self.default_cpu_usage)
        assert resp[0], resp[1]
        LOGGER.info("\nStep 4:CPU usage fault is resolved.")
        self.default_mem_usage = False

        LOGGER.info("\nStep 5: Keep the cpu usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 5: cpu usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("\nStep 6: Checking if cpu fault resolved is present in new alerts")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 6: Verified cpu fault resolved is present in new alerts\n")

        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    @pytest.mark.tags("TEST-22719")
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_22719_memory_usage_threshold_node_reboot(self):
        """System Test to validate OS server alert generation and check for fault resolved
        (Memory Usage) with persistence cache (node reboot)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("\n%s Test started -  %s %s\n", "#" * 50, test_case_name, "#" * 50)
        LOGGER.info("\nStep 1: Generate memory usage fault.")
        starttime = time.time()
        test_cfg = RAS_TEST_CFG["test_21588"]
        self.default_mem_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_MEM_USAGE)
        resp = self.sw_alert_obj.gen_mem_usage_fault_reboot_node(test_cfg["delta_mem_usage"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 1: Memory usage fault is created successfully.\n")
        self.node_reboot = True
        LOGGER.info("\nStep 2: Keep the Memory usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 2: Memory usage was above threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("\nStep 3: Checking if memory usage alert is present in new alerts")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            starttime,
            const.AlertType.FAULT,
            False,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 3: Verified memory usage alert is present in new alerts\n")

        starttime = time.time()
        LOGGER.info("\nStep 4: Resolving Memory usage fault.")
        LOGGER.info("Updating default Memory usage threshold value")
        resp = self.sw_alert_obj.resolv_mem_usage_fault_reboot_node(self.default_mem_usage)
        assert resp[0], resp[1]
        LOGGER.info("\nStep 4: Memory usage fault is resolved.\n")
        self.default_mem_usage = False

        LOGGER.info("\nStep 5: Keep the memory usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("\nStep 5: Memory usage was below threshold for %s seconds\n",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("\nStep 6: Checking if memory usage resolved alert is present in new alerts")
        resp = self.csm_alert_obj.wait_for_alert(
            self.cfg["csm_alert_gen_delay"],
            starttime,
            const.AlertType.RESOLVED,
            True,
            test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("\nStep 6: Verified memory usage resolved alert is present in new alerts\n")

        LOGGER.info("\n%s Test completed -  %s %s\n", "#" * 50, test_case_name, "#" * 50)

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-branches
    @pytest.mark.skip("CPU faults brings down motr - EOS-21174")
    @pytest.mark.tags("TEST-22891")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_22891_load_test(self):
        """
        Load testing with high memory usage, CPU usage,
         disk usage are above threshold and CPU faults.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        cpu_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_CPU_USAGE)
        disk_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_DISK_USAGE)
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
        obj_name = f"{self.obj_name_prefix}{time.perf_counter_ns()}"
        folder_path_prefix = f"test_data{time.perf_counter_ns()}"
        folder_path = os.path.join(os.getcwd(), folder_path_prefix)
        file_name = f"obj_workflow{time.perf_counter_ns()}"
        file_path = os.path.join(folder_path, file_name)
        if not path_exists(folder_path):
            resp = make_dirs(folder_path)
            LOGGER.info("Created path: %s", resp)
        disk_flag = False
        while not disk_flag:
            bucket_name = f"{self.bkt_name_prefix}{time.perf_counter_ns()}"
            LOGGER.info("Creating a bucket with name %s", bucket_name)
            resp = self.s3_test_obj.create_bucket(bucket_name)
            assert resp[0], resp[1]
            assert resp[1] == bucket_name, resp[0]
            LOGGER.info("Created a bucket with name %s", bucket_name)
            create_file(file_path, S3_OBJ_TST["s3_object"]["mb_count"])
            LOGGER.info("Uploading an object %s to a bucket %s", obj_name, bucket_name)
            resp = self.s3_test_obj.put_object(bucket_name, obj_name, file_path)
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

    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.tags("TEST-22781")
    @pytest.mark.skip("RAID integrity not reported - EOS-23324")
    def test_22781_raid_integrity(self):
        """
        Generate and resolve RAID integrity fault.
        """
        LOGGER.info(
            "STARTED: TEST-22781 RAID integrity")
        test_cfg = RAS_TEST_CFG["test_22781"]

        LOGGER.info(
            "Step 1: Create RAID Integrity fault")
        resp = self.alert_api_obj.generate_alert(AlertType.RAID_INTEGRITY_FAULT,
                                                 host_details={"host": self.host,
                                                               "host_user": self.uname,
                                                               "host_password": self.passwd},
                                                 input_parameters={'count': 5, 'timeout': 60})
        assert resp[0], resp[1]
        self.integrity_fault = True
        LOGGER.info("Step 1: RAID integrity fault created.")

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info("Step 3: Checking CSM REST API for RAID integrity alert")
        resp = self.csm_alert_obj.wait_for_alert(self.cfg["csm_alert_gen_delay"], self.starttime,
                                                 const.AlertType.RESOLVED, True,
                                                 test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info(
            "Step 3: Successfully verified RAID integrity alert using CSM REST API")

        LOGGER.info("Step 4: Resolve RAID integrity fault")
        resp = self.alert_api_obj.generate_alert(AlertType.RAID_INTEGRITY_RESOLVED)
        assert resp[0], resp[1]
        self.integrity_fault = False
        LOGGER.info("Step 4: Resolved RAID integrity fault.")

        if self.start_msg_bus:
            LOGGER.info("Checking the generated alert on SSPL")
            alert_list = [test_cfg["resource_type"], const.AlertType.RESOLVED]
            resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
            assert resp[0], resp[1]
            LOGGER.info("Verified the generated alert on the SSPL")

        LOGGER.info("Step 6: Checking CSM REST API for RAID integrity resolved alert")
        resp = self.csm_alert_obj.wait_for_alert(self.cfg["csm_alert_gen_delay"], self.starttime,
                                                 const.AlertType.RESOLVED, True,
                                                 test_cfg["resource_type"])
        assert resp[0], resp[1]
        LOGGER.info("Step 6: Successfully verified RAID integrity resolved alert using CSM"
                    " REST API")
