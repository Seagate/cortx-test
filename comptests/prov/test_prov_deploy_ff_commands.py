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
Prov test file to test factory and field deployment commands.
"""

import os
import logging
import pytest

from commons import commands
from commons.utils import assert_utils
from commons.helpers.node_helper import Node
from config import CMN_CFG, PROV_CFG
from libs.prov.prov_deploy_ff import ProvDeployFFLib

LOGGER = logging.getLogger(__name__)


class TestProvFFCommands:
    """
    Test suite for factory and field deployment commands.
    """

    @classmethod
    def setup_class(cls):
        """Setup operations for the test file."""
        LOGGER.info("STARTED: Setup Module operations")
        cls.node_list = []
        cls.deploy_cfg = PROV_CFG["deploy_ff"]
        for node in range(len(CMN_CFG["nodes"])):
            cls.host = CMN_CFG["nodes"][node]["hostname"]
            cls.uname = CMN_CFG["nodes"][node]["username"]
            cls.passwd = CMN_CFG["nodes"][node]["password"]
            cls.node_obj = Node(hostname=cls.host, username=cls.uname,
                                password=cls.passwd)
            cls.node_list.append(cls.node_obj)
        cls.build_no = os.getenv("Build", None)
        cls.build_branch = os.getenv("Build_Branch", "stable")
        if cls.build_no:
            if cls.build_branch == "stable" or cls.build_branch == "main":
                cls.build = "{}/{}".format(cls.build_no, "prod")
        else:
            cls.build = "last_successful_prod"
        os_version = cls.node_obj.execute_cmd(cmd=commands.CMD_OS_REL,
                                              read_lines=True)[0].strip()
        cls.version = str(os_version.split()[3])
        cls.build_url = PROV_CFG["build_url"].format(
            cls.build_branch, cls.version, cls.build)
        cls.deploy_ff_obj = ProvDeployFFLib()
        LOGGER.info("Install all RPMs required for deployment.")
        for node_obj in cls.node_list:
            cls.res = ProvDeployFFLib.cortx_prepare(node_obj, cls.build_no, cls.build_url)
        LOGGER.info("Initial deployment prereq started.")
        for node_obj in cls.node_list:
            result = ProvDeployFFLib.deployment_prereq(node_obj)
            assert_utils.assert_true(result[0])
        LOGGER.info("Done: Setup module operations")

    @pytest.mark.lr
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-24960")
    def test_24960(self):
        """
        Verify cortx_setup config set command fails for MOTR Client
        Instances when value is not given.
        """
        LOGGER.info("Test Started.")
        cmd = "cortx_setup config set --key 'cortx>software>motr>service>client_instances'"
        out = "cortx_setup command Failed: Invalid input. " \
              "Expected Config param format: --key 'key' --value 'value'"
        for node_obj in self.node_list:
            res = node_obj.execute_cmd(cmd=cmd, exc=False,
                                       read_lines=True)
            assert_utils.assert_exact_string(out, res[1][0])
        LOGGER.info("Test Completed.")

    @pytest.mark.lr
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-24958")
    def test_24958(self):
        """
        Verify cortx_setup config set to add MOTR Client Instances
        key and value in Confstore and Pillar.
        """
        LOGGER.info("Test Started.")
        motr_client_instances = self.deploy_cfg["feature_config"][
            "'cortx>software>motr>service>client_instances'"]
        feature_conf = {"'cortx>software>motr>service>client_instances'": motr_client_instances}
        for node_obj in self.node_list:
            res = ProvDeployFFLib.configure_feature(node_obj, feature_conf)
            assert_utils.assert_true(res[0])
        LOGGER.info("Test Completed.")

    @pytest.mark.lr
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-24959")
    def test_24959(self):
        """
        Verify cortx_setup config get is returning MOTR Client Instances set key.
        """
        LOGGER.info("Test Started.")
        motr_client_instances = self.deploy_cfg["feature_config"][
            "'cortx>software>motr>service>client_instances'"]
        key = "'cortx>software>motr>service>client_instances'"
        for node_obj in self.node_list:
            res = node_obj.execute_cmd(cmd=commands.FEATURE_GET_CFG.
                                       format(key)).decode("utf-8").strip()
            assert_utils.assert_equal(int(res), motr_client_instances)
        LOGGER.info("Test Completed.")

    @pytest.mark.lr
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-24954")
    def test_24954(self):
        """
        Verify cortx_setup config set fails for S3 IO Max Units when value is not given.
        """
        LOGGER.info("Test Started.")
        cmd = "cortx_setup config set --key 'cortx>software>s3>io>max_units'"
        out = "cortx_setup command Failed: Invalid input. " \
              "Expected Config param format: --key 'key' --value 'value'"
        for node_obj in self.node_list:
            res = node_obj.execute_cmd(cmd=cmd, exc=False,
                                       read_lines=True)
            assert_utils.assert_exact_string(out, res[1][0])
        LOGGER.info("Test Completed.")

    @pytest.mark.lr
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-24952")
    def test_24952(self):
        """
        Verify cortx_setup config set to add S3 IO Max Units key and value in Confstore and Pillar.
        """
        LOGGER.info("Test Started.")
        motr_client_instances = self.deploy_cfg["feature_config"][
            "'cortx>software>s3>io>max_units'"]
        feature_conf = {"'cortx>software>s3>io>max_units'": motr_client_instances}
        for node_obj in self.node_list:
            res = ProvDeployFFLib.configure_feature(node_obj, feature_conf)
            assert_utils.assert_true(res[0])
        LOGGER.info("Test Completed.")

    @pytest.mark.lr
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-24953")
    def test_24953(self):
        """
        Verify cortx_setup config get is returning S3 IO Max Units set key.
        """
        LOGGER.info("Test Started.")
        motr_client_instances = self.deploy_cfg["feature_config"][
            "'cortx>software>s3>io>max_units'"]
        key = "'cortx>software>s3>io>max_units'"
        for node_obj in self.node_list:
            res = node_obj.execute_cmd(cmd=commands.FEATURE_GET_CFG.
                                       format(key)).decode("utf-8").strip()
            assert_utils.assert_equal(int(res), motr_client_instances)
        LOGGER.info("Test Completed.")
