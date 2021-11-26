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


"""Continuous Deployment on N nodes config."""
import logging
import os
import pytest
from commons import pswdmanager, configmanager
from commons.helpers.pods_helper import LogicalNode
from config import CMN_CFG, HA_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

DEPLOY_CFG = configmanager.get_config_wrapper(fpath="config/prov/deploy_config.yaml")


class TestContDeployment:
    """Test Multiple config of N+K+S deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.setup_k8s_cluster_flag = os.getenv("setup_k8s_cluster")
        cls.setup_client_config_flag = os.getenv("setup_client_config")
        cls.cortx_cluster_deploy_flag = os.getenv("cortx_cluster_deploy")
        cls.run_basic_s3_io_flag = os.getenv("run_basic_s3_io")
        cls.run_s3bench_workload_flag = os.getenv("run_s3bench_workload")
        cls.collect_support_bundle = os.getenv("collect_support_bundle")
        cls.destroy_setup_flag = os.getenv("destroy_setup")
        cls.conf = (os.getenv("EC_CONFIG")).lower()
        cls.iterations = os.getenv("NO_OF_ITERATIONS")
        cls.raise_jira = os.getenv("raise_jira")
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

    @pytest.mark.tags("TEST-N-NODE")
    @pytest.mark.lc
    def test_n(self):
        """
        test to run continuous deployment
        """
        count = int(self.iterations)
        node = "nodes_{}".format(len(self.worker_node_list))
        self.log.debug("nodes are %s", node)
        config = DEPLOY_CFG[node][self.conf]
        self.log.debug("config is %s", self.conf)
        while count > 0:
            self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                               sns_parity=config['sns_parity'],
                                               sns_spare=config['sns_spare'],
                                               dix_data=config['dix_data'],
                                               dix_parity=config['dix_parity'],
                                               dix_spare=config['dix_spare'],
                                               cvg_count=config['cvg_per_node'],
                                               data_disk_per_cvg=config['data_disk_per_cvg'],
                                               master_node_list=self.master_node_list,
                                               worker_node_list=self.worker_node_list,
                                               setup_k8s_cluster_flag=
                                               self.setup_k8s_cluster_flag,
                                               cortx_cluster_deploy_flag=
                                               self.cortx_cluster_deploy_flag,
                                               setup_client_config_flag=
                                               self.setup_client_config_flag,
                                               destroy_setup_flag=
                                               self.destroy_setup_flag,
                                               run_s3bench_workload_flag=
                                               self.run_s3bench_workload_flag,
                                               run_basic_s3_io_flag=
                                               self.run_basic_s3_io_flag)
            count = count - 1
