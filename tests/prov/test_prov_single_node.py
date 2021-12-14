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
import logging
import pytest
from commons.helpers.node_helper import Node
from commons import commands as common_cmds
from commons import constants as common_cnst
from commons.utils import assert_utils
from commons import pswdmanager
from config import CMN_CFG, PROV_CFG
from libs.prov.provisioner import Provisioner

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
        cls.host = CMN_CFG["nodes"][0]["hostname"]
        cls.build = os.getenv("Build", None)
        cls.build_branch = os.getenv("Build_Branch", "stable")
        if cls.build:
            if cls.build_branch == "stable" or cls.build_branch == "main":
                cls.build = "{}/{}".format(cls.build, "prod")
        else:
            cls.build = "last_successful_prod"
        cls.build_path = PROV_CFG["build_url"].format(
            cls.build_branch, cls.build)

        LOGGER.info(
            "User provided Hostname: {} and build path: {}".format(
                cls.host, cls.build_path))
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.nd_obj = Node(hostname=cls.host, username=cls.uname,
                          password=cls.passwd)
        cls.prov_obj = Provisioner()
        LOGGER.info("Done: Setup module operations")

    def teardown_method(self):
        """
        Teardown operations after each test.
        """
        LOGGER.info("Successfully performed Teardown operation")

    @pytest.mark.cluster_management_ops
    @pytest.mark.singlenode
    @pytest.mark.lr
    @pytest.mark.tags("TEST-19439")
    def test_deployment_single_node(self):
        """
        Test method for the single node VM deployment.
        This has 3 main stages: check for the required prerequisites, trigger the deployment jenkins job
        and after deployment done, check for services status.
        """
        LOGGER.info("Starting the prerequisite checks.")
        test_cfg = PROV_CFG["single-node"]["prereq"]

        LOGGER.info("Check that the host is pinging")
        cmd = common_cmds.CMD_PING.format(self.host)
        self.nd_obj.execute_cmd(cmd, read_lines=True)

        LOGGER.info("Checking number of volumes present")
        cmd = common_cmds.CMD_LSBLK
        count = self.nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("count : {}".format(int(count[0])))
        assert_utils.assert_greater_equal(
            int(count[0]), test_cfg["count"], "Need at least 2 disks for deployment")

        LOGGER.info("Checking OS release version")
        cmd = common_cmds.CMD_OS_REL
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        resp = resp[0].strip()
        LOGGER.info("os rel: {}".format(resp))
        assert_utils.assert_equal(resp, test_cfg["os_release"],
                                  "OS release is different than expected.")

        LOGGER.info("Checking kernel version")
        cmd = common_cmds.CMD_KRNL_VER
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        resp = resp[0].strip()
        LOGGER.info("kernel: {}".format(resp))
        assert_utils.assert_equal(
            resp,
            test_cfg["kernel"],
            "Kernel version differs than expected.")

        LOGGER.info("Starting the deployment steps.")
        test_cfg = PROV_CFG["single-node"]["deploy"]

        common_cnst.PARAMS["CORTX_BUILD"] = self.build_path
        common_cnst.PARAMS["HOST"] = self.host
        common_cnst.PARAMS["HOST_PASS"] = self.passwd
        token = pswdmanager.decrypt(common_cnst.TOKEN_NAME)
        output = Provisioner.build_job(
            test_cfg["job_name"], common_cnst.PARAMS, token)
        LOGGER.info("Jenkins Build URL: {}".format(output['url']))
        assert_utils.assert_equal(
            output['result'],
            test_cfg["success_msg"],
            "Deployment is not successful, please check the url.")

        LOGGER.info("Starting the post deployment checks.")
        test_cfg = PROV_CFG["system"]

        LOGGER.info("Check that all the services are up in hctl.")
        cmd = common_cmds.MOTR_STATUS_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("hctl status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                test_cfg["offline"], line, "Some services look offline.")

        LOGGER.info("Check that all services are up in pcs.")
        cmd = common_cmds.PCS_STATUS_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("PCS status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(
                test_cfg["stopped"], line, "Some services are not up.")
        LOGGER.info(
            "Successfully deployed the build after prereq checks and done post "
            "deploy checks as well.")
