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

"""Provisioner Component level test cases for K8s CORTX Software Granular Type Pod."""

import logging
import os
import time
import queue
from threading import Thread
import pytest

from commons import commands
from commons import constants as cons
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG, PROV_CFG, PROV_TEST_CFG
from libs.ha.ha_common_libs_k8s import HAK8s
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

LOGGER = logging.getLogger(__name__)


class TestProvK8CortxGranular:
    """
    This class contains Provisioner Component level test cases for K8s
    CORTX Software Granular Type Upgrade.
    """

    @classmethod
    def setup_class(cls):
        """Setup class"""
        LOGGER.info("STARTED: Setup Module operations")
        cls.cortx_all_image = os.getenv("CORTX_ALL_IMAGE", None)
        cls.cortx_ha_image = os.getenv("CORTX_HA_IMAGE", None)
        cls.cortx_control_image = os.getenv("CORTX_CONTROL_IMAGE", None)
        cls.cortx_data_image = os.getenv("CORTX_DATA_IMAGE", None)
        cls.cortx_server_image = os.getenv("CORTX_SERVER_IMAGE", None)
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

    def perform_upgrade(self, exc: bool = True, output=None):
        """Function calls upgrade and put return value in queue object."""
        LOGGER.info("Calling upgrade.")
        resp = self.deploy_lc_obj.upgrade_software(self.master_node_obj,
                                                   self.prov_deploy_cfg["git_remote_path"],
                                                   exc=exc)
        output.put(resp)

    @pytest.mark.run(order=1)
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-37354")
    def test_37354(self):
        """
        Verify CORTX Software upgrade for HA Pod.
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
        image_dict = {"cortxha": self.cortx_ha_image}
        local_path = self.deploy_lc_obj.update_sol_with_image_any_pod(self.local_sol_path, image_dict)
        assert_utils.assert_true(local_path[0], local_path[1])
        for node_obj in self.host_list:
            resp = self.deploy_lc_obj.copy_sol_file(node_obj, local_sol_path=local_path[1],
                                                    remote_code_path=self.
                                                    prov_deploy_cfg["git_remote_path"])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")

        LOGGER.info("Step 5: Pull the images for upgrade.")
        for node_obj in self.host_list:
            for image in image_dict:
                resp = self.deploy_lc_obj.pull_image(node_obj, image_dict[image])
                assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Done.")

        LOGGER.info("Step 6: Start upgrade.")
        LOGGER.info("Upgrading HA CORTX image to version: %s.", self.cortx_ha_image)
        resp = self.deploy_lc_obj.upgrade_software_any_pod(self.master_node_obj,
                                                   self.prov_deploy_cfg["git_remote_path"],granular_type="ha")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Done.")

        LOGGER.info("Step 7: Check if installed version is equals to installing version.")
        ha_pod_list = self.deploy_lc_obj.get_ha_pod(self.master_node_obj)
        for ha_pod_name in ha_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(
                cmd=commands.GET_POD.format(ha_pod_name),
                read_lines=True)
            resp2 = resp[1].split('"')
            new_version = resp2[1].split(":")[1].split("-")
            new_version= new_version[0] + "-" + new_version[1]
        LOGGER.info("New CORTX image version: %s Installing Version %s", new_version, installing_version)
        assert_utils.assert_equals(installing_version, new_version,
                                   "Installing version is not equal to new installed version.")
        LOGGER.info("Step 7: Done.")
        LOGGER.info("Test Completed.")

    @pytest.mark.run(order=1)
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-37353")
    def test_37353(self):
        """
        Verify CORTX Software upgrade for Control Pod.
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
        image_dict = {"cortxcontrol": self.cortx_control_image}
        local_path = self.deploy_lc_obj.update_sol_with_image_any_pod(self.local_sol_path, image_dict)
        assert_utils.assert_true(local_path[0], local_path[1])
        for node_obj in self.host_list:
            resp = self.deploy_lc_obj.copy_sol_file(node_obj, local_sol_path=local_path[1],
                                                    remote_code_path=self.
                                                    prov_deploy_cfg["git_remote_path"])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")

        LOGGER.info("Step 5: Pull the images for upgrade.")
        for node_obj in self.host_list:
            for image in image_dict:
                resp = self.deploy_lc_obj.pull_image(node_obj, image_dict[image])
                assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Done.")

        LOGGER.info("Step 6: Start upgrade.")
        LOGGER.info("Upgrading CORTX CONTROL image to version: %s.", self.cortx_control_image)
        resp = self.deploy_lc_obj.upgrade_software_any_pod(self.master_node_obj,
                                                   self.prov_deploy_cfg["git_remote_path"], granular_type="control")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Done.")

        LOGGER.info("Step 7: Check if installed version is equals to installing version.")
        control_pod_list = self.deploy_lc_obj.get_control_pod(self.master_node_obj)
        for control_pod_name in control_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(
                cmd=commands.GET_POD.format(control_pod_name),
                read_lines=True)
            resp2 = resp[1].split('"')
            new_version = resp2[1].split(":")[1].split("-")
            new_version= new_version[0] + "-" + new_version[1]
        LOGGER.info("New CORTX image version: %s Installing Version %s", new_version, installing_version)
        assert_utils.assert_equals(installing_version, new_version,
                                   "Installing version is not equal to new installed version.")
        LOGGER.info("Step 7: Done.")
        LOGGER.info("Test Completed.")

    @pytest.mark.run(order=1)
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-37355")
    def test_37355(self):
        """
        Verify CORTX Software upgrade for Data Pod.
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
        image_dict = {"cortxdata": self.cortx_data_image}
        local_path = self.deploy_lc_obj.update_sol_with_image_any_pod(self.local_sol_path, image_dict)
        assert_utils.assert_true(local_path[0], local_path[1])
        for node_obj in self.host_list:
            resp = self.deploy_lc_obj.copy_sol_file(node_obj, local_sol_path=local_path[1],
                                                    remote_code_path=self.
                                                    prov_deploy_cfg["git_remote_path"])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")

        LOGGER.info("Step 5: Pull the images for upgrade.")
        for node_obj in self.host_list:
            for image in image_dict:
                resp = self.deploy_lc_obj.pull_image(node_obj, image_dict[image])
                assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Done.")

        LOGGER.info("Step 6: Start upgrade.")
        LOGGER.info("Upgrading CORTX DATA image to version: %s.", self.cortx_data_image)
        resp = self.deploy_lc_obj.upgrade_software_any_pod(self.master_node_obj,
                                                   self.prov_deploy_cfg["git_remote_path"], granular_type="data")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Done.")

        LOGGER.info("Step 7: Check if installed version is equals to installing version.")
        data_pod_list = self.deploy_lc_obj.get_data_pods(self.master_node_obj)
        for data_pod_name in data_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(
                cmd=commands.GET_POD.format(data_pod_name),
                read_lines=True)
            resp2 = resp[1].split('"')
            new_version = resp2[1].split(":")[1].split("-")
            new_version= new_version[0] + "-" + new_version[1]
        LOGGER.info("New CORTX image version: %s Installing Version %s", new_version, installing_version)
        assert_utils.assert_equals(installing_version, new_version,
                                   "Installing version is not equal to new installed version.")
        LOGGER.info("Step 7: Done.")
        LOGGER.info("Test Completed.")

    @pytest.mark.run(order=1)
    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-37356")
    def test_37356(self):
        """
        Verify CORTX Software upgrade for Server Pod.
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
        image_dict = {"cortxserver": self.cortx_server_image}
        local_path = self.deploy_lc_obj.update_sol_with_image_any_pod(self.local_sol_path, image_dict)
        assert_utils.assert_true(local_path[0], local_path[1])
        for node_obj in self.host_list:
            resp = self.deploy_lc_obj.copy_sol_file(node_obj, local_sol_path=local_path[1],
                                                    remote_code_path=self.
                                                    prov_deploy_cfg["git_remote_path"])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")

        LOGGER.info("Step 5: Pull the images for upgrade.")
        for node_obj in self.host_list:
            for image in image_dict:
                resp = self.deploy_lc_obj.pull_image(node_obj, image_dict[image])
                assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Done.")

        LOGGER.info("Step 6: Start upgrade.")
        LOGGER.info("Upgrading CORTX SERVER image to version: %s.", self.cortx_server_image)
        resp = self.deploy_lc_obj.upgrade_software_any_pod(self.master_node_obj,
                                                   self.prov_deploy_cfg["git_remote_path"], granular_type="server")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Done.")

        LOGGER.info("Step 7: Check if installed version is equals to installing version.")
        server_pod_list = self.deploy_lc_obj.get_server_pod(self.master_node_obj)
        for server_pod_name in server_pod_list[1]:
            resp = self.master_node_obj.execute_cmd(
                cmd=commands.GET_POD.format(server_pod_name),
                read_lines=True)
            resp2 = resp[1].split('"')
            new_version = resp2[1].split(":")[1].split("-")
            new_version= new_version[0] + "-" + new_version[1]
        LOGGER.info("New CORTX image version: %s Installing Version %s", new_version, installing_version)
        assert_utils.assert_equals(installing_version, new_version,
                                   "Installing version is not equal to new installed version.")
        LOGGER.info("Step 7: Done.")
        LOGGER.info("Test Completed.")
        