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

LOGGER = logging.getLogger(__name__)


class Test3PSvcMonitoring:
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
            LOGGER.info("External service list : %s",cls.external_svcs )
        else:
            cls.external_svcs = const.SVCS_3P
        LOGGER.info("External service list : %s",cls.external_svcs)
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
        self.sw_alert_obj.restore_svc_config(teardown_restore=True, svc_path_dict=self.svc_path_dict)
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

    @pytest.mark.tags("TEST-19609")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    @pytest.mark.skip
    def test_19609_3ps_monitoring(self):
        "Tests 3rd party service monitoring and management"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = const.SVCS_3P

        for svc in external_svcs:
            LOGGER.info("----- Started verifying operations on service:  %s ------", svc)

            LOGGER.info("Stopping %s service...", svc)
            starttime = time.time()
            result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
            assert result, "Failed in stop service"
            assert self.csm_alert_obj.verify_csm_response(
                starttime, const.ResourceType.SW_SVC, False)

            LOGGER.info("Starting %s service...", svc)
            starttime = time.time()
            result = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
            assert result, " Failed in start service"
            assert self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, True)

            LOGGER.info("Disabling %s service...", svc)
            starttime = time.time()
            result = self.sw_alert_obj.run_verify_svc_state(
                svc, "disable", external_svcs)
            assert result, "Failed in disable service"
            assert self.csm_alert_obj.verify_csm_response(
                starttime, const.ResourceType.SW_SVC, False)

            LOGGER.info("Enabling %s service...", svc)
            starttime = time.time()
            result = self.sw_alert_obj.run_verify_svc_state(
                svc, "enable", external_svcs)
            assert result, "Failed in enable service"
            assert self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, True)

            LOGGER.info("Restarting %s service...", svc)
            starttime = time.time()
            result = self.sw_alert_obj.run_verify_svc_state(
                svc, "restart", external_svcs)
            assert result, "Failed in restart service"
            assert self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, True)
            # TODO message bus check.
            LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    @pytest.mark.tags("TEST-19963")
    def test_multiple_services_monitoring_19963(self):
        """
        Multiple 3rd party services monitoring and management
        """
        LOGGER.info("Step 1: Start IOs")
        # TODO: Add command to start IOs in background.

        LOGGER.info("Step 2: Stopping multiple randomly selected services")
        num_services = random.randint(0, 5)
        random_services = random.sample(const.SVCS_3P, num_services)

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
        LOGGER.info(f"Step 2: Successfully stopped {random_services}")

        time.sleep(self.timeouts["alert_timeout"])
        LOGGER.info("Step 3: Check if fault alert is generated for "
                    "%s services", random_services)
        # TODO: Check alert in message bus and using CSM cli/rest.

        LOGGER.info("Step 4: Starting %s", random_services)
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
        LOGGER.info("Step 4: Successfully started %s", random_services)

        time.sleep(self.timeouts["alert_timeout"])
        LOGGER.info("Step 5: Check if fault_resolved alert is generated for "
                    "%s services", random_services)
        # TODO: Check alert in message bus and using CSM cli/rest.

        LOGGER.info("Step 6: Check IO state")
        # TODO: Check IO state after performing operations on services

        LOGGER.info("Step 7: Stop IOs")
        # TODO: Stop background IOs.

    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    @pytest.mark.tags("TEST-21194")
    def test_21194_deactivating_alerts(self):
        """
        Test when service takes longer than expected to deactivate
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        for svc in self.external_svcs:
            LOGGER.info("-"*100)
            LOGGER.info("----- Started verifying operations on service:  %s ------", svc)
            LOGGER.info("Step 1: Deactivating %s service...", svc)
            starttime = time.time()
            result = self.sw_alert_obj.run_verify_svc_state(svc, "deactivating", [])  # external_svcs
            assert result, "Failed in deactivating service"
            LOGGER.info("Step 1: Deactivated %s service...", svc)

            LOGGER.info("Step 2: Wait for : %s seconds", self.intrmdt_state_timeout)
            time.sleep(self.intrmdt_state_timeout)

            self.sw_alert_obj.restore_svc_config()
            if self.start_msg_bus:
                LOGGER.info("Step 3: Checking the fault alert on message bus")
                alert_list = [const.ResourceType.SW_SVC, const.Severity.CRITICAL,
                              const.AlertType.FAULT, svc]
                resp = self.ras_test_obj.alert_validation(string_list=alert_list,
                                                          restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 3: Verified the fault alert on message bus")


            LOGGER.info("Step 4: Checking the fault alert on CSM")
            resp = self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, False, svc)
            assert resp, "Fault alert is not reported on CSM"
            LOGGER.info("Step 4: Verified the fault alert on CSM")

            LOGGER.info("Step 5: Start the %s service again", svc)
            op = self.sw_alert_obj.recover_svc(svc)
            LOGGER.info("Service recovery details : %s", op)
            assert op["state"] == "active", "Unable to recover the service"
            LOGGER.info("Step 5: %s service is active and running", svc)

            if self.start_msg_bus:
                LOGGER.info("Step 6: Checking the fault resolved alert on message bus")
                alert_list = [const.ResourceType.SW_SVC, const.Severity.INFO,
                              const.AlertType.RESOLVED, svc]
                resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 6: Verified the fault resolved alert on message bus")

            LOGGER.info("Step 7: Checking the fault resolved alert on CSM")
            resp = self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, True, svc)
            assert resp, "Fault resolved Alert is not reported on CSM"
            LOGGER.info("Step 7: Verified the fault resolved alert on CSM")
            LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
            LOGGER.info("-"*100)

    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    @pytest.mark.tags("TEST-21193")
    def test_21193_activating_alerts(self):
        """
        Test when service takes longer than expected to activate
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        for svc in self.external_svcs:
            LOGGER.info("----- Started verifying operations on service:  %s ------", svc)

            LOGGER.info("Step 1: Stopping %s service...", svc)
            result = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
            assert result, "Failed in stop service"

            LOGGER.info("Step 2: Activating %s service...", svc)
            starttime = time.time()
            result = self.sw_alert_obj.run_verify_svc_state(svc, "activating", external_svcs)
            assert result, "Failed in activating service"
            LOGGER.info("Step 2: Activated %s service...", svc)

            LOGGER.info("Step 3: Wait for : %s seconds", self.intrmdt_state_timeout)
            time.sleep(self.intrmdt_state_timeout)

            if self.start_msg_bus:
                LOGGER.info("Step 4: Checking the fault alert on message bus")
                alert_list = [const.ResourceType.SW_SVC, const.Severity.CRITICAL,
                              const.AlertType.FAULT, svc]
                resp = self.ras_test_obj.alert_validation(string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 4: Verified the fault alert on message bus")


            LOGGER.info("Step 5: Checking the fault alert on CSM")
            resp = self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, False, svc)
            assert resp, "Fault alert is not reported on CSM"
            LOGGER.info("Step 5: Verified the fault alert on CSM")

            LOGGER.info("Step 6: Wait for the %s service to start", svc)
            op = self.sw_alert_obj.recover_svc(svc, attempt_start=False, timeout=200)
            LOGGER.info("Service recovery details : %s", op)
            assert op["state"] == "active", "Unable to recover the service"
            LOGGER.info("Step 6: %s service is active and running", svc)

            if self.start_msg_bus:
                LOGGER.info("Step 7: Checking the fault resolved alert on message bus")
                alert_list = [const.ResourceType.SW_SVC, const.Severity.INFO,
                              const.AlertType.RESOLVED, svc]
                resp = self.ras_test_obj.alert_validation(string_list=alert_list,
                                                          restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 7: Verified the fault resolved alert on message bus")

            LOGGER.info("Step 8: Checking the fault resolved alert on CSM")
            resp = self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, True, svc)
            assert resp, "Fault resolved alert is not reported on CSM"
            LOGGER.info("Step 8: Verified the fault resolved alert on CSM")

            LOGGER.info("Step 9: Restore the service configuration")
            self.sw_alert_obj.restore_svc_config()
            op = self.sw_alert_obj.recover_svc(svc)
            LOGGER.info("Service recovery details : %s", op)
            assert op["state"] == "active", "Unable to recover the service"
            LOGGER.info("Step 9: Service configuration restored")

    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    @pytest.mark.tags("TEST-21196")
    def test_21196_restarting_alerts(self):
        """
        Test when service takes longer than expected to restart
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        for svc in self.external_svcs:
            LOGGER.info("----- Started verifying operations on service:  %s ------", svc)

            LOGGER.info("Step 1: Simulating long restart for %s service...", svc)
            starttime = time.time()
            ignore_svc_param = RAS_VAL["test21196"]["ignore_params"]
            state_change_timeout = 50
            result = self.sw_alert_obj.run_verify_svc_state(
                svc, "restarting", self.external_svcs, timeout=state_change_timeout, ignore_param=ignore_svc_param)
            assert result, f"Failed in restarting {svc} service"
            LOGGER.info("Step 1: Restarted %s service...", svc)

            LOGGER.info("Step 2: Wait for : %s seconds", self.intrmdt_state_timeout)
            time.sleep(self.intrmdt_state_timeout)

            if self.start_msg_bus:
                LOGGER.info("Step 3: Checking the fault alert on message bus")
                alert_list = [const.ResourceType.SW_SVC, const.Severity.CRITICAL,
                              const.AlertType.FAULT, svc]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list,restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 3: Verified the fault alert on message bus")


            LOGGER.info("Step 4: Checking the fault alert on CSM")
            assert self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, True)
            LOGGER.info("Step 4: Verified the fault alert on CSM")

            LOGGER.info("Step 5: Restore %s service config and wait to start", svc)
            self.sw_alert_obj.restore_svc_config()
            op = self.sw_alert_obj.recover_svc(svc, attempt_start=True)
            LOGGER.info("Service recovery details : %s", op)
            assert op["state"] == "active", f"Unable to recover {svc} service"
            LOGGER.info("Step 5: %s service is active and running", svc)

            if self.start_msg_bus:
                LOGGER.info("Step 6: Checking the fault resolved alert on message bus")
                alert_list = [const.ResourceType.SW_SVC, const.Severity.INFO,
                              const.AlertType.RESOLVED, svc]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 6: Verified the fault resolved alert on message bus")


            LOGGER.info("Step 7: Checking the fault resolved alert on CSM")
            assert self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, True)
            LOGGER.info("Step 7: Verified the fault resolved alert on CSM")
            LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)

    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    @pytest.mark.tags("TEST-21193")
    def test_21193_failed_alerts(self):
        """
        Test when service file is missing and related process is killed.
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        LOGGER.info("External services : %s", self.external_svcs)
        for svc in self.external_svcs:
            LOGGER.info("----- Started verifying operations on service:  %s ------", svc)

            LOGGER.info("Step 1: Fail %s service...", svc)
            starttime = time.time()
            result = self.sw_alert_obj.run_verify_svc_state(svc, "failed", [],
                                                                        timeout=60)
            assert result, f"Failed in failing {svc} service"
            LOGGER.info("Step 1: Failed %s service...", svc)

            if self.start_msg_bus:
                LOGGER.info("Step 2: Checking the fault alert on message bus")
                alert_list = [const.ResourceType.SW_SVC, const.Severity.CRITICAL,
                              const.AlertType.FAULT, svc]
                resp = self.ras_test_obj.alert_validation(string_list=alert_list,
                                                          restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 2: Verified the fault alert on message bus")

            LOGGER.info("Step 3: Checking the fault alert on CSM")

            assert self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, True)
            LOGGER.info("Step 3: Verified the fault alert on CSM")

            self.sw_alert_obj.restore_svc_config()
            LOGGER.info("Step 4: Wait for the %s service to start", svc)
            op = self.sw_alert_obj.recover_svc(svc, attempt_start=True,
                                               timeout=const.SVC_LOAD_TIMEOUT_SEC)
            LOGGER.info("Service recovery details : %s", op)
            assert op["state"] == "active", f"Unable to recover {svc} service"
            LOGGER.info("Step 4: %s service is active and running", svc)

            if self.start_msg_bus:
                LOGGER.info("Step 5: Checking the fault resolved alert on message bus")
                alert_list = [const.ResourceType.SW_SVC, const.Severity.INFO,
                              const.AlertType.RESOLVED, svc]
                resp = self.ras_test_obj.alert_validation(string_list=alert_list,
                                                          restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 5: Verified the fault resolved alert on message bus")

            LOGGER.info("Step 6: Checking the fault resolved alert on CSM")

            assert self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, True)
            LOGGER.info("Step 6: Verified the fault resolved alert on CSM")

            LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)

    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    @pytest.mark.tags("TEST-21197")
    def test_21197_reloading_alerts(self):
        """
        Test when service takes longer than expected to reload
        """
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        for svc in self.external_svcs:
            LOGGER.info("----- Started verifying operations on service:  %s ------", svc)

            thrs_inact_time_tmp = 20
            LOGGER.info("Step 1: Configure threshold_inactive_time to {}".format(thrs_inact_time_tmp))
            self.ras_test_obj.set_conf_store_vals(
                url=self.sspl_cfg_url, encl_vals={"CONF_SSPL_SRV_THRS_INACT_TIME": thrs_inact_time_tmp})
            resp = self.ras_test_obj.get_conf_store_vals(
                url=self.sspl_cfg_url, field=self.sspl_thrs_inact_time)
            assert resp == str(thrs_inact_time_tmp), "Unable to configure threshold_inactive_time"
            LOGGER.info("Step 1: Configured threshold_inactive_time is : %s", resp)

            LOGGER.info("Step 2: Reloading %s service...", svc)
            starttime = time.time()
            result = self.sw_alert_obj.run_verify_svc_state(
                svc, "reloading", self.external_svcs, timeout=10)
            assert result, f"Failed in reloading {svc} service"
            LOGGER.info("Step 2: Reloaded %s service...", svc)

            if self.start_msg_bus:
                LOGGER.info("Step 3: Checking the fault alert on message bus")
                alert_list = [const.ResourceType.SW_SVC, const.Severity.CRITICAL,
                              const.AlertType.FAULT, svc]
                resp = self.ras_test_obj.alert_validation(string_list=alert_list,
                                                          restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 3: Verified the fault alert on message bus")


            LOGGER.info("Step 4: Checking the fault alert on CSM")
            assert self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, True)
            LOGGER.info("Step 4: Verified the fault alert on CSM")

            LOGGER.info("Step 5: Restore threshold_inactive_time to {}".format(self.thrs_inact_time_org))
            self.ras_test_obj.set_conf_store_vals(
                url=self.sspl_cfg_url, encl_vals={"CONF_SSPL_SRV_THRS_INACT_TIME": self.thrs_inact_time_org})
            resp = self.ras_test_obj.get_conf_store_vals(url=self.sspl_cfg_url,
                                                         field=self.sspl_thrs_inact_time)
            assert resp == self.thrs_inact_time_org, "Unable to restore threshold_inactive_time"
            LOGGER.info("Step 5: Restored threshold_inactive_time is : %s", resp)

            LOGGER.info("Step 6: Restore %s service config and wait to start", svc)
            self.sw_alert_obj.restore_svc_config()
            op = self.sw_alert_obj.recover_svc(svc, attempt_start=True)
            LOGGER.info("Service recovery details : %s", op)
            assert op["state"] == "active", f"Unable to recover {svc} service"
            LOGGER.info("Step 6: %s service is active and running", svc)

            if self.start_msg_bus:
                LOGGER.info("Step 7: Checking the fault resolved alert on message bus")
                alert_list = [const.ResourceType.SW_SVC, const.Severity.INFO,
                              const.AlertType.RESOLVED, svc]
                resp = self.ras_test_obj.alert_validation(
                    string_list=alert_list, restart=False)
                assert resp[0], resp[1]
                LOGGER.info("Step 7: Verified the fault resolved alert on message bus")


            LOGGER.info("Step 8: Checking the fault resolved alert on CSM")
            assert self.csm_alert_obj.verify_csm_response(starttime, const.ResourceType.SW_SVC, True)
            LOGGER.info("Step 8: Verified the fault resolved alert on CSM")
            LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
