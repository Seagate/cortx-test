# !/usr/bin/python
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
# pylint: disable=R0904

"""Tests Query Deployment scenarios using REST API."""

import logging
import os.path
import time

import base64
import binascii
import random
import string
from http import HTTPStatus

import pytest

from commons.helpers.pods_helper import LogicalNode
from commons.params import LOG_DIR
from commons.params import LATEST_LOG_FOLDER
from commons.utils import assert_utils
from commons.utils import support_bundle_utils
from config import CMN_CFG
from config import  PROV_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from commons import configmanager, cortxlogging
from commons.constants import K8S_SCRIPTS_PATH, K8S_PRE_DISK, POD_NAME_PREFIX
from libs.csm.csm_interface import csm_api_factory
from libs.ha.ha_common_libs_k8s import HAK8s

LOGGER = logging.getLogger(__name__)

class TestQueryDeployment():
    """Query Deployment Testsuites"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.deploy_obj = ProvDeployK8sCortxLib()
        cls.deploy_conf = PROV_CFG['k8s_cortx_deploy']
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
        cls.log_disk_size = os.getenv('log_disk_size')
        cls.ha_obj = HAK8s()
        cls.csm_obj = csm_api_factory("rest")
        cls.csm_conf = configmanager.get_config_wrapper(
            fpath="config/csm/test_rest_query_deployment.yaml")
        cls.deploy_start_time = None
        cls.deploy_end_time = None
        cls.update_seconds = cls.csm_conf["update_seconds"]
        cls.collect_sb = True

    def teardown_method(self):
        """
        Teardown method
        """
        if self.collect_sb:
            path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER)
            support_bundle_utils.collect_support_bundle_k8s(local_dir_path=path,
                                                            scripts_path=
                                                            self.deploy_conf['k8s_dir'])
        resp = self.deploy_obj.destroy_setup(self.master_node_list[0],
                                             self.worker_node_list)
        assert_utils.assert_true(resp)
        self.deploy_obj.close_connections(self.master_node_list, self.worker_node_list)

    @pytest.mark.skip(reason="Function not avaliable")
    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-45743")
    def test_45743(self):
        """
        Test to verify query should be able to fetch standard 3 node configuration.
        """
        config_list = self.deploy_obj.get_durability_config(num_nodes=len(self.worker_node_list))
        config = secrets.choice(config_list)
        self.log.info("config is picked :%s", config)
        self.log.info("Running %s N with config %s+%s+%s", (len(self.worker_node_list)),
                      config['sns_data'], config['sns_parity'],
                      config['sns_spare'])
        self.deploy_obj.test_deployment(
            sns_data=config['sns_data'], sns_parity=config['sns_parity'],
            sns_spare=config['sns_spare'], dix_data=config['dix_data'],
            dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
            cvg_count=config['cvg_count'], data_disk_per_cvg=config['data_disk_per_cvg'],
            master_node_list=self.master_node_list, worker_node_list=self.worker_node_list,
            destroy_setup_flag=False)
        resp = LogicalNode.get_all_pods(self.master_node_list[0])
        assert_utils.assert_true(resp[0])
#       self.log.info(" Send node details query request")
#       get_topology = self.csm_obj.get_system_topology()
#       resp = self.csm_obj.get_node_topology()
#       assert resp.status_code == HTTPStatus.OK

        @pytest.mark.skip(reason="Function not avaliable")
        @pytest.mark.lc
        @pytest.mark.cluster_deployment
        @pytest.mark.tags("TEST-45745")
        def test_45745(self):
            """
            Test to verify query should be able to fetch standard 5 node configuration.
            """
            config_list = self.deploy_obj.get_durability_config(num_nodes=len(self.worker_node_list))
            config = secrets.choice(config_list)
            self.log.info("config is picked :%s", config)
            self.log.info("Running %s N with config %s+%s+%s", (len(self.worker_node_list)),
                          config['sns_data'], config['sns_parity'],
                          config['sns_spare'])
            self.deploy_obj.test_deployment(
                sns_data=config['sns_data'], sns_parity=config['sns_parity'],
                sns_spare=config['sns_spare'], dix_data=config['dix_data'],
                dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
                cvg_count=config['cvg_count'], data_disk_per_cvg=config['data_disk_per_cvg'],
                master_node_list=self.master_node_list, worker_node_list=self.worker_node_list,
                destroy_setup_flag=False)
            resp = LogicalNode.get_all_pods(self.master_node_list[0])
            assert_utils.assert_true(resp[0])
#           self.log.info(" Send node details query request")
#           get_topology = self.csm_obj.get_system_topology()
#           resp = self.csm_obj.get_node_topology()
#           assert resp.status_code == HTTPStatus.OK

        @pytest.mark.skip(reason="Function not avaliable")
        @pytest.mark.lc
        @pytest.mark.cluster_deployment
        @pytest.mark.tags("TEST-45744")
        def test_45744(self):
            """
            Test to verify query should be able to fetch standard 3 node configuration
            if cluster is in degraded state.
            """
            config_list = self.deploy_obj.get_durability_config(num_nodes=len(self.worker_node_list))
            config = secrets.choice(config_list)
            self.log.info("config is picked :%s", config)
            self.log.info("Running %s N with config %s+%s+%s", (len(self.worker_node_list)),
                          config['sns_data'], config['sns_parity'],
                          config['sns_spare'])
            self.deploy_obj.test_deployment(
                sns_data=config['sns_data'], sns_parity=config['sns_parity'],
                sns_spare=config['sns_spare'], dix_data=config['dix_data'],
                dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
                cvg_count=config['cvg_count'], data_disk_per_cvg=config['data_disk_per_cvg'],
                master_node_list=self.master_node_list, worker_node_list=self.worker_node_list,
                destroy_setup_flag=False)
            resp = LogicalNode.get_all_pods(self.master_node_list[0])
            assert_utils.assert_true(resp[0])
#           self.log.info(" Send node details query request")
#           get_topology = self.csm_obj.get_system_topology()
#           resp = self.csm_obj.get_node_topology()
#           assert resp.status_code == HTTPStatus.OK

        @pytest.mark.skip(reason="Function not avaliable")
        @pytest.mark.lc
        @pytest.mark.cluster_deployment
        @pytest.mark.tags("TEST-45835")
        def test_45835(self):
            """
            Test to verify query should be able to fetch standard 3 node configuration
            if cluster is in degraded state.
            """
            config_list = self.deploy_obj.get_durability_config(num_nodes=len(self.worker_node_list))
            config = secrets.choice(config_list)
            self.log.info("config is picked :%s", config)
            self.log.info("Running %s N with config %s+%s+%s", (len(self.worker_node_list)),
                          config['sns_data'], config['sns_parity'],
                          config['sns_spare'])
            self.deploy_obj.test_deployment(
                sns_data=config['sns_data'], sns_parity=config['sns_parity'],
                sns_spare=config['sns_spare'], dix_data=config['dix_data'],
                dix_parity=config['dix_parity'], dix_spare=config['dix_spare'],
                cvg_count=config['cvg_count'], data_disk_per_cvg=config['data_disk_per_cvg'],
                master_node_list=self.master_node_list, worker_node_list=self.worker_node_list,
                destroy_setup_flag=False)
            resp = LogicalNode.get_all_pods(self.master_node_list[0])
            assert_utils.assert_true(resp[0])
#           self.log.info(" Send node details query request")
#           get_topology = self.csm_obj.get_system_topology()
#           resp = self.csm_obj.get_node_topology()
#           assert resp.status_code == HTTPStatus.OK


