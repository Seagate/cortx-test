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
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

# pylint: disable=R0904

"""Failure Domain (k8s based Cortx) Test Suite."""
import logging
import pytest

from commons import configmanager
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

DEPLOY_CFG = configmanager.get_config_wrapper(fpath="config/prov/deploy_config.yaml")
# pylint: disable = too-many-lines


class TestMultipleConfDeploy:
    """Test Multiple config of N+K+S deployment testsuite"""

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

    def teardown_method(self):
        """
        Teardown method
        """
        resp = self.deploy_lc_obj.destroy_setup(self.master_node_list[0],
                                                self.worker_node_list)
        assert_utils.assert_true(resp)
        # TODO: collect support bundle

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31384")
    def test_31384(self):
        """
        Deployment- 3node config_1
        """
        config = DEPLOY_CFG['nodes_3']['config_1']
        self.log.info("Running 3 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-29975")
    def test_29975(self):
        """
        Deployment- 3node config_2
        """
        config = DEPLOY_CFG['nodes_3']['config_2']
        self.log.info("Running 3 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-32790")
    def test_32790(self):
        """
        Deployment- 3node config_3
        """
        config = DEPLOY_CFG['nodes_3']['config_3']
        self.log.info("Running 3 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31946")
    def test_31946(self):
        """
        Deployment- 3node config_4
        """
        config = DEPLOY_CFG['nodes_3']['config_4']
        self.log.info("Running 3 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.three_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31875")
    def test_31875(self):
        """
        Deployment- 3node config_5
        """
        config = DEPLOY_CFG['nodes_3']['config_5']
        self.log.info("Running 3 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31385")
    def test_31385(self):
        """
        Deployment- 4node config_1
        """
        config = DEPLOY_CFG['nodes_4']['config_1']
        self.log.info("Running 4 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31386")
    def test_31386(self):
        """
        Deployment- 4node config_2
        """
        config = DEPLOY_CFG['nodes_4']['config_2']
        self.log.info("Running 4 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31387")
    def test_31387(self):
        """
        Deployment- 4node config_3
        """
        config = DEPLOY_CFG['nodes_4']['config_3']
        self.log.info("Running 4 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31388")
    def test_31388(self):
        """
        Deployment- 4node config_4
        """
        config = DEPLOY_CFG['nodes_4']['config_4']
        self.log.info("Running 4 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31568")
    def test_31568(self):
        """
        Deployment- 4node config_5
        """
        config = DEPLOY_CFG['nodes_4']['config_5']
        self.log.info("Running 4 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.four_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31397")
    def test_31397(self):
        """
        Deployment- 4node config_6
        """
        config = DEPLOY_CFG['nodes_4']['config_6']
        self.log.info("Running 4 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31389")
    def test_31389(self):
        """
        Deployment- 5node
        """
        config = DEPLOY_CFG['nodes_5']['config_1']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31390")
    def test_31390(self):
        """
        Deployment- 5node - SNS- 6+4+0 dix 1+2+0
        """
        config = DEPLOY_CFG['nodes_5']['config_2']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31391")
    def test_31391(self):
        """
        Deployment- 5node
        """
        config = DEPLOY_CFG['nodes_5']['config_3']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31392")
    def test_31392(self):
        """
        Deployment- 5node
        """
        config = DEPLOY_CFG['nodes_5']['config_4']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31393")
    def test_31393(self):
        """
        Deployment- 5node
        """
        config = DEPLOY_CFG['nodes_5']['config_5']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.five_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31394")
    def test_31394(self):
        """
        Deployment- 5node
        """
        config = DEPLOY_CFG['nodes_5']['config_6']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31399")
    def test_31399(self):
        """
        Deployment- 6node
        """
        config = DEPLOY_CFG['nodes_6']['config_1']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31396")
    def test_31396(self):
        """
        Deployment- 6node
        """
        config = DEPLOY_CFG['nodes_6']['config_2']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31395")
    def test_31395(self):
        """
        Deployment- 6node
        """
        config = DEPLOY_CFG['nodes_6']['config_3']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31398")
    def test_31398(self):
        """
        Deployment- 6node
        """
        config = DEPLOY_CFG['nodes_6']['config_4']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31400")
    def test_31400(self):
        """
        Deployment- 6node
        """
        config = DEPLOY_CFG['nodes_6']['config_5']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.six_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31401")
    def test_31401(self):
        """
        Deployment- 6node
        """
        config = DEPLOY_CFG['nodes_6']['config_6']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31402")
    def test_31402(self):
        """
        Deployment- 7node
        """
        config = DEPLOY_CFG['nodes_7']['config_1']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31403")
    def test_31403(self):
        """
        Deployment- 7node
        """
        config = DEPLOY_CFG['nodes_7']['config_2']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31404")
    def test_31404(self):
        """
        Deployment- 7node
        """
        config = DEPLOY_CFG['nodes_7']['config_3']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31405")
    def test_31405(self):
        """
        Deployment- 7node
        """
        config = DEPLOY_CFG['nodes_7']['config_4']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31406")
    def test_31406(self):
        """
        Deployment- 7node
        """
        config = DEPLOY_CFG['nodes_7']['config_5']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.seven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31412")
    def test_31412(self):
        """
        Deployment- 7node
        """
        config = DEPLOY_CFG['nodes_7']['config_6']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31414")
    def test_31414(self):
        """
        Deployment- 8node
        """
        config = DEPLOY_CFG['nodes_8']['config_1']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31415")
    def test_31415(self):
        """
        Deployment- 8node
        """
        config = DEPLOY_CFG['nodes_8']['config_2']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31416")
    def test_31416(self):
        """
        Deployment- 8node
        """
        config = DEPLOY_CFG['nodes_8']['config_3']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31417")
    def test_31417(self):
        """
        Deployment- 8node
        """
        config = DEPLOY_CFG['nodes_8']['config_4']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31418")
    def test_31418(self):
        """
        Deployment- 8node
        """
        config = DEPLOY_CFG['nodes_8']['config_5']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eight_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31419")
    def test_31419(self):
        """
        Deployment- 8node
        """
        config = DEPLOY_CFG['nodes_8']['config_6']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31423")
    def test_31423(self):
        """
        Deployment- 9node
        """
        config = DEPLOY_CFG['nodes_9']['config_1']
        self.log.info("Running 9 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-32794")
    def test_32794(self):
        """
        Deployment- 9node
        """
        config = DEPLOY_CFG['nodes_9']['config_2']
        self.log.info("Running 9 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31424")
    def test_31424(self):
        """
        Deployment- 9node
        """
        config = DEPLOY_CFG['nodes_9']['config_3']
        self.log.info("Running 9 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31421")
    def test_31421(self):
        """
        Deployment- 9node
        """
        config = DEPLOY_CFG['nodes_9']['config_4']
        self.log.info("Running 9 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31420")
    def test_31420(self):
        """
        Deployment- 9node
        """
        config = DEPLOY_CFG['nodes_9']['config_5']
        self.log.info("Running 9 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.nine_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31422")
    def test_31422(self):
        """
        Deployment- 9node
        """
        config = DEPLOY_CFG['nodes_9']['config_6']
        self.log.info("Running 9 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31439")
    def test_31439(self):
        """
        Deployment- 10node
        """
        config = DEPLOY_CFG['nodes_10']['config_1']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31565")
    def test_31565(self):
        """
        Deployment- 10node
        """
        config = DEPLOY_CFG['nodes_10']['config_2']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31566")
    def test_31566(self):
        """
        Deployment- 10node
        """
        config = DEPLOY_CFG['nodes_10']['config_3']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31567")
    def test_31567(self):
        """
        Deployment- 10node
        """
        config = DEPLOY_CFG['nodes_10']['config_4']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31571")
    def test_31571(self):
        """
        Deployment- 10node
        """
        config = DEPLOY_CFG['nodes_10']['config_5']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31569")
    def test_31569(self):
        """
        Deployment- 10node
        """
        config = DEPLOY_CFG['nodes_10']['config_6']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.ten_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31570")
    def test_31570(self):
        """
        Deployment- 10node
        """
        config = DEPLOY_CFG['nodes_10']['config_7']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31938")
    def test_31938(self):
        """
        Deployment- 11node
        """
        config = DEPLOY_CFG['nodes_11']['config_1']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31939")
    def test_31939(self):
        """
        Deployment- 11node
        """
        config = DEPLOY_CFG['nodes_11']['config_2']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31940")
    def test_31940(self):
        """
        Deployment- 11node
        """
        config = DEPLOY_CFG['nodes_11']['config_3']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31936")
    def test_31936(self):
        """
        Deployment- 11node
        """
        config = DEPLOY_CFG['nodes_11']['config_4']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31941")
    def test_31941(self):
        """
        Deployment- 11node
        """
        config = DEPLOY_CFG['nodes_11']['config_5']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.eleven_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31942")
    def test_31942(self):
        """
        Deployment- 11node
        """
        config = DEPLOY_CFG['nodes_11']['config_6']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31788")
    def test_31788(self):
        """
        Deployment- 12node
        """
        config = DEPLOY_CFG['nodes_12']['config_1']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31789")
    def test_31789(self):
        """
        Deployment- 12node
        """
        config = DEPLOY_CFG['nodes_12']['config_2']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31790")
    def test_31790(self):
        """
        Deployment- 12node
        """
        config = DEPLOY_CFG['nodes_12']['config_3']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31791")
    def test_31791(self):
        """
        Deployment- 12node
        """
        config = DEPLOY_CFG['nodes_12']['config_4']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31792")
    def test_31792(self):
        """
        Deployment- 12node
        """
        config = DEPLOY_CFG['nodes_12']['config_5']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31793")
    def test_31793(self):
        """
        Deployment- 12node
        """
        config = DEPLOY_CFG['nodes_12']['config_6']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31794")
    def test_31794(self):
        """
        Deployment- 12node
        """
        config = DEPLOY_CFG['nodes_12']['config_7']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.twelve_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31795")
    def test_31795(self):
        """
        Deployment- 12node
        """
        config = DEPLOY_CFG['nodes_12']['config_8']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31943")
    def test_31943(self):
        """
        Deployment- 13node
        """
        config = DEPLOY_CFG['nodes_13']['config_1']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31944")
    def test_31944(self):
        """
        Deployment- 13node
        """
        config = DEPLOY_CFG['nodes_13']['config_2']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31945")
    def test_31945(self):
        """
        Deployment- 13node
        """
        config = DEPLOY_CFG['nodes_13']['config_3']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31934")
    def test_31934(self):
        """
        Deployment- 13node
        """
        config = DEPLOY_CFG['nodes_13']['config_4']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-32793")
    def test_32793(self):
        """
        Deployment- 13node
        """
        config = DEPLOY_CFG['nodes_13']['config_5']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.thirteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31947")
    def test_31947(self):
        """
        Deployment- 13node
        """
        config = DEPLOY_CFG['nodes_13']['config_6']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31948")
    def test_31948(self):
        """
        Deployment- 14node
        """
        config = DEPLOY_CFG['nodes_14']['config_1']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31949")
    def test_31949(self):
        """
        Deployment- 14node
        """
        config = DEPLOY_CFG['nodes_14']['config_2']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31935")
    def test_31935(self):
        """
        Deployment- 14node
        """
        config = DEPLOY_CFG['nodes_14']['config_3']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31950")
    def test_31950(self):
        """
        Deployment- 14node
        """
        config = DEPLOY_CFG['nodes_14']['config_4']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31951")
    def test_31951(self):
        """
        Deployment- 14node
        """
        config = DEPLOY_CFG['nodes_14']['config_5']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fourteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31952")
    def test_31952(self):
        """
        Deployment- 14node
        """
        config = DEPLOY_CFG['nodes_14']['config_6']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31572")
    def test_31572(self):
        """
        Deployment- 15node
        """
        config = DEPLOY_CFG['nodes_15']['config_1']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31573")
    def test_31573(self):
        """
        Deployment- 15node
        """
        config = DEPLOY_CFG['nodes_15']['config_2']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31574")
    def test_31574(self):
        """
        Deployment- 15node
        """
        config = DEPLOY_CFG['nodes_15']['config_3']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31575")
    def test_31575(self):
        """
        Deployment- 15node
        """
        config = DEPLOY_CFG['nodes_15']['config_4']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31576")
    def test_31576(self):
        """
        Deployment- 15node
        """
        config = DEPLOY_CFG['nodes_15']['config_5']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.fifteen_node_deployment
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31577")
    def test_31577(self):
        """
        Deployment- 15node
        """
        config = DEPLOY_CFG['nodes_15']['config_6']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_per_node'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list)
