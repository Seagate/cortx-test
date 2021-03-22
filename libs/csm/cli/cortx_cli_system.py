#!/usr/bin/python
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
This library contains methods for system node operations using CORTX CLI
"""

import logging
from commons import commands
from config import CMN_CFG
from libs.csm.cli.cortx_cli import CortxCli

LOGGER = logging.getLogger(__name__)


class CortxCliSystemtOperations(CortxCli):
    """
    This class has all system related operations
    """

    def __init__(
            self,
            session_obj: object = None,
            host=CMN_CFG["nodes"][0]["host"],
            username=CMN_CFG["nodes"][0]["username"],
            password=CMN_CFG["nodes"][0]["password"]):
        """
        This method initializes members of CortxCliSystemtOperations
        :param object session_obj: session object of host connection if already established
        """
        super().__init__(host=host, username=username, password=password, session_obj=session_obj)

    def check_resource_status(self) -> tuple:
        """
        This function is used to check resource status
        :return: (Boolean, response)
        :rtype: Tuple
        """
        LOGGER.info("Checking resource status using cli command")
        output = self.execute_cli_commands(cmd=commands.CMD_SYSTEM_STATUS)[1]
        if "error" in output.lower() or "exception" in output.lower():
            LOGGER.error("Unable to check system status")
            return False, output

        return True, output

    def start_node(self, node_name: str = None) -> tuple:
        """
        This function is used to start system node
        :param str node_name: Name of node to be start
        :return: (Boolean, response)
        """
        LOGGER.info("Starting system node %s", format(node_name))
        command = " ".join(
            [commands.CMD_SYSTEM_START, node_name])
        output = self.execute_cli_commands(cmd=command)[1]
        if "[Y/n]" in output:
            output = self.execute_cli_commands(cmd="Y")[1]
        if "error" in output.lower() or "exception" in output.lower():
            LOGGER.error("Failed to start system node")

        return True, output

    def stop_node(self, node_name: str = None) -> tuple:
        """
        This function is used to stop system node
        :param str node_name: Name of node to be start
        :return: (Boolean, response)
        """
        LOGGER.info("Stopping system node %s", format(node_name))
        command = " ".join(
            [commands.CMD_SYSTEM_STOP, node_name])
        output = self.execute_cli_commands(cmd=command)[1]
        if "[Y/n]" in output:
            output = self.execute_cli_commands(cmd="Y")[1]
        if "error" in output.lower() or "exception" in output.lower():
            LOGGER.error("Failed to stop system node")

        return True, output

    def shutdown_node(self, node_name: str = None) -> tuple:
        """
        This function is used to shutdown system node
        :param str node_name: Name of node to be start
        :return: (Boolean, response)
        """
        LOGGER.info("Shutdown system node %s", format(node_name))
        command = " ".join(
            [commands.CMD_SYSTEM_SHUTDOWN, node_name])
        output = self.execute_cli_commands(cmd=command)[1]
        if "[Y/n]" in output:
            output = self.execute_cli_commands(cmd="Y")[1]
        if "error" in output.lower() or "exception" in output.lower():
            LOGGER.error("Failed to shutdown system node")

        return True, output
