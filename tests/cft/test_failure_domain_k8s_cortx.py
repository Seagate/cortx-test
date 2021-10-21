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
        # TODO: Added below to jenkins job
        cls.git_script_tag = os.getenv("GIT_SCRIPT_TAG", PROV_CFG["k8s_cortx_deploy"]["git_tag"])
        cls.cortx_image = os.getenv("CORTX_IMAGE", PROV_CFG["k8s_cortx_deploy"]["cortx_image"])
        # TODO: Update Docker credentials
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
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29485")
    def test_29485(self):
        """
        Intel ISA  - 3node - SNS- 4+2+0 Deployment
        """
        self.log.info("STARTED: 3node (SNS-4+2+0) k8s based Cortx Deployment")
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
                                                  cortx_image=self.cortx_image)
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
        self.log.info("ENDED: 3node (SNS-4+2+0) k8s based Cortx Deployment")
