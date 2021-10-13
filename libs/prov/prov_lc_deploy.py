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

"""
Provisioner utiltiy methods for Deployment of Lyve Cloud.
"""
import logging
from configparser import ConfigParser

from commons import commands as common_cmd
from commons.helpers.node_helper import Node
from commons.utils import assert_utils, system_utils
from config import CMN_CFG, PROV_CFG
import yaml
LOGGER = logging.getLogger(__name__)


class ProvDeployLCLib:
    """
    This class contains utility methods for all the operations related
    to Deployment for Lyve Cloud.
    """

    def __init__(self):
        self.deploy_cfg = PROV_CFG["lc_deploy"]
        self.num_nodes = len(CMN_CFG["nodes"])
        self.node_list = []
        self.master_node = None
        for node in range(self.num_nodes):
            node_obj = Node(hostname=CMN_CFG["nodes"][node]["hostname"],
                            username=CMN_CFG["nodes"][node]["username"],
                            password=CMN_CFG["nodes"][node]["password"])
            self.node_list.append(node_obj)
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                self.master_node = node_obj

    @staticmethod
    def prereq_vm(node_obj: Node):
        try:
            prereq_cfg = PROV_CFG["deploy_ff"]["lc_deploy"]
            LOGGER.info(
                "Starting the prerequisite checks on node %s",
                node_obj.hostname)
            LOGGER.info("Check that the host is pinging")
            node_obj.execute_cmd(cmd=
                                 common_cmd.CMD_PING.format(node_obj.hostname), read_lines=True)

            LOGGER.info("Checking number of disks present")
            count = node_obj.execute_cmd(cmd=common_cmd.CMD_LSBLK, read_lines=True)
            LOGGER.info("No. of disks : %s", count[0])
            assert_utils.assert_greater_equal(int(
                count[0]), prereq_cfg["min_disks"],
                "Need at least {} disks for deployment".format(prereq_cfg["min_disks"]))

            LOGGER.info("Checking OS release version")
            resp = node_obj.execute_cmd(cmd=
                                        common_cmd.CMD_OS_REL,
                                        read_lines=True)[0].strip()
            LOGGER.info("OS Release Version: %s", resp)
            assert_utils.assert_in(resp, prereq_cfg["os_release"],
                                   "OS version is different than expected.")

            LOGGER.info("Checking kernel version")
            resp = node_obj.execute_cmd(cmd=
                                        common_cmd.CMD_KRNL_VER,
                                        read_lines=True)[0].strip()
            LOGGER.info("Kernel Version: %s", resp)
            assert_utils.assert_in(
                resp,
                prereq_cfg["kernel"],
                "Kernel Version is different than expected.")
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployLCLib.prereq_vm.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, "Prerequisite VM check successful"

    def prereq_local_path_prov(self, node_obj: Node, disk_partition: str):
        """
        Perform the prerequisite for Local Path Provisioner
        """
        LOGGER.info("Create directory for Local Path provisioner")
        node_obj.make_dir(self.deploy_cfg["local_path_prov"])

        LOGGER.info("Make file system on the system disk")
        node_obj.execute_cmd(common_cmd.CMD_MKFS_EXT4.format(disk_partition))

        LOGGER.info("Mount the file system")
        node_obj.execute_cmd(
            common_cmd.CMD_MOUNT_EXT4.format(disk_partition, self.deploy_cfg["local_path_prov"]))

    def prereq_glusterfs(self, node_obj: Node):
        LOGGER.info("Create Directories for GlusterFS")
        for each in self.deploy_cfg["glusterfs_dir"]:
            node_obj.make_dir(each)

        LOGGER.info("Install Gluster-fuse package")
        node_obj.execute_cmd(common_cmd.RPM_INSTALL_CMD.format(self.deploy_cfg["gluster_pkg"]))

    def prereq_openldap(self, node_obj: Node):
        LOGGER.info("Create directory for 3rd Party services")
        for each in self.deploy_cfg["3rd_party_dir"]:
            node_obj.make_dir(each)

    @staticmethod
    def docker_login(node_obj, docker_user, docker_pswd):
        LOGGER.info("Perform Docker Login")
        node_obj.execute_cmd(common_cmd.CMD_DOCKER_LOGIN.format(docker_user, docker_pswd))

    def prereq_git(self, node_obj, git_id, git_token):
        LOGGER.info("Git clone cortx-k8s repo")
        url = self.deploy_cfg["git_k8_repo"].format(git_id, git_token)
        node_obj.execute_cmd(common_cmd.CMD_GIT_CLONE.format(url))

        LOGGER.info("Git checkout tag %s", self.deploy_cfg["git_tag"])
        cmd = "cd cortx-k8s && " + common_cmd.CMD_GIT_CHECKOUT.format(self.deploy_cfg["git_tag"])
        node_obj.execute_cmd(cmd)

    def deploy_cluster(self, node_obj: Node, remote_code_path: str, local_sol_path: str):
        LOGGER.info("Copy Solution file to remote path")
        if system_utils.path_exists(local_sol_path):
            node_obj.copy_file_to_remote(local_sol_path, remote_code_path)
        else:
            return False,f"{local_sol_path} not found"

        LOGGER.info("Deploy Cortx cloud")
        cmd = "cd {}; {}".format(remote_code_path, self.deploy_cfg["deploy_cluster"])
        node_obj.execute_cmd(cmd)

    def destroy_cluster(self, node_obj: Node, remote_code_path: str):
        LOGGER.info("Destroy Cortx cloud")
        cmd = "cd {}; {}".format(remote_code_path, self.deploy_cfg["destroy_cluster"])
        node_obj.execute_cmd(cmd)

    def deploy_cortx_cluster(self, solution_file_path,
                             docker_username, docker_password, git_id, git_token):
        LOGGER.info("Read solution config file")

        sol_cfg = yaml.safe_load(open(solution_file_path))
        for node in self.node_list:
            self.prereq_vm(node)
            # parse system disk and pass to local path prov: UDX-6356
            self.prereq_local_path_prov(node, "/dev/sdb")
            self.prereq_glusterfs(node)
            self.prereq_openldap(node)

        if self.master_node is None:
            assert_utils.assert_true(False, "No master node assigned")
        self.docker_login(self.master_node, docker_username, docker_password)
        self.prereq_git(self.master_node, git_id, git_token)
        self.deploy_cluster(self.master_node, self.deploy_cfg["git_remote_dir"],solution_file_path)
