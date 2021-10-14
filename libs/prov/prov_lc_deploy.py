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
import time

import yaml

from commons import commands as common_cmd
from commons.helpers.pods_helper import LogicalNode
from commons.utils import system_utils, assert_utils
from config import CMN_CFG, PROV_CFG

LOGGER = logging.getLogger(__name__)


class ProvDeployLCLib:
    """
    This class contains utility methods for all the operations related
    to Deployment for Lyve Cloud.
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

    def prereq_vm(self, node_obj: LogicalNode):
        """
        Perform prerequisite check for VM configurations
        param: node_obj : Node object to perform the checks on
        """
        try:
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

    @staticmethod
    def make_fs(node_obj: LogicalNode, disk_partition: str, timeout: int = 120):
        """
        Create ext4 file system on the disk partition specified.
        param: node_obj : Node Object
        param: disk_partition: Disk partition for creating file system.
        param: timeout : timeout for mkfs command
        """
        try:
            node_obj.connect(shell=True)
            channel = node_obj.shell_obj
            output = ""
            current_output = ""
            start_time = time.time()
            cmd = common_cmd.CMD_MKFS_EXT4.format(disk_partition) + "\n"
            LOGGER.info("Command : %s", cmd)
            channel.send(cmd)
            while (time.time() - start_time) < timeout:
                time.sleep(10)
                if channel.recv_ready():
                    current_output = channel.recv(9999).decode("utf-8")
                    output = output + current_output
                    LOGGER.info(current_output)
                if "Proceed anyway" in current_output:
                    channel.send('y\n')
                if "Writing superblocks and filesystem accounting information:" in output:
                    LOGGER.info("mkfs done!!")
                    break
            else:
                LOGGER.info("Timeout: file system creation failed")
                return False, "file system creation failed"
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployLCLib.make_fs.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error
        return True, "file system created"

    def prereq_local_path_prov(self, node_obj: LogicalNode, disk_partition: str):
        """
        Perform the prerequisite for Local Path Provisioner
        param: node_obj: Node object
        param: disk_partition : Mount this partition for Local Path Prov.
        """
        LOGGER.info("Create directory for Local Path provisioner")
        node_obj.make_dir(self.deploy_cfg["local_path_prov"])

        LOGGER.info("Validate if any mount point present on the disk,umount it")
        cmd = "lsblk | grep \"{}\" |awk '{{print $7}}'".format(disk_partition)
        resp = node_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.debug("resp: %s", resp)
        for mp in resp:
            node_obj.execute_cmd("umount {}".format(mp))

        LOGGER.info("Make file system on the system disk")
        resp = self.make_fs(node_obj, disk_partition)
        if not resp[0]:
            return resp
        LOGGER.info("Mount the file system")
        node_obj.execute_cmd(
            common_cmd.CMD_MOUNT_EXT4.format(disk_partition, self.deploy_cfg["local_path_prov"]))

    def prereq_glusterfs(self, node_obj: LogicalNode):
        """
        Prerequisite for GlusterFS - Create specified directory
        param: node_obj : Node Object
        """
        LOGGER.info("Create Directories for GlusterFS")
        for each in self.deploy_cfg["glusterfs_dir"]:
            node_obj.make_dir(each)

        LOGGER.info("Install Gluster-fuse package")
        node_obj.execute_cmd(common_cmd.RPM_INSTALL_CMD.format(self.deploy_cfg["gluster_pkg"]))

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
        node_obj.execute_cmd(common_cmd.CMD_DOCKER_LOGIN.format(docker_user, docker_pswd))

    def prereq_git(self, node_obj: LogicalNode, git_id: str, git_token: str):
        """
        Checkout cortx-k8s code on the master node. Delete is any previous exists.
        param: node_obj : Node object to checkout code - Master node.
        param: git_id : Git ID
        param: git_token : Git token for accessing cortx-k8s repo.
        """
        LOGGER.info("Delete cortx-k8s repo on node")
        node_obj.execute_cmd(common_cmd.CMD_REMOVE_DIR.format("cortx-k8s"))

        LOGGER.info("Git clone cortx-k8s repo")
        url = self.deploy_cfg["git_k8_repo"].format(git_id, git_token)
        node_obj.execute_cmd(common_cmd.CMD_GIT_CLONE.format(url))

        LOGGER.info("Git checkout tag %s", self.deploy_cfg["git_tag"])
        cmd = "cd cortx-k8s && " + common_cmd.CMD_GIT_CHECKOUT.format(self.deploy_cfg["git_tag"])
        node_obj.execute_cmd(cmd)

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
        node_obj.execute_cmd(cmd)

    def destroy_cluster(self, node_obj: LogicalNode, remote_code_path: str):
        """
        Destroy cortx cluster
        param: node_obj: Node object
        param: remote_code_path: Cortx-k8's repo Path on node
        """
        LOGGER.info("Destroy Cortx cloud")
        cmd = "cd {}; {}".format(remote_code_path, self.deploy_cfg["destroy_cluster"])
        node_obj.execute_cmd(cmd)

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
            self.prereq_vm(node)
            # TODO: parse system disk and pass to local path prov: UDX-6356
            self.prereq_local_path_prov(node, "/dev/sdb")
            self.prereq_glusterfs(node)
            self.prereq_3rd_party_srv(node)

        if self.master_node is None:
            assert_utils.assert_true(False, "No master node assigned")
        self.docker_login(self.master_node, docker_username, docker_password)
        self.prereq_git(self.master_node, git_id, git_token)
        self.deploy_cluster(self.master_node, solution_file_path, self.deploy_cfg["git_remote_dir"])

    def update_sol_yaml(self, obj: list, node_list: int, filepath,
                        **kwargs):
        """
        This function updates the yaml file
        :Param: obj: list of node object
        :Param: node_list:int the count of worker nodes
        :Param: filepath: Filename with complete path
        :Keyword: cluster_id: cluster id
        :Keyword: cvg_count: cvg_count per node
        :Keyword: type_cvg: ios or cas
        :Keyword: data_disk_per_cvg: data disk required per cvg
        :Keyword: sns_data: N
        :Keyword: sns_parity: K
        :Keyword: sns_spare: S
        :Keyword: dix_data:
        :Keyword: dix_parity:
        :Keyword: dix_spare:
        :Keyword: size_metadata: size of metadata disk
        :Keyword: size_data_disk: size of data disk
        :Keyword: skip_disk_count_check: disk count check

        """
        # cluster_id = kwargs.get("cluster_id", 1)
        cvg_count = kwargs.get("cvg_count", 1)
        # type_cvg = kwargs.get("type_cvg", "cas")
        data_disk_per_cvg = kwargs.get("data_disk_per_cvg", "0")
        sns_data = kwargs.get("sns_data", 1)
        sns_parity = kwargs.get("sns_parity", 0)
        sns_spare = kwargs.get("sns_spare", 0)
        dix_data = kwargs.get("dix_data", 1)
        dix_parity = kwargs.get("dix_parity", 2)
        dix_spare = kwargs.get("dix_spare", 0)
        size_metadata = kwargs.get("size_metadata", '5Gi')
        size_data_disk = kwargs.get("size_data_disk", '5Gi')
        skip_disk_count_check = kwargs.get("skip_disk_count_check", False)

        data_devices = list()  # empty list for data disk
        metadata_devices_per_cvg = list()  # empty metadata list

        nks = "{}+{}+{}".format(sns_data, sns_parity, sns_spare)  # Value of N+K+S for sns
        dix = "{}+{}+{}".format(dix_data, dix_parity, dix_spare)  # Value of N+K+S for dix
        valid_disk_count = sns_spare + sns_data + sns_parity
        for node_count, node_obj in enumerate(obj, start=1):
            print(node_count)
            device_list = node_obj.execute_cmd(cmd=common_cmd.CMD_LIST_DEVICES,
                                               read_lines=True)[0].split(",")
            device_list[-1] = device_list[-1].replace("\n", "")
            metadata_devices = device_list[0:cvg_count * 2]
            # This will split the metadata disk list
            # into metadata devices per cvg
            # 2 is defined the split size based
            # on disk required for metadata,system
            metadata_devices_per_cvg = [metadata_devices[i:i + 2]
                                        for i in range(0, len(metadata_devices), 2)]
            device_list_len = len(device_list)
            new_device_lst_len = (device_list_len - cvg_count * 2)
            count = cvg_count
            if data_disk_per_cvg == "0":
                data_disk_per_cvg = len(device_list[cvg_count * 2:])
            # The condition to validate the config.
            if not skip_disk_count_check and valid_disk_count > \
                    (data_disk_per_cvg * cvg_count * node_list):
                return False, "The sum of data disks per cvg " \
                              "is less than N+K+S count"
            # This condition validated the total available disk count
            # and split the disks per cvg.
            if (data_disk_per_cvg * cvg_count) < new_device_lst_len and data_disk_per_cvg != "0":
                count_end = int(data_disk_per_cvg + cvg_count * 2)
                data_devices.append(device_list[cvg_count * 2:count_end])
                while count:
                    count = count - 1
                    new_end = int(count_end + data_disk_per_cvg)
                    if new_end > new_device_lst_len:
                        break
                    data_devices_ad = device_list[count_end:new_end]
                    count_end = int(count_end + data_disk_per_cvg)
                    data_devices.append(data_devices_ad)
            else:
                print("Entered in the else to list data_devices\n")
                data_devices_f = device_list[cvg_count * 2:]
                data_devices = [data_devices_f[i:i + data_disk_per_cvg]
                                for i in range(0, len(data_devices_f), data_disk_per_cvg)]
        # Reading the yaml file
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            common = parent_key['common']  # Parent key
            # cmn_storage = common['storage']  # child of child key
            cmn_storage_sets = common['storage_sets']  # child of child key
            node = parent_key['nodes']  # Child Key
            total_nodes = node.keys()
            # Creating Default Schema to update the yaml file
            share_value = "/mnt/fs-local-volume"  # This needs to changed
            # based on disk we get in solution.yaml file
            disk_schema = {'device': data_devices[0], 'size': size_metadata}
            meta_disk_schema = {'device': metadata_devices_per_cvg[0][0],
                                'size': size_data_disk}
            data_schema = {'d1': disk_schema}
            # vol_schema = {'local': share_value, 'share': share_value}
            device_schema = {'system': share_value, 'metadata': meta_disk_schema, 'data': data_schema}
            # vol_key = {'volumes': vol_schema}
            device_key = {'devices': device_schema}
            cmn_storage_sets['durability']['sns'] = nks
            cmn_storage_sets['durability']['dix'] = dix
            key_count = len(total_nodes)
            print("key count \n", key_count, total_nodes)
            # Removing the elements from the node dict
            for key_count in list(total_nodes):
                node.pop(key_count)
            # Updating the node dict
            for item in range(0, node_list):
                dict_node = {}
                name = {'name': "node-{}".format(item + 1)}
                dict_node.update(name)
                dict_node.update(device_key)
                new_node = {'node{}'.format(item + 1): dict_node}
                node.update(new_node)
                # Updating the metadata disk in solution.yaml file
                nname = 'node{}'.format(item + 1)
                devices = node[nname]['devices']
                metadata_schema = {'device': metadata_devices_per_cvg[0][0],
                                   'size': size_metadata}
                devices['metadata'].update(metadata_schema)
                data_d = devices['data']
                for per_cvg in range(0, cvg_count):
                    for disk in range(0, data_disk_per_cvg):
                        data_disk_device = "d{}".format(disk + 1)
                        upd_disk = {data_disk_device: {'device': data_devices[per_cvg][disk],
                                                       'size': size_data_disk}}
                        data_d.update(upd_disk)
            conf['solution']['nodes'] = node
            soln.close()
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(filepath, 'w+') as soln:
            yaml.dump(conf, soln, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        return True, filepath
