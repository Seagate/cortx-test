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

"""Prov Deployment with Redefined Structure."""
import logging
import os
import secrets
import pytest
from commons.params import LOG_DIR, LATEST_LOG_FOLDER
from commons.utils import assert_utils, support_bundle_utils, system_utils
from commons.helpers.pods_helper import LogicalNode
from config import CMN_CFG
from config import PROV_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib


class TestNamespaceDeployment:
    """Test Custom Namespace based deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.deploy_conf = PROV_CFG['k8s_cortx_deploy']
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.namespace = os.getenv("NAMESPACE", cls.deploy_conf["namespace"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        for node in CMN_CFG["nodes"]:
            vm_name = node["hostname"].split(".")[0]
            cls.host_list.append(vm_name)
            node_obj = LogicalNode(hostname=node["hostname"],
                                   username=node["username"],
                                   password=node["password"])
            if node["node_type"].lower() == "master":
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        cls.collect_sb = True
        cls.destroy_flag = True

    def teardown_method(self):
        """
        Teardown method
        """
        if self.collect_sb:
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                            scripts_path=
                                                            self.deploy_conf['k8s_dir'])
        if self.destroy_flag:
            resp = self.deploy_lc_obj.destroy_setup(self.master_node_list[0],
                                                    self.worker_node_list)
            assert_utils.assert_true(resp)

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-40440")
    def test_40440(self):
        """
        Test to verify the CORTX deployment in custom namespace
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
                                           destroy_setup_flag=True,
                                           namespace=self.namespace)
        self.collect_sb = False
        self.destroy_flag = False

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-40441")
    def test_40441(self):
        """
        Test to verify the CORTX deployment in pre defined custom namespace
        """
        self.log.info("Creating the namespace")
        custom_namespace = self.deploy_lc_obj.namespace_name_generator(8)
        self.deploy_lc_obj.create_namespace(self.master_node_list[0], custom_namespace)
        self.log.info("NAMESPACE is created %s", custom_namespace)

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
                                           destroy_setup_flag=True,
                                           namespace=custom_namespace)
        self.collect_sb = False
        self.destroy_flag = False
        self.namespace = custom_namespace
        self.log.info("Deleting the created namespace %s", custom_namespace)
        resp = self.deploy_lc_obj.del_namespace(self.master_node_list[0], custom_namespace)
        assert_utils.assert_true(resp)

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-40442")
    def test_40442(self):
        """
        Test to verify the CORTX deployment in supported char in
         name of custom namespace upto max length
        """

        custom_namespace = self.deploy_lc_obj.namespace_name_generator(
            self.deploy_conf["max_size_namespace"])
        self.log.info("NAMESPACE is %s", custom_namespace)
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
                                           destroy_setup_flag=True,
                                           namespace=custom_namespace)
        self.namespace = custom_namespace
        self.log.info("Deleting the created namespace %s", custom_namespace)
        resp = self.deploy_lc_obj.del_namespace(self.master_node_list[0], custom_namespace)
        assert_utils.assert_true(resp)
        self.collect_sb = False
        self.destroy_flag = False

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-40443")
    def test_40443(self):
        """
        Test to verify the CORTX deployment in unsupported chars in
        name of custom namespace
        """

        custom_namespace = system_utils.random_string_generator(23)
        self.log.info("NAMESPACE is %s", custom_namespace)
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
                                           setup_client_config_flag=False,
                                           run_basic_s3_io_flag=False,
                                           run_s3bench_workload_flag=False,
                                           destroy_setup_flag=False,
                                           namespace=custom_namespace)
        self.collect_sb = False
        self.destroy_flag = False
