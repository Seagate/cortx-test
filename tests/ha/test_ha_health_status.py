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
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from config import CMN_CFG, HA_CFG
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
        LOGGER.info("Logging into CORTXCLI as admin...")
        login = self.cli_obj1.login_cortx_cli()
        assert_utils.assert_true(login[0], login[1])
        LOGGER.info("Logged into CORTXCLI as admin successfully")
        LOGGER.info("ENDED: Setup Operations")

    def teardown_method(self):
        """
        This function will be invoked after each test function in the module.
        It is performing below operations.
            - Log out from CORTX CLI console.
        """
        if self.pri_node_logout:
            LOGGER.info("Logging out from CSMCLI console...")
            self.cli_obj1.logout_cortx_cli()
            LOGGER.info("Logged out from CSMCLI console successfully")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-22544")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_safe(self):
        """
        Test to Check that correct node status is shown in Cortx CLI when node goes offline and comes back
        online(one by one, safe shutdown)
        """
        LOGGER.info("Started: Test to check node status one by one for all nodes with safe shutdown.")

        LOGGER.info("Checking if all nodes online and PCS clean.")
        hlt_list = [self.hlt_obj1, self.hlt_obj2, self.hlt_obj3]
        for hlt_obj in hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are online adn PCS looks clean.")

        LOGGER.info("Check in cortxcli that all nodes are shown online.")
        