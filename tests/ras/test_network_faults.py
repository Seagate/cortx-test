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

"""Test Network Faults"""

import logging
import random
import time

import pandas as pd
import pytest

from commons import commands as common_cmd
from commons import constants as cons
from commons.alerts_simulator.generate_alert_lib import AlertType
from commons.alerts_simulator.generate_alert_lib import GenerateAlertLib
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


class TestNetworkFault:
    """Network Fault Test Suite"""

    @classmethod
    def setup_class(cls):
        """Setup for module."""
        LOGGER.info("Running setup_class")
        cls.cm_cfg = RAS_VAL["ras_sspl_alert"]
        cls.node_cnt = len(CMN_CFG["nodes"])
        LOGGER.info("Total number of nodes in cluster: %s", cls.node_cnt)

        LOGGER.info("Randomly picking node to create fault")
        cls.system_random = random.SystemRandom()
        cls.test_node = cls.system_random.randint(1, cls.node_cnt)

        LOGGER.info("Fault testing will be done on node: %s", cls.test_node)
        cls.host = CMN_CFG["nodes"][cls.test_node - 1]["host"]
        cls.uname = CMN_CFG["nodes"][cls.test_node - 1]["username"]
        cls.passwd = CMN_CFG["nodes"][cls.test_node - 1]["password"]
        cls.hostname = CMN_CFG["nodes"][cls.test_node - 1]["hostname"]
        cls.public_data_ip = CMN_CFG["nodes"][cls.test_node - 1]["public_data_ip"]
        cls.mgmt_ip = CMN_CFG["nodes"][cls.test_node - 1]["ip"]
        cls.setup_type = CMN_CFG['setup_type']
        cls.sspl_resource_id = cls.cm_cfg["sspl_resource_id"]

        cls.ras_test_obj = RASTestLib(host=cls.hostname, username=cls.uname,
                                      password=cls.passwd)
        cls.node_obj = Node(hostname=cls.hostname, username=cls.uname,
                            password=cls.passwd)
        cls.health_obj = Health(hostname=cls.hostname, username=cls.uname,
                                password=cls.passwd)
        cls.alert_api_obj = GenerateAlertLib()
        cls.csm_alert_obj = SystemAlerts(cls.node_obj)

        resp = cls.ras_test_obj.get_nw_infc_names(node_num=cls.test_node-1)
        cls.nw_interfaces = resp[1] if resp[0] else assert_utils.assert_true(resp[0],
                                                                             "Failed to get network"
                                                                             " interface names")
        cls.mgmt_device = cls.nw_interfaces["MGMT"]
        cls.public_data_device = cls.nw_interfaces["PUBLIC_DATA"]
        cls.private_data_device = cls.nw_interfaces["PRIVATE_DATA"]

        # Enable this flag for starting message_bus
        cls.start_msg_bus = cls.cm_cfg["start_msg_bus"]
        cls.mgmt_fault_flag = False
        cls.public_data_fault_flag = False
        cls.mgmt_cable_fault = False
        cls.public_data_cable_fault = False

        node_d = cls.health_obj.get_current_srvnode()
        cls.current_srvnode = node_d[cls.hostname.split('.')[0]] if \
            cls.hostname.split('.')[0] in node_d.keys() else assert_utils.assert_true(
            False, "Node name not found")

        cls.csm_alerts_obj = SystemAlerts()
        cls.s3obj = S3H_OBJ
        cls.alert_type = RAS_TEST_CFG["alert_types"]

        LOGGER.info("ENDED: Successfully performed setup_class")

    def setup_method(self):
        """Setup operations per test."""
        LOGGER.info("Running setup_method")
        LOGGER.info("Checking health of cluster")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        self.starttime = time.time()
        LOGGER.info("Retaining the original/default config")
        self.ras_test_obj.retain_config(
            self.cm_cfg["file"]["original_sspl_conf"],
            False)

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
            assert_utils.assert_true(resp, "Failed to start RMQ channel")
            LOGGER.info(
                "Successfully started read_message_bus.py script on node")

        LOGGER.info("Check status of all network interfaces")
        nw_infcs = [self.nw_interfaces["MGMT"],
                    self.nw_interfaces["PUBLIC_DATA"],
                    self.nw_interfaces["PRIVATE_DATA"]]
        status = self.health_obj.check_nw_interface_status(nw_infcs=nw_infcs)
        for key, value in status.items():
            if "DOWN" in value:
                LOGGER.info("%s is down. Please check network connections and "
                            "restart tests.", key)
                assert False, f"{key} is down. Please check network connections " \
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
                    service["kafka_zookeeper"]]
        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[
                                                     self.sspl_resource_id],
                                                    srvnode=self.current_srvnode)

        time.sleep(15)
        for svc in services:
            LOGGER.info("Checking status of %s service", svc)
            resp = self.s3obj.get_s3server_service_status(service=svc,
                                                          host=self.hostname,
                                                          user=self.uname,
                                                          pwd=self.passwd)
            assert resp[0], resp[1]
            LOGGER.info("%s service is active/running", svc)

        LOGGER.info("Starting collection of sspl.log")
        res = self.ras_test_obj.sspl_log_collect()
        assert_utils.assert_true(res[0], res[1])
        LOGGER.info("Started collection of sspl logs")
        LOGGER.info("Successfully performed Setup operations")

    # pylint: disable=too-many-statements
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
                host_details={'host': self.public_data_ip, 'host_user': self.uname,
                              'host_password': self.passwd},
                input_parameters={'device': self.mgmt_device})

            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"{network_fault_params['error_msg']} up")

        if self.public_data_fault_flag:
            LOGGER.info("Resolving Public data Network port Fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_PORT_FAULT_RESOLVED,
                host_details={'host': self.mgmt_ip, 'host_user': self.uname,
                              'host_password': self.passwd},
                input_parameters={'device': self.public_data_device})
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp[0], f"{network_fault_params['error_msg']} up")

        if self.mgmt_cable_fault:
            network_cable_fault = RAS_TEST_CFG["nw_cable_fault"]
            LOGGER.info("Resolving Public data Network port Fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_CABLE_FAULT_RESOLVED,
                host_details={'host': self.hostname, 'host_user': self.uname,
                              'host_password': self.passwd},
                input_parameters={'device': self.mgmt_device,
                                  'action': network_cable_fault["connect"]})
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp[0], network_fault_params["error_msg"].format("connect"))
            LOGGER.info("Successfully resolved management network "
                        "port fault on %s", self.hostname)

        if self.public_data_cable_fault:
            network_cable_fault = RAS_TEST_CFG["nw_cable_fault"]
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_CABLE_FAULT_RESOLVED,
                host_details={'host': self.hostname, 'host_user': self.uname,
                              'host_password': self.passwd},
                input_parameters={'device': self.public_data_device,
                                  'action': network_cable_fault["connect"]})
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp[0], network_fault_params["error_msg"].format("connect"))
            self.public_data_cable_fault = False
            LOGGER.info("Step 2: Successfully resolved management network "
                        "port fault on %s", self.hostname)

        LOGGER.info("Reverting sysfs_base_path value in sspl.conf file to "
                    "/sys/")
        self.ras_test_obj.set_conf_store_vals(
            url=cons.SSPL_CFG_URL,
            encl_vals={'CONF_SYSFS_BASE_PATH': "/sys/"})

        res = self.ras_test_obj.get_conf_store_vals(url=cons.SSPL_CFG_URL,
                                                    field=cons.CONF_SYSFS_BASE_PATH)
        LOGGER.debug("Response: %s", res)

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

        resp = self.health_obj.pcs_resource_ops_cmd(command="restart",
                                                    resources=[
                                                     self.sspl_resource_id],
                                                    srvnode=self.current_srvnode)

        time.sleep(self.cm_cfg["sleep_val"])

        LOGGER.info("Checking health of cluster")
        resp = self.health_obj.check_node_health()
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("ENDED: Successfully performed the Teardown Operations")

    # pylint: disable=too-many-statements
    @pytest.mark.tags("TEST-21493")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_mgmt_network_port_fault_test_21493(self):
        """
        TEST-21493: TA Destructive test : Automate management network port
        fault and fault-resolved scenarios by making respective network
        interface down and up.
        """
        LOGGER.info("STARTED: Verifying management network port fault and "
                    "fault-resolved scenarios")

        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_port_fault"]
        resource_id = self.mgmt_device
        host_details = {'host': self.public_data_ip, 'host_user': self.uname,
                        'host_password': self.passwd}

        ras_test_obj = RASTestLib(host=host_details["host"],
                                  username=host_details["host_user"],
                                  password=host_details["host_password"])
        health_obj = Health(hostname=host_details["host"],
                            username=host_details["host_user"],
                            password=host_details["host_password"])

        # TODO: Start CRUD operations in one thread
        # TODO: Start IOs in one thread
        # TODO: Start random alert generation in one thread

        LOGGER.info("Step 1: Generating management network faults")
        LOGGER.info("Step 1.1: Creating fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_PORT_FAULT,
            host_details={'host': self.public_data_ip, 'host_user': self.uname,
                          'host_password': self.passwd},
            input_parameters={'device': self.mgmt_device})
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"{network_fault_params['error_msg']} down")
        self.mgmt_fault_flag = True
        LOGGER.info("Step 1.1: Successfully created management network "
                    "port fault on %s", self.hostname)

        wait_time = self.system_random.randint(common_params["min_wait_time"],
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
            resp = ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)

            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 1.2: Successfully checked generated alerts")

        if self.setup_type != "VM":
            LOGGER.info("Step 1.3: Validating csm alert response")
            resp = self.csm_alerts_obj.verify_csm_response(
                            self.starttime, self.alert_type["fault"],
                            False, network_fault_params["resource_type"],
                            network_fault_params["resource_id_csm"].format(
                                          resource_id))
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp, "Failed to get alert in CSM REST")
            LOGGER.info("Step 1.3: Successfully Validated csm alert response")

        LOGGER.info("Checking health of cluster")
        resp = health_obj.check_node_health()
        LOGGER.info("Response: %s", resp)
        # TODO: Revisit when information of expected response is available

        LOGGER.info("Step 2: Resolving fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_PORT_FAULT_RESOLVED,
            host_details={'host': self.public_data_ip, 'host_user': self.uname,
                          'host_password': self.passwd},
            input_parameters={'device': self.mgmt_device})
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"{network_fault_params['error_msg']} up")
        self.mgmt_fault_flag = False
        LOGGER.info("Step 2: Successfully resolved management network port fault on %s",
                    self.hostname)

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
            resp = ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
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
            assert_utils.assert_true(resp, "Failed to get alert in CSM REST")
            LOGGER.info(
                "Step 2.2: Successfully validated csm alert response after "
                "resolving fault")

        # TODO: Check status of CRUD operations
        # TODO: Check status of IOs
        # TODO: Check status of random alert generation

        LOGGER.info("ENDED: Verifying management network port fault and "
                    "fault-resolved scenarios")

    # pylint: disable=too-many-statements
    @pytest.mark.tags("TEST-21506")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_public_data_network_port_fault_21506(self):
        """
        TEST-21506: TA Destructive test : Automate public_data network port
        fault and fault-resolved scenarios by making respective network
        interface down and up.
        """
        LOGGER.info("STARTED: Verifying public_data network port fault and "
                    "fault-resolved scenarios")

        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_port_fault"]
        resource_id = self.public_data_device

        # TODO: Start CRUD operations in one thread
        # TODO: Start IOs in one thread
        # TODO: Start random alert generation in one thread

        LOGGER.info("Step 1: Generating public_data network port fault")
        LOGGER.info("Step 1.1: Creating fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_PORT_FAULT,
            host_details={'host': self.mgmt_ip, 'host_user': self.uname,
                          'host_password': self.passwd},
            input_parameters={'device': self.public_data_device})
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"{network_fault_params['error_msg']} down")
        self.public_data_fault_flag = True
        LOGGER.info("Step 1.1: Successfully created public_data network port fault on %s",
                    self.hostname)

        wait_time = self.system_random.randint(common_params["min_wait_time"],
                                               common_params["max_wait_time"])

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 1.2: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["fault"],
                          network_fault_params["resource_id_monitor"].format(
                              resource_id),
                          network_fault_params["host_id"].format(self.test_node)]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)

            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 1.2: Successfully checked generated alerts")

            LOGGER.info("Step 1.3: Validating csm alert response")
            resp = self.csm_alerts_obj.verify_csm_response(
                            self.starttime, self.alert_type["fault"],
                            False, network_fault_params["resource_type"],
                            network_fault_params["resource_id_csm"].format(
                                          resource_id),
                            network_fault_params["host_id"].format(
                              self.test_node))
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp, "Failed to get alert in CSM REST")
            LOGGER.info("Step 1.3: Successfully Validated csm alert response")

        LOGGER.info("Checking health of cluster")
        resp = self.health_obj.check_node_health()
        LOGGER.info("Response: %s", resp)
        # TODO: Revisit when information of expected response is available

        LOGGER.info("Step 2: Resolving fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_PORT_FAULT_RESOLVED,
            host_details={'host': self.mgmt_ip, 'host_user': self.uname,
                          'host_password': self.passwd},
            input_parameters={'device': self.public_data_device})
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp[0], f"{network_fault_params['error_msg']} up")
        self.public_data_fault_flag = False
        LOGGER.info("Step 2: Successfully resolved public_data network port fault on %s",
                    self.hostname)

        wait_time = common_params["min_wait_time"]

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 2.1: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["resolved"],
                          network_fault_params["resource_id_monitor"].format(
                              resource_id),
                          network_fault_params["host_id"].format(self.test_node)]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 2.1: Successfully checked generated alerts")

        LOGGER.info(
            "Step 2.2: Validating csm alert response after resolving fault")

        resp = self.csm_alerts_obj.verify_csm_response(
                        self.starttime,
                        self.alert_type["resolved"],
                        True, network_fault_params["resource_type"],
                        network_fault_params["resource_id_csm"].format(
                                      resource_id),
                        network_fault_params["host_id"].format(self.test_node))
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp, "Failed to get alert in CSM REST")
        LOGGER.info(
            "Step 2.2: Successfully validated csm alert response after "
            "resolving fault")

        # TODO: Check status of CRUD operations
        # TODO: Check status of IOs
        # TODO: Check status of random alert generation

        LOGGER.info("ENDED: Verifying public data network port fault and "
                    "fault-resolved scenarios")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-branches
    @pytest.mark.tags("TEST-21510")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_nw_prt_flt_persistent_cache_sspl_21510(self):
        """
        TEST-21510: TA Destructive test : Test network alert persistency across
        stop and start sspl-ll.
        """
        LOGGER.info("STARTED: Verifying alerts in persistent cache for network "
                    "faults when SSPL is stopped and started in between")
        service = self.cm_cfg["service"]
        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_port_fault"]

        nw_port_faults = {'mgmt_fault': {'host': self.public_data_ip,
                                         'host_user': self.uname,
                                         'host_password': self.passwd,
                                         'resource_id': self.mgmt_device,
                                         'flag': self.mgmt_fault_flag},
                          'public_data_fault': {'host': self.mgmt_ip,
                                                'host_user': self.uname,
                                                'host_password': self.passwd,
                                                'resource_id': self.public_data_device,
                                                'flag':
                                                    self.public_data_fault_flag}
                          }
        d_f = pd.DataFrame(columns=f"{list(nw_port_faults.keys())[0]} "
                                   f"{list(nw_port_faults.keys())[1]}".split(),
                           index='Step1 Step2 Step3 Step4 Step5 Step6 Step7 '
                                 'Step8 Step9 Step10'.split())
        for key, value in nw_port_faults.items():
            d_f[key] = 'Pass'
            host = value['host']
            host_user = value['host_user']
            host_password = value['host_password']

            ras_test_obj = RASTestLib(host=host, username=host_user,
                                      password=host_password)
            health_obj = Health(hostname=host, username=host_user,
                                password=host_password)
            node_obj = Node(hostname=host, username=host_user,
                            password=host_password)

            resource_id = value['resource_id']
            LOGGER.info("Generating %s port fault", key)
            LOGGER.info("Step 1: Stopping pcs resource for SSPL: %s",
                        self.sspl_resource_id)
            resp = health_obj.pcs_resource_ops_cmd(command="ban",
                                                   resources=[
                                                         self.sspl_resource_id],
                                                   srvnode=self.current_srvnode)
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Successfully disabled %s", self.sspl_resource_id)
            LOGGER.info("Step 1: Checking if SSPL is in stopped state.")
            resp = node_obj.send_systemctl_cmd(command="is-active",
                                               services=[service["sspl_service"]],
                                               decode=True, exc=False)
            if resp[0] != "inactive":
                d_f[key]['Step1'] = 'Fail'
                assert_utils.compare(resp[0], "inactive")
            else:
                LOGGER.info("Step 1: Successfully stopped SSPL service")

            LOGGER.info("Step 2: Creating fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_PORT_FAULT,
                host_details={'host': host, 'host_user': host_user,
                              'host_password': host_password},
                input_parameters={'device': resource_id})
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                d_f[key]['Step2'] = 'Fail'
                LOGGER.error("Step 2: Failed to create fault %s", key)
            else:
                value['flag'] = True
                LOGGER.info("Step 2: Successfully created %s "
                            "port fault on %s", key, host)

            LOGGER.info("Step 3: Starting SSPL service")
            resp = health_obj.pcs_resource_ops_cmd(command="clear",
                                                   resources=[
                                                         self.sspl_resource_id],
                                                   srvnode=self.current_srvnode)
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Step 3: Checking if SSPL is in running state.")
            resp = node_obj.send_systemctl_cmd(command="is-active",
                                               services=[service["sspl_service"]],
                                               decode=True, exc=False)
            if resp[0] != "active":
                d_f[key]['Step3'] = 'Fail'
                assert_utils.compare(resp[0], "active")
            else:
                LOGGER.info("Step 3: Successfully started SSPL service")

            wait_time = self.system_random.randint(common_params["min_wait_time"],
                                                   common_params["max_wait_time"])

            LOGGER.info("Waiting for %s seconds", wait_time)
            time.sleep(wait_time)

            if self.start_msg_bus:
                LOGGER.info("Step 4: Checking the generated alert logs")
                alert_list = [network_fault_params["resource_type"],
                              self.alert_type["fault"],
                              network_fault_params[
                                  "resource_id_monitor"].format(resource_id)]
                LOGGER.info("RAS checks: %s", alert_list)
                resp = ras_test_obj.list_alert_validation(alert_list)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    d_f[key]['Step4'] = 'Fail'
                    LOGGER.error("Step 4: %s", resp[1])
                else:
                    LOGGER.info("Step 4: Successfully checked generated alerts")

            if key != 'mgmt_fault' or self.setup_type != 'VM':
                LOGGER.info("Step 5: Validating csm alert response")
                resp = self.csm_alerts_obj.verify_csm_response(
                    self.starttime, self.alert_type["fault"],
                    False, network_fault_params["resource_type"],
                    network_fault_params["resource_id_csm"].format(
                        resource_id))
                LOGGER.info("Response: %s", resp)
                if not resp:
                    d_f[key]['Step5'] = 'Fail'
                    LOGGER.error("Step 5: Failed to get alert in CSM REST")
                else:
                    LOGGER.info("Step 5: Successfully Validated csm alert "
                                "response")

            LOGGER.info("Step 6: Stopping pcs resource for SSPL: %s",
                        self.sspl_resource_id)
            resp = health_obj.pcs_resource_ops_cmd(command="ban",
                                                   resources=[
                                                         self.sspl_resource_id],
                                                   srvnode=self.current_srvnode)
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Successfully disabled %s", self.sspl_resource_id)
            LOGGER.info("Step 6: Checking if SSPL is in stopped state.")
            resp = node_obj.send_systemctl_cmd(command="is-active",
                                               services=[service[
                                                         "sspl_service"]],
                                               decode=True, exc=False)
            if resp[0] != "inactive":
                d_f[key]['Step6'] = 'Fail'
                assert_utils.compare(resp[0], "inactive")
            else:
                LOGGER.info("Step 6: Successfully stopped SSPL service")

            LOGGER.info("Step 7: Resolving fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_PORT_FAULT_RESOLVED,
                host_details={'host': host, 'host_user': host_user,
                              'host_password': host_password},
                input_parameters={'device': resource_id})
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                d_f[key]['Step7'] = 'Fail'
                LOGGER.error("Step 7: %s up", network_fault_params["error_msg"])
            else:
                value['flag'] = False
                LOGGER.info("Step 7: Successfully resolved %s "
                            "port fault on %s", key, host)

            LOGGER.info("Step 8: Starting SSPL service")
            resp = health_obj.pcs_resource_ops_cmd(command="clear",
                                                   resources=[
                                                         self.sspl_resource_id],
                                                   srvnode=self.current_srvnode)
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Step 8: Checking if SSPL is in running state.")
            resp = node_obj.send_systemctl_cmd(command="is-active",
                                               services=[service[
                                                               "sspl_service"]],
                                               decode=True, exc=False)
            if resp[0] != "active":
                d_f[key]['Step8'] = 'Fail'
                assert_utils.compare(resp[0], "active")
            else:
                LOGGER.info("Step 8: Successfully started SSPL service")

            wait_time = common_params["min_wait_time"]

            LOGGER.info("Waiting for %s seconds", wait_time)
            time.sleep(wait_time)

            if self.start_msg_bus:
                LOGGER.info("Step 9: Checking the generated alert logs")
                alert_list = [network_fault_params["resource_type"],
                              self.alert_type["resolved"],
                              network_fault_params[
                                  "resource_id_monitor"].format(resource_id)]
                LOGGER.info("RAS checks: %s", alert_list)
                resp = ras_test_obj.list_alert_validation(alert_list)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    d_f[key]['Step9'] = 'Fail'
                    LOGGER.error("Step 9: %s", resp[1])
                else:
                    LOGGER.info("Step 9: Successfully checked generated alerts")

            LOGGER.info(
                "Step 10: Validating csm alert response after resolving fault")

            if key != 'mgmt_fault' or self.setup_type != 'VM':
                resp = self.csm_alerts_obj.verify_csm_response(
                    self.starttime,
                    self.alert_type["resolved"],
                    True, network_fault_params["resource_type"],
                    network_fault_params["resource_id_csm"].format(
                        resource_id))
                LOGGER.info("Response: %s", resp)
                if not resp:
                    d_f[key]['Step10'] = 'Fail'
                    LOGGER.error("Step 10: Failed to get alert in CSM "
                                 "REST")
                else:
                    LOGGER.info("Step 10: Successfully validated csm alert "
                                "response after resolving fault")

        LOGGER.info("Summary of test: \n%s", d_f)
        result = False if 'Fail' in d_f.values else True
        assert_utils.assert_true(result, "Test failed. Please check summary for failed "
                                         "step.")
        LOGGER.info("ENDED: Verifying alerts in persistent cache for network "
                    "faults when SSPL is stopped and started in between")

    # pylint: disable=too-many-statements
    @pytest.mark.tags("TEST-21507")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_mgmt_nw_cable_faults_21507(self):
        """
        TEST-21507: Test alerts when management network cable is
        disconnected and connected.
        """
        LOGGER.info("STARTED: Verifying alerts when management network cable is"
                    " disconnected/connected")
        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_cable_fault"]
        resource_id = self.mgmt_device
        host_id = network_fault_params["host_id"].format(self.test_node)

        # TODO: Start CRUD operations in one thread
        # TODO: Start IOs in one thread
        # TODO: Start random alert generation in one thread

        LOGGER.info("Step 1: Generating management cable faults")
        LOGGER.info("Step 1.1: Creating fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_CABLE_FAULT,
            host_details={'host': self.hostname, 'host_user': self.uname,
                          'host_password': self.passwd},
            input_parameters={'device': self.mgmt_device, 'action':
                              network_fault_params["disconnect"]})
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp[0], network_fault_params["error_msg"].format("disconnect"))
        self.mgmt_cable_fault = True
        LOGGER.info("Step 1.1: Successfully created management network "
                    "port fault on %s", self.hostname)

        wait_time = self.system_random.randint(common_params["min_wait_time"],
                                               common_params["max_wait_time"])

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 1.2: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["fault"],
                          network_fault_params["resource_id_monitor"].format(
                              resource_id), host_id]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)

            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 1.2: Successfully checked generated alerts")

        LOGGER.info("Step 1.3: Validating csm alert response")
        resp = self.csm_alerts_obj.verify_csm_response(
            self.starttime, self.alert_type["fault"],
            False, network_fault_params["resource_type"],
            network_fault_params["resource_id_csm"].format(
                resource_id), host_id)
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp, "Failed to get alert in CSM REST")
        LOGGER.info("Step 1.3: Successfully Validated csm alert response")

        LOGGER.info("Checking health of cluster")
        resp = self.health_obj.check_node_health()
        LOGGER.info("Response: %s", resp)
        # TODO: Revisit when information of expected response is available

        LOGGER.info("Step 2: Resolving fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_CABLE_FAULT_RESOLVED,
            host_details={'host': self.hostname, 'host_user': self.uname,
                          'host_password': self.passwd},
            input_parameters={'device': self.mgmt_device,
                              'action': network_fault_params["connect"]})
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp[0], network_fault_params["error_msg"].format("connect"))
        self.mgmt_cable_fault = False
        LOGGER.info("Step 2: Successfully resolved management network "
                    "port fault on %s", self.hostname)

        wait_time = common_params["min_wait_time"]

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 2.1: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["resolved"],
                          network_fault_params["resource_id_monitor"].format(
                          resource_id), host_id]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 2.1: Successfully checked generated alerts")

        LOGGER.info(
            "Step 2.2: Validating csm alert response after resolving fault")

        resp = self.csm_alerts_obj.verify_csm_response(
            self.starttime,
            self.alert_type["resolved"],
            True, network_fault_params["resource_type"],
            network_fault_params["resource_id_csm"].format(
                resource_id), host_id)
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp, "Failed to get alert in CSM REST")
        LOGGER.info(
            "Step 2.2: Successfully validated csm alert response after "
            "resolving fault")

        # TODO: Check status of CRUD operations
        # TODO: Check status of IOs
        # TODO: Check status of random alert generation

        LOGGER.info("ENDED: Verifying alerts when management network cable is"
                    " disconnected/connected")

    # pylint: disable=too-many-statements
    @pytest.mark.tags("TEST-21508")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_public_data_nw_cable_faults_21508(self):
        """
        TEST-21508: Test alerts when public data network cable is
        disconnected and connected.
        """
        LOGGER.info("STARTED: Verifying alerts when public data network cable "
                    "is disconnected/connected")
        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_cable_fault"]
        resource_id = self.public_data_device
        host_id = network_fault_params["host_id"].format(self.test_node)

        # TODO: Start CRUD operations in one thread
        # TODO: Start IOs in one thread
        # TODO: Start random alert generation in one thread

        LOGGER.info("Step 1: Generating public data cable faults")
        LOGGER.info("Step 1.1: Creating fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_CABLE_FAULT,
            host_details={'host': self.hostname, 'host_user': self.uname,
                          'host_password': self.passwd},
            input_parameters={'device': self.public_data_device,
                              'action': network_fault_params["disconnect"]})
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp[0], network_fault_params["error_msg"].format("disconnect"))
        self.public_data_cable_fault = True
        LOGGER.info("Step 1.1: Successfully created public data cable "
                    "fault on %s", self.hostname)

        wait_time = self.system_random.randint(common_params["min_wait_time"],
                                               common_params["max_wait_time"])

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 1.2: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["fault"],
                          network_fault_params["resource_id_monitor"].format(
                              resource_id), host_id]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)

            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 1.2: Successfully checked generated alerts")

        LOGGER.info("Step 1.3: Validating csm alert response")
        resp = self.csm_alerts_obj.verify_csm_response(
            self.starttime, self.alert_type["fault"],
            False, network_fault_params["resource_type"],
            network_fault_params["resource_id_csm"].format(
                resource_id), host_id)
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp, "Failed to get alert in CSM REST")
        LOGGER.info("Step 1.3: Successfully Validated csm alert response")

        LOGGER.info("Checking health of cluster")
        resp = self.health_obj.check_node_health()
        LOGGER.info("Response: %s", resp)
        # TODO: Revisit when information of expected response is available

        LOGGER.info("Step 2: Resolving fault")
        resp = self.alert_api_obj.generate_alert(
            AlertType.NW_CABLE_FAULT_RESOLVED,
            host_details={'host': self.hostname, 'host_user': self.uname,
                          'host_password': self.passwd},
            input_parameters={'device': self.public_data_device,
                              'action': network_fault_params["connect"]})
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp[0], network_fault_params["error_msg"].format("connect"))
        self.public_data_cable_fault = False
        LOGGER.info("Step 2: Successfully resolved public data cable "
                    "fault on %s", self.hostname)

        wait_time = common_params["min_wait_time"]

        LOGGER.info("Waiting for %s seconds", wait_time)
        time.sleep(wait_time)

        if self.start_msg_bus:
            LOGGER.info("Step 2.1: Checking the generated alert logs")
            alert_list = [network_fault_params["resource_type"],
                          self.alert_type["resolved"],
                          network_fault_params["resource_id_monitor"].format(
                              resource_id), host_id]
            LOGGER.info("RAS checks: %s", alert_list)
            resp = self.ras_test_obj.list_alert_validation(alert_list)
            LOGGER.info("Response: %s", resp)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 2.1: Successfully checked generated alerts")

        LOGGER.info(
            "Step 2.2: Validating csm alert response after resolving fault")

        resp = self.csm_alerts_obj.verify_csm_response(
            self.starttime,
            self.alert_type["resolved"],
            True, network_fault_params["resource_type"],
            network_fault_params["resource_id_csm"].format(
                resource_id), host_id)
        LOGGER.info("Response: %s", resp)
        assert_utils.assert_true(resp, "Failed to get alert in CSM REST")
        LOGGER.info(
            "Step 2.2: Successfully validated csm alert response after "
            "resolving fault")

        # TODO: Check status of CRUD operations
        # TODO: Check status of IOs
        # TODO: Check status of random alert generation

        LOGGER.info("ENDED: Verifying alerts when public data network cable is"
                    " disconnected/connected")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-branches
    @pytest.mark.tags("TEST-21509")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_nw_prt_flt_persistent_cache_node_reboot_21509(self):
        """
        TEST-21509: TA Destructive test : Test network alerts are persistent
        across node reboot.
        """
        LOGGER.info("STARTED: Verifying alerts in persistent cache for network "
                    "faults across node reboot")
        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_port_fault"]
        nw_port_faults = {'mgmt_fault': {'host': self.public_data_ip,
                                         'host_user': self.uname,
                                         'host_password': self.passwd,
                                         'resource_id': self.mgmt_device,
                                         'flag': self.mgmt_fault_flag},
                          'public_data_fault': {'host': self.mgmt_ip,
                                                'host_user': self.uname,
                                                'host_password': self.passwd,
                                                'resource_id': self.public_data_device,
                                                'flag':
                                                    self.public_data_fault_flag}
                          }
        d_f = pd.DataFrame(columns=f"{list(nw_port_faults.keys())[0]} "
                                   f"{list(nw_port_faults.keys())[1]}".split(),
                           index='Step1 Step2 Step3 Step4 Step5 Step6 Step7'.split())
        for key, value in nw_port_faults.items():
            d_f[key] = 'Pass'
            host = value['host']
            host_user = value['host_user']
            host_password = value['host_password']

            ras_test_obj = RASTestLib(host=host, username=host_user,
                                      password=host_password)
            health_obj = Health(hostname=host, username=host_user,
                                password=host_password)
            node_obj = Node(hostname=host, username=host_user,
                            password=host_password)

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
                d_f[key]['Step1'] = 'Fail'
                LOGGER.error(
                            "Step 1: %s down", network_fault_params["error_msg"])
            else:
                value['flag'] = True
                LOGGER.info("Step 1: Successfully created %s "
                            "port fault on %s", key, host)

            wait_time = self.system_random.randint(common_params["min_wait_time"],
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
                resp = ras_test_obj.list_alert_validation(alert_list)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    d_f[key]['Step2'] = 'Fail'
                    LOGGER.error("Step 2: %s", resp[1])
                else:
                    LOGGER.info("Step 2: Successfully checked generated alerts")

            if key != 'mgmt_fault' or self.setup_type != 'VM':
                LOGGER.info("Step 3: Validating csm alert response")
                resp = self.csm_alerts_obj.verify_csm_response(
                    self.starttime, self.alert_type["fault"],
                    False, network_fault_params["resource_type"],
                    network_fault_params["resource_id_csm"].format(
                        resource_id))
                LOGGER.info("Response: %s", resp)
                if not resp:
                    d_f[key]['Step3'] = 'Fail'
                    LOGGER.error("Step 3: Failed to get alert in CSM REST")
                else:
                    LOGGER.info("Step 3: Successfully Validated csm alert "
                                "response")

            LOGGER.info("Step 4: Rebooting node %s ", self.hostname)
            resp = node_obj.execute_cmd(cmd=common_cmd.REBOOT_NODE_CMD,
                                        read_lines=True, exc=False)
            LOGGER.info(
                "Step 4: Rebooted node: %s, Response: %s", self.hostname, resp)
            time.sleep(self.cm_cfg["reboot_delay"])

            LOGGER.info("Step 4: Performing health check after node reboot")
            resp = health_obj.check_node_health()
            LOGGER.info("Step 4: Response: %s", resp)

            LOGGER.info("Step 5: Resolving fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_PORT_FAULT_RESOLVED,
                host_details={'host': host, 'host_user': host_user,
                              'host_password': host_password},
                input_parameters={'device': resource_id})
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                d_f[key]['Step5'] = 'Fail'
                LOGGER.error(
                            "Step 5: %s up", network_fault_params["error_msg"])
            else:
                value['flag'] = False
                LOGGER.info("Step 5: Successfully resolved %s "
                            "port fault on %s", key, host)

            wait_time = common_params["min_wait_time"]

            LOGGER.info("Waiting for %s seconds", wait_time)
            time.sleep(wait_time)

            if self.start_msg_bus:
                LOGGER.info("Step 6: Checking the generated alert logs")
                alert_list = [network_fault_params["resource_type"],
                              self.alert_type["resolved"],
                              network_fault_params[
                                  "resource_id_monitor"].format(resource_id)]
                LOGGER.info("RAS checks: %s", alert_list)
                resp = ras_test_obj.list_alert_validation(alert_list)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    d_f[key]['Step6'] = 'Fail'
                    LOGGER.error("Step 6: %s", resp[1])
                else:
                    LOGGER.info("Step 6: Successfully checked generated alerts")

            LOGGER.info(
                "Step 7: Validating csm alert response after resolving fault")

            if key != 'mgmt_fault' or self.setup_type != 'VM':
                resp = self.csm_alerts_obj.verify_csm_response(
                    self.starttime,
                    self.alert_type["resolved"],
                    True, network_fault_params["resource_type"],
                    network_fault_params["resource_id_csm"].format(
                        resource_id))
                LOGGER.info("Response: %s", resp)
                if not resp:
                    d_f[key]['Step7'] = 'Fail'
                    LOGGER.error("Step 7: Failed to get alert in CSM REST")
                else:
                    LOGGER.info(
                        "Step 7: Successfully validated csm alert response "
                        "after resolving fault")

        LOGGER.info("Summary of test: \n%s", d_f)
        result = False if 'Fail' in d_f.values else True
        assert_utils.assert_true(result, "Test failed. Please check summary for failed "
                                         "step.")
        LOGGER.info("ENDED: Verifying alerts in persistent cache for network "
                    "faults when SSPL is stopped and started in between")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-branches
    @pytest.mark.tags("TEST-25292")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_nw_cable_flt_persistent_cache_node_reboot_25292(self):
        """
        TEST-25292: TA Destructive test : Test network cable alert persistency
        across node reboot.
        """
        LOGGER.info("STARTED: Verifying alerts in persistent cache for network "
                    "cable faults across node reboot")
        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_cable_fault"]
        host_details = {'host': self.hostname, 'host_user': self.uname,
                        'host_password': self.passwd}
        create_fault = network_fault_params["disconnect"]
        resolve_fault = network_fault_params["connect"]
        host_id = network_fault_params["host_id"].format(self.test_node)
        nw_cable_faults = {'mgmt_cable_fault': {'device': self.mgmt_device,
                                                'flag': self.mgmt_cable_fault},
                           'public_data_cable_fault': {
                               'device': self.public_data_device,
                               'flag': self.public_data_fault_flag}}

        d_f = pd.DataFrame(columns=f"{list(nw_cable_faults.keys())[0]} "
                                   f"{list(nw_cable_faults.keys())[1]}".split(),
                           index='Step1 Step2 Step3 Step4 Step5 Step6 Step7'.split())
        for key, value in nw_cable_faults.items():
            d_f[key] = 'Pass'
            resource_id = value['device']
            LOGGER.info("Generating %s fault", key)
            LOGGER.info("Step 1: Creating fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_CABLE_FAULT,
                host_details=host_details,
                input_parameters={'device': resource_id,
                                  'action': create_fault})
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                d_f[key]['Step1'] = 'Fail'
                LOGGER.error(
                            "Step 1: %s down", network_fault_params["error_msg"])
            else:
                value['flag'] = True
                LOGGER.info("Step 1: Successfully created %s "
                            "port fault on %s", key, self.hostname)

            wait_time = self.system_random.randint(common_params["min_wait_time"],
                                                   common_params["max_wait_time"])

            LOGGER.info("Waiting for %s seconds", wait_time)
            time.sleep(wait_time)

            if self.start_msg_bus:
                LOGGER.info("Step 2: Checking the generated alert logs")
                alert_list = [network_fault_params["resource_type"],
                              self.alert_type["fault"],
                              network_fault_params[
                                  "resource_id_monitor"].format(resource_id),
                              host_id]
                LOGGER.info("RAS checks: %s", alert_list)
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    d_f[key]['Step2'] = 'Fail'
                    LOGGER.error("Step 2: %s", resp[1])
                else:
                    LOGGER.info("Step 2: Successfully checked generated alerts")

            LOGGER.info("Step 3: Validating csm alert response")
            resp = self.csm_alerts_obj.verify_csm_response(
                   self.starttime, self.alert_type["fault"],
                   False, network_fault_params["resource_type"],
                   network_fault_params["resource_id_csm"].format(
                       resource_id), host_id)
            LOGGER.info("Response: %s", resp)
            if not resp:
                d_f[key]['Step3'] = 'Fail'
                LOGGER.error("Step 3: Failed to get alert in CSM REST")
            else:
                LOGGER.info("Step 3: Successfully Validated csm alert "
                            "response")

            LOGGER.info("Step 4: Rebooting node %s ", self.hostname)
            resp = self.node_obj.execute_cmd(cmd=common_cmd.REBOOT_NODE_CMD,
                                             read_lines=True, exc=False)
            LOGGER.info(
                "Step 4: Rebooted node: %s, Response: %s", self.hostname, resp)
            time.sleep(self.cm_cfg["reboot_delay"])

            LOGGER.info("Step 4: Performing health check after node reboot")
            resp = self.health_obj.check_node_health()
            LOGGER.info("Step 4: Response: %s", resp)

            LOGGER.info("Step 5: Resolving fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_CABLE_FAULT,
                host_details=host_details,
                input_parameters={'device': resource_id,
                                  'action': resolve_fault})
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                d_f[key]['Step5'] = 'Fail'
                LOGGER.error(
                            "Step 5: %s up", network_fault_params["error_msg"])
            else:
                value['flag'] = False
                LOGGER.info("Step 5: Successfully resolved %s "
                            "port fault on %s", key, self.hostname)

            wait_time = common_params["min_wait_time"]

            LOGGER.info("Waiting for %s seconds", wait_time)
            time.sleep(wait_time)

            if self.start_msg_bus:
                LOGGER.info("Step 6: Checking the generated alert logs")
                alert_list = [network_fault_params["resource_type"],
                              self.alert_type["resolved"],
                              network_fault_params[
                                  "resource_id_monitor"].format(resource_id),
                              host_id]
                LOGGER.info("RAS checks: %s", alert_list)
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    d_f[key]['Step6'] = 'Fail'
                    LOGGER.error("Step 6: %s", resp[1])
                else:
                    LOGGER.info("Step 6: Successfully checked generated alerts")

            LOGGER.info(
                "Step 7: Validating csm alert response after resolving fault")

            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime,
                self.alert_type["resolved"],
                True, network_fault_params["resource_type"],
                network_fault_params["resource_id_csm"].format(resource_id),
                host_id)
            LOGGER.info("Response: %s", resp)
            if not resp:
                d_f[key]['Step7'] = 'Fail'
                LOGGER.error("Step 7: Failed to get alert in CSM "
                             "REST")
            else:
                LOGGER.info("Step 7: Successfully validated csm alert "
                            "response after resolving fault")

        LOGGER.info("Summary of test: \n%s", d_f)
        result = False if 'Fail' in d_f.values else True
        assert_utils.assert_true(result, "Test failed. Please check summary for failed "
                                         "step.")
        LOGGER.info("ENDED: Verifying alerts in persistent cache for network "
                    "faults when SSPL is stopped and started in between")

    # pylint: disable=too-many-statements
    # pylint: disable-msg=too-many-locals
    # pylint: disable-msg=too-many-branches
    @pytest.mark.tags("TEST-25293")
    @pytest.mark.lr
    @pytest.mark.cluster_monitor_ops
    @pytest.mark.sw_alert
    def test_nw_cable_flt_persistent_cache_sspl_25293(self):
        """
        TEST-25293: TA Destructive test : Test network cable alert persistency
        across stop and start sspl-ll.
        """
        LOGGER.info("STARTED: Verifying alerts in persistent cache for network "
                    "cable faults when SSPL is stopped and started in between")
        service = self.cm_cfg["service"]
        common_params = RAS_VAL["nw_fault_params"]
        network_fault_params = RAS_TEST_CFG["nw_cable_fault"]
        host_details = {'host': self.hostname, 'host_user': self.uname,
                        'host_password': self.passwd}
        create_fault = network_fault_params["disconnect"]
        resolve_fault = network_fault_params["connect"]
        host_id = network_fault_params["host_id"].format(self.test_node)
        nw_cable_faults = {'mgmt_cable_fault': {'device': self.mgmt_device,
                                                'flag': self.mgmt_cable_fault},
                           'public_data_cable_fault': {
                              'device': self.public_data_device,
                              'flag': self.public_data_fault_flag}}

        d_f = pd.DataFrame(columns=f"{list(nw_cable_faults.keys())[0]} "
                                   f"{list(nw_cable_faults.keys())[1]}".split(),
                           index='Step1 Step2 Step3 Step4 Step5 Step6 Step7 '
                                 'Step8 Step9 Step10'.split())
        for key, value in nw_cable_faults.items():
            d_f[key] = 'Pass'
            resource_id = value['device']
            LOGGER.info("Generating %s port fault", key)
            LOGGER.info("Step 1: Stopping pcs resource for SSPL: %s",
                        self.sspl_resource_id)
            resp = self.health_obj.pcs_resource_ops_cmd(command="ban",
                                                        resources=[
                                                            self.sspl_resource_id],
                                                        srvnode=self.current_srvnode)
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Successfully disabled %s", self.sspl_resource_id)
            LOGGER.info("Step 1: Checking if SSPL is in stopped state.")
            resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                    services=[service[
                                                                  "sspl_service"]],
                                                    decode=True, exc=False)
            if resp[0] != "inactive":
                d_f[key]['Step1'] = 'Fail'
                assert_utils.compare(resp[0], "inactive")
            else:
                LOGGER.info("Step 1: Successfully stopped SSPL service")

            LOGGER.info("Step 2: Creating fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_CABLE_FAULT,
                host_details=host_details,
                input_parameters={'device': resource_id,
                                  'action': create_fault})
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                d_f[key]['Step2'] = 'Fail'
                LOGGER.error(
                            "Step 2: %s down", network_fault_params["error_msg"])
            else:
                value['flag'] = True
                LOGGER.info("Step 2: Successfully created %s "
                            "port fault on %s", key, self.hostname)

            LOGGER.info("Step 3: Starting SSPL service")
            resp = self.health_obj.pcs_resource_ops_cmd(command="clear",
                                                        resources=[
                                                            self.sspl_resource_id],
                                                        srvnode=self.current_srvnode)
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Step 3: Checking if SSPL is in running state.")
            resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                    services=[service[
                                                                  "sspl_service"]],
                                                    decode=True, exc=False)
            if resp[0] != "active":
                d_f[key]['Step3'] = 'Fail'
                assert_utils.compare(resp[0], "active")
            else:
                LOGGER.info("Step 3: Successfully started SSPL service")

            wait_time = self.system_random.randint(common_params["min_wait_time"],
                                                   common_params["max_wait_time"])

            LOGGER.info("Waiting for %s seconds", wait_time)
            time.sleep(wait_time)

            if self.start_msg_bus:
                LOGGER.info("Step 4: Checking the generated alert logs")
                alert_list = [network_fault_params["resource_type"],
                              self.alert_type["fault"],
                              network_fault_params[
                                  "resource_id_monitor"].format(resource_id),
                              host_id]
                LOGGER.info("RAS checks: %s", alert_list)
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    d_f[key]['Step4'] = 'Fail'
                    LOGGER.error("Step 4: %s", resp[1])
                else:
                    LOGGER.info("Step 4: Successfully checked generated alerts")

            LOGGER.info("Step 5: Validating csm alert response")
            resp = self.csm_alerts_obj.verify_csm_response(
                   self.starttime, self.alert_type["fault"],
                   False, network_fault_params["resource_type"],
                   network_fault_params["resource_id_csm"].format(
                       resource_id), host_id)
            LOGGER.info("Response: %s", resp)
            if not resp:
                d_f[key]['Step5'] = 'Fail'
                LOGGER.error("Step 5: Failed to get alert in CSM REST")
            else:
                LOGGER.info("Step 5: Successfully Validated csm alert "
                            "response")

            LOGGER.info("Step 6: Stopping pcs resource for SSPL: %s",
                        self.sspl_resource_id)
            resp = self.health_obj.pcs_resource_ops_cmd(command="ban",
                                                        resources=[
                                                            self.sspl_resource_id],
                                                        srvnode=self.current_srvnode)
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Successfully disabled %s", self.sspl_resource_id)
            LOGGER.info("Step 6: Checking if SSPL is in stopped state.")
            resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                    services=[service[
                                                                  "sspl_service"]],
                                                    decode=True, exc=False)
            if resp[0] != "inactive":
                d_f[key]['Step6'] = 'Fail'
                assert_utils.compare(resp[0], "inactive")
            else:
                LOGGER.info("Step 6: Successfully stopped SSPL service")

            LOGGER.info("Step 7: Resolving fault")
            resp = self.alert_api_obj.generate_alert(
                AlertType.NW_CABLE_FAULT,
                host_details=host_details,
                input_parameters={'device': resource_id,
                                  'action': resolve_fault})
            LOGGER.info("Response: %s", resp)
            if not resp[0]:
                d_f[key]['Step7'] = 'Fail'
                LOGGER.error(
                            "Step 7: %s up", network_fault_params["error_msg"])
            else:
                value['flag'] = False
                LOGGER.info("Step 7: Successfully resolved %s "
                            "port fault on %s", key, self.hostname)

            LOGGER.info("Step 8: Starting SSPL service")
            resp = self.health_obj.pcs_resource_ops_cmd(command="clear",
                                                        resources=[
                                                            self.sspl_resource_id],
                                                        srvnode=self.current_srvnode)
            LOGGER.info("Response: %s", resp)
            LOGGER.info("Step 8: Checking if SSPL is in running state.")
            resp = self.node_obj.send_systemctl_cmd(command="is-active",
                                                    services=[service[
                                                                  "sspl_service"]],
                                                    decode=True, exc=False)
            if resp[0] != "active":
                d_f[key]['Step8'] = 'Fail'
                assert_utils.compare(resp[0], "active")
            else:
                LOGGER.info("Step 8: Successfully started SSPL service")

            wait_time = common_params["min_wait_time"]

            LOGGER.info("Waiting for %s seconds", wait_time)
            time.sleep(wait_time)

            if self.start_msg_bus:
                LOGGER.info("Step 9: Checking the generated alert logs")
                alert_list = [network_fault_params["resource_type"],
                              self.alert_type["resolved"],
                              network_fault_params[
                                  "resource_id_monitor"].format(resource_id),
                              host_id]
                LOGGER.info("RAS checks: %s", alert_list)
                resp = self.ras_test_obj.list_alert_validation(alert_list)
                LOGGER.info("Response: %s", resp)
                if not resp[0]:
                    d_f[key]['Step9'] = 'Fail'
                    LOGGER.error("Step 9: %s", resp[1])
                else:
                    LOGGER.info("Step 9: Successfully checked generated alerts")

            LOGGER.info(
                "Step 10: Validating csm alert response after resolving fault")

            resp = self.csm_alerts_obj.verify_csm_response(
                   self.starttime,
                   self.alert_type["resolved"],
                   True, network_fault_params["resource_type"],
                   network_fault_params["resource_id_csm"].format(
                       resource_id), host_id)
            LOGGER.info("Response: %s", resp)
            if not resp:
                d_f[key]['Step10'] = 'Fail'
                LOGGER.error("Step 10: Failed to get alert in CSM "
                             "REST")
            else:
                LOGGER.info("Step 10: Successfully validated csm alert "
                            "response after resolving fault")

        LOGGER.info("Summary of test: \n%s", d_f)
        result = False if 'Fail' in d_f.values else True
        assert_utils.assert_true(result, "Test failed. Please check summary for failed "
                                         "step.")
        LOGGER.info("ENDED: Verifying alerts in persistent cache for network "
                    "faults when SSPL is stopped and started in between")
