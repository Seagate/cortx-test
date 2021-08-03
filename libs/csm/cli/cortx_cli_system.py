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
            host=None,
            username=None,
            password=None):
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

    def check_health_status(self, cmd: str):
        """
        This function is used to check the health status from cortxcli.
        :param cmd: command to be run
        :return: (Boolean, response)
        """
        LOGGER.info("Checking health status using cli command")
        output = self.execute_cli_commands(cmd, patterns=["Resource", "Status"])[1]
        if "error" in output.lower() or "exception" in output.lower():
            LOGGER.error("Unable to check health status")
            return False, output

        return True, output

    def node_operation(self, operation, resource_id, force_op: bool = False, storage_off: bool = False):
        """
        This function is used to perform node operation (stop/poweroff/start)
        :param operation: Operation to be performed on node
        :param resource_id: Resource ID for the operation
        :param force_op: Specifying this enables force operation.
        :param storage_off: The poweroff operation will be performed along with powering off the storage.
        Valid only with poweroff operation on node.
        :return: (Boolean, response)
        """
        LOGGER.info("Performing %s on node ID %s", operation, resource_id)
        cmd = 'node {} {}'.format(operation, resource_id)
        if force_op:
            cmd = cmd + " -f"
        if storage_off:
            cmd = cmd + " -s"
        output = self.execute_cli_commands(cmd=cmd)[1]
        if "invalid" in output.lower() or "exception" in output.lower():
            return False, output
        return True, output
