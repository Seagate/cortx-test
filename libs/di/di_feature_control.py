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
import time
from commons import errorcodes, const
from commons.exceptions import CTException
from commons.helpers.node_helper import Node
from commons.utils import config_utils
from commons.utils.system_utils import run_remote_cmd_wo_decision
from libs.di import di_constants
from libs.s3 import CM_CFG
from libs.s3 import S3H_OBJ

logger = logging.getLogger(__name__)


class DIFeatureControlLib:
    def __init__(self,
                 primary_node=CM_CFG["nodes"][0]["hostname"],
                 username=CM_CFG["nodes"][0]["username"],
                 password=CM_CFG["nodes"][0]["password"]
                 ):
        """This method initializes members of DIFeatureControlLib
        :param primary_node: hostname of primary name
        :type primary_node: str
        :param username: username
        :type username: str
        :param password: password
        :type password: str
        """
        self.primary_node = primary_node
        self.username = username
        self.password = password

    def enable_maintenance_mode(self):
        """
        Enable the System Maintenance mode
        """
        logger.info("Enabling System Maintenance mode")
        try:
            result, std_err, _ = run_remote_cmd_wo_decision(
                self.primary_node, self.username, self.password,
                di_constants.HCTL_MAINTENANCE_MODE_CMD)
        except Exception as error:
            logger.error("Error in %s: %s",
                         DIFeatureControlLib.enable_maintenance_mode.__name__,
                         error)
            raise CTException(errorcodes.MAINTENANCE_MODE, error.args[0])
        if "All nodes are in standby mode now" in std_err:
            logger.info("The System is into Maintenance mode")
            logger.debug(f"result: {result} std_err : {std_err}")
            return
        else:
            logger.error("Error while enabling System Maintenance mode")
            logger.error(f"result: {result} std_err : {std_err}")
            raise CTException(errorcodes.MAINTENANCE_MODE, f"result: {result} std_err : {std_err}")

    def disable_maintenance_mode(self):
        """
        Disable the System Maintenance Mode
        """
        logger.info("Disabling System Maintenance mode")
        try:
            result, std_err, _ = run_remote_cmd_wo_decision(
                self.primary_node, self.username, self.password,
                di_constants.HCTL_UNMAINTENANCE_MODE_CMD)
        except Exception as error:
            logger.error("Error in %s: %s",
                         DIFeatureControlLib.disable_maintenance_mode.__name__,
                         error)
            raise CTException(errorcodes.UNMAINTENANCE_MODE, error.args[0])
        if "All nodes are back to normal mode" in std_err and \
                "Cluster is functional now" in std_err:
            logger.info("Disabled the System Maintenance mode")
            logger.debug(f"result: {result} std_err : {std_err}")
            return
        else:
            logger.error("Error while disabling System Maintenance mode")
            logger.error(f"result: {result} std_err : {std_err}")
            raise CTException(errorcodes.UNMAINTENANCE_MODE, f"result: {result} std_err : {std_err}")

    def set_flag_in_s3server_config(self, section, flag, value, host, user, password):
        """
        Set s3_md5_check_flag, s3_range_read_flag or s3_disable_metadata_corr_iem or
        s3_disable_data_corr_iem flag in s3 configuration file
        :param section: s3config section.
        :param flag: flag to be updated.
        :param value: value of flag.
        :param host: IP of the host.
        :param user: user name of the host.
        :param password: password for the user.
        """
        self.enable_maintenance_mode()
        time.sleep(60)
        logger.info("Setting %s flag value to %s in s3server config file", flag, value)
        try:
            status, response = S3H_OBJ.update_s3config(section=section, parameter=flag, value=value,
                                                       host=host, user=user, password=password)
        except Exception as error:
            logger.error("Error in %s: %s",
                         DIFeatureControlLib.set_flag_in_s3server_config.__name__,
                         error)
            raise CTException(errorcodes.S3_SET_FLAG, error.args[0])
        if not status:
            raise CTException(errorcodes.S3_SET_FLAG, f"Unable to set {flag} in s3server.")
        self.disable_maintenance_mode()

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
        backup_path = const.LOCAL_S3_CONFIG
        logger.info(f"Verify DI flags on {host}")
        node = Node(hostname=host, username=username, password=password)
        status, resp = node.copy_file_to_local(const.S3_CONFIG, backup_path)
        if not status:
            return status, f"Unable to copy {const.S3_CONFIG} on client: {resp}"
        status, resp = config_utils.read_yaml(backup_path)
        if not status:
            return status, f"Unable to read {backup_path} on client: {resp}"
        logger.info(resp)
        if resp[section][flag]:
            return True, f"{flag} flag is set on {host}"
        else:
            return False, f"{flag} flag is not set on {host}"
