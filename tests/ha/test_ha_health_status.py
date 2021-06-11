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
from config import CMN_CFG, HA_CFG
from commons import pswdmanager
from libs.csm.cli.cortx_cli_system import CortxCliSystemtOperations
from libs.csm.cli.cortx_cli import CortxCli

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
        cls.vm_username = os.getenv("QA_VM_POOL_ID",
                                    pswdmanager.decrypt(HA_CFG["vm_params"]["uname"]))
        cls.vm_password = os.getenv("QA_VM_POOL_PASSWORD",
                                    pswdmanager.decrypt(HA_CFG["vm_params"]["passwd"]))

        cls.host1 = CMN_CFG["nodes"][0]["hostname"]
        cls.uname1 = CMN_CFG["nodes"][0]["username"]
        cls.passwd1 = CMN_CFG["nodes"][0]["password"]
        cls.nd1_obj = Node(hostname=cls.host1, username=cls.uname1,
                           password=cls.passwd1)
        cls.hlt_obj1 = Health(hostname=cls.host1, username=cls.uname1,
                              password=cls.passwd1)
        cls.bmc_obj1 = Bmc(hostname=cls.host1, username=cls.uname1,
                              password=cls.passwd1)
        cls.sys_obj1 = CortxCliSystemtOperations(
            host=cls.host1, username=cls.uname1, password=cls.passwd1)
        cls.cli_obj1 = CortxCli(host=cls.host1,
                                username=cls.uname1, password=cls.passwd1)

        cls.host2 = CMN_CFG["nodes"][1]["hostname"]
        cls.uname2 = CMN_CFG["nodes"][1]["username"]
        cls.passwd2 = CMN_CFG["nodes"][1]["password"]
        cls.nd2_obj = Node(hostname=cls.host2, username=cls.uname2,
                           password=cls.passwd2)
        cls.hlt_obj2 = Health(hostname=cls.host2, username=cls.uname2,
                              password=cls.passwd2)
        cls.bmc_obj2 = Bmc(hostname=cls.host2, username=cls.uname2,
                              password=cls.passwd2)
        cls.sys_obj2 = CortxCliSystemtOperations(
            host=cls.host2, username=cls.uname2, password=cls.passwd2)
        cls.cli_obj2 = CortxCli(host=cls.host2,
                                username=cls.uname2, password=cls.passwd2)

        cls.host3 = CMN_CFG["nodes"][2]["hostname"]
        cls.uname3 = CMN_CFG["nodes"][2]["username"]
        cls.passwd3 = CMN_CFG["nodes"][2]["password"]
        cls.nd3_obj = Node(hostname=cls.host3, username=cls.uname3,
                           password=cls.passwd3)
        cls.hlt_obj3 = Health(hostname=cls.host3, username=cls.uname3,
                              password=cls.passwd3)
        cls.bmc_obj3 = Bmc(hostname=cls.host3, username=cls.uname3,
                              password=cls.passwd3)
        cls.sys_obj3 = CortxCliSystemtOperations(
            host=cls.host3, username=cls.uname3, password=cls.passwd3)
        cls.cli_obj3 = CortxCli(host=cls.host3,
                                username=cls.uname3, password=cls.passwd3)

        LOGGER.info("Done: Setup module operations")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        It is performing below operations as pre-requisites.
            - Login to CSMCLI as admin
        """
        LOGGER.info("STARTED: Setup Operations")
        self.node_list = [self.nd1_obj, self.nd2_obj, self.nd3_obj]
        self.host_list = [self.host1, self.host2, self.host3]
        self.sys_list = [self.sys_obj1, self.sys_obj2, self.sys_obj3]
        self.bmc_list = [self.bmc_obj1, self.bmc_obj2, self.bmc_obj3]
        if self.setup_type == "HW":
            self.bmc_ip1 = self.bmc_obj1.get_bmc_ip()
            self.bmc_ip2 = self.bmc_obj2.get_bmc_ip()
            self.bmc_ip3 = self.bmc_obj3.get_bmc_ip()
            self.bmc_ip_list = [self.bmc_ip1, self.bmc_ip2, self.bmc_ip3]
        LOGGER.info("Checking if all nodes online and PCS clean.")
        self.hlt_list = [self.hlt_obj1, self.hlt_obj2, self.hlt_obj3]
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are online and PCS looks clean.")

        LOGGER.info("ENDED: Setup Operations")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Log out from CORTX CLI console.
        """

    def check_csm_service(self, nd_obj):
        """
        Helper function to get the node on which the CSM service is running.
        :param nd_obj: node object for running pcs command
        :return: sys_obj
        """
        res = nd_obj.execute_cmd(common_cmds.CMD_PCS_SERV.format("csm_agent"))
        for line in res:
            if "srvnode-1" in line:
                sys_obj = self.sys_obj1
            if "srvnode-2" in line:
                sys_obj = self.sys_obj2
            if "srvnode-3" in line:
                sys_obj = self.sys_obj3

        return sys_obj

    def check_service_other_nodes(self, node_id):
        """
        Helper function to get services status on nodes which are online.
        :param node_id: node which is down to be skipped
        :return: boolean
        """
        for node in range(3):
            if node != node_id:
                node_name = "srvnode-{}".format(node+1)
                res = self.node_list[node].execute_cmd(common_cmds.CMD_PCS_GREP.format(node_name))
                for line in res:
                    if "FAILED" in line or "Stopped" in line:
                        return False
        return True


    @pytest.mark.ha
    @pytest.mark.tags("TEST-22544")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_safe(self):
        """
        Test to Check that correct node status is shown in Cortx CLI when node goes offline and comes back
        online(one by one, safe shutdown)
        """
        LOGGER.info("Started: Test to check node status one by one for all nodes with safe shutdown.")

        LOGGER.info("Check in cortxcli that all nodes are shown online.")
        sys_obj = self.check_csm_service(self.nd1_obj)
        resp = sys_obj.check_health_status(common_cmds.CMD_HEALTH_SHOW.format("node"))
        assert_utils.assert_true(resp[0], resp[1])
        resp_table =  self.cli_obj1.split_table_response(resp[1])
        LOGGER.info("Response for health check for all nodes: {}".format(resp_table))
        #TODO: assert if any node is offline
        sys_obj.logout_cortx_cli()
        LOGGER.info("All nodes are online.")

        LOGGER.info("Shutdown nodes one by one and check status.")
        for node in range(3):
            node_name = "srvnode-{}".format(node+1)
            LOGGER.info("Shutting down {}".format(node_name))
            if self.setup_type == "HW":
                LOGGER.debug("HW: Need to disable stonith on the node before shutdown")
                #TODO: Need to get the command once F-11A available.
            resp = self.node_list[node].execute_cmd(cmd="shutdown now")
            LOGGER.debug("Response for shutdown: {}".format(resp))
            LOGGER.info("Check if the node has shutdown.")
            time.sleep(10)
            resp = system_utils.check_ping(self.host_list[node])
            assert_utils.assert_not_equal(resp, 0, "Host has not shutdown yet.")
            LOGGER.info("Check in cortxcli that the status is changed for node to offline")
            if node == 2:
                nd_obj = self.nd1_obj
            else:
                nd_obj = self.node_list[node+1]
            sys_obj = self.check_csm_service(nd_obj)
            resp = sys_obj.check_health_status(common_cmds.CMD_HEALTH_SHOW.format("node"))
            assert_utils.assert_true(resp[0], resp[1])
            resp_table = self.cli_obj1.split_table_response(resp[1])
            LOGGER.debug("Response for {} in cortxcli is: {}".format(node_name, resp_table))
            #TODO: Check if node is shown offline and other nodes as online
            LOGGER.info("Check that cortx services on other nodes are not affected.")
            resp = self.check_service_other_nodes(node)
            assert_utils.assert_true(resp, "Some services are down for other nodes.")
            LOGGER.info("Power on {}".format(node_name))
            if self.setup_type == "VM":
                vm_name = self.host_list[node].split(".")[0]
                res = system_utils.execute_cmd(common_cmds.CMD_VM_POWER_ON
                                         .format(self.vm_username, self.vm_password, vm_name))
                assert_utils.assert_true(res[0], "VM power on command not executed")
            else:
                self.bmc_list[node].bmc_node_power_on_off(self.bmc_ip_list[node], self.bmc_user,
                                                     self.bmc_pwd, "on")
            time.sleep(40)
            resp = system_utils.check_ping(self.host_list[node])
            assert_utils.assert_equal(resp, 0, "Host has not powered on yet.")
            LOGGER.info("Node {} has powered on".format(node_name))
            LOGGER.info("Check health of the cluster.")
            for hlt_obj in self.hlt_list:
                res = hlt_obj.check_node_health()
                assert_utils.assert_true(res[0], res[1])
            LOGGER.info("All nodes are online and PCS looks clean.")

        LOGGER.info("Once all nodes online check the same again in cortxcli")
        sys_obj = self.check_csm_service(self.nd1_obj)
        resp = sys_obj.check_health_status(common_cmds.CMD_HEALTH_SHOW.format("node"))
        assert_utils.assert_true(resp[0], resp[1])
        resp_table = self.cli_obj1.split_table_response(resp[1])
        LOGGER.info("Response for health check for all nodes: {}".format(resp_table))
        # TODO: assert if any node is offline
        LOGGER.info("All nodes shown online in cortxcli.")

        LOGGER.info("Completed: Test to check node status one by one for all nodes with safe shutdown.")
