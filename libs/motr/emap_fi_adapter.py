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
from typing import AnyStr
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
EMAP_CMD = "python3 ~/error_injection.py"


class EmapCommand:
    """
    It is expected that emap script will grow to complex script with multiple options.
    """

    def __init__(self):
        self.parent_cmd = [EMAP_CMD]
        self.cmd_options = list()
        self.opts = dict()

    def add_option(self, option: AnyStr) -> None:
        self.cmd_options.append(option)

    def build_options(self, **kwargs):
        """ Options significant to emap are as shown below
        -corrupt_emap 0x200000500000017:0x15' \
        -e 1
        -m /etc/cortx/motr/m0d-0x7200000000000001\:0x32/db/o/100000000000000:2a' \
        -parse_size 10485760'
        :returns options string
        """
        self.opts = kwargs
        if self.opts.get("corrupt_emap"):
            # Cob FID of object is specified for corrupt_emap
            option = "-corrupt_emap " + str(self.opts.get("corrupt_emap"))
            self.add_option(option)

        if self.opts.get("list_emap"):
            # Cob FID of object is specified for corrupt_emap
            option = "-list_emap "
            self.add_option(option)

        if self.opts.get("emap_count"):
            # number of checksum corruption instances for parity or data
            option = "-e " + str(self.opts.get("emap_count"))
            self.add_option(option)

        if self.opts.get("metadata_db_path"):
            # Metadata DB path within each motr fid dir as shown below.
            # /etc/cortx/motr/m0d-0x7200000000000001\:0x32/db/o/100000000000000:2a'
            option = "-m " + str(self.opts.get("metadata_db_path"))
            self.add_option(option)

        if self.opts.get("parse_size"):
            # File Size to parse from start offset.
            option = "-parse_size " + str(self.opts.get("parse_size"))
            self.add_option(option)

        return self.cmd_options

    def __str__(self):
        if len(self.cmd_options) == 0:
            return self.parent_cmd[0]
        options_str = " ".join(map(str, self.cmd_options))
        return " ".join((self.parent_cmd[0], options_str))


class EmapCommandBuilder:
    """
    The Concrete Emap command Builder class provide
    specific implementations of the emap script's command building steps.
    """

    def __init__(self) -> None:
        """
        A blank Emap Command object, which is
        used to build options.
        """
        self._command = EmapCommand()
        self.reset()

    def reset(self) -> None:
        """
        You can make EmapCommandBuilder wait for an explicit reset call from the
        client code before disposing of the previous command.
        """
        self._command = EmapCommand()

    def build(self, **kwargs) -> EmapCommand:
        """
        Constructs the concrete command with provided options or arguments.
        """
        cmd = self._command
        cmd.build_options(**kwargs)
        return cmd


class InjectCorruption(ABC):
    """Abstract class to perform failure injection."""

    @abstractmethod
    def inject_checksum_corruption(self, oid: list):
        """Enable Checksum failure."""
        pass

    @abstractmethod
    def inject_parity_corruption(self, oid: list):
        """Enable Checksum failure."""
        pass

    @abstractmethod
    def inject_metadata_corruption(self, oid: list):
        """Enable metadata corruption."""
        pass


