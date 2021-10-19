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
import os
import logging
import traceback
from abc import ABC, abstractmethod
from fabric import Connection
from fabric import Config
from fabric import ThreadingGroup, SerialGroup
from fabric import runners
from fabric.exceptions import GroupException

from commons.helpers.node_helper import Node
from commons import Globals
from commons.constants import PROD_FAMILY_LC
from commons.constants import PROD_FAMILY_LR
from commons.constants import PROD_TYPE_K8S
from commons.constants import PROD_TYPE_NODE
from commons import commands
from commons import params
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
        self.connections = list()
        self._connections = list() # Fabric connections
        self.ctg = None # Common ThreadGroup connection
        hostnames = list()
        if self.cmn_cfg["product_family"] == PROD_FAMILY_LR and \
                self.cmn_cfg["product_type"] == PROD_TYPE_NODE:
            for node in self.nodes:
                node_obj = Node(hostname=node["hostname"],
                                username=node["username"],
                                password=node["password"])
                node_obj.connect()
                self.connections.append(node_obj)
                hostnames.append(node["hostname"])
        elif self.cmn_cfg["product_family"] == PROD_FAMILY_LC and \
                self.cmn_cfg["product_type"] == PROD_TYPE_K8S:
            LOGGER.critical("Product family: LC")
            # TODO: Add LC related calls
        nodes_str = ','.join(hostnames)
        self.nodes_str = 'NODES="{}"'.format(nodes_str)

    def create_nodes_connection(self):
        if self.cmn_cfg["product_family"] == PROD_FAMILY_LR and \
                self.cmn_cfg["product_type"] == PROD_TYPE_NODE:
            self._connections = [Connection(node["hostname"], user=node["username"],
                                           connect_kwargs={'password': node["password"]},
                                           config=Config(overrides={
                                               'sudo': {'password': node["password"]}}))
                                for node in self.nodes]
            self.ctg = ThreadingGroup.from_connections(self._connections)
        elif self.cmn_cfg["product_family"] == PROD_FAMILY_LC:
            LOGGER.critical("Product family: LC")
            # TODO: Add LC related calls

    def _inject_fault(self, fault_type=None, s3_instances_per_node=1):
        """Injects fault by directly connecting to all Nodes and using REST API.
        Works for s3 server instance = 1
        TODO: Check if output is needed
        """
        stdout = list()
        status = list()
        enable = commands.FI_ENABLE
        f_type = fault_type if not fault_type else commands.DI_DATA_CORRUPT_ON_WRITE
        start_port = commands.S3_SRV_START_PORT
        if s3_instances_per_node == 1:
            h_p = f'localhost:{start_port}'
            fault_cmd = (f'curl -X PUT -H "x-seagate-faultinjection: {enable}'
                         f',{f_type},0,0'
                         f'" {h_p}'
                         )
            for conn in self._connections:
                try:
                    out = conn.run(fault_cmd, pty=False).stdout
                    stdout.append(out)
                except Exception as fault:
                    LOGGER.warning("Connections to node was broken. Retrying...")
                    out = conn.run(fault_cmd, pty=False).stdout
                    stdout.append(out)
                status.append(True)
            return status, stdout
        elif s3_instances_per_node > 1:
            for conn in self._connections:
                start_port = commands.S3_SRV_START_PORT
                for ix in range(s3_instances_per_node):
                    h_p = f'localhost:{start_port}'
                    fault_cmd = (f'curl -X PUT -H "x-seagate-faultinjection: {enable}'
                                 f',{f_type},0,0'
                                 f'" {h_p}'
                                 )
                    try:
                        out = conn.run(fault_cmd, pty=False).stdout
                        stdout.append(out)
                    except Exception as fault:
                        LOGGER.warning("Connections to node was broken %s. Retrying..." % fault)
                        out = conn.run(fault_cmd, pty=False).stdout
                        stdout.append(out)
                    status.append(True)
                    start_port += 1
            return status, stdout

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
        s3_instances_per_node = params.S3_INSTANCES_PER_NODE
        fault_op = commands.FI_ENABLE if fault_operation else commands.FI_DISABLE
        if use_script:
            # todo requires pdsh
            cmd = f'NINST={s3_instances_per_node} {self.nodes_str} FIS="{fault_type}" ' \
                  f'sh {DI_CFG["fault_injection_script"]} {fault_op}'
            result = self.connections[0].execute_cmd(cmd)

            if "Host key verification failed" not in result or "ssh exited" not in result \
                    or "pdsh: command not found" not in result or "Permission denied" not in result:
                LOGGER.info(f"Fault {fault_type} : {fault_op}")
                return True
            else:
                LOGGER.error(f"Error during Fault {fault_type} : {fault_op}")
                LOGGER.error(result)
                return False
        else:
            self._inject_fault(fault_type=fault_type, fault_operation=fault_op,
                               s3_instances_per_node=s3_instances_per_node)

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

    def close_connections(self):
        if self.cmn_cfg["product_family"] == PROD_FAMILY_LR and \
                self.cmn_cfg["product_type"] == PROD_TYPE_NODE:
            for conn in self.connections:
                if isinstance(conn, Node):
                    conn.disconnect()

        elif self.cmn_cfg["product_family"] == PROD_FAMILY_LC and \
                self.cmn_cfg["product_type"] == PROD_TYPE_K8S:
            LOGGER.critical("Not supported right now")


