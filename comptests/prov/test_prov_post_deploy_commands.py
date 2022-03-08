#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#

"""
Prov test file for all the commands needs to be checked after deployment.
"""

import os
import logging
import pytest
from commons import commands as common_cmd
from commons.utils import assert_utils
from commons.helpers.node_helper import Node
from config import CMN_CFG, PROV_CFG
from libs.prov.prov_deploy_ff import ProvDeployFFLib
from libs.prov.provisioner import Provisioner

LOGGER = logging.getLogger(__name__)


class TestProvisionerPostDeployment:
    """
        Test suite for post deploy commands.
        """

    @classmethod
    def setup_class(cls):
        """
        Setup class
        """
        cls.log = logging.getLogger(__name__)

        cls.deplymt_cfg = PROV_CFG["deploy_ff"]
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.node_list = []
        cls.host_list = []
        for node in range(cls.num_nodes):
            cls.host_list.append(CMN_CFG["nodes"][node]["host"])
            cls.node_list.append(Node(hostname=CMN_CFG["nodes"][node]["hostname"],
                                      username=CMN_CFG["nodes"][node]["username"],
                                      password=CMN_CFG["nodes"][node]["password"]))
        cls.nd1_obj = cls.node_list[0]
        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.test_config_template = cls.deplymt_cfg["deployment_template"]
        cls.deploy_ff_obj = ProvDeployFFLib()
        cls.build_branch = os.getenv("Build_Branch", "stable")
        cls.build = os.getenv("Build", None)
        cls.build_no = cls.build
        os_version = cls.nd1_obj.execute_cmd(cmd=common_cmd.CMD_OS_REL,
                                             read_lines=True)[0].strip()
        version = "centos-" + str(os_version.split()[3])
        if cls.build:
            if cls.build_branch == "stable" or cls.build_branch == "main":
                cls.build = "{}/{}".format(cls.build, "prod")
        else:
            cls.build = "last_successful_prod"
        cls.build_url = cls.deplymt_cfg["build_url"].format(
            cls.build_branch, version, cls.build)
        cls.deploy_ff_obj = ProvDeployFFLib()

    @pytest.mark.lr
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-26562")
    def test_26562(self):
        """Performing start command"""
        LOGGER.info("Starting Start Command Response")
        resp = self.deploy_ff_obj.check_start_command(self.nd1_obj)
        assert_utils.assert_exact_string(resp,"status")
        LOGGER.info("Completed Start Command Response")

    @pytest.mark.lr
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-26563")
    def test_26563(self):
        """Performing status command"""
        LOGGER.info("Starting Status Command")
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              )
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_no, self.build_url, resp[1])
        assert_utils.assert_exact_string(resp,"status")
        LOGGER.info("Response for status command: %s", resp)

    @pytest.mark.lr
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-26253")
    def test_26253(self):
        """Performing reset command"""
        LOGGER.info("Starting Cluster Show Command Response")
        resp = self.deploy_ff_obj.post_deploy_check(self.nd1_obj)
        assert_utils.assert_exact_string(resp,"Cluster name")
        resp = self.deploy_ff_obj.reset_deployment_check(self.nd1_obj)
        assert_utils.assert_exact_string(resp,"srv-glusterfs-volume_prvsnr_data")
        LOGGER.info("Response for reset command: %s", resp)
        resp = self.deploy_ff_obj.post_deploy_check(self.nd1_obj)
        assert_utils.assert_exact_string(resp,"Cluster name")
        resp = self.deploy_ff_obj.cluster_show(self.nd1_obj)
        assert_utils.assert_exact_string(resp,"srvnode-1")
        LOGGER.info("Response for cluster show command: %s", resp)

    @pytest.mark.lr
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-26220")
    def test_26220(self):
        """Performing cluster show command"""
        LOGGER.info("Starting Cluster Show Command Response")
        resp = self.deploy_ff_obj.post_deploy_check(self.nd1_obj)
        assert_utils.assert_exact_string(resp,"No such file or directory")
        resp = self.deploy_ff_obj.cluster_show(self.nd1_obj)
        assert_utils.assert_exact_string(resp,"srvnode-0")
        LOGGER.info("Response for cluster show command: %s", resp)

    @pytest.mark.lr
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-26206")
    def test_26206(self):
        """ Performing reset_h_check command"""
        LOGGER.info("Starting Reset_H Command Response")
        resp = self.deploy_ff_obj.reset_h_check(self.nd1_obj)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Response for reset_h_check command: %s", resp)
        