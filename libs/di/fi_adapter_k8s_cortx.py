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
from abc import ABC, abstractmethod

from commons import commands
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


    def _restart_s3_servers(self):
        """
        Restart S3 server of all the pods to reset the faults injected
        """

    def _enable_fi(self):
        """
        Enable Fault Injection (Restarts S3 server with fault_injection flag)
        Note: Check POD status online before and after this call
        """
        try:
            LOGGER.info("Enabling Fault Injection : ")
            local_path = DI_CFG["enable_fi_k8s"]
            remote_path = DI_CFG["remote_enable_fi_k8s"]
            cmd = f"chmod +x {remote_path} && sh {remote_path}"
            self.master_node_list[0].copy_file_to_remote(local_path=local_path, remote_path=remote_path)
            resp = self.master_node_list[0].execute_cmd(cmd=cmd,read_lines=True)
            LOGGER.debug("Resp: %s",resp)
            return True,resp
        except IOError as ex:
            LOGGER.error("Exception :%s",ex)
            return False,ex

    def _disable_fi(self):
        """
        Disable Fault Injection (Restarts S3 server without fault_injection flag)
        Note: Check POD status online before and after this call
        """
        try:
            LOGGER.info("Disabling Fault Injection : ")
            local_path = DI_CFG["disable_fi_k8s"]
            remote_path = DI_CFG["remote_disable_fi_k8s"]
            cmd = f"chmod +x {remote_path} && sh {remote_path}"
            self.master_node_list[0].copy_file_to_remote(local_path=local_path, remote_path=remote_path)
            resp = self.master_node_list[0].execute_cmd(cmd=cmd,read_lines=True)
            LOGGER.debug("Resp: %s",resp)
            return True,resp
        except IOError as ex:
            LOGGER.error("Exception :%s",ex)
            return False,ex

    def _set_fault(self, fault_type: str, fault_operation: bool, use_script: bool = False):
        """
        sets the following faults
        S3_FI_FLAG_DC_ON_WRITE = 'di_data_corrupted_on_write'
        S3_FI_FLAG_DC_ON_READ = 'di_data_corrupted_on_read'
        S3_FI_FLAG_CSUM_CORRUPT = 'di_obj_md5_corrupted'

        :param use_script: use shell script
        :param fault_type: Type of fault to be injected
               ex: S3_FI_FLAG_DC_ON_WRITE
        :param fault_operation: enable is true and disable is false
        :return boolean :true :if successful
                          false: if error
        """

        fault_op = commands.FI_ENABLE if fault_operation else commands.FI_DISABLE
        #Retrieve all the data pods
        resp = self.master_node_list[0].get_pod_name()
        if not resp:
            return resp
        data_pods = resp[1]
        #Enable fault for each of the data pods
        for pod in data_pods:
            s3_instance = 3
            pod_ip = "abc"
            for each in s3_instance:
                cmd = f'curl -X PUT -H "x-seagate-faultinjection: {fault_op},always,{fault_type},0,0" <pod-ip>:28071'


    def enable_checksum_failure(self):
        raise NotImplementedError('S3 team does not support checksum failure')

    def enable_data_block_corruption(self):
        fault_type = commands.S3_FI_FLAG_DC_ON_WRITE
        status, stout = self._set_fault(fault_type=fault_type, fault_operation=True, use_script=False)
        all(status)

    def enable_data_block_corruption_using_node_script(self):
        fault_type = commands.S3_FI_FLAG_DC_ON_WRITE
        ret = self._set_fault(fault_type=fault_type, fault_operation=True, use_script=True)
        assert ret == True

    def enable_meta_data_failure(self):
        raise NotImplementedError('Motr team does not support Meta data failure')

    def enable_s3_meta_data_failure(self):
        raise NotImplementedError('Motr team does not support Meta data failure')

class MotrFailureInjectionAdapter(EnableFailureInjection):
    """Make this class concrete when DC tool is available."""
    def __init__(self, dc_tool):
        self.dc_tool = dc_tool # delegates task to DC tool

    def enable_checksum_failure(self):
        raise NotImplementedError('Not Implemented')

    def enable_data_block_corruption(self):
        raise NotImplementedError('Not Implemented')

    def enable_meta_data_failure(self):
        raise NotImplementedError('Not Implemented')

    def enable_s3_meta_data_failure(self):
        raise NotImplementedError('Not Implemented')
