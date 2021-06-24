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
Prov test file for all the Prov tests scenarios for SW update disruptive.
"""

import os
import logging
import random
import pytest
import json
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons import commands as common_cmds
from commons import constants as common_cnst
from commons.utils import assert_utils
from commons import pswdmanager
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from config import CMN_CFG, PROV_CFG
from libs.prov.prov_upgrade import ProvSWUpgrade

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestSWUpdateDisruptive:
    """
    Test suite for prov tests scenarios for SW update disruptive.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.prov_obj = ProvSWUpgrade()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.build_update1 = os.getenv("Build_update1", PROV_CFG["build_def"])
        cls.build_update2 = os.getenv("Build_update2", PROV_CFG["build_def"])
        cls.build_update1 = "{}/{}".format(cls.build_update1,
                                   "prod") if cls.build_update1 else "last_successful_prod"
        cls.build_update2 = "{}/{}".format(cls.build_update2,
                                           "prod") if cls.build_update2 else "last_successful_prod"
        cls.build_branch = os.getenv("Build_Branch", "stable")
        cls.build_iso1 = PROV_CFG["build_iso"].format(
            cls.build_branch, cls.build_update1, cls.build_update1)
        cls.build_sig1 = PROV_CFG["build_sig"].format(
            cls.build_branch, cls.build_update1, cls.build_update1)
        cls.build_key1 = PROV_CFG["build_key"].format(
            cls.build_branch, cls.build_update1)
        cls.build_iso2 = PROV_CFG["build_iso"].format(
            cls.build_branch, cls.build_update2, cls.build_update2)
        cls.build_sig2 = PROV_CFG["build_sig"].format(
            cls.build_branch, cls.build_update2, cls.build_update2)
        cls.build_key2 = PROV_CFG["build_key"].format(
            cls.build_branch, cls.build_update2)
        cls.iso1_list = [cls.build_iso1, cls.build_sig1, cls.build_key1]
        cls.iso2_list = [cls.build_iso2, cls.build_sig2, cls.build_key2]
        cls.node_list = []
        cls.host_list = []
        cls.hlt_list = []
        cls.srvnode_list = []

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

        LOGGER.info("Done: Setup module operations")

    def setup_method(self):
        """
        This function will be invoked prior to each test case.
        """
        LOGGER.info("STARTED: Setup Operations")
        LOGGER.info("Checking if all nodes online and PCS clean.")
        for hlt_obj in self.hlt_list:
            res = hlt_obj.check_node_health()
            assert_utils.assert_true(res[0], res[1])
        LOGGER.info("All nodes are online and PCS looks clean.")
        LOGGER.info("ENDED: Setup Operations")

    @pytest.mark.cluster_management_ops
    @pytest.mark.tags("TEST-23175")
    @CTFailOn(error_handler)
    def sw_upgrade(self):
        """
        This test will trigger SW upgrade with correct ISO and on healthy system to check
        if SW upgrade command works fine. Also once process is complete, it will check if new
        version is shown on provisioner as well as CSM and check system health and Run IOs.
        """
        LOGGER.info("Started: SW upgrade disruptive for CORTX sw components.")

        nd_obj1 = self.node_list[0]
        LOGGER.info("Check the current version of the build.")
        resp = nd_obj1.execute_cmd(common_cmds.CMD_SW_VER, read_lines=True)
        data = json.loads(resp[0])
        build_org = data["BUILD"]
        LOGGER.info("Current version of build on system: {}".format(build_org))

        LOGGER.info("Download the upgrade ISO, SIG file and GPG key")
        tmp_dir = "/root/iso/"
        nd_obj1.make_dir(tmp_dir)
        for dnld in self.iso1_list:
            nd_obj1.execute_cmd(common_cmds.CMD_WGET.format(tmp_dir, dnld), read_lines=True)
        LOGGER.info("Set the update repo.")
