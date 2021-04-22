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
from commons import cortxlogging

from libs.csm.rest.csm_rest_alert import SystemAlerts
from commons.alerts_simulator.generate_alert_lib import \
     GenerateAlertLib, AlertType
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG

LOGGER = logging.getLogger(__name__)


class TestSSPL:
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
        # cls.default_cpu_usage = cls.default_mem_usage = True

        cls.ras_test_obj = RASTestLib(host=cls.host, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                            password=cls.passwd)
        cls.health_obj = Health(hostname=cls.host, username=cls.uname,
                                password=cls.passwd)
        # cls.controller_obj = ControllerLib(
        #     host=cls.host, h_user=cls.uname, h_pwd=cls.passwd,
        #     enclosure_ip=CMN_CFG["enclosure"]["primary_enclosure_ip"],
        #     enclosure_user=CMN_CFG["enclosure"]["enclosure_user"],
        #     enclosure_pwd=CMN_CFG["enclosure"]["enclosure_pwd"])

        # cls.alert_api_obj = GenerateAlertLib()
        cls.csm_alert_obj = SystemAlerts(cls.node_obj)
        # Enable this flag for starting RMQ channel
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.s3obj = S3H_OBJ

        field_list = ("primary_controller_ip", "secondary_controller_ip",
                      "primary_controller_port", "secondary_controller_port",
                      "user", "password", "secret")
        LOGGER.info("Putting expected values in KV store")
        for field in field_list:
            res = cls.ras_test_obj.put_kv_store(
                CMN_CFG["enclosure"]["enclosure_user"],
                CMN_CFG["enclosure"]["enclosure_pwd"], field)
            assert res

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

        LOGGER.info("Delete keys with prefix SSPL_")
        cmd = common_cmd.REMOVE_UNWANTED_CONSUL
        self.node_obj.execute_cmd(cmd=cmd, read_lines=True)

        LOGGER.info("Restarting sspl service")
        resp = self.health_obj.restart_pcs_resource(self.cm_cfg["sspl_resource_id"])
        assert resp, "Failed to restart sspl-ll"
        time.sleep(self.cm_cfg["after_service_restart_sleep_val"])
        LOGGER.info(
            "Verifying the status of sspl and rabittmq service is online")

        # Getting SSPl and Kafka service status
        services = self.cm_cfg["service"]
        resp = self.s3obj.get_s3server_service_status(
            service=services["sspl_service"], host=self.host, user=self.uname,
            pwd=self.passwd)
        assert resp[0], resp[1]
        resp = self.s3obj.get_s3server_service_status(
            service=services["kafka"], host=self.host, user=self.uname,
            pwd=self.passwd)
        assert resp[0], resp[1]

        LOGGER.info(
            "Validated the status of sspl and kafka service are online")

        if self.start_msg_bus:
            LOGGER.info("Running read_message_bus.py script on node")
            resp = self.ras_test_obj.start_message_bus_reader_cmd(
                self.cm_cfg["sspl_exch"], self.cm_cfg["sspl_key"])
            assert resp, "Failed to start RMQ channel"
            LOGGER.info(
                "Successfully started read_message_bus.py script on node")

        LOGGER.info("Starting collection of sspl.log")
        res = self.ras_test_obj.sspl_log_collect()
        assert res[0], res[1]
        LOGGER.info("Started collection of sspl logs")

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
            assert resp, "Failed to enable sspl-master"

        LOGGER.info("Restoring values to default in consul")

        if self.changed_level:
            kv_store_path = cons.LOG_STORE_PATH
            common_cfg = RAS_VAL["ras_sspl_alert"]["sspl_config"]
            res = self.ras_test_obj.update_threshold_values(
                kv_store_path, common_cfg["sspl_log_level_key"],
                common_cfg["sspl_log_dval"],
                update=True)
            assert res

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
            assert resp[0], "Failed to update selinux file"
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
    @CTFailOn(error_handler)
    def test_19609(self):
        test_case_name = cortxlogging.get_frame()
        LOGGER.info("##### Test started -  %s #####", test_case_name)
        external_svcs = 

        LOGGER.info("##### Test completed -  %s #####", test_case_name)