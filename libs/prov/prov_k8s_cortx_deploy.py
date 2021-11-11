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
import json

from commons import commands as common_cmd
from commons import constants as common_const
from commons import pswdmanager
from commons.helpers.pods_helper import LogicalNode
from commons.utils import system_utils, assert_utils
from config import PROV_CFG
from libs.csm.rest.csm_rest_s3user import RestS3user
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
        LOGGER.info("Checking No of CPU's")
        resp = node_obj.execute_cmd(cmd=
                                    common_cmd.CMD_NUM_CPU,
                                    read_lines=True)[0].strip()
        LOGGER.info("No of CPU : %s", resp)
        if int(resp) < self.deploy_cfg["prereq"]["cpu_cores"]:
            return False, "No of CPU are not as expected."
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
        cmd = "cd {}; {} {}| tee prereq-deploy-cortx-cloud.log". \
            format(remote_code_path, self.deploy_cfg["exe_prereq"], system_disk)
        resp = node_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.debug("\n".join(resp).replace("\\n", "\n"))

    @staticmethod
    def copy_sol_file(node_obj: LogicalNode, local_sol_path: str,
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
        cmd = "cd {}; {} | tee deployment.log".format(remote_code_path,
                                                      self.deploy_cfg["deploy_cluster"])
        resp = node_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.debug("\n".join(resp).replace("\\n", "\n"))
        return True, resp

    @staticmethod
    def validate_cluster_status(node_obj: LogicalNode, remote_code_path):
        LOGGER.info("Validate Cluster status")
        cmd = "cd {}; {} | tee cluster_status.log".format(remote_code_path,
                                                          common_cmd.CLSTR_STATUS_CMD)
        resp = node_obj.execute_cmd(cmd, read_lines=True)
        LOGGER.debug("\n".join(resp).replace("\\n", "\n"))
        if "FAILED" in resp:
            return False, resp
        return True, resp

    def pull_third_party_images(self, worker_obj_list: list):
        """
        This method pulls the third party images
        param: worker_obj_list: Worker Object list
        return : Boolean
        """
        LOGGER.info("Pull 3rd party images on all worker nodes.")
        LOGGER.debug(self.deploy_cfg['third_party_images'])
        data = self.deploy_cfg['third_party_images']
        LOGGER.debug("Data: %s", data)
        for obj in worker_obj_list:
            for key, value in data.items():
                if key in ("kafka", "zookeeper"):
                    value = "bitnami/" + key + ":" + value
                cmd = common_cmd.CMD_DOCKER_PULL.format(value)
                obj.execute_cmd(cmd=cmd)
        return True

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
        self.pull_third_party_images(worker_node_list)

        self.docker_login(master_node_list[0], docker_username, docker_password)
        self.prereq_git(master_node_list[0], git_id, git_token, git_tag)
        self.copy_sol_file(master_node_list[0], sol_file_path, self.deploy_cfg["git_remote_dir"])
        resp = self.deploy_cluster(master_node_list[0], self.deploy_cfg["git_remote_dir"])
        if resp[0]:
            LOGGER.info("Validate cluster status using status-cortx-cloud.sh")
            resp = self.validate_cluster_status(master_node_list[0],
                                                self.deploy_cfg["git_remote_dir"])
            return resp
        return resp

    def checkout_solution_file(self, token, git_tag):
        url = self.deploy_cfg["git_k8_repo_file"].format(token, git_tag)
        cmd = common_cmd.CMD_CURL.format(self.deploy_cfg["new_file_path"], url)
        system_utils.execute_cmd(cmd=cmd)
        return self.deploy_cfg["new_file_path"]

    def update_sol_yaml(self, worker_obj: list, filepath: str, cortx_image: str,
                        control_lb_ip: list, data_lb_ip: list,
                        **kwargs):
        """
        This function updates the yaml file
        :Param: worker_obj: list of worker node object
        :Param: filepath: Filename with complete path
        :Param: cortx_image: this is cortx image name
        :Param: control_lb_ip : List of control ips
        :Param: data_lb_ip : List of data ips
        :Keyword: cvg_count: cvg_count per node
        :Keyword: type_cvg: ios or cas
        :Keyword: data_disk_per_cvg: data disk required per cvg
        :Keyword: size_metadata: size of metadata disk
        :Keyword: size_data_disk: size of data disk
        :Keyword: glusterfs_size: size of glusterfs
        :Keyword: sns_data: N
        :Keyword: sns_parity: K
        :Keyword: sns_spare: S
        :Keyword: dix_data:
        :Keyword: dix_parity:
        :Keyword: dix_spare:
        :Keyword: skip_disk_count_check: disk count check
        :Keyword: third_party_image: dict of third party image
        returns the status, filepath and system reserved disk
        """
        cvg_count = kwargs.get("cvg_count", 2)
        data_disk_per_cvg = kwargs.get("data_disk_per_cvg", 0)
        cvg_type = kwargs.get("cvg_type", "ios")
        sns_data = kwargs.get("sns_data", 1)
        sns_parity = kwargs.get("sns_parity", 0)
        sns_spare = kwargs.get("sns_spare", 0)
        dix_data = kwargs.get("dix_data", 1)
        dix_parity = kwargs.get("dix_parity", 0)
        dix_spare = kwargs.get("dix_spare", 0)
        size_metadata = kwargs.get("size_metadata", '20Gi')
        size_data_disk = kwargs.get("size_data_disk", '20Gi')
        glusterfs_size = kwargs.get("glusterfs_size", '20Gi')
        skip_disk_count_check = kwargs.get("skip_disk_count_check", False)
        third_party_images_dict = kwargs.get("third_party_images",
                                             self.deploy_cfg['third_party_images'])
        data_devices = list()  # empty list for data disk
        sys_disk_pernode = {}  # empty dict
        node_list = len(worker_obj)
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
            new_device_lst_len = (device_list_len - cvg_count - 1)
            count = cvg_count
            if data_disk_per_cvg == 0:
                data_disk_per_cvg = int(len(device_list[cvg_count + 1:]) / cvg_count)

            LOGGER.debug("Data disk per cvg : %s", data_disk_per_cvg)
            # The condition to validate the config.
            if not skip_disk_count_check and valid_disk_count > \
                    (data_disk_per_cvg * cvg_count * node_list):
                return False, "The sum of data disks per cvg " \
                              "is less than N+K+S count"

            if new_device_lst_len < data_disk_per_cvg * cvg_count:
                return False, "The requested data disk is more than" \
                              " the data disk available on the system"
            # This condition validated the total available disk count
            # and split the disks per cvg.
            data_devices_f = device_list[cvg_count + 1:]
            if (data_disk_per_cvg * cvg_count) < new_device_lst_len:
                count_end = int(data_disk_per_cvg)
                data_devices.append(data_devices_f[0:count_end])
                while count:
                    count = count - 1
                    new_end = int(count_end + data_disk_per_cvg)
                    if new_end > new_device_lst_len:
                        break
                    data_devices_ad = data_devices_f[count_end:new_end]
                    count_end = int(count_end + data_disk_per_cvg)
                    data_devices.append(data_devices_ad)
            else:
                LOGGER.debug("Data devices : else : %s", data_devices_f)
                LOGGER.debug("data disk per cvg : %s", data_disk_per_cvg)
                data_devices = [data_devices_f[i:i + data_disk_per_cvg]
                                for i in range(0, len(data_devices_f), data_disk_per_cvg)]

            # Create dict for host and disk
            system_disk = device_list[0]
            schema = {node_obj.hostname: system_disk}
            sys_disk_pernode.update(schema)
        LOGGER.info("Metadata disk %s", metadata_devices)
        LOGGER.info("data disk %s", data_devices)
        # Update the solution yaml file with password
        resp_passwd = self.update_password_sol_file(filepath)
        if not resp_passwd[0]:
            return False, "Failed to update passwords in solution file"
        # # Update load balancer ips
        # resp_lb_ip = self.update_lb_ip(filepath, control_ip=control_lb_ip, data_ip=data_lb_ip)
        # if not resp_lb_ip[0]:
        #     return False, "Failed to update lb ip in solution file"

        # Update the solution yaml file with images
        resp_image = self.update_image_section_sol_file(filepath, cortx_image,
                                                        third_party_images_dict)
        if not resp_image[0]:
            return False, "Failed to update images in solution file"

        # Update the solution yaml file with cvg
        resp_cvg = self.update_cvg_sol_file(filepath, metadata_devices,
                                            data_devices,
                                            cvg_count,
                                            cvg_type,
                                            data_disk_per_cvg,
                                            sns_data,
                                            sns_parity,
                                            sns_spare,
                                            dix_data,
                                            dix_parity,
                                            dix_spare,
                                            size_metadata,
                                            size_data_disk,
                                            glusterfs_size)
        if not resp_cvg[0]:
            return False, "Fail to update the cvg details in solution file"

        # Update the solution yaml file with node
        resp_node = self.update_nodes_sol_file(filepath, worker_obj)
        if not resp_node[0]:
            return False, "Failed to update nodes details in solution file"

        return True, filepath, sys_disk_pernode

    def update_nodes_sol_file(self, filepath, worker_obj):
        """
        Method to update the nodes section in solution.yaml
        Param: filepath: Filename with complete path
        Param: worker_obj: list of node object
        :returns the filepath and status True
        """
        node_list = len(worker_obj)
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            node = parent_key['nodes']  # Child Key
            total_nodes = node.keys()
            # Removing the elements from the node dict
            for key_count in list(total_nodes):
                node.pop(key_count)
            # Updating the node dict
            for item, host in zip(list(range(node_list)), worker_obj):
                dict_node = {}
                name = {'name': host.hostname}
                dict_node.update(name)
                new_node = {'node{}'.format(item + 1): dict_node}
                node.update(new_node)
            conf['solution']['nodes'] = node
            soln.close()
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(filepath, 'w') as soln:
            yaml.dump(conf, soln, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        return True, filepath

    def update_cvg_sol_file(self, filepath,
                            metadata_devices: list,
                            data_devices: list,
                            cvg_count: int,
                            cvg_type: str,
                            data_disk_per_cvg: int,
                            sns_data: int,
                            sns_parity: int,
                            sns_spare: int,
                            dix_data: int,
                            dix_parity: int,
                            dix_spare: int,
                            size_metadata: str,
                            size_data_disk: str,
                            glusterfs_size: str):

        """
        Method to update the cvg
        :Param: metadata_devices: list of meta devices
        :Param: data_devices: list of data devices
        :Param: filepath: file with complete path
        :Param: cvg_count: cvg_count per node
        :Param: type_cvg: ios or cas
        :Param: data_disk_per_cvg: data disk required per cvg
        :Param: sns_data: N
        :Param: sns_parity: K
        :Param: sns_spare: S
        :Param: dix_data:
        :Param: dix_parity:
        :Param: dix_spare:
        :Param: size_metadata: size of metadata disk
        :Param: size_data_disk: size of data disk
        :Param: glusterfs_size: size of glusterfs
        :returns the status ,filepath
        """
        nks = "{}+{}+{}".format(sns_data, sns_parity, sns_spare)  # Value of N+K+S for sns
        dix = "{}+{}+{}".format(dix_data, dix_parity, dix_spare)  # Value of N+K+S for dix
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            common = parent_key['common']  # Parent key
            storage = parent_key['storage']  # child of child key
            cmn_storage_sets = common['storage_sets']  # child of child key
            common['glusterfs']['size'] = glusterfs_size
            total_cvg = storage.keys()
            # SNS and dix value update
            cmn_storage_sets['durability']['sns'] = nks
            cmn_storage_sets['durability']['dix'] = dix
            for cvg_item in list(total_cvg):
                storage.pop(cvg_item)
            for cvg in range(0, cvg_count):
                cvg_dict = {}
                metadata_schema_upd = {'device': metadata_devices[cvg], 'size': size_metadata}
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
            conf['solution']['storage'] = storage
            LOGGER.debug("Storage Details : %s", storage)
            soln.close()
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(filepath, 'w') as soln:
            yaml.dump(conf, soln, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        return True, filepath

    def update_image_section_sol_file(self, filepath, cortx_image, third_party_images_dict):
        """
        Method use to update the Images section in solution.yaml
        Param: filepath: filename with complete path
        cortx_image: this is cortx image name
        third_party_image: dict of third party image
        :returns the status, filepath
        """
        cortx_im = dict()
        image_default_dict = {}
        image_default_dict.update(self.deploy_cfg['third_party_images'])

        for image_key in self.deploy_cfg['cortx_images_key']:
            cortx_im[image_key] = cortx_image
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            image = parent_key['images']  # Parent key
            conf['solution']['images'] = image
            image.update(cortx_im)
            for key, value in list(third_party_images_dict.items()):
                if key in list(self.deploy_cfg['third_party_images'].keys()):
                    image.update({key: value})
                    image_default_dict.pop(key)
            image.update(image_default_dict)
            soln.close()
        LOGGER.debug("Images used for deployment : %s", image)
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(filepath, 'w') as soln:
            yaml.dump(conf, soln, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        return True, filepath

    def update_password_sol_file(self, filepath):
        """
        This Method update the password in solution.yaml file
        Param: filepath: filename with complete path
        :returns the status, filepath
        """
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            content = parent_key['secrets']['content']
            common = parent_key['common']
            common['storage_provisioner_path'] = self.deploy_cfg['local_path_prov']
            common['s3']['max_start_timeout'] = self.deploy_cfg['s3_max_start_timeout']
            passwd_dict = {}
            for key, value in self.deploy_cfg['password'].items():
                passwd_dict[key] = pswdmanager.decrypt(value)
            content.update(passwd_dict)
            soln.close()
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(filepath, 'w') as soln:
            yaml.dump(conf, soln, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        return True, filepath

    def update_lb_ip(self, filepath, data_ip: list, control_ip: list):
        """
        This Method is used to update the lb IP's
        :Param: filepath: solution.yaml file path
        :Param: data_ip: list of ip of data lb pod
        :Param: control_ip: ip of data lb pod
        """
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            loadbal = parent_key['common']['loadbal']
            control_lb_dict = loadbal['control']
            cip_dict = {}
            for num, c_ip in zip(range(len(control_ip)), control_ip):
                control_schema = {"ip{}".format(num + 1): c_ip}
                LOGGER.debug("Control %s", control_schema)
                cip_dict.update(control_schema)
            control_lb_dict.update({"externalips": cip_dict})

            data_lb_dict = loadbal['data']
            ip_dict = {}
            for num, d_ip in zip(range(len(data_ip)), data_ip):
                ip_schema = {"ip{}".format(num + 1): d_ip}
                LOGGER.debug("data %s", ip_schema)
                ip_dict.update(ip_schema)
            data_lb_dict.update({"externalips": ip_dict})
            soln.close()
            LOGGER.debug("Load balancer : %s", loadbal)
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(filepath, 'w') as soln:
            yaml.dump(conf, soln, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        return True, filepath

    @staticmethod
    def deploy_cortx_k8s_cluster(master_node_list: list, worker_node_list: list,
                                 deploy_target: str = "CORTX-CLUSTER") -> tuple:
        """
        Setup k8s cluster using RE jenkins job
        param: master_node_list : List of all master nodes(Logical Node object)
        param: worker_node_list : List of all worker nodes(Logical Node object)
        param: deploy_target : Only Third Party Components or Cortx Cluster
        return : True/False and success/failure message
        """
        k8s_deploy_cfg = PROV_CFG["k8s_cluster_deploy"]
        LOGGER.info("Create inputs for RE jenkins job")
        hosts_input_str = []
        jen_parameter = {}
        if len(master_node_list) > 0:
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
        jen_parameter["DEPLOY_TARGET"] = deploy_target

        output = Provisioner.build_job(
            k8s_deploy_cfg["cortx_job_name"], jen_parameter, k8s_deploy_cfg["auth_token"],
            k8s_deploy_cfg["jenkins_url"])
        LOGGER.info("Jenkins Build URL: {}".format(output['url']))
        if output['result'] == "SUCCESS":
            LOGGER.info("k8s Cluster Deployment successful")
            return True, output['result']
        else:
            LOGGER.error(f"k8s Cluster Deployment {output['result']},please check URL")
            return False, output['result']

    @staticmethod
    def get_hctl_status(node_obj, pod_name: str) -> tuple:
        """
        Get hctl status for cortx.
        param: master_node: Master node(Logical Node object)
        param: pod_name: Running Data Pod
        return: True/False and success/failure message
        """
        LOGGER.info("Get Cluster status")
        cluster_status = node_obj.execute_cmd(cmd=common_cmd.K8S_HCTL_STATUS.format(pod_name)).decode('UTF-8')
        cluster_status = json.loads(cluster_status)
        if cluster_status is not None:
            nodes_data = cluster_status["nodes"]
            for node_data in nodes_data:
                services = node_data["svcs"]
                for svc in services:
                    if svc["status"] != "started":
                        return False, "Service {} not started.".format(svc["name"])
            return True, "Cluster is up and running."
        return False, "Cluster status is not retrieved."

    def destroy_setup(self, master_node_obj, worker_node_obj):
        """
        Method used to run destroy script
        """
        cmd1 = "cd {} && {}".format(self.deploy_cfg["git_remote_dir"],
                                    self.deploy_cfg["destroy_cluster"])
        cmd2 = "umount {}".format(self.deploy_cfg["local_path_prov"])
        cmd3 = "rm -rf /etc/3rd-party/openldap /var/data/3rd-party/"
        resp = master_node_obj.execute_cmd(cmd=cmd1)
        LOGGER.debug("resp : %s", resp)
        for worker in worker_node_obj:
            resp = worker.execute_cmd(cmd=cmd2, read_lines=True)
            LOGGER.debug("resp : %s", resp)
            resp = worker.execute_cmd(cmd=cmd3, read_lines=True)
            LOGGER.debug("resp : %s", resp)
        return resp

    # use check_cluster_status from ha_common_libs once hctl status issue is resolved,
    @staticmethod
    def s3_service_status(master_node_obj):
        """
        This method is used to fetch the s3 services status
        param: master_node_obj : Master Node object
        """
        resp = master_node_obj.get_pod_name(pod_prefix=common_const.POD_NAME_PREFIX)
        pod_name = resp[1]
        res = master_node_obj.send_k8s_cmd(
            operation="exec", pod=pod_name, namespace=common_const.NAMESPACE,
            command_suffix=f"-c {common_const.HAX_CONTAINER_NAME} "
                           f"-- {'consul kv get -recurse | grep s3 | grep name'}",
            decode=True)
        resp = res.split('\n')
        LOGGER.info("Response for cortx cluster status: %s", resp)
        for line in resp:
            if "online" not in line:
                LOGGER.debug("Line: %s",line)
                return False, resp
        return True, resp

    @staticmethod
    def configure_metallb(node_obj: LogicalNode, data_ip: list, control_ip: list):
        """
        Configure MetalLB on the master node
        param: node_obj : Master node object
        param: data_ip : List of data IPs.
        param: control_ip : List of control IPs.
        return : Boolean
        """
        LOGGER.info("Configuring MetaLB: ")
        metallb_cfg = PROV_CFG['config_metallb']
        LOGGER.info("Enable strict ARP mode")
        resp = node_obj.execute_cmd(cmd=metallb_cfg['check_ARP'], read_lines=True)
        LOGGER.debug("resp: %s", resp)
        resp = node_obj.execute_cmd(cmd=metallb_cfg['enable_strict_ARP'], read_lines=True)
        LOGGER.debug("resp: %s", resp)

        LOGGER.info("Apply manifest")
        resp = node_obj.execute_cmd(cmd=metallb_cfg['apply_manifest_namespace'], read_lines=True)
        LOGGER.debug("resp: %s", resp)
        resp = node_obj.execute_cmd(cmd=metallb_cfg['apply_manifest_metalb'], read_lines=True)
        LOGGER.debug("resp: %s", resp)

        LOGGER.info("Check metallb-system namespace")
        resp = node_obj.execute_cmd(cmd=metallb_cfg['check_namespace'], read_lines=True)
        LOGGER.debug("resp: %s", resp)

        LOGGER.info("Update config file with the provided IPs")
        ip_list = data_ip + control_ip
        filepath = metallb_cfg['config_path']
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            new_dict = conf['data']
            ori_value = conf['data']['config']
            temp1 = ori_value.split('addresses:')[1]
            ips = ' \n\t'.join(f'- {each}-{each}' for each in ip_list)
            temp2 = '\n\t' + ips
            new_value = ori_value.replace(temp1, temp2)
            schema = {'config': f'| {new_value}'}
            new_dict.update(schema)
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(metallb_cfg['new_config_file'], 'w') as soln:
            yaml.dump(conf, soln, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)

        LOGGER.info("Copy metalLB config file to master node")
        resp = node_obj.copy_file_to_remote(metallb_cfg['new_config_file'],
                                            metallb_cfg['remote_path'])
        if not resp:
            return resp

        LOGGER.info("Apply metalLB config")
        resp = node_obj.execute_cmd(metallb_cfg['apply_config'], read_lines=True)
        LOGGER.debug("resp: %s", resp)

        return True

    @staticmethod
    def post_deployment_steps_lc():
        """
        Perform CSM login, S3 account creation and AWS configuration on client
        returns status boolean
        """
        LOGGER.info("Post Deployment Steps")
        csm_s3 = RestS3user()

        LOGGER.info("Create S3 account")
        csm_s3.create_custom_s3_payload("valid")
        resp = csm_s3.create_s3_account()
        LOGGER.info("Response for account creation: %s", resp.json())
        details = resp.json()
        access_key = details['access_key']
        secret_key = details["secret_key"]
        try:
            LOGGER.info("Configure AWS keys on Client")
            system_utils.execute_cmd(
                common_cmd.CMD_AWS_CONF_KEYS.format(access_key, secret_key))
        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvDeployK8sCortxLib.post_deployment_steps_lc.__name__)
            if isinstance(error.args[0], list):
                LOGGER.error("\n".join(error.args[0]).replace("\\n", "\n"))
            else:
                LOGGER.error(error.args[0])
            return False, error

        return True, "Post Deployment Steps Successful!!"
