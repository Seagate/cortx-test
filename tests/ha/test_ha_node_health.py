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

"""
HA test suite for node status reflected for multinode.
"""

import logging
from random import SystemRandom
import time
import pytest
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.helpers.bmc_helper import Bmc
from commons import commands as common_cmds
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.constants import SwAlerts as SwAlertsconst
from config import CMN_CFG, HA_CFG, RAS_TEST_CFG
from libs.csm.cli.cortx_cli_system import CortxCliSystemtOperations
from libs.csm.cli.cortx_cli import CortxCli
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ha.ha_common_libs import HALibs
from libs.csm.rest.csm_rest_system_health import SystemHealth

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestHANodeHealth:
    """
    Test suite for node status tests of HA.
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
        cls.system_random = SystemRandom()

        cls.node_list = []
        cls.host_list = []
        cls.bmc_list = []
        cls.sys_list = []
        cls.cli_list = []
        cls.hlt_list = []
        cls.srvnode_list = []
        cls.restored = True
        cls.starttime = cls.nw_data = None

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.host_list.append(cls.host)
            cls.srvnode_list.append(f"srvnode-{node + 1}")
            cls.node_list.append(Node(hostname=cls.host, username=cls.uname, password=cls.passwd))
            cls.hlt_list.append(Health(hostname=cls.host, username=cls.uname, password=cls.passwd))
            cls.bmc_list.append(Bmc(hostname=cls.host, username=cls.uname, password=cls.passwd))
            cls.sys_list.append(CortxCliSystemtOperations(host=cls.host, username=cls.uname,
                                                          password=cls.passwd))
            cls.cli_list.append(CortxCli(host=cls.host, username=cls.uname, password=cls.passwd))

        LOGGER.info("Done: Setup module operations")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        self.starttime = time.time()
        self.nw_data = None
        LOGGER.info(
            "Checking in cortxcli and REST that all nodes are shown online and PCS clean.")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        self.ha_obj.status_nodes_online(node_obj=self.node_list[0], srvnode_list=self.srvnode_list,
                                        sys_list=self.sys_list, no_nodes=self.num_nodes)
        LOGGER.info("All nodes are online and PCS looks clean.")
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
                    resp = self.ha_obj.host_power_on(host=self.host_list[node],
                                                     bmc_obj=self.bmc_list[node])
                    assert_utils.assert_true(resp, f"Failed to power on {self.srvnode_list[node]}.")
                    if self.setup_type == "HW":
                        LOGGER.debug("HW: Need to enable stonith on the node after node powered on")
                        self.node_list[node].execute_cmd(
                            common_cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node + 1),
                            read_lines=True)
                if self.nw_data:
                    resp = self.node_list[node].execute_cmd(
                        common_cmds.GET_IFCS_STATUS.format(self.nw_data[1][node]), read_lines=True)
                    LOGGER.debug("%s interface status for %s = %s", self.nw_data[0][node],
                                 self.srvnode_list[node], resp[0])
                    if "DOWN" in resp[0]:
                        LOGGER.info("Make the %s interface back up for %s",
                                    self.nw_data[0][node], self.srvnode_list[node])
                        self.node_list[node].execute_cmd(
                            common_cmds.IP_LINK_CMD.format(self.nw_data[0][node], "up"),
                            read_lines=True)
                        resp = self.node_list[node].execute_cmd(common_cmds.CMD_PING.format(
                                self.nw_data[1][node]), read_lines=True, exc=False)
                        assert_utils.assert_not_in("Name or service not known", resp[1][0],
                                                   "Node interface still down.")
                    LOGGER.info("All network interfaces are up")

        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are online and PCS looks clean.")
        LOGGER.info("ENDED: Teardown Operations.")

    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.tags("TEST-22544")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_os_shutdown(self):
        """
        Test to Check that correct node status is shown in Cortx CLI and REST when node goes down
        and comes back up(one by one, os shutdown)
        """
        LOGGER.info("Started: Test to check node status one by one for all nodes with os shutdown.")

        LOGGER.info("Shutdown nodes one by one and check status.")
        for node in range(self.num_nodes):
            self.restored = False
            node_name = self.srvnode_list[node]
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to disable stonith on the node before shutdown")
                self.node_list[node].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("disable", node+1), read_lines=True)
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node],
                                                          node_obj=self.node_list[node],
                                                          is_safe=True)
            assert_utils.assert_true(resp, f"Failed to shutdown {self.host_list[node]}")

            LOGGER.info("Check in cortxcli and REST that the status is changed for %s to Failed",
                        node_name)
            if node_name == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node + 1]
            resp = self.ha_obj.check_csm_service(nd_obj, self.srvnode_list, self.sys_list)
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj = resp[1]
            check_rem_node = [
                "failed" if num == node else "online" for num in range(self.num_nodes)]
            resp = self.ha_obj.verify_node_health_status(sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(self.starttime, self.alert_type["get"],
                                                           False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info("Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(node, self.num_nodes, self.node_list)
            assert_utils.assert_true(resp, "Some services are down for other nodes.")

            resp = self.ha_obj.host_power_on(host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(resp, f"Failed to power on {self.host_list[node]}.")
            self.restored = True
            # To get all the services up and running
            time.sleep(40)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to enable stonith on the node after node came back up")
                self.node_list[node].execute_cmd(common_cmds.PCS_RESOURCE_STONITH_CMD.format(
                    "enable", node+1), read_lines=True)

            LOGGER.info("Check all nodes are back online in CLI and REST.")
            self.ha_obj.status_nodes_online(node_obj=nd_obj, srvnode_list=self.srvnode_list,
                                            sys_list=self.sys_list, no_nodes=self.num_nodes)

            LOGGER.info("Checking PCS clean after powered on %s", node_name)
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes are online and PCS looks clean.")

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            self.starttime = time.time()
            LOGGER.info("Node down/up worked fine for node: %s", node_name)

        LOGGER.info("Ended: Test to check node status one by one for all nodes with os shutdown.")

    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.tags("TEST-22574")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_unsafe_shutdown(self):
        """
        Test to Check that correct node status is shown in Cortx CLI and REST when node goes down
        and comes back up(one by one, unsafe shutdown)
        """
        LOGGER.info(
            "Started: Test to check node status one by one for all nodes with unsafe shutdown.")

        LOGGER.info("Shutdown nodes one by one and check status.")
        for node in range(self.num_nodes):
            self.restored = False
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to disable stonith on the node before shutdown")
                self.node_list[node].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("disable", node+1),
                    read_lines=True)
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node],
                                                          bmc_obj=self.bmc_list[node],
                                                          node_obj=self.node_list[node])
            assert_utils.assert_true(resp, f"Failed to shutdown {self.host_list[node]}")
            LOGGER.info("Check %s is in Failed state and other nodes state is not affected",
                        self.srvnode_list[node])
            LOGGER.info("Get the new node on which CSM service is running.")
            if self.srvnode_list[node] == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node + 1]
            resp = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj = resp[1]
            check_rem_node = [
                "failed" if num == node else "online" for num in range(self.num_nodes)]
            resp = self.ha_obj.verify_node_health_status(sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["get"], False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            LOGGER.info("Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(node, self.num_nodes, self.node_list)
            assert_utils.assert_true(resp, "Some services are down for other nodes.")
            resp = self.ha_obj.host_power_on(host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(resp, f"Failed to power on {self.host_list[node]}.")
            self.restored = True
            # To get all the services up and running
            time.sleep(40)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to enable stonith on the node after node came back up")
                self.node_list[node].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node+1), read_lines=True)

            LOGGER.info("Check all nodes are back online in CLI and REST.")
            self.ha_obj.status_nodes_online(node_obj=nd_obj, srvnode_list=self.srvnode_list,
                                            sys_list=self.sys_list, no_nodes=self.num_nodes)

            LOGGER.info("Checking PCS clean after powered on %s", self.host_list[node])
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes are online and PCS looks clean.")

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(self.starttime,
                                                           self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            self.starttime = time.time()

            LOGGER.info("Node down/up worked fine for node: %s", self.srvnode_list[node])
        LOGGER.info(
            "Completed: Test to check node status one by one for all nodes with unsafe shutdown.")

    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.tags("TEST-23274")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_nw_down(self):
        """
        Test to Check that correct node status is shown in Cortx CLI and REST when nw interface
        on node goes down and comes back up (one by one)
        """
        LOGGER.info(
            "Started: Test to check node status one by one on all nodes when nw interface on "
            "node goes down and comes back up")

        response = self.ha_obj.get_iface_ip_list(node_list=self.node_list, num_nodes=self.num_nodes)
        iface_list = response[0]
        private_ip_list = response[1]
        self.nw_data = [iface_list, private_ip_list]

        for node in range(self.num_nodes):
            self.restored = False
            node_name = self.srvnode_list[node]
            LOGGER.info("Make the private data interface %s down for %s",
                        iface_list[node], node_name)
            self.node_list[node].execute_cmd(common_cmds.IP_LINK_CMD.format(
                iface_list[node], "down"), read_lines=True)

            if node_name == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node + 1]
            resp = nd_obj.execute_cmd(common_cmds.CMD_PING.format(private_ip_list[node]),
                                      read_lines=True, exc=False)
            LOGGER.debug("Response : %s", resp)
            assert_utils.assert_in(b"100% packet loss", resp, f"Node interface still up. {resp}")
            time.sleep(120)
            LOGGER.info("Check in cortxcli and REST that the status is changed for %s to Failed",
                        node_name)
            resp = self.ha_obj.check_csm_service(nd_obj, self.srvnode_list, self.sys_list)
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj = resp[1]
            check_rem_node = ["failed" if num == node else "online" for num in range(
                self.num_nodes)]
            resp = self.ha_obj.verify_node_health_status(sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, SwAlertsconst.ResourceType.NW_INTFC, False, iface_list[node])
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            LOGGER.info("Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(node, self.num_nodes, self.node_list)
            assert_utils.assert_true(resp, "Some services are down for other nodes.")

            LOGGER.info(
                "Make the private data interface %s back up for %s", iface_list[node], node_name)
            self.node_list[node].execute_cmd(common_cmds.IP_LINK_CMD.format(iface_list[node], "up"),
                                             read_lines=True)
            resp = nd_obj.execute_cmd(common_cmds.CMD_PING.format(private_ip_list[node]),
                                      read_lines=True, exc=False)
            assert_utils.assert_not_in(b"100% packet loss", resp,
                                       f"Node interface still down. {resp}")
            self.restored = True
            # To get all the services up and running
            time.sleep(40)
            LOGGER.info("Check all nodes are back online in CLI/REST and PCS clean after making "
                        "the private data interface %s down for %s", iface_list[node], node_name)
            self.ha_obj.status_nodes_online(node_obj=nd_obj, srvnode_list=self.srvnode_list,
                                            sys_list=self.sys_list, no_nodes=self.num_nodes)
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes are online and PCS looks clean.")

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, SwAlertsconst.ResourceType.NW_INTFC, True, iface_list[node])
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            self.starttime = time.time()
            LOGGER.info("Node nw interface down/up worked fine for node: %s", node_name)

        LOGGER.info(
            "Completed: Test to check node status one by one on all nodes when nw interface"
            "on node goes down and comes back up")

    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.tags("TEST-22623")
    @CTFailOn(error_handler)
    def test_single_node_multiple_times_os_shutdown(self):
        """
        Test to Check that correct node status is shown in Cortx CLI and REST, when node
        goes down and comes back up(single node multiple times, os shutdown)
        """
        LOGGER.info("Started: Test to check single node status with multiple os shutdown.")
        LOGGER.info("Get the node for multiple os shutdown.")
        node_index = self.system_random.choice(list(range(self.num_nodes)))

        LOGGER.info("Shutdown %s node multiple time and check status.",
                    self.srvnode_list[node_index])
        for loop in range(self.loop_count):
            self.restored = False
            LOGGER.info("Shutting down node: %s, Loop: %s", self.srvnode_list[node_index], loop)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to disable stonith on the %s before shutdown",
                             self.srvnode_list[node_index])
                self.node_list[node_index].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("disable", node_index+1),
                    read_lines=True)

            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node_index],
                                                          node_obj=self.node_list[node_index],
                                                          is_safe=True)
            assert_utils.assert_true(resp, f"Failed to shutdown {self.host_list[node_index]}")

            LOGGER.info("Get the new node on which CSM service failover.")
            if self.srvnode_list[node_index] == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node_index + 1]
            resp = self.ha_obj.check_csm_service(nd_obj, self.srvnode_list, self.sys_list)
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj = resp[1]

            check_rem_node = [
                "failed" if num == node_index else "online" for num in range(self.num_nodes)]
            resp = self.ha_obj.verify_node_health_status(sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(self.starttime, self.alert_type["get"],
                                                           False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info("Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(node_index, self.num_nodes, self.node_list)
            assert_utils.assert_true(resp, "Some services are down for other nodes.")
            resp = self.ha_obj.host_power_on(host=self.host_list[node_index],
                                             bmc_obj=self.bmc_list[node_index])
            assert_utils.assert_true(resp, f"Failed to power on {self.host_list[node_index]}.")
            self.restored = True

            # To get all the services up and running
            time.sleep(40)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to enable stonith on the node after node came back up")
                self.node_list[node_index].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node_index+1),
                    read_lines=True)

            LOGGER.info("Checked All nodes are online in CLI and REST.")
            self.ha_obj.status_nodes_online(node_obj=nd_obj, srvnode_list=self.srvnode_list,
                                            sys_list=self.sys_list, no_nodes=self.num_nodes)

            LOGGER.info("Checking PCS clean after powered on %s", self.host_list[node_index])
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes are online and PCS looks clean.")

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            self.starttime = time.time()
            LOGGER.info("Node down/up worked fine for node: %s, Loop: %s",
                        self.srvnode_list[node_index], loop)
        LOGGER.info("Completed: Test to check single node status with multiple os shutdown.")

    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.tags("TEST-22626")
    @CTFailOn(error_handler)
    def test_single_node_multiple_times_unsafe_shutdown(self):
        """
        Test to Check that correct node status is shown in Cortx CLI and REST, when node
        goes down and comes back up(single node multiple times, unsafe shutdown)
        """
        LOGGER.info("Started: Test to check single node status with multiple unsafe shutdown.")

        LOGGER.info("Get the node for multiple unsafe shutdown.")
        node_index = self.system_random.choice(list(range(self.num_nodes)))

        LOGGER.info("Shutdown %s node multiple time and check status.",
                    self.srvnode_list[node_index])
        for loop in range(self.loop_count):
            self.restored = False
            LOGGER.info("Shutting down node: %s, Loop: %s", self.srvnode_list[node_index], loop)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to disable stonith on the node before shutdown")
                self.node_list[node_index].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("disable", node_index+1),
                    read_lines=True)
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node_index],
                                                          bmc_obj=self.bmc_list[node_index],
                                                          node_obj=self.node_list[node_index])
            assert_utils.assert_true(resp, f"Failed to shutdown {self.host_list[node_index]}")

            LOGGER.info("Get the new node on which CSM service failover.")
            if self.srvnode_list[node_index] == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node_index + 1]
            resp = self.ha_obj.check_csm_service(nd_obj, self.srvnode_list, self.sys_list)
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj = resp[1]

            check_rem_node = [
                "failed" if num == node_index else "online" for num in range(self.num_nodes)]
            resp = self.ha_obj.verify_node_health_status(sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(self.starttime, self.alert_type["get"],
                                                           False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info("Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(
                node_index, self.num_nodes, self.node_list)
            assert_utils.assert_true(resp, "Some services are down for other nodes.")
            resp = self.ha_obj.host_power_on(host=self.host_list[node_index],
                                             bmc_obj=self.bmc_list[node_index])
            assert_utils.assert_true(resp, f"Failed to power on {self.host_list[node_index]}.")
            self.restored = True

            # To get all the services up and running
            time.sleep(40)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to enable stonith on the node after node came back up")
                self.node_list[node_index].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node_index+1),
                    read_lines=True)

            LOGGER.info("Check all nodes are back online in CLI and REST")
            self.ha_obj.status_nodes_online(node_obj=nd_obj, srvnode_list=self.srvnode_list,
                                            sys_list=self.sys_list, no_nodes=self.num_nodes)
            LOGGER.info("Checking PCS clean after powered on %s", self.host_list[node_index])
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes are online and PCS looks clean.")

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            self.starttime = time.time()
            LOGGER.info("Node down/up worked fine for node: %s, Loop: %s",
                        self.srvnode_list[node_index], loop)
        LOGGER.info("Completed: Test to check single node status with multiple unsafe shutdown.")
