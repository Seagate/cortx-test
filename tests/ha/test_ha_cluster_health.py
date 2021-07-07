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

"""
HA test suite for cluster status reflected for multinode.
"""

import logging
import time

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.bmc_helper import Bmc
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG, HA_CFG, RAS_TEST_CFG
from libs.csm.cli.cortx_cli import CortxCli
from libs.csm.cli.cortx_cli_system import CortxCliSystemtOperations
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.ha.ha_common_libs import HALibs

LOGGER = logging.getLogger(__name__)


class TestHAClusterHealth:
    """
    Test suite for cluster status tests of HA.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.setup_type = CMN_CFG["setup_type"]
        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.csm_user = CMN_CFG["csm"]["csm_admin_user"]["username"]
        cls.csm_passwd = CMN_CFG["csm"]["csm_admin_user"]["password"]
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.csm_alerts_obj = SystemAlerts()
        cls.alert_type = RAS_TEST_CFG["alert_types"]
        cls.ha_obj = HALibs()
        cls.ha_rest = SystemHealth()
        cls.loop_count = HA_CFG["common_params"]["loop_count"]

        cls.node_list = []
        cls.host_list = []
        cls.bmc_list = []
        cls.sys_list = []
        cls.cli_list = []
        cls.hlt_list = []
        cls.srvnode_list = []
        cls.restored = True

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.host_list.append(cls.host)
            cls.srvnode_list.append(f"srvnode-{node + 1}")
            cls.node_list.append(Node(hostname=cls.host,
                                      username=cls.uname, password=cls.passwd))
            cls.hlt_list.append(Health(hostname=cls.host, username=cls.uname,
                                       password=cls.passwd))
            cls.bmc_list.append(Bmc(hostname=cls.host, username=cls.uname,
                                    password=cls.passwd))
            cls.sys_list.append(CortxCliSystemtOperations(
                host=cls.host, username=cls.uname, password=cls.passwd))
            cls.cli_list.append(
                CortxCli(
                    host=cls.host,
                    username=cls.uname,
                    password=cls.passwd))

        LOGGER.info("Done: Setup module operations")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.start_time = time.time()
        LOGGER.info("Checking if all nodes are reachable and PCS clean.")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are reachable and PCS looks clean.")

        LOGGER.info("Checking in cortxcli and REST that cluster is shown online.")
        self.ha_obj.status_cluster_resource_online(self.srvnode_list, self.sys_list,
                                                   self.node_list[0])
        LOGGER.info("Cluster is online in cortxcli and REST.")
        LOGGER.info("ENDED: Setup Operations")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        LOGGER.info("Checking if all nodes online and PCS clean after test.")
        if not self.restored:
            for node in range(self.num_nodes):
                resp = system_utils.check_ping(self.host_list[node])
                if not resp:
                    resp = self.ha_obj.host_power_on(
                        host=self.host_list[node],
                        bmc_obj=self.bmc_list[node])
                    assert_utils.assert_true(
                        resp, f"Failed to power on {self.srvnode_list[node]}.")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are online and PCS looks clean.")
        LOGGER.info("ENDED: Teardown Operations.")

    # pylint: disable=R0201
    @pytest.mark.ha
    @pytest.mark.tags("TEST-22893")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_safe_shutdown(self):
        """
        Test to Check that correct cluster status is shown in Cortx CLI and REST when node goes down
        and comes back up(one by one, safe shutdown)
        """
        LOGGER.info("Started: Test to check cluster status, with safe shutdown nodes one by one.")
        self.restored = False
        LOGGER.info("Shutdown nodes one by one and check status.")
        for node in range(self.num_nodes):
            node_name = self.srvnode_list[node]
            LOGGER.info(f"Shutting down {node_name}")
            if self.setup_type == "HW":
                LOGGER.debug(
                    "HW: Need to disable stonith on the node before shutdown")
                # TODO: Need to get the command once F-11A available.
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node], is_safe=True)
            assert_utils.assert_true(resp, "Host has not shutdown yet.")

            LOGGER.info(
                f"Check in cortxcli and REST that the status is changed for {node_name} to Failed")
            if node_name == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node + 1]
            sys_obj = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            check_rem_node = [
                "failed" if num == node else "online" for num in range(
                    self.num_nodes)]
            LOGGER.info("Verify node status via CortxCLI")
            resp = self.ha_obj.verify_node_health_status(
                sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status via CortxCLI")
            resp = self.ha_obj.verify_csr_health_status(sys_obj, "failed")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Verify node status via REST")
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status via REST")
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.start_time, self.alert_type["fault"], False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info(
                "Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(
                node, self.num_nodes, self.node_list)
            assert_utils.assert_true(
                resp, "Some services are down for other nodes.")

            LOGGER.info(f"Power on {node_name}")
            resp = self.ha_obj.host_power_on(
                host=self.host_list[node],
                bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(
                resp, "Host has not powered on yet.")
            LOGGER.info(f"{node_name} has powered on")
            self.restored = True
            # To get all the services up and running
            time.sleep(40)

            LOGGER.info("Check all nodes, cluster, rack, site are back online in CLI and REST.")
            self.ha_obj.status_cluster_resource_online(self.srvnode_list, self.sys_list,
                                                       nd_obj)

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.start_time, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info(f"Node down/up worked fine for node: {node_name}")

        LOGGER.info(
            "Completed: Test to check cluster status one by one for all nodes with safe shutdown.")

    # pylint: disable=R0201
    @pytest.mark.ha
    @pytest.mark.tags("TEST-22895")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_unsafe_shutdown(self):
        """
        Test to check that correct cluster status is shown in Cortx CLI when nodes goes
        offline and comes back online(one by one, unsafe shutdown)
        """
        LOGGER.info(
            "Started: Test to check cluster status, with unsafe shutdown nodes one by one")
        self.restored = False
        LOGGER.info("Shutdown nodes one by one and check status.")
        for node in range(self.num_nodes):
            LOGGER.info(f"Shutting down {self.srvnode_list[node]}")
            if self.setup_type == "HW":
                LOGGER.debug(
                    "HW: Need to disable stonith on the node before shutdown")
                # TODO: Need to get the command once F-11A available.
            resp = self.ha_obj.host_safe_unsafe_power_off(
                host=self.host_list[node],
                bmc_obj=self.bmc_list[node],
                node_obj=self.node_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not shutdown yet.")
            LOGGER.info(f"{self.host_list[node]} is powered off.")

            LOGGER.info(
                f"Check in cortxcli and REST that the status is changed for "
                f"{self.srvnode_list[node]} to Failed")
            if self.srvnode_list[node] == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node + 1]
            sys_obj = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            check_rem_node = [
                "failed" if num == node else "online" for num in range(
                    self.num_nodes)]
            LOGGER.info("Verify node status via CortxCLI")
            resp = self.ha_obj.verify_node_health_status(
                sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status via CortxCLI")
            resp = self.ha_obj.verify_csr_health_status(sys_obj, "failed")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Verify node status via REST")
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status via REST")
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.start_time, self.alert_type["fault"], False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info(
                "Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(
                node, self.num_nodes, self.node_list)
            assert_utils.assert_true(
                resp, "Some services are down for other nodes.")

            LOGGER.info(f"Power on {self.srvnode_list[node]}")
            resp = self.ha_obj.host_power_on(
                host=self.host_list[node],
                bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not powered on yet.")
            LOGGER.info(f"{self.host_list[node]} is powered on.")
            self.restored = True
            # To get all the services up and running
            time.sleep(40)
            LOGGER.info("Check all nodes, cluster, rack, site are back online in CLI and REST.")
            self.ha_obj.status_cluster_resource_online(self.srvnode_list, self.sys_list,
                                                       nd_obj)

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.start_time, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info("fNode down/up worked fine for node: {self.srvnode_list[node]}")

        LOGGER.info(
            "Completed: Test to check cluster status one by one for all nodes with unsafe shutdown.")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-22872")
    @CTFailOn(error_handler)
    def test_two_nodes_down_safe_shutdown(self):
        """
        Test to check that correct cluster status is shown in Cortx CLI when two nodes goes
        offline and comes back online(safe shutdown)
        """
        LOGGER.info(
            "Started: Test to check cluster status by making two nodes down and up, "
            "with safe shutdown.")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-22873")
    @CTFailOn(error_handler)
    def test_two_nodes_down_unsafe_shutdown(self):
        """
        Test to check that correct cluster status is shown in Cortx CLI when two nodes goes
        offline and comes back online(unsafe shutdown)
        """
        LOGGER.info(
            "Started: Test to check cluster status by making two nodes down and up, "
            "with unsafe shutdown.")
