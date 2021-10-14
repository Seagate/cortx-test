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

import yaml

from commons import commands as common_cmd
from commons.helpers.pods_helper import LogicalNode
from commons.utils import system_utils, assert_utils
from config import CMN_CFG, PROV_CFG

LOGGER = logging.getLogger(__name__)


class ProvDeployLCLib:
    """
    This class contains utility methods for all the operations related
    to k8s based Cortx Deployment .
    """

    def __init__(self):
        self.deploy_cfg = PROV_CFG["lc_deploy"]
        self.num_nodes = len(CMN_CFG["nodes"])
        self.worker_node_list = []
        self.master_node = None
        for node in range(self.num_nodes):
            node_obj = LogicalNode(hostname=CMN_CFG["nodes"][node]["hostname"],
                                   username=CMN_CFG["nodes"][node]["username"],
                                   password=CMN_CFG["nodes"][node]["password"])
            if CMN_CFG["nodes"][node]["node_type"].lower() == "master":
                self.master_node = node_obj
            else:
                self.worker_node_list.append(node_obj)

    def prereq_vm(self, node_obj: LogicalNode) -> tuple:
        """
        Perform prerequisite check for VM configurations
        param: node_obj : Node object to perform the checks on
        """
        LOGGER.info(
            "Starting the prerequisite checks on node %s",
            node_obj.hostname)
        LOGGER.info("Check that the host is pinging")
        node_obj.execute_cmd(cmd=
                             common_cmd.CMD_PING.format(node_obj.hostname), read_lines=True)

        LOGGER.info("Checking number of disks present")
        count = node_obj.execute_cmd(cmd=common_cmd.CMD_LSBLK, read_lines=True)
        LOGGER.info("No. of disks : %s", count[0])
        if int(count[0]) < self.deploy_cfg["prereq"]["min_disks"]:
            return False, f"Need at least " \
                          f"{self.deploy_cfg['prereq']['min_disks']} disks for deployment"

        LOGGER.info("Checking OS release version")
        resp = node_obj.execute_cmd(cmd=
                                    common_cmd.CMD_OS_REL,
                                    read_lines=True)[0].strip()
        LOGGER.info("OS Release Version: %s", resp)
        if resp not in self.deploy_cfg["prereq"]["os_release"]:
            return False, "OS version is different than expected."

        LOGGER.info("Checking kernel version")
        resp = node_obj.execute_cmd(cmd=
                                    common_cmd.CMD_KRNL_VER,
                                    read_lines=True)[0].strip()
        LOGGER.info("Kernel Version: %s", resp)
        if resp not in self.deploy_cfg["prereq"]["kernel"]:
            return False, "Kernel Version is different than expected."

        return True, "Prerequisite VM check successful"

    def prereq_local_path_prov(self, node_obj: LogicalNode, disk_partition: str):
        """
        Perform the prerequisite for Local Path Provisioner
        param: node_obj: Node object
        param: disk_partition : Mount this partition for Local Path Prov.
        """
        LOGGER.info("Create directory for Local Path provisioner")
        node_obj.make_dir(self.deploy_cfg["local_path_prov"])

        LOGGER.info("Validate if any mount point present on the disk,unmount it")
        cmd = "lsblk | grep \"{}\" |awk '{{print $7}}'".format(disk_partition)
        resp = node_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.debug("resp: %s", resp)
        for mp in resp:
            node_obj.execute_cmd("umount {}".format(mp))

        LOGGER.info("mkfs %s", disk_partition)
        resp = node_obj.execute_cmd(cmd=common_cmd.CMD_MKFS_EXT4, read_lines=True)
        LOGGER.debug("resp: %s", resp)

        LOGGER.info("Mount the file system")
        resp = node_obj.execute_cmd(
            common_cmd.CMD_MOUNT_EXT4.format(disk_partition, self.deploy_cfg["local_path_prov"]))
        LOGGER.debug("resp: %s", resp)

    def prereq_glusterfs(self, node_obj: LogicalNode):
        """
        Prerequisite for GlusterFS - Create specified directory
        param: node_obj : Node Object
        """
        LOGGER.info("Create Directories for GlusterFS")
        for each in self.deploy_cfg["glusterfs_dir"]:
            node_obj.make_dir(each)

        LOGGER.info("Install Gluster-fuse package")
        resp = node_obj.execute_cmd(
            common_cmd.RPM_INSTALL_CMD.format(self.deploy_cfg["gluster_pkg"]))
        LOGGER.debug("resp: %s", resp)

    def prereq_3rd_party_srv(self, node_obj: LogicalNode):
        """
        Prerequisite for 3rd Party Services - Create specified directory
        param: node_obj : Node Object
        """
        LOGGER.info("Create directory for 3rd Party services")
        for each in self.deploy_cfg["3rd_party_dir"]:
            node_obj.make_dir(each)

    @staticmethod
    def docker_login(node_obj: LogicalNode, docker_user: str, docker_pswd: str):
        """
        Perform Docker Login
        param: node_obj: Node Object
        param: docker_user : Docker username
        param: docker_pswd : Docker password
        """
        LOGGER.info("Perform Docker Login")
        resp = node_obj.execute_cmd(common_cmd.CMD_DOCKER_LOGIN.format(docker_user, docker_pswd))
        LOGGER.debug("resp: %s", resp)

    def prereq_git(self, node_obj: LogicalNode, git_id: str, git_token: str):
        """
        Checkout cortx-k8s code on the master node. Delete is any previous exists.
        param: node_obj : Node object to checkout code - Master node.
        param: git_id : Git ID
        param: git_token : Git token for accessing cortx-k8s repo.
        """
        LOGGER.info("Delete cortx-k8s repo on node")
        resp = node_obj.execute_cmd(common_cmd.CMD_REMOVE_DIR.format("cortx-k8s"))
        LOGGER.debug("resp: %s", resp)

        LOGGER.info("Git clone cortx-k8s repo")
        url = self.deploy_cfg["git_k8_repo"].format(git_id, git_token)
        resp = node_obj.execute_cmd(common_cmd.CMD_GIT_CLONE.format(url))
        LOGGER.debug("resp: %s", resp)

        LOGGER.info("Git checkout tag %s", self.deploy_cfg["git_tag"])
        cmd = "cd cortx-k8s && " + common_cmd.CMD_GIT_CHECKOUT.format(self.deploy_cfg["git_tag"])
        resp = node_obj.execute_cmd(cmd)
        LOGGER.debug("resp: %s", resp)

    def deploy_cluster(self, node_obj: LogicalNode, local_sol_path: str, remote_code_path: str):
        """
        Copy solution file from local path to remote path and deploy cortx cluster.
        cortx-k8s repo code should be checked out on node at remote_code_path
        param: node_obj: Node object
        param: local_sol_path: Local path for solution.yaml
        param: remote_code_path: Cortx-k8's repo Path on node
        """
        LOGGER.info("Copy Solution file to remote path")
        LOGGER.debug("Local path %s", local_sol_path)
        remote_path = remote_code_path + "solution.yaml"
        LOGGER.debug("Remote path %s", remote_path)
        if system_utils.path_exists(local_sol_path):
            node_obj.copy_file_to_remote(local_sol_path, remote_path)
        else:
            return False, f"{local_sol_path} not found"

        LOGGER.info("Deploy Cortx cloud")
        cmd = "cd {}; {}".format(remote_code_path, self.deploy_cfg["deploy_cluster"])
        resp = node_obj.execute_cmd(cmd)
        LOGGER.debug("resp :%s", resp)

    def destroy_cluster(self, node_obj: LogicalNode, remote_code_path: str):
        """
        Destroy cortx cluster
        param: node_obj: Node object
        param: remote_code_path: Cortx-k8's repo Path on node
        """
        LOGGER.info("Destroy Cortx cloud")
        cmd = "cd {}; {}".format(remote_code_path, self.deploy_cfg["destroy_cluster"])
        resp = node_obj.execute_cmd(cmd)
        LOGGER.debug("resp: %s", resp)

    def deploy_cortx_cluster(self, solution_file_path,
                             docker_username, docker_password, git_id, git_token):
        """
        Perform cortx cluster deployment
        param: solution_file_path: Local Solution file path
        param: docker_username: Docker Username
        param: docker_password: Docker password
        param: git_id: Git ID to access Cortx-k8s repo
        param: git_token: Git token to access Cortx-k8s repo
        """
        LOGGER.info("Read solution config file")
        sol_cfg = yaml.safe_load(open(solution_file_path))
        for node in self.worker_node_list:
            resp = self.prereq_vm(node)
            assert_utils.assert_true(resp[0], resp[1])
            # TODO: parse system disk and pass to local path prov: UDX-6356
            self.prereq_local_path_prov(node, "/dev/sdb")
            self.prereq_glusterfs(node)
            self.prereq_3rd_party_srv(node)

        if self.master_node is None:
            assert_utils.assert_true(False, "No master node assigned")

        self.docker_login(self.master_node, docker_username, docker_password)
        self.prereq_git(self.master_node, git_id, git_token)
        self.deploy_cluster(self.master_node, solution_file_path, self.deploy_cfg["git_remote_dir"])

