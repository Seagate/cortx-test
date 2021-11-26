# -*- coding: utf-8 -*-
# !/usr/bin/python
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
#

"""Failure Injection adapter. Handles S3 FI and Motr FI.
"""
import logging
import time
from abc import ABC, abstractmethod

from commons import commands
from commons.constants import POD_NAME_PREFIX
from commons.helpers.pods_helper import LogicalNode
from config import DI_CFG

# check and set pytest logging level as Globals.LOG_LEVEL

LOGGER = logging.getLogger(__name__)


class EnableFailureInjection(ABC):

    @abstractmethod
    def enable_checksum_failure(self):
        pass

    @abstractmethod
    def enable_data_block_corruption(self):
        pass

    @abstractmethod
    def enable_meta_data_failure(self):
        pass

    @abstractmethod
    def enable_s3_meta_data_failure(self):
        pass


class S3FailureInjection(EnableFailureInjection):

    def __init__(self, cmn_cfg):
        """Initialize connection to Nodes or Pods."""
        self.cmn_cfg = cmn_cfg
        self.nodes = cmn_cfg["nodes"]
        self.master_node_list = list()
        for node in self.nodes:
            if node["node_type"].lower() == "master":
                node_obj = LogicalNode(hostname=node["hostname"],
                                       username=node["username"],
                                       password=node["password"])
                self.master_node_list.append(node_obj)

    def restart_s3_servers(self):
        """
        Restart S3 server of all the pods to reset the faults injected
        """
        try:
            resp = self.master_node_list[0].get_pod_name()
            if resp[0]:
                data_pods = resp[1]
                LOGGER.debug("Data Pods : %s", data_pods)
                for pod_name in data_pods:
                    s3_containers = self.master_node_list[0].get_container_of_pod(pod_name,
                                                                                  "cortx-s3-0")
                    LOGGER.debug("S3 Container : %s",s3_containers)
                    for s3_cont in s3_containers:
                        LOGGER.info("Restarting service in pod %s container %s",pod_name,s3_cont)
                        cmd = f"kubectl exec -it {pod_name} -c {s3_cont} -- pkill -9 s3server"
                        resp = self.master_node_list[0].execute_cmd(cmd=cmd,read_lines=True)
                        LOGGER.debug("Resp :",resp)
                return True
            else:
                return False
        except IOError as ex:
            LOGGER.error("Exception: %s",ex)
            return False

    def set_fault_injection(self,flag: bool):
        """
        Enable/Disable Fault Injections.(Controls the fault injection flag)
        param: flag:  If true- enable FI
                      False- disable FI
        """
        fi_op = "enable" if flag else "disable"
        try:
            LOGGER.info("%s fault injection",fi_op)
            local_path = DI_CFG["fi_k8s"]
            remote_path = DI_CFG["remote_fi_k8s"]
            cmd = f"chmod +x {remote_path} && ./{remote_path} {fi_op}"
            self.master_node_list[0].copy_file_to_remote(local_path=local_path,
                                                         remote_path=remote_path)
            resp = self.master_node_list[0].execute_cmd(cmd=cmd, read_lines=True)
            LOGGER.debug("Resp: %s", resp)
            time.sleep(30)
            return True, resp
        except IOError as ex:
            LOGGER.error("Exception :%s", ex)
            return False, ex

    def set_fault(self, fault_type: str, fault_operation: bool):
        """
        sets the following faults
        S3_FI_FLAG_DC_ON_WRITE = 'di_data_corrupted_on_write'
        S3_FI_FLAG_CSUM_CORRUPT = 'di_obj_md5_corrupted'

        :param fault_type: Type of fault to be injected
               ex: S3_FI_FLAG_DC_ON_WRITE
        :param fault_operation: enable is true and disable is false
        :return boolean :true :if successful
                          false: if error
        """
        try:
            fault_op = commands.FI_ENABLE if fault_operation else commands.FI_DISABLE
            data_pods = self.master_node_list[0].get_all_pods_and_ips(POD_NAME_PREFIX)
            LOGGER.debug("Data pods and ips : %s",data_pods)
            for pod_name, pod_ip in data_pods.items():
                s3_containers = self.master_node_list[0].get_container_of_pod(pod_name,
                                                                              "cortx-s3-0")
                s3_instance = len(s3_containers)
                for each in range(0, s3_instance):
                    s3_port = 28070 + each + 1
                    cmd = f'curl -X PUT -H "x-seagate-faultinjection: {fault_op},always,{fault_type},0,0" {pod_ip}:{s3_port}'
                    resp = self.master_node_list[0].execute_cmd(cmd=cmd, read_lines=True)
                    LOGGER.debug("resp : %s", resp)
            return True
        except IOError as ex:
            LOGGER.error("Exception: %s", ex)
            return False

    def enable_checksum_failure(self):
        raise NotImplementedError('S3 team does not support checksum failure')

    def enable_data_block_corruption(self):
        resp = self.set_fault(fault_type=commands.S3_FI_FLAG_DC_ON_WRITE, fault_operation=True)
        return resp

    def enable_meta_data_failure(self):
        raise NotImplementedError('Motr team does not support Meta data failure')

    def enable_s3_meta_data_failure(self):
        raise NotImplementedError('Motr team does not support Meta data failure')


class MotrFailureInjectionAdapter(EnableFailureInjection):
    """Make this class concrete when DC tool is available."""

    def __init__(self, dc_tool):
        self.dc_tool = dc_tool  # delegates task to DC tool

    def enable_checksum_failure(self):
        raise NotImplementedError('Not Implemented')

    def enable_data_block_corruption(self):
        raise NotImplementedError('Not Implemented')

    def enable_meta_data_failure(self):
        raise NotImplementedError('Not Implemented')

    def enable_s3_meta_data_failure(self):
        raise NotImplementedError('Not Implemented')
