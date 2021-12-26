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

"""Prov Deployment with Redefined Structure."""
import logging
import secrets
import pytest
from commons import configmanager, constants
from commons.utils import assert_utils
from commons.helpers.pods_helper import LogicalNode
from config import CMN_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

DEPLOY_CFG = configmanager.get_config_wrapper(fpath="config/prov/deploy_config.yaml")


class TestProvPodsDeployment:
    """Test Prov Redefined structure deployment testsuite"""

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
        # TODO: collect support bundle
        resp = self.deploy_lc_obj.destroy_setup(self.master_node_list[0],
                                                self.worker_node_list)
        assert_utils.assert_true(resp)

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-33218")
    def test_33218(self):
        """
        Test to verify the CONTROL pod being deployed
        """
        config_list = self.deploy_lc_obj.get_durability_config(num_nodes=len(self.worker_node_list))
        config = secrets.choice(config_list)
        self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", (len(self.worker_node_list)),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_count'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list,
                                           destroy_setup_flag=False)
        resp = LogicalNode.get_all_pods(self.master_node_list[0],
                                        pod_prefix=constants.CONTROL_POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0])
        self.log.info("Pod list are %s", resp[0])
        self.log.info("Pod count is %s", len(resp))
        assert_utils.assert_equal(len(resp), 1)
        self.log.info("===Test Completed===")

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-33219")
    def test_33219(self):
        """
        Test to verify the DATA pod being deployed
        """
        config_list = self.deploy_lc_obj.get_durability_config(num_nodes=len(self.worker_node_list))
        config = secrets.choice(config_list)
        self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", len(self.worker_node_list),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_count'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list,
                                           destroy_setup_flag=False)
        resp = LogicalNode.get_all_pods(self.master_node_list[0],
                                        pod_prefix=constants.POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0])
        self.log.info("Pod list are %s", resp[0])
        self.log.info("Pod count is %s", len(resp))
        assert_utils.assert_equal(len(resp), len(self.worker_node_list))
        self.log.info("===Test Completed===")

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-33220")
    def test_33220(self):
        """
        Test to verify the SERVER pod being deployed
        """
        config_list = self.deploy_lc_obj.get_durability_config(num_nodes=len(self.worker_node_list))
        config = secrets.choice(config_list)
        self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", len(self.worker_node_list),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_count'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list,
                                           destroy_setup_flag=False)
        resp = LogicalNode.get_all_pods(self.master_node_list[0],
                                        pod_prefix=constants.SERVER_POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0])
        self.log.info("Pod list are %s", resp[0])
        self.log.info("Pod count is %s", len(resp))
        assert_utils.assert_equal(len(resp), len(self.worker_node_list))
        self.log.info("===Test Completed===")

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-33221")
    def test_33221(self):
        """
        Test to verify the HA pod being deployed
        """
        config_list = self.deploy_lc_obj.get_durability_config(num_nodes=len(self.worker_node_list))
        config = secrets.choice(config_list)
        self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", (self.num_nodes - 1),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_lc_obj.test_deployment(sns_data=config['sns_data'],
                                           sns_parity=config['sns_parity'],
                                           sns_spare=config['sns_spare'],
                                           dix_data=config['dix_data'],
                                           dix_parity=config['dix_parity'],
                                           dix_spare=config['dix_spare'],
                                           cvg_count=config['cvg_count'],
                                           data_disk_per_cvg=config['data_disk_per_cvg'],
                                           master_node_list=self.master_node_list,
                                           worker_node_list=self.worker_node_list,
                                           destroy_setup_flag=False)
        resp = LogicalNode.get_all_pods(self.master_node_list[0],
                                        pod_prefix=constants.HA_POD_NAME_PREFIX)
        assert_utils.assert_true(resp[0])
        self.log.info("Pod list are %s", resp[0])
        self.log.info("Pod count is %s", len(resp))
        assert_utils.assert_equal(len(resp), 1)
        self.log.info("===Test Completed===")
