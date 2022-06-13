#!/usr/bin/python
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
import pytest

from commons import commands
from commons import constants as cons
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from config import CMN_CFG, PROV_CFG, PROV_TEST_CFG
from libs.prov.prov_k8s_cortx_upgrade import ProvUpgradeK8sCortxLib
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

LOGGER = logging.getLogger(__name__)


class TestProvK8CortxGranular:
    """
    This class contains Provisioner Component level test cases for K8s.
    CORTX Software Granular Type Upgrade.
    """

    @classmethod
    def setup_class(cls):
        """Setup class."""
        LOGGER.info("STARTED: Setup Module operations")
        cls.cortx_all_image = os.getenv("CORTX_ALL_IMAGE", None)
        cls.cortx_ha_image = os.getenv("CORTX_HA_IMAGE", None)
        cls.cortx_control_image = os.getenv("CORTX_CONTROL_IMAGE", None)
        cls.cortx_data_image = os.getenv("CORTX_DATA_IMAGE", None)
        cls.cortx_server_image = os.getenv("CORTX_SERVER_IMAGE", None)
        cls.deploy_cfg = PROV_CFG["k8s_cortx_deploy"]
        cls.prov_deploy_cfg = PROV_TEST_CFG["k8s_prov_cortx_deploy"]
        cls.deploy_obj = ProvDeployK8sCortxLib()
        cls.upgrade_obj = ProvUpgradeK8sCortxLib()
        cls.deploy_pod_obj = LogicalNode(hostname="hostname", username="user", password="pswd")
        cls.num_nodes = CMN_CFG["nodes"]
        cls.worker_node_list = []
        cls.master_node_list = []
        cls.host_list = []
        cls.local_sol_path = cons.LOCAL_SOLUTION_PATH
        for node in cls.num_nodes:
            node_obj = LogicalNode(hostname=node["hostname"],
                                   username=node["username"], password=node["password"])
            cls.host_list.append(node_obj)
            if node["node_type"].lower() == "master":
                cls.master_node_obj = node_obj
                cls.master_node_list.append(node_obj)
            else:
                cls.worker_node_list.append(node_obj)
        LOGGER.info("Done: Setup operations finished.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-37354")
    def test_37354(self):
        """
        Verify CORTX Software upgrade for HA Pod.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get installed version.")
        installed_version = self.deploy_obj.get_installed_version(self.master_node_obj)
        LOGGER.info("Current version: %s", installed_version)
        LOGGER.info("Step 1: Done.")

        LOGGER.info("Step 2: Check if installing version is higher than installed version.")
        ver_resp = self.deploy_obj.generate_and_compare_both_version(self.cortx_all_image,
                                                                     installed_version)
        assert_utils.assert_true(ver_resp)
        LOGGER.info("Step 2: Done.")

        LOGGER.info("Step 3: Check cluster health.")
        resp = self.deploy_obj.check_s3_status(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Done.")

        LOGGER.info("Step 4: Change image version in solution.yaml.")
        remote_sol_path = self.prov_deploy_cfg["git_remote_path"] + "solution.yaml"
        solution_path = self.master_node_obj.copy_file_to_local(remote_path=remote_sol_path,
                                                                local_path=self.local_sol_path)
        assert_utils.assert_true(solution_path[0], solution_path[1])
        image_dict = {"cortxha": self.cortx_ha_image}
        local_path = self.deploy_obj.update_sol_with_image_any_pod(self.local_sol_path,
                                                                   image_dict)
        assert_utils.assert_true(local_path[0], local_path[1])
        for node_obj in self.host_list:
            resp = self.deploy_obj.copy_sol_file(node_obj, local_sol_path=local_path[1],
                                                 remote_code_path=self.
                                                 prov_deploy_cfg["git_remote_path"])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")

        LOGGER.info("Step 5: Pull the images for upgrade.")
        for node_obj in self.host_list:
            for image in image_dict:
                resp = self.deploy_obj.pull_image(node_obj, image_dict[image])
                assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Done.")

        LOGGER.info("Step 6: Start upgrade.")
        LOGGER.info("Upgrading HA CORTX image to version: %s.", self.cortx_ha_image)
        resp = self.upgrade_obj.upgrade_software(self.master_node_obj,
                                                 self.prov_deploy_cfg["git_remote_path"],
                                                 granular_type="ha")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Done.")

        LOGGER.info("Step 7: Check if installed version is equals to installing version.")
        ha_pod_list = self.master_node_list[0].get_pod_name(pod_prefix=cons.HA_POD_NAME_PREFIX)
        LOGGER.info(ha_pod_list[1])
        resp = self.master_node_obj.execute_cmd(
            cmd=commands.GET_IMAGE_VERSION.format(ha_pod_list[1]), read_lines=True)
        LOGGER.info(resp)
        version = resp[1].split("cortx-all:")[1].split("-")
        new_version = version[0] + "-" + version[1].strip()
        installing_version = self.deploy_obj.generate_and_compare_both_version(
            self.cortx_all_image, installed_version)
        assert_utils.assert_equals(new_version, installing_version, "Installing version is equal"
                                                                    " to new installed version.")
        LOGGER.info("New CORTX image version: %s", new_version)
        LOGGER.info("Step 7: Done.")
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-37353")
    def test_37353(self):
        """
        Verify CORTX Software upgrade for Control Pod.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get installed version.")
        installed_version = self.deploy_obj.get_installed_version(self.master_node_obj)
        LOGGER.info("Current version: %s", installed_version)
        LOGGER.info("Step 1: Done.")

        LOGGER.info("Step 2: Check if installing version is higher than installed version.")
        ver_resp = self.deploy_obj.generate_and_compare_both_version(self.cortx_all_image,
                                                                     installed_version)
        assert_utils.assert_true(ver_resp)
        LOGGER.info("Step 2: Done.")

        LOGGER.info("Step 3: Check cluster health.")
        resp = self.deploy_obj.check_s3_status(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Done.")

        LOGGER.info("Step 4: Change image version in solution.yaml.")
        remote_sol_path = self.prov_deploy_cfg["git_remote_path"] + "solution.yaml"
        solution_path = self.master_node_obj.copy_file_to_local(remote_path=remote_sol_path,
                                                                local_path=self.local_sol_path)
        assert_utils.assert_true(solution_path[0], solution_path[1])
        image_dict = {"cortxcontrol": self.cortx_control_image}
        local_path = self.deploy_obj.update_sol_with_image_any_pod(self.local_sol_path,
                                                                   image_dict)
        assert_utils.assert_true(local_path[0], local_path[1])
        for node_obj in self.host_list:
            resp = self.deploy_obj.copy_sol_file(node_obj, local_sol_path=local_path[1],
                                                 remote_code_path=self.
                                                 prov_deploy_cfg["git_remote_path"])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")

        LOGGER.info("Step 5: Pull the images for upgrade.")
        for node_obj in self.host_list:
            for image in image_dict:
                resp = self.deploy_obj.pull_image(node_obj, image_dict[image])
                assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Done.")

        LOGGER.info("Step 6: Start upgrade.")
        LOGGER.info("Upgrading CORTX CONTROL image to version: %s.", self.cortx_control_image)
        resp = self.upgrade_obj.upgrade_software(self.master_node_obj,
                                                 self.prov_deploy_cfg["git_remote_path"],
                                                 granular_type="control")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Done.")

        LOGGER.info("Step 7: Check if installed version is equals to installing version.")
        control_pod_list = self.master_node_list[0].get_pod_name(
            pod_prefix=cons.CONTROL_POD_NAME_PREFIX)
        LOGGER.info(control_pod_list[1])
        resp = self.master_node_obj.execute_cmd(
            cmd=commands.GET_IMAGE_VERSION.format(control_pod_list[1]), read_lines=True)
        LOGGER.info(resp)
        version = resp[1].split("cortx-all:")[1].split("-")
        new_version = version[0] + "-" + version[1].strip()
        LOGGER.info(new_version)
        installing_version = self.deploy_obj.generate_and_compare_both_version(
            self.cortx_all_image, installed_version)
        LOGGER.info("New CORTX image version: %s Installing Version %s", new_version,
                    installing_version)
        assert_utils.assert_equals(installing_version, new_version,
                                   "Installing version is not equal to new installed version.")
        LOGGER.info("Step 7: Done.")
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-37355")
    def test_37355(self):
        """
        Verify CORTX Software upgrade for Data Pod.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get installed version.")
        installed_version = self.deploy_obj.get_installed_version(self.master_node_obj)
        LOGGER.info("Current version: %s", installed_version)
        LOGGER.info("Step 1: Done.")

        LOGGER.info("Step 2: Check if installing version is higher than installed version.")
        ver_resp = self.deploy_obj.generate_and_compare_both_version(self.cortx_all_image,
                                                                     installed_version)
        assert_utils.assert_true(ver_resp)
        LOGGER.info("Step 2: Done.")

        LOGGER.info("Step 3: Check cluster health.")
        resp = self.deploy_obj.check_s3_status(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Done.")

        LOGGER.info("Step 4: Change image version in solution.yaml.")
        remote_sol_path = self.prov_deploy_cfg["git_remote_path"] + "solution.yaml"
        solution_path = self.master_node_obj.copy_file_to_local(remote_path=remote_sol_path,
                                                                local_path=self.local_sol_path)
        assert_utils.assert_true(solution_path[0], solution_path[1])
        image_dict = {"cortxdata": self.cortx_data_image}
        local_path = self.deploy_obj.update_sol_with_image_any_pod(self.local_sol_path,
                                                                   image_dict)
        assert_utils.assert_true(local_path[0], local_path[1])
        for node_obj in self.host_list:
            resp = self.deploy_obj.copy_sol_file(node_obj, local_sol_path=local_path[1],
                                                 remote_code_path=self.
                                                 prov_deploy_cfg["git_remote_path"])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")

        LOGGER.info("Step 5: Pull the images for upgrade.")
        for node_obj in self.host_list:
            for image in image_dict:
                resp = self.deploy_obj.pull_image(node_obj, image_dict[image])
                assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Done.")

        LOGGER.info("Step 6: Start upgrade.")
        LOGGER.info("Upgrading CORTX DATA image to version: %s.", self.cortx_data_image)
        resp = self.upgrade_obj.upgrade_software(self.master_node_obj,
                                                 self.prov_deploy_cfg["git_remote_path"],
                                                 granular_type="data")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Done.")

        LOGGER.info("Step 7: Check if installed version is equals to installing version.")
        data_pod_list = self.master_node_list[0].get_pod_name(pod_prefix=cons.POD_NAME_PREFIX)
        LOGGER.info(data_pod_list[1])
        resp = self.master_node_obj.execute_cmd(
            cmd=commands.GET_IMAGE_VERSION.format(data_pod_list[1]), read_lines=True)
        LOGGER.info(resp)
        version = resp[1].split("cortx-all:")[1].split("-")
        new_version = version[0] + "-" + version[1].strip()
        LOGGER.info(new_version)
        installing_version = self.deploy_obj.generate_and_compare_both_version(
            self.cortx_all_image, installed_version)
        LOGGER.info("New CORTX image version: %s Installing Version %s", new_version,
                    installing_version)
        assert_utils.assert_equals(installing_version, new_version,
                                   "Installing version is not equal to new installed version.")
        LOGGER.info("Step 7: Done.")
        LOGGER.info("Test Completed.")

    @pytest.mark.lc
    @pytest.mark.comp_prov
    @pytest.mark.tags("TEST-37356")
    def test_37356(self):
        """
        Verify CORTX Software upgrade for Server Pod.
        """
        LOGGER.info("Test Started.")
        LOGGER.info("Step 1: Get installed version.")
        installed_version = self.deploy_obj.get_installed_version(self.master_node_obj)
        LOGGER.info("Current version: %s", installed_version)
        LOGGER.info("Step 1: Done.")

        LOGGER.info("Step 2: Check if installing version is higher than installed version.")
        ver_resp = self.deploy_obj.generate_and_compare_both_version(self.cortx_all_image,
                                                                     installed_version)
        assert_utils.assert_true(ver_resp)
        LOGGER.info("Step 2: Done.")

        LOGGER.info("Step 3: Check cluster health.")
        resp = self.deploy_obj.check_s3_status(self.master_node_obj)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 3: Done.")

        LOGGER.info("Step 4: Change image version in solution.yaml.")
        remote_sol_path = self.prov_deploy_cfg["git_remote_path"] + "solution.yaml"
        solution_path = self.master_node_obj.copy_file_to_local(remote_path=remote_sol_path,
                                                                local_path=self.local_sol_path)
        assert_utils.assert_true(solution_path[0], solution_path[1])
        image_dict = {"cortxserver": self.cortx_server_image}
        local_path = self.deploy_obj.update_sol_with_image_any_pod(self.local_sol_path,
                                                                   image_dict)
        assert_utils.assert_true(local_path[0], local_path[1])
        for node_obj in self.host_list:
            resp = self.deploy_obj.copy_sol_file(node_obj, local_sol_path=local_path[1],
                                                 remote_code_path=self.
                                                 prov_deploy_cfg["git_remote_path"])
            assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 4: Done.")

        LOGGER.info("Step 5: Pull the images for upgrade.")
        for node_obj in self.host_list:
            for image in image_dict:
                resp = self.deploy_obj.pull_image(node_obj, image_dict[image])
                assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 5: Done.")

        LOGGER.info("Step 6: Start upgrade.")
        LOGGER.info("Upgrading CORTX SERVER image to version: %s.", self.cortx_server_image)
        resp = self.upgrade_obj.upgrade_software(self.master_node_obj,
                                                 self.prov_deploy_cfg["git_remote_path"],
                                                 granular_type="server")
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Step 6: Done.")

        LOGGER.info("Step 7: Check if installed version is equals to installing version.")
        server_pod_list = self.master_node_list[0].get_pod_name(
            pod_prefix=cons.SERVER_POD_NAME_PREFIX)
        LOGGER.info(server_pod_list[1])
        resp = self.master_node_obj.execute_cmd(
            cmd=commands.GET_IMAGE_VERSION.format(server_pod_list[1]), read_lines=True)
        LOGGER.info(resp)
        version = resp[1].split("cortx-rgw:")[1].split("-")
        new_version = version[0] + "-" + version[1].strip()
        LOGGER.info(new_version)
        installing_version = self.deploy_obj.generate_and_compare_both_version(
            self.cortx_all_image, installed_version)
        LOGGER.info("New CORTX image version: %s Installing Version %s", new_version,
                    installing_version)
        assert_utils.assert_equals(installing_version, new_version,
                                   "Installing version is not equal to new installed version.")
        LOGGER.info("Step 7: Done.")
        LOGGER.info("Test Completed.")
