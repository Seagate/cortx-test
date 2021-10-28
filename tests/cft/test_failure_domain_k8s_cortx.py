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

"""Failure Domain (k8s based Cortx) Test Suite."""
import logging
import os
from multiprocessing import Pool

import pytest

from commons import commands as common_cmd
from commons import pswdmanager
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons.utils import system_utils
from config import CMN_CFG, HA_CFG, PROV_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib


class TestFailureDomainK8Cortx:
    """Test Failure Domain - k8s based Cortx (EC,Intel ISA) deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.git_id = os.getenv("GIT_ID")
        cls.git_token = os.getenv("GIT_PASSWORD")
        cls.git_script_tag = os.getenv("GIT_SCRIPT_TAG")
        cls.cortx_image = os.getenv("CORTX_IMAGE")
        cls.docker_username = os.getenv("DOCKER_USERNAME")
        cls.docker_password = os.getenv("DOCKER_PASSWORD")
        cls.vm_username = os.getenv("QA_VM_POOL_ID",
                                    pswdmanager.decrypt(HA_CFG["vm_params"]["uname"]))
        cls.vm_password = os.getenv("QA_VM_POOL_PASSWORD",
                                    pswdmanager.decrypt(HA_CFG["vm_params"]["passwd"]))
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        for node in range(cls.num_nodes):
            vm_name = CMN_CFG["nodes"][node]["hostname"].split(".")[0]
            cls.host_list.append(vm_name)
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        cls.control_lb_ip = CMN_CFG["load_balancer_ip"]["control_ip"]
        cls.data_lb_ip = CMN_CFG["load_balancer_ip"]["data_ip"]
        cls.control_lb_ip = cls.control_lb_ip.split(",")
        cls.data_lb_ip = cls.data_lb_ip.split(",")

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

    # pylint: disable=too-many-arguments
    def test_deployment(self, sns_data, sns_parity,
                        sns_spare, dix_data,
                        dix_parity, dix_spare,
                        cvg_count, data_disk_per_cvg):
        """
        This method is used for deployment with various config on N nodes
        """
        self.log.info("STARTED: {%s node (SNS-%s+%s+%s) k8s based Cortx Deployment",
                      len(self.worker_node_list), sns_data, sns_parity, sns_spare)
        self.log.info("Step 1: Perform k8s Cluster Deployment")
        resp = self.deploy_lc_obj.setup_k8s_cluster(self.master_node_list, self.worker_node_list)
        assert_utils.assert_true(resp[0], resp[1])

        self.log.info("Step 2: Taint master nodes if not already done.")
        for node in self.master_node_list:
            resp = self.deploy_lc_obj.validate_master_tainted(node)
            if not resp:
                self.deploy_lc_obj.taint_master(node)

        self.log.info("Step 3: Download solution file template")
        path = self.deploy_lc_obj.checkout_solution_file(self.git_token, self.git_script_tag)
        self.log.info("Step 4 : Update solution file template")
        resp = self.deploy_lc_obj.update_sol_yaml(worker_obj=self.worker_node_list, filepath=path,
                                                  cortx_image=self.cortx_image,
                                                  control_lb_ip=self.control_lb_ip,
                                                  data_lb_ip=self.data_lb_ip,
                                                  sns_data=sns_data, sns_parity=sns_parity,
                                                  sns_spare=sns_spare, dix_data=dix_data,
                                                  dix_parity=dix_parity,
                                                  dix_spare=dix_spare, cvg_count=cvg_count,
                                                  data_disk_per_cvg=data_disk_per_cvg,
                                                  size_data_disk="20Gi",
                                                  size_metadata="20Gi",
                                                  glusterfs_size="20Gi")
        assert_utils.assert_true(resp[0], "Failure updating solution.yaml")
        sol_file_path = resp[1]
        system_disk_dict = resp[2]

        self.log.info("Step 5: Perform Cortx Cluster Deployment")
        resp = self.deploy_lc_obj.deploy_cortx_cluster(sol_file_path, self.master_node_list,
                                                       self.worker_node_list, system_disk_dict,
                                                       self.docker_username,
                                                       self.docker_password, self.git_id,
                                                       self.git_token, self.git_script_tag)
        assert_utils.assert_true(resp[0], resp[1])
        self.log.info("ENDED: %s node (SNS-%s+%s+%s) k8s based Cortx Deployment",
                      len(self.worker_node_list), sns_parity, sns_spare)

    @pytest.mark.run(order=1)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29485")
    def test_29485(self):
        """
        Intel ISA  - 3node - SNS- 4+2+0 dix 1+2+0 Deployment
        """
        self.test_deployment(sns_data=4, sns_parity=2, sns_spare=0, dix_data=1,
                             dix_parity=2, dix_spare=0, cvg_count=2, data_disk_per_cvg=2)

    @pytest.mark.run(order=4)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29488")
    def test_29488(self):
        """
        Intel ISA -5node -SNS - 10+5+0, dix 1+2+0 Deployment
        """
        self.test_deployment(sns_data=10, sns_parity=5, sns_spare=0,
                             dix_data=1, dix_parity=2, dix_spare=0, cvg_count=3,
                             data_disk_per_cvg=1)

    @pytest.mark.run(order=7)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29491")
    def test_29491(self):
        """
        Intel ISA  - 5node - SNS- 6+4+0 , dix 1+2+0 Deployment
        """
        self.test_deployment(sns_data=6, sns_parity=4, sns_spare=0,
                             dix_data=1, dix_parity=2, dix_spare=0, cvg_count=2,
                             data_disk_per_cvg=2)

    @pytest.mark.run(order=10)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29494")
    def test_29494(self):
        """
        Intel ISA  - 16node - SNS- 8+8+0 dix 1+8+0 Deployment
        """
        self.test_deployment(sns_data=8, sns_parity=8, sns_spare=0, dix_data=1,
                             dix_parity=8, dix_spare=0, cvg_count=2, data_disk_per_cvg=2)

    @pytest.mark.run(order=13)
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29497")
    def test_29497(self):
        """
        Intel ISA  - 16node - SNS- 16+4+0 dix 1+4+0 Deployment
        """
        self.test_deployment(sns_data=16, sns_parity=4, sns_spare=0, dix_data=1,
                             dix_parity=4, dix_spare=0, cvg_count=2, data_disk_per_cvg=2)