class MotrCorruptionAdapter(InjectCorruption):
    """Implements InjectCorruption interface to perform corruption at Motr level."""

    def __init__(self, cmn_cfg, oid: str):
        """Initialize connection to Nodes or Pods."""
        self.cmn_cfg = cmn_cfg
        self.nodes = cmn_cfg["nodes"]
        self.connections = list()
        self.oid = oid  # deals with a single oid at a moment
        self.master_node_list = list()
        self.worker_node_list = list()
        self.motr_obj = MotrCoreK8s()
        if self.cmn_cfg["product_family"] in (LC, LR) and self.cmn_cfg["product_type"] == K8S:
            for node in self.nodes:
                if node["node_type"].lower() == "master":
                    node_obj = LogicalNode(
                        hostname=node["hostname"],
                        username=node["username"],
                        password=node["password"],
                    )
                    self.master_node_list.append(node_obj)
                else:
                    node_obj = LogicalNode(
                        hostname=node["hostname"],
                        username=node["username"],
                        password=node["password"],
                    )
                    self.worker_node_list.append(node_obj)

    def close_connections(self):
        """Close connections to target nodes."""
        if self.cmn_cfg["product_family"] in (LR, LC) and self.cmn_cfg["product_type"] == K8S:
            for conn in self.master_node_list + self.worker_node_list:
                if isinstance(conn, LogicalNode):
                    conn.disconnect()

    def get_object_cob_id(self, oid, dtype):
        """
        Fetch COB ID from the M0CP trace file.
        : param oid:
        : param dtype:
        : return: COB ID in FID format to be corrupted
        """
        return ""

    def get_metadata_device(self, oid):
        """
        Locate metadata device from solution.yaml.
        :param oid:
        :return: COB ID in FID format to be corrupted
        """
        # Todo - read from solution.yaml
        return "/dev/sdc"

    def restart_motr_container(self, index):
        """
        Restart Motr container of index and check if it has already restarted.
        :param index:
        :return:
        """
        return False

    def build_emap_command(self, oid, ftype=FT_PARITY):
        selected_shard = self.get_metadata_device(self.oid)
        cob_id = self.get_object_cob_id(oid, dtype=ftype)
        emap_bldr = EmapCommandBuilder()
        kwargs = dict(
                      list_emap="list_emap",
                      corrupt_emap=cob_id,
                      parse_size=10485760,
                      emap_count=1,
                      metadata_db_path=selected_shard
        )
        cmd = EmapCommandBuilder.build(emap_bldr, **kwargs)
        return cmd

    def inject_fault_k8s(self, oid: list, fault_type: int):
        """
        Inject fault of type checksum or parity.
        :param oid object id list
        :param fault_type: checksum or parity
        :return boolean :true :if successful
                          false: if error
        """
        try:
            # data_pods = self.master_node_list[0].get_all_pods_and_ips(POD_NAME_PREFIX)
            data_pods = self.master_node_list[0].get_all_pods(POD_NAME_PREFIX)
            for index, pod_name in enumerate(data_pods):
                motr_containers = self.master_node_list[0].get_container_of_pod(
                    pod_name, MOTR_CONTAINER_PREFIX
                )
                # motr_instances = len(motr_containers)  # Todo here and also check for copy to 002
                # select 1st motr pod
                logging.debug(f"pod_name = {pod_name}")
                if pod_name == "cortx-data-g0-0":
                    logging.debug(f"Inside.......... pod_name = {pod_name}")
                    retries = 1
                    success = False
                    while retries > 0:
                        try:
                            resp = self.master_node_list[0].send_k8s_cmd(
                                operation="exec",
                                pod=pod_name,
                                namespace=NAMESPACE,
                                command_suffix=f"-c {motr_containers[0]} -- "
                                f"{self.build_emap_command(oid, fault_type)}",
                                decode=True,
                            )
                            logging.debug(f"resp = {resp}")
                            if resp:
                                success = True
                                break
                            retries -= 1
                        except IOError as ex:
                            LOGGER.exception("remaining retrying: %s")
                            retries -= 1
                            time.sleep(2)
                    if success:
                        break
            # Todo:
            # if self.restart_motr_container(0):
            #     return True
        except IOError as ex:
            LOGGER.exception("Exception occurred while injecting emap fault", exc_info=ex)
            return False

    def inject_checksum_corruption(self, oid: list):
        """Injects data checksum error by providing the DU FID."""
        return self.inject_fault_k8s(oid, FT_CHKSUM)

    def inject_parity_corruption(self,oid: list):
        """Injects parity checksum error by providing the Parity FID."""
        return self.inject_fault_k8s(oid, FT_PARITY)

    def inject_metadata_corruption(self, oid: list):
        """Not supported."""
        raise NotImplementedError("Not Implemented")
