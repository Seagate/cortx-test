# pylint: disable=too-many-lines
# !/usr/bin/python
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
Provisioner utility methods for Deployment of k8s based Cortx Deployment
"""
import csv
import json
import logging
import math
import os
import re
import shutil
import signal
import string
import time
from threading import Thread
from typing import List
from string import Template
import requests.exceptions
import yaml

from commons import commands as common_cmd
from commons import constants as common_const
from commons import pswdmanager
from commons.helpers.pods_helper import LogicalNode
from commons.params import LOG_DIR
from commons.params import LATEST_LOG_FOLDER
from commons.params import TEST_DATA_FOLDER
from commons.utils import system_utils
from commons.utils import assert_utils
from commons.utils import ext_lbconfig_utils
from config import PROV_CFG
from config import S3_CFG
from config import PROV_TEST_CFG
from config import CMN_CFG
from libs.csm.rest.csm_rest_s3user import RestS3user
from libs.prov.provisioner import Provisioner
from libs.s3 import S3H_OBJ
from libs.s3.s3_test_lib import S3TestLib
from libs.ha.ha_common_libs_k8s import HAK8s
from scripts.s3_bench import s3bench

LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class ProvDeployK8sCortxLib:
    """
    This class contains utility methods for all the operations related
    to k8s based Cortx Deployment .
    """

    def __init__(self):
        self.deploy_cfg = PROV_CFG["k8s_cortx_deploy"]
        self.git_script_tag = os.getenv("GIT_SCRIPT_TAG")
        self.s3_engine = int(os.getenv("S3_ENGINE", CMN_CFG["s3_engine"]))
        self.cortx_image = os.getenv("CORTX_CONTROL_IMAGE")
        self.cortx_server_image = os.getenv("CORTX_SERVER_IMAGE", None)
        self.cortx_data_image = os.getenv("CORTX_DATA_IMAGE", None)
        self.service_type = os.getenv("SERVICE_TYPE", self.deploy_cfg["service_type"])
        self.deployment_type = os.getenv("DEPLOYMENT_TYPE", self.deploy_cfg["deployment_type"])
        self.lb_count = int(os.getenv("LB_COUNT", self.deploy_cfg["lb_count"]))
        self.nodeport_https = int(os.getenv("HTTPS_PORT", self.deploy_cfg["https_port"]))
        self.nodeport_http = int(os.getenv("HTTP_PORT", self.deploy_cfg["http_port"]))
        self.control_nodeport_https = int(os.getenv("CONTROL_HTTPS_PORT",
                                                    self.deploy_cfg["control_port_https"]))
        self.client_instance = int(os.getenv("CLIENT_INSTANCE", self.deploy_cfg['client_instance']))
        self.test_dir_path = os.path.join(TEST_DATA_FOLDER, "testDeployment")
        self.data_only_list = ["data-only", "standard"]
        self.server_only_list = ["server-only", "standard"]
        self.exclusive_pod_list = ["data-only", "server-pod"]
        self.patterns = "invalid release"
        self.local_sol_path = common_const.LOCAL_SOLUTION_PATH

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
        jen_parameter["PODS_ON_PRIMARY"] = taint_master

        output = Provisioner.build_job(
            k8s_deploy_cfg["job_name"], jen_parameter, k8s_deploy_cfg["auth_token"],
            k8s_deploy_cfg["jenkins_url"])
        LOGGER.info("Jenkins Build URL: %s", output['url'])
        if output['result'] == "SUCCESS":
            LOGGER.info("k8s Cluster Deployment successful")
            return True, output['result']
        LOGGER.error("k8s Cluster Deployment %s ,please check URL", output['result'])
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

    def prereq_git(self, node_obj: LogicalNode, git_tag: str):
        """
        Checkout cortx-k8s code on the  node. Delete if any previous exists.
        param: node_obj : Node object to checkout code - node.
        param: git tag: tag of service repo
        """
        LOGGER.info("Delete cortx-k8s repo on node")
        url = self.deploy_cfg["git_k8_repo"]
        clone_dir = self.deploy_cfg['clone_dir']
        resp = node_obj.execute_cmd(common_cmd.CMD_REMOVE_DIR.format(clone_dir))
        LOGGER.debug("resp: %s", resp)

        LOGGER.info("Git clone cortx-k8s repo")
        resp = node_obj.execute_cmd(common_cmd.CMD_GIT_CLONE_D.format(url, clone_dir))
        LOGGER.debug("resp: %s", resp)

        LOGGER.info("Git checkout tag %s", git_tag)
        cmd = f"cd {clone_dir} && " + common_cmd.CMD_GIT_CHECKOUT.format(git_tag)
        resp = node_obj.execute_cmd(cmd)
        LOGGER.debug("resp: %s", resp)

    def execute_prereq_cortx(self, node_obj: LogicalNode, remote_code_path: str, system_disk: str):
        """
        Execute prerq script on worker node,
        param: node_obj: Worker node object
        param: system_disk: parameter to prereq script
        """
        LOGGER.info("Execute prereq script")
        pre_req_log = PROV_CFG['k8s_cortx_deploy']["pre_req_log"]
        pre_req_cmd = Template(common_cmd.PRE_REQ_CMD + "> $log").substitute(
            dir=remote_code_path, disk=system_disk, log=pre_req_log)
        list_mnt_dir = Template(common_cmd.LS_LH_CMD).substitute(dir=
                                                                 self.deploy_cfg['local_path_prov'])
        list_etc_3rd_party = Template(common_cmd.LS_LH_CMD).substitute(
            dir=self.deploy_cfg['3rd_party_dir'])
        list_data_3rd_party = Template(common_cmd.LS_LH_CMD).substitute(
            dir=self.deploy_cfg['3rd_party_data_dir'])
        resp = node_obj.execute_cmd(pre_req_cmd, read_lines=True, recv_ready=True,
                                    timeout=self.deploy_cfg['timeout']['pre-req'])
        LOGGER.debug("\n".join(resp).replace("\\n", "\n"))
        if node_obj.path_exists(self.deploy_cfg['local_path_prov']):
            resp1 = node_obj.execute_cmd(list_mnt_dir, read_lines=True)
            if node_obj.path_exists(self.deploy_cfg["mnt_path"]):
                resp = node_obj.execute_cmd(
                    common_cmd.CMD_REMOVE_DIR.format(self.deploy_cfg["mnt_path"]))
                LOGGER.debug(resp)
            LOGGER.info("\n %s", resp1)
        if node_obj.path_exists(self.deploy_cfg['3rd_party_dir']):
            openldap_dir_residue = node_obj.execute_cmd(list_etc_3rd_party, read_lines=True)
            LOGGER.info("\n %s", openldap_dir_residue)
        if node_obj.path_exists(self.deploy_cfg['3rd_party_data_dir']):
            thirdparty_residue = node_obj.execute_cmd(list_data_3rd_party, read_lines=True)
            LOGGER.info("\n %s", thirdparty_residue)

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
            return True, f"Files copied at {remote_path}"
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
        cmd = Template(common_cmd.DEPLOY_CLUSTER_CMD).substitute(path=remote_code_path,
                                                                 log=self.deploy_cfg['log_file'])
        try:
            resp = node_obj.execute_cmd(cmd, read_lines=True, recv_ready=True,
                                        timeout=self.deploy_cfg['timeout']['deploy'])
            LOGGER.debug("\n".join(resp).replace("\\n", "\n"))
            return True, resp
        except TimeoutError as error:
            LOGGER.error(error, self.deploy_cfg['timeout']['deploy'])
            node_obj.kill_remote_process(cmd)
            return False, str(error)
        except IOError as error:
            LOGGER.exception("The exception occurred is %s", error)
            return False, str(error)

    @staticmethod
    def validate_cluster_status(node_obj: LogicalNode, remote_code_path):
        """
        Validate cluster status
        param: node_obj : Logical node object of Master node
        param: remote_code_path: Remote code path of cortx-k8s repo on master node.
        return : Boolean
        """
        LOGGER.info("Validate Cluster status")
        status_file = PROV_CFG['k8s_cortx_deploy']["status_log_file"]
        cmd = common_cmd.CLSTR_STATUS_CMD.format(remote_code_path) + \
              Template(" > $log").substitute(log=status_file)
        resp = node_obj.execute_cmd(cmd, read_lines=True, recv_ready=True,
                                    timeout=PROV_CFG['k8s_cortx_deploy']['timeout']['status'])
        LOGGER.debug(resp)
        local_path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER, status_file)
        remote_path = os.path.join(PROV_CFG['k8s_cortx_deploy']["k8s_dir"], status_file)
        LOGGER.debug("COPY status file to local")
        node_obj.copy_file_to_local(remote_path, local_path)
        with open(local_path, 'r') as file:
            lines = file.readlines()
            for line in lines:
                LOGGER.debug("line is %s", line)
                if "FAILED" in line:
                    return False, line
        return True, lines

    def pull_cortx_image(self, worker_obj: LogicalNode):
        """
        This method pulls  cortx image
        param: worker_obj_list: Worker Object list
        return : Boolean
        """
        LOGGER.info("Pull Cortx image on worker node %s", worker_obj.hostname)
        worker_obj.execute_cmd(common_cmd.CMD_DOCKER_PULL.format(self.cortx_image))
        if self.cortx_server_image:
            worker_obj.execute_cmd(common_cmd.CMD_DOCKER_PULL.format(self.cortx_server_image))
        if self.cortx_data_image:
            worker_obj.execute_cmd(common_cmd.CMD_DOCKER_PULL.format(self.cortx_data_image))
        return True

    def deploy_cortx_cluster(self, sol_file_path: str, master_node_list: list,
                             worker_node_list: list, system_disk_dict: dict,
                             **kwargs) -> tuple:
        """
        Perform cortx cluster deployment
        param: solution_file_path: Local Solution file path
        param: master_node_list : List of all master nodes(Logical Node object)
        param: worker_node_list : List of all worker nodes(Logical Node object)
        param: docker_username: Docker Username
        param: docker_password: Docker password
        param: git tag: tag of service repo
        namespace: defines the custom namespace for deployment of cortx stack on k8s
        return : True/False and resp
        """
        git_tag = kwargs.get("git_tag")
        namespace = kwargs.get("namespace", PROV_CFG["k8s_cortx_deploy"]["namespace"])
        if len(master_node_list) == 0:
            return False, "Minimum one master node needed for deployment"
        if len(worker_node_list) == 0:
            return False, "Minimum one worker node needed for deployment"

        def _operation_on_worker_node():
            for node in worker_node_list:
                pre_req_resp = self.prereq_vm(node)
                assert_utils.assert_true(pre_req_resp[0], pre_req_resp[1])
                system_disk = system_disk_dict[node.hostname]
                self.prereq_git(node, git_tag)
                self.copy_sol_file(node, sol_file_path, self.deploy_cfg["k8s_dir"])
                # system disk will be used mount /mnt/fs-local-volume on worker node
                self.execute_prereq_cortx(node, self.deploy_cfg["k8s_dir"], system_disk)

            thread_list = []
            for each in worker_node_list:
                worker_thread = Thread(target=self.pull_cortx_image, args=(each,))
                worker_thread.start()
                thread_list.append(worker_thread)
            for each in thread_list:
                each.join()

        def _post_deploy_check(resp):
            if not resp[1]:
                LOGGER.info("Setting the current namespace")
                resp_ns = master_node_list[0].execute_cmd(
                    cmd=common_cmd.KUBECTL_SET_CONTEXT.format(namespace),
                    read_lines=True)
                LOGGER.debug("response is %s,", resp_ns)
                local_path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER,
                                          self.deploy_cfg['log_file'])
                remote_path = os.path.join(self.deploy_cfg["k8s_dir"],
                                           self.deploy_cfg['log_file'])
                LOGGER.debug("remote path is %s", remote_path)
                master_node_list[0].copy_file_to_local(remote_path, local_path)
                pod_status = master_node_list[0].execute_cmd(cmd=common_cmd.K8S_GET_PODS,
                                                             read_lines=True)
                LOGGER.debug("\n=== POD STATUS ===\n")
                LOGGER.debug(pod_status)
                if not resp[0]:
                    with open(local_path, 'r') as file:
                        lines = file.read()
                        LOGGER.debug(lines)

        _operation_on_worker_node()
        self.prereq_git(master_node_list[0], git_tag)
        self.copy_sol_file(master_node_list[0], sol_file_path, self.deploy_cfg["k8s_dir"])
        pre_check_resp = self.pre_check(master_node_list[0])
        LOGGER.debug("pre-check result %s", pre_check_resp)
        deploy_resp = self.deploy_cluster(master_node_list[0], self.deploy_cfg["k8s_dir"])
        LOGGER.debug("Deploy script response %s", deploy_resp)
        _post_deploy_check(deploy_resp)
        return deploy_resp

    def checkout_solution_file(self, git_tag):
        """
        Method to checkout solution.yaml file
        param: git tag: tag of service repo
        """
        url = Template(self.deploy_cfg["git_k8_repo_file"]).substitute(
            tag=git_tag, file=self.deploy_cfg["new_file_path"])
        cmd = Template(common_cmd.CMD_CURL).substitute(file=self.deploy_cfg["new_file_path"],
                                                       url=url)
        system_utils.execute_cmd(cmd=cmd)
        shutil.copyfile(self.deploy_cfg["new_file_path"], self.deploy_cfg['solution_file'])
        return self.deploy_cfg["solution_file"]

    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-return-statements
    def update_sol_yaml(self, worker_obj: list, filepath: str, cortx_image: str,
                        **kwargs):
        """
        This function updates the yaml file
        :Param: worker_obj: list of worker node object
        :Param: filepath: Filename with complete path
        :Param: cortx_image: this is cortx image name
        :Keyword: cvg_count: cvg_count per node
        :Keyword: type_cvg: ios or cas
        :Keyword: data_disk_per_cvg: data disk required per cvg
        :Keyword: size_metadata: size of metadata disk
        :Keyword: size_data_disk: size of data disk
        :Keyword: sns_data: N
        :Keyword: sns_parity: K
        :Keyword: sns_spare: S
        :Keyword: dix_data:
        :Keyword: dix_parity:
        :Keyword: dix_spare:
        :Keyword: skip_disk_count_check: disk count check
        :Keyword: third_party_image: dict of third party image
        :Keyword: log_path: to provide custom log path
        :Keyword: cortx_server_image: to provide cortx server image
        :Keyword: service_type: to provide service type as LoadBalancer/NodePort
        :Keyword: namespace: to provide custom namespace
        returns the status, filepath and system reserved disk
        """
        cvg_count = kwargs.get("cvg_count", 2)
        cvg_type = kwargs.get("cvg_type", "ios")
        data_disk_per_cvg = kwargs.get("data_disk_per_cvg", 0)
        sns_data = kwargs.get("sns_data", 1)
        sns_parity = kwargs.get("sns_parity", 0)
        sns_spare = kwargs.get("sns_spare", 0)
        dix_data = kwargs.get("dix_data", 1)
        dix_parity = kwargs.get("dix_parity", 0)
        dix_spare = kwargs.get("dix_spare", 0)
        size_metadata = kwargs.get("size_metadata", '20Gi')
        size_data_disk = kwargs.get("size_data_disk", '20Gi')
        skip_disk_count_check = kwargs.get("skip_disk_count_check", False)
        third_party_images_dict = kwargs.get("third_party_images",
                                             self.deploy_cfg['third_party_images'])
        cortx_server_image = kwargs.get("cortx_server_image", None)
        cortx_data_image = kwargs.get("cortx_data_image", None)
        log_path = kwargs.get("log_path", self.deploy_cfg['log_path'])
        service_type = kwargs.get("service_type", self.deploy_cfg['service_type'])
        namespace = kwargs.get("namespace", self.deploy_cfg['namespace'])
        nodeport_http = kwargs.get("http_port", self.deploy_cfg['http_port'])
        nodeport_https = kwargs.get("https_port", self.deploy_cfg['https_port'])
        control_nodeport_https = kwargs.get("control_https_port",
                                            self.deploy_cfg['control_port_https'])
        deployment_type = kwargs.get("deployment_type", self.deployment_type)
        client_instance = kwargs.get("client_instance", self.client_instance)

        LOGGER.debug("Service type & Ports are %s\n%s\n%s\n%s", service_type,
                     nodeport_http, nodeport_https, control_nodeport_https)
        LOGGER.debug("Client instances are %s", self.client_instance)
        node_list = len(worker_obj)
        valid_disk_count = sns_spare + sns_data + sns_parity
        sys_disk_pernode = {}  # empty dict
        data_devices = []  # empty list for data disk
        metadata_devices = []
        for node_count, node_obj in enumerate(worker_obj, start=1):
            LOGGER.info(node_count)
            device_list = node_obj.execute_cmd(cmd=common_cmd.CMD_LIST_DEVICES,
                                               read_lines=True)[0].split(",")
            device_list[-1] = device_list[-1].replace("\n", "")
            metadata_devices = device_list[1:cvg_count + 1]
            LOGGER.info(metadata_devices)
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
                    (cvg_count * node_list):
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
        # Update the solution yaml file with service_type,deployment type, ports,namespace
        resp_passwd = self.update_miscellaneous_param(filepath, log_path,
                                                      nodeport_http=self.nodeport_http,
                                                      nodeport_https=self.nodeport_https,
                                                      control_nodeport_https=
                                                      self.control_nodeport_https,
                                                      service_type=self.service_type,
                                                      deployment_type=deployment_type,
                                                      namespace=namespace,
                                                      lb_count=self.lb_count,
                                                      client_instance=client_instance)
        if not resp_passwd[0]:
            return False, "Failed to update service type,deployment type, ports in solution file"
        # Update resources for third_party
        resource_resp = self.update_res_limit_third_party(filepath)
        if not resource_resp:
            return False, "Failed to update the resources for thirdparty"
        # Update resources for cortx component
        cortx_resource_resp = self.update_res_limit_cortx(filepath)
        if not cortx_resource_resp:
            return False, "Failed to update the resources for cortx components"
        # Update the solution yaml file with images
        resp_image = self.update_image_section_sol_file(filepath, third_party_images_dict,
                                                        cortx_image=cortx_image,
                                                        cortx_server_image=cortx_server_image,
                                                        cortx_data_image=cortx_data_image)
        if not resp_image[0]:
            return False, "Failed to update images in solution file"

        # Update the solution yaml file with cvg
        resp_cvg = self.update_cvg_sol_file(filepath, metadata_devices,
                                            data_devices, data_disk_per_cvg,
                                            cvg_count=cvg_count,
                                            cvg_type=cvg_type,
                                            sns_data=sns_data,
                                            sns_parity=sns_parity,
                                            sns_spare=sns_spare,
                                            dix_data=dix_data,
                                            dix_parity=dix_parity,
                                            dix_spare=dix_spare,
                                            size_metadata=size_metadata,
                                            size_data_disk=size_data_disk)
        if not resp_cvg[0]:
            return False, "Fail to update the cvg details in solution file"

        # Update the solution yaml file with node
        resp_node = self.update_nodes_sol_file(filepath, worker_obj)
        if not resp_node[0]:
            return False, "Failed to update nodes details in solution file"
        return True, filepath, sys_disk_pernode

    @staticmethod
    def update_nodes_sol_file(filepath, worker_obj):
        """
        Method to update the nodes section in solution.yaml
        Param: filepath: Filename with complete path
        Param: worker_obj: list of node object
        :returns the filepath and status True
        """
        node_list = len(worker_obj)
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            node = conf['solution']['nodes']
            total_nodes = node.keys()
            # Removing the elements from the node dict
            for key_count in list(total_nodes):
                node.pop(key_count)
            # Updating the node dict
            for item, host in zip(list(range(node_list)), worker_obj):
                dict_node = {}
                name = {'name': host.hostname}
                dict_node.update(name)
                new_node = {Template('node$num').substitute(num=item + 1): dict_node}
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

    # pylint: disable-msg=too-many-locals
    @staticmethod
    def update_cvg_sol_file(filepath,
                            metadata_devices: list,
                            data_devices: list,
                            data_disk_per_cvg: int,
                            **kwargs):

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
        :returns the status ,filepath
        """
        cvg_type = kwargs.get("cvg_type", )
        cvg_count = kwargs.get("cvg_count")
        sns_data = kwargs.get("sns_data")
        sns_parity = kwargs.get("sns_parity")
        sns_spare = kwargs.get("sns_spare")
        dix_data = kwargs.get("dix_data")
        dix_parity = kwargs.get("dix_parity")
        dix_spare = kwargs.get("dix_spare")
        size_metadata = kwargs.get("size_metadata")
        size_data_disk = kwargs.get("size_data_disk")
        nks = Template("$data+$parity+$spare").substitute(data=sns_data,
                                                          parity=sns_parity,
                                                          spare=sns_spare)  # Value of N+K+S for sns
        dix = Template("$data+$parity+$spare").substitute(data=dix_data,
                                                          parity=dix_parity,
                                                          spare=dix_spare)  # Value of N+K+S for dix
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            storage = parent_key['storage']  # child of child key
            cmn_storage_sets = parent_key['common']['storage_sets']  # child of child key
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
                    disk_schema_upd = \
                        {'device': data_devices[cvg][disk], 'size': size_data_disk}
                    c_data_device_schema = {'d{}'.format(disk + 1): disk_schema_upd}
                    data_schema.update(c_data_device_schema)
                c_device_schema = {'metadata': metadata_schema_upd, 'data': data_schema}
                key_cvg_devices = {'devices': c_device_schema}
                cvg_name = {'name': Template('cvg-0$num').substitute(num=cvg + 1)}
                cvg_type_schema = {'type': cvg_type}
                cvg_dict.update(cvg_name)
                cvg_dict.update(cvg_type_schema)
                cvg_dict.update(key_cvg_devices)
                cvg_key = {Template('cvg$num').substitute(num=cvg + 1): cvg_dict}
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

    def update_image_section_sol_file(self, filepath, third_party_images_dict,
                                      **kwargs):
        """
        Method use to update the Images section in solution.yaml
        Param: filepath: filename with complete path
        cortx_image: this is cortx image name
        third_party_image: dict of third party image
        cortx_server_image: cortx_server image name
        :returns the status, filepath
        """
        cortx_image = kwargs.get("cortx_image")
        cortx_server_image = kwargs.get("cortx_server_image")
        cortx_data_image = kwargs.get("cortx_data_image")
        cortx_im = dict()
        image_default_dict = {}

        for image_key in self.deploy_cfg['cortx_images_key']:
            if image_key == "cortxcontrol":
                cortx_im[image_key] = cortx_image
            elif self.cortx_data_image and image_key == "cortxdata":
                cortx_im[image_key] = cortx_data_image
            elif self.cortx_server_image and image_key == "cortxserver":
                cortx_im[image_key] = cortx_server_image
            elif image_key == "cortxha":
                cortx_im[image_key] = cortx_image
            elif self.cortx_data_image and image_key == "cortxclient":
                cortx_im[image_key] = cortx_data_image

        def _update_file(cortx_im):
            image_default_dict.update(self.deploy_cfg['third_party_images'])
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

        _update_file(cortx_im)
        return True, filepath

    # pylint: disable-msg=too-many-locals
    def update_miscellaneous_param(self, filepath, log_path,
                                   **kwargs):
        """
        This Method update the miscellaneous params in solution.yaml file
        Param: filepath: filename with complete path
        Param: log_path: to change the log path inside pods
        Param: nodeport_http: http Port for node port service for s3
        Param: nodeport_https: https Port for node port service for s3
        Param: control_nodeport_https: https Port for node port service for control
        :returns the status, filepath
        """
        service_type = kwargs.get('service_type', self.deploy_cfg['service_type'])
        nodeport_http = kwargs.get('nodeport_http', self.deploy_cfg['http_port'])
        nodeport_https = kwargs.get('nodeport_https', self.deploy_cfg['https_port'])
        control_nodeport_https = kwargs.get('control_nodeport_https',
                                            self.deploy_cfg['control_port_https'])
        lb_count = int(kwargs.get('lb_count', self.deploy_cfg['lb_count']))
        deployment_type = kwargs.get('deployment_type', self.deploy_cfg['deployment_type'])
        namespace = kwargs.get('namespace', self.deploy_cfg['namespace'])
        client_instance = kwargs.get('client_instance', self.deploy_cfg['client_instance'])
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            if deployment_type:
                parent_key['deployment_type'] = deployment_type
            parent_key['namespace'] = namespace
            common = parent_key['common']
            content = parent_key['secrets']['content']
            common['storage_provisioner_path'] = self.deploy_cfg['local_path_prov']
            common['container_path']['log'] = log_path
            motr_config = common['motr']
            motr_config['num_client_inst'] = client_instance
            s3_service = common['external_services']['s3']
            control_service = common['external_services']['control']
            s3_service['type'] = service_type
            control_service['type'] = service_type
            s3_service['nodePorts']['http'] = nodeport_http
            s3_service['nodePorts']['https'] = nodeport_https
            control_service['nodePorts']['https'] = control_nodeport_https
            common['s3']['max_start_timeout'] = self.deploy_cfg['s3_max_start_timeout']
            if service_type == "LoadBalancer":
                s3_service['count'] = lb_count
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

    @staticmethod
    def deploy_cortx_k8s_re_job(master_node_list: list, worker_node_list: list,
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
        hosts = "\n".join(each for each in hosts_input_str)
        jen_parameter["hosts"] = hosts
        jen_parameter["DEPLOY_TARGET"] = deploy_target

        output = Provisioner.build_job(
            k8s_deploy_cfg["cortx_job_name"], jen_parameter, k8s_deploy_cfg["auth_token"],
            k8s_deploy_cfg["jenkins_url"])
        LOGGER.info("Jenkins Build URL: %s", output['url'])
        if output['result'] == "SUCCESS":
            LOGGER.info("k8s Cluster Deployment successful")
            return True, output['result']
        LOGGER.error("k8s Cluster Deployment %s,please check URL", output['result'])
        return False, output['result']

    @staticmethod
    def get_hctl_status(node_obj, pod_name: str) -> tuple:
        """
        Get hctl status for cortx.
        param: master_node: Master node(Logical Node object)
        param: pod_name: Running Data Pod
        return: True/False and success/failure message
        """
        try:
            LOGGER.info("Get Cluster status")
            cluster_status = node_obj.execute_cmd(cmd=common_cmd.K8S_HCTL_STATUS.
                                                  format(pod_name)).decode('UTF-8')
        finally:
            node_obj.disconnect()
        cluster_status = json.loads(cluster_status)
        if cluster_status is not None:
            nodes_data = cluster_status["nodes"]
            for node_data in nodes_data:
                services = node_data["svcs"]
                LOGGER.debug(services)
                for svc in services:
                    if svc["status"] != "started":
                        if svc["name"] == common_const.MOTR_CLIENT:
                            continue
                        return False, "Service {} not started.".format(svc["name"])
            return True, "Cluster is up and running."
        return False, "Cluster status is not retrieved."

    def destroy_setup(self, master_node_obj: LogicalNode, worker_node_obj: list,
                      custom_repo_path: str = PROV_CFG["k8s_cortx_deploy"]["k8s_dir"]):
        """
        Method used to run destroy script
        param: master node obj list
        param: worker node obj list
        """
        destroy_cmd = Template(common_cmd.DESTROY_CLUSTER_CMD).substitute(dir=custom_repo_path)
        list_etc_3rd_party = Template(common_cmd.LS_LH_CMD).substitute(
            dir=self.deploy_cfg['3rd_party_dir'])
        list_data_3rd_party = Template(common_cmd.LS_LH_CMD).substitute(
            dir=self.deploy_cfg['3rd_party_data_dir'])
        try:
            if not master_node_obj.path_exists(custom_repo_path):
                raise Exception(f"Repo path {custom_repo_path} does not exist")
            resp = master_node_obj.execute_cmd(cmd=destroy_cmd, recv_ready=True,
                                               timeout=self.deploy_cfg['timeout']['destroy'])
            LOGGER.debug("resp : %s", resp)
            for worker in worker_node_obj:
                if worker.path_exists(self.deploy_cfg["mnt_path"]):
                    resp_mnt = worker.execute_cmd(
                        common_cmd.CMD_REMOVE_DIR.format(self.deploy_cfg["mnt_path"]))
                    LOGGER.debug(resp_mnt)
                if worker.path_exists(self.deploy_cfg['3rd_party_dir']):
                    resp_ls = worker.execute_cmd(cmd=list_etc_3rd_party, read_lines=True)
                    LOGGER.debug("resp : %s", resp_ls)
                if worker.path_exists(self.deploy_cfg['3rd_party_data_dir']):
                    resp_data = worker.execute_cmd(cmd=list_data_3rd_party, read_lines=True)
                    LOGGER.debug("resp : %s", resp_data)
            return True, resp
        # pylint: disable=broad-except
        except BaseException as error:
            return False, error

    @staticmethod
    # pylint: disable-msg=too-many-locals
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
    def post_deployment_steps_lc(s3_engine, endpoint, **kwargs):
        """
        Perform CSM login, S3 account creation and AWS configuration on client
        returns status boolean
        """
        access_key = kwargs.get("access_key", None)
        secret_key = kwargs.get("secret_key", None)
        LOGGER.info("Post Deployment Steps")
        if not secret_key and not access_key:
            LOGGER.info("Create S3 account")
            csm_s3 = RestS3user()
            csm_s3.create_custom_s3_payload("valid")
            resp = csm_s3.create_s3_account()
            LOGGER.info("Response for account creation: %s", resp.json())
            details = resp.json()
            access_key = details['access_key']
            secret_key = details["secret_key"]

        try:
            LOGGER.info("Configure AWS on Client")
            resp = system_utils.execute_cmd(common_cmd.CMD_AWS_INSTALL)
            LOGGER.debug("resp : %s", resp)
            if s3_engine == common_const.S3_ENGINE_RGW:
                LOGGER.info("Configure AWS keys on Client %s", s3_engine)
                resp = system_utils.execute_cmd(
                    common_cmd.CMD_AWS_CONF_KEYS_RGW.format(access_key, secret_key, endpoint))
                LOGGER.debug("resp : %s", resp)
            else:
                LOGGER.info("Configure AWS keys on Client %s")
                resp = system_utils.execute_cmd(
                    common_cmd.CMD_AWS_CONF_KEYS.format(access_key, secret_key))
                LOGGER.debug("resp : %s", resp)
        # workaround till we have solution for minio configure error
        # URL `192.168.54.66:30443` for MinIO Client should be of the
        # form scheme://host[:port]/ without resource component.
        # \nmake: *** [minio-configure] Error 1\n'
        except requests.exceptions.InvalidURL as error:
            LOGGER.exception(error)
            return True, resp
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

    # pylint: disable=too-many-arguments
    def write_read_validate_file(self, s3t_obj, bucket_name,
                                 test_file, count, block_size):
        """
        Create test_file with file_size(count*blocksize) and upload to bucket_name
        validate checksum after download and deletes the file
        param:s3t_obj: s3 obj to fetch access_key and secret_key
        param:bucket_name: bucket name
        param: test_file: test file
        param: count: no. of objects
        param block size: block size of the object
        """
        file_path = os.path.join(self.test_dir_path, test_file)
        if not os.path.isdir(self.test_dir_path):
            LOGGER.debug("File path not exists")
            system_utils.execute_cmd(cmd=common_cmd.CMD_MKDIR.format(self.test_dir_path))

        LOGGER.info("Creating a file with name %s", test_file)
        system_utils.create_file(file_path, count, "/dev/urandom", block_size)

        LOGGER.info("Retrieving checksum of file %s", test_file)
        resp1 = system_utils.get_file_checksum(file_path)
        assert_utils.assert_true(resp1[0], resp1[1])
        chksm_before_put_obj = resp1[1]

        LOGGER.info("Uploading a object %s to a bucket %s", test_file, bucket_name)
        resp = s3t_obj.put_object(bucket_name, test_file, file_path)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Validate upload of object %s ", test_file)
        resp = s3t_obj.object_list(bucket_name)
        assert_utils.assert_in(test_file, resp[1], f"Failed to upload create {test_file}")

        LOGGER.info("Removing local file from client and downloading object")
        system_utils.remove_file(file_path)
        resp = s3t_obj.get_object(bucket=bucket_name, key=test_file)
        with open(file_path, "wb") as data:
            data.write(resp[1]['Body'].read())
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Verifying checksum of downloaded file with old file should be same")
        resp = system_utils.get_file_checksum(file_path)
        assert_utils.assert_true(resp[0], resp[1])
        chksm_after_dwnld_obj = resp[1]
        assert_utils.assert_equal(chksm_before_put_obj, chksm_after_dwnld_obj)

        LOGGER.info("Delete the file from the bucket")
        resp = s3t_obj.delete_object(bucket_name, test_file)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Delete downloaded file")
        resp = system_utils.remove_file(file_path)
        assert_utils.assert_true(resp[0], resp[1])

    def basic_io_write_read_validate(self, s3t_obj: S3TestLib, bucket_name: str):
        """
        This method write, read and validate the object.
        param: s3t_obj: s3 obj to fetch access_key and secret key
        param: bucket_name:bucket name
        """
        LOGGER.info("STARTED: Basic IO")
        basic_io_config = PROV_CFG["test_basic_io"]

        LOGGER.info("Creating bucket %s", bucket_name)
        resp = s3t_obj.create_bucket(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])

        LOGGER.info("Perform write/read/validate/delete with multiples object sizes. ")
        for b_size, max_count in basic_io_config["io_upper_limits"].items():
            for count in range(0, max_count):
                test_file = "basic_io_" + str(count) + str(b_size)
                block_size = "1M"
                if str(b_size).lower() == "kb":
                    block_size = "1K"

                self.write_read_validate_file(s3t_obj, bucket_name, test_file, count, block_size)

        LOGGER.info("Delete bucket %s", bucket_name)
        resp = s3t_obj.delete_bucket(bucket_name)
        assert_utils.assert_true(resp[0], resp[1])
        LOGGER.info("Basic IO Completed")

    @staticmethod
    def io_workload(access_key, secret_key, bucket_prefix, clients=5,
                    **kwargs):
        """
        S3 bench workload test executed for each of Erasure coding config
        param: access_key: s3 user access key
        param: secret_key: s3 user secret keys
        param: bucket_prefix: bucket prefix
        param: client: no clients request
        param: endpoint_url: endpoint url
        """
        endpoint_url = kwargs.get('endpoint_url', "s3.seagate.com")
        LOGGER.info("STARTED: S3 bench workload test")
        workloads = [
            "1Kb", "4Kb", "8Kb", "16Kb", "32Kb", "64Kb", "128Kb", "256Kb", "512Kb",
            "1Mb", "4Mb", "8Mb", "16Mb", "32Mb", "64Mb", "128Mb", "256Mb", "512Mb", "1Gb", "2Gb"
        ]
        resp = s3bench.setup_s3bench()
        assert (resp, resp), "Could not setup s3bench."
        for workload in workloads:
            bucket_name = bucket_prefix + "-" + str(workload).lower()
            if "Kb" in workload:
                samples = 50
            elif "Mb" in workload:
                samples = 10
            else:
                samples = 5
            resp = s3bench.s3bench(access_key, secret_key, bucket=bucket_name,
                                   num_clients=clients,
                                   num_sample=samples, obj_name_pref=f"test-object-{workload}",
                                   obj_size=workload,
                                   skip_cleanup=False, duration=None, log_file_prefix=bucket_prefix,
                                   end_point=endpoint_url, validate_certs=S3_CFG["validate_certs"])
            LOGGER.info("json_resp %s\n Log Path %s", resp[0], resp[1])
            assert not s3bench.check_log_file_error(resp[1]), \
                f"S3bench workload for object size {workload} failed. " \
                    f"Please read log file {resp[1]}"
            LOGGER.info("ENDED: S3 bench workload test")

    @staticmethod
    def dump_in_csv(test_list: List, csv_filepath):
        """
        Method to dump the data in csv file
        param: list of data which needs to be added in row of csv file
        param: csv_filepath: csv file path
        returns: updated csv file with its path
        """
        with open(csv_filepath, 'a+') as fptr:
            # writing the fields
            write = csv.writer(fptr)
            write.writerow(test_list)
            fptr.close()
        return csv_filepath

    @staticmethod
    def get_data_pods(node_obj) -> tuple:
        """
        Get list of data pods in cluster.
        param: node_obj: Master node(Logical Node object)
        return: True/False and pods list/failure message
        """
        LOGGER.info("Get list of data pods in cluster.")
        output = node_obj.execute_cmd(common_cmd.CMD_POD_STATUS +
                                      " -o=custom-columns=NAME:.metadata.name",
                                      read_lines=True)
        data_pod_list = [pod.strip() for pod in output if common_const.POD_NAME_PREFIX in pod]
        if data_pod_list is not None:
            return True, data_pod_list
        return False, "Data PODS are not retrieved for cluster."

    @staticmethod
    def check_pods_status(node_obj) -> bool:
        """
        Helper function to check pods status.
        :param node_obj: Master node(Logical Node object)
        :return: True/False
        """
        LOGGER.info("Checking all Pods are online.")
        resp = node_obj.execute_cmd(cmd=common_cmd.CMD_POD_STATUS,
                                    read_lines=True)
        for line in range(1, len(resp)):
            if "Running" not in resp[line]:
                return False
        return True

    def deploy_stage(self, sol_file_path, master_node_list,
                     worker_node_list, namespace, system_disk_dict,
                     **kwargs):
        """
        This method is used to perform deploy,validate cluster and check services
        param: master_node_list: master_node_obj list
        param: worker_node_list: worker_node_obj list
        param: namespace : custom namespace
        param: system_disk_dict system disk dict to utilize for mounting
         provisioner path
        returns True, resp
        """
        deployment_type = kwargs.get("deployment_type", self.deployment_type)
        LOGGER.info("Step to Perform Cortx Cluster Deployment")
        deploy_resp = self.deploy_cortx_cluster(sol_file_path, master_node_list,
                                                worker_node_list, system_disk_dict,
                                                git_tag=self.git_script_tag,
                                                namespace=namespace)
        LOGGER.debug("Deploy execution response %s", deploy_resp)
        if len(namespace) > self.deploy_cfg["max_char_limit"] or \
                bool(re.findall(r'\w*[A-Z]\w*', namespace)):
            LOGGER.debug("Negative Test Scenario")
            assert_utils.assert_false(deploy_resp[0], deploy_resp[1])
            if self.patterns in deploy_resp[1]:
                return True, 0
        # Run status-cortx-cloud.sh script to fetch the status of all resources.
        if deploy_resp[0]:
            LOGGER.info("Validate cluster status using status-cortx-cloud.sh")
            resp = self.validate_cluster_status(master_node_list[0],
                                                self.deploy_cfg["k8s_dir"])
            assert_utils.assert_true(resp[0], resp[1])
            if not deploy_resp[1]:
                LOGGER.info("Step to Check  ALL service status")
                time.sleep(self.deploy_cfg["sleep_time"])
                service_status = self.check_service_status(master_node_list[0],
                                                           deployment_type=deployment_type)
                LOGGER.info("All service resp is %s", service_status)
                assert_utils.assert_true(service_status[0], service_status[1])
                if self.deployment_type != self.deploy_cfg["deployment_type_data"]:
                    if self.cortx_server_image:
                        resp = self.verfiy_installed_rpms(master_node_list,
                                                          common_const.RGW_CONTAINER_NAME,
                                                          self.deploy_cfg["rgw_rpm"])
                        assert_utils.assert_true(resp[0], resp[1])
        return True, service_status[-1]

    def client_config(self, master_node_list, namespace, **kwargs):
        """
        This method is used to setup the client
        param: master_node_list: master_node_obj
        param: namespace: custom namespace
        returns True, s3t_obj, list of access,secret key with ext_port_ip
        """
        access_key = kwargs.get("access_key", None)
        secret_key = kwargs.get("secret_key", None)
        flag = kwargs.get("flag", None)
        LOGGER.info("Setting the current namespace")
        resp_ns = master_node_list[0].execute_cmd(
            cmd=common_cmd.KUBECTL_SET_CONTEXT.format(namespace),
            read_lines=True)
        LOGGER.debug("response is %s,", resp_ns)
        resp = system_utils.execute_cmd(
            common_cmd.CMD_GET_IP_IFACE.format(self.deploy_cfg['iface']))
        eth1_ip = resp[1].strip("'\\n'b'")
        if self.service_type == "NodePort":
            resp = ext_lbconfig_utils.configure_nodeport_lb(master_node_list[0],
                                                            self.deploy_cfg['iface'])
            if not resp[0]:
                LOGGER.debug("Did not get expected response: %s", resp)
            ext_ip = resp[1]
            port = resp[2]
            http_port = resp[3]
            ext_port_ip = Template(self.deploy_cfg['https_protocol']
                                   + ":$port").substitute(ip=ext_ip, port=port)
            LOGGER.debug("External LB value, ip and port will be: %s", ext_port_ip)
            if flag == "component":
                ext_port_ip = Template(self.deploy_cfg['http_protocol']
                                       + ":$port").substitute(ip=ext_ip, port=http_port)
                LOGGER.debug("External LB value, ip and port will be: %s", ext_port_ip)
        else:
            LOGGER.info("Configure HAproxy on client")
            ext_lbconfig_utils.configure_haproxy_rgwlb(master_node_list[0].hostname,
                                                       master_node_list[0].username,
                                                       master_node_list[0].password,
                                                       eth1_ip, self.deploy_cfg['iface'])
            ext_port_ip = Template(self.deploy_cfg['https_protocol']).substitute(ip=
                                                                                 eth1_ip)
        LOGGER.info("Step to Create S3 account and configure credentials")
        if self.s3_engine == 2:  # "s3_engine flag is used for picking up the configuration
            # for legacy s3 and rgw, `1` - legacy s3 and `2` - rgw"
            if flag == "component":
                LOGGER.debug("Access_key and Secret_key %s %s ", access_key, secret_key)
                resp = self.post_deployment_steps_lc(self.s3_engine,
                                                     ext_port_ip, access_key=access_key,
                                                     secret_key=secret_key)
                assert_utils.assert_true(resp[0], resp[1])
            else:
                resp = self.post_deployment_steps_lc(self.s3_engine, ext_port_ip)
                assert_utils.assert_true(resp[0], resp[1])
                access_key, secret_key = S3H_OBJ.get_local_keys()
            if self.service_type == "NodePort":
                s3t_obj = S3TestLib(access_key=access_key, secret_key=secret_key,
                                    endpoint_url=ext_port_ip)

            else:
                s3t_obj = S3TestLib(access_key=access_key, secret_key=secret_key)
            response = [access_key, secret_key, ext_port_ip]
        return True, s3t_obj, response

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements
    def test_deployment(self, master_node_list,
                        worker_node_list, **kwargs):
        """
        This method is used for deployment with various config on N nodes
        param: sns_data
        param: sns_parity
        param: sns_spare
        param: dix_data
        param: dix_parity
        param: dix_spare
        param: cvg_count
        param: data disk per cvg
        param: master node obj list
        param: worker node obj list
        keyword:setup_k8s_cluster_flag: flag to deploy k8s setup
        keyword:cortx_cluster_deploy_flag: flag to deploy cortx cluster
        keyword:setup_client_config_flag: flsg to setup client with haproxy
        keyword:run_basic_s3_io_flag: flag to run basic s3 io
        keyword:run_s3bench_workload_flag: flag to run s3bench IO
        keyword:destroy_setup_flag:flag to destroy cortx cluster
        keyword:log_path:log_path of cortx cluster
        keyword:data_disk_size: data disk size
        keyword:meta_disk_size: metadata disk size
        keyword:namespace: custom namespace
        keyword:custom_repo_path: Custom repo path to be used for ONLY DESTROY cortx cluster
        """
        sns_data = kwargs.get("sns_data")
        sns_parity = kwargs.get("sns_parity")
        sns_spare = kwargs.get("sns_spare")
        dix_data = kwargs.get("dix_data")
        dix_parity = kwargs.get("dix_parity")
        dix_spare = kwargs.get("dix_spare")
        cvg_count = kwargs.get("cvg_count")
        data_disk_per_cvg = kwargs.get("data_disk_per_cvg")
        setup_k8s_cluster_flag = \
            kwargs.get("setup_k8s_cluster_flag", self.deploy_cfg['setup_k8s_cluster_flag'])
        cortx_cluster_deploy_flag = \
            kwargs.get("cortx_cluster_deploy_flag",
                       self.deploy_cfg['cortx_cluster_deploy_flag'])
        setup_client_config_flag = \
            kwargs.get("setup_client_config_flag",
                       self.deploy_cfg['setup_client_config_flag'])
        run_basic_s3_io_flag = \
            kwargs.get("run_basic_s3_io_flag", self.deploy_cfg['run_basic_s3_io_flag'])
        run_s3bench_workload_flag = \
            kwargs.get("run_s3bench_workload_flag",
                       self.deploy_cfg['run_s3bench_workload_flag'])
        destroy_setup_flag = kwargs.get("destroy_setup_flag", self.deploy_cfg['destroy_setup_flag'])
        log_path = kwargs.get("log_path", self.deploy_cfg['log_path'])
        custom_repo_path = kwargs.get("custom_repo_path", self.deploy_cfg["k8s_dir"])
        namespace = kwargs.get("namespace", self.deploy_cfg["namespace"])
        report_path = kwargs.get("report_filepath", self.deploy_cfg["report_file"])
        data_disk_size = kwargs.get("data_disk_size", self.deploy_cfg["data_disk_size"])
        metadata_disk_size = kwargs.get("meta_disk_size", self.deploy_cfg["metadata_disk_size"])
        deployment_type = kwargs.get("deployment_type", self.deployment_type)
        client_instance = kwargs.get("client_instances", self.client_instance)
        row = list()
        row.append(len(worker_node_list))
        LOGGER.info("STARTED: {%s node (SNS-%s+%s+%s) (DIX-%s+%s+%s) "
                    "k8s based Cortx Deployment", len(worker_node_list),
                    sns_data, sns_parity, sns_spare, dix_data, dix_parity, dix_spare)
        sns = Template("$data+$parity+$spare").substitute(data=sns_data,
                                                          parity=sns_parity,
                                                          spare=sns_spare)  # Value of N+K+S for sns
        dix = Template("$data+$parity+$spare").substitute(data=dix_data,
                                                          parity=dix_parity,
                                                          spare=dix_spare)  # Value of N+K+S for dix

        LOGGER.debug("The deployment NAMESPACE is %s", namespace)
        row.append(sns)
        row.append(dix)
        if setup_k8s_cluster_flag:
            resp = self.verify_k8s_cluster_exists(master_node_list, worker_node_list)
            if not resp:
                LOGGER.info("Step to Perform k8s Cluster Deployment")
                resp = self.setup_k8s_cluster(master_node_list, worker_node_list)
                assert_utils.assert_true(resp[0], resp[1])

        if cortx_cluster_deploy_flag:
            LOGGER.info("Step to Taint master nodes if not already done.")
            for node in master_node_list:
                resp = self.validate_master_tainted(node)
                if not resp:
                    self.taint_master(node)
            LOGGER.info("Step to Download solution file template")
            path = self.checkout_solution_file(self.git_script_tag)
            LOGGER.info("Step to Update solution file template")
            resp = self.update_sol_yaml(worker_obj=worker_node_list, filepath=path,
                                        cortx_image=self.cortx_image,
                                        sns_data=sns_data, sns_parity=sns_parity,
                                        sns_spare=sns_spare, dix_data=dix_data,
                                        dix_parity=dix_parity, dix_spare=dix_spare,
                                        cvg_count=cvg_count, data_disk_per_cvg=data_disk_per_cvg,
                                        size_data_disk=data_disk_size,
                                        size_metadata=metadata_disk_size,
                                        log_path=log_path,
                                        cortx_server_image=self.cortx_server_image,
                                        cortx_data_image=self.cortx_data_image,
                                        service_type=self.service_type,
                                        namespace=namespace,
                                        https_port=self.nodeport_https,
                                        http_port=self.nodeport_http,
                                        control_https_port=self.control_nodeport_https,
                                        deployment_type=deployment_type,
                                        client_instance=client_instance)
            assert_utils.assert_true(resp[0], "Failure updating solution.yaml")
            with open(resp[1]) as file:
                LOGGER.info("The detailed solution yaml file is\n")
                for line in file.readlines():
                    LOGGER.info(line)
            sol_file_path = resp[1]
            system_disk_dict = resp[2]
            deploy_stage_resp = self.deploy_stage(sol_file_path,
                                                  master_node_list,
                                                  worker_node_list,
                                                  namespace, system_disk_dict)
            row.append(deploy_stage_resp[1])
        if self.deployment_type not in self.exclusive_pod_list:
            if setup_client_config_flag:
                client_config_res = self.client_config(master_node_list, namespace)
                if client_config_res[0]:
                    s3t_obj = client_config_res[1]
                    if run_basic_s3_io_flag:
                        LOGGER.info("Step to Perform basic IO operations")
                        bucket_name = "bucket-" + str(int(time.time()))
                        self.basic_io_write_read_validate(s3t_obj, bucket_name)
                    if run_s3bench_workload_flag:
                        LOGGER.info("Step to Perform S3bench IO")
                        bucket_name = "bucket-" + str(int(time.time()))
                        access_key = client_config_res[2][0]
                        secret_key = client_config_res[2][1]
                        ext_port_ip = client_config_res[2][2]
                        self.io_workload(access_key=access_key,
                                         secret_key=secret_key,
                                         bucket_prefix=bucket_name,
                                         endpoint_url=ext_port_ip)
        if destroy_setup_flag:
            LOGGER.info("Step to Destroy setup")
            resp = self.destroy_setup(master_node_list[0], worker_node_list, custom_repo_path)
            assert_utils.assert_true(resp[0], resp[1])
        row.append("PASS")
        if os.path.isfile(report_path):
            resp = self.dump_in_csv(row, report_path)
            LOGGER.info("Report path is %s", resp)
        LOGGER.info("ENDED: %s node (SNS-%s+%s+%s) k8s based Cortx Deployment",
                    len(worker_node_list), sns_data, sns_parity, sns_spare)

    def check_s3_status(self, master_node_obj: LogicalNode,
                        pod_prefix: str = common_const.POD_NAME_PREFIX):
        """
        Function to check s3 server status
        """
        deploy_ff_cfg = PROV_CFG["deploy_ff"]
        start_time = int(time.time())
        end_time = start_time + 1800  # 30 mins timeout
        response = list()
        while int(time.time()) < end_time:
            pod_name = master_node_obj.get_pod_name(pod_prefix=pod_prefix)
            assert_utils.assert_true(pod_name[0], pod_name[1])
            resp = self.get_hctl_status(master_node_obj, pod_name[1])
            if resp[0]:
                time_taken = (int(time.time()) - start_time)
                LOGGER.info("All the services are online. Time Taken : %s", time_taken)
                response.extend(resp)
                response.append(time_taken)
                break
            time.sleep(deploy_ff_cfg["per_step_delay"])
        if len(response) == 0:
            return False, "All Services are not started."
        return response

    def check_service_status(self, master_node_obj: LogicalNode, **kwargs):
        """
        Function to check all service status
        param: nodeObj of Master node.
        returns: dict of all pods with service status True/False and time taken
        """
        deployment_type = kwargs.get("deployment_type", self.deployment_type)
        LOGGER.debug("DEPLOYMENT TYPE IN SERVICE CHECK IS %s", deployment_type)
        resp = self.check_pods_status(master_node_obj)
        assert_utils.assert_true(resp, "All Pods are not in Running state")
        if self.deployment_type in self.data_only_list:
            data_pod_list = LogicalNode.get_all_pods(master_node_obj,
                                                     common_const.POD_NAME_PREFIX)
            assert_utils.assert_not_equal(len(data_pod_list), 0, "No cortx-data Pods found")
            pod_count = len(data_pod_list)
            LOGGER.debug("THE DATA POD LIST ARE %s", data_pod_list)
        if self.deployment_type in self.server_only_list:
            server_pod_list = LogicalNode.get_all_pods(master_node_obj,
                                                       common_const.SERVER_POD_NAME_PREFIX)
            assert_utils.assert_not_equal(len(server_pod_list), 0, "No cortx-server Pods found")
            pod_count = len(server_pod_list)
            LOGGER.debug("THE SERVER POD LIST ARE %s", server_pod_list)
        sleep_val = self.deploy_cfg["service_delay"]
        if len(data_pod_list) > self.deploy_cfg["node_count"]:
            sleep_val = self.deploy_cfg["service_delay_scale"]
        start_time = int(time.time())
        end_time = start_time + sleep_val * (pod_count * 2)  # max 32 mins timeout
        response = list()
        hctl_status = dict()
        while int(time.time()) < end_time:
            if self.deployment_type in self.data_only_list:
                for pod_name in data_pod_list:
                    resp = self.get_hctl_status(master_node_obj, pod_name)
                    hctl_status.update({pod_name: resp[0]})
                    LOGGER.debug("Service time taken from data pod is %s",
                                 end_time - int(time.time()))
                LOGGER.debug(hctl_status)
            if self.deployment_type in self.server_only_list:
                for server_pod_name in server_pod_list:
                    resp = self.get_hctl_status(master_node_obj, server_pod_name)
                    hctl_status.update({server_pod_name: resp[0]})
                    LOGGER.debug("Service time taken from server pod is %s",
                                 end_time - int(time.time()))
                LOGGER.debug(hctl_status)
            LOGGER.debug("services status is %s, End Time is %s", resp[0], end_time)
            status = all(element is True for element in list(hctl_status.values()))
            if status:
                time_taken = time.time() - start_time
                LOGGER.info("#### Services online. Time Taken : %s", time_taken)
                response.append(status)
                response.append(time_taken)
                return response
        LOGGER.info("hctl_status = %s", hctl_status)
        response.extend([False, 'Timeout'])
        return response

    # pylint: disable=broad-except
    @staticmethod
    def kill_all_process_instance(name: str):
        """
        Kill all instances of specified process
        :param name: Name of process
        return : boolean
        """
        try:
            command = f"ps ax | grep '{name}' | grep -v grep"
            LOGGER.info("Command : %s", command)
            for line in os.popen(command):
                fields = line.split()
                pid = fields[0]
                # terminating process
                LOGGER.debug("Killing PID : %s", pid)
                os.kill(int(pid), signal.SIGKILL)
            LOGGER.info("Process Successfully terminated")
            return True
        except OSError as error:
            LOGGER.error("Error Encountered while killing %s: %s", name, error)
            return False

    @staticmethod
    def get_durability_config(num_nodes) -> list:
        """
        Get 3 EC configs based on the number of nodes given as args.
        EC config will be calculated considering CVG as 1,2,3.
        NOTE: Minimum 7 disks per node are required for this method.
        param: num_nodes : Number of nodes
        return : list of configs. (List of Dictionary)
        """
        config_list = []
        LOGGER.debug("Configurations for %s Nodes", num_nodes)
        for i in range(1, 4):
            config = {}
            cvg_count = i
            sns_total = num_nodes * cvg_count
            sns_data = math.ceil(sns_total / 2)
            sns_data = sns_data + i
            if sns_data >= sns_total:
                sns_data = sns_data - 1
            sns_parity = sns_total - sns_data

            dix_parity = math.ceil((num_nodes + cvg_count) / 2) + i
            if dix_parity > (num_nodes - 1):
                dix_parity = num_nodes - 1

            config["sns_data"] = sns_data
            config["sns_parity"] = sns_parity
            config["sns_spare"] = 0
            config["dix_data"] = 1
            config["dix_parity"] = dix_parity
            config["dix_spare"] = 0
            config["data_disk_per_cvg"] = 0  # To utilize max possible on the available system
            config["cvg_count"] = i
            config_list.append(config)
            LOGGER.debug("Config %s : %s", i, config)

        return config_list

    @staticmethod
    def verify_k8s_cluster_exists(master_node_list, worker_node_list):
        """
        This method is to verify the K8S setup exists for given set of nodes.
        master_node_list: is the Master Node
        worker_node_list: Worker Nodes
        returns True if we have K8s cluster exists
        """
        resp = master_node_list[0].execute_cmd(common_cmd.K8S_WORKER_NODES,
                                               read_lines=True)
        if len(resp) == 0:
            return False
        worker_list = []
        worker_nodes = []
        for worker in resp[1:]:
            worker_list.append(worker.strip())
        LOGGER.debug(worker_list)
        for nodes in worker_node_list:
            worker_nodes.append(nodes.hostname)
        LOGGER.debug("Data from setup_details %s", worker_nodes)
        master_rsp = master_node_list[0].execute_cmd(common_cmd.K8S_MASTER_NODE,
                                                     read_lines=True)
        if len(worker_nodes) == len(worker_list):
            if worker_nodes.sort() == worker_list.sort() and master_rsp[-1].strip() == \
                    master_node_list[0].hostname:
                LOGGER.debug("Master and Worker nodes are matched."
                             "skipping K8s Cluster deployment")
                return True
            LOGGER.error("Input Setup details mismatch with current setup")
            return False
        LOGGER.debug("The nodes count mismatched need to deploy new K8s cluster")
        return False

    @staticmethod
    def verfiy_installed_rpms(master_node_list, container_name, rpm_name):
        """
        This method is to verify the installed rpms in the pods.
        param: master_node_list: master node obj.
        param: rpm_name: rpm which need to be verify if its
        installed or not
        returns True
        """
        server_pods_list = LogicalNode.get_all_pods(master_node_list[0],
                                                    common_const.SERVER_POD_NAME_PREFIX)
        installed_rpm = []
        for server_pod in server_pods_list:
            resp = master_node_list[0].execute_cmd(
                common_cmd.KUBECTL_GET_RPM.format(server_pod, container_name, rpm_name),
                read_lines=True)
        for element in resp:
            installed_rpm.append(element.strip())
        LOGGER.debug("Installed rpm is %s", installed_rpm)
        result = re.search(rpm_name, installed_rpm[0])
        if result is not None:
            LOGGER.debug("RPM is %s", installed_rpm)
            return True, installed_rpm
        return False, installed_rpm

    @staticmethod
    def pull_image(node_obj: LogicalNode, image: str) -> tuple:
        """
        Helper function to pull cortx image.
        :param: node_obj: node object(Logical Node object)
        :param: image: cortx image to pull
        :return: True/False and success/failure message
        """
        LOGGER.info("Pull Cortx image.")
        try:
            node_obj.execute_cmd(common_cmd.CMD_DOCKER_PULL.format(image))
        except IOError as err:
            LOGGER.error("An error occurred in %s:", ProvDeployK8sCortxLib.pull_image.__name__)
            return False, err
        return True, "Image pulled."

    @staticmethod
    def update_sol_with_image(file_path: str, image_dict: dict) -> tuple:
        """
        Helper function to update image in solution.yaml.
        :param: file_path: Filename with complete path
        :param: image_dict: Dict with images
        :return: True/False and local file
        """
        LOGGER.info("Pull Cortx image.")
        prov_deploy_cfg = PROV_TEST_CFG["k8s_prov_cortx_deploy"]
        with open(file_path) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']
            soln.close()
        for image in prov_deploy_cfg["images_key"]:
            if image == "cortxserver":
                parent_key['images'][image] = image_dict['rgw_image']
            elif image == "cortxdata":
                parent_key['images'][image] = image_dict['data_image']
            else:
                parent_key['images'][image] = image_dict['all_image']
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(file_path, 'w') as pointer:
            yaml.dump(conf, pointer, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            pointer.close()
        return True, file_path

    def pre_check(self, master_node_list):
        """
        This method will dump all the info before deployment starts
        It will capture the taint nodes is any stale entries left out like
        services or any other resources.
        Param: master_node_list: node obj for master node.
        returns true, resp_list
        """
        taint_cmd = common_cmd.KUBECTL_GET_TAINT_NODES.format(self.deploy_cfg["pre_check_log"])
        all_resource = common_cmd.KUBECTL_GET_ALL.format(self.deploy_cfg["pre_check_log"])
        get_secret = common_cmd.KUBECTL_GET_SCT.format("secret",
                                                       self.deploy_cfg["pre_check_log"])
        get_pv = common_cmd.KUBECTL_GET_PV.format(self.deploy_cfg["pre_check_log"])
        get_pvc = common_cmd.KUBECTL_GET_PVC.format(self.deploy_cfg["pre_check_log"])
        list_pre_check = [taint_cmd, all_resource, get_secret, get_pvc, get_pv]
        LOGGER.info("======== Running Pre-checks before deployment ==========")
        for cmd in list_pre_check:
            master_node_list.execute_cmd(cmd, read_lines=True)
        local_path = os.path.join(LOG_DIR, LATEST_LOG_FOLDER, self.deploy_cfg["pre_check_log"])
        if master_node_list.path_exists(self.deploy_cfg["pre_check_log"]):
            master_node_list.copy_file_to_local(remote_path=self.deploy_cfg["pre_check_log"],
                                                local_path=local_path)
            master_node_list.execute_cmd(
                common_cmd.CMD_REMOVE_DIR.format(self.deploy_cfg["pre_check_log"]))
        return True, local_path

    @staticmethod
    def update_sol_with_image_any_pod(file_path: str, image_dict: dict) -> tuple:
        """
        Helper function to update image in solution.yaml.
        :param: file_path: Filename with complete path
        :param: image_dict: Dict with images
        :return: True/False and local file
        """
        LOGGER.info("Pull Cortx image.")
        with open(file_path) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']
            soln.close()
        for image in image_dict:
            if image == "cortxcontrol":
                parent_key['images'][image] = image_dict['cortxcontrol']
            elif image == "cortxha":
                parent_key['images'][image] = image_dict['cortxha']
            elif image == "cortxdata":
                parent_key['images'][image] = image_dict['cortxdata']
            elif image == "cortxserver":
                parent_key['images'][image] = image_dict['cortxserver']
            else:
                LOGGER.info("Error")
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(file_path, 'w') as pointer:
            yaml.dump(conf, pointer, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            pointer.close()
        return True, file_path

    @staticmethod
    def get_installed_version(master_node_obj):
        """
        Get installed version for image
        return : image version
        """
        resp = HAK8s.get_config_value(master_node_obj)
        version = resp[1]['cortx']['common']['release']['version']
        LOGGER.debug("Current Version is %s", version)
        return version

    @staticmethod
    def generate_and_compare_both_version(input_installing_version, installed_version):
        """
        This method is used for comparing the versions
        param: input_installing_version
        param: installed_version
        return : True/False, installing version
        """
        installing_version = input_installing_version.split(":")[1].split("-")
        installed_version = installed_version.split("-")
        LOGGER.info("Current CORTX image version: %s", installed_version)
        LOGGER.info("Installing CORTX image version: %s", installing_version)
        if int(installing_version[1]) > int(installed_version[1]):
            LOGGER.info("Installing version is higher than installed version. %s ,%s",
                        installing_version[1], installed_version[1])
            return True, installing_version
        return False, installing_version, "Installing version is not lower than installed version"

    def update_sol_for_granular_deploy(self, file_path: str, host_list: list, master_node_list,
                                       image: str, deployment_type: str, **kwargs):
        """
        Helper function to update image in solution.yaml.
        :param: file_path: Filename with complete path
        :param: host_list: List of setup hosts
        :param: image: Image to be used for deployment
        :param: deployment_type: Type of deployment(Standard/Data-Only)
        :return: True/False and local file
        """
        cvg_count = kwargs.get("cvg_count", 2)
        data_disk_per_cvg = kwargs.get("data_disk_per_cvg", 0)
        LOGGER.debug("Update nodes section with setup details.")
        prov_deploy_cfg = PROV_TEST_CFG["k8s_prov_cortx_deploy"]
        resp = self.update_nodes_sol_file(file_path, host_list)
        if not resp[0]:
            return False, "solution.yaml is not updated properly."
        LOGGER.debug("Update storage section and deployment type.")
        with open(file_path) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']
            storage_key = parent_key["storage"]
            soln.close()
        parent_key["deployment_type"] = deployment_type
        if "data" in deployment_type:
            parent_key["images"]["cortxdata"] = image
        else:
            # Extend else condition when a different granular deployment type is available.
            pass
        for cvg in prov_deploy_cfg["cvg_config"]:
            if cvg == "cvg1":
                cvg_key = storage_key[cvg]["devices"]["data"]
                device_list = master_node_list.execute_cmd(cmd=common_cmd.CMD_LIST_DEVICES,
                                                           read_lines=True)[0].split(",")
                device_list[-1] = device_list[-1].replace("\n", "")
                if data_disk_per_cvg == 0:
                    data_disk_per_cvg = int(len(device_list[cvg_count + 1:]) / cvg_count)

                LOGGER.debug("Data disk per cvg : %s", data_disk_per_cvg)
                LOGGER.info(len(cvg_key))
                cvg_len = len(cvg_key)
                for data_disk in range(len(cvg_key) - data_disk_per_cvg):
                    cvg_key.pop("d" + str(cvg_len))
                    cvg_len = cvg_len - 1
                    LOGGER.info(data_disk)
            else:
                storage_key.pop(cvg)
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(file_path, 'w') as pointer:
            yaml.dump(conf, pointer, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            pointer.close()
        return True, file_path

    @staticmethod
    def create_namespace(master_node_list, namespace):
        """
        This method is used for creating custom namespace
        param: master_node_list: node object for primary node
        param: namespace: custom namespace [a-z][0-9] `-``characters
        returns True, namespace created message
        """
        LOGGER.debug("The namespace to be created is %s", namespace)
        master_node_list.execute_cmd(common_cmd.KUBECTL_CREATE_NAMESPACE.format(namespace),
                                     read_lines=True)
        resp = master_node_list.execute_cmd(common_cmd.KUBECTL_GET_NAMESPACE, read_lines=True)
        if namespace in resp:
            LOGGER.debug("The namespace is %s", resp)
            return namespace
        return False, f"Failed to create namespace: {resp}"

    @staticmethod
    def del_namespace(master_node_list, namespace):
        """
        This method is used for delete custom namespace
        param: master_node_list: node object for primary node
        param: namespace: custom namespace [a-z][0-9] `-``characters
        returns True
        """
        LOGGER.debug("The namespace to be deleted is %s", namespace)
        master_node_list.execute_cmd(common_cmd.KUBECTL_DEL_NAMESPACE.format(namespace),
                                     read_lines=True)
        resp = master_node_list.execute_cmd(common_cmd.KUBECTL_GET_NAMESPACE, read_lines=True)
        LOGGER.debug("The namespace is %s", resp.pop(0))
        if namespace in resp:
            return False, f"Failed to del namespace {namespace}"
        return True, f"Successfully deleted the NAMESPACE {namespace}"

    @staticmethod
    def namespace_name_generator(size):
        """
        This method generate random string with combination of lowercase,digit,`-`
        and returns alphanumeric string
        param: size : length of string
        returns Alphanumeric String with `-`
        """
        char = string.ascii_lowercase + string.digits
        generated_string = system_utils.random_string_generator(size, char)
        string_len = int(len(generated_string) / 2)
        string_alpha = generated_string[:string_len] + "-" + generated_string[string_len:]
        LOGGER.info("The string is %s and length is %s", string_alpha, len(string_alpha))
        return string_alpha

    def update_res_limit_third_party(self, filepath):
        """
        This Method is used to update the resource limits for third party services
        file: solution.yaml file
        returns True
        """

        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            common = parent_key['common']
            resource = common['resource_allocation']
            consul = resource['consul']
            zookeeper = resource['zookeeper']['resources']
            kafka = resource['kafka']['resources']
            type_list = ['requests', 'limits']
            consul_list = ['server', 'client']
            third_party_resource = self.deploy_cfg['thirdparty_resource']
            # updating the consul server /client request and limit resources
            for res_type in type_list:
                zookeeper[res_type]['memory'] = \
                    third_party_resource['zookeeper'][res_type]['mem']
                zookeeper[res_type]['cpu'] = \
                    third_party_resource['zookeeper'][res_type]['cpu']
                kafka[res_type]['memory'] = third_party_resource['kafka'][res_type]['mem']
                kafka[res_type]['cpu'] = third_party_resource['kafka'][res_type]['cpu']
                for elem in consul_list:
                    consul[elem]['resources'][res_type]['memory'] = \
                        third_party_resource[elem][res_type]['mem']
                    consul[elem]['resources'][res_type]['cpu'] = \
                        third_party_resource[elem][res_type]['cpu']
            soln.close()
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(filepath, 'w') as soln:
            yaml.dump(conf, soln, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        return True, filepath

    def update_res_limit_cortx(self, filepath):
        """
        This Method is used to update the resource limits for cortx services
        param: filepath: solution.yaml filepath
        returns True, filepath
        """

        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            common = parent_key['common']
            resource = common['resource_allocation']
            hare_hax_res = resource['hare']['hax']['resources']
            data_res = resource['data']
            control_res = resource['control']['agent']['resources']
            server_res = resource['server']['rgw']['resources']
            ha_res = resource['ha']
            type_list = ['requests', 'limits']
            data_list = ['motr', 'confd']
            ha_list = ['fault_tolerance', 'health_monitor', 'k8s_monitor']
            cortx_resource = self.deploy_cfg['cortx_resource']

            for res_type in type_list:
                hare_hax_res[res_type]['memory'] = \
                    cortx_resource['hax'][res_type]['mem']
                hare_hax_res[res_type]['cpu'] = \
                    cortx_resource['hax'][res_type]['cpu']
                server_res[res_type]['memory'] = cortx_resource['rgw'][res_type]['mem']
                server_res[res_type]['cpu'] = cortx_resource['rgw'][res_type]['cpu']
                control_res[res_type]['memory'] = cortx_resource['agent'][res_type]['mem']
                control_res[res_type]['cpu'] = cortx_resource['agent'][res_type]['cpu']
                # updating the motr /confd requests and limits resources
                for elem in data_list:
                    data_res[elem]['resources'][res_type]['memory'] = \
                        cortx_resource[elem][res_type]['mem']
                    data_res[elem]['resources'][res_type]['cpu'] = \
                        cortx_resource[elem][res_type]['cpu']
                # updating the ha component resources
                for ha_elem in ha_list:
                    ha_res[ha_elem]['resources'][res_type]['memory'] = \
                        cortx_resource[ha_elem][res_type]['mem']
                    ha_res[ha_elem]['resources'][res_type]['cpu'] = \
                        cortx_resource[ha_elem][res_type]['cpu']
            soln.close()
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True
        with open(filepath, 'w') as soln:
            yaml.dump(conf, soln, default_flow_style=False,
                      sort_keys=False, Dumper=noalias_dumper)
            soln.close()
        return True, filepath

    @staticmethod
    def get_default_access_secret_key(filepath):
        """
        This is used to access access key and secret key
        file: solution.yaml file
        returns access key and secrets key
        """
        with open(filepath) as soln:
            conf = yaml.safe_load(soln)
            parent_key = conf['solution']  # Parent key
            common = parent_key['common']
            access_key = common["s3"]["default_iam_users"]["auth_admin"]
            secrets = parent_key['secrets']
            secret_key = secrets["content"]["s3_auth_admin_secret"]
            LOGGER.info("Getting access and secret key")
        return access_key, secret_key
