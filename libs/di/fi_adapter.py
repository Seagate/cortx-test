# -*- coding: utf-8 -*-
# !/usr/bin/python
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
#

"""Failure Injection adapter. Handles S3 FI and Motr FI.
"""
import logging
import time
from abc import ABC, abstractmethod

from fabric import Config
from fabric import Connection
from fabric import ThreadingGroup

from commons import commands
from commons import params
from commons.constants import POD_NAME_PREFIX
from commons.constants import PROD_FAMILY_LC
from commons.constants import PROD_FAMILY_LR
from commons.constants import PROD_TYPE_K8S
from commons.constants import PROD_TYPE_NODE
from commons.helpers.node_helper import Node
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
        self.connections = list()
        self._connections = list()  # Fabric connections
        self.ctg = None  # Common ThreadGroup connection
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
            self.master_node_list = list()
            for node in self.nodes:
                if node["node_type"].lower() == "master":
                    node_obj = LogicalNode(hostname=node["hostname"],
                                           username=node["username"],
                                           password=node["password"])
                    self.master_node_list.append(node_obj)

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
            pass

    def _inject_fault(self, fault_type=None, fault_operation='enable', s3_instances_per_node=1):
        """Injects fault by directly connecting to all Nodes and using REST API.
        Works for s3 server instance = 1
        TODO: Check if output is needed
        """
        stdout = list()
        status = list()
        f_type = fault_type if not fault_type else commands.DI_DATA_CORRUPT_ON_WRITE
        start_port = commands.S3_SRV_START_PORT
        if s3_instances_per_node == 1:
            h_p = f'localhost:{start_port}'
            fault_cmd = (f'curl -X PUT -H "x-seagate-faultinjection: {fault_operation}'
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
                for index in range(s3_instances_per_node):
                    h_p = f'localhost:{start_port + index}'
                    fault_cmd = (f'curl -X PUT -H "x-seagate-faultinjection: {fault_operation}'
                                 f',{f_type},0,0'
                                 f'" {h_p}'
                                 )
                    try:
                        out = conn.run(fault_cmd, pty=False).stdout
                        stdout.append(out)
                    except Exception as fault:
                        LOGGER.warning("Connections to node was broken %s. Retrying...", fault)
                        out = conn.run(fault_cmd, pty=False).stdout
                        stdout.append(out)
                    status.append(True)
                    start_port += 1
            return status, stdout
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
                LOGGER.info("Fault %s : %s", fault_type, fault_op)
                return True
            else:
                LOGGER.error("Error during Fault %s : %s", fault_type, fault_op)
                LOGGER.error(result)
                return False
        else:
            status, stdout = self._inject_fault(fault_type=fault_type, fault_operation=fault_op,
                                                s3_instances_per_node=s3_instances_per_node)
            return True if all(status) else False

    # pylint: disable=too-many-nested-blocks
    def _set_fault_k8s(self, fault_type: str, fault_operation: bool):
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
            LOGGER.debug("Data pods and ips : %s", data_pods)
            for pod_name, pod_ip in data_pods.items():
                s3_containers = self.master_node_list[0].get_container_of_pod(pod_name,
                                                                              "cortx-s3-0")
                s3_instance = len(s3_containers)
                for each in range(0, s3_instance):
                    retries = 3
                    s3_port = 28070 + each + 1
                    cmd = f'curl -X PUT -H "x-seagate-faultinjection: ' \
                          f'{fault_op},always,{fault_type},0,0" {pod_ip}:{s3_port}'
                    while retries > 0:
                        try:
                            resp = self.master_node_list[0].execute_cmd(cmd=cmd, read_lines=True)
                            LOGGER.debug("http server resp : %s", resp)
                            if "not allowed against this resource" in str(resp):
                                return False
                            if not resp:
                                break
                        except IOError as ex:
                            LOGGER.error("Exception: %s", ex)
                            LOGGER.error("remaining retrying: %s", retries)
                            retries -= 1
                            time.sleep(2)
                    if retries == 0:
                        return False
            return True
        except IOError as ex:
            LOGGER.error("Exception: %s", ex)
            return False

    def set_fault_injection(self, flag: bool):
        """
        Enable/Disable Fault Injections.(Controls the fault injection flag)
        param: flag:  If true- enable FI
                      False- disable FI
        """
        fi_op = "enable" if flag else "disable"

        if self.cmn_cfg["product_family"] == PROD_FAMILY_LR and \
                self.cmn_cfg["product_type"] == PROD_TYPE_NODE:
            raise NotImplementedError('Enable fault injection not implemented for LR')
        elif self.cmn_cfg["product_family"] == PROD_FAMILY_LC and \
                self.cmn_cfg["product_type"] == PROD_TYPE_K8S:
            try:
                LOGGER.info("%s fault injection", fi_op)
                local_path = DI_CFG["fi_k8s"]
                remote_path = DI_CFG["remote_fi_k8s"]
                cmd = f"chmod +x {remote_path} && ./{remote_path} {fi_op}"
                self.master_node_list[0].copy_file_to_remote(local_path=local_path,
                                                             remote_path=remote_path)
                resp = self.master_node_list[0].execute_cmd(cmd=cmd, read_lines=True)
                LOGGER.debug("Set S3 Srv with Fault Injection Resp: %s", resp)
                time.sleep(30)
                return True, resp
            except IOError as ex:
                LOGGER.error("Exception :%s", ex)
                return False, ex

    def enable_checksum_failure(self):
        raise NotImplementedError('S3 team does not support checksum failure')

    def enable_data_block_corruption(self) -> bool:
        fault_type = commands.S3_FI_FLAG_DC_ON_WRITE
        status = False
        if self.cmn_cfg["product_family"] == PROD_FAMILY_LR and \
                self.cmn_cfg["product_type"] == PROD_TYPE_NODE:
            status, stout = self._set_fault(fault_type=fault_type, fault_operation=True,
                                            use_script=False)
            all(status)
        elif self.cmn_cfg["product_family"] == PROD_FAMILY_LC and \
                self.cmn_cfg["product_type"] == PROD_TYPE_K8S:
            status = self._set_fault_k8s(fault_type=fault_type, fault_operation=True)
        return status

    def disable_data_block_corruption(self) -> bool:
        """
        disable data block corruption
        output: Bool
        """
        fault_type = commands.S3_FI_FLAG_DC_ON_WRITE
        status = False
        if self.cmn_cfg["product_family"] == PROD_FAMILY_LR and \
                self.cmn_cfg["product_type"] == PROD_TYPE_NODE:
            status, stout = self._set_fault(fault_type=fault_type, fault_operation=False,
                                            use_script=False)
            LOGGER.debug("status: %s  stout: %s", status, stout)
            all(status)
        elif self.cmn_cfg["product_family"] == PROD_FAMILY_LC and \
                self.cmn_cfg["product_type"] == PROD_TYPE_K8S:
            status = self._set_fault_k8s(fault_type=fault_type, fault_operation=False)
        return status

    def enable_data_block_corruption_using_node_script(self):
        fault_type = commands.S3_FI_FLAG_DC_ON_WRITE
        status = False
        if self.cmn_cfg["product_family"] == PROD_FAMILY_LR and \
                self.cmn_cfg["product_type"] == PROD_TYPE_NODE:
            status = self._set_fault(fault_type=fault_type, fault_operation=True, use_script=True)
        elif self.cmn_cfg["product_family"] == PROD_FAMILY_LC and \
                self.cmn_cfg["product_type"] == PROD_TYPE_K8S:
            raise NotImplementedError('Not supported for LC')
        return status

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
            pass


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
