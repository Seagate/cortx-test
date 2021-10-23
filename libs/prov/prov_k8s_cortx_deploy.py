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
Provisioner utiltiy methods for Deployment of k8s based Cortx Deployment
"""
import logging

import yaml

from commons import commands as common_cmd
from commons.helpers.health_helper import Health
from commons.helpers.pods_helper import LogicalNode
from commons.utils import system_utils, assert_utils
from config import PROV_CFG
from libs.prov.provisioner import Provisioner

LOGGER = logging.getLogger(__name__)


class ProvDeployK8sCortxLib:
    """
    This class contains utility methods for all the operations related
    to k8s based Cortx Deployment .
    """

    def __init__(self):
        self.deploy_cfg = PROV_CFG["k8s_cortx_deploy"]

    @staticmethod
    def setup_k8s_cluster(master_node_list: list, worker_node_list: list,
                          taint_master: bool = True) -> tuple:
        """
        Setup k8s cluster using RE jenkins job
        param: master_node_list : List of all master nodes(Logical Node object)
        param: worker_node_list : List of all worker nodes(Logical Node object)
        param: taint_master : Taint master - boolean
        return : True/False and success/failure message
        """
        k8s_deploy_cfg = PROV_CFG["k8s_cluster_deploy"]
        LOGGER.info("Create inputs for RE jenkins job")
        hosts_input_str = []
        jen_parameter = {}
        if len(master_node_list) > 0:
            # TODO : handle multiple master node case.
            input_str = f'hostname={master_node_list[0].hostname},' \
                        f'user={master_node_list[0].username},' \
                        f'pass={master_node_list[0].password}'
            hosts_input_str.append(input_str)
        else:
            return False, "Master Node List is empty"

        if len(worker_node_list) > 0:
            for each in worker_node_list:
                input_str = f'hostname={each.hostname},' \
                            f'user={each.username},' \
                            f'pass={each.password}'
                hosts_input_str.append(input_str)
        else:
            return False, "Worker Node List is empty"
        hosts = "\n".join(each for each in hosts_input_str)
        jen_parameter["hosts"] = hosts
        jen_parameter["TAINT"] = taint_master

        output = Provisioner.build_job(
            k8s_deploy_cfg["job_name"], jen_parameter, k8s_deploy_cfg["auth_token"],
            k8s_deploy_cfg["jenkins_url"])
        LOGGER.info("Jenkins Build URL: {}".format(output['url']))
        if output['result'] == "SUCCESS":
            LOGGER.info("k8s Cluster Deployment successful")
            return True, output['result']
        else:
            LOGGER.error(f"k8s Cluster Deployment {output['result']},please check URL")
            return False, output['result']

    @staticmethod
    def validate_master_tainted(node_obj: LogicalNode) -> bool:
        """
        Validate master node tainted.
        param: node_obj: Master node object
        return: Boolean
        """
        LOGGER.info("Check if master is tainted")
        resp = node_obj.execute_cmd(common_cmd.K8S_CHK_TAINT.format(node_obj.hostname))
        LOGGER.debug("resp: %s", resp)
        if isinstance(resp, bytes):
            resp = str(resp, 'UTF-8')
        if "NoSchedule" in resp:
            LOGGER.info("%s is tainted", node_obj.hostname)
            return True
        LOGGER.info("%s is not tainted", node_obj.hostname)
        return False

    @staticmethod
    def taint_master(node_obj: LogicalNode):
        """
        Taint master node.
        param: node_obj: Master node object
        """
        LOGGER.info("Adding taint to %s", node_obj.hostname)
        resp = node_obj.execute_cmd(common_cmd.K8S_TAINT_NODE.format(node_obj.hostname))
        LOGGER.debug("resp: %s", resp)

    def prereq_vm(self, node_obj: LogicalNode) -> tuple:
        """
        Perform prerequisite check for VM configurations
        param: node_obj : Node object to perform the checks on
        return: True/False and success/failure message
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

    def prereq_git(self, node_obj: LogicalNode, git_id: str, git_token: str, git_tag: str):
        """
        Checkout cortx-k8s code on the  node. Delete is any previous exists.
        param: node_obj : Node object to checkout code - node.
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

        LOGGER.info("Git checkout tag %s", git_tag)
        cmd = "cd cortx-k8s && " + common_cmd.CMD_GIT_CHECKOUT.format(git_tag)
        resp = node_obj.execute_cmd(cmd)
        LOGGER.debug("resp: %s", resp)

    def execute_prereq_cortx(self, node_obj: LogicalNode, remote_code_path: str, system_disk: str):
        """
        Execute prerq script on worker node,
        param: node_obj: Worker node object
        param: system_disk: parameter to prereq script
        """
        LOGGER.info("Execute prereq script")
        cmd = "cd {}; {} {}".format(remote_code_path, self.deploy_cfg["exe_prereq"], system_disk)
        resp = node_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.debug("\n".join(resp).replace("\\n", "\n"))

    def copy_sol_file(self, node_obj: LogicalNode, local_sol_path: str,
                      remote_code_path: str):
        """
        Copy Solution file from local path tp remote path
        """
        LOGGER.info("Copy Solution file to remote path")
        LOGGER.debug("Local path %s", local_sol_path)
        remote_path = remote_code_path + "solution.yaml"
        LOGGER.debug("Remote path %s", remote_path)
        if system_utils.path_exists(local_sol_path):
            node_obj.copy_file_to_remote(local_sol_path, remote_path)
            return True, f"File copied at {remote_path}"
        return False, f"{local_sol_path} not found"

    def deploy_cluster(self, node_obj: LogicalNode, remote_code_path: str) -> tuple:
        """
        Deploy cortx cluster.
        cortx-k8s repo code should be checked out on node at remote_code_path
        param: node_obj: Node object
        param: remote_code_path: Cortx-k8s repo Path on node
        return : True/False and resp
        """
        LOGGER.info("Deploy Cortx cloud")
        cmd = "cd {}; {}".format(remote_code_path, self.deploy_cfg["deploy_cluster"])
        resp = node_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.debug("\n".join(resp).replace("\\n", "\n"))
        return True, resp

    def deploy_cortx_cluster(self, sol_file_path: str, master_node_list: list,
                             worker_node_list: list, system_disk_dict: dict,
                             docker_username: str, docker_password: str, git_id: str,
                             git_token: str, git_tag) -> tuple:
        """
        Perform cortx cluster deployment
        param: solution_file_path: Local Solution file path
        param: master_node_list : List of all master nodes(Logical Node object)
        param: worker_node_list : List of all worker nodes(Logical Node object)
        param: docker_username: Docker Username
        param: docker_password: Docker password
        param: git_id: Git ID to access Cortx-k8s repo
        param: git_token: Git token to access Cortx-k8s repo
        return : True/False and resp
        """
        if len(master_node_list) == 0:
            return False, "Minimum one master node needed for deployment"
        if len(worker_node_list) == 0:
            return False, "Minimum one worker node needed for deployment"

        for node in worker_node_list:
            resp = self.prereq_vm(node)
            assert_utils.assert_true(resp[0], resp[1])
            system_disk = system_disk_dict[node.hostname]
            self.docker_login(node, docker_username, docker_password)
            self.prereq_git(node, git_id, git_token, git_tag)
            self.copy_sol_file(node, sol_file_path, self.deploy_cfg["git_remote_dir"])
            # system disk will be used mount /mnt/fs-local-volume on worker node
            self.execute_prereq_cortx(node, self.deploy_cfg["git_remote_dir"], system_disk)

        self.docker_login(master_node_list[0], docker_username, docker_password)
        self.prereq_git(master_node_list[0], git_id, git_token, git_tag)
        self.copy_sol_file(master_node_list[0], sol_file_path, self.deploy_cfg["git_remote_dir"])
        resp = self.deploy_cluster(master_node_list[0], self.deploy_cfg["git_remote_dir"])
        if resp[0]:
            LOGGER.info("Validate all cluster services are online using hclt status")
            health_obj = Health(hostname=master_node_list[0].hostname,
                                username=master_node_list[0].username,
                                password=master_node_list[0].password)
            resp = health_obj.all_cluster_services_online()
            LOGGER.debug("resp: %s", resp)
            return resp

        return resp

    def checkout_solution_file(self, token, git_tag):
        url = self.deploy_cfg["git_k8_repo_file"].format(token, git_tag)
        cmd = common_cmd.CMD_CURL.format(self.deploy_cfg["template_path"], url)
        system_utils.execute_cmd(cmd=cmd)
        return self.deploy_cfg["template_path"]

    def update_sol_yaml(self, worker_obj: list, filepath,
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
        returns the status, filepath and system reserved disk

        """
        # cluster_id = kwargs.get("cluster_id", 1)
        cvg_count = kwargs.get("cvg_count", 1)
        cvg_type = kwargs.get("cvg_type", "ios")
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
        new_filepath = self.deploy_cfg['new_file_path']
        data_devices = list()  # empty list for data disk
        sys_disk_pernode = {}  # empty dict
        node_list = len(worker_obj)
        nks = "{}+{}+{}".format(sns_data, sns_parity, sns_spare)  # Value of N+K+S for sns
        dix = "{}+{}+{}".format(dix_data, dix_parity, dix_spare)  # Value of N+K+S for dix
        valid_disk_count = sns_spare + sns_data + sns_parity
        metadata_devices = []
        for node_count, node_obj in enumerate(worker_obj, start=1):
            LOGGER.info(node_count)
            device_list = node_obj.execute_cmd(cmd=common_cmd.CMD_LIST_DEVICES,
                                               read_lines=True)[0].split(",")
            device_list[-1] = device_list[-1].replace("\n", "")
            metadata_devices = device_list[1:cvg_count + 1]
            # This will split the metadata disk list
            # into metadata devices per cvg
            # 2 is defined the split size based
            # on disk required for metadata,system
            device_list_len = len(device_list)
            new_device_lst_len = (device_list_len - cvg_count)
            count = cvg_count
            if data_disk_per_cvg == "0":
                data_disk_per_cvg = len(device_list[cvg_count + 1:])
            # The condition to validate the config.
            if not skip_disk_count_check and valid_disk_count > \
                    (data_disk_per_cvg * cvg_count * node_list):
                return False, "The sum of data disks per cvg " \
                              "is less than N+K+S count"
            if len(data_devices) < data_disk_per_cvg * cvg_count:
                return False, "The requested data disk is more than" \
                              " the data disk available on the system"
            # This condition validated the total available disk count
            # and split the disks per cvg.

            if (data_disk_per_cvg * cvg_count) < new_device_lst_len and data_disk_per_cvg != "0":
                count_end = int(data_disk_per_cvg + cvg_count + 1)
                data_devices.append(device_list[cvg_count + 1:count_end])
                while count:
                    count = count - 1
                    new_end = int(count_end + data_disk_per_cvg)
                    if new_end > new_device_lst_len:
                        break
                    data_devices_ad = device_list[count_end:new_end]
                    count_end = int(count_end + data_disk_per_cvg)
                    data_devices.append(data_devices_ad)
            else:
                data_devices_f = device_list[cvg_count:]
                data_devices = [data_devices_f[i:i + data_disk_per_cvg]
                                for i in range(0, len(data_devices_f), data_disk_per_cvg)]

            # Create dict for host and disk
            system_disk = device_list[0]
            schema = {node_obj.hostname: system_disk}
            sys_disk_pernode.update(schema)

        # Reading the yaml file
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            common = parent_key['common']  # Parent key
            storage = parent_key['storage']  # child of child key
            cmn_storage_sets = common['storage_sets']  # child of child key
            node = parent_key['nodes']  # Child Key
            total_nodes = node.keys()
            total_cvg = storage.keys()
            # Creating Default Schema to update the yaml file
            share_value = "/mnt/fs-local-volume"  # This needs to changed
            device_schema = {'system': share_value}
            device_key = {'devices': device_schema}
            # SNS and dix value update
            cmn_storage_sets['durability']['sns'] = nks
            cmn_storage_sets['durability']['dix'] = dix
            # Removing the elements from the node dict
            for key_count in list(total_nodes):
                node.pop(key_count)
            for cvg in list(total_cvg):
                storage.pop(cvg)
            # Updating the node dict
            for item, host in zip(list(range(node_list)), worker_obj):
                dict_node = {}
                name = {'name': host.hostname}
                dict_node.update(name)
                dict_node.update(device_key)
                new_node = {'node{}'.format(item + 1): dict_node}
                node.update(new_node)
            # Updating the metadata and data disk
            for cvg in range(0, cvg_count):
                cvg_dict = {}
                metadata_schema_upd = {'devices': metadata_devices[cvg], 'size': size_metadata}
                data_schema = {}
                for disk in range(0, data_disk_per_cvg):
                    disk_schema_upd = {'device': data_devices[cvg][disk], 'size': size_data_disk}
                    c_data_device_schema = {'d{}'.format(disk + 1): disk_schema_upd}
                    data_schema.update(c_data_device_schema)
                c_device_schema = {'metadata': metadata_schema_upd, 'data': data_schema}
                key_cvg_devices = {'devices': c_device_schema}
                cvg_name = {'name': 'cvg-0{}'.format(cvg + 1)}
                cvg_type_schema = {'type': cvg_type}
                cvg_dict.update(cvg_name)
                cvg_dict.update(cvg_type_schema)
                cvg_dict.update(key_cvg_devices)
                cvg_key = {'cvg{}'.format(cvg + 1): cvg_dict}
                storage.update(cvg_key)

            conf['solution']['nodes'] = node
            conf['solution']['storage'] = storage
            soln.close()
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(new_filepath, 'w') as soln:
            yaml.dump(conf, soln, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        return True, new_filepath, sys_disk_pernode
