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
Prov test file for all the commands needs to be checked after deployment.
"""

import os
import pytest
from commons import commands as common_cmd
from commons.utils import assert_utils
from config import CMN_CFG, PROV_CFG
from libs.prov.prov_deploy_ff import ProvDeployFFLib
from libs.prov.provisioner import Provisioner
import logging
from commons.helpers.node_helper import Node
LOGGER = logging.getLogger(__name__)


class TestProvisionerPostDeployment:

    @classmethod
    def setup_class(cls):
        """Setup class"""
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


    @pytest.mark.tags("TEST-26563")
    def test_26563(self):
        """Performing status command"""
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              )
        assert_utils.assert_true(resp[0], resp[1])
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_no, self.build_url, resp[1])

    @pytest.mark.tags("TEST-26253")
    def test_26253(self):
        """Performing reset command"""
        self.deploy_ff_obj.reset_deployment_check(self.nd1_obj)

    @pytest.mark.tags("TEST-26220")
    def test_26220(self):
        """Performing cluster show command"""
        self.deploy_ff_obj.cluster_show(self.nd1_obj)

    @pytest.mark.tags("TEST-26206")
    def test_26206(self):
        """ Performing reset_h_check command"""
        self.deploy_ff_obj.reset_h_check(self.nd1_obj)
