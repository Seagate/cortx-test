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
#

"""Failure Injection adapter which Handles motr emap, checksum, data corruption.
"""
import logging
import time
from abc import ABC, abstractmethod

from commons.constants import POD_NAME_PREFIX
from commons.constants import MOTR_CONTAINER_PREFIX
from commons.constants import PROD_FAMILY_LC as LC
from commons.constants import PROD_FAMILY_LR as LR
from commons.constants import PROD_TYPE_K8S as K8S
from commons.constants import NAMESPACE
from commons.helpers.pods_helper import LogicalNode
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

LOGGER = logging.getLogger(__name__)

FT_CHKSUM = 1
FT_PARITY = 2


class InjectCorruption(ABC):
    """Abstract class to perform failure injection."""

    @abstractmethod
    def inject_checksum_corruption(self):
        """Enable Checksum failure."""
        pass

    @abstractmethod
    def inject_parity_corruption(self):
        """Enable Checksum failure."""
        pass

    @abstractmethod
    def inject_metadata_corruption(self):
        """Enable metadata corruption."""
        pass


class MotrCorruptionAdapter(InjectCorruption):
    """Implements InjectCorruption interface to perform corruption at Motr level."""

    def __init__(self, cmn_cfg):
        """Initialize connection to Nodes or Pods."""
        self.cmn_cfg = cmn_cfg
        self.nodes = cmn_cfg["nodes"]
        self.connections = list()
        self.emap_script  # delegates task to emap script
        self.ctg = None  # Common ThreadGroup connection
        self.master_node_list = list()
        self.worker_node_list = list()
        self.motr_obj = MotrCoreK8s()
        #node_enpts = self.motr_obj.get_cortx_node_endpoints(node)
        if self.cmn_cfg["product_family"] in (LC, LR) and \
                self.cmn_cfg["product_type"] == K8S:
            for node in self.nodes:
                if node["node_type"].lower() == "master":
                    node_obj = LogicalNode(hostname=node["hostname"],
                                           username=node["username"],
                                           password=node["password"])
                    self.master_node_list.append(node_obj)
                else:
                    node_obj = LogicalNode(hostname=node["hostname"],
                                           username=node["username"],
                                           password=node["password"])
                    self.worker_node_list.append(node_obj)

    def close_connections(self):
        """Close connections to target nodes."""
        if self.cmn_cfg["product_family"] in (LR, LC) and \
                self.cmn_cfg["product_type"] == K8S:
            for conn in self.master_node_list + self.worker_node_list:
                if isinstance(conn, LogicalNode):
                    conn.disconnect()

    def get_object_cob_id(self, oid):
        """
        Fetch COB ID from the M0CP trace file.
        :param oid:
        :return: COB ID in FID format to be corrupted
        """
        return ''

    def get_metadata_shard(self, oid):
        """
        Locate metadata shard.
        :param oid:
        :return: COB ID in FID format to be corrupted
        """
        return ''

    def restart_motr_container(self, index):
        """
        Restart Motr container of index and check if it has already restarted.
        :param index:
        :return:
        """
        return False

    def build_emap_command(self, ftype=FT_PARITY):
        if ftype == 1:
            cmd = 'python3 ~/error_injection.py -corrupt_emap 0x200000500000017:0x15' \
                  ' -e 1 -m /etc/cortx/motr/m0d-0x7200000000000001\:0x32/db/o/100000000000000:2a' \
                  ' -parse_size 10485760'
        elif ftype == 1:
            cmd = 'python3 ~/error_injection.py -corrupt_emap 0x200000500000017:0x15' \
                  ' -e 1 -m /etc/cortx/motr/m0d-0x7200000000000001\:0x32/db/o/100000000000000:2a' \
                  ' -parse_size 10485760'
        return cmd

    def inject_fault_k8s(self, fault_type: int):
        """
        Inject fault of type checksum or parity.
        :param fault_type: checksum or parity
        :return boolean :true :if successful
                          false: if error
        """
        try:
            data_pods = self.master_node_list[0].get_all_pods_and_ips(POD_NAME_PREFIX)
            LOGGER.debug("Data pods and ips : %s", data_pods)
            for pod_name, pod_ip in data_pods.items():
                motr_containers = self.master_node_list[0].get_container_of_pod(
                    pod_name, MOTR_CONTAINER_PREFIX)
                motr_instances = len(motr_containers)
                # select 1st motr instance
                retries = 1
                success = False
                while retries > 0:
                    try:
                        resp = self.master_node_list[0].send_k8s_cmd(
                            operation="exec",
                            pod=pod_name,
                            namespace=NAMESPACE,
                            command_suffix=f"-c {motr_containers[0]} -- "
                                           f"{self.build_emap_command(fault_type)}",
                            decode=True)
                        if resp:
                            success = True
                            break
                    except IOError as ex:
                        LOGGER.exception("remaining retrying: %s")
                        retries -= 1
                        time.sleep(2)

                if success:
                    break
            if self.restart_motr_container(0):
                return True
        except IOError as ex:
            LOGGER.exception("Exception occured while injecting emap fault", exc_info=ex)
            return False

    def inject_checksum_corruption(self):
        """Injects data checksum error by providing the DU FID."""
        return self.inject_fault_k8s(FT_CHKSUM)

    def inject_parity_corruption(self):
        """Injects parity checksum error by providing the Parity FID."""
        return self.inject_fault_k8s(FT_PARITY)

    def inject_metadata_corruption(self):
        """Not supported."""
        raise NotImplementedError('Not Implemented')


