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
import os
import time
import distutils.util
import pytest
from commons import configmanager, constants, commands as common_cmd
from commons.utils import assert_utils, system_utils, ext_lbconfig_utils
from commons.helpers.pods_helper import LogicalNode
from config import CMN_CFG, PROV_CFG
from libs.s3 import S3H_OBJ
from libs.s3.s3_test_lib import S3TestLib
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

DEPLOY_CFG = configmanager.get_config_wrapper(fpath="config/prov/deploy_config.yaml")


class TestProvPodsDeployment:
    """Test Prov Redefined structure deployment testsuite"""

    @classmethod
    def setup_class(cls):
        """Setup class"""
        cls.log = logging.getLogger(__name__)
        cls.setup_k8s_cluster_flag = bool(distutils.util.strtobool(os.getenv("setup_k8s_cluster")))
        cls.setup_client_config_flag = \
            bool(distutils.util.strtobool(os.getenv("setup_client_config")))
        cls.cortx_cluster_deploy_flag = \
            bool(distutils.util.strtobool(os.getenv("cortx_cluster_deploy")))
        cls.run_basic_s3_io_flag = bool(distutils.util.strtobool(os.getenv("run_basic_s3_io")))
        cls.run_s3bench_workload_flag = \
            bool(distutils.util.strtobool(os.getenv("run_s3bench_workload")))
        cls.collect_support_bundle = \
            bool(distutils.util.strtobool(os.getenv("collect_support_bundle")))
        cls.destroy_setup_flag = bool(distutils.util.strtobool(os.getenv("destroy_setup")))
        cls.conf = (os.getenv("EC_CONFIG", "")).lower()
        cls.s3_status_flag = bool(distutils.util.strtobool(os.getenv("s3_status_flag", True)))
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

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-33219")
    def test_33219(self):
        """
        Deployment- N node config_1
        """
        row_list = list()
        row_list.append(['3N'])
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
        row_list.append(['config_1'])
        pod_prefix_list = [constants.POD_NAME_PREFIX, constants.SERVER_POD_NAME_PREFIX,
                           constants.HA_POD_NAME_PREFIX, constants.CONTROL_POD_NAME_PREFIX]
        for pod_prefix in pod_prefix_list:
            resp = self.deploy_lc_obj.get_pods(self.master_node_list[0], pod_prefix=pod_prefix)
            assert_utils.assert_true(resp)
            self.log.info("Pod list are %s", resp[1])

    @pytest.mark.lc
    @pytest.mark.cluster_deployment
    @pytest.mark.tags("TEST-33220")
    def test_33220(self):
        """
        test to validate the s3 status from all data pods
        """
        config = DEPLOY_CFG['nodes_3']['config_1']
        if self.setup_k8s_cluster_flag:
            self.log.info("Step to Perform k8s Cluster Deployment")
            resp = self.deploy_lc_obj.setup_k8s_cluster(self.master_node_list, self.worker_node_list)
            assert_utils.assert_true(resp[0], resp[1])
            self.log.info("Step to Taint master nodes if not already done.")
            for node in self.master_node_list:
                resp = self.deploy_lc_obj.validate_master_tainted(node)
                if not resp:
                    self.deploy_lc_obj.taint_master(node)

        if self.cortx_cluster_deploy_flag:
            self.log.info("Step to Download solution file template")
            path = self.deploy_lc_obj.checkout_solution_file(self.deploy_lc_obj.git_script_tag)
            self.log.info("Step to Update solution file template")
            resp = self.deploy_lc_obj.update_sol_yaml(worker_obj=self.worker_node_list, filepath=path,
                                                      cortx_image=self.deploy_lc_obj.cortx_image,
                                                      sns_data=config['sns_data'],
                                                      sns_parity=config['sns_parity'],
                                                      sns_spare=config['sns_spare'],
                                                      dix_data=config['dix_data'],
                                                      dix_parity=config['dix_parity'],
                                                      dix_spare=config['dix_spare'],
                                                      cvg_count=config['cvg_per_node'],
                                                      data_disk_per_cvg=config['data_disk_per_cvg'],
                                                      size_data_disk="20Gi", size_metadata="20Gi")
            assert_utils.assert_true(resp[0], "Failure updating solution.yaml")
            with open(resp[1]) as file:
                self.log.info("The detailed solution yaml file is\n")
                for line in file.readlines():
                    self.log.info(line)
            sol_file_path = resp[1]
            system_disk_dict = resp[2]
            self.log.info("Step to Perform Cortx Cluster Deployment")
            resp = self.deploy_lc_obj.deploy_cortx_cluster(sol_file_path, self.master_node_list,
                                                           self.worker_node_list, system_disk_dict,
                                                           self.deploy_lc_obj.docker_username,
                                                           self.deploy_lc_obj.docker_password,
                                                           self.deploy_lc_obj.git_script_tag)
            assert_utils.assert_true(resp[0], resp[1])
            pod_status = self.master_node_list[0].execute_cmd(cmd=common_cmd.K8S_GET_PODS,
                                                              read_lines=True)
            self.log.debug("\n=== POD STATUS ===\n")
            self.log.debug(pod_status)
        if self.s3_status_flag:
            self.log.info("Step to Check s3 server status")
            # s3_status = self.deploy_lc_obj.check_s3_status(self.master_node_list[0])
            # self.log.info("s3 resp is %s", s3_status)
            resp = self.deploy_lc_obj.get_pods(self.master_node_list[0],
                                               pod_prefix=constants.POD_NAME_PREFIX)
            data_pod_list = resp[1]
            start_time = int(time.time())
            end_time = start_time + 900  # 30 mins timeout
            while int(time.time()) < end_time:
                for data_pod in data_pod_list:
                    resp1 = self.deploy_lc_obj.get_hctl_status(self.master_node_list[0], data_pod)
                    if resp1[0]:
                        self.log.info("####All the services online. Time Taken : %s",
                                      (int(time.time()) - start_time))
                    assert_utils.assert_true(resp1[0], resp1[1])
                time.sleep(60)
                break

        if self.setup_client_config_flag:
            resp = system_utils.execute_cmd(common_cmd.CMD_GET_IP_IFACE.format('eth1'))
            eth1_ip = resp[1].strip("'\\n'b'")
            self.log.info("Configure HAproxy on client")
            ext_lbconfig_utils.configure_haproxy_lb(self.master_node_list[0].hostname,
                                                    self.master_node_list[0].username,
                                                    self.master_node_list[0].password,
                                                    eth1_ip)
            self.log.info("Step to Create S3 account and configure credentials")
            resp = self.deploy_lc_obj.post_deployment_steps_lc()
            assert_utils.assert_true(resp[0], resp[1])
            access_key, secret_key = S3H_OBJ.get_local_keys()
            s3t_obj = S3TestLib(access_key=access_key, secret_key=secret_key)
            if self.run_basic_s3_io_flag:
                self.log.info("Step to Perform basic IO operations")
                bucket_name = "bucket-" + str(int(time.time()))
                self.deploy_lc_obj.basic_io_write_read_validate(s3t_obj, bucket_name)
            if self.run_s3bench_workload_flag:
                self.log.info("Step to Perform S3bench IO")
                bucket_name = "bucket-" + str(int(time.time()))
                self.deploy_lc_obj.io_workload(access_key=access_key, secret_key=secret_key,
                                               bucket_prefix=bucket_name)

        if self.destroy_setup_flag:
            self.log.info("Step to Destroy setup")
            resp = self.deploy_lc_obj.destroy_setup(self.master_node_list[0], self.worker_node_list)
            assert_utils.assert_true(resp[0], resp[1])

        self.log.info("ENDED: %s node (SNS-%s+%s+%s) k8s based Cortx Deployment",
                      len(self.worker_node_list), config["sns_data"], config["sns_parity"],
                      config["sns_spare"])
