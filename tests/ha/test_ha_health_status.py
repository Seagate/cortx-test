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
HA test suite for node status reflected for multinode.
"""

import os
import logging
import random
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
from config import CMN_CFG, HA_CFG, RAS_TEST_CFG
from commons import pswdmanager
from libs.csm.cli.cortx_cli_system import CortxCliSystemtOperations
from libs.csm.cli.cortx_cli import CortxCli
from libs.csm.rest.csm_rest_alert import SystemAlerts
from libs.ha.ha_common_libs import HALibs
from libs.csm.rest.csm_rest_system_health import SystemHealth

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestHAHealthStatus:
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
        cls.bmc_user = CMN_CFG["bmc"]["username"]
        cls.bmc_pwd = CMN_CFG["bmc"]["password"]
        cls.vm_username = os.getenv(
            "QA_VM_POOL_ID", pswdmanager.decrypt(
                HA_CFG["vm_params"]["uname"]))
        cls.vm_password = os.getenv(
            "QA_VM_POOL_PASSWORD", pswdmanager.decrypt(
                HA_CFG["vm_params"]["passwd"]))
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.csm_alerts_obj = SystemAlerts()
        cls.alert_type = RAS_TEST_CFG["alert_types"]
        cls.ha_obj = HALibs()
        cls.ha_rest = SystemHealth()

        cls.node_list = []
        cls.host_list = []
        cls.bmc_list = []
        cls.sys_list = []
        cls.cli_list = []
        cls.hlt_list = []
        cls.srvnode_list = []
        cls.bmc_ip_list = []

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
        self.starttime = time.time()
        if self.setup_type == "HW":
            for bmc_obj in self.bmc_list:
                self.bmc_ip_list.append(bmc_obj.get_bmc_ip())
        LOGGER.info("Checking if all nodes online and PCS clean.")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are online and PCS looks clean.")

        LOGGER.info("ENDED: Setup Operations")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        """
        LOGGER.info("STARTED: Teardown Operations.")
        LOGGER.info("Checking if all nodes online and PCS clean after test.")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are online and PCS looks clean.")
        LOGGER.info("ENDED: Teardown Operations.")

    def status_nodes_online(self):
        """
        Helper function to check that all nodes are shown online in cortx cli/REST
        before starting any other operations.
        """
        LOGGER.info("Check the node which is running CSM service and login to CSM on that node.")
        sys_obj = self.ha_obj.check_csm_service(
            self.node_list[0], self.srvnode_list, self.sys_list)
        sys_obj.open_connection()
        res = sys_obj.login_cortx_cli()
        assert_utils.assert_true(res[0], res[1])
        resp = sys_obj.check_health_status(
            common_cmds.CMD_HEALTH_SHOW.format("node"))
        assert_utils.assert_true(resp[0], resp[1])
        resp_table = sys_obj.split_table_response(resp[1])
        LOGGER.info("Response for health check for all nodes: %s", resp_table)
        resp = self.ha_obj.verify_node_health_status(
            response=resp_table, status="online")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Check REST response for node status.")
        resp = self.ha_rest.get_node_health_status(
            exp_key='status', exp_val='online')
        assert_utils.assert_true(resp[0], resp[1])
        sys_obj.logout_cortx_cli()
        sys_obj.close_connection()
        LOGGER.info("All nodes are online.")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-22544")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_safe(self):
        """
        Test to Check that correct node status is shown in Cortx CLI and REST when node goes down
        and comes back up(one by one, safe shutdown)
        """
        LOGGER.info(
            "Started: Test to check node status one by one for all nodes with safe shutdown.")

        LOGGER.info("Check in cortxcli and REST that all nodes are shown online.")
        self.status_nodes_online()

        LOGGER.info("Shutdown nodes one by one and check status.")
        for node in range(self.num_nodes):
            node_name = self.srvnode_list[node]
            LOGGER.info("Shutting down {}".format(node_name))
            if self.setup_type == "HW":
                LOGGER.debug(
                    "HW: Need to disable stonith on the node before shutdown")
                # TODO: Need to get the command once F-11A available.
            resp = self.node_list[node].execute_cmd(cmd="shutdown now")
            LOGGER.debug("Response for shutdown: {}".format(resp))
            LOGGER.info("Check if the {} has shutdown.".format(node_name))
            resp = self.ha_obj.polling_host(
                max_timeout=120, host_index=node, exp_resp=False, host_list=self.host_list)
            assert_utils.assert_true(
                resp, "Host has not shutdown yet.")

            LOGGER.info(
                "Check in cortxcli and REST that the status is changed for {} to Failed".format(node_name))
            if node_name == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node + 1]
            sys_obj = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            sys_obj.open_connection()
            res = sys_obj.login_cortx_cli()
            assert_utils.assert_true(res[0], res[1])
            resp = sys_obj.check_health_status(
                common_cmds.CMD_HEALTH_SHOW.format("node"))
            assert_utils.assert_true(resp[0], resp[1])
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.debug(
                "Response in cortxcli is: {}".format(resp_table))
            check_rem_node = [
                "failed" if num == node else "online" for num in range(
                    self.num_nodes)]
            for node_check, state in enumerate(check_rem_node):
                resp = self.ha_rest.get_node_health_status(
                    exp_key='state', exp_val=state, node_id=node_check)
                assert_utils.assert_true(resp[0], resp[1])
                resp = self.ha_obj.verify_node_health_status(
                    response=resp_table, status=state, node_id=node_check)
                assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["fault"], False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info(
                "Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(
                node, self.num_nodes, self.node_list)
            assert_utils.assert_true(
                resp, "Some services are down for other nodes.")

            LOGGER.info("Power on {}".format(node_name))
            if self.setup_type == "VM":
                vm_name = self.host_list[node].split(".")[0]
                res = system_utils.execute_cmd(
                    common_cmds.CMD_VM_POWER_ON .format(
                        self.vm_username, self.vm_password, vm_name))
                assert_utils.assert_true(
                    res[0], "VM power on command not executed")
            else:
                self.bmc_list[node].bmc_node_power_on_off(
                    self.bmc_ip_list[node], self.bmc_user, self.bmc_pwd, "on")
            # SSC cloud is taking time to start VM host hence max_timeout 120
            resp = self.ha_obj.polling_host(
                max_timeout=120, host_index=node, exp_resp=True, host_list=self.host_list)
            assert_utils.assert_true(
                resp, "Host has not powered on yet.")
            LOGGER.info("{} has powered on".format(node_name))
            # To get all the services up and running
            time.sleep(40)

            LOGGER.info("Check all nodes are back online in CLI and REST.")
            resp = self.ha_rest.get_node_health_status(
                exp_key='status', exp_val='online')
            assert_utils.assert_true(resp[0], resp[1])
            resp = sys_obj.check_health_status(
                common_cmds.CMD_HEALTH_SHOW.format("node"))
            assert_utils.assert_true(resp[0], resp[1])
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.info(
                "Response for health check for all nodes: {}".format(resp_table))
            resp = self.ha_obj.verify_node_health_status(
                response=resp_table, status="online")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            sys_obj.logout_cortx_cli()
            sys_obj.close_connection()
            LOGGER.info(
                "Node down/up worked fine for node: {}".format(node_name))

        LOGGER.info(
            "Completed: Test to check node status one by one for all nodes with safe shutdown.")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-22574")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_unsafe(self):
        """
        Test to Check that correct node status is shown in Cortx CLI and REST when node goes down
        and comes back up(one by one, unsafe shutdown)
        """
        LOGGER.info(
            "Started: Test to check node status one by one for all nodes with unsafe shutdown.")

        LOGGER.info("Check in cortxcli and REST that all nodes are shown online.")
        self.status_nodes_online()

        LOGGER.info("Shutdown nodes one by one and check status.")
        for node in range(self.num_nodes):
            LOGGER.info("Shutting down %s", self.srvnode_list[node])
            if self.setup_type == "HW":
                LOGGER.debug(
                    "HW: Need to disable stonith on the node before shutdown")
                # TODO: Need to get the command once F-11A available.
            if self.setup_type == "VM":
                vm_name = self.host_list[node].split(".")[0]
                res = system_utils.execute_cmd(
                    common_cmds.CMD_VM_POWER_OFF.format(
                        self.vm_username, self.vm_password, vm_name))
                assert_utils.assert_true(
                    res[0], f"{common_cmds.CMD_VM_POWER_OFF} Execution Failed")
            else:
                self.bmc_list[node].bmc_node_power_on_off(
                    self.bmc_ip_list[node], self.bmc_user, self.bmc_pwd, "off")
            LOGGER.info(
                "Check if the %s has shutdown.",
                self.srvnode_list[node])
            resp = self.ha_obj.polling_host(
                max_timeout=120, host_index=node, exp_resp=False, host_list=self.host_list)
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not shutdown yet.")
            LOGGER.info("%s is powered off.", self.host_list[node])
            LOGGER.info(
                "Check %s is in Failed state and other nodes state is not affected",
                self.srvnode_list[node])
            LOGGER.info("Get the new node on which CSM service is running.")
            if self.srvnode_list[node] == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node + 1]
            sys_obj = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            sys_obj.open_connection()
            resp = sys_obj.login_cortx_cli()
            assert_utils.assert_true(resp[0], resp[1])
            resp = sys_obj.check_health_status(
                common_cmds.CMD_HEALTH_SHOW.format("node"))
            assert_utils.assert_true(resp[0], resp[1])
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.debug(
                "Response for node health in cortxcli is: %s",
                resp_table)
            check_rem_node = [
                "failed" if num == node else "online" for num in range(
                    self.num_nodes)]
            for node_check, state in enumerate(check_rem_node):
                resp = self.ha_rest.get_node_health_status(
                    exp_key='state', exp_val=state, node_id=node_check)
                assert_utils.assert_true(resp[0], resp[1])
                resp = self.ha_obj.verify_node_health_status(
                    response=resp_table, status=state, node_id=node_check)
                assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["fault"], False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            LOGGER.info(
                "Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(
                node, self.num_nodes, self.node_list)
            assert_utils.assert_true(
                resp, "Some services are down for other nodes.")
            LOGGER.info("Power on %s", self.srvnode_list[node])
            if self.setup_type == "VM":
                res = system_utils.execute_cmd(
                    common_cmds.CMD_VM_POWER_ON.format(
                        self.vm_username, self.vm_password, vm_name))
                assert_utils.assert_true(
                    res[0], "VM power on command not executed")
            else:
                self.bmc_list[node].bmc_node_power_on_off(
                    self.bmc_ip_list[node], self.bmc_user, self.bmc_pwd, "on")

            # SSC cloud is taking more time to start VM host hence max_timeout
            # 120
            resp = self.ha_obj.polling_host(
                max_timeout=120, host_index=node, exp_resp=True, host_list=self.host_list)
            assert_utils.assert_true(
                resp, f"{self.host_list[node]} has not powered on yet.")
            LOGGER.info("%s is powered on.", self.host_list[node])
            # To get all the services up and running
            time.sleep(40)
            LOGGER.info("Check all nodes are back online in CLI.")
            resp = self.ha_rest.get_node_health_status(
                exp_key='status', exp_val='online')
            assert_utils.assert_true(resp[0], resp[1])
            resp = sys_obj.check_health_status(
                common_cmds.CMD_HEALTH_SHOW.format("node"))
            assert_utils.assert_true(resp[0], resp[1])
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.info(
                "Response for node health in cortxcli is: %s", resp_table)
            resp = self.ha_obj.verify_node_health_status(
                response=resp_table, status="online")
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("All nodes are online in CLI.")
            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            resp = sys_obj.logout_cortx_cli()
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj.close_connection()
            LOGGER.info(
                "Node down/up worked fine for node: %s",
                self.srvnode_list[node])
        LOGGER.info(
            "Completed: Test to check node status one by one for all nodes with unsafe shutdown.")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-23274")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_nw_down(self):
        """
        Test to Check that correct node status is shown in Cortx CLI and REST when nw interface
        on node goes down and comes back up (one by one)
        """
        LOGGER.info(
            "Started: Test to check node status one by one on all nodes when nw interface on node goes"
            "down and comes back up")

        LOGGER.info("Check in cortxcli and REST that all nodes are shown online.")
        self.status_nodes_online()

        LOGGER.info("Get the list of private data interfaces for all nodes.")
        response = self.ha_obj.get_iface_ip_list(node_list=self.node_list, num_nodes=self.num_nodes)
        iface_list = response[0]
        private_ip_list = response[1]
        LOGGER.debug("List of private data IP : {} and interfaces on all nodes: {}"
                     .format(private_ip_list, iface_list))

        for node in range(self.num_nodes):
            node_name = self.srvnode_list[node]
            LOGGER.info("Make the private data interface down for {}".format(node_name))
            self.node_list[node].execute_cmd(common_cmds.IP_LINK_CMD
                                             .format(iface_list[node], "down"), read_lines=True)
            if node_name == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node + 1]
            resp = nd_obj.execute_cmd(common_cmds.CMD_PING.format(private_ip_list[node]),
                                      read_lines=True, exc=False)
            assert_utils.assert_in("Name or service not known", resp[1][0], "Node interface still up.")

            LOGGER.info(
                "Check in cortxcli and REST that the status is changed for {} to Failed".format(node_name))
            sys_obj = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            sys_obj.open_connection()
            res = sys_obj.login_cortx_cli()
            assert_utils.assert_true(res[0], res[1])
            resp = sys_obj.check_health_status(
                common_cmds.CMD_HEALTH_SHOW.format("node"))
            assert_utils.assert_true(resp[0], resp[1])
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.debug(
                "Response in cortxcli is: {}".format(resp_table))
            check_rem_node = [
                "failed" if num == node else "online" for num in range(
                    self.num_nodes)]
            for node_check, state in enumerate(check_rem_node):
                resp = self.ha_rest.get_node_health_status(
                    exp_key='state', exp_val=state, node_id=node_check)
                assert_utils.assert_true(resp[0], resp[1])
                resp = self.ha_obj.verify_node_health_status(
                    response=resp_table, status=state, node_id=node_check)
                assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["fault"], False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info(
                "Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(
                node, self.num_nodes, self.node_list)
            assert_utils.assert_true(
                resp, "Some services are down for other nodes.")

            LOGGER.info("Make the private data interface back up for {}".format(node_name))
            self.node_list[node].execute_cmd(common_cmds.IP_LINK_CMD
                                             .format(iface_list[node], "up"), read_lines=True)
            resp = nd_obj.execute_cmd(common_cmds.CMD_PING.format(private_ip_list[node]),
                                      read_lines=True, exc=False)
            assert_utils.assert_not_in("Name or service not known", resp[1][0],
                                       "Node interface still down.")
            # To get all the services up and running
            time.sleep(40)
            LOGGER.info("Check all nodes are back online in CLI and REST.")
            resp = self.ha_rest.get_node_health_status(
                exp_key='status', exp_val='online')
            assert_utils.assert_true(resp[0], resp[1])
            resp = sys_obj.check_health_status(
                common_cmds.CMD_HEALTH_SHOW.format("node"))
            assert_utils.assert_true(resp[0], resp[1])
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.info(
                "Response for health check for all nodes: {}".format(resp_table))
            resp = self.ha_obj.verify_node_health_status(
                response=resp_table, status="online")
            assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            sys_obj.logout_cortx_cli()
            sys_obj.close_connection()
            LOGGER.info(
                "Node nw interface down/up worked fine for node: {}".format(node_name))

        LOGGER.info(
            "Completed: Test to check node status one by one on all nodes when nw interface on node goes"
            "down and comes back up")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-22623")
    @CTFailOn(error_handler)
    def test_single_node_multiple_times_safe(self):
        """
        Test to Check that correct node status is shown in Cortx CLI and REST, when node
        goes down and comes back up(single node multiple times, safe shutdown)
        """
        LOGGER.info(
            "Started: Test to check single node status with multiple safe shutdown.")

        LOGGER.info("Check in cortxcli and REST that all nodes are shown online.")
        self.status_nodes_online()
        LOGGER.info("Get the node for multiple unsafe shutdown.")
        test_cli_node = random.choice([obj for obj in self.sys_list])
        node_index = self.sys_list.index(test_cli_node)

        LOGGER.info(
            "Shutdown %s node multiple time and check status.",
            self.srvnode_list[node_index])
        for loop in range(11):
            LOGGER.info(
                "Shutting down node: %s, Loop: %s",
                self.srvnode_list[node_index],
                loop)
            if self.setup_type == "HW":
                LOGGER.debug(
                    "HW: Need to disable stonith on the %s before shutdown",
                    self.srvnode_list[node_index])
                # TODO: Need to get the command once F-11A available.
            resp = self.node_list[node_index].execute_cmd(cmd="shutdown now")
            LOGGER.debug("Response for shutdown: %s", resp)
            LOGGER.info(
                "Check if the %s has shutdown.",
                self.srvnode_list[node_index])
            resp = self.ha_obj.polling_host(
                max_timeout=120, host_index=node_index, exp_resp=False,  host_list=self.host_list)
            assert_utils.assert_true(
                resp, f"{self.host_list[node_index]} has not shutdown yet.")
            LOGGER.info("%s is powered off.", self.host_list[node_index])

            LOGGER.info("Get the new node on which CSM service failover.")
            if self.srvnode_list[node_index] == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node_index + 1]
            sys_obj = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            sys_obj.open_connection()
            resp = sys_obj.login_cortx_cli()
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Check %s is in Failed state and other nodes state is not affected in CLI and REST ",
                self.srvnode_list[node_index])
            resp = sys_obj.check_health_status(
                common_cmds.CMD_HEALTH_SHOW.format("node"))
            assert_utils.assert_true(resp[0], resp[1])
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.debug(
                "Response for node health in cortxcli is: %s",
                resp_table)
            check_rem_node = [
                "failed" if num == node_index else "online" for num in range(
                    self.num_nodes)]
            for node_check, state in enumerate(check_rem_node):
                resp = self.ha_rest.get_node_health_status(
                    exp_key='state', exp_val=state, node_id=node_check)
                assert_utils.assert_true(resp[0], resp[1])
                resp = self.ha_obj.verify_node_health_status(
                    response=resp_table, status=state, node_id=node_check)
                assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["fault"], False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info(
                "Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(
                node_index, self.num_nodes, self.node_list)
            assert_utils.assert_true(
                resp, "Some services are down for other nodes.")
            LOGGER.info("Power on %s", self.srvnode_list[node_index])
            if self.setup_type == "VM":
                vm_name = self.host_list[node_index].split(".")[0]
                res = system_utils.execute_cmd(
                    common_cmds.CMD_VM_POWER_ON.format(
                        self.vm_username, self.vm_password, vm_name))
                assert_utils.assert_true(
                    res[0], "VM power on command not executed")
            else:
                self.bmc_list[node_index].bmc_node_power_on_off(
                    self.bmc_ip_list[node_index], self.bmc_user, self.bmc_pwd, "on")
            # SSC cloud is taking more time to start VM host hence max_timeout
            # 120
            resp = self.ha_obj.polling_host(
                max_timeout=120, host_index=node_index, exp_resp=True,  host_list=self.host_list)
            assert_utils.assert_true(
                resp, f"{self.host_list[node_index]} has not powered on yet.")
            LOGGER.info("%s is powered on", self.host_list[node_index])

            # To get all the services up and running
            time.sleep(40)
            LOGGER.info("Check all nodes are back online in CLI and REST")
            resp = self.ha_rest.get_node_health_status(
                exp_key='status', exp_val='online')
            assert_utils.assert_true(resp[0], resp[1])
            resp = sys_obj.check_health_status(
                common_cmds.CMD_HEALTH_SHOW.format("node"))
            assert_utils.assert_true(resp[0], resp[1])
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.info(
                "Response for node health in cortxcli is: %s",
                resp_table)
            resp = self.ha_obj.verify_node_health_status(
                response=resp_table, status="online")
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Checked All nodes are online in CLI and REST.")

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            LOGGER.info("Logging out from cortxcli")
            resp = sys_obj.logout_cortx_cli()
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj.close_connection()
            LOGGER.info(
                "Node down/up worked fine for node: %s, Loop: %s",
                self.srvnode_list[node_index],
                loop)
        LOGGER.info(
            "Completed: Test to check single node status with multiple safe shutdown.")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-22626")
    @CTFailOn(error_handler)
    def test_single_node_multiple_times_unsafe(self):
        """
        Test to Check that correct node status is shown in Cortx CLI and REST, when node
        goes down and comes back up(single node multiple times, unsafe shutdown)
        """
        LOGGER.info(
            "Started: Test to check single node status with multiple unsafe shutdown.")

        LOGGER.info("Check in cortxcli and REST that all nodes are shown online.")
        self.status_nodes_online()
        LOGGER.info("Get the node for multiple unsafe shutdown.")
        test_cli_node = random.choice([obj for obj in self.sys_list])
        node_index = self.sys_list.index(test_cli_node)

        LOGGER.info(
            "Shutdown %s node multiple time and check status.",
            self.srvnode_list[node_index])
        for loop in range(11):
            LOGGER.info(
                "Shutting down node: %s, Loop: %s",
                self.srvnode_list[node_index],
                loop)
            if self.setup_type == "HW":
                LOGGER.debug(
                    "HW: Need to disable stonith on the node before shutdown")
                # TODO: Need to get the command once F-11A available.
            if self.setup_type == "VM":
                vm_name = self.host_list[node_index].split(".")[0]
                res = system_utils.execute_cmd(
                    common_cmds.CMD_VM_POWER_OFF.format(
                        self.vm_username, self.vm_password, vm_name))
                assert_utils.assert_true(
                    res[0], f"{common_cmds.CMD_VM_POWER_OFF} Execution Failed")
            else:
                self.bmc_list[node_index].bmc_node_power_on_off(
                    self.bmc_ip_list[node_index], self.bmc_user, self.bmc_pwd, "off")
            LOGGER.info(
                "Check if the %s has shutdown.",
                self.srvnode_list[node_index])
            resp = self.ha_obj.polling_host(
                max_timeout=120, host_index=node_index, exp_resp=False,  host_list=self.host_list)
            assert_utils.assert_true(
                resp, f"{self.host_list[node_index]} has not shutdown yet.")
            LOGGER.info("%s is powered off.", self.host_list[node_index])

            LOGGER.info("Get the new node on which CSM service failover.")
            if self.srvnode_list[node_index] == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node_index + 1]
            sys_obj = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            sys_obj.open_connection()
            resp = sys_obj.login_cortx_cli()
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info(
                "Check %s is in Failed state and other nodes state is not affected in CLI and REST ",
                self.srvnode_list[node_index])
            resp = sys_obj.check_health_status(
                common_cmds.CMD_HEALTH_SHOW.format("node"))
            assert_utils.assert_true(resp[0], resp[1])
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.debug(
                "Response for node health in cortxcli is: %s",
                resp_table)
            check_rem_node = [
                "failed" if num == node_index else "online" for num in range(
                    self.num_nodes)]
            for node_check, state in enumerate(check_rem_node):
                resp = self.ha_rest.get_node_health_status(
                    exp_key='state', exp_val=state, node_id=node_check)
                assert_utils.assert_true(resp[0], resp[1])
                resp = self.ha_obj.verify_node_health_status(
                    response=resp_table, status=state, node_id=node_check)
                assert_utils.assert_true(resp[0], resp[1])

            LOGGER.info("Check for the node down alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["fault"], False, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info(
                "Check that cortx services on other nodes are not affected.")
            resp = self.ha_obj.check_service_other_nodes(
                node_index, self.num_nodes, self.node_list)
            assert_utils.assert_true(
                resp, "Some services are down for other nodes.")
            LOGGER.info("Power on %s", self.srvnode_list[node_index])
            if self.setup_type == "VM":
                res = system_utils.execute_cmd(
                    common_cmds.CMD_VM_POWER_ON.format(
                        self.vm_username, self.vm_password, vm_name))
                assert_utils.assert_true(
                    res[0], "VM power on command not executed")
            else:
                self.bmc_list[node_index].bmc_node_power_on_off(
                    self.bmc_ip_list[node_index], self.bmc_user, self.bmc_pwd, "on")
            # SSC cloud is taking more time to start VM host hence max_timeout
            # 120
            resp = self.ha_obj.polling_host(
                max_timeout=120, host_index=node_index, exp_resp=True,  host_list=self.host_list)
            assert_utils.assert_true(
                resp, f"{self.host_list[node_index]} has not powered on yet.")
            LOGGER.info("%s is powered on", self.host_list[node_index])

            # To get all the services up and running
            time.sleep(40)
            LOGGER.info("Check all nodes are back online in CLI and REST")
            resp = self.ha_rest.get_node_health_status(
                exp_key='status', exp_val='online')
            assert_utils.assert_true(resp[0], resp[1])
            resp = sys_obj.check_health_status(
                common_cmds.CMD_HEALTH_SHOW.format("node"))
            assert_utils.assert_true(resp[0], resp[1])
            resp_table = sys_obj.split_table_response(resp[1])
            LOGGER.info(
                "Response for node health in cortxcli is: % s",
                resp_table)
            resp = self.ha_obj.verify_node_health_status(
                response=resp_table, status="online")
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Checked All nodes are online in CLI and REST.")

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus
            LOGGER.info("Logging out from cortxcli")
            resp = sys_obj.logout_cortx_cli()
            assert_utils.assert_true(resp[0], resp[1])
            sys_obj.close_connection()
            LOGGER.info(
                "Node down/up worked fine for node: %s, Loop: %s",
                self.srvnode_list[node_index],
                loop)
        LOGGER.info(
            "Completed: Test to check single node status with multiple unsafe shutdown.")
