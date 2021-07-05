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

import logging
import os
import time

import pytest

from commons import commands as common_cmds
from commons import pswdmanager
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
        cls.csm_alerts_obj = SystemAlerts()
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

    def status_cluster_resource_online(self, node_obj=None):
        """
        Helper function to check that cluster/rack/site/nodes are shown online in cortx cli/REST
        before starting any other operations.
        """
        if node_obj is None:
            node_obj = self.node_list[0]

        LOGGER.info("Check the node which is running CSM service and login to CSM on that node.")
        sys_obj = self.ha_obj.check_csm_service(
            node_obj, self.srvnode_list, self.sys_list)

        LOGGER.info("Check cluster, site and rack health status is online in CLI and REST")
        resp = self.ha_obj.verify_csr_health_status(sys_obj, status="online")
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.check_csr_health_status_rest(exp_status='online')
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster, site and rack health status is online in CLI and REST")

        LOGGER.info("Check all nodes health status is online in CLI and REST")
        check_rem_node = ["online" for _ in range(self.num_nodes)]
        resp = self.ha_obj.verify_node_health_status(sys_obj, status=check_rem_node)
        assert_utils.assert_true(resp[0], resp[1])
        resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
        assert_utils.assert_true(resp[0], resp[1])
        sys_obj.logout_cortx_cli()
        sys_obj.close_connection()
        LOGGER.info("All nodes health status is online in CLI and REST")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-22893")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_safe_shutdown(self):
        """
        Test to Check that correct cluster status is shown in Cortx CLI and REST when node goes down
        and comes back up(one by one, safe shutdown)
        """
        LOGGER.info("Started: Test to check cluster status, with safe shutdown nodes one by one.")

        LOGGER.info("Check in cortxcli and REST that cluster is shown online.")
        self.status_cluster_resource_online()

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
                "Check in cortxcli and REST that the status is changed for {} to Failed".format(
                    node_name))
            if node_name == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node + 1]
            sys_obj = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            check_rem_node = [
                "failed" if num == node else "online" for num in range(
                    self.num_nodes)]
            # Verify node status via CortxCLI
            resp = self.ha_obj.verify_node_health_status(
                sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            # Verify Cluster/Site/Rack status via CortxCLI
            resp = self.ha_obj.verify_csr_health_status(sys_obj, "failed")
            assert_utils.assert_true(resp[0], resp[1])

            # Verify node status via REST
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            # Verify Cluster/Site/Rack status via CortxCLI
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
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
                    common_cmds.CMD_VM_POWER_ON.format(
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
            self.status_cluster_resource_online(node_obj=nd_obj)

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info(
                "Node down/up worked fine for node: {}".format(node_name))

        LOGGER.info(
            "Completed: Test to check node status one by one for all nodes with safe shutdown.")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-22895")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_unsafe_shutdown(self):
        """
        Test to check that correct cluster status is shown in Cortx CLI when nodes goes
        offline and comes back online(one by one, unsafe shutdown)
        """
        LOGGER.info(
            "Started: Test to check cluster status one by one by making all nodes down and up, "
            "with unsafe shutdown.")

        LOGGER.info("Check in cortxcli and REST that cluster is shown online.")
        self.status_cluster_resource_online()

        LOGGER.info("Shutdown nodes one by one and check status.")
        for node in range(self.num_nodes):
            node_name = self.srvnode_list[node]
            LOGGER.info("Shutting down {}".format(node_name))
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
            LOGGER.info("Check if the {} has shutdown.".format(node_name))
            resp = self.ha_obj.polling_host(
                max_timeout=120, host_index=node, exp_resp=False, host_list=self.host_list)
            assert_utils.assert_true(
                resp, "Host has not shutdown yet.")

            LOGGER.info(
                "Check in cortxcli and REST that the status is changed for {} to Failed".format(
                    node_name))
            if node_name == self.srvnode_list[-1]:
                nd_obj = self.node_list[0]
            else:
                nd_obj = self.node_list[node + 1]
            sys_obj = self.ha_obj.check_csm_service(
                nd_obj, self.srvnode_list, self.sys_list)
            check_rem_node = [
                "failed" if num == node else "online" for num in range(
                    self.num_nodes)]
            # Verify node status via CortxCLI
            resp = self.ha_obj.verify_node_health_status(
                sys_obj, status=check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            # Verify Cluster/Site/Rack status via CortxCLI
            resp = self.ha_obj.verify_csr_health_status(sys_obj, "failed")
            assert_utils.assert_true(resp[0], resp[1])

            # Verify node status via REST
            resp = self.ha_rest.verify_node_health_status_rest(check_rem_node)
            assert_utils.assert_true(resp[0], resp[1])
            # Verify Cluster/Site/Rack status via CortxCLI
            resp = self.ha_rest.check_csr_health_status_rest("degraded")
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
                    common_cmds.CMD_VM_POWER_ON.format(
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
            self.status_cluster_resource_online(node_obj=nd_obj)

            LOGGER.info("Check for the node back up alert.")
            resp = self.csm_alerts_obj.verify_csm_response(
                self.starttime, self.alert_type["resolved"], True, "iem")
            assert_utils.assert_true(resp, "Failed to get alert in CSM")
            # TODO: If CSM REST getting changed, add alert check from msg bus

            LOGGER.info(
                "Node down/up worked fine for node: {}".format(node_name))

        LOGGER.info(
            "Completed: Test to check node status one by one for all nodes with safe shutdown.")

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

        LOGGER.info("Check in cortxcli and REST that all nodes & cluster/rack/site are online.")
        self.status_cluster_resource_online()

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

        LOGGER.info("Check in cortxcli and REST that all nodes & cluster/rack/site are online.")
        self.status_cluster_resource_online()
