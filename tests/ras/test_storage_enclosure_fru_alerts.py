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

"""Test suite for storage enclosure fru related tests."""

import logging
import os
import random
import time

import pandas as pd
import pytest

from commons import commands as common_cmd
from commons import constants as cons
from commons.alerts_simulator.generate_alert_lib import AlertType
from commons.alerts_simulator.generate_alert_lib import GenerateAlertLib
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.controller_helper import ControllerLib
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from config import CMN_CFG
from config import RAS_TEST_CFG
from config import RAS_VAL
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ras.ras_test_lib import RASTestLib
from libs.s3 import S3H_OBJ

LOGGER = logging.getLogger(__name__)


class TestStorageAlerts:
    """SSPL Storage Enlosure FRU Test Suite."""

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

        field_list = ["CONF_PRIMARY_IP", "CONF_PRIMARY_PORT",
                      "CONF_SECONDARY_IP", "CONF_SECONDARY_PORT",
                      "CONF_ENCL_USER", "CONF_ENCL_SECRET"]
        LOGGER.info("Putting enclosure values in CONF store")
        resp = cls.ras_test_obj.update_enclosure_values(enclosure_vals=dict(
            zip(field_list, [None]*len(field_list))))
        assert_utils.assert_true(resp[0], "Successfully updated enclosure values")
        cls.system_random = random.SystemRandom()

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
            assert_utils.assert_true(resp, "Failed to start message bus channel")
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
        assert_utils.assert_true(res[0], res[1])
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
        service = self.cm_cfg["service"]
        self.node_obj.send_systemctl_cmd(command="restart",
                                         services=[service["sspl_service"]],
                                         decode=True)
        time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-11762")
    @CTFailOn(error_handler)
    def test_disable_enclosure_drive_157(self):
        """
        EOS-9962: Test verifies fault alert in message bus and
        CSM REST after disabling a drive from disk group
        """
        LOGGER.info("STARTED: Test Disabling a drive from disk group")

        common_cfg = RAS_VAL["ras_sspl_alert"]
        csm_error_msg = common_cfg["csm_error_msg"]
        test_cfg = RAS_TEST_CFG["test_157"]

        LOGGER.info("Step 1: Getting total number of drives mapped")
        resp = self.controller_obj.get_total_drive_count(
            telnet_file=common_cfg["file"]["telnet_xml"])

        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Total number of mapped drives is %s", resp[1])

        LOGGER.info("Randomly picking phy to disable")
        phy_num = self.system_random.randint(0, resp[1] - 1)

        LOGGER.info("Step 2: Disabling phy number %s", phy_num)
        resp = self.alert_api_obj.generate_alert(
            AlertType.DISK_DISABLE,
            input_parameters={"enclid": test_cfg["encl"],
                              "ctrl_name": test_cfg["ctrl"],
                              "phy_num": phy_num,
                              "operation": test_cfg["operation_fault"],
                              "exp_status": test_cfg["degraded_phy_status"],
                              "telnet_file": common_cfg["file"]["telnet_xml"]})
        assert_utils.assert_true(resp[0], resp[1])

        phy_stat = test_cfg["degraded_phy_status"]
        LOGGER.info("Step 2: Successfully put phy in %s state", phy_stat)

        if phy_num < 10:
            resource_id = f"disk_00.0{phy_num}"
        else:
            resource_id = f"disk_00.{phy_num}"
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
        assert_utils.assert_true(resp[0], resp[1])
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
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 6: Checked generated alert logs")

        assert_utils.assert_true(resp_csm, csm_error_msg)
        LOGGER.info("Step 3: Successfully checked CSM REST API for alerts")

        LOGGER.info(
            "ENDED: Test Disabling a drive from disk group")

    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-11763")
    @CTFailOn(error_handler)
    def test_enable_enclosure_drive_158(self):
        """
        EOS-9963: Test verifies fault resolved alert in message bus and
        CSM REST after enabling a drive from disk group
        """
        LOGGER.info(
            "STARTED: Test Enabling a drive from disk group")

        common_cfg = RAS_VAL["ras_sspl_alert"]
        csm_error_msg = common_cfg["csm_error_msg"]
        test_cfg = RAS_TEST_CFG["test_158"]

        LOGGER.info("Step 1: Getting total number of drives mapped")
        resp = self.controller_obj.get_total_drive_count(
            telnet_file=common_cfg["file"]["telnet_xml"])

        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Total number of mapped drives is %s", resp[1])

        LOGGER.info("Randomly picking phy to disable")
        phy_num = self.system_random.randint(0, resp[1] - 1)

        LOGGER.info("Step 2: Disabling phy number %s", phy_num)
        resp = self.alert_api_obj.generate_alert(
            AlertType.DISK_DISABLE,
            input_parameters={"enclid": test_cfg["encl"],
                              "ctrl_name": test_cfg["ctrl"],
                              "phy_num": phy_num,
                              "operation": test_cfg["operation_fault"],
                              "exp_status": test_cfg["degraded_phy_status"],
                              "telnet_file": common_cfg["file"]["telnet_xml"]})
        assert_utils.assert_true(resp[0], resp[1])

        phy_stat = test_cfg["degraded_phy_status"]
        LOGGER.info("Step 2: Successfully put phy in %s state", phy_stat)

        LOGGER.info("Step 3: Clearing metadata of drive %s", phy_num)
        drive_num = f"0.{phy_num}"
        resp = self.controller_obj.clear_drive_metadata(drive_num=drive_num)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Cleared %s drive metadata successfully", drive_num)

        LOGGER.info("Step 4: Again enabling phy number %s", phy_num)
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
                assert phy_stat == resp[1], f"Step 3: Failed to put phy in " \
                                            f"{phy_stat} state"

        LOGGER.info("Step 4: Successfully put phy in %s state", phy_stat)

        if phy_num < 10:
            resource_id = f"disk_00.0{phy_num}"
        else:
            resource_id = f"disk_00.{phy_num}"

        time.sleep(common_cfg["sleep_val"])
        if self.start_msg_bus:
            LOGGER.info("Step 5: Checking the generated alert logs")
            alert_list = [test_cfg["resource_type"], test_cfg["alert_type"],
                          resource_id]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 5: Checked generated alert logs")

        LOGGER.info("Step 6: Checking CSM REST API for alert")
        time.sleep(common_cfg["csm_alert_gen_delay"])
        resp = self.csm_alert_obj.verify_csm_response(self.starttime,
                                                      test_cfg["alert_type"],
                                                      True,
                                                      test_cfg["resource_type"],
                                                      resource_id)

        assert_utils.assert_true(resp, csm_error_msg)
        LOGGER.info("Step 6: Successfully checked CSM REST API for alerts")

        LOGGER.info(
            "ENDED: Test Enabling a drive from disk group")

    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-22060")
    def test_basic_dg_alerts_22060(self):
        """
        Test alerts when disk group is in degraded/OK health
        """
        LOGGER.info("STARTED: Test Disk group failure faults")

        test_cfg = RAS_TEST_CFG["test_22060"]
        disk_group = test_cfg["disk_group"]
        d_f = pd.DataFrame(index='Step1 Step2 Step3 Step4 Step5 Step6'.split(),
                           columns='Iteration0'.split())
        d_f = d_f.assign(Iteration0='Pass')
        LOGGER.info("Step 1: Create disk group failure on %s", disk_group)
        resp = self.alert_api_obj.generate_alert(
            AlertType.DG_FAULT,
            input_parameters={"enclid": test_cfg["enclid"],
                              "ctrl_name": test_cfg["ctrl_name"],
                              "operation": test_cfg["operation_fault"],
                              "disk_group": disk_group})
        if not resp[0]:
            d_f['Iteration0']['Step1'] = 'Fail'
            LOGGER.error("Step 1: Failed to create fault. Error: %s", resp[1])
        else:
            self.dg_failure = True
            LOGGER.info("Step 1: Successfully created disk group failure on "
                        "%s\n Response: %s", disk_group, resp)
        drives = resp[1]

        time.sleep(self.cm_cfg["sleep_val"])
        if self.start_msg_bus:
            LOGGER.info("Step 2: Verifying alert logs for fault alert ")
            alert_list = [test_cfg["resource_type"], self.alert_types["fault"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            if not resp[0]:
                d_f['Iteration0']['Step2'] = 'Fail'
                LOGGER.error("Step 2: Expected alert not found. Error: %s",
                             resp[1])
            else:
                LOGGER.info("Step 2: Checked generated alert logs. Response: "
                            "%s", resp)

        # Revisit when alerts are available in CSM.
        # LOGGER.info("Step 3: Checking CSM REST API for fault alert")
        # time.sleep(self.cm_cfg["csm_alert_gen_delay"])
        # resp = self.csm_alert_obj.verify_csm_response(self.starttime,
        #                                               self.alert_types["fault"],
        #                                               False,
        #                                               test_cfg["resource_type"])
        #
        # if not resp[0]:
        #     d_f['Iteration0']['Step3'] = 'Fail'
        #     LOGGER.error("Step 3: Expected alert not found. Error: %s",
        #     test_cfg["csm_error_msg"])
        # else:
        #     LOGGER.info("Step 3: Successfully checked CSM REST API for fault "
        #                 "alert. Response: %s", resp)

        LOGGER.info("Step 4: Resolve disk group failure on %s", disk_group)
        resp = self.alert_api_obj.generate_alert(
            AlertType.DG_FAULT_RESOLVED,
            input_parameters={"enclid": test_cfg["enclid"],
                              "ctrl_name": test_cfg["ctrl_name"],
                              "operation": test_cfg["operation_fault_resolved"],
                              "disk_group": disk_group,
                              "phy_num": drives, "poll": True})
        if not resp[0]:
            d_f['Iteration0']['Step4'] = 'Fail'
            LOGGER.error("Step 4: Failed to resolve fault. Error: %s", resp[1])
        else:
            self.dg_failure = False
            LOGGER.info("Step 4: Successfully resolved disk group failure on "
                        "%s\n Response: %s", disk_group, resp)

        time.sleep(self.cm_cfg["sleep_val"])
        if self.start_msg_bus:
            LOGGER.info("Step 5: Verifying alert logs for fault_resolved "
                        "alert ")
            alert_list = [test_cfg["resource_type"],
                          self.alert_types["resolved"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            if not resp[0]:
                d_f['Iteration0']['Step5'] = 'Fail'
                LOGGER.error("Step 5: Expected alert not found. Error: %s",
                             resp[1])
            else:
                LOGGER.info("Step 5: Checked generated alert logs\n Response: %s", resp)

        # Revisit when alerts are available in CSM.
        # LOGGER.info("Step 6: Checking CSM REST API for fault alert")
        # time.sleep(self.cm_cfg["csm_alert_gen_delay"])
        # resp = self.csm_alert_obj.verify_csm_response(self.starttime,
        #                                               self.alert_types["resolved"],
        #                                               True,
        #                                               test_cfg["resource_type"])
        #
        # if not resp[0]:
        #     d_f['Iteration0']['Step6'] = 'Fail'
        #     LOGGER.error("Step 6: Expected alert not found.Error: %s",
        #     test_cfg["csm_error_msg"])
        # else:
        #     LOGGER.info("Step 6: Successfully checked CSM REST API for "
        #                 "fault_resolved alert. Response: %s", resp)

        LOGGER.info("Summary of test: %s", d_f)
        result = False if 'Fail' in d_f.values else True
        assert_utils.assert_true(result, "Test failed. Please check summary for failed "
                                         "step.")
        LOGGER.info("ENDED: Test Disk group failure faults")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-branches
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-22062")
    def test_persistent_cache_dg_alerts_sspl_22062(self):
        """
        Test alerts in persistent cache for storage enclosure fru
        (disk group failure) - Restart SSPL
        """
        LOGGER.info("STARTED: Test persistent cache for Disk group faults "
                    "when SSPL is stopped and started")

        test_cfg = RAS_TEST_CFG["test_22060"]
        disk_group = test_cfg["disk_group"]
        d_f = pd.DataFrame(index='Step1 Step2 Step3 Step4 Step5 Step6 '
                                 'Step7 Step8'.split(),
                           columns='Iteration0'.split())
        d_f = d_f.assign(Iteration0='Pass')
        LOGGER.info("Step 1: Create disk group failure on %s", disk_group)
        resp = self.alert_api_obj.generate_alert(
            AlertType.DG_FAULT,
            input_parameters={"enclid": test_cfg["enclid"],
                              "ctrl_name": test_cfg["ctrl_name"],
                              "operation": test_cfg["operation_fault"],
                              "disk_group": disk_group})
        if not resp[0]:
            d_f['Iteration0']['Step1'] = 'Fail'
            LOGGER.error("Step 1: Failed to create fault. Error: %s", resp[1])
        else:
            self.dg_failure = True
            LOGGER.info("Step 1: Successfully created disk group failure on "
                        "%s \n Response: %s", disk_group, resp)
        drives = resp[1]

        time.sleep(self.cm_cfg["sleep_val"])
        if self.start_msg_bus:
            LOGGER.info("Step 2: Verifying alert logs for fault alert ")
            alert_list = [test_cfg["resource_type"], self.alert_types["fault"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            if not resp[0]:
                d_f['Iteration0']['Step2'] = 'Fail'
                LOGGER.error("Step 2: Expected alert not found. Error: %s",
                             resp[1])
            else:
                LOGGER.info("Step 2: Checked generated alert logs, Response: "
                            "%s", resp)

        # Revisit when R2 HW is available.
        # LOGGER.info("Step 3: Checking CSM REST API for fault alert")
        # time.sleep(self.cm_cfg["csm_alert_gen_delay"])
        # resp = self.csm_alert_obj.verify_csm_response(self.starttime,
        #                                               self.alert_types["fault"],
        #                                               False,
        #                                               test_cfg["resource_type"])
        #
        # if not resp[0]:
        #     d_f['Iteration0']['Step3'] = 'Fail'
        #     LOGGER.error("Step 3: Expected alert not found. Error: %s",
        #     test_cfg["csm_error_msg"])
        # else:
        #     LOGGER.info("Step 3: Successfully checked CSM REST API for fault "
        #                 "alert. \n Response: %s", resp)

        LOGGER.info("Step 4: Stopping SSPL service")
        service = self.cm_cfg["service"]
        resp = self.node_obj.send_systemctl_cmd(command="stop",
                                                services=[service["sspl_service"]])

        resp = self.s3obj.get_s3server_service_status(
                service=service["sspl_service"], host=self.host,
                user=self.uname,
                pwd=self.passwd)
        if resp[0]:
            d_f['Iteration0']['Step4'] = 'Fail'
            LOGGER.error("Step 4: Failed to stop SSPL service. Error: %s",
                         resp[1])
        else:
            LOGGER.info("Step 4: Successfully stopped SSPL service\n "
                        "Response: %s", resp)

        LOGGER.info("Step 5: Resolve disk group failure on %s", disk_group)
        resp = self.alert_api_obj.generate_alert(
            AlertType.DG_FAULT_RESOLVED,
            input_parameters={"enclid": test_cfg["enclid"],
                              "ctrl_name": test_cfg["ctrl_name"],
                              "operation": test_cfg["operation_fault_resolved"],
                              "disk_group": disk_group,
                              "phy_num": drives, "poll": True})
        if not resp[0]:
            d_f['Iteration0']['Step5'] = 'Fail'
            LOGGER.error("Step 5: Failed to resolve fault. Error: %s", resp[1])
        else:
            self.dg_failure = False
            LOGGER.info("Step 5: Successfully resolved disk group failure on "
                        "%s. Response: %s", disk_group, resp)

        LOGGER.info("Step 6: Starting SSPL service")
        service = self.cm_cfg["service"]
        resp = self.node_obj.send_systemctl_cmd(command="start",
                                                services=[service["sspl_service"]])

        resp = self.s3obj.get_s3server_service_status(
            service=service["sspl_service"], host=self.host,
            user=self.uname,
            pwd=self.passwd)
        if not resp[0]:
            d_f['Iteration0']['Step6'] = 'Fail'
            LOGGER.error("Step 6: Failed to start SSPL service. Error: %s",
                         resp[1])
        else:
            LOGGER.info("Step 6: Successfully stopped SSPL service. \n "
                        "Response: %s", resp)

        time.sleep(self.cm_cfg["sleep_val"])
        if self.start_msg_bus:
            LOGGER.info("Step 7: Verifying alert logs for fault_resolved "
                        "alert ")
            alert_list = [test_cfg["resource_type"],
                          self.alert_types["resolved"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            if not resp[0]:
                d_f['Iteration0']['Step7'] = 'Fail'
                LOGGER.error("Step 7: Expected alert not found. Error: %s",
                             resp[1])
            else:
                LOGGER.info("Step 7: Checked generated alert logs. \n "
                            "Response: %s", resp)

        # Revisit when R2 HW is available.
        # LOGGER.info("Step 8: Checking CSM REST API for fault alert")
        # time.sleep(self.cm_cfg["csm_alert_gen_delay"])
        # resp = self.csm_alert_obj.verify_csm_response(self.starttime,
        #                                               self.alert_types["resolved"],
        #                                               True,
        #                                               test_cfg["resource_type"])
        #
        # if not resp[0]:
        #     d_f['Iteration0']['Step8'] = 'Fail'
        #     LOGGER.error("Step 8: Expected alert not found. Error: %s",
        #     test_cfg["csm_error_msg"])
        # else:
        #     LOGGER.info("Step 8: Successfully checked CSM REST API for "
        #                 "fault_resolved alert. \n Response: %s", resp)

        LOGGER.info("Summary of test: %s", d_f)
        result = False if 'Fail' in d_f.values else True
        assert_utils.assert_true(result, "Test failed. Please check summary for failed "
                                         "step.")
        LOGGER.info("ENDED: Test persistent cache for Disk group faults "
                    "when SSPL is stopped and started")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-branches
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.hw_alert
    @pytest.mark.tags("TEST-22063")
    def test_persistent_cache_dg_alerts_reboot_22063(self):
        """
        Test alerts in persistent cache for storage enclosure fru
        (disk group failure) - Reboot node
        """
        LOGGER.info("STARTED: Test persistent cache for Disk group faults "
                    "when node is rebooted")

        test_cfg = RAS_TEST_CFG["test_22060"]
        disk_group = test_cfg["disk_group"]
        d_f = pd.DataFrame(index='Step1 Step2 Step3 Step4 Step5 Step6 '
                                 'Step7 Step8 Step9'.split(),
                           columns='Iteration0'.split())
        d_f = d_f.assign(Iteration0='Pass')
        LOGGER.info("Step 1: Create disk group failure on %s", disk_group)
        resp = self.alert_api_obj.generate_alert(
            AlertType.DG_FAULT,
            input_parameters={"enclid": test_cfg["enclid"],
                              "ctrl_name": test_cfg["ctrl_name"],
                              "operation": test_cfg["operation_fault"],
                              "disk_group": disk_group})
        if not resp[0]:
            d_f['Iteration0']['Step1'] = 'Fail'
            LOGGER.error("Step 1: Failed to create fault. Error: %s", resp[1])
        else:
            self.dg_failure = True
            LOGGER.info("Step 1: Successfully created disk group failure on "
                        "%s. Response: %s", disk_group, resp)
        drives = resp[1]

        time.sleep(self.cm_cfg["sleep_val"])
        if self.start_msg_bus:
            LOGGER.info("Step 2: Verifying alert logs for fault alert ")
            alert_list = [test_cfg["resource_type"], self.alert_types["fault"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            if not resp[0]:
                d_f['Iteration0']['Step2'] = 'Fail'
                LOGGER.error("Step 2: Expected alert not found. Error: %s",
                             resp[1])
            else:
                LOGGER.info("Step 2: Checked generated alert logs. \n "
                            "Response: %s", resp)

        # Revisit when R2 HW is available.
        # LOGGER.info("Step 3: Checking CSM REST API for fault alert")
        # time.sleep(self.cm_cfg["csm_alert_gen_delay"])
        # resp = self.csm_alert_obj.verify_csm_response(self.starttime,
        #                                               self.alert_types["fault"],
        #                                               False,
        #                                               test_cfg["resource_type"])
        #
        # if not resp[0]:
        #     d_f['Iteration0']['Step3'] = 'Fail'
        #     LOGGER.error("Step 3: Expected alert not found. Error: %s",
        #     test_cfg["csm_error_msg"])
        # else:
        #     LOGGER.info("Step 3: Successfully checked CSM REST API for fault "
        #                 "alert. \n Response: %s", resp)

        LOGGER.info("Step 4: Start reconstruction of disk group %s", disk_group)
        resp = self.alert_api_obj.generate_alert(
            AlertType.DG_FAULT_RESOLVED,
            input_parameters={"enclid": test_cfg["enclid"],
                              "ctrl_name": test_cfg["ctrl_name"],
                              "operation": test_cfg["operation_fault_resolved"],
                              "disk_group": disk_group,
                              "phy_num": drives, "poll": False})
        if not resp[0]:
            d_f['Iteration0']['Step4'] = 'Fail'
            LOGGER.error("Step 4: Failed to resolve fault. Error: %s", resp[1])
        else:
            self.dg_failure = False
            LOGGER.info("Step 4: Successfully started reconstruction of disk "
                        "group %s. Response: %s", disk_group, resp)

        LOGGER.info("Step 5: Polling progress of reconstruction job of disk "
                    "group")
        dg_health, _, poll_percent = self.controller_obj.poll_dg_recon_status(
            disk_group=disk_group, percent=93)
        if poll_percent == 100:
            d_f['Iteration0']['Step5'] = 'Fail'
            LOGGER.error("Step 5: Expected reconstruction percent <100. "
                         "Actual: %s", resp[1])
        elif poll_percent < 100:
            LOGGER.info("Step 6: Rebooting node %s ", self.host)
            resp = self.node_obj.execute_cmd(cmd=common_cmd.REBOOT_NODE_CMD,
                                             read_lines=True, exc=False)
            LOGGER.info(
                "Step 6: Rebooted node: %s, Response: %s", self.host, resp)

        time.sleep(self.cm_cfg["reboot_delay"])
        LOGGER.info("Step 7: Checking health state of disk group %s",
                    disk_group)
        _, disk_group_dict = self.controller_obj.get_show_disk_group()
        if disk_group_dict[disk_group]['health'] == 'OK':
            LOGGER.info("Step 7: Disk group %s is in healthy state", disk_group)
        else:
            LOGGER.info("Step 7: Checking if disk group is reconstructed "
                        "successfully")
            dg_health, job, poll_percent = self.controller_obj.poll_dg_recon_status(
                                        disk_group=disk_group)
            if dg_health == "OK":
                LOGGER.info("Step 7: Successfully recovered disk group %s \n "
                            "Reconstruction percent = %s", disk_group,
                            poll_percent)
            else:
                LOGGER.error("Step 7: Failed to recover disk group %s",
                             disk_group)
                d_f['Iteration0']['Step7'] = 'Fail'
                LOGGER.error("Expected reconstruction percent: 100. Actual: "
                             "%s\n Expected dg health: OK, Actual: %s",
                             poll_percent, dg_health)

        if self.start_msg_bus:
            LOGGER.info("Step 8: Verifying alert logs for fault_resolved "
                        "alert ")
            alert_list = [test_cfg["resource_type"],
                          self.alert_types["resolved"]]
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            if not resp[0]:
                d_f['Iteration0']['Step8'] = 'Fail'
                LOGGER.error("Step 8: Expected alert not found. Error: %s",
                             resp[1])
            else:
                LOGGER.info("Step 8: Checked generated alert logs. \n "
                            "Response: %s", resp)

        # Revisit when R2 HW is available.
        # LOGGER.info("Step 9: Checking CSM REST API for fault alert")
        # time.sleep(self.cm_cfg["csm_alert_gen_delay"])
        # resp = self.csm_alert_obj.verify_csm_response(self.starttime,
        #                                               self.alert_types["resolved"],
        #                                               True,
        #                                               test_cfg["resource_type"])
        #
        # if not resp[0]:
        #     d_f['Iteration0']['Step9'] = 'Fail'
        #     LOGGER.error("Step 9: Expected alert not found. Error: %s",
        #     test_cfg["csm_error_msg"])
        # else:
        #     LOGGER.info("Step 9: Successfully checked CSM REST API for "
        #                 "fault_resolved alert. \n Response: %s", resp)

        LOGGER.info("Summary of test: %s", d_f)
        result = False if 'Fail' in d_f.values else True
        assert_utils.assert_true(result, "Test failed. Please check summary for failed "
                                         "step.")
        LOGGER.info("ENDED: Test persistent cache for Disk group faults "
                    "when SSPL is stopped and started")
