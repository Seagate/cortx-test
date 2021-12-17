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

"""Provisioner Component level test cases for CORTX deployment in k8s environment."""

import logging
import pytest

from commons import commands
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG, PROV_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

LOGGER = logging.getLogger(__name__)

SECRETS_FILES_LIST = ["s3_auth_admin_secret", "openldap_admin_secret", "kafka_admin_secret",
                      "csm_mgmt_admin_secret", "csm_auth_admin_secret", "consul_admin_secret",
                      "common_admin_secret"]
PVC_LIST = ["auth", "cluster.conf", "hare", "motr", "s3", "solution", "utils"]


class TestProvK8Cortx:

    @classmethod
    def setup_class(cls):
        """Setup class"""
        LOGGER.info("STARTED: Setup Module operations")
        cls.deploy_cfg = PROV_CFG["k8s_cortx_deploy"]
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        for node in range(cls.num_nodes):
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                cls.master_node_obj = node_obj
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        LOGGER.info("Done: Setup operations finished.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-30239")
    def test_30239(self):
        """
        Verify N-Node Cortx Stack Deployment in K8s environment.
        """
        LOGGER.info("STARTED: N-Node k8s based Cortx Deployment.")
        LOGGER.info("Step 1: Perform k8s Cluster Deployment.")
        resp = self.deploy_lc_obj.deploy_cortx_k8s_re_job(self.master_node_list,self.worker_node_list)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 1: Cluster Deployment completed.")
        LOGGER.info("Step 2: Check s3 server status.")
        resp = self.deploy_lc_obj.check_s3_status(self.master_node_obj,self.master_node_list)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 2: Done.")
        LOGGER.info("Step 3: Check Pods Status.")
        path = self.deploy_cfg["k8s_dir"]
        for node in self.master_node_list:
            resp = self.deploy_lc_obj.validate_cluster_status(node, path)
            assert_utils.assert_true(resp[0], resp[1])
            LOGGER.info("Step 3: Done.")
        LOGGER.info("ENDED: Test Case Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-29269")
    def test_29269(self):
        """
        Verify if all the third party services (kafka, consul, openldap) pods are running.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check third party services Pods status.")
        resp = ProvDeployK8sCortxLib.check_pods_status(self.master_node_obj)
        assert_utils.assert_true(resp)
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-28387")
    def test_28387(self):
        """
        Verify if components secrets are copied inside the POD.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check secret files are copied inside the POD.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        assert_utils.assert_true(data_pod_list[0], data_pod_list[1])
        LOGGER.info("Step 2: Check secret files are copied to each data pod.")
        secrets_path = "ls /etc/cortx/solution/secret/"
        for pod_name in data_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(cmd=commands.K8S_POD_INTERACTIVE_CMD.
                                                    format(pod_name, secrets_path),
                                                    read_lines=True)
            assert_utils.assert_is_not_none(resp)
            for secret in resp:
                secret = secret.split("\n")
                assert_utils.assert_in(secret[0], SECRETS_FILES_LIST)
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-28437")
    def test_28437(self):
        """
        Verify machine id is unique in every POD.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check every machine id is unique in each pod.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        assert_utils.assert_true(data_pod_list[0])
        LOGGER.info("Step 2: Check machine id is unique in every pod.")
        machine_id_list = []
        for pod_name in data_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(
                cmd=commands.K8S_POD_INTERACTIVE_CMD.format(pod_name, 'cat /etc/machine-id'),
                read_lines=True)
            machine_id_list.append(resp[0])
        assert_utils.assert_true(len(machine_id_list) == len(set(machine_id_list)))
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-28384")
    def test_28384(self):
        """
        Verify files are copied and accessible to containers through shared Persistent volume.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check files are copied and accessible to containers.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        assert_utils.assert_true(data_pod_list[0])
        LOGGER.info("Step 2: Check files are copied and accessible to containers.")
        for pod_name in data_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(
                cmd=commands.K8S_POD_INTERACTIVE_CMD.format(pod_name, 'ls /etc/cortx'),
                read_lines=True)
            assert_utils.assert_is_not_none(resp)
            for out in resp:
                out = out.split("\n")
                assert_utils.assert_in(out[0], PVC_LIST)
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-28351")
    def test_28351(self):
        """
        Verify cortx_setup commands are running inside Provisioner Container.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check cortx_setup commands are running inside Provisioner Container.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        assert_utils.assert_true(data_pod_list[0])
        LOGGER.info("Step 2: Check cortx_setup commands are running inside Provisioner Container.")
        for pod_name in data_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(
                cmd=commands.K8S_POD_INTERACTIVE_CMD.format(pod_name, 'cortx_setup --help'),
                read_lines=True)
            assert_utils.assert_is_not_none(resp)
            for output in resp:
                output = output.split("\n")
                resp = str(resp)
                assert_utils.assert_not_in(resp, "error")
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-29114")
    def test_29114(self):
        """
        Verify single Provisioner Container pod get deployed on each VM/node.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check single Provisioner Container pod get deployed on each VM/node.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        assert_utils.assert_true(data_pod_list[0])
        data_pod_count = (data_pod_list[1:])
        LOGGER.info("Step 2: Get all running data nodes from cluster.")
        resp = self.master_node_obj.execute_cmd(cmd=commands.CMD_GET_NODE, read_lines=True)
        node_list = resp[2:]
        LOGGER.info("Identify pods and nodes are equal.")
        assert_utils.assert_true(len(list(data_pod_count[0])) == len(node_list))
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-28436")
    def test_28436(self):
        """
        Verify cluster id from cluster.yaml matches with cluster.conf file.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        data_pod_list = ProvDeployK8sCortxLib.get_data_pods(self.master_node_obj)
        assert_utils.assert_true(data_pod_list[0])
        cluster_yaml_cmd = "cat " + self.deploy_cfg["cluster_yaml_path"] + " | grep id"
        cluster_conf_cmd = "cat " + self.deploy_cfg["cluster_conf_path"] + " | grep cluster_id"
        LOGGER.info("Step 2: Fetch Cluster ID from cluster.yaml and cluster.conf.")
        for pod_name in data_pod_list[1]:
            cluster_id_yaml = self.master_node_obj.execute_cmd(cmd=commands.
                                                               K8S_POD_INTERACTIVE_CMD.
                                                               format(pod_name,
                                                                      cluster_yaml_cmd),
                                                               read_lines=True)
            assert_utils.assert_is_not_none(cluster_id_yaml)
            cluster_id_yaml = cluster_id_yaml[0].split("\n")[0].strip().split(":")[1].strip()
            cluster_id_conf = self.master_node_obj.execute_cmd(cmd=commands.
                                                               K8S_POD_INTERACTIVE_CMD.
                                                               format(pod_name,
                                                                      cluster_conf_cmd),
                                                               read_lines=True)
            assert_utils.assert_is_not_none(cluster_id_conf)
            cluster_id_conf = cluster_id_conf[0].split("\n")[0].strip().split(":")[1].strip()
            assert_utils.assert_exact_string(cluster_id_yaml, cluster_id_conf,
                                             "Cluster ID does not match in both files..")
        LOGGER.info("Test Completed.")