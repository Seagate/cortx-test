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

"""CSM GUI: Server OS Alert Tests"""

import os
import time
import logging
import pytest
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG
from commons import constants as cons
from commons import cortxlogging
from commons.utils.assert_utils import assert_equals
from commons import Globals
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.ras.sw_alerts import SoftwareAlert
from robot_gui.utils.call_robot_test import trigger_robot

LOGGER = logging.getLogger(__name__)

class TestServerOSAlerts:
    """3rd party service monitoring test suite."""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("Running setup_class...")
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.cfg = RAS_VAL["ras_sspl_alert"]
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.csm_url = "https://" + cls.mgmt_vip + "/#"
        cls.cwd = os.getcwd()
        cls.robot_gui_path = os.path.join(cls.cwd + '/robot_gui/')
        cls.robot_test_path = cls.robot_gui_path + 'testsuites/gui/.'
        cls.browser_type = 'chrome'
        cls.csm_user = CMN_CFG["csm"]["csm_admin_user"]["username"]
        cls.csm_passwd = CMN_CFG["csm"]["csm_admin_user"]["password"]
        cls.sw_alert_obj = SoftwareAlert(cls.host, cls.uname, cls.passwd)
        cls.ras_test_obj = RASTestLib(host=cls.host, username=cls.uname, password=cls.passwd)
        cls.csm_alert_obj = SystemAlerts(cls.sw_alert_obj.node_utils)
        cls.default_cpu_usage = False
        cls.default_mem_usage = False
        cls.default_disk_usage = False
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

        self.default_cpu_usage = False
        self.default_mem_usage = False
        self.default_disk_usage = False
        LOGGER.info("Completed setup_method.")

    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("Performing Teardown operation")

        if self.default_cpu_usage:
            LOGGER.info("Updating default CPU usage threshold value")
            resp = self.sw_alert_obj.resolv_cpu_usage_fault_thresh(self.default_cpu_usage)
            assert resp[0], resp[1]

        if self.default_mem_usage:
            LOGGER.info("Updating default Memory usage threshold value")
            resp = self.sw_alert_obj.resolv_mem_usage_fault(self.default_mem_usage)
            assert resp[0], resp[1]

        if self.default_disk_usage:
            LOGGER.info("Updating default Disk usage threshold value")
            resp = self.sw_alert_obj.resolv_disk_usage_fault(self.default_disk_usage)
            assert resp[0], resp[1]


    @pytest.mark.tags("TEST-25090")
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_25090_cpu_usage_threshold(self):
        """CSM-GUI: System Test to validate OS server alert generation and check for fault resolved (CPU Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21587"]

        LOGGER.info("Step 1: Checking if cpu fault is not already present in new alerts")
        alert_description = 'CPU usage increased to'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + '/log/latest/TEST-25090_Gui_Logs'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in new alert')

        LOGGER.info("Acknowledge alert from active alert table if any")
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: error is acknowledging active alert')

        self.default_cpu_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_CPU_USAGE)
        LOGGER.info("Step 2: Generate CPU usage fault.")
        resp = self.sw_alert_obj.gen_cpu_usage_fault_thres(test_cfg["delta_cpu_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: CPU usage fault is created successfully.")

        LOGGER.info("Step 4: Keep the CPU usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: CPU usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("Step 6: Checking if cpu fault is present in new alerts")
        time.sleep(10)
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in new alert')

        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in active alert')

        LOGGER.info("Step 7: Resolving CPU usage fault.")
        LOGGER.info("Updating default CPU usage threshold value")
        resp = self.sw_alert_obj.resolv_cpu_usage_fault_thresh(self.default_cpu_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 8: CPU usage fault is resolved.")
        self.default_cpu_usage = False

        LOGGER.info("Step 9: Keep the CPU usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 10: CPU usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        time.sleep(10)
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in active alert')

        LOGGER.info("Step 11: Successfully verified CPU usage alert on CSM GUI")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-25091")
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_25091_memory_usage_threshold(self):
        """CSM-GUI: System Test to validate OS server alert generation and check for fault resolved (Memory Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21588"]

        LOGGER.info("Step 1: Checking if memory usage fault is not already present in new alerts")
        alert_description = 'Host memory usage increased to'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + '/log/latest/TEST-25091_Gui_Logs'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in new alert')

        LOGGER.info("Acknowledge alert from active alert table if any")
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: error is acknowledging active alert')

        self.default_mem_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_MEM_USAGE)
        LOGGER.info("Step 2: Generate memory usage fault.")
        resp = self.sw_alert_obj.gen_mem_usage_fault(test_cfg["delta_mem_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Memory usage fault is created successfully.")

        LOGGER.info("Step 4: Keep the Memory usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: Memory usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("Step 6: Checking if memory fault is present in new alerts")
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        time.sleep(10)
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in new alert')

        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in active alert')

        LOGGER.info("Step 7: Successfully verified Memory usage fault alert on CSM GUI")

        LOGGER.info("Step 8: Resolving Memory usage fault.")
        LOGGER.info("Updating default Memory usage threshold value")
        resp = self.sw_alert_obj.resolv_mem_usage_fault(self.default_mem_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 9: Memory usage fault is resolved.")
        self.default_mem_usage = False

        LOGGER.info("Step 10: Keep the memory usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 11: Memory usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("Step 12: Checking Memory usage resolved alerts on CSM GUI")
        time.sleep(10)
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in active alert')

        LOGGER.info("Step 13: Successfully verified Memory usage alert on CSM GUI")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-25092")
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_25092_disk_usage_threshold(self):
        """Test to validate OS server alert generation and check for fault resolved (Disk Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21586"]

        LOGGER.info("Step 1: Checking if disk usage fault is not already present in new alerts")
        alert_description = 'Disk usage increased to'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + '/log/latest/TEST-25092_Gui_Logs'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in new alert')

        LOGGER.info("Acknowledge alert from active alert table if any")
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: error is acknowledging active alert')

        self.default_disk_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_DISK_USAGE)
        if self.default_disk_usage == 'False':
            self.default_disk_usage = 80
        LOGGER.info("Step 2: Generate disk usage fault.")
        resp = self.sw_alert_obj.gen_disk_usage_fault(test_cfg["delta_disk_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Disk usage fault is created successfully.")

        LOGGER.info("Step 4: Keep the Disk usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: Disk usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("Step 6: Checking if disk fault is present in new alerts")
        time.sleep(10)
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in new alert')

        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in active alert')

        LOGGER.info("Step 7: Successfully verified Disk usage fault alert on CSM GUI")

        LOGGER.info("Step 8: Resolving Disk usage fault.")
        LOGGER.info("Updating default Disk usage threshold value")
        resp = self.sw_alert_obj.resolv_disk_usage_fault(self.default_disk_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 9: Disk usage fault is resolved.")
        self.default_disk_usage = False

        LOGGER.info("Step 10: Keep the Disk usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 11: Disk usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("Step 12: Checking Disk usage resolved alerts on CSM GUI")
        time.sleep(10)
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in active alert')

        LOGGER.info("Step 13: Successfully verified Memory usage alert on CSM REST API")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-25093")
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_25093_disk_usage_thres_with_persistence_cache(self):
        """CSM-GUI: Test to validate OS server alert generation and check for fault resolved (Disk Usage)
           with persistence cache (service disable/enable)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21586"]

        LOGGER.info("Step 1: Checking if disk usage fault is not already present in new alerts")
        alert_description = 'Disk usage increased to'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + '/log/latest/TEST-25093_Gui_Logs'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in new alert')

        LOGGER.info("Acknowledge alert from active alert table if any")
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: error is acknowledging active alert')

        self.default_disk_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_DISK_USAGE)
        if self.default_disk_usage == 'False':
            self.default_disk_usage = 80
        LOGGER.info("Step 2: Generate disk usage fault.")
        resp = self.sw_alert_obj.gen_disk_usage_fault_with_persistence_cache(test_cfg["delta_disk_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Disk usage fault is created successfully.")

        LOGGER.info("Step 4: Keep the Disk usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: Disk usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("Step 6: Checking if disk fault is present in new alerts")
        time.sleep(10)
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in new alert')

        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in active alert')

        LOGGER.info("Step 7: Successfully verified Disk usage fault alert with persistent cache on CSM GUI")

        LOGGER.info("Step 8: Resolving Disk usage fault.")
        LOGGER.info("Updating default Disk usage threshold value")
        resp = self.sw_alert_obj.resolv_disk_usage_fault_with_persistence_cache(self.default_disk_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 9: Disk usage fault is resolved.")
        self.default_disk_usage = False

        LOGGER.info("Step 10: Keep the Disk usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 11: Disk usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("Step 12: Checking Disk usage resolved alerts on CSM GUI")
        time.sleep(10)
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in active alert')

        LOGGER.info("Step 13: Successfully verified Disk usage alert with persistent cache on CSM GUI")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-25094")
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_25094_cpu_usage_thresh_with_persistence_cache(self):
        """Test to validate OS server alert generation and check for fault resolved (CPU Usage)
           with persistence cache (service disable/enable)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21587"]

        LOGGER.info("Step 1: Checking if cpu fault is not already present in new alerts")
        alert_description = 'CPU usage increased to'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + '/log/latest/TEST-25094_Gui_Logs'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in new alert')

        LOGGER.info("Acknowledge alert from active alert table if any")
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: error is acknowledging active alert')

        self.default_cpu_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_CPU_USAGE)
        LOGGER.info("Step 2: Generate CPU usage fault.")
        resp = self.sw_alert_obj.gen_cpu_usage_fault_with_persistence_cache(test_cfg["delta_cpu_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: CPU usage fault is created successfully.")

        LOGGER.info("Step 4: Keep the CPU usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: CPU usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("Step 6: Checking if cpu fault is present in new alerts")
        time.sleep(10)
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in new alert')

        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in active alert')

        LOGGER.info("Step 7: Resolving CPU usage fault.")
        LOGGER.info("Updating default CPU usage threshold value")
        resp = self.sw_alert_obj.resolv_cpu_usage_fault_with_persistence_cache(self.default_cpu_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 8: CPU usage fault is resolved.")
        self.default_cpu_usage = False

        LOGGER.info("Step 9: Keep the CPU usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 10: CPU usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        time.sleep(10)
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in active alert')

        LOGGER.info("Step 11: Successfully verified CPU usage alert with persistence cache on CSM GUI")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-25095")
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_25095_memory_usage_thresh_with_persistence_cache(self):
        """Test to validate OS server alert generation and check for fault resolved (Memory Usage)
           with persistence cache (service disable/enable)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21588"]

        LOGGER.info("Step 1: Checking if memory usage fault is not already present in new alerts")
        alert_description = 'Host memory usage increased to'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + '/log/latest/TEST-25095_Gui_Logs'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in new alert')

        LOGGER.info("Acknowledge alert from active alert table if any")
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: error is acknowledging active alert')

        self.default_mem_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_MEM_USAGE)
        LOGGER.info("Step 2: Generate memory usage fault.")
        resp = self.sw_alert_obj.gen_mem_usage_fault_with_persistence_cache(test_cfg["delta_mem_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Memory usage fault is created successfully.")

        LOGGER.info("Step 4: Keep the Memory usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: Memory usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("Step 6: Checking if memory fault is present in new alerts")
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        time.sleep(10)
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in new alert')

        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in active alert')

        LOGGER.info("Step 7: Successfully verified Memory usage fault alert on CSM GUI")

        LOGGER.info("Step 8: Resolving Memory usage fault.")
        LOGGER.info("Updating default Memory usage threshold value")
        resp = self.sw_alert_obj.resolv_mem_usage_fault_with_persistence_cache(self.default_mem_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 9: Memory usage fault is resolved.")
        self.default_mem_usage = False

        LOGGER.info("Step 10: Keep the memory usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 11: Memory usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])

        LOGGER.info("Step 12: Checking Memory usage resolved alerts with persistent cache on CSM GUI")
        time.sleep(10)
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in active alert')

        LOGGER.info("Step 13: Successfully verified Memory usage alert with persistent cache on CSM GUI")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-25106")
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_25106_cpu_usage_threshold(self):
        """CSM-GUI: System Test to validate OS server alert generation and check for fault resolved (CPU Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21587"]
        LOGGER.info("Step 1: Checking if cpu fault is not already present in new alerts")
        alert_description = 'CPU usage increased to'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + '/log/latest/TEST-22718_Gui_Logs'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in new alert')
        LOGGER.info("Acknowledge alert from active alert table if any")
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: error is acknowledging active alert')
        self.default_cpu_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_CPU_USAGE)
        LOGGER.info("Step 2: Generate CPU usage fault.")
        resp = self.sw_alert_obj.gen_cpu_usage_fault_thres_restart_node(test_cfg["delta_cpu_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: CPU usage fault is created successfully.")
        LOGGER.info("Step 4: Keep the CPU usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: CPU usage was above threshold for %s seconds",
                 self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 6: Checking if cpu fault is present in new alerts")
        time.sleep(10)
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in new alert')
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in active alert')
        LOGGER.info("Step 7: Resolving CPU usage fault.")
        LOGGER.info("Updating default CPU usage threshold value")
        resp = self.sw_alert_obj.resolv_cpu_usage_fault_thresh_restart_node(self.default_cpu_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 8:CPU usage fault is resolved.")
        self.default_mem_usage = False
        LOGGER.info("Step 9: Keep the cpu usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 10: cpu usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        time.sleep(10)
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in active alert')
        LOGGER.info("Step 11: Successfully verified CPU usage alert on CSM GUI")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-25107")
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_25107_memory_usage_threshold(self):
        """CSM-GUI: System Test to validate OS server alert generation and check for fault resolved (Memory Usage)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21588"]
        LOGGER.info("Step 1: Checking if memory usage fault is not already present in new alerts")
        alert_description = 'Host memory usage increased to'
        gui_dict = dict()
        gui_dict['log_path'] = Globals.CSM_LOGS + '/log/latest/TEST-22719_Gui_Logs'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in new alert')
        LOGGER.info("Acknowledge alert from active alert table if any")
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: error is acknowledging active alert')
        self.default_mem_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_MEM_USAGE)
        LOGGER.info("Step 2: Generate memory usage fault.")
        resp = self.sw_alert_obj.gen_mem_usage_fault_reboot_node(test_cfg["delta_mem_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Memory usage fault is created successfully.")
        LOGGER.info("Step 4: Keep the Memory usage above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: Memory usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 6: Checking if memory fault is present in new alerts")
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        time.sleep(10)
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in new alert')
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in active alert')
        LOGGER.info("Step 7: Successfully verified Memory usage fault alert on CSM GUI")
        LOGGER.info("Step 8: Resolving Memory usage fault.")
        LOGGER.info("Updating default Memory usage threshold value")
        resp = self.sw_alert_obj.resolv_mem_usage_fault_reboot_node(self.default_mem_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 9: Memory usage fault is resolved.")
        self.default_mem_usage = False
        LOGGER.info("Step 10: Keep the memory usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 11: Memory usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 12: Checking Memory usage resolved alerts on CSM GUI")
        time.sleep(10)
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in active alert')
        LOGGER.info("Step 13: Successfully verified Memory usage alert on CSM GUI")
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-25105")
    @pytest.mark.csm_gui
    @pytest.mark.sw_alert
    def test_25105_diskspace_full_threshold(self):
        """CSM-GUI: System Test to validate OS server alert and check for fault resolved (Disk space full)
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        test_cfg = RAS_TEST_CFG["test_21586"]
        LOGGER.info("Step 1: Check if disk space full fault is not already present in new alerts")
        alert_description = 'Disk usage increased to'
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/TEST-25105_Gui_Logs'
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path,
                                "description:" + alert_description]
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in new alert')
        LOGGER.info("Acknowledge alert from active alert table if any")
        gui_dict['tag'] = 'ACKNOWLEDGE_ACTIVE_ALERT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: error is acknowledging active alert')
        self.default_disk_usage = self.sw_alert_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL, field=cons.CONF_DISK_USAGE)
        LOGGER.info("Step 2: Generate Disk Full usage fault.")
        resp = self.sw_alert_obj.gen_disk_usage_fault(test_cfg["delta_disk_usage"])
        assert resp[0], resp[1]
        LOGGER.info("Step 3: Disk Full fault is created successfully.")
        LOGGER.info("Step 4: Keep the Disk Full fault above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 5: Disk Full fault usage was above threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 6: Checking if Disk full fault is present in new alerts")
        gui_dict['tag'] = 'CHECK_IN_NEW_ALERTS'
        time.sleep(30)
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in new alert')
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(False, gui_response, 'GUI FAILED: Alert is already present in active alert')
        LOGGER.info("Step 7: Successfully verified disk space full fault alert on CSM GUI")
        LOGGER.info("Step 8: Resolving Disk space full usage fault.")
        LOGGER.info("Updating default Disk usage threshold value")
        resp = self.sw_alert_obj.resolv_disk_usage_fault_reboot_node(self.default_disk_usage)
        assert resp[0], resp[1]
        LOGGER.info("Step 9: Rebooting node %s ", self.host)
        self.default_disk_usage = False
        LOGGER.info("Step 10: Keep the disk usage below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        time.sleep(self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 11: Disk usage was below threshold for %s seconds",
                    self.cfg["alert_wait_threshold"])
        LOGGER.info("Step 12: Checking Disk usage resolved alerts on CSM GUI")
        time.sleep(30)
        gui_dict['tag'] = 'CHECK_IN_ACTIVE_ALERTS'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED: Alert is not present in active alert')
        LOGGER.info("Step 14: Successfully verified Disk space full  usage alert on CSM GUI")
        LOGGER.info("### Test completed - %s ###", test_case_name)
