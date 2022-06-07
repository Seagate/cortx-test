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
HA test suite for cluster status reflected for multinode.
"""

import logging
import secrets
import time

import pytest

from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from commons.helpers.bmc_helper import Bmc
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from commons import commands as common_cmds
from config import CMN_CFG, HA_CFG, RAS_TEST_CFG
from libs.csm.cli.cortx_cli import CortxCli
from libs.csm.cli.cortx_cli_system import CortxCliSystemtOperations
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.csm.rest.csm_rest_system_health import SystemHealth
from libs.ha.ha_common_libs import HALibs
from libs.ha.ha_common_libs_gui import HAGUILibs

LOGGER = logging.getLogger(__name__)


class TestHAClusterHealthGUI:
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
        cls.system_random = secrets.SystemRandom()
        cls.node_list = []
        cls.host_list = []
        cls.bmc_list = []
        cls.sys_list = []
        cls.cli_list = []
        cls.hlt_list = []
        cls.srvnode_list = []
        cls.restored = True
        cls.nw_data = None
        # required for Robot_GUI
        cls.ha_gui_obj = HAGUILibs()

        for node in range(cls.num_nodes):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.host_list.append(cls.host)
            cls.srvnode_list.append(f"srvnode-{node+1}")
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
        LOGGER.info("Checking if all nodes are reachable and PCS clean.")
        self.nw_data = None
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
                    resp = self.ha_obj.host_power_on(host=self.host_list[node],
                                                     bmc_obj=self.bmc_list[node])
                    assert_utils.assert_true(
                        resp, f"Failed to power on {self.srvnode_list[node]}.")
                    if self.setup_type == "HW":
                        LOGGER.debug(
                            "HW: Need to enable stonith on the node after node powered on")
                        self.node_list[node].execute_cmd(
                            common_cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node+1),
                            read_lines=True)
                if self.nw_data:
                    resp = self.node_list[node].execute_cmd(
                        common_cmds.GET_IFCS_STATUS.format(self.nw_data[1][node]), read_lines=True)
                    LOGGER.debug("%s interface status for %s = %s",
                                 self.nw_data[0][node], self.srvnode_list[node], resp[0])
                    if "DOWN" in resp[0]:
                        LOGGER.info(
                            "Make the %s interface back up for %s", self.nw_data[0][node],
                            self.srvnode_list[node])
                        self.node_list[node].execute_cmd(
                            common_cmds.IP_LINK_CMD.format(
                                self.nw_data[0][node], "up"), read_lines=True)
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

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.tags("TEST-22894")
    @CTFailOn(error_handler)
    def test_cluster_one_by_one_os_shutdown_gui(self):
        """
        Test to Check that correct cluster status is shown in Cortx GUI when node goes down
        and comes back up(one by one, os shutdown)
        """
        LOGGER.info("Started: Test to check cluster status, with os shutdown nodes one by one.")

        LOGGER.info("Acknowledge node alerts if present in new alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_new_alerts()
        LOGGER.info("Acknowledge node alerts if present in active alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_active_alerts()
        LOGGER.info("Verify Cluster is in healthy state")
        self.ha_gui_obj.verify_cluster_state("online")

        LOGGER.info("Shutdown nodes one by one and check status.")
        for node in range(self.num_nodes):
            node_name = self.srvnode_list[node]
            LOGGER.info("Verify if node state online")
            self.ha_gui_obj.verify_node_state(node, "online")
            LOGGER.info("Shutting down %s", node_name)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to disable stonith on the node before shutdown")
                self.node_list[node].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("disable", node+1),
                    read_lines=True)
            resp = self.ha_obj.host_safe_unsafe_power_off(host=self.host_list[node],
                                                          node_obj=self.node_list[node],
                                                          bmc_obj=self.bmc_list[node],
                                                          is_safe=True)
            assert_utils.assert_true(resp, f"Failed to shutdown {self.host_list[node]}")
            self.restored = False

            LOGGER.info("Check in cortxcli and REST that the status is changed for %s to Failed",
                        node_name)
            if node_name == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node+1]
            sys_obj = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            assert_utils.assert_true(
                sys_obj[0], f"{sys_obj[1]} Could not get server which has CSM service running.")
            check_rem_node = [
                "failed" if num == node else "online" for num in range(
                    self.num_nodes)]
            LOGGER.info("Verify node status via CortxCLI")
            resp = self.ha_obj.verify_node_health_status(
                sys_obj[1], status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status via CortxCLI")
            resp = self.ha_obj.verify_csr_health_status(sys_obj[1], "degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Verify node status via REST")
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status via REST")
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            self.ha_gui_obj.verify_node_down_alert(node)
            LOGGER.info("Verify if node state failed")
            self.ha_gui_obj.verify_node_state(node, "failed")
            LOGGER.info("Verify Cluster is in degraded state ")
            self.ha_gui_obj.verify_cluster_state("degraded")

            LOGGER.info("Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(
                node, self.num_nodes, self.node_list)
            assert_utils.assert_true(resp, "Some services are down for other nodes.")

            LOGGER.info("Power on %s", node_name)
            resp = self.ha_obj.host_power_on(host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(resp, f"Failed to power on {self.host_list[node]}.")
            LOGGER.info("%s has powered on", node_name)
            self.restored = True
            # To get all the services up and running
            time.sleep(40)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to enable stonith on the node after node came back up")
                self.node_list[node].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node+1),
                    read_lines=True)

            LOGGER.info("Check all nodes, cluster, rack, site are back online in CLI and REST.")
            self.ha_obj.status_cluster_resource_online(self.srvnode_list, self.sys_list, nd_obj)
            LOGGER.info("Checking PCS clean after powered on %s", self.host_list[node])
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes are online and PCS looks clean.")

            LOGGER.info("Check for the node back up alert.")
            self.ha_gui_obj.verify_node_back_up_alert(node)
            LOGGER.info("Verify if node state online")
            self.ha_gui_obj.verify_node_state(node, "online")
            LOGGER.info("Verify Cluster is in healthy state")
            self.ha_gui_obj.verify_cluster_state("online")

            LOGGER.info("Node down/up worked fine for node: %s", node_name)

        LOGGER.info(
            "Complete: Test to check cluster status one by one for all nodes with os shutdown.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.tags("TEST-22896")
    @CTFailOn(error_handler)
    def test_cluster_one_by_one_unsafe_shutdown_gui(self):
        """
        Test to check that correct cluster status is shown in Cortx GUI when nodes goes
        offline and comes back online(one by one, unsafe shutdown)
        """
        LOGGER.info("Started: Test to check cluster status, with unsafe shutdown nodes one by one")

        LOGGER.info("Acknowledge node alerts if present in new alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_new_alerts()
        LOGGER.info("Acknowledge node alerts if present in active alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_active_alerts()
        LOGGER.info("Verify Cluster is in healthy state")
        self.ha_gui_obj.verify_cluster_state("online")

        LOGGER.info("Shutdown nodes one by one and check status.")
        for node in range(self.num_nodes):
            LOGGER.info("Verify if node state online")
            self.ha_gui_obj.verify_node_state(node, "online")
            LOGGER.info("Shutting down %s", self.srvnode_list[node])
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to disable stonith on the node before shutdown")
                self.node_list[node].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("disable", node+1),
                    read_lines=True)
            resp = self.ha_obj.host_safe_unsafe_power_off(
                host=self.host_list[node],
                bmc_obj=self.bmc_list[node],
                node_obj=self.node_list[node])
            assert_utils.assert_true(resp, f"Failed to shutdown {self.host_list[node]}")
            LOGGER.info("%s is powered off.", self.host_list[node])
            self.restored = False

            LOGGER.info("Check in cortxcli and REST that the status is changed for %s to Failed",
                        self.srvnode_list[node])
            if self.srvnode_list[node] == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node+1]
            sys_obj = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            assert_utils.assert_true(
                sys_obj[0], f"{sys_obj[1]} Could not get server which has CSM service running.")
            check_rem_node = ["failed" if num == node else "online"
                              for num in range(self.num_nodes)]
            LOGGER.info("Verify node status via CortxCLI")
            resp = self.ha_obj.verify_node_health_status(sys_obj[1], status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status via CortxCLI")
            resp = self.ha_obj.verify_csr_health_status(sys_obj[1], "degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Verify node status via REST")
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status via REST")
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            self.ha_gui_obj.verify_node_down_alert(node)
            LOGGER.info("Verify if node state failed")
            self.ha_gui_obj.verify_node_state(node, "failed")
            LOGGER.info("Verify Cluster is in degraded state ")
            self.ha_gui_obj.verify_cluster_state("degraded")

            LOGGER.info("Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(node, self.num_nodes, self.node_list)
            assert_utils.assert_true(resp, "Some services are down for other nodes.")

            LOGGER.info("Power on %s", self.srvnode_list[node])
            resp = self.ha_obj.host_power_on(host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(
                resp, f"Failed to power on {self.host_list[node]}.")
            LOGGER.info("%s is powered on.", self.host_list[node])
            self.restored = True
            # To get all the services up and running
            time.sleep(40)
            if self.setup_type == "HW":
                LOGGER.debug(
                    "HW: Need to enable stonith on the node after node came back up")
                self.node_list[node].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node+1),
                    read_lines=True)

            LOGGER.info("Check all nodes, cluster, rack, site are back online in CLI and REST.")
            self.ha_obj.status_cluster_resource_online(self.srvnode_list, self.sys_list, nd_obj)
            LOGGER.info("Checking PCS clean after powered on %s", self.host_list[node])
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes are online and PCS looks clean.")

            LOGGER.info("Check for the node back up alert.")
            self.ha_gui_obj.verify_node_back_up_alert(node)
            LOGGER.info("Verify if node state online")
            self.ha_gui_obj.verify_node_state(node, "online")
            LOGGER.info("Verify Cluster is in healthy state")
            self.ha_gui_obj.verify_cluster_state("online")

            LOGGER.info("fNode down/up worked fine for node: {self.srvnode_list[node]}")

        LOGGER.info(
            "Complete: Test to check cluster status one by one for all nodes with unsafe shutdown.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.tags("TEST-22903")
    @CTFailOn(error_handler)
    def test_two_nodes_down_os_shutdown_gui(self):
        """
        Test to check that correct cluster status is shown in Cortx GUI when two nodes goes
        offline and comes back online(os shutdown)
        """
        LOGGER.info(
            "Started: Test to check cluster status by making two nodes down and up, "
            "with os shutdown.")

        LOGGER.info("Acknowledge node alerts if present in new alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_new_alerts()
        LOGGER.info("Acknowledge node alerts if present in active alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_active_alerts()
        LOGGER.info("Verify Cluster is in healthy state")
        self.ha_gui_obj.verify_cluster_state("online")

        LOGGER.info("Shutdown two nodes randomly.")
        off_nodes = self.system_random.sample(list(range(len(self.srvnode_list))), 2)

        for count, node in enumerate(off_nodes):
            LOGGER.info("Shutting down %s", self.srvnode_list[node])
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to disable stonith on the node before shutdown")
                self.node_list[node].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("disable", node+1),
                    read_lines=True)
            resp = self.ha_obj.host_safe_unsafe_power_off(
                host=self.host_list[node],
                bmc_obj=self.bmc_list[node],
                node_obj=self.node_list[node],
                is_safe=True
            )
            assert_utils.assert_true(resp, f"Failed to shutdown {self.host_list[node]}")
            LOGGER.info("%s is powered off.", self.host_list[node])
            time.sleep(40)
            self.restored = False

            if count == 0:
                LOGGER.info("Check for the node down alert.")
                self.ha_gui_obj.verify_node_down_alert(node)
                LOGGER.info("Verify if node state failed")
                self.ha_gui_obj.verify_node_state(node, "failed")
                LOGGER.info("Verify Cluster is in degraded state ")
                self.ha_gui_obj.verify_cluster_state("degraded")

        for count, node in enumerate(off_nodes):
            LOGGER.info("Power on %s", self.srvnode_list[node])
            resp = self.ha_obj.host_power_on(host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(resp, f"Failed to power on {self.host_list[node]}.")
            LOGGER.info("%s is powered on.", self.host_list[node])
            time.sleep(120)

            LOGGER.info("Check for the node back up alert.")
            self.ha_gui_obj.verify_node_back_up_alert(node)
            LOGGER.info("Verify if node state online")
            self.ha_gui_obj.verify_node_state(node, "online")

            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to enable stonith on the node after node came back up")
                self.node_list[node].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node+1),
                    read_lines=True)

        LOGGER.info("Verify Cluster is in healthy state")
        self.ha_gui_obj.verify_cluster_state("online")

        LOGGER.info("Checking PCS clean for all nodes")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are online and PCS looks clean.")

        self.restored = True
        LOGGER.info("Complete: Test to check cluster status two nodes off & on with os shutdown.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.tags("TEST-22904")
    @CTFailOn(error_handler)
    def test_two_nodes_down_unsafe_shutdown_gui(self):
        """
        Test to check that correct cluster status is shown in Cortx GUI when two nodes goes
        offline and comes back online(unsafe shutdown)
        """
        LOGGER.info(
            "Started: Test to check cluster status by making two nodes down and up, "
            "with unsafe shutdown.")

        LOGGER.info("Acknowledge node alerts if present in new alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_new_alerts()
        LOGGER.info("Acknowledge node alerts if present in active alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_active_alerts()
        LOGGER.info("Verify Cluster is in healthy state")
        self.ha_gui_obj.verify_cluster_state("online")

        LOGGER.info("Shutdown two nodes randomly.")
        off_nodes = self.system_random.sample(list(range(len(self.srvnode_list))), 2)

        for count, node in enumerate(off_nodes):
            LOGGER.info("Shutting down %s", self.srvnode_list[node])
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to disable stonith on the node before shutdown")
                self.node_list[node].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("disable", node+1),
                    read_lines=True)
            resp = self.ha_obj.host_safe_unsafe_power_off(
                host=self.host_list[node],
                bmc_obj=self.bmc_list[node],
                node_obj=self.node_list[node],
            )
            assert_utils.assert_true(resp, f"Failed to shutdown {self.host_list[node]}")
            LOGGER.info("%s is powered off.", self.host_list[node])

            self.restored = False

            if count == 0:
                LOGGER.info("Check for the node down alert.")
                self.ha_gui_obj.verify_node_down_alert(node)
                LOGGER.info("Verify if node state failed")
                self.ha_gui_obj.verify_node_state(node, "failed")
                LOGGER.info("Verify Cluster is in degraded state ")
                self.ha_gui_obj.verify_cluster_state("degraded")

        for count, node in enumerate(off_nodes):
            LOGGER.info("Power on %s", self.srvnode_list[node])
            resp = self.ha_obj.host_power_on(host=self.host_list[node], bmc_obj=self.bmc_list[node])
            assert_utils.assert_true(resp, f"Failed to power on {self.host_list[node]}.")
            LOGGER.info("%s is powered on.", self.host_list[node])

            LOGGER.info("Check for the node back up alert.")
            self.ha_gui_obj.verify_node_back_up_alert(node)
            LOGGER.info("Verify if node state online")
            self.ha_gui_obj.verify_node_state(node, "online")

            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to enable stonith on the node after node came back up")
                self.node_list[node].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node+1),
                    read_lines=True)

        LOGGER.info("Verify Cluster is in healthy state")
        self.ha_gui_obj.verify_cluster_state("online")

        LOGGER.info("Checking PCS clean for all nodes")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are online and PCS looks clean.")

        self.restored = True
        LOGGER.info(
            "Complete: Test to check cluster status two nodes off & on with unsafe shutdown.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.tags("TEST-22898")
    @CTFailOn(error_handler)
    def test_single_node_multiple_os_shutdown_gui(self):
        """
        Check that correct cluster/site/rack and node status is shown in Cortx GUI when node
        goes down and comes back up (single node multiple times, os shutdown)
        """
        LOGGER.info(
            "Started: Test to check cluster/site/rack and node status with os "
            "shutdown of single node multiple times.")

        LOGGER.info("Acknowledge node alerts if present in new alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_new_alerts()
        LOGGER.info("Acknowledge node alerts if present in active alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_active_alerts()
        LOGGER.info("Verify Cluster is in healthy state")
        self.ha_gui_obj.verify_cluster_state("online")

        LOGGER.info("Get the node for multiple os shutdown.")
        node_index = self.system_random.choice(list(range(self.num_nodes)))

        LOGGER.info("Shutdown %s node multiple time and check cluster status.",
                    self.srvnode_list[node_index])

        LOGGER.info("Verify if node state online")
        self.ha_gui_obj.verify_node_state(node_index, "online")

        for loop in range(self.loop_count):
            LOGGER.info("Shutting down node: %s, Loop: %s", self.srvnode_list[node_index], loop)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to disable stonith on the %s before shutdown",
                             self.srvnode_list[node_index])
                self.node_list[node_index].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("disable", node_index+1),
                    read_lines=True)
            resp = self.ha_obj.host_safe_unsafe_power_off(
                host=self.host_list[node_index],
                node_obj=self.node_list[node_index],
                bmc_obj=self.bmc_list[node_index],
                is_safe=True)
            assert_utils.assert_true(resp, f"Failed to shutdown {self.host_list[node_index]}")
            LOGGER.info("%s is powered off.", self.host_list[node_index])
            self.restored = False

            LOGGER.info("Get the new node on which CSM service failover.")
            if self.srvnode_list[node_index] == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node_index + 1]
            resp = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj = resp[1]
            LOGGER.info("Check resources health status in CLI and REST after shutdown %s",
                        self.srvnode_list[node_index])

            check_rem_node = [
                "failed" if num == node_index else "online" for num in range(
                    self.num_nodes)]
            LOGGER.info("Verify %s status is failed via CortxCLI", self.srvnode_list[node_index])
            resp = self.ha_obj.verify_node_health_status(sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status is degraded via CortxCLI")
            resp = self.ha_obj.verify_csr_health_status(sys_obj, "degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Verify %s status is failed via REST", self.srvnode_list[node_index])
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status is degraded via REST")
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            self.ha_gui_obj.verify_node_down_alert(node_index)
            LOGGER.info("Verify if node state failed")
            self.ha_gui_obj.verify_node_state(node_index, "failed")
            LOGGER.info("Verify Cluster is in degraded state ")
            self.ha_gui_obj.verify_cluster_state("degraded")

            LOGGER.info("Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(node_index, self.num_nodes, self.node_list)
            assert_utils.assert_true(resp, "Some services are down for other nodes.")
            LOGGER.info("Power on %s", self.srvnode_list[node_index])
            resp = self.ha_obj.host_power_on(host=self.host_list[node_index],
                                             bmc_obj=self.bmc_list[node_index])
            assert_utils.assert_true(resp, f"Failed to power on {self.srvnode_list[node_index]}.")
            LOGGER.info("%s is powered on", self.host_list[node_index])
            self.restored = True

            # To get all the services up and running
            time.sleep(40)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to enable stonith on the node after node came back up")
                self.node_list[node_index].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node_index+1),
                    read_lines=True)

            LOGGER.info(
                "Check all nodes, cluster, rack, site are back online in "
                "CLI and REST after power on %s", self.srvnode_list[node_index])
            self.ha_obj.status_cluster_resource_online(self.srvnode_list, self.sys_list, nd_obj)

            LOGGER.info("Checking PCS clean after powered on %s", self.host_list[node_index])
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes are online and PCS looks clean.")

            LOGGER.info("Check for the node back up alert.")
            self.ha_gui_obj.verify_node_back_up_alert(node_index)
            LOGGER.info("Verify if node state online")
            self.ha_gui_obj.verify_node_state(node_index, "online")
            LOGGER.info("Verify Cluster is in healthy state")
            self.ha_gui_obj.verify_cluster_state("online")

            LOGGER.info(
                "Check for cluster/site/rack degraded/online and node failed/online status "
                "with %s down/up worked fine for Loop: %s",
                self.srvnode_list[node_index],
                loop)
        LOGGER.info(
            "Completed: Test to check cluster/site/rack and node status with os "
            "shutdown of single node multiple times.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.tags("TEST-22899")
    @CTFailOn(error_handler)
    def test_single_node_multiple_unsafe_shutdown_gui(self):
        """
        Check that correct cluster/site/rack and node status is shown in Cortx GUI when
        node goes down and comes back up(single node multiple times, unsafe shutdown
        """
        LOGGER.info(
            "Started: Test to check cluster/site/rack and node status with unsafe "
            "shutdown of single node multiple times.")

        LOGGER.info("Acknowledge node alerts if present in new alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_new_alerts()
        LOGGER.info("Acknowledge node alerts if present in active alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_active_alerts()
        LOGGER.info("Verify Cluster is in healthy state")
        self.ha_gui_obj.verify_cluster_state("online")

        LOGGER.info("Get the node for multiple safe shutdown.")
        node_index = self.system_random.choice(list(range(self.num_nodes)))

        LOGGER.info("Shutdown %s node multiple time and check cluster status.",
                    self.srvnode_list[node_index])

        LOGGER.info("Verify if node state online")
        self.ha_gui_obj.verify_node_state(node_index, "online")

        for loop in range(self.loop_count):
            LOGGER.info("Shutting down node: %s, Loop: %s", self.srvnode_list[node_index], loop)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to disable stonith on the %s before shutdown",
                             self.srvnode_list[node_index])
                self.node_list[node_index].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("disable", node_index+1),
                    read_lines=True)
            resp = self.ha_obj.host_safe_unsafe_power_off(
                host=self.host_list[node_index],
                bmc_obj=self.bmc_list[node_index],
                node_obj=self.node_list[node_index])
            assert_utils.assert_true(resp, f"Failed to shutdown {self.host_list[node_index]}")
            LOGGER.info("%s is powered off.", self.host_list[node_index])
            self.restored = False

            LOGGER.info("Get the new node on which CSM service failover.")
            if self.srvnode_list[node_index] == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node_index + 1]
            resp = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj = resp[1]
            LOGGER.info("Check resources health in CLI and REST after shutdown %s",
                        self.srvnode_list[node_index])

            check_rem_node = [
                "failed" if num == node_index else "online" for num in range(
                    self.num_nodes)]
            LOGGER.info("Verify %s status is failed via CortxCLI", self.srvnode_list[node_index])
            resp = self.ha_obj.verify_node_health_status(sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status is degraded via CortxCLI")
            resp = self.ha_obj.verify_csr_health_status(sys_obj, "degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Verify %s status is failed via REST", self.srvnode_list[node_index])
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status is degraded via REST")
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            self.ha_gui_obj.verify_node_down_alert(node_index)
            LOGGER.info("Verify if node state failed")
            self.ha_gui_obj.verify_node_state(node_index, "failed")
            LOGGER.info("Verify Cluster is in degraded state ")
            self.ha_gui_obj.verify_cluster_state("degraded")

            LOGGER.info("Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(node_index, self.num_nodes, self.node_list)
            assert_utils.assert_true(resp, "Some services are down for other nodes.")
            LOGGER.info("Power on %s", self.srvnode_list[node_index])
            resp = self.ha_obj.host_power_on(host=self.host_list[node_index],
                                             bmc_obj=self.bmc_list[node_index])
            assert_utils.assert_true(resp, f"Failed to power on {self.srvnode_list[node_index]}.")
            LOGGER.info("%s is powered on", self.host_list[node_index])
            self.restored = True

            # To get all the services up and running
            time.sleep(40)
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to enable stonith on the node after node came back up")
                self.node_list[node_index].execute_cmd(
                    common_cmds.PCS_RESOURCE_STONITH_CMD.format("enable", node_index+1),
                    read_lines=True)

            LOGGER.info(
                "Check all nodes, cluster, rack, site are back online in CLI and "
                "REST after power on %s", self.srvnode_list[node_index])
            self.ha_obj.status_cluster_resource_online(self.srvnode_list, self.sys_list, nd_obj)

            LOGGER.info("Checking PCS clean after powered on %s", self.host_list[node_index])
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes are online and PCS looks clean.")

            LOGGER.info("Check for the node back up alert.")
            self.ha_gui_obj.verify_node_back_up_alert(node_index)
            LOGGER.info("Verify if node state online")
            self.ha_gui_obj.verify_node_state(node_index, "online")
            LOGGER.info("Verify Cluster is in healthy state")
            self.ha_gui_obj.verify_cluster_state("online")

            LOGGER.info(
                "Check for cluster/site/rack degraded/online and node failed/online status "
                "with %s down/up worked fine for Loop: %s",
                self.srvnode_list[node_index],
                loop)
        LOGGER.info(
            "Completed: Test to check cluster/site/rack and node status with unsafe "
            "shutdown of single node multiple times.")

    # pylint: disable=too-many-statements
    @pytest.mark.ha
    @pytest.mark.lr
    @pytest.mark.csm_gui
    @pytest.mark.tags("TEST-23384")
    @CTFailOn(error_handler)
    def test_one_by_one_network_port_down_gui(self):
        """
        Test to Check that correct cluster/site/rack and node status is shown in Cortx GUI
        when nw interface on node goes down and comes back up (one by one)
        """
        LOGGER.info(
            "Started: Test to check cluster/site/rack and node status, "
            "when one by one all node's nw interface goes down and comes back up")

        LOGGER.info("Acknowledge node alerts if present in new alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_new_alerts()
        LOGGER.info("Acknowledge node alerts if present in active alert table already")
        self.ha_gui_obj.acknowledge_node_alerts_in_active_alerts()
        LOGGER.info("Acknowledge network alerts if present in active alert table already")
        self.ha_gui_obj.acknowledge_network_interface_back_up_alerts()
        LOGGER.info("Verify Cluster is in healthy state")
        self.ha_gui_obj.verify_cluster_state("online")
        LOGGER.info("Fail if newtork alert in new alert table already present")
        self.ha_gui_obj.assert_if_network_interface_down_alert_present()

        response = self.ha_obj.get_iface_ip_list(node_list=self.node_list, num_nodes=self.num_nodes)
        iface_list = response[0]
        private_ip_list = response[1]
        self.nw_data = [iface_list, private_ip_list]

        for node in range(self.num_nodes):
            LOGGER.info("Make the private data interface %s down for %s",
                        iface_list[node], self.srvnode_list[node])
            self.node_list[node].execute_cmd(
                common_cmds.IP_LINK_CMD.format(
                    iface_list[node], "down"), read_lines=True)
            self.restored = False

            if self.srvnode_list[node] == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node+1]
            resp = nd_obj.execute_cmd(
                common_cmds.CMD_PING.format(
                    private_ip_list[node]), read_lines=True, exc=False)
            assert_utils.assert_in(
                b"100% packet loss",
                resp,
                f"Node interface still up. {resp}")
            time.sleep(60)
            LOGGER.info(
                "Check resources health in CLI and REST after making network interface down for %s",
                self.srvnode_list[node])
            resp = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj = resp[1]
            check_rem_node = [
                "failed" if num == node else "online" for num in range(
                    self.num_nodes)]
            LOGGER.info("Verify %s status is failed via CortxCLI", self.srvnode_list[node])
            resp = self.ha_obj.verify_node_health_status(
                sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Verify Cluster/Site/Rack status is degraded via CortxCLI")
            resp = self.ha_obj.verify_csr_health_status(sys_obj, "degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Verify %s status is failed via REST", self.srvnode_list[node])
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Verify Cluster/Site/Rack status is degraded via REST")
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            self.ha_gui_obj.verify_node_down_alert(node)
            LOGGER.info("Verify if node state failed")
            self.ha_gui_obj.verify_node_state(node, "failed")
            LOGGER.info("Verify Network interface down alert")
            self.ha_gui_obj.verify_network_interface_down_alert(iface_list[node])
            LOGGER.info("Verify Cluster is in degraded state ")
            self.ha_gui_obj.verify_cluster_state("degraded")

            LOGGER.info("Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(node, self.num_nodes, self.node_list)
            assert_utils.assert_true(resp, "Some services are down for other nodes.")

            LOGGER.info(
                "Make the private data interface %s back up for %s",
                iface_list[node],
                self.srvnode_list[node])
            self.node_list[node].execute_cmd(
                common_cmds.IP_LINK_CMD.format(
                    iface_list[node], "up"), read_lines=True)
            resp = nd_obj.execute_cmd(
                common_cmds.CMD_PING.format(
                    private_ip_list[node]),
                read_lines=True,
                exc=False)
            assert_utils.assert_not_in(b"100% packet loss", resp,
                                       f"Node interface still down. {resp}")
            self.restored = True
            # To get all the services up and running
            time.sleep(40)
            LOGGER.info(
                "Check all nodes, cluster, rack, site are back online in CLI and REST /"
                "after making the private data interface %s up for %s",
                iface_list[node],
                self.srvnode_list[node])
            self.ha_obj.status_cluster_resource_online(self.srvnode_list, self.sys_list, nd_obj)

            LOGGER.info("Checking PCS clean after making the private data interface %s down for %s",
                        iface_list[node], self.sys_list[node])
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes are online and PCS looks clean.")

            LOGGER.info("Check for the node back up alert.")
            self.ha_gui_obj.verify_node_back_up_alert(node)
            LOGGER.info("Verify if node state online")
            self.ha_gui_obj.verify_node_state(node, "online")
            LOGGER.info("Verify Network interface up alert")
            self.ha_gui_obj.verify_network_interface_back_up_alert(iface_list[node])
            LOGGER.info("Verify Cluster is in healthy state")
            self.ha_gui_obj.verify_cluster_state("online")

            LOGGER.info(
                "Check for cluster/site/rack degraded/online and node failed/online "
                "status with %s nw interface down/up worked fine",
                self.srvnode_list[node])

        LOGGER.info(
            "Completed: Test to check cluster/site/rack and node status, "
            "when one by one all node's nw interface goes down and comes back up")
