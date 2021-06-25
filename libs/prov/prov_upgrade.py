#!/usr/bin/python
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

"""
Provisioner utiltiy methods for sw upgrade functionality
"""
import shutil
import logging
import json
from commons import commands as common_cmd

LOGGER = logging.getLogger(__name__)


class ProvSWUpgrade:
    """
    This class contains utility methods for all the operations related
    to SW upgrade processes.
    """

    @staticmethod
    def set_validate_repo(iso_list, node_object):
        """
        Setting the SW upgrade repo and validating it if set to desired build
        :param iso_list: list of iso files which need to be used for setting repo
        :type: list
        :param node_object: node object for execution of command
        :type: object
        :return: True/False, response
        :rtype: boolean, str
        """
        try:
            LOGGER.info("ISO to be set in repo: {}".format(iso_list[0]))
            resp = node_object.execute_cmd(common_cmd.CMD_SW_SET_REPO
                                           .format(iso_list[0], iso_list[1], iso_list[3]), read_lines=True)
            LOGGER.debug("Set repo response: {}".format(resp))
            for line in resp:
                if "ERROR" in line or "failed" in line:
                    return False, resp
            res = node_object.execute_cmd(common_cmd.CMD_ISO_VER, read_lines=True)
            LOGGER.debug("Response for ISO version: {}".format(res))
            data = res[0].split('-')
            return True, data[1]

        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvSWUpgrade.set_validate_repo.__name__)
            return False, error

    @staticmethod
    def check_sw_upgrade(node_object):
        """
        Run the SW upgrade command and check the status.
        :param node_object: node object to execute command on node
        :type: object
        :return: True/False, response
        :rtype: boolean, str
        """
        try:
            LOGGER.info("SW upgrade process starting...")
            resp = node_object.execute_cmd(common_cmd.CMD_SW_UP, read_lines=True)
            for line in resp:
                if "ERROR" in line or "failed" in line:
                    return False, resp
            LOGGER.debug("Response for SW upgrade process: {}".format(resp))
            LOGGER.info("SW upgrade process completed successfully.")

            LOGGER.info("Checking the build version on system.")
            res = node_object.execute_cmd(common_cmd.CMD_SW_VER, read_lines=True)
            data = json.loads(res[0])
            build_new = data["BUILD"]
            return True, build_new

        except IOError as error:
            LOGGER.error(
                "An error occurred in %s:",
                ProvSWUpgrade.check_sw_upgrade.__name__)
            return False, error
