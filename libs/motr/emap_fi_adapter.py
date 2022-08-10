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
import os
import secrets
import time
from abc import ABC, abstractmethod
from string import Template
from typing import AnyStr

import yaml

from commons.constants import POD_NAME_PREFIX
from commons.constants import MOTR_CONTAINER_PREFIX
from commons.constants import PROD_FAMILY_LC as LC
from commons.constants import PROD_FAMILY_LR as LR
from commons.constants import PROD_TYPE_K8S as K8S
from commons.constants import CLUSTER_YAML_PATH
from commons.constants import LOCAL_CLS_YAML_PATH
from commons.constants import NAMESPACE
from commons.constants import CONTAINER_PATH
from commons.constants import CLUSTER_YAML
from commons.constants import PARSE_SIZE
from commons import commands as common_cmd
from commons.helpers.pods_helper import LogicalNode
from libs.motr.motr_core_k8s_lib import MotrCoreK8s

LOGGER = logging.getLogger(__name__)

FT_CHKSUM = 1
FT_PARITY = 2
EMAP_CMD = 'python3 ~/error_injection.py'


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
        if self.opts.get('list_emap'):
            # Cob FID of object is specified for corrupt_emap
            option = "-list_emap "
            self.add_option(option)
        if self.opts.get('corrupt_emap'):
            # Cob FID of object is specified for corrupt_emap
            option = "-corrupt_emap " + str(self.opts.get('corrupt_emap'))
            self.add_option(option)

        if self.opts.get('emap_count'):
            # number of checksum corruption instances for parity or data
            option = "-e " + str(self.opts.get('emap_count'))
            self.add_option(option)

        if self.opts.get('metadata_db_path'):
            # Metadata DB path within each motr fid dir as shown below.
            # /etc/cortx/motr/m0d-0x7200000000000001\:0x32/db/o/100000000000000:2a'
            option = "-m " + str(self.opts.get('metadata_db_path'))
            self.add_option(option)

        if self.opts.get('parse_size'):
            # File Size to parse from start offset.
            option = "-parse_size " + str(self.opts.get('parse_size'))
            self.add_option(option)

        return self.cmd_options

    def __str__(self):
        if len(self.cmd_options) == 0:
            return self.parent_cmd
        options_str = ' '.join(map(str, self.cmd_options))
        return ' '.join((self.parent_cmd, options_str))


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
        cmd.build_options(kwargs)
        return cmd


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

    def __init__(self, cmn_cfg, oid):
        """Initialize connection to Nodes or Pods."""
        self.cmn_cfg = cmn_cfg
        self.nodes = cmn_cfg["nodes"]
        self.connections = list()
        self.oid = oid  # deals with a single oid at a moment
        self.master_node_list = list()
        self.worker_node_list = list()
        self.motr_obj = MotrCoreK8s()
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

    def get_object_cob_id(self, oid, dtype):
        """
        Fetch COB ID from the M0CP trace file.
        :param oid:
        :param dtype:
        :return: COB ID in FID format to be corrupted
        """
        return ''

    # pylint: disable-msg=too-many-locals
    def get_object_gob_id(self, metadata_device, parse_size=PARSE_SIZE, fid: dict = None):
        """
        Fetch COB ID from the M0CP trace file.
        :param metadata_device:
        :param parse_size:
        :param fid: dict of object id of data and parity block
        :return: FID to be corrupted
        """
        pod_list = self.master_node_list[0].get_all_pods(POD_NAME_PREFIX)
        LOGGER.debug("pod list is %s", pod_list)
        data_fid_list = []
        parity_fid_list = []
        data_checksum_list = []
        parity_checksum_list = []
        for key, value in fid.items():
            if "DATA" in key:  # fetch the value from dict for data block
                fid_val = value[7:16]
                data_fid_list.append(fid_val)
            else:  # fetch the value from dict for parity block
                fid_val = value[7:16]
                parity_fid_list.append(fid_val)
        # Iterate over data pods to copy the error_injection.py script on motr container
        for pod in pod_list:
            result = self.master_node_list[0].copy_file_to_container(
                "error_injection.py", pod, CONTAINER_PATH, MOTR_CONTAINER_PREFIX + "-001")
            if not result:
                raise FileNotFoundError
            # Run script to list emap and dump the output to the file
            cmd = Template(common_cmd.EMAP_LIST).substitute(path=metadata_device, size=parse_size,
                                                            file=f"{pod}-emap_list.txt")
            self.master_node_list[0].send_k8s_cmd(
                operation="exec", pod=pod, namespace=NAMESPACE,
                command_suffix=f"-c {MOTR_CONTAINER_PREFIX}-001 "
                               f"-- {cmd}", decode=True)
            data_fid_list = [*set(data_fid_list)]
            parity_fid_list = [*set(parity_fid_list)]
            LOGGER.debug("lists of data_fid_list, parity_fid_list %s \n %s", data_fid_list,
                         parity_fid_list)
            # Fetch the target fid from emap list output captured in file while running
            # emap list on motr container
            for data_fid in data_fid_list:
                cmd = common_cmd.FETCH_ID_EMAP.format(
                    f"{pod}-emap_list.txt", data_fid)
                d_resp = self.master_node_list[0].execute_cmd(cmd)
                d_resp = d_resp.decode('UTF-8').strip(",\n")  # strip the resp and make it readable
                if d_resp:
                    LOGGER.debug("gob data entity %s", d_resp)
                    data_checksum_list.append(d_resp)
            for parity_fid in parity_fid_list:
                cmd = common_cmd.FETCH_ID_EMAP.format(
                    f"{pod}-emap_list.txt", parity_fid)
                p_resp = self.master_node_list[0].execute_cmd(cmd)
                p_resp = p_resp.decode('UTF-8').strip(",\n")  # strip the resp and make it readable
                if p_resp:
                    parity_checksum_list.append(p_resp)
        LOGGER.debug("gob data %s", data_checksum_list)
        LOGGER.debug("gob Parity %s", parity_checksum_list)
        return data_checksum_list, parity_checksum_list

    @staticmethod
    def get_metadata_shard(master_node_obj: LogicalNode):
        """
        Locate metadata shard.
        :param master_node_obj: master node obj
        :return: COB ID in FID format to be corrupted
        """
        metadata_device = ''
        pod_list = master_node_obj.get_all_pods(pod_prefix=POD_NAME_PREFIX)
        pod_name = secrets.choice(pod_list)
        cmd = "cat " + CLUSTER_YAML_PATH + " > " + LOCAL_CLS_YAML_PATH
        # Copy from pod to master node
        conf_cp = common_cmd.K8S_POD_INTERACTIVE_CMD.format(pod_name, cmd)
        try:
            resp_node = master_node_obj.execute_cmd(cmd=conf_cp, read_lines=False)
        except IOError as error:
            LOGGER.exception("Error: Not able to get cluster yaml file")
            return False, error
        if not resp_node:
            # Copy from master node to Client machine
            master_node_obj.copy_file_to_local(LOCAL_CLS_YAML_PATH, CLUSTER_YAML)
            # Read the yaml file to fetch metadata device path.
            try:
                with open(CLUSTER_YAML, "r", encoding="utf-8") as file_data:
                    data = yaml.safe_load(file_data)
            except IOError as error:
                LOGGER.exception("Error: Not able to read local yaml file")
                return False, error
            metadata_device = \
                data['cluster']['node_types'][0]['storage'][0]['devices']['metadata']
            LOGGER.debug("Data is %s and metadata device is %s", data, metadata_device)
        return metadata_device

    def restart_motr_container(self, index):
        """
        Restart Motr container of index and check if it has already restarted.
        :param index:
        :return:
        """
        return False

    @staticmethod
    def build_emap_command(fid=None, selected_shard=None):
        # cob_id = self.get_object_cob_id(self.oid, dtype=ftype)
        if fid or selected_shard is None:
            return False, "metadata path or fid cannot be None"
        kwargs = dict(corrupt_emap=fid, parse_size=10485760,
                      emap_count=1, metadata_db_path=selected_shard)
        cmd = EmapCommandBuilder.build(**kwargs)
        return cmd

    def inject_fault_k8s(self, oid):
        """
        Inject fault of type checksum or parity.
        :param oid: fid of data or parity block
        :param fault_type: checksum or parity
        :return boolean :true :if successful
                          false: if error
        """
        try:
            data_pods = self.master_node_list[0].get_all_pods(POD_NAME_PREFIX)
            for pod_name in enumerate(data_pods):
                motr_containers = self.master_node_list[0].get_container_of_pod(
                    pod_name, MOTR_CONTAINER_PREFIX)
                # motr_instances = len(motr_containers)  # Todo here and also check for copy to 002
                # select 1st motr pod
                logging.debug("pod_name = %s", pod_name)
                if pod_name == "cortx-data-g0-0":
                    logging.debug("Inside.......... pod_name = %s", pod_name)
                    retries = 1
                    success = False
                    while retries > 0:
                        try:
                            resp = self.master_node_list[0].send_k8s_cmd(
                                operation="exec",
                                pod=str(pod_name), namespace=NAMESPACE,
                                command_suffix=f"-c {motr_containers[0]} -- "
                                               f"{self.build_emap_command(oid)}",
                                decode=True,
                            )
                            logging.debug("resp =%s", resp)
                            if resp:
                                success = True
                                break
                            retries -= 1
                            LOGGER.exception("remaining retrying: %s", retries)
                        except IOError as ex:
                            LOGGER.exception("Exception occurred %s", ex)
                            retries -= 1
                            time.sleep(2)
                    if success:
                        break
            # Todo:
            # if self.restart_motr_container(0):
            #     return True
        except IOError as ex:
            LOGGER.exception("Exception occurred while injecting emap fault %s", ex)
            return False
        return True

    def inject_checksum_corruption(self):
        """Injects data checksum error by providing the DU FID."""
        return self.inject_fault_k8s(FT_CHKSUM)

    def inject_parity_corruption(self):
        """Injects parity checksum error by providing the Parity FID."""
        return self.inject_fault_k8s(FT_PARITY)

    def inject_metadata_corruption(self):
        """Not supported."""
        raise NotImplementedError('Not Implemented')
