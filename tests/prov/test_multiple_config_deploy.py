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
import time
from multiprocessing import Pool

import pytest

from commons import commands as common_cmd
from commons import pswdmanager
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons.utils import system_utils
from commons.utils import ext_lbconfig_utils
from config import CMN_CFG, HA_CFG, PROV_CFG, DEPLOY_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib
from libs.s3 import S3H_OBJ
from libs.s3.s3_test_lib import S3TestLib

# pylint: disable = too-many-lines


class TestMultipleConfDeploy:
    """Test Multiple config of N+K+S deployment testsuite"""

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

    # pylint: disable=too-many-arguments, too-many-locals
    def test_deployment(self, sns_data, sns_parity,
                        sns_spare, dix_data,
                        dix_parity, dix_spare,
                        cvg_count, data_disk_per_cvg):
        """
        This method is used for deployment with various config on N nodes
        """
        self.log.info("STARTED: {%s node (SNS-%s+%s+%s) (DIX-%s+%s+%s) "
                      "k8s based Cortx Deployment", len(self.worker_node_list),
                      sns_data, sns_parity, sns_spare, dix_data, dix_parity, dix_spare)

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
        self.log.info("Step 6: Check s3 server status")
        start_time = int(time.time())
        end_time = start_time + 1800  # 30 mins timeout
        while int(time.time()) < end_time:
            resp = self.deploy_lc_obj.s3_service_status(self.master_node_list[0])
            if resp[0]:
                self.log.info("####All the services online. Time Taken : %s",
                              (int(time.time()) - start_time))
                break
            time.sleep(60)
        assert_utils.assert_true(resp[0], resp[1])

        resp = system_utils.execute_cmd(common_cmd.CMD_GET_IP_IFACE.format('eth1'))
        eth1_ip = resp[1].strip("'\\n'b'")
        self.log.info("Step 7: Configure HAproxy on client")
        ext_lbconfig_utils.configure_haproxy_lb(self.master_node_list[0].hostname,
                                                self.master_node_list[0].username,
                                                self.master_node_list[0].password, eth1_ip,
                                                PROV_CFG['k8s_cortx_deploy']['pem_file_path'])

        self.log.info("Step 8: Create S3 account and configure credentials")
        resp = self.deploy_lc_obj.post_deployment_steps_lc()
        assert_utils.assert_true(resp[0], resp[1])
        access_key,secret_key = S3H_OBJ.get_local_keys()
        s3t_obj = S3TestLib(access_key=access_key, secret_key=secret_key)

        self.log.info("Step 9: Perform basic IO operations")
        bucket_name = "bucket-"+ str(int(time.time()))
        self.deploy_lc_obj.basic_io_with_parity_check_enabled(s3t_obj,bucket_name)

        self.log.info("Step 10: Perform S3bench IO")
        self.deploy_lc_obj.io_workload(access_key=access_key,
                                       secret_key=secret_key,
                                       bucket_prefix=bucket_name)
        self.log.info("ENDED: %s node (SNS-%s+%s+%s) k8s based Cortx Deployment",
                      len(self.worker_node_list), sns_data, sns_parity, sns_spare)

        self.log.info("Step 11: Destroy setup")
        self.deploy_lc_obj.destroy_setup(self.master_node_list[0],
                                         self.worker_node_list)

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31875")
    def test_31875(self):
        """
        Deployment- 3node - SNS- 4+2+0 dix 1+2+0
        """
        row_list = list()
        row_list.append(['3N'])
        config = DEPLOY_CFG['nodes_3']['config_1']
        self.log.info("Running 3 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-29975")
    def test_29975(self):
        """
        Deployment- 3node - SNS- 4+2+0 dix 1+2+0
        """
        row_list = list()
        row_list.append(['3N'])
        config = DEPLOY_CFG['nodes_3']['config_2']
        self.log.info("Running 3 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31382")
    def test_31382(self):
        """
        Deployment- 3node - SNS- 3+3+0 dix 1+2+0
        """
        row_list = list()
        row_list.append(['3N'])
        config = DEPLOY_CFG['nodes_3']['config_3']
        self.log.info("Running 3 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31384")
    def test_31384(self):
        """
        Deployment- 3node - SNS- 1+2+0 dix 1+1+0
        """
        row_list = list()
        row_list.append(['3N'])
        config = DEPLOY_CFG['nodes_3']['config_4']
        self.log.info("Running 3 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31385")
    def test_31385(self):
        """
        Deployment- 4node
        """
        row_list = list()
        row_list.append(['4N'])
        config = DEPLOY_CFG['nodes_4']['config_1']
        self.log.info("Running 4 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31386")
    def test_31386(self):
        """
        Deployment- 4node
        """
        row_list = list()
        row_list.append(['4N'])
        config = DEPLOY_CFG['nodes_4']['config_2']
        self.log.info("Running 4 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31387")
    def test_31387(self):
        """
        Deployment- 4node
        """
        row_list = list()
        row_list.append(['4N'])
        config = DEPLOY_CFG['nodes_4']['config_3']
        self.log.info("Running 4 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31388")
    def test_31388(self):
        """
        Deployment- 4node
        """
        row_list = list()
        row_list.append(['4N'])
        config = DEPLOY_CFG['nodes_4']['config_4']
        self.log.info("Running 4 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31389")
    def test_31389(self):
        """
        Deployment- 5node
        """
        row_list = list()
        row_list.append(['5N'])
        config = DEPLOY_CFG['nodes_5']['config_1']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31390")
    def test_31390(self):
        """
        Deployment- 5node - SNS- 6+4+0 dix 1+2+0
        """
        row_list = list()
        row_list.append(['5N'])
        config = DEPLOY_CFG['nodes_5']['config_2']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31391")
    def test_31391(self):
        """
        Deployment- 5node - SNS- 5+5+0 dix 1+3+0
        """
        row_list = list()
        row_list.append(['5N'])
        config = DEPLOY_CFG['nodes_5']['config_3']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31392")
    def test_31392(self):
        """
        Deployment- 5node - SNS- 10+5+0 dix 1+1+0
        """
        row_list = list()
        row_list.append(['5N'])
        config = DEPLOY_CFG['nodes_5']['config_4']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31393")
    def test_31393(self):
        """
        Deployment- 5node
        """
        row_list = list()
        row_list.append(['5N'])
        config = DEPLOY_CFG['nodes_5']['config_5']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_5'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31394")
    def test_31394(self):
        """
        Deployment- 5node - SNS- 4+1+0 dix 1+3+0
        """
        row_list = list()
        row_list.append(['5N'])
        config = DEPLOY_CFG['nodes_5']['config_6']
        self.log.info("Running 5 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_6'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31395")
    def test_31395(self):
        """
        Deployment- 6node
        """
        row_list = list()
        row_list.append(['6N'])
        config = DEPLOY_CFG['nodes_6']['config_1']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31396")
    def test_31396(self):
        """
        Deployment- 6node
        """
        row_list = list()
        row_list.append(['6N'])
        config = DEPLOY_CFG['nodes_6']['config_2']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31397")
    def test_31397(self):
        """
        Deployment- 6node
        """
        row_list = list()
        row_list.append(['6N'])
        config = DEPLOY_CFG['nodes_6']['config_3']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31398")
    def test_31398(self):
        """
        Deployment- 6node
        """
        row_list = list()
        row_list.append(['6N'])
        config = DEPLOY_CFG['nodes_6']['config_4']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31399")
    def test_31399(self):
        """
        Deployment- 6node
        """
        row_list = list()
        row_list.append(['6N'])
        config = DEPLOY_CFG['nodes_6']['config_5']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_5'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31400")
    def test_31400(self):
        """
        Deployment- 6node
        """
        row_list = list()
        row_list.append(['6N'])
        config = DEPLOY_CFG['nodes_6']['config_6']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_6'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31401")
    def test_31401(self):
        """
        Deployment- 6node
        """
        row_list = list()
        row_list.append(['6N'])
        config = DEPLOY_CFG['nodes_6']['config_7']
        self.log.info("Running 6 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_7'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31402")
    def test_31402(self):
        """
        Deployment- 7node
        """
        row_list = list()
        row_list.append(['7N'])
        config = DEPLOY_CFG['nodes_7']['config_1']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31403")
    def test_31403(self):
        """
        Deployment- 7node
        """
        row_list = list()
        row_list.append(['7N'])
        config = DEPLOY_CFG['nodes_7']['config_2']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31404")
    def test_31404(self):
        """
        Deployment- 7node
        """
        row_list = list()
        row_list.append(['7N'])
        config = DEPLOY_CFG['nodes_7']['config_3']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31405")
    def test_31405(self):
        """
        Deployment- 7node
        """
        row_list = list()
        row_list.append(['7N'])
        config = DEPLOY_CFG['nodes_7']['config_4']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31406")
    def test_31406(self):
        """
        Deployment- 7node
        """
        row_list = list()
        row_list.append(['7N'])
        config = DEPLOY_CFG['nodes_7']['config_5']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_5'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31412")
    def test_31412(self):
        """
        Deployment- 7node
        """
        row_list = list()
        row_list.append(['7N'])
        config = DEPLOY_CFG['nodes_7']['config_6']
        self.log.info("Running 7 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_6'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31414")
    def test_31414(self):
        """
        Deployment- 8node
        """
        row_list = list()
        row_list.append(['8N'])
        config = DEPLOY_CFG['nodes_8']['config_1']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31414")
    def test_31415(self):
        """
        Deployment- 8node
        """
        row_list = list()
        row_list.append(['8N'])
        config = DEPLOY_CFG['nodes_8']['config_2']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31416")
    def test_31416(self):
        """
        Deployment- 8node
        """
        row_list = list()
        row_list.append(['8N'])
        config = DEPLOY_CFG['nodes_8']['config_3']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31417")
    def test_31417(self):
        """
        Deployment- 8node
        """
        row_list = list()
        row_list.append(['8N'])
        config = DEPLOY_CFG['nodes_8']['config_4']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31418")
    def test_31418(self):
        """
        Deployment- 8node
        """
        row_list = list()
        row_list.append(['8N'])
        config = DEPLOY_CFG['nodes_8']['config_5']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_5'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31419")
    def test_31419(self):
        """
        Deployment- 8node
        """
        row_list = list()
        row_list.append(['8N'])
        config = DEPLOY_CFG['nodes_8']['config_6']
        self.log.info("Running 8 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_6'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31420")
    def test_31420(self):
        """
        Deployment- 9node - SNS- 5+4+0 dix 1+4+0
        """
        row_list = list()
        row_list.append(['9N'])
        config = DEPLOY_CFG['nodes_9']['config_5']
        self.log.info("Running 9 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_5'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31423")
    def test_31423(self):
        """
        Deployment- 9node - SNS- 7+2+0 dix 1+2+0
        """
        row_list = list()
        row_list.append(['9N'])
        config = DEPLOY_CFG['nodes_9']['config_1']
        self.log.info("Running 9 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31422")
    def test_31422(self):
        """
        Deployment- 9node - SNS- 12+6+0 dix 1+2+0
        """
        row_list = list()
        row_list.append(['9N'])
        config = DEPLOY_CFG['nodes_9']['config_2']
        self.log.info("Running 9 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31424")
    def test_31424(self):
        """
        Deployment- 9node - SNS- 20+7+0 dix 1+6+0
        """
        row_list = list()
        row_list.append(['9N'])
        config = DEPLOY_CFG['nodes_9']['config_3']
        self.log.info("Running 9 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31421")
    def test_31421(self):
        """
        Deployment- 9node - SNS- 9+9+0 dix 1+6+0
        """
        row_list = list()
        row_list.append(['9N'])
        config = DEPLOY_CFG['nodes_9']['config_4']
        self.log.info("Running 9 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31439")
    def test_31439(self):
        """
        Deployment- 10node - SNS- 9+1+0 dix 1+1+0
        """
        row_list = list()
        row_list.append(['10N'])
        config = DEPLOY_CFG['nodes_10']['config_1']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31565")
    def test_31565(self):
        """
        Deployment- 10node - SNS- 8+2+0 dix 1+2+0
        """

        row_list = list()
        row_list.append(['10N'])
        config = DEPLOY_CFG['nodes_10']['config_2']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31566")
    def test_31566(self):
        """
        Deployment- 10node - SNS- 7+3+0 dix 1+3+0
        """

        row_list = list()
        row_list.append(['10N'])
        config = DEPLOY_CFG['nodes_10']['config_3']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31567")
    def test_31567(self):
        """
        Deployment- 10node - SNS- 6+4+0 dix 1+4+0
        """
        row_list = list()
        row_list.append(['10N'])
        config = DEPLOY_CFG['nodes_10']['config_4']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31568")
    def test_31568(self):
        """
        Deployment- 10node - SNS- 5+5+0 dix 1+7+0
        """
        row_list = list()
        row_list.append(['10N'])
        config = DEPLOY_CFG['nodes_10']['config_5']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_5'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31571")
    def test_31571(self):
        """
        Deployment- 10node
        """
        row_list = list()
        row_list.append(['10N'])
        config = DEPLOY_CFG['nodes_10']['config_6']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_6'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31569")
    def test_31569(self):
        """
        Deployment- 10node
        """
        row_list = list()
        row_list.append(['10N'])
        config = DEPLOY_CFG['nodes_10']['config_7']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_7'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31570")
    def test_31570(self):
        """
        Deployment- 10node
        """
        row_list = list()
        row_list.append(['10N'])
        config = DEPLOY_CFG['nodes_10']['config_8']
        self.log.info("Running 10 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_8'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31936")
    def test_31936(self):
        """
        Deployment- 11node
        """
        row_list = list()
        row_list.append(['11N'])
        config = DEPLOY_CFG['nodes_11']['config_4']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31588")
    def test_31588(self):
        """
        Deployment- 12node
        """
        row_list = list()
        row_list.append(['12N'])
        for num in list(DEPLOY_CFG['nodes_12'].keys()):
            config = DEPLOY_CFG['nodes_12'][num]
            self.log.info("Running 12 N with config %s+%s+%s",
                          config['sns_data'], config['sns_parity'], config['sns_spare'])
            self.test_deployment(sns_data=config['sns_data'],
                                 sns_parity=config['sns_parity'],
                                 sns_spare=config['sns_spare'],
                                 dix_data=config['dix_data'],
                                 dix_parity=config['dix_parity'],
                                 dix_spare=config['dix_spare'],
                                 cvg_count=config['cvg_per_node'],
                                 data_disk_per_cvg=config['data_disk_per_cvg'])
            row_list.append([num])
            self.deploy_lc_obj.dump_in_csv(row_list, PROV_CFG["k8s_cortx_deploy"]["report"])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31589")
    def test_31589(self):
        """
        Deployment- 12node
        """
        row_list = list()
        row_list.append(['12N'])
        config = DEPLOY_CFG['nodes_12']['config_2']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31590")
    def test_31590(self):
        """
        Deployment- 12node
        """
        row_list = list()
        row_list.append(['12N'])
        config = DEPLOY_CFG['nodes_12']['config_3']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31591")
    def test_31591(self):
        """
        Deployment- 12node
        """
        row_list = list()
        row_list.append(['12N'])
        config = DEPLOY_CFG['nodes_12']['config_4']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31592")
    def test_31592(self):
        """
        Deployment- 12node
        """
        row_list = list()
        row_list.append(['12N'])
        config = DEPLOY_CFG['nodes_12']['config_5']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_5'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31593")
    def test_31593(self):
        """
        Deployment- 12node
        """
        row_list = list()
        row_list.append(['12N'])
        config = DEPLOY_CFG['nodes_12']['config_6']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_6'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31594")
    def test_31594(self):
        """
        Deployment- 12node
        """
        row_list = list()
        row_list.append(['12N'])
        config = DEPLOY_CFG['nodes_12']['config_7']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_7'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31595")
    def test_31595(self):
        """
        Deployment- 12node
        """
        row_list = list()
        row_list.append(['12N'])
        config = DEPLOY_CFG['nodes_12']['config_8']
        self.log.info("Running 12 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_8'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31938")
    def test_31938(self):
        """
        Deployment- 11node
        """
        row_list = list()
        row_list.append(['11N'])
        config = DEPLOY_CFG['nodes_11']['config_1']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31939")
    def test_31939(self):
        """
        Deployment- 11node
        """
        row_list = list()
        row_list.append(['11N'])
        config = DEPLOY_CFG['nodes_11']['config_2']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31940")
    def test_31940(self):
        """
        Deployment- 11node
        """
        row_list = list()
        row_list.append(['11N'])
        config = DEPLOY_CFG['nodes_11']['config_3']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31941")
    def test_31941(self):
        """
        Deployment- 11node
        """
        row_list = list()
        row_list.append(['11N'])
        config = DEPLOY_CFG['nodes_11']['config_5']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_5'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31942")
    def test_31942(self):
        """
        Deployment- 11node
        """
        row_list = list()
        row_list.append(['11N'])
        config = DEPLOY_CFG['nodes_11']['config_6']
        self.log.info("Running 11 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_6'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31943")
    def test_31943(self):
        """
        Deployment- 13node
        """
        row_list = list()
        row_list.append(['13N'])
        config = DEPLOY_CFG['nodes_13']['config_1']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31944")
    def test_31944(self):
        """
        Deployment- 13node
        """
        row_list = list()
        row_list.append(['13N'])
        config = DEPLOY_CFG['nodes_13']['config_2']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31945")
    def test_31945(self):
        """
        Deployment- 13node
        """
        row_list = list()
        row_list.append(['13N'])
        config = DEPLOY_CFG['nodes_13']['config_3']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31934")
    def test_31934(self):
        """
        Deployment- 13node
        """
        row_list = list()
        row_list.append(['13N'])
        config = DEPLOY_CFG['nodes_13']['config_4']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31946")
    def test_31946(self):
        """
        Deployment- 13node
        """
        row_list = list()
        row_list.append(['13N'])
        config = DEPLOY_CFG['nodes_13']['config_5']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_5'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31947")
    def test_31947(self):
        """
        Deployment- 13node
        """
        row_list = list()
        row_list.append(['13N'])
        config = DEPLOY_CFG['nodes_13']['config_6']
        self.log.info("Running 13 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_6'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31948")
    def test_31948(self):
        """
        Deployment- 14node
        """
        row_list = list()
        row_list.append(['14N'])
        config = DEPLOY_CFG['nodes_14']['config_1']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31949")
    def test_31949(self):
        """
        Deployment- 14node
        """
        row_list = list()
        row_list.append(['14N'])
        config = DEPLOY_CFG['nodes_14']['config_2']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31935")
    def test_31935(self):
        """
        Deployment- 14node
        """
        row_list = list()
        row_list.append(['14N'])
        config = DEPLOY_CFG['nodes_14']['config_3']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31950")
    def test_31950(self):
        """
        Deployment- 14node
        """
        row_list = list()
        row_list.append(['14N'])
        config = DEPLOY_CFG['nodes_14']['config_4']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31951")
    def test_31951(self):
        """
        Deployment- 14node
        """
        row_list = list()
        row_list.append(['14N'])
        config = DEPLOY_CFG['nodes_14']['config_5']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_5'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31952")
    def test_31952(self):
        """
        Deployment- 14node
        """
        row_list = list()
        row_list.append(['14N'])
        config = DEPLOY_CFG['nodes_14']['config_6']
        self.log.info("Running 14 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_6'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31572")
    def test_31572(self):
        """
        Deployment- 15node - SNS- 8+7+0 dix 1+7+0
        """

        row_list = list()
        row_list.append(['15N'])
        config = DEPLOY_CFG['nodes_15']['config_1']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_1'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31573")
    def test_31573(self):
        """
        Deployment- 15node - SNS- 9+6+0 dix 1+6+0
        """

        row_list = list()
        row_list.append(['15N'])
        config = DEPLOY_CFG['nodes_15']['config_2']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_2'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31574")
    def test_31574(self):
        """
        Deployment- 15node - SNS- 10+5+0 dix 1+5+0
        """

        row_list = list()
        row_list.append(['15N'])
        config = DEPLOY_CFG['nodes_15']['config_3']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_3'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31575")
    def test_31575(self):
        """
        Deployment- 15node - SNS- 12+3+0 dix 1+3+0
        """

        row_list = list()
        row_list.append(['15N'])
        config = DEPLOY_CFG['nodes_15']['config_4']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_4'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31576")
    def test_31576(self):
        """
        Deployment- 15node - SNS- 5+3+0 dix 1+3+0
        """
        row_list = list()
        row_list.append(['15N'])
        config = DEPLOY_CFG['nodes_15']['config_5']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_5'])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-31577")
    def test_31577(self):
        """
        Deployment- 15node - SNS- 25+5+0 dix 1+2+0
        """
        row_list = list()
        row_list.append(['15N'])
        config = DEPLOY_CFG['nodes_15']['config_6']
        self.log.info("Running 15 N with config %s+%s+%s",
                      config['sns_data'], config['sns_parity'], config['sns_spare'])
        self.test_deployment(sns_data=config['sns_data'],
                             sns_parity=config['sns_parity'],
                             sns_spare=config['sns_spare'],
                             dix_data=config['dix_data'],
                             dix_parity=config['dix_parity'],
                             dix_spare=config['dix_spare'],
                             cvg_count=config['cvg_per_node'],
                             data_disk_per_cvg=config['data_disk_per_cvg'])
        row_list.append(['config_6'])
