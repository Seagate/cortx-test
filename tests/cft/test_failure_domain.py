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

"""Failure Domain Test Suite."""
import logging
import os

import pytest

from commons import commands as common_cmd
from commons import configmanager
from commons import pswdmanager
from commons.helpers.node_helper import Node
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG, HA_CFG
from libs.prov.prov_deploy_ff import ProvDeployFFLib
from libs.prov.provisioner import Provisioner


class TestFailureDomain:
    """Test Failure Domain (EC,Intel ISA) deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        test_config = "config/cft/test_failure_domain.yaml"
        cls.cft_test_cfg = configmanager.get_config_wrapper(fpath=test_config)
        cls.deplymt_cfg = cls.cft_test_cfg["test_deployment_ff"]
        cls.setup_type = CMN_CFG["setup_type"]
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

        cls.vm_username = os.getenv(
            "QA_VM_POOL_ID", pswdmanager.decrypt(
                HA_CFG["vm_params"]["uname"]))
        cls.vm_password = os.getenv(
            "QA_VM_POOL_PASSWORD", pswdmanager.decrypt(
                HA_CFG["vm_params"]["passwd"]))
        cls.build = os.getenv("Build", None)
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
        for host in self.host_list:
            self.revert_vm_snapshot(host)

    def revert_vm_snapshot(self, host):
        """Revert VM snapshot
           host: VM name """
        resp = system_utils.execute_cmd(cmd=common_cmd.CMD_VM_REVERT.format(
            self.vm_username, self.vm_password, host), read_lines=True)

        assert_utils.assert_true(resp[0], resp[1])

    def deploy_3node_vm(self, config_file_path: str = None, expect_failure: bool = False):
        """
        Deploy 3 node using jenkins job
        """
        test_cfg = self.cft_test_cfg["test_deployment"]
        self.log.info("Adding data required for the jenkins job execution")
        parameters = dict()

        parameters['Client_Node'] = os.getenv("Client_Node", None)
        parameters['Git_Repo'] = os.getenv("Git_Repo", 'https://github.com/Seagate/cortx-test.git')
        parameters['Git_Branch'] = os.getenv("Git_Branch", 'dev')
        parameters['Cortx_Build'] = os.getenv("Build", None)
        parameters['Cortx_Build_Branch'] = os.getenv("Build_Branch", "stable")

        parameters['Target_Node'] = CMN_CFG["setupname"]
        parameters['Node1_Hostname'] = CMN_CFG["nodes"][0]["hostname"]
        parameters['Node2_Hostname'] = CMN_CFG["nodes"][1]["hostname"]
        parameters['Node3_Hostname'] = CMN_CFG["nodes"][2]["hostname"]
        parameters['HOST_PASS'] = CMN_CFG["nodes"][0]["password"]
        parameters['MGMT_VIP'] = CMN_CFG["csm"]["mgmt_vip"]
        parameters['ADMIN_USR'] = CMN_CFG["csm"]["csm_admin_user"]["username"]
        parameters['ADMIN_PWD'] = CMN_CFG["csm"]["csm_admin_user"]["password"]
        parameters['Skip_Deployment'] = test_cfg["skip_deployment"]
        parameters['Skip_Preboarding'] = test_cfg["skip_preboarding"]
        parameters['Skip_Onboarding'] = test_cfg["skip_onboarding"]
        parameters['Skip_S3_Configuration'] = test_cfg["skip_s3_configure"]

        self.log.info("Parameters for jenkins job : %s", parameters)

        if config_file_path is not None and os.path.exists(config_file_path):
            self.log.info("Retrieving the config details for deployment from provided config file")
            with open(config_file_path, 'r') as file:
                parameters['Provisioner_Config'] = file.read()
        else:
            self.log.error(
                "Config file not provided, Deployment to be proceeded with defaults values")
            assert_utils.assert_true(False, "Config File not provided for deployment")

        output = Provisioner.build_job(test_cfg["jenkins_job_name"], parameters,
                                       test_cfg["jenkins_token"],
                                       test_cfg["jenkins_job_url"])
        self.log.info("Jenkins Build URL: %s", output['url'])
        self.log.info("Result : %s", output['result'])
        if not expect_failure:
            assert_utils.assert_equal(output['result'], "SUCCESS",
                                      "Job is not successful, please check the url.")
        else:
            assert_utils.assert_equal(output['result'], "FAILURE",
                                      "Job is successful, expected to fail")

    @pytest.mark.run(order=1)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-23540")
    def test_23540(self):
        """Perform deployment,preboarding, onboarding,s3 configuration with 4+2+0 config"""
        resp = Provisioner.create_deployment_config_universal(self.test_config_template,
                                                              self.node_list,
                                                              mgmt_vip=self.mgmt_vip,
                                                              )
        assert_utils.assert_true(resp[0], resp[1])
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_branch, self.build_url, resp[1])

    @pytest.mark.run(order=4)
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 1, [6, 2, 0])])
    @pytest.mark.tags("TEST-22901")
    def test_22901(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Perform deployment with Invalid config and expect failure
        datapool : N+K+S : 6+2+0, data device per cvg: 1
        """
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
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_branch, self.build_url, resp[1])

    @pytest.mark.run(order=5)
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(1, 7, [8, 2, 0])])
    @pytest.mark.tags("TEST-26959")
    def test_26959(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """ Test Deployment using following config
        N+K+S: 8+2+0
        CVG’s per node : 1
        Data Devices per CVG: 7
        Metadata Device per CVG : 1
        """
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
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_branch, self.build_url, resp[1])

    @pytest.mark.run(order=8)
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 3, [3, 2, 0])])
    @pytest.mark.tags("TEST-26960")
    def test_26960(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Test Deployment using following config
        N+K+S: 3+2+0
        CVG’s per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
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
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_branch, self.build_url, resp[1])

    @pytest.mark.run(order=12)
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 3, [8, 4, 0])])
    @pytest.mark.tags("TEST-26961")
    def test_26961(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Test Deployment using following config
        N+K+S: 8+4+0
        CVG’s per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
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
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_branch, self.build_url, resp[1])

    @pytest.mark.run(order=16)
    @pytest.mark.data_durability
    @pytest.mark.parametrize("cvg_count_per_node, data_disk_per_cvg, sns_config",
                             [(2, 3, [10, 5, 0])])
    @pytest.mark.tags("TEST-26962")
    def test_26962(self, cvg_count_per_node, data_disk_per_cvg, sns_config):
        """
        Test Deployment using following config
        N+K+S: 10+5+0
        CVG’s per node : 2
        Data Devices per CVG: 3
        Metadata Device per CVG : 1
        """
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
        self.deploy_ff_obj.deploy_3node_vm_ff(self.build_branch, self.build_url, resp[1])