class DIFault:
    def __init__(self,
                 primary_node=CM_CFG["host"],
                 nodes=CM_CFG["nodes"],
                 username=CM_CFG["username"],
                 password=CM_CFG["password"]
                 ):
        """This method initializes members of DIFeatureControlLib
        :param primary_node: hostname of primary name
        :type primary_node: str
        :param nodes: host name of all nodes
        :type nodes: list
        :param username: username
        :type username: str
        :param password: password
        :type password: str
        """
        self.primary_node = primary_node
        self.nodes = nodes
        self.username = username
        self.password = password

    def restart_s3_services(self):
        LOGGER.info("Restarting the S3 server")
        resp = S3H_OBJ.restart_s3server_processes(
        self.host_ip, self.uname, self.passwd)
        for each in self.nodes:
            ret_stat, error = utils_obj.restart_s3server_processes(each)
            if not ret_stat:
                logger.error("Error during restarting S3 server")
                logger.error(error)
                return False

        logger.info("Check all S3 services are online")
        ret_stat, error = utils_obj.check_s3services_online()
        if not ret_stat:
            logger.error("Error: Not all S3 services are online")
            logger.error(error)
            return False

        return True

    def set_fi_framework(self, flag):
        """
        Set Fault injection framework as the input flag
        :param flag: boolean : True : Enable the framework
                               False: Disable the framework
        :return: Boolean : True if successful
                           False if error
        """
        operation = "enable" if flag else "disable"
        logger.info(f"Set Fault Injection Framework : {operation}")

        fi_framework_cmd = f'{nodes_str} sh {DI_CFG["framework_startup_script"]} {operation}'
        result = utils_obj.run_cmd(fi_framework_cmd)

        if "Host key verification failed" not in result or "ssh exited" not in result \
                or "pdsh: command not found" not in result or "Permission denied" not in result:
            logger.info(f"Fault Injection Framework {operation}d")
        else:
            logger.error(f"Error during Fault Injection Framework {operation}")
            logger.error(result)
            return False

        if not self.restart_s3_services():
            return False

        return True

    def verify_fi_framework(self):
        """
        Verify if Fault Injection framework is enabled/disabled
        :return:Boolean : True if no error
                        Boolean: True : if fault injection framework enabled
                                 False: if fault injection framework disabled
                Boolean : False if error
                        Error string
        """
        fault_str = "--fault_injection true"
        and_flag = True
        or_flag = False
        flag_value = None

        for each in self.nodes:
            logger.info(f"Validating fault injection enabled on {each}")
            if os.path.exists(temp_s3startsystem):
                os.remove(temp_s3startsystem)
            res = utils_obj.copy_s3server_file(DI_CFG["fi_framework_file"], temp_s3startsystem,
                                               each, self.username, self.password)
            if res[0]:
                with open(temp_s3startsystem) as fp:
                    temp = True if fault_str in fp.read() else False
                    logger.info(f"Fault Injection enabled : {temp}")
                and_flag = and_flag and temp
                or_flag = or_flag or temp
            else:
                return False, "Error while reading remote file on {each}"

        if and_flag:
            flag_value = True
        if or_flag is False:
            flag_value = False

        if flag_value is None:
            logger.error(f"Flaut Injection flag on both the nodes is not equal."
                         f"Check {DI_CFG['fi_framework_file']}")
            return False, 'f"Flaut Injection flag on both the nodes is not equal."'
        else:
            return True, flag_value

    def set_fault(self, fault_type, fault_operation):
        """
        :param fault_type: Type of fault to be set
               ex: di_data_corrupted_on_write/di_data_corrupted_on_read
        :param fault_operation:boolean : enable : true
                                         disable : false
        :return: boolean :true :if successful
                          false: if error
        """

        fault_op = "enable" if fault_operation else "disable"
        cmd = f'NINST=11 {nodes_str} FIS="{fault_type}" sh {DI_CFG["fault_injection_script"]} {fault_op}'
        result = utils_obj.run_cmd(cmd)

        if "Host key verification failed" not in result or "ssh exited" not in result \
                or "pdsh: command not found" not in result or "Permission denied" not in result:
            logger.info(f"Fault {fault_type} : {fault_op}")
            return True
        else:
            logger.error(f"Error during Fault {fault_type} : {fault_op}")
            logger.error(result)
            return False




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
