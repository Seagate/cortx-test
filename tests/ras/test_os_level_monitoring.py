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
from commons.utils.system_utils import systemctl_cmd
from commons import constants as cons
from commons import commands as common_cmd
from commons.utils.assert_utils import *
from commons import cortxlogging
from libs.s3 import S3H_OBJ
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.ras.sw_alerts import SoftwareAlert

LOGGER = logging.getLogger(__name__)


class TestOSLevelMonitoring:
    """SSPL Test Suite."""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("Running setup_class")
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.host = CMN_CFG["nodes"][0]["host"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.sspl_stop = cls.changed_level = cls.selinux_enabled = False

        cls.ras_test_obj = RASTestLib(host=cls.host, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                            password=cls.passwd)
        cls.health_obj = Health(hostname=cls.host, username=cls.uname,
                                password=cls.passwd)

        cls.csm_alert_obj = SystemAlerts(cls.node_obj)
        # Enable this flag for starting RMQ channel
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.s3obj = S3H_OBJ
        cls.sw_alert_obj = SoftwareAlert("10.230.246.237", "root", "seagate")

    def setup_method(self):
        """Setup operations per test."""
        external_services = RAS_TEST_CFG["third_party_services"]
        common_cfg = RAS_VAL["ras_sspl_alert"]

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
            assert_true(response[0], response[1])
        LOGGER.info("Done Checking SSPL state file")

        LOGGER.info("Delete keys with prefix SSPL_")
        cmd = common_cmd.REMOVE_UNWANTED_CONSUL
        self.node_obj.execute_cmd(cmd=cmd, read_lines=True)

        LOGGER.info("Restarting sspl service")
        resp = self.health_obj.restart_pcs_resource(self.cm_cfg["sspl_resource_id"])
        assert_true(resp, "Failed to restart sspl-ll")
        time.sleep(self.cm_cfg["sspl_timeout"])
        LOGGER.info(
            "Verifying the status of sspl and kafka service is online")

        # Getting SSPl and Kafka service status
        services = self.cm_cfg["service"]
        resp = self.s3obj.get_s3server_service_status(
            service=services["sspl_service"], host=self.host, user=self.uname,
            pwd=self.passwd)
        assert_true(resp[0], resp[1])
        # resp = self.s3obj.get_s3server_service_status(
        #     service=services["kafka"], host=self.host, user=self.uname,
        #     pwd=self.passwd)
        # assert resp[0], resp[1]

        LOGGER.info(
            "Validated the status of sspl and kafka service are online")

        if self.start_msg_bus:
            LOGGER.info("Running read_message_bus.py script on node")
            resp = self.ras_test_obj.start_message_bus_reader_cmd(
                self.cm_cfg["sspl_exch"], self.cm_cfg["sspl_key"])
            assert_true(resp, "Failed to start message bus reader")
            LOGGER.info(
                "Successfully started read_message_bus.py script on node")

        LOGGER.info("Starting collection of sspl.log")
        res = self.ras_test_obj.sspl_log_collect()
        assert_true(res[0], res[1])
        LOGGER.info("Started collection of sspl logs")

        LOGGER.info("Check that all the 3rd party services are active")
        resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                services=external_services,
                                                decode=True, exc=False)

        stat_list = list(
            filter(lambda j: resp[j] != "active", range(0, len(resp))))
        inactive_list = []
        if stat_list:
            for i in stat_list:
                inactive_list.append(services[i])
            assert_true(False, f"{inactive_list} services are not in active "
                               f"state")
        LOGGER.info("All 3rd party services are in active state.")

        self.timeouts = common_cfg["os_lvl_monitor_timeouts"]

        LOGGER.info("Successfully performed Setup operations")

    def teardown_method(self):
        """Teardown operations."""
        LOGGER.info("Performing Teardown operation")
        self.ras_test_obj.retain_config(self.cm_cfg["file"]["original_sspl_conf"],
                                        True)

        if self.sspl_stop:
            LOGGER.info("Enable the SSPL master")
            resp = self.ras_test_obj.enable_disable_service(
                "enable", self.cm_cfg["sspl_resource_id"])
            assert_true(resp, "Failed to enable sspl-master")

        LOGGER.info("Restoring values to default in consul")

        if self.changed_level:
            kv_store_path = cons.LOG_STORE_PATH
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

        self.health_obj.restart_pcs_resource(
            resource=self.cm_cfg["sspl_resource_id"])
        time.sleep(self.cm_cfg["sleep_val"])

        if self.selinux_enabled:
            local_path = self.cm_cfg["local_selinux_path"]
            new_value = self.cm_cfg["selinux_disabled"]
            old_value = self.cm_cfg["selinux_enforced"]
            LOGGER.info("Modifying selinux status from %s to %s on node %s",
                        old_value, new_value, self.host)
            resp = self.ras_test_obj.modify_selinux_file()
            assert_true(resp[0], "Failed to update selinux file")
            LOGGER.info(
                "Modified selinux status to %s", new_value)

            LOGGER.info(
                "Rebooting node %s after modifying selinux status", self.host)
            self.node_obj.execute_cmd(cmd=common_cmd.REBOOT_NODE_CMD)
            time.sleep(self.cm_cfg["reboot_delay"])
            os.remove(local_path)
            LOGGER.info("Rebooted node %s after modifying selinux status",
                        self.host)

        LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.ras
    @pytest.mark.tags("TEST-19609")
    @pytest.mark.sw_alert
    @pytest.mark.skip
    def test_19609(self):
        "Tests 3rd party service monitoring and management"
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = RAS_TEST_CFG["third_party_services"]
        for svc in external_svcs:
            LOGGER.info("----- Started verifying operations on service:  %s ------", svc)

            LOGGER.info("Stopping %s service...", svc)
            starttime = time.time()
            result, e_csm_resp = self.sw_alert_obj.run_verify_svc_state(svc, "stop", external_svcs)
            assert result, "Failed in stop service"
            assert self.csm_alert_obj.verify_csm_response(
                starttime, e_csm_resp["alert_type"], False)

            LOGGER.info("Starting %s service...", svc)
            starttime = time.time()
            result, e_csm_resp = self.sw_alert_obj.run_verify_svc_state(svc, "start", external_svcs)
            assert result, " Failed in start service"
            assert self.csm_alert_obj.verify_csm_response(starttime, e_csm_resp["alert_type"], True)

            LOGGER.info("Disabling %s service...", svc)
            starttime = time.time()
            result, e_csm_resp = self.sw_alert_obj.run_verify_svc_state(
                svc, "disable", external_svcs)
            assert result, "Failed in disable service"
            assert self.csm_alert_obj.verify_csm_response(
                starttime, e_csm_resp["alert_type"], False)

            LOGGER.info("Enabling %s service...", svc)
            starttime = time.time()
            result, e_csm_resp = self.sw_alert_obj.run_verify_svc_state(
                svc, "enable", external_svcs)
            assert result, "Failed in enable service"
            assert self.csm_alert_obj.verify_csm_response(starttime, e_csm_resp["alert_type"], True)

            LOGGER.info("Restarting %s service...", svc)
            starttime = time.time()
            result, e_csm_resp = self.sw_alert_obj.run_verify_svc_state(
                svc, "restart", external_svcs)
            assert result, "Failed in restart service"
            assert self.csm_alert_obj.verify_csm_response(starttime, e_csm_resp["alert_type"], True)

            LOGGER.info("----- Completed verifying operations on service:  %s ------", svc)
        LOGGER.info("##### Test completed -  %s #####", test_case_name)

    @pytest.mark.ras
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
        random_services = random.sample(RAS_TEST_CFG["third_party_services"],
                                        num_services)

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

        LOGGER.info(f"Step 6: Check IO state")
        # TODO: Check IO state after performing operations on services

        LOGGER.info(f"Step 7: Stop IOs")
        # TODO: Stop background IOs.
