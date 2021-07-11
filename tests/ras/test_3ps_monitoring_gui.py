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
from config import CMN_CFG, RAS_VAL
from commons.helpers.node_helper import Node
from commons.constants import LOG_STORE_PATH
from commons.constants import CONF_SSPL_SRV_THRS_INACT_TIME
from commons.constants import SSPL_CFG_URL
from commons.constants import SwAlerts as const
from commons import cortxlogging
from commons.utils.assert_utils import *
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.ras.sw_alerts import SoftwareAlert
from robot_gui.utils.call_robot_test import trigger_robot

LOGGER = logging.getLogger(__name__)


class Test3PSvcMonitoringGUI:
    """3rd party service monitoring test suite."""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("############ Running setup_class ############")
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
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.sw_alert_obj = SoftwareAlert(cls.host, cls.uname, cls.passwd)
        cls.svc_path_dict = {}
        cls.sspl_cfg_url = SSPL_CFG_URL
        cls.intrmdt_state_timeout = RAS_VAL["ras_sspl_alert"]["os_lvl_monitor_timeouts"]["intrmdt_state"]
        cls.sspl_thrs_inact_time = CONF_SSPL_SRV_THRS_INACT_TIME
        cls.thrs_inact_time_org = None
        if CMN_CFG["setup_type"] == "VM":
            cls.external_svcs = const.SVCS_3P_ENABLED_VM
        else:
            cls.external_svcs = const.SVCS_3P
        # required for Robot_GUI
        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.csm_url = "https://" + cls.mgmt_vip + "/#"
        cls.cwd = os.getcwd()
        cls.robot_gui_path = os.path.join(cls.cwd + '/robot_gui/')
        cls.robot_test_path = cls.robot_gui_path + 'testsuites/gui/.'
        cls.browser_type = 'chrome'
        cls.csm_user = CMN_CFG["csm"]["csm_admin_user"]["username"]
        cls.csm_passwd = CMN_CFG["csm"]["csm_admin_user"]["password"]
        LOGGER.info("External service list : %s", cls.external_svcs)
        LOGGER.info("############ Completed setup_class ############")

    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("############ Running setup_method ############")
        common_cfg = RAS_VAL["ras_sspl_alert"]
        services = self.cm_cfg["service"]
        sspl_svc = services["sspl_service"]
        self.timeouts = common_cfg["os_lvl_monitor_timeouts"]

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

        LOGGER.info("Store copy of config files for all the 3rd party services")
        for svc in self.external_svcs:
            self.svc_path_dict[svc] = self.sw_alert_obj.store_svc_config(svc)

        LOGGER.info("Capture threshold_inactive_time form {}".format(self.sspl_cfg_url))
        self.thrs_inact_time_org = self.ras_test_obj.get_conf_store_vals(
            url=self.sspl_cfg_url, field=self.sspl_thrs_inact_time)
        LOGGER.info("Captured threshold_inactive_time is {}".format(self.thrs_inact_time_org))

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
        LOGGER.info("############ Setup method completed ############")

    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("############ Performing Teardown operation ############")
        resp = self.ras_test_obj.get_conf_store_vals(
            url=self.sspl_cfg_url, field=self.sspl_thrs_inact_time)
        if resp != self.thrs_inact_time_org:
            LOGGER.info("Restore threshold_inactive_time to {}".format(self.thrs_inact_time_org))
            self.ras_test_obj.set_conf_store_vals(
                url=self.sspl_cfg_url, encl_vals={"CONF_SSPL_SRV_THRS_INACT_TIME": self.thrs_inact_time_org})
            resp = self.ras_test_obj.get_conf_store_vals(
                url=self.sspl_cfg_url, field=self.sspl_thrs_inact_time)
            assert resp == self.thrs_inact_time_org, "Unable to restore threshold_inactive_time in teardown"
            LOGGER.info("Successfully restored threshold_inactive_time to : %s", resp)

        LOGGER.info("Restore service config for all the 3rd party services")
        self.sw_alert_obj.restore_svc_config(
            teardown_restore=True, svc_path_dict=self.svc_path_dict)
        for svc in self.external_svcs:
            op = self.sw_alert_obj.recover_svc(svc, attempt_start=True)
            LOGGER.info("Service recovery details : %s", op)
            assert op["state"] == "active", f"Unable to recover the {svc} service"
        LOGGER.info("All 3rd party services recovered and in active state.")

        if self.changed_level:
            kv_store_path = LOG_STORE_PATH
            common_cfg = RAS_VAL["ras_sspl_alert"]["sspl_config"]
            res = self.ras_test_obj.update_threshold_values(
                kv_store_path, common_cfg["sspl_log_level_key"],
                common_cfg["sspl_log_dval"],
                update=True)
            assert_true(res)

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
        LOGGER.info("############ Successfully performed Teardown operation ############")

    @pytest.mark.tags("TEST-21265")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert

    def test_21265_3ps_monitoring_gui(self):
        "CSM GUI: Verify Alerts for SW Service : SaltStack"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "salt-master.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)

        svc = "salt-minion.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21257")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert

    def test_21257_3ps_monitoring_gui(self):
        "CSM GUI: Verify Alerts for SW Service : ElasticSearch-OSS"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "elasticsearch.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21256")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert

    def test_21256_3ps_monitoring_gui(self):
        "CSM GUI: Verify Alerts for SW Service : Consul"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "hare-consul-agent.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21258")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert

    def test_21258_3ps_monitoring_gui(self):
        "CSM GUI: Verify Alerts for SW Service : Scsi-network-relay"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "scsi-network-relay.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21260")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert

    def test_21260_3ps_monitoring_gui(self):
        "CSM GUI: Verify Alerts for SW Service : Statsd"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "statsd.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21266")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert

    def test_21266_3ps_monitoring_gui(self):
        "CSM GUI: Verify Alerts for SW Service : GlusterFS"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "glusterd.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21264")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert

    def test_21264_3ps_monitoring_gui(self):
        "CSM GUI: Verify Alerts for SW Service : Lustre"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "lnet.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21261")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert

    def test_21261_3ps_monitoring_gui(self):
        "CSM GUI: Verify Alerts for SW Service : Rsyslog"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "rsyslog.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        # Rsyslog is the medium to raise alerts. So when Rsyslog is down, no alerts will come.
        # Once Rsyslog is up, then both alerts will come.
        # gui_dict = dict()
        # gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        # gui_dict['test_path'] = self.robot_test_path
        # gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
        #                         self.browser_type, 'username:' + self.csm_user,
        #                         'servicename:' + svc,
        #                         'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        # gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        # gui_response = trigger_robot(gui_dict)
        # assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        # Rsyslog is the medium to raise alerts. So when Rsyslog is down, no alerts will come.
        # Once Rsyslog is up, then both alerts will come.
        # gui_dict = dict()
        # gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        # gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
        #                         self.browser_type, 'username:' + self.csm_user,
        #                         'servicename:' + svc,
        #                         'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        # gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        # gui_response = trigger_robot(gui_dict)
        # assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21263")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert

    def test_21263_3ps_monitoring_gui(self):
        "CSM GUI: Verify Alerts for SW Service : OpenLDAP"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "slapd.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21267")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert

    def test_21267_3ps_monitoring_gui(self):
        "CSM GUI: Verify Alerts for SW Service : Multipathd"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "multipathd.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.tags("TEST-21259")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert

    def test_21259_3ps_monitoring_gui(self):
        "CSM GUI: Verify Alerts for SW Service : Kafka"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = self.external_svcs

        svc = "kafka.service"
        LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
        assert result, "Failed in stop service"
        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        # Kafka is the medium to raise alerts. So when Kafka is down, no alerts will come.
        # Once Kafka is up, then both alerts will come.
        # gui_dict = dict()
        # gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_Gui_Logs_' + svc
        # gui_dict['test_path'] = self.robot_test_path
        # gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
        #                         self.browser_type, 'username:' + self.csm_user,
        #                         'servicename:' + svc,
        #                         'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        # gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE'
        # gui_response = trigger_robot(gui_dict)
        # assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Starting %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
        assert result, " Failed in start service"

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_INACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_INACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Deactivating %s service...", svc)
        result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", self.external_svcs)
        assert result, "Failed in deactivating service"
        LOGGER.info("Deactivated %s service...", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)

        # Kafka is the medium to raise alerts. So when Kafka is down, no alerts will come.
        # Once Kafka is up, then both alerts will come.
        # gui_dict = dict()
        # gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_Gui_Logs_' + svc
        # gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
        #                         self.browser_type, 'username:' + self.csm_user,
        #                         'servicename:' + svc,
        #                         'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        # gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE'
        # gui_response = trigger_robot(gui_dict)
        # assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Start the %s service again", svc)
        op = self.sw_alert_obj.recover_svc(svc)
        LOGGER.info("Service recovery details : %s", op)
        assert op["state"] == "active", "Unable to recover the service"
        LOGGER.info("%s service is active and running", svc)

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_VERIFY_DEACTIVATE_RESOLVED'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.skip
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    @pytest.mark.tags("TEST-19878")
    def test_19878_multiple_services_monitoring_gui(self):
        """
        Multiple 3rd party services monitoring and management
        """
        starttime = time.time()
        gui_dict = dict()
        gui_dict['log_path'] = self.cwd + '/log/latest/SW_SERVICE_INIT_Gui_Logs_' + svc
        gui_dict['test_path'] = self.robot_test_path
        gui_dict['variable'] = ['headless:True', 'url:' + self.csm_url, 'browser:' +
                                self.browser_type, 'username:' + self.csm_user,
                                'servicename:' + svc,
                                'password:' + self.csm_passwd, 'RESOURCES:' + self.robot_gui_path]
        gui_dict['tag'] = 'SW_SERVICE_INIT'
        gui_response = trigger_robot(gui_dict)
        assert_equals(True, gui_response, 'GUI FAILED')

        LOGGER.info("Stopping multiple randomly selected services")
        num_services = random.randint(0, len(self.external_svcs))
        random_services = random.sample(self.external_svcs, num_services)
        self.node_obj.send_systemctl_cmd("stop", services=random_services)
        LOGGER.info("Checking that %s services are in stopped state",
                    random_services)
        resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                services=random_services,
                                                decode=True, exc=False)
        stat_list = list(filter(lambda j: resp[j] == "active", range(0, len(resp))))
        active_list = []
        if stat_list:
            for i in stat_list:
                active_list.append(random_services[i])
            assert_true(False, f"Failed to put {active_list} services in "
                               f"stopped/inactive state")
        LOGGER.info(f"Successfully stopped {random_services}")

        LOGGER.info("Wait for : %s seconds", self.intrmdt_state_timeout)
        time.sleep(self.intrmdt_state_timeout)
        LOGGER.info("Wait completed")

        LOGGER.info("Check if fault alert is generated for %s services", random_services)
        resp = self.csm_alert_obj.wait_for_alert(200, starttime, const.ResourceType.SW_SVC, False)
        assert resp[0], resp[1]

        LOGGER.info("Starting %s", random_services)
        self.node_obj.send_systemctl_cmd("start", services=random_services)
        LOGGER.info("Checking that %s services are in active state", random_services)
        resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                services=random_services,
                                                decode=True, exc=False)
        stat_list = list(filter(lambda j: resp[j] != "active", range(0, len(resp))))
        inactive_list = []
        if stat_list:
            for i in stat_list:
                inactive_list.append(random_services[i])
            assert_true(False, f"Failed to put {inactive_list} services in "
                               f"active state")
        LOGGER.info("Successfully started %s", random_services)

        time.sleep(self.timeouts["alert_timeout"])
        LOGGER.info("Check if fault_resolved alert is generated for %s services",
            random_services)
        resp = self.csm_alert_obj.wait_for_alert(200, starttime, const.ResourceType.SW_SVC, True)
        assert resp[0], resp[1]
