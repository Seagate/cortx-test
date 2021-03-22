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

import jenkins
import time
import logging
import pytest
from commons.helpers.health_helper import Health
from commons.helpers.node_helper import Node
from commons import commands as common_cmds
from commons import constants as common_cnst
from commons.utils import assert_utils
from commons import pswdmanager
from commons import params as prm
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
        cls.host = pytest.host_fqdn
        cls.build_path = pytest.buildpath
        LOGGER.info("User provided Hostname: {} and build path: {}".format(cls.host, cls.build_path))
        cls.uname = CMN_CFG["nodes"][0]["username"]
        cls.passwd = CMN_CFG["nodes"][0]["password"]
        cls.nd_obj = Node(hostname=cls.host, username=cls.uname,
                          password=cls.passwd)
        cls.hlt_obj = Health(hostname=cls.host, username=cls.uname,
                             password=cls.passwd)
        LOGGER.info("Done: Setup module operations")

    def setup_method(self):
        """
        Setup operations for each test.
        """

    def build_job(self, name: str, parameters: dict=None, token: str=None):
        """
        Helper function to start the jenkins job.
        :param name: Name of the jenkins job
        :param parameters: Dict of different parameters to be passed
        :param token: Authentication Token for jenkins job
        :return: response
        """
        username = pswdmanager.decrypt(common_cnst.JENKINS_USERNAME)
        password = pswdmanager.decrypt(common_cnst.JENKINS_PASSWORD)
        self.jenkins_server = jenkins.Jenkins(prm.JENKINS_URL, username=username, password=password)
        LOGGER.debug("Jenkins_server obj: {}".format(self.jenkins_server))
        completed_build_number = self.jenkins_server.get_job_info(name)['lastCompletedBuild']['number']
        next_build_number = self.jenkins_server.get_job_info(name)['nextBuildNumber']
        LOGGER.info(
            "Complete build number: {} and  Next build number: {}".format(completed_build_number, next_build_number))
        self.jenkins_server.build_job(name, parameters=parameters, token=token)
        time.sleep(10)
        LOGGER.info("Running the deployment job")
        while True:
            if self.jenkins_server.get_job_info(name)['lastCompletedBuild']['number'] == \
                    self.jenkins_server.get_job_info(name)['lastBuild']['number']:
                break
        build_info = self.jenkins_server.get_build_info(name, next_build_number)
        console_output = self.jenkins_server.get_build_console_output(name, next_build_number)
        LOGGER.debug("console output: {}".format(console_output))
        return build_info

    def teardown_method(self):
        """
        Teardown operations after each test.
        """

    @pytest.mark.prov
    @pytest.mark.singlenode
    @pytest.mark.tags("TEST-19439")
    @CTFailOn(error_handler)
    def test_deployment_single_node(self):
        """
        Test method for the single node VM deployment.
        This has 3 main stages: check for the required prerequisites, trigger the deployment jenkins job
        and after deployment done, check for services status.
        """
        LOGGER.info("Starting the prerequisite checks.")
        test_cfg = PROV_CFG["prereq"]

        LOGGER.info("Check that the host is pinging")
        cmd = common_cmds.CMD_PING.format(self.host)
        self.nd_obj.execute_cmd(cmd, read_lines=True)

        LOGGER.info("Checking number of volumes present")
        cmd = common_cmds.CMD_LSBLK
        count = self.nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("count : {}".format(int(count[0])))
        assert int(count[0]) >= test_cfg["count"], "Need at least 2 disks for deployment"

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
        assert_utils.assert_equal(resp, test_cfg["kernel"], "Kernel version differs than expected.")

        LOGGER.info("Starting the deployment steps.")
        test_cfg = PROV_CFG["deploy"]

        common_cnst.PARAMS["CORTX_BUILD"] = self.build_path
        common_cnst.PARAMS["HOST"] = self.host
        common_cnst.PARAMS["HOST_PASS"] = self.passwd
        token = pswdmanager.decrypt(common_cnst.TOKEN_NAME)
        output = self.build_job(test_cfg["job_name"], common_cnst.PARAMS, token)
        LOGGER.info("Jenkins Build URL: {}".format(output['url']))
        assert_utils.assert_equal(output['result'], test_cfg["success_msg"],
                                  "Deployment is not successful, please check the url.")

        LOGGER.info("Starting the post deployment checks.")
        test_cfg = PROV_CFG["system"]

        LOGGER.info("Check that all the services are up in hctl.")
        cmd = common_cmds.MOTR_STATUS_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("hctl status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(test_cfg["offline"], line, "Some services look offline.")

        LOGGER.info("Check that all services are up in pcs.")
        cmd = common_cmds.PCS_STATUS_CMD
        resp = self.nd_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.info("PCS status: %s", resp)
        for line in resp:
            assert_utils.assert_not_in(test_cfg["stopped"], line, "Some services are not up.")

        LOGGER.info("Successfully deployed the build after prereq checks and done post "
                    "deploy checks as well.")
