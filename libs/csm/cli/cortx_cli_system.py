#!/usr/bin/python
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
This library contains methods for system node operations using CORTX CLI
"""

import logging
from commons import commands
from commons.constants import Rest as Const
from commons.exceptions import CTException
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

    def node_operation(
            self,
            operation: str,
            resource_id: int,
            force_op: bool = False,
            storage_off: bool = False):
        """
        This function is used to perform node operation (stop/poweroff/start)
        :param operation: Operation to be performed on node
        :param resource_id: Resource ID for the operation
        :param force_op: Specifying this enables force operation.
        :param storage_off: The poweroff operation will be performed along
        with powering off the storage.
        Valid only with poweroff operation on node.
        :return: (Boolean, response)
        """
        try:
            LOGGER.info("Performing %s on node ID %s", operation, resource_id)
            cmd = commands.CMD_NODE_OPERATION.format(operation, resource_id)
            if storage_off and operation == 'poweroff':
                cmd = cmd + " -s true"
            if force_op:
                cmd = cmd + " -f true"
            output = self.execute_cli_commands(cmd=cmd)[1]
            # TODO: Need to add some delay after node operation performed
            if "successfully" not in output.lower() or "error" in output.lower():
                return False, output
            return True, output
        except (ValueError, CTException) as error:
            LOGGER.error("%s %s: %s",
                         Const.EXCEPTION_ERROR,
                         CortxCliSystemtOperations.node_operation.__name__,
                         error)
            return False, error
