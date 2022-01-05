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

import pytest

from commons import configmanager
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib


class TestFailureDomainK8Cortx:
    """Test Failure Domain - k8s based Cortx (EC,Intel ISA) deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
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
        test_config = "config/cft/test_failure_domain_k8s_cortx.yaml"
        cls.test_config = configmanager.get_config_wrapper(fpath=test_config)

    def setup_method(self):
        """Destroy the cortx cluster before starting the deployment tests"""
        self.log.info("Destroy the cluster from master node")
        resp = self.deploy_lc_obj.destroy_setup(self.master_node_list[0], self.worker_node_list)
        assert_utils.assert_true(resp[0], resp[1])

    # pylint: disable=too-many-arguments
    def test_deployment(self, sns_data, sns_parity,
                        sns_spare, dix_data,
                        dix_parity, dix_spare,
                        cvg_count, data_disk_per_cvg):
        """
        This method is used for deployment with various config on N nodes
        """
        self.deploy_lc_obj.test_deployment(sns_data=sns_data, sns_parity=sns_parity,
                                           sns_spare=sns_spare, dix_data=dix_data,
                                           dix_parity=dix_parity,
                                           dix_spare=dix_spare, cvg_count=cvg_count,
                                           data_disk_per_cvg=data_disk_per_cvg,
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list,
                                           setup_k8s_cluster_flag=True,
                                           cortx_cluster_deploy_flag=True,
                                           setup_client_config_flag=True,
                                           run_basic_s3_io_flag=False,
                                           run_s3bench_workload_flag=False,
                                           destroy_setup_flag=False)

    @pytest.mark.run(order=1)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29485")
    def test_29485(self):
        """
        Intel ISA  - 3node - SNS- 4+2+0 dix 1+2+0 Deployment
        """
        self.test_deployment(sns_data=4, sns_parity=2, sns_spare=0, dix_data=1,
                             dix_parity=2, dix_spare=0, cvg_count=2, data_disk_per_cvg=2)

    @pytest.mark.run(order=4)
    @pytest.mark.lc
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
    @pytest.mark.lc
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
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29494")
    def test_29494(self):
        """
        Intel ISA  - 16node - SNS- 8+8+0 dix 1+8+0 Deployment
        """
        self.test_deployment(sns_data=8, sns_parity=8, sns_spare=0, dix_data=1,
                             dix_parity=8, dix_spare=0, cvg_count=2, data_disk_per_cvg=2)

    @pytest.mark.run(order=13)
    @pytest.mark.lc
    @pytest.mark.data_durability
    @pytest.mark.tags("TEST-29497")
    def test_29497(self):
        """
        Intel ISA  - 16node - SNS- 16+4+0 dix 1+4+0 Deployment
        """
        self.test_deployment(sns_data=16, sns_parity=4, sns_spare=0, dix_data=1,
                             dix_parity=4, dix_spare=0, cvg_count=2, data_disk_per_cvg=2)
