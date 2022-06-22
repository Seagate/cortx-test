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

"""
Provisioner utility methods for Upgrade of k8s based Cortx Upgrade
"""
import logging
import os
from string import Template
from commons import commands as common_cmd
from commons import constants as cons
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from libs.prov.prov_k8s_cortx_deploy import ProvDeployK8sCortxLib

LOGGER = logging.getLogger(__name__)


class ProvUpgradeK8sCortxLib:
    """
    This class contains utility methods for all the operations related
    to k8s based Cortx Upgrade .
    """

    def __init__(self):
        self.prov_obj = ProvDeployK8sCortxLib()
        self.cortx_upg_image = os.getenv("CORTX_CONTROL_IMAGE", None)
        self.cortx_server_upg_image = os.getenv("CORTX_SERVER_IMAGE", None)
        self.cortx_data_upg_image = os.getenv("CORTX_DATA_IMAGE", None)
        self.local_sol_path = cons.LOCAL_SOLUTION_PATH

    def upgrade_software(self, node_obj: LogicalNode, git_remote_path: str,
                         exc: bool = True, **kwargs) -> tuple:
        """
        Helper function to Upgrade CORTX stack.
        :param node_obj: Master node(Logical Node object)
        :param git_remote_path: Remote path of repo.
        :keyword upgrade_type: Type of upgrade (rolling or cold).
        :keyword granular_type: Type to upgrade all or particular pod.
        :keyword flag: Mode of upgrade [start,suspend,resume,status]
        :param exc: Flag to disable/enable exception raising
        :return: True/False resp
        """
        menu_list = ["suspend", "resume", "status"]
        upgrade_type = kwargs.get("upgrade_type", self.prov_obj.deploy_cfg["upgrade_type_rolling"])
        granular_type = kwargs.get("granular_type", self.prov_obj.deploy_cfg["granular_type"])
        flag = kwargs.get("flag", None)
        LOGGER.info("Upgrading CORTX..... %s, %s, %s", upgrade_type, granular_type, flag)
        if upgrade_type == self.prov_obj.deploy_cfg["upgrade_type_rolling"]:
            upg_cmd = Template(common_cmd.UPGRADE_CLUSTER_CMD).substitute(dir=git_remote_path, pod=
                                                                          granular_type)
            if flag in menu_list:
                upg_cmd = Template(common_cmd.UPGRADE_NEG_CMD).substitute(dir=git_remote_path) + \
                          " " + flag
        else:
            upg_cmd = Template(common_cmd.UPGRADE_NEG_CMD).substitute(dir=git_remote_path) + "-" + \
                      self.prov_obj.deploy_cfg["upgrade_type_cold"]
        resp = node_obj.execute_cmd(cmd=upg_cmd, read_lines=True, exc=exc, timeout=
                                    self.prov_obj.deploy_cfg["timeout"]["upgrade"], recv_ready=
                                    True)
        if isinstance(resp, bytes):
            resp = str(resp, 'UTF-8')
        LOGGER.debug("".join(resp).replace("\\n", "\n"))
        resp = "".join(resp).replace("\\n", "\n")
        if "Error" in resp or "Failed" in resp:
            return False, resp
        return True, resp

    def service_upgrade_software(self, node_obj: LogicalNode, upgrade_image_version: str) -> tuple:
        """
        Helper function to upgrade.
        :param node_obj: Master node(Logical Node object)
        :param upgrade_image_version: Version Image to Upgrade.
        :return: resp
        """
        LOGGER.info("Upgrading CORTX image to version: %s.", upgrade_image_version)
        upg_disrupt = Template(common_cmd.UPGRADE_NEG_CMD).substitute(
            dir=self.prov_obj.deploy_cfg["k8s_dir"]) + "-i" + upgrade_image_version + "-r"
        resp = node_obj.execute_cmd(upg_disrupt, read_lines=True)
        return resp

    def retain_solution_file(self, master_node_obj, **kwargs):
        """
        This method is used to retain the original solution.yaml file
        and later update teh file with newer images
        :param: master_node_obj: node obj for master node
        :keyword:cortx_control_img: Upgrade Image for control pod
        :keyword:cortx_data_img: Upgrade Image for data pod
        :keyword:cortx_server_img : Upgrade Image for server pod
        :keyword:git_branch : git branch
        """
        cortx_control_image = kwargs.get("cortx_control_img", self.cortx_upg_image)
        cortx_data_image = kwargs.get("cortx_data_img", self.cortx_data_upg_image)
        cortx_server_image = kwargs.get("cortx_server_img", self.cortx_server_upg_image)
        git_branch = kwargs.get("git_branch", self.prov_obj.deploy_cfg["prov_branch"])
        remote_sol_path = self.prov_obj.deploy_cfg["k8s_dir"] + "solution.yaml"
        master_node_obj.copy_file_to_local(remote_path=remote_sol_path,
                                           local_path=self.local_sol_path)
        self.prov_obj.prereq_git(master_node_obj, git_branch)
        local_path = self.prov_obj.update_image_section_sol_file(self.local_sol_path, self.prov_obj
                                                                 .deploy_cfg["third_party_images"],
                                                                 cortx_image=cortx_control_image,
                                                                 cortx_server_image=
                                                                 cortx_server_image,
                                                                 cortx_data_image=
                                                                 cortx_data_image)
        assert_utils.assert_true(local_path[0], local_path[1])
        resp = self.prov_obj.copy_sol_file(master_node_obj, local_sol_path=local_path[1],
                                           remote_code_path=self.prov_obj.deploy_cfg["k8s_dir"])
        assert_utils.assert_true(resp[0], resp[1])
