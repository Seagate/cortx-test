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

"""Failure Domain Test Suite."""
import logging
import os
from multiprocessing import Pool

import pytest

from commons import commands as common_cmd
from commons import pswdmanager
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG, HA_CFG, PROV_CFG
from libs.prov.prov_deploy_ff import ProvDeployFFLib
from libs.prov.provisioner import Provisioner


class TestFailureDomain:
    """Test Failure Domain (EC,Intel ISA) deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.deplymt_cfg = PROV_CFG["deploy_ff"]
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.node_list = []
        cls.host_list = []
        for node in range(cls.num_nodes):
            vm_name = CMN_CFG["nodes"][node]["hostname"].split(".")[0]
            cls.host_list.append(vm_name)
            cls.node_list.append(Node(hostname=CMN_CFG["nodes"][node]["hostname"],
                                      username=CMN_CFG["nodes"][node]["username"],
                                      password=CMN_CFG["nodes"][node]["password"]))
        cls.nd1_obj = cls.node_list[0]
        cls.mgmt_vip = CMN_CFG["csm"]["mgmt_vip"]
        cls.test_config_template = cls.deplymt_cfg["deployment_template"]

        cls.vm_username = os.getenv(
            "QA_VM_POOL_ID", pswdmanager.decrypt(
                HA_CFG["vm_params"]["uname"]))
        cls.vm_password = os.getenv(
            "QA_VM_POOL_PASSWORD", pswdmanager.decrypt(
                HA_CFG["vm_params"]["passwd"]))
        cls.build = os.getenv("Build", None)
        cls.build_no = cls.build
        cls.build_branch = os.getenv("Build_Branch", "stable")
        if cls.build:
            if cls.build_branch == "stable" or cls.build_branch == "main":
                cls.build = "{}/{}".format(cls.build, "prod")
        else:
            cls.build = "last_successful_prod"
        os_version = cls.nd1_obj.execute_cmd(cmd=common_cmd.CMD_OS_REL,
                                             read_lines=True)[0].strip()
        version = "centos-" + str(os_version.split()[3])
        cls.build_url = cls.deplymt_cfg["build_url"].format(
            cls.build_branch, version, cls.build)
        cls.deploy_ff_obj = ProvDeployFFLib()

    def setup_method(self):
        """Revert the VM's before starting the deployment tests"""
        self.log.info("Reverting all the VM before deployment")
        with Pool(self.num_nodes) as proc_pool:
            proc_pool.map(self.revert_vm_snapshot, self.host_list)

    def revert_vm_snapshot(self, host):
        """Revert VM snapshot
           host: VM name """
        resp = system_utils.execute_cmd(cmd=common_cmd.CMD_VM_REVERT.format(
            self.vm_username, self.vm_password, host), read_lines=True)

        assert_utils.assert_true(resp[0], resp[1])

    @pytest.mark.run(order=1)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-23540")
    def test_23540(self):
        """Perform deployment,preboarding, onboarding,s3 configuration with 4+2+0 config"""
        self.log.info("Step 1: Create Deployment Config")
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip
                                                              )
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Perform Deployment with SNS NKS : 4+2+0")
        resp = self.deploy_ff_obj.deploy_3node_vm_ff(self.build_no, self.build_url, resp[1])
        assert_utils.assert_true(resp, "Failure in Deployment")

        self.log.info("Step 3: Perform Post Deployment Steps")
        self.deploy_ff_obj.post_deployment_steps()

    @pytest.mark.run(order=4)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 1, [6, 2, 0])])
    @pytest.mark.tags("TEST-22901")
    def test_22901(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Perform deployment with Invalid config and expect failure
        datapool : N+K+S : 6+2+0, data device per cvg: 1
        """
        self.log.info("Step 1: Create Deployment Config")
        assert_utils.assert_equal(len(sns_config), 3)
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              cvg_count_per_node=cvg_count_per_node,
                                                              data_disk_per_cvg=data_disk_per_cvg,
                                                              sns_data=str(sns_config[0]),
                                                              sns_parity=str(sns_config[1]),
                                                              sns_spare=str(sns_config[2]),
                                                              skip_disk_count_check=True
                                                              )
        assert_utils.assert_true(resp[0], resp[1])
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_no, self.build_url, resp[1])

    @pytest.mark.run(order=5)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(1, 7, [8, 2, 0])])
    @pytest.mark.tags("TEST-26959")
    def test_26959(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """ Test Deployment using following config
        N+K+S: 8+2+0
        CVG's per node : 1
        Data Devices per CVG: 7
        Metadata Device per CVG : 1
        """
        self.log.info("Step 1: Create Deployment Config")
        assert_utils.assert_equal(len(sns_config), 3)
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              cvg_count_per_node=cvg_count_per_node,
                                                              data_disk_per_cvg=data_disk_per_cvg,
                                                              sns_data=str(sns_config[0]),
                                                              sns_parity=str(sns_config[1]),
                                                              sns_spare=str(sns_config[2]))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info(resp[1])
        self.log.info("Step 2: Perform Deployment with SNS NKS : 8+2+0")
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_no, self.build_url, resp[1])

        self.log.info("Step 3: Perform Post Deployment Steps")
        self.deploy_ff_obj.post_deployment_steps()

    @pytest.mark.run(order=8)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 3, [3, 2, 0])])
    @pytest.mark.tags("TEST-26960")
    def test_26960(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Test Deployment using following config
        N+K+S: 3+2+0
        CVG's per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        self.log.info("Step 1: Create Deployment Config")
        assert_utils.assert_equal(len(sns_config), 3)
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              cvg_count_per_node=cvg_count_per_node,
                                                              data_disk_per_cvg=data_disk_per_cvg,
                                                              sns_data=str(sns_config[0]),
                                                              sns_parity=str(sns_config[1]),
                                                              sns_spare=str(sns_config[2]))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Perform Deployment with SNS NKS : 3+2+0")
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_no, self.build_url, resp[1])

        self.log.info("Step 3: Perform Post Deployment Steps")
        self.deploy_ff_obj.post_deployment_steps()

    @pytest.mark.run(order=12)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 3, [8, 4, 0])])
    @pytest.mark.tags("TEST-26961")
    def test_26961(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Test Deployment using following config
        N+K+S: 8+4+0
        CVG's per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        self.log.info("Step 1: Create Deployment Config")
        assert_utils.assert_equal(len(sns_config), 3)
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              cvg_count_per_node=cvg_count_per_node,
                                                              data_disk_per_cvg=data_disk_per_cvg,
                                                              sns_data=str(sns_config[0]),
                                                              sns_parity=str(sns_config[1]),
                                                              sns_spare=str(sns_config[2]))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Perform Deployment with SNS NKS : 8+4+0")
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_no, self.build_url, resp[1])

        self.log.info("Step 3: Perform Post Deployment Steps")
        self.deploy_ff_obj.post_deployment_steps()

    @pytest.mark.run(order=16)
    @pytest.mark.lr
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 3, [10, 5, 0])])
    @pytest.mark.tags("TEST-26962")
    def test_26962(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Test Deployment using following config
        N+K+S: 10+5+0
        CVG's per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
        self.log.info("Step 1: Create Deployment Config")
        assert_utils.assert_equal(len(sns_config), 3)
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              cvg_count_per_node=cvg_count_per_node,
                                                              data_disk_per_cvg=data_disk_per_cvg,
                                                              sns_data=str(sns_config[0]),
                                                              sns_parity=str(sns_config[1]),
                                                              sns_spare=str(sns_config[2]))
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("Step 2: Perform Deployment with SNS NKS : 10+5+0")
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_no, self.build_url, resp[1])

        self.log.info("Step 3: Perform Post Deployment Steps")
        self.deploy_ff_obj.post_deployment_steps()
