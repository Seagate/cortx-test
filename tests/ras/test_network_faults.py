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
import pandas as pd
from libs.ras.ras_test_lib import RASTestLib
from commons.helpers.node_helper import Node
from commons.helpers.health_helper import Health
from libs.s3 import S3H_OBJ
from commons.utils.assert_utils import *
from libs.csm.rest.csm_rest_alert import SystemAlerts
from commons.alerts_simulator.generate_alert_lib import \
     GenerateAlertLib, AlertType
from config import CMN_CFG, RAS_VAL, RAS_TEST_CFG
from commons import constants as cons

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
        cls.mgmt_ip = CMN_CFG["nodes"][0]["ip"]
        cls.setup_type = CMN_CFG['setup_type']
        cls.nw_interfaces = RAS_TEST_CFG["network_interfaces"][cls.setup_type]
        cls.mgmt_device = cls.nw_interfaces["MGMT"]
        cls.public_data_device = cls.nw_interfaces["PUBLIC_DATA"]
        cls.private_data_device = cls.nw_interfaces["PRIVATE_DATA"]
        cls.sspl_resource_id = cls.cm_cfg["sspl_resource_id"]

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
        cls.public_data_fault_flag = False

        resp = cls.health_obj.get_current_srvnode()
        cls.current_srvnode = resp[1] if resp[0] else assert_true(resp[0],
                                                                  "Check pcs "
                                                                  "status")
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

        if self.start_msg_bus:
            LOGGER.info("Running read_message_bus.py script on node")
            resp = self.ras_test_obj.start_message_bus_reader_cmd()
            assert_true(resp, "Failed to start RMQ channel")
            LOGGER.info(
                "Successfully started read_message_bus.py script on node")

        LOGGER.info("Check status of all network interfaces")
        status = self.health_obj.check_nw_interface_status()
        for k, v in status.items():
            if "DOWN" in v:
                LOGGER.info("%s is down. Please check network connections and "
                            "restart tests.", k)
                assert False, f"{k} is down. Please check network connections " \
                              f"and restart tests."
        LOGGER.info("All network interfaces are up.")
        LOGGER.info("Change sspl log level to DEBUG")
        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "DEBUG"})
        resp = self.ras_test_obj.get_conf_store_vals(
            url=cons.SSPL_CFG_URL,
            field=cons.CONF_SSPL_LOG_LEVEL)
        LOGGER.info("Now SSPL log level is: %s", resp)

        LOGGER.info("Restarting SSPL service")
        service = self.cm_cfg["service"]
        services = [service["sspl_service"], service["kafka_service"],
                    service["kafka_zookeeper"], service["csm_web"],
                    service["csm_agent"]]
        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[
                                                     self.sspl_resource_id],
                                                    srvnode=self.current_srvnode)

        time.sleep(15)
        for svc in services:
            LOGGER.info("Checking status of %s service", svc)
            resp = self.s3obj.get_s3server_service_status(service=svc,
                                                          host=self.host,
                                                          user=self.uname,
                                                          pwd=self.passwd)
            assert resp[0], resp[1]
            LOGGER.info("%s service is active/running", svc)

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
        network_fault_params = RAS_TEST_CFG["nw_port_fault"]
        if self.mgmt_fault_flag:
            LOGGER.info("Resolving Mgmt Network port Fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_PORT_FAULT_RESOLVED,
                input_parameters={'device': self.mgmt_device})

            LOGGER.info("Response: %s", resp)
            assert_true(resp[0], "{} up".format(network_fault_params["error_msg"]))

        if self.public_data_fault_flag:
            LOGGER.info("Resolving Public data Network port Fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_PORT_FAULT_RESOLVED,
                host_details={'host': self.mgmt_ip, 'h_user': self.uname,
                              'h_pwd': self.passwd},
                input_parameters={'device': self.public_data_device})
            LOGGER.info("Response: %s", resp)
            assert_true(resp[0],
                        "{} up".format(network_fault_params["error_msg"]))

        LOGGER.info("Change sspl log level to INFO")
        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "INFO"})
        resp = self.ras_test_obj.get_conf_store_vals(url=cons.SSPL_CFG_URL,
                                                     field=cons.CONF_SSPL_LOG_LEVEL)
        LOGGER.info("Now SSPL log level is: %s", resp)

        if self.public_data_fault_flag:
            LOGGER.info("Resolving Public data Network port Fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_PORT_FAULT_RESOLVED,
                host_details={'host': self.mgmt_ip, 'h_user': self.uname,
                              'h_pwd': self.passwd},
                input_parameters={'device': self.public_data_device})
            LOGGER.info("Response: %s", resp)
            assert_true(resp[0],
                        "{} up".format(network_fault_params["error_msg"]))

        LOGGER.info("Change sspl log level to INFO")
        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL, encl_vals={"CONF_SSPL_LOG_LEVEL": "INFO"})
        resp = self.ras_test_obj.get_conf_store_vals(url=cons.SSPL_CFG_URL,
                                                     field=cons.CONF_SSPL_LOG_LEVEL)
        LOGGER.info("Now SSPL log level is: %s", resp)

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

        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[
                                                     self.sspl_resource_id],
                                                    srvnode=self.current_srvnode)

        time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("ENDED: Successfully performed the Teardown Operations")

    @pytest.mark.tags("TEST-21493")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_mgmt_network_port_fault_test_21493(self):
        """
        EOS-21493: TA Destructive test : Automate mgt network port fault
        """
        LOGGER.info("STARTED: Verifying management network port fault and "
                    "fault-resolved scenarios")

        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_port_fault"]
        resource_id = self.mgmt_device

        LOGGER.info("Step 1: Generating management network faults")
        LOGGER.info("Step 1.1: Creating fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_PORT_FAULT,
            input_parameters={'device': self.mgmt_device})
        LOGGER.info("Response: %s", resp)
        assert_true(resp[0], "{} down".format(network_fault_params["error_msg"]))
        self.mgmt_fault_flag = True
        LOGGER.info("Step 1.1: Successfully created management network "
                    "port fault on %s", self.host)

        wait_time = random.randint(common_params["min_wait_time"],
                                   common_params["max_wait_time"])

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 1.2: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["fault"],
                          network_fault_params["resource_id_monitor"].format(
                              resource_id)]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)

            assert_true(resp[0], resp[1])
            LOGGER.info("Step 1.2: Successfully checked generated alerts")

        if self.setup_type != "VM":
            LOGGER.info("Step 1.3: Validating csm alert response")
            resp = self.csm_alerts_obj.verify_csm_response(
                            self.starttime, self.alert_type["fault"],
                            False, network_fault_params["resource_type"],
                            network_fault_params["resource_id_csm"].format(
                                          resource_id))
            LOGGER.info("Response: %s", resp)
            assert_true(resp, "Failed to get alert in CSM REST")
            LOGGER.info("Step 1.3: Successfully Validated csm alert response")

        LOGGER.info("Step 2: Resolving fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_PORT_FAULT_RESOLVED,
            input_parameters={'device': self.mgmt_device})
        LOGGER.info("Response: %s", resp)
        assert_true(resp[0], "{} up".format(network_fault_params["error_msg"]))
        self.mgmt_fault_flag = False
        LOGGER.info("Step 2: Successfully resolved management network "
                    "port fault on %s", self.host)

        wait_time = common_params["min_wait_time"]

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 2.1: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["resolved"],
                          network_fault_params["resource_id_monitor"].format(
                              resource_id)]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)
            assert_true(resp[0], resp[1])
            LOGGER.info("Step 2.1: Successfully checked generated alerts")

        if self.setup_type != "VM":
            LOGGER.info(
                "Step 2.2: Validating csm alert response after resolving fault")

            resp = self.csm_alerts_obj.verify_csm_response(
                            self.starttime,
                            self.alert_type["resolved"],
                            True, network_fault_params["resource_type"],
                            network_fault_params["resource_id_csm"].format(
                                          resource_id))
            LOGGER.info("Response: %s", resp)
            assert_true(resp, "Failed to get alert in CSM REST")
            LOGGER.info(
                "Step 2.2: Successfully validated csm alert response after "
                "resolving fault")

        LOGGER.info("ENDED: Verifying management network port fault and "
                    "fault-resolved scenarios")

    @pytest.mark.tags("TEST-21506")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_public_data_network_port_fault_21506(self):
        """
        EOS-21506: TA Destructive test : Automate public_data network port fault
        """
        LOGGER.info("STARTED: Verifying public_data network port fault and "
                    "fault-resolved scenarios")

        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_port_fault"]
        resource_id = self.public_data_device

        LOGGER.info("Step 1: Generating public_data network port fault")
        LOGGER.info("Step 1.1: Creating fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_PORT_FAULT,
            host_details={'host': self.mgmt_ip, 'host_user': self.uname,
                          'host_password': self.passwd},
            input_parameters={'device': self.public_data_device})
        LOGGER.info("Response: %s", resp)
        assert_true(resp[0], "{} down".format(network_fault_params["error_msg"]))
        self.public_data_fault_flag = True
        LOGGER.info("Step 1.1: Successfully created public_data network port "
                    f"fault on %s", self.host)

        wait_time = random.randint(common_params["min_wait_time"],
                                   common_params["max_wait_time"])

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 1.2: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["fault"],
                          network_fault_params["resource_id_monitor"].format(
                              resource_id)]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)

            assert_true(resp[0], resp[1])
            LOGGER.info("Step 1.2: Successfully checked generated alerts")

            LOGGER.info("Step 1.3: Validating csm alert response")
            resp = self.csm_alerts_obj.verify_csm_response(
                            self.starttime, self.alert_type["fault"],
                            False, network_fault_params["resource_type"],
                            network_fault_params["resource_id_csm"].format(
                                          resource_id))
            LOGGER.info("Response: %s", resp)
            assert_true(resp, "Failed to get alert in CSM REST")
            LOGGER.info("Step 1.3: Successfully Validated csm alert response")

        LOGGER.info("Step 2: Resolving fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_PORT_FAULT_RESOLVED,
            host_details={'host': self.mgmt_ip, 'host_user': self.uname,
                          'host_password': self.passwd},
            input_parameters={'device': self.public_data_device})
        LOGGER.info("Response: %s", resp)
        assert_true(resp[0], "{} up".format(network_fault_params["error_msg"]))
        self.public_data_fault_flag = False
        LOGGER.info("Step 2: Successfully resolved public_data network port "
                    f"fault on %s", self.host)

        wait_time = common_params["min_wait_time"]

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 2.1: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["resolved"],
                          network_fault_params["resource_id_monitor"].format(
                              resource_id)]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)
            assert_true(resp[0], resp[1])
            LOGGER.info("Step 2.1: Successfully checked generated alerts")

        LOGGER.info(
            "Step 2.2: Validating csm alert response after resolving fault")

        resp = self.csm_alerts_obj.verify_csm_response(
                        self.starttime,
                        self.alert_type["resolved"],
                        True, network_fault_params["resource_type"],
                        network_fault_params["resource_id_csm"].format(
                                      resource_id))
        LOGGER.info("Response: %s", resp)
        assert_true(resp, "Failed to get alert in CSM REST")
        LOGGER.info(
            "Step 2.2: Successfully validated csm alert response after "
            "resolving fault")

        LOGGER.info("ENDED: Verifying public data network port fault and "
                    "fault-resolved scenarios")

    @pytest.mark.skip(reason="Skipping for now as test is failing due to "
                             "EOS-21176")
    @pytest.mark.tags("TEST-21510")
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_nw_prt_flt_persistent_cache_sspl_21510(self):
        """
        EOS-21510: TA Destructive test : Test alerts in persistent cache for
        network faults - Restart SSPL
        """
        LOGGER.info("STARTED: Verifying alerts in persistent cache for network "
                    "faults when SSPL is stopped and started in between")

        service = self.cm_cfg["service"]
        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_port_fault"]
        nw_port_faults = {'mgmt_fault': {'host': self.host,
                                         'host_user': self.uname,
                                         'host_password': self.passwd,
                                         'resource_id': self.mgmt_device,
                                         'flag': self.mgmt_fault_flag},
                          'public_data_fault': {'host': self.mgmt_ip,
                                                'host_user': self.uname,
                                                'host_password': self.passwd,
                                                'resource_id': self.public_data_device,
                                                'flag': self.public_data_fault_flag}
                          }
        df = pd.DataFrame(columns=f"{list(nw_port_faults.keys())[0]} "
                                  f"{list(nw_port_faults.keys())[1]}".split(),
                          index='Step1 Step2 Step3 Step4 Step5 Step6 Step7 '
                                'Step8'.split())
        for key, value in nw_port_faults.items():
            df[key] = 'Pass'
            host = value['host']
            host_user = value['host_user']
            host_password = value['host_password']
            resource_id = value['resource_id']
            LOGGER.info("Generating %s port fault", key)
            LOGGER.info("Step 1: Creating fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_PORT_FAULT,
                host_details={'host': host, 'host_user': host_user,
                              'host_password': host_password},
                input_parameters={'device': resource_id})
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                df[key]['Step 1'] = 'Fail'
                assert_true(resp[0], "Step 1: {} down".format(network_fault_params[
                                                      "error_msg"]))
            else:
                value['flag'] = True
                LOGGER.info("Step 1: Successfully created public_data network "
                            "port fault on %s", host)

            wait_time = random.randint(common_params["min_wait_time"],
                                       common_params["max_wait_time"])

            LOGGER.info("Waiting for %s seconds", wait_time)
            time.sleep(wait_time)

            if self.start_msg_bus:
                LOGGER.info("Step 2: Checking the generated alert logs")
                alert_list = [network_fault_params["resource_type"],
                              self.alert_type["fault"],
                              network_fault_params[
                                  "resource_id_monitor"].format(resource_id)]
                LOGGER.info("RAS checks: %s", alert_list)
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    df[key]['Step2'] = 'Fail'
                    assert_true(resp[0], "Step 2:" + resp[1])
                else:
                    LOGGER.info("Step 2: Successfully checked generated alerts")

            # LOGGER.info("Step 3: Validating csm alert response")
            # resp = self.csm_alerts_obj.verify_csm_response(
            #     self.starttime, self.alert_type["fault"],
            #     False, network_fault_params["resource_type"],
            #     network_fault_params["resource_id_csm"].format(resource_id))
            # LOGGER.info("Response: %s", resp)
            # if not resp:
            #    df[key]['Step3'] = 'Fail'
            #   assert_true(resp, "Step 3: Failed to get alert in CSM REST")
            # else:
            #   LOGGER.info("Step 3: Successfully Validated csm alert response")

            LOGGER.info("Step 4: Stopping pcs resource for SSPL: %s",
                        self.sspl_resource_id)
            resp = self.health_obj.pcs_resource_ops_cmd(command="ban",
                                                        resources=[
                                                         self.sspl_resource_id],
                                                        srvnode=self.current_srvnode)
            assert_true(resp, f"Failed to ban/stop {self.sspl_resource_id} "
                              f"on node {self.current_srvnode}")
            LOGGER.info("Successfully disabled %s", self.sspl_resource_id)
            LOGGER.info("Step 4: Checking if SSPL is in stopped state.")
            resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                    services=[service[
                                                            "sspl_service"]],
                                                    decode=True, exc=False)
            if resp[0] != "inactive":
                df[key]['Step4'] = 'Fail'
                compare(resp[0], "inactive")
            else:
                LOGGER.info("Step 4: Successfully stopped SSPL service")

            LOGGER.info("Step 5: Resolving fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_PORT_FAULT_RESOLVED,
                host_details={'host': host, 'host_user': host_user,
                              'host_password': host_password},
                input_parameters={'device': resource_id})
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                df[key]['Step5'] = 'Fail'
                assert_true(resp[0], "Step 5: {} up".format(network_fault_params[
                                                    "error_msg"]))
            else:
                value['flag'] = False
                LOGGER.info("Step 5: Successfully resolved public_data network "
                            "port fault on %s", host)

            wait_time = common_params["min_wait_time"]

            LOGGER.info("Waiting for %s seconds", wait_time)
            time.sleep(wait_time)

            LOGGER.info("Step 6: Starting SSPL service")
            resp = self.health_obj.pcs_resource_ops_cmd(command="clear",
                                                        resources=[
                                                         self.sspl_resource_id],
                                                        srvnode=self.current_srvnode)
            LOGGER.info("Step 6: Checking if SSPL is in running state.")
            resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                    services=[service[
                                                                  "sspl_service"]],
                                                    decode=True, exc=False)
            if resp[0] != "active":
                df[key]['Step6'] = 'Fail'
                compare(resp[0], "active")
            else:
                LOGGER.info("Step 6: Successfully started SSPL service")

            if self.start_msg_bus:
                LOGGER.info("Step 7: Checking the generated alert logs")
                alert_list = [network_fault_params["resource_type"],
                              self.alert_type["resolved"],
                              network_fault_params[
                                  "resource_id_monitor"].format(resource_id)]
                LOGGER.info("RAS checks: %s", alert_list)
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    df[key]['Step7'] = 'Fail'
                    assert_true(resp[0], "Step 7:" + resp[1])
                else:
                    LOGGER.info("Step 7: Successfully checked generated alerts")

            LOGGER.info(
                "Step 8: Validating csm alert response after resolving fault")

            # resp = self.csm_alerts_obj.verify_csm_response(
            #     self.starttime,
            #     self.alert_type["resolved"],
            #     True, network_fault_params["resource_type"],
            #     network_fault_params["resource_id_csm"].format(resource_id))
            # LOGGER.info("Response: %s", resp)
            # if not resp:
            #     df[key]['Step8'] = 'Fail'
            #     assert_true(resp, "Step 8: Failed to get alert in CSM REST")
            # else:
            #     LOGGER.info("Step 8: Successfully validated csm alert response "
            #                 "after resolving fault")

        LOGGER.info("Summary of test: %s", df)
        result = False if 'Fail' in df.values else True
        assert_true(result, "Test failed. Please check summary for failed "
                            "step.")
        LOGGER.info("ENDED: Verifying alerts in persistent cache for network "
                    "faults when SSPL is stopped and started in between")
