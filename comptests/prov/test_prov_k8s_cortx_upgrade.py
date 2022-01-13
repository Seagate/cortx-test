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

"""Provisioner Component level test cases for K8s CORTX Software Upgrade."""

import logging
import os
import time
import queue
from threading import Thread
import yaml
import pytest

from commons import commands
from commons import constants as cons
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG, PROV_CFG, PROV_TEST_CFG
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

LOGGER = logging.getLogger(__name__)


class TestProvK8CortxUpgrade:
    """
    This class contains Provisioner Component level test cases for K8s CORTX Software Upgrade.
    """

    @classmethod
    def setup_class(cls):
        """Setup class"""
        LOGGER.info("STARTED: Setup Module operations")
        cls.que = queue.Queue()
        cls.repo_clone_path = "root"
        cls.deployment_version = os.getenv("DEPLOYMENT_VERSION")
        cls.upgrade_image_version = os.getenv("UPGRADE_IMAGE_VERSION")
        cls.upgrade_image = os.getenv("UPGRADE_IMAGE")
        cls.parallel_upgrade_image = os.getenv("PARALLEL_UPGRADE_IMAGE")
        cls.deploy_cfg = PROV_CFG["k8s_cortx_deploy"]
        cls.prov_deploy_cfg = PROV_TEST_CFG["k8s_prov_cortx_deploy"]
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        cls.remote_path = cons.CLUSTER_CONF_PATH
        cls.local_path = cons.LOCAL_CONF_PATH
        for node in range(cls.num_nodes):
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            cls.host_list.append(node_obj)
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                cls.master_node_obj = node_obj
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        LOGGER.info("Perform prerequisite.")
        LOGGER.info("Install k8s cluster.")
        resp = cls.deploy_lc_obj.setup_k8s_cluster(cls.master_node_list, cls.worker_node_list)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Clone Provisioner cortx framework.")
        repo_url = cls.prov_deploy_cfg["git_prov_k8_repo"]
        repo_clone_cmd = "cd {}; {}".format(cls.repo_clone_path,
                                            commands.CMD_GIT_CLONE.format(repo_url))
        for node_obj in cls.host_list:
            resp = node_obj.execute_cmd(repo_clone_cmd)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Deploy third party services.")
        for node_obj in cls.host_list:
            cmd = "cd {}; {}".format(cls.prov_deploy_cfg["git_remote_path"],
                                     cls.prov_deploy_cfg["deploy_services"])
            resp = node_obj.execute_cmd(cmd=cmd)
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Deploy CORTX cluster with image version: %s", cls.deployment_version)
        cmd = "cd {}; {}".format(cls.prov_deploy_cfg["git_remote_path"],
                                 cls.prov_deploy_cfg["deploy_cluster"].
                                 format(cls.deployment_version))
        resp = cls.master_node_obj.execute_cmd(cmd=cmd)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Wait for cluster services to start.")
        time.sleep(PROV_CFG["deploy_ff"]["per_step_delay"])
        resp = cls.deploy_lc_obj.check_s3_status(cls.master_node_obj, pod_prefix="data-node1")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Done: Setup operations finished.")

    @classmethod
    def teardown_class(cls):
        """Test teardown class."""
        LOGGER.info("Started: Teardown class operations.")
        LOGGER.info("Destroy CORTX cluster.")
        repo_name = "cortx-prvsnr"
        cmd = "cd {}; {}".format(cls.prov_deploy_cfg["git_remote_path"],
                                 cls.prov_deploy_cfg["destroy_cluster"])
        resp = cls.master_node_obj.execute_cmd(cmd=cmd)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Delete prov k8s repo.")
        repo_path = f"/{cls.repo_clone_path}/{repo_name}"
        for node_obj in cls.host_list:
            resp = node_obj.remove_dir(dpath=repo_path)
            assert_utils.assert_true(resp)
        LOGGER.info("Done: Teardown class operations completed.")

    def perform_upgrade(self, upgrade_image_version: str, exc: bool = True):
        """Function calls upgrade and put return in queue object."""
        LOGGER.info("Calling upgrade.")
        resp = self.deploy_lc_obj.upgrade_software(self.master_node_obj, upgrade_image_version,
                                                   self.prov_deploy_cfg["git_remote_path"], exc=exc)
        self.que.put(resp)

    @pytest.mark.run(order=1)
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-32442")
    def test_32442(self):
        """
        Verify CORTX Software upgrade.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get installed version.")
        resp = self.master_node_obj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        assert_utils.assert_true(resp[0], resp[1])
        stream = open(self.local_path, 'r')
        data = yaml.safe_load(stream)
        installed_version = data['cortx']['common']['release']['version']
        LOGGER.info("Current version: %s", installed_version)
        LOGGER.info("Step 1: Done.")
        LOGGER.info("Step 2: Check if installing version is higher than installed version.")
        # TODO : Better way to compare two versions.
        installing_version = self.upgrade_image_version.split(":")[1].split("-")
        installing_version = installing_version[0] + "-" + installing_version[1]
        LOGGER.info("Installing CORTX image verson: %s", installing_version)
        assert installing_version > installed_version, \
            "Installed version is higher than installing version."
        LOGGER.info("Step 2: Done.")
        # TODO : Use data-pod when cortx services framework is done.
        LOGGER.info("Step 3: Check cluster health.")
        resp = self.deploy_lc_obj.check_s3_status(self.master_node_obj, pod_prefix="data-node1")
        assert_utils.assert_true(resp[0], resp[1])
        pod_name = self.master_node_obj.get_pod_name(pod_prefix="data-node1")
        assert_utils.assert_true(pod_name[0], pod_name[1])
        resp = self.deploy_lc_obj.get_hctl_status(self.master_node_obj, pod_name[1])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Done.")
        LOGGER.info("Step 4: Start upgrade.")
        resp = self.deploy_lc_obj.upgrade_software(self.master_node_obj, self.upgrade_image_version,
                                                   self.prov_deploy_cfg["git_remote_path"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")
        LOGGER.info("Step 5: Check if installed version is equals to installing version.")
        resp = self.master_node_obj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        assert_utils.assert_true(resp[0], resp[1])
        stream = open(self.local_path, 'r')
        data = yaml.safe_load(stream)
        new_installed_version = data['cortx']['common']['release']['version']
        LOGGER.info("New CORTX image version: %s", new_installed_version)
        assert_utils.assert_equals(installing_version, new_installed_version,
                                   "Installing version is not equal to new installed version.")
        LOGGER.info("Step 5: Done.")
        # assert True
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-32586")
    def test_32586(self):
        """
        Verify pods are up and running after upgrade.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check PODs are up and running.")
        resp = self.deploy_lc_obj.check_pods_status(self.master_node_obj)
        assert_utils.assert_true(resp)
        LOGGER.info("All PODs are up and running.")
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-32549")
    def test_32549(self):
        """
        Verify cluster status after upgrade.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Check Cluster health and services.")
        time.sleep(PROV_CFG["deploy_ff"]["per_step_delay"])
        resp = self.deploy_lc_obj.check_s3_status(self.master_node_obj, pod_prefix="data-node1")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Cluster is up and all services are started.")
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-32600")
    def test_32600(self):
        """
        Verify cluster id in cluster.yaml and confstore files is same after upgrade.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get all running data pods from cluster.")
        # TODO : Get all data pods from cluster once cortx services framework is done.
        pod_name = self.master_node_obj.get_pod_name(pod_prefix="data-node1")
        assert_utils.assert_true(pod_name[0], pod_name[1])
        LOGGER.info("Step 1: Done.")
        cluster_yaml_cmd = "cat " + self.deploy_cfg["cluster_yaml_path"] + " | grep id"
        cluster_conf_cmd = "cat " + self.deploy_cfg["cluster_conf_path"] + " | grep cluster_id"
        LOGGER.info("Step 2: Fetch Cluster ID from cluster.yaml and cluster.conf.")
        cluster_id_yaml = self.master_node_obj.execute_cmd(cmd=commands.
                                                           K8S_POD_INTERACTIVE_CMD.
                                                           format(pod_name[1],
                                                                  cluster_yaml_cmd),
                                                           read_lines=True)
        assert_utils.assert_is_not_none(cluster_id_yaml)
        cluster_id_yaml = cluster_id_yaml[0].split("\n")[0].strip().split(":")[1].strip()
        cluster_id_conf = self.master_node_obj.execute_cmd(cmd=commands.
                                                           K8S_POD_INTERACTIVE_CMD.
                                                           format(pod_name[1],
                                                                  cluster_conf_cmd),
                                                           read_lines=True)
        assert_utils.assert_is_not_none(cluster_id_conf)
        cluster_id_conf = cluster_id_conf[0].split("\n")[0].strip().split(":")[1].strip()
        LOGGER.info("Step 2: Done.")
        LOGGER.info("Step 3: Compare cluster id retrieved from cluster.yaml and confstore.")
        assert_utils.assert_exact_string(cluster_id_yaml, cluster_id_conf,
                                         "Cluster ID does not match in both files.")
        LOGGER.info("Step 3: Done.")
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-32605")
    def test_32605(self):
        """
        Verify parallel upgrade fails when cluster is upgrading already.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get installed version.")
        resp = self.master_node_obj.copy_file_to_local(
            remote_path=self.remote_path, local_path=self.local_path)
        assert_utils.assert_true(resp[0], resp[1])
        stream = open(self.local_path, 'r')
        data = yaml.safe_load(stream)
        installed_version = data['cortx']['common']['release']['version']
        LOGGER.info("Current version: %s", installed_version)
        LOGGER.info("Step 1: Done.")
        LOGGER.info("Step 2: Check if installing version is higher than installed version.")
        # TODO : Better way to compare two versions.
        installing_version = self.upgrade_image.split(":")[1].split("-")
        installing_version = installing_version[0] + "-" + installing_version[1]
        LOGGER.info("Installing CORTX image verson: %s", installing_version)
        assert installing_version > installed_version, \
            "Installed version is higher than installing version."
        LOGGER.info("Step 2: Done.")
        # TODO : Use data-pod when cortx services framework is done.
        LOGGER.info("Step 3: Check cluster health.")
        resp = self.deploy_lc_obj.check_s3_status(self.master_node_obj, pod_prefix="data-node1")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Done.")
        LOGGER.info("Step 4: Test parallel upgrades.")
        parallel_upgrade_message = "Upgrade is already being performed on the cluster."
        upgrade_thread = Thread(target=self.perform_upgrade, args=([self.upgrade_image]))
        parallel_upgrade_thread = Thread(target=self.perform_upgrade,
                                         args=(self.parallel_upgrade_image, False))
        upgrade_thread.start()
        time.sleep(10)  # Wait to start upgrade_thread thread
        parallel_upgrade_thread.start()
        resp = self.que.get(1)
        assert_utils.assert_exact_string(resp[1], parallel_upgrade_message)
        upgrade_thread.join()
        LOGGER.info("Step 4: Done.")
        LOGGER.info("Test Completed.")
