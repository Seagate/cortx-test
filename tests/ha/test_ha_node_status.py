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
from commons import commands as common_cmds
from commons.utils import assert_utils
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler
from config import CMN_CFG, HA_CFG
from libs.prov.provisioner import Provisioner

# Global Constants
LOGGER = logging.getLogger(__name__)


class TestNodeStatus:
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

        cls.host1 = CMN_CFG["nodes"][0]["hostname"]
        cls.uname1 = CMN_CFG["nodes"][0]["username"]
        cls.passwd1 = CMN_CFG["nodes"][0]["password"]
        cls.nd1_obj = Node(hostname=cls.host1, username=cls.uname1,
                           password=cls.passwd1)
        cls.hlt_obj1 = Health(hostname=cls.host1, username=cls.uname1,
                              password=cls.passwd1)

        cls.host2 = CMN_CFG["nodes"][1]["hostname"]
        cls.uname2 = CMN_CFG["nodes"][1]["username"]
        cls.passwd2 = CMN_CFG["nodes"][1]["password"]
        cls.nd2_obj = Node(hostname=cls.host2, username=cls.uname2,
                           password=cls.passwd2)
        cls.hlt_obj2 = Health(hostname=cls.host2, username=cls.uname2,
                              password=cls.passwd2)

        cls.host3 = CMN_CFG["nodes"][2]["hostname"]
        cls.uname3 = CMN_CFG["nodes"][2]["username"]
        cls.passwd3 = CMN_CFG["nodes"][2]["password"]
        cls.nd3_obj = Node(hostname=cls.host3, username=cls.uname3,
                           password=cls.passwd3)
        cls.hlt_obj3 = Health(hostname=cls.host3, username=cls.uname3,
                              password=cls.passwd3)

        LOGGER.info("Done: Setup module operations")

    @pytest.mark.ha
    @pytest.mark.tags("TEST-22544")
    @CTFailOn(error_handler)
    def test_nodes_one_by_one_safe(self):
        """
        Test to Check that correct node status is shown in Cortx CLI when node goes offline and comes back
        online(one by one, safe shutdown)
        """
        test_cfg = HA_CFG["common"]
        node_obj_list = [self.nd1_obj, self.nd2_obj, self.nd3_obj]
        LOGGER.info("Check that the host is pinging")
        for nd_obj in node_obj_list:
            nd_obj.execute_cmd(
                common_cmds.CMD_PING.format(
                    nd_obj.hostname),
                read_lines=True)

        LOGGER.info("Check that all the services are up in hctl.")
        cmd = common_cmds.MOTR_STATUS_CMD
        resp = self.nd1_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("hctl status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                "offline", line, "Some services look offline.")

        LOGGER.info("Check that all services are up in pcs.")
        cmd = common_cmds.PCS_STATUS_CMD
        resp = self.nd1_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("PCS status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                "Stopped", line, "Some services are not up.")

        