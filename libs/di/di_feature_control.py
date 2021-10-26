# !/usr/bin/python
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
#
"""
Python library which will perform the operations to enable/disable DI feature
"""
import logging
import os
import traceback
from commons import errorcodes, const
from commons.exceptions import CTException
from commons.helpers.node_helper import Node
from commons.utils import config_utils
from commons.utils.system_utils import run_remote_cmd_wo_decision
from commons.constants import PROD_FAMILY_LC
from commons.constants import PROD_FAMILY_LR
from commons.constants import PROD_TYPE_K8S
from commons.constants import PROD_TYPE_NODE
from commons.params import LOCAL_S3_CONFIG
from libs.s3 import S3H_OBJ


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
            LOGGER.critical("Product family: LC")
            # TODO: Add LC related calls. Check for k8s master.

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
    def verify_flag_enable(section, flag, host, username, password):
        """
        Verify if flags are set on the given node
        :param section: s3config section.
        :param flag: flag to be updated.
        :param host: IP of the host.
        :param username: user name of the host.
        :param password: password for the user.
        :return Boolean: True if given flag is enabled
                          False if given flag is disabled
        """
        backup_path = LOCAL_S3_CONFIG
        LOGGER.info(f"Verify DI flags on {host}")
        node = Node(hostname=host, username=username, password=password)
        status, resp = node.copy_file_to_local(const.S3_CONFIG, backup_path)
        if not status:
            return status, f"Unable to copy {const.S3_CONFIG} on client: {resp}"
        status, resp = config_utils.read_yaml(backup_path)
        if not status:
            return status, f"Unable to read {backup_path} on client: {resp}"
        LOGGER.info(resp)
        if resp[section][flag]:
            return True, f"{flag} flag is set on {host}"
        else:
            return False, f"{flag} flag is not set on {host}"

    def verify_s3config_flag_enable_all_nodes(self, section, flag):
        """
        Verify if flags are set on the given node
        :param section: s3config section.
        :param flag: flag to be updated.
        :return Boolean: True, Message if given flag is enabled
                          False, Message if given flag is disabled
        """
        backup_path = LOCAL_S3_CONFIG
        for node in self.connections:
            LOGGER.info(f"Verify DI flags on {node.hostname}")
            status, resp = node.copy_file_to_local(const.S3_CONFIG, backup_path)
            if not status:
                return status, f"Unable to copy {const.S3_CONFIG} on client: {resp}"
            status, resp = config_utils.read_yaml(backup_path)
            if not status:
                return status, f"Unable to read {backup_path} on client: {resp}"
            LOGGER.info(resp)
            if resp[section][flag]:
                return True, f"{flag} flag is set on {node.hostname}"
            else:
                return False, f"{flag} flag is not set on {node.hostname}"
