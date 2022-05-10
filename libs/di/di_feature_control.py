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
#
"""
Python library which will perform the operations to enable/disable DI feature
"""
import logging
import os
from commons import commands
from commons import const
from commons.constants import POD_NAME_PREFIX
from commons.constants import PROD_FAMILY_LC
from commons.constants import PROD_FAMILY_LR
from commons.constants import PROD_TYPE_K8S
from commons.constants import PROD_TYPE_NODE
from commons.helpers.node_helper import Node
from commons.helpers.pods_helper import LogicalNode
from commons.params import LOCAL_S3_CONFIG
from commons.utils import config_utils

LOGGER = logging.getLogger(__name__)


class DIFeatureControl:
    """
    Class Controls the enabling and disabling of DI Feature in s3config.yaml.
    S3_WRITE_DATA_INTEGRITY_CHECK
    S3_READ_DATA_INTEGRITY_CHECK
    S3_METADATA_INTEGRITY_CHECK
    S3_SALT_CHECKSUM
    """

    def __init__(self, cmn_cfg):
        """This method initializes members of DIFeatureControl
        :param cmn_cfg: common config injected object
        """
        self.cmn_cfg = cmn_cfg
        self.nodes = cmn_cfg["nodes"]
        self.connections = list()
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
            LOGGER.info("Product family: LC")
            for node in self.nodes:
                if node["node_type"].lower() == "master":
                    node_obj = LogicalNode(hostname=node["hostname"],
                                           username=node["username"],
                                           password=node["password"])
                    node_obj.connect()
                    self.connections.append(node_obj)
                    hostnames.append(node["hostname"])

    def set_flag_in_s3server_config(self, section, flag, value, **kwargs):
        """
        Set s3_md5_check_flag, s3_range_read_flag or s3_disable_metadata_corr_iem or
        s3_disable_data_corr_iem flag in s3 configuration file
        :param section: s3config section.
        :param flag: flag to be updated.
        :param value: value of flag.
        :param backup_path: modified s3config file
        """
        LOGGER.info("Setting %s flag value to %s in s3server config file", flag, value)
        try:
            backup_path = kwargs.get("backup_path", const.LOCAL_S3_CONFIG)
            status, resp = config_utils.read_yaml(backup_path)
            if not status:
                return status, resp
            LOGGER.debug(resp)
            old_value = resp[section][flag]
            LOGGER.info(old_value)
            resp[section][flag] = value
            status, resp = config_utils.write_yaml(backup_path, resp, backup=True)
            if not status:
                return status, resp
            for node_conn in self.connections:
                status, resp = node_conn.copy_file_to_local(const.S3_CONFIG, backup_path)
                if not status:
                    return status, resp

                status, resp = node_conn.copy_file_to_remote(backup_path, const.S3_CONFIG)
                if not status:
                    return status, resp
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                node_conn.disconnect()

            return status, (flag, value, old_value)
        except Exception as error:
            LOGGER.exception("Error in %s: %s",
                             DIFeatureControl.set_flag_in_s3server_config.__name__,
                             error)

    @staticmethod
    def get_s3server_config_file(master_node: LogicalNode, pod: str):
        """
        Retrieve S3 server config file. (Supports LC)
        :param: master_node: Master node object to access specified pods
        :param: pod: Pod name to retrieve s3 config file
        return: tuple
        """
        LOGGER.info("Copying Config file from pod %s", pod)
        node_path = "/root/s3config.yaml"
        cmd = commands.K8S_CP_PV_FILE_TO_LOCAL_CMD.format(pod, const.S3_CONFIG_K8s, node_path)
        resp = master_node.execute_cmd(cmd=cmd, read_lines=True)
        LOGGER.debug("Resp : %s", resp)

        resp = master_node.copy_file_to_local(node_path, LOCAL_S3_CONFIG)
        if not resp:
            raise Exception("Error during copying file to client")

        status, resp = config_utils.read_yaml(LOCAL_S3_CONFIG)
        if not status:
            raise Exception(f"Unable to read {LOCAL_S3_CONFIG} on client: {resp}")

        LOGGER.debug("Remove local file")
        if os.path.exists(LOCAL_S3_CONFIG):
            os.remove(LOCAL_S3_CONFIG)

        return resp

    @staticmethod
    def verify_flag_enable(section: str, flag: str, node_obj: Node):
        """
        Verify if flags are set on the given node (Supports LR)
        :param section: s3config section.
        :param flag: flag to be updated.
        :param node_obj: Node object to check the flag
        :return Boolean: True if given flag is enabled
                          False if given flag is disabled
        """
        backup_path = LOCAL_S3_CONFIG
        LOGGER.info("Verify DI flags on %s",node_obj.hostname)

        status, resp = node_obj.copy_file_to_local(const.S3_CONFIG, backup_path)
        if not status:
            return status, f"Unable to copy {const.S3_CONFIG} on client: {resp}"
        status, resp = config_utils.read_yaml(backup_path)
        if not status:
            return status, f"Unable to read {backup_path} on client: {resp}"
        LOGGER.info(resp)
        if resp[section][flag]:
            return True, f"{flag} flag is set on {node_obj.hostname}"
        return False, f"{flag} flag is not set on {node_obj.hostname}"

    def verify_s3config_flag_all_nodes(self, section: str, flag: str):
        """
        Verify if flags are set on the all nodes. (Supports both LC/LR)
        :param section: s3config section.
        :param flag: flag to be verified.
        :return Tuple[Boolean,Boolean]: Boolean - True if operation successful else False
                                 Boolean - flag_value
        """
        if self.cmn_cfg["product_family"] == PROD_FAMILY_LR and \
                self.cmn_cfg["product_type"] == PROD_TYPE_NODE:
            flag_value = []
            try:
                for node in self.connections:
                    resp = self.verify_flag_enable(section=section, flag=flag, node_obj=node)
                    flag_value.append(resp[0])
                    LOGGER.info("Node: %s flag: %s flag_value: %s", node.hostname, flag, resp[0])
                if len(set(flag_value)) == 1:
                    return True, flag_value[0]
                else:
                    return False, f"S3 config values for {flag} are not equal in all pods."
            except Exception as ex:
                LOGGER.error(f"Exception Occurred while reading {flag}: %s", ex)
                return False, ex
        elif self.cmn_cfg["product_family"] == PROD_FAMILY_LC and \
                self.cmn_cfg["product_type"] == PROD_TYPE_K8S:
            flag_value = []
            try:
                master_node = self.connections[0]
                pods_list = master_node.get_all_pods(pod_prefix=POD_NAME_PREFIX)
                for pod in pods_list:
                    resp = self.get_s3server_config_file(master_node, pod)
                    flag_value.append(resp[section][flag])
                    LOGGER.info("Pods: %s flag: %s flag_value: %s", pod, flag, resp[section][flag])
                if len(set(flag_value)) == 1:
                    return True, flag_value[0]
                else:
                    return False, f"S3 config values for {flag} are not equal in all pods."
            except Exception as ex:
                LOGGER.error(f"Exception Occurred while reading {flag}: %s", ex)
                return False, ex
