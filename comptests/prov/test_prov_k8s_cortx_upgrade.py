#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Seagate Technology LLC and/or its Affiliates
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

"""Provisioner Component level test cases for K8s CORTX Software Rolling Upgrade."""

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
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

LOGGER = logging.getLogger(__name__)


class TestProvK8CortxRollingUpgrade:
    """
    This class contains Provisioner Component level test cases for K8s
    CORTX Software Rolling Upgrade.
    """

    @classmethod
    def setup_class(cls):
        """Setup class"""
        LOGGER.info("STARTED: Setup Module operations")
        cls.que = queue.Queue()
        cls.cortx_all_image = os.getenv("CORTX_ALL_IMAGE", None)
        cls.cortx_rgw_image = os.getenv("CORTX_RGW_IMAGE", None)
        cls.cortx_all_parallel_image = os.getenv("CORTX_ALL_UPGRADE", None)
        cls.cortx_rgw_parallel_image = os.getenv("CORTX_RGW_UPGRADE", None)
        cls.deploy_cfg = PROV_CFG["k8s_cortx_deploy"]
        cls.prov_deploy_cfg = PROV_TEST_CFG["k8s_prov_cortx_deploy"]
        cls.deploy_lc_obj = ProvDeployK8sCortxLib()
        cls.num_nodes = len(CMN_CFG["nodes"])
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        cls.local_sol_path = cons.LOCAL_SOLUTION_PATH
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
        LOGGER.info("Done: Setup operations finished.")

    def perform_upgrade(self, exc: bool = True):
        """Function calls upgrade and put return value in queue object."""
        LOGGER.info("Calling upgrade.")
        resp = self.deploy_lc_obj.upgrade_software(self.master_node_obj,
                                                   self.prov_deploy_cfg["git_remote_path"],
                                                   exc=exc)
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
        resp = HAK8s.get_config_value(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        installed_version = resp[1]['cortx']['common']['release']['version']
        LOGGER.info("Current version: %s", installed_version)
        LOGGER.info("Step 1: Done.")

        LOGGER.info("Step 2: Check if installing version is higher than installed version.")
        # TODO : Better way to compare two versions.
        installing_version = self.cortx_all_image.split(":")[1].split("-")
        installing_version = installing_version[0] + "-" + installing_version[1]
        LOGGER.info("Installing CORTX image verson: %s", installing_version)
        assert installing_version > installed_version, \
            "Installed version is higher than installing version."
        LOGGER.info("Step 2: Done.")

        LOGGER.info("Step 3: Check cluster health.")
        resp = self.deploy_lc_obj.check_s3_status(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Done.")

        LOGGER.info("Step 4: Change image version in solution.yaml.")
        remote_sol_path = self.prov_deploy_cfg["git_remote_path"] + "solution.yaml"
        solution_path = self.master_node_obj.copy_file_to_local(remote_path=remote_sol_path,
                                                                local_path=self.local_sol_path)
        assert_utils.assert_true(solution_path[0], solution_path[1])
        with open(self.local_sol_path) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']
            soln.close()
        parent_key['images']['cortxcontrol'] = self.cortx_all_image
        parent_key['images']['cortxdata'] = self.cortx_all_image
        parent_key['images']['cortxserver'] = self.cortx_rgw_image
        parent_key['images']['cortxha'] = self.cortx_all_image
        parent_key['images']['cortxclient'] = self.cortx_all_image
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(self.local_sol_path, 'w') as pointer:
            yaml.dump(conf, pointer, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        for node_obj in self.host_list:
            resp = self.deploy_lc_obj.copy_sol_file(node_obj, self.local_sol_path,
                                                    self.prov_deploy_cfg["git_remote_path"])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")

        LOGGER.info("Step 5: Pull the images for upgrade.")
        for node_obj in self.host_list:
            node_obj.execute_cmd(commands.CMD_DOCKER_PULL.format(self.cortx_all_image))
            node_obj.execute_cmd(commands.CMD_DOCKER_PULL.format(self.cortx_rgw_image))
        LOGGER.info("Step 5: Done.")

        LOGGER.info("Step 6: Start upgrade.")
        LOGGER.info("Upgrading CORTX image to version: %s.", self.cortx_all_image)
        resp = self.deploy_lc_obj.upgrade_software(self.master_node_obj,
                                                   self.prov_deploy_cfg["git_remote_path"])
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Done.")

        LOGGER.info("Step 7: Check if installed version is equals to installing version.")
        resp = HAK8s.get_config_value(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        new_installed_version = resp[1]['cortx']['common']['release']['version']
        LOGGER.info("New CORTX image version: %s", new_installed_version)
        assert_utils.assert_equals(installing_version, new_installed_version,
                                   "Installing version is not equal to new installed version.")
        LOGGER.info("Step 7: Done.")
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
        resp = self.deploy_lc_obj.check_s3_status(self.master_node_obj, pod_prefix="cortx-data")
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
        pod_name = self.master_node_obj.get_pod_name(pod_prefix="cortx-data")
        assert_utils.assert_true(pod_name[0], pod_name[1])
        LOGGER.info("Step 1: Done.")

        LOGGER.info("Step 2: Fetch Cluster ID from cluster.yaml and cluster.conf.")
        cluster_yaml_cmd = "cat " + self.deploy_cfg["cluster_yaml_path"] + " | grep id"
        cluster_conf_cmd = "cat " + self.deploy_cfg["cluster_conf_path"] + " | grep cluster_id"
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
        resp = HAK8s.get_config_value(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        installed_version = resp[1]['cortx']['common']['release']['version']
        LOGGER.info("Current version: %s", installed_version)
        LOGGER.info("Step 1: Done.")

        LOGGER.info("Step 2: Check if installing version is higher than installed version.")
        # TODO : Better way to compare two versions.
        installing_version = self.cortx_all_parallel_image.split(":")[1].split("-")
        installing_version = installing_version[0] + "-" + installing_version[1]
        LOGGER.info("Installing CORTX image verson: %s", installing_version)
        assert installing_version > installed_version, \
            "Installed version is higher than installing version."
        LOGGER.info("Step 2: Done.")

        LOGGER.info("Step 3: Check cluster health.")
        resp = self.deploy_lc_obj.check_s3_status(self.master_node_obj, pod_prefix="cortx-data")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Done.")

        LOGGER.info("Step 4: Change image version in solution.yaml.")
        remote_sol_path = self.prov_deploy_cfg["git_remote_path"] + "solution.yaml"
        solution_path = self.master_node_obj.copy_file_to_local(remote_path=remote_sol_path,
                                                                local_path=self.local_sol_path)
        assert_utils.assert_true(solution_path[0], solution_path[1])
        with open(self.local_sol_path) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']
            soln.close()
        parent_key['images']['cortxcontrol'] = self.cortx_all_parallel_image
        parent_key['images']['cortxdata'] = self.cortx_all_parallel_image
        parent_key['images']['cortxserver'] = self.cortx_rgw_parallel_image
        parent_key['images']['cortxha'] = self.cortx_all_parallel_image
        parent_key['images']['cortxclient'] = self.cortx_all_parallel_image
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(self.local_sol_path, 'w') as pointer:
            yaml.dump(conf, pointer, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        for node_obj in self.host_list:
            resp = self.deploy_lc_obj.copy_sol_file(node_obj, self.local_sol_path,
                                                    self.prov_deploy_cfg["git_remote_path"])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")

        LOGGER.info("Step 5: Pull the images for upgrade.")
        for node_obj in self.host_list:
            node_obj.execute_cmd(commands.CMD_DOCKER_PULL.format(self.cortx_all_parallel_image))
            node_obj.execute_cmd(commands.CMD_DOCKER_PULL.format(self.cortx_rgw_parallel_image))
        LOGGER.info("Step 5: Done.")

        LOGGER.info("Step 6: Test parallel upgrades.")
        parallel_upgrade_message = "An upgrade is already in progress"
        upgrade_thread = Thread(target=self.perform_upgrade)
        parallel_upgrade_thread = Thread(target=self.perform_upgrade, args=(False,))
        upgrade_thread.start()
        time.sleep(10)  # Wait to start upgrade_thread thread
        parallel_upgrade_thread.start()
        resp = self.que.get(1)
        assert_utils.assert_in(parallel_upgrade_message, resp[1])
        upgrade_thread.join()
        LOGGER.info("Step 6: Done.")
        LOGGER.info("Test Completed.")
