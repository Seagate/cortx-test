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

"""Test Network Faults"""

import time
import random
import logging
import pytest
from libs.ras.ras_test_lib import RASTestLib
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health
from libs.s3 import S3H_OBJ
from commons.utils.assert_utils import *
from libs.csm.rest.csm_rest_alert import SystemAlerts
from commons.alerts_simulator.generate_alert_lib import \
     GenerateAlertLib, AlertType
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG

LOGGER = logging.getLogger(__name__)


class TestNetworkFault:
    """Network Fault Test Suite"""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("Running setup_class")
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.host = CMN_CFG["nodes"][0]["host"]
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.public_data_ip = CMN_CFG["nodes"][0]["public_data_ip"]
        cls.mgmt_ip = CMN_CFG["nodes"][0]['ip']
        cls.setup_type = CMN_CFG['setup_type']
        cls.nw_interfaces = RAS_TEST_CFG["network_interfaces"][cls.setup_type]
        cls.mgmt_device = cls.nw_interfaces["MGMT"]
        cls.public_data_device = cls.nw_interfaces["PUBLIC_DATA"]
        cls.private_data_device = cls.nw_interfaces["PRIVATE_DATA"]
        cls.sspl_stop = cls.changed_level = False

        cls.ras_test_obj = RASTestLib(host=cls.host, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                            password=cls.passwd)
        cls.health_obj = Health(hostname=cls.host, username=cls.uname,
                                password=cls.passwd)
        cls.alert_api_obj = GenerateAlertLib()
        cls.csm_alert_obj = SystemAlerts(cls.node_obj)
        # Enable this flag for starting message_bus
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]

        cls.mgmt_fault_flag = False

        cls.csm_alerts_obj = SystemAlerts()
        cls.s3obj = S3H_OBJ
        cls.alert_type = RAS_TEST_CFG["alert_types"]

        LOGGER.info("ENDED: Successfully performed setup_class")

    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("Running setup_method")
        self.starttime = time.time()
        LOGGER.info("Retaining the original/default config")
        self.ras_test_obj.retain_config(
            self.cm_cfg["file"]["original_sspl_conf"],
            False)

        LOGGER.info("Performing Setup operations")

        LOGGER.info("Checking SSPL state file")
        res = self.ras_test_obj.get_sspl_state()
        if not res:
            LOGGER.info("SSPL state file not present, creating same on server")
            response = self.ras_test_obj.check_status_file()
            assert response[0], response[1]
        LOGGER.info("Done Checking SSPL state file")

        services = self.cm_cfg["service"]

        resp = self.s3obj.get_s3server_service_status(
            service=services["sspl_service"], host=self.host, user=self.uname,
            pwd=self.passwd)
        assert resp[0], resp[1]
        # resp = self.s3obj.get_s3server_service_status(
        #     service=services["kafka_service"], host=self.host,
        #     user=self.uname,
        #     pwd=self.passwd)
        # assert resp[0], resp[1]
        #
        # LOGGER.info("Check CSM Web status")
        # resp = self.s3obj.get_s3server_service_status(
        #     service="csm_web", host=self.host, user=self.uname, pwd=self.passwd)
        # assert resp[0], resp[1]
        #
        # LOGGER.info("Check CSM Agent status")
        # resp = self.s3obj.get_s3server_service_status(
        #     service="csm_agent", host=self.host, user=self.uname,
        #     pwd=self.passwd)
        # assert resp[0], resp[1]
        #
        if self.start_msg_bus:
            LOGGER.info("Running read_message_bus.py script on node")
            resp = self.ras_test_obj.start_message_bus_reader_cmd()
            assert_true(resp, "Failed to start RMQ channel")
            LOGGER.info(
                "Successfully started read_message_bus.py script on node")

        LOGGER.info("Starting collection of sspl.log")
        res = self.ras_test_obj.sspl_log_collect()
        assert_true(res[0], res[1])
        LOGGER.info("Started collection of sspl logs")
        LOGGER.info("Successfully performed Setup operations")

    def teardown_method(self):
        """
        Teardown operations
        """
        LOGGER.info("STARTED: Performing the Teardown Operations")
        network_fault_params = RAS_TEST_CFG["mgmt_nw_port_fault"]
        if self.mgmt_fault_flag:
            LOGGER.info("Resolving Mgmt Network Fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.MGMT_NW_PRT_FAULT_RESOLVED,
                input_parameters={'device': self.mgmt_device,
                                  'status': network_fault_params["generate_fault"],
                                  'host_data_ip': self.public_data_ip})

            assert_true(resp[0], "{} {}".format(network_fault_params["error_msg"],
                                             network_fault_params["resolve_fault"]))

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
            LOGGER.info("Terminating the process rabbitmq_reader.py")
            self.ras_test_obj.kill_remote_process("rabbitmq_reader.py")
            files = [self.cm_cfg["file"]["alert_log_file"],
                     self.cm_cfg["file"]["extracted_alert_file"],
                     self.cm_cfg["file"]["screen_log"]]
            for file in files:
                LOGGER.info("Removing log file %s from the Node", file)
                self.node_obj.remove_file(filename=file)

        # self.health_obj.restart_pcs_resource(
        #     resource=self.cm_cfg["sspl_resource_id"])
        # time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("ENDED: Successfully performed the Teardown Operations")

    @pytest.mark.tags("TEST-21493")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_mgmt_network_port_fault(self):
        """
        EOS-21493: TA Destructive test : Automate mgt network port fault
        """
        LOGGER.info("STARTED: Verifying management network fault and "
                    "fault-resolved scenarios")

        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["mgmt_nw_port_fault"]
        LOGGER.info("Get values from cluster.sls")

        LOGGER.info("Step 1: Generating management network faults")
        LOGGER.info("Step 1.1: Creating fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.MGMT_NW_PORT_FAULT,
            input_parameters={'device': self.mgmt_device,
                              'status': network_fault_params["generate_fault"]})
        assert_true(resp[0], "{} {}".format(network_fault_params["error_msg"],
                                         network_fault_params["generate_fault"]))
        self.fault_flag = True
        LOGGER.info("Step 1.1: Successfully created management network "
                    f"port fault on {self.host}")

        wait_time = random.randint(common_params["min_wait_time"],
                                   common_params["max_wait_time"])

        LOGGER.info(f"Waiting for {wait_time} seconds")
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 1.2: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["fault"],
                          network_fault_params["resource_id_monitor"]]
            LOGGER.info(f"RAS checks: {alert_list}")
            resp = self.ras_test_obj.list_alert_validation(alert_list)

            assert_true(resp[0], resp[1])
            LOGGER.info("Step 1.2: Successfully checked generated alerts")

        # LOGGER.info("Step 1.3: Validating csm alert response")
        # resp = self.csm_alerts_obj.verify_csm_response(
        #                 self.starttime, self.alert_type["fault"],
        #                 False, network_fault_params["resource_type"],
        #                 network_fault_params["resource_id_csm"])
        # assert_true(resp, "Failed to get alert in CSM REST")
        # LOGGER.info("Step 1.3: Successfully Validated csm alert response")

        LOGGER.info("Step 2: Resolving fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.MGMT_NW_PRT_FAULT_RESOLVED,
            input_parameters={'device': self.mgmt_device,
                              'status': network_fault_params["resolve_fault"],
                              'host_data_ip': self.public_data_ip})
        assert_true(resp[0], "{} {}".format(network_fault_params["error_msg"],
                                         network_fault_params["resolve_fault"]))
        self.mgmt_fault_flag = False
        LOGGER.info("Step 2: Successfully resolved management network "
                    f"port fault on {self.host}")

        wait_time = common_params["min_wait_time"]

        LOGGER.info(f"Waiting for {wait_time} seconds")
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 2.1: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["resolved"],
                          network_fault_params["resource_id_monitor"]]
            LOGGER.info(f"RAS checks: {alert_list}")
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            assert_true(resp[0], resp[1])
            LOGGER.info("Step 2.1: Successfully checked generated alerts")

        # LOGGER.info(
        #     "Step 2.2: Validating csm alert response after resolving fault")
        #
        # resp = self.csm_alerts_obj.verify_csm_response(
        #                 self.starttime,
        #                 self.alert_type["resolved"],
        #                 True, network_fault_params["resource_type"],
        #                 network_fault_params["resource_id_csm"])
        # assert_true(resp, "Failed to get alert in CSM REST")
        # LOGGER.info(
        #     "Step 2.2: Successfully validated csm alert response after "
        #     "resolving fault")

        LOGGER.info("ENDED: Verifying management network fault and "
                    "fault-resolved scenarios")
