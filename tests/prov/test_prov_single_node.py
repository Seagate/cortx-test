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
Prov test file for all the Prov tests scenarios for single node VM.
"""

import os
import time
import logging
import pytest
from commons.utils import system_utils as sys_utils
from commons.helpers.s3_helper import S3Helper
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons import constants as common_cons
from commons import commands as common_cmds
from config import CMN_CFG, PROV_CFG
from commons.ct_fail_on import CTFailOn
from commons.errorcodes import error_handler

# Global Constants
LOGGER = logging.getLogger(__name__)

class TestProvSingleNode:
    """
    Test suite for prov tests scenarios for single node VM.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup operations for the test file.
        """
        LOGGER.info("STARTED: Setup Module operations")
        cls.host = input('Specify hostname fqdn:\n')
        cls.uname = CMN_CFG["username"]
        cls.passwd = CMN_CFG["password"]
        cls.nd_obj = Node(hostname=cls.host, username=cls.uname,
                          password=cls.passwd)
        cls.hlt_obj = Health(hostname=cls.host, username=cls.uname,
                             password=cls.passwd)
        LOGGER.info("Done: Setup module operations")

    def setup_method(self):
        """
        Setup operations for each test.
        """
        pass

    def teardown_method(self):
        """
        Teardown operations after each test.
        """
        pass

    @CTFailOn(error_handler)
    @pytest.mark.prov
    @pytest.mark.singlenode
    def test_deployment_single_node(self):
        """
        Test method for the single node VM deployment.
        """
        LOGGER.info("Starting the prerequisite checks.")
        test_cfg = PROV_CFG["prereq"]

        LOGGER.info("Check that the host is pinging")
        cmd = common_cmds.CMD_PING.format(self.host)
        self.nd_obj.execute_cmd(cmd, read_lines=True)

        LOGGER.info("Checking number of volumes present")
        cmd = common_cmds.CMD_LSBLK
        count = self.nd_obj.execute_cmd(cmd, read_lines=True)
        assert count >= test_cfg["count"], "Need at least 2 disks for deployment"

        LOGGER.info("Checking kernel and release version")
        cmd = common_cmds.OS_REL_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        assert resp == test_cfg["os_release"], "OS release is different than expected."

        LOGGER.info("Checking kernel version")
        cmd = common_cmds.KRNL_VER_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        assert resp == test_cfg["kernel"], "Kernel version differs than expected."

        LOGGER.info("Starting the deployment steps.")
        test_cfg = PROV_CFG["deploy"]

        LOGGER.info("Starting the post deployment checks.")
        test_cfg = PROV_CFG["system"]

        LOGGER.info("Check that all the services are up in hctl.")
        cmd = common_cmds.MOTR_STATUS_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("hctl status: %s", resp)
        for line in resp:
            assert test_cfg["offline"] not in line, "Some services look offline."

        LOGGER.info("Check that all services are up in pcs.")
        cmd = common_cmds.PCS_STATUS_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("PCS status: %s", resp)
        for line in resp:
            assert test_cfg["stopped"] not in line, "Some services are not up."














