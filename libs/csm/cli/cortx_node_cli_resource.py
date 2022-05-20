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
This library contains methods for resource operations using CORTX CLI
"""
import logging
from commons import commands
from commons.helpers import node_helper
from config import CMN_CFG
from libs.csm.cli.cortx_node_cli import CortxNodeCli

LOGGER = logging.getLogger(__name__)


class CortxNodeCLIResourceOps(CortxNodeCli):
    """Resource operations using CORTX CLI"""
    def __init__(
            self,
            host: str = None,
            username: str = None,
            password: str = None,
            **kwargs):
        """
        This method initializes members of CortxNodeCli and its parent class
        :param str host: host/ip of CSM server
        :param str username: username of CSM server
        :param str password: password of CSM server
        :keyword object session_obj: session object of host connection if already established
        :keyword int port: port number
        """
        self.log = logging.getLogger(__name__)
        csm = CMN_CFG.get("csm")
        nodes = CMN_CFG.get("nodes")
        host = host if host else csm["mgmt_vip"] if csm else None
        username = username if username else nodes[0]["username"] if nodes else None
        password = password if password else nodes[0]["password"] if nodes else None
        session_obj = kwargs.get("session_obj", None)
        port = kwargs.get("port", 22)
        super().__init__(
            host=host,
            username=username,
            password=password,
            session_obj=session_obj,
            port=port)

    def resource_discover_node_cli(self):
        """"
        This functions executes the cortx_setup command
        to create the Health map
        """
        node_utils = node_helper.Node(hostname=self.host,
                                      username=self.username,
                                      password=self.password)
        res = node_utils.execute_cmd(cmd=commands.CMD_RESOURCE_DISCOVER)
        if not res:
            LOGGER.info("Command executed \n")
            return True, res
        LOGGER.error("Failed to execute the command %s", res)
        return False, res

    def resource_health_show_node_cli(self, timeout: int):
        """"
        This functions executes the cortx_setup command
        to show health of the various components in Server
        """
        default_patterns = [
            "exception",
            "usage:",
            "storage",
            "argument",
            "Error",
            "command not found"]
        res = super().execute_cli_commands(cmd=commands.CMD_RESOURCE_SHOW_HEALTH,
                                           patterns=default_patterns, time_out=timeout)
        return res

    def resource_show_disk_health(self, timeout: int):
        """"
        This functions executes the cortx_setup command
        to fetch the OS disk health status
        """
        default_patterns = [
            "Error",
            "exception",
            "usage:",
            "last_updated",
            "command not found"]
        cmd = (commands.CMD_RESOURCE_SHOW_HEALTH_RES + " " + " 'node>server[0]>sw>raid'")
        self.log.info("The command to be executed is %s", cmd)
        res = super().execute_cli_commands(cmd=cmd,
                                           patterns=default_patterns, time_out=timeout)
        return res

    def resource_show_cont_health(self, timeout: int):
        """"
        This functions executes the cortx_setup command
        to fetch the controller health
        """
        default_patterns = [
            "Error",
            "exception",
            "usage:",
            "last_updated",
            "location",
            "command not found"]
        cmd = commands.CMD_RESOURCE_SHOW_HEALTH_RES + " " + "'node>storage[0]>hw>controller'"
        self.log.info("The command to be executed is %s", cmd)
        res = super().execute_cli_commands(cmd=cmd,
                                           patterns=default_patterns, time_out=timeout)
        return res

    def resource_show_psu_health(self, timeout: int):
        """"
        This functions fetch the health of the storage PSU's
        using cortx_setup.
        """
        default_patterns = [
            "Error",
            "exception",
            "usage:",
            "Plugged",
            "last_updated",
            "Location",
            "command not found"]
        cmd = commands.CMD_RESOURCE_SHOW_HEALTH_RES + " " + "'node>storage[0]>hw>psu'"
        self.log.info("The command to be executed is %s", cmd)
        res = super().execute_cli_commands(cmd=cmd,
                                           patterns=default_patterns, time_out=timeout)
        return res

    def resource_health_show_invalid_param(self, timeout: int):
        """"
        This functions executes the cortx_setup command
        with wrong resource_path
        """
        default_patterns = [
            "usage:",
            "command not found",
            "Error",
            "exception",
            "storage",
            "Failed",
            "argument"]
        cmd = commands.CMD_RESOURCE_SHOW_HEALTH_RES + " " + "'node>storage[0]>hw>psus'"
        res = super().execute_cli_commands(cmd=cmd,
                                           patterns=default_patterns, time_out=timeout)
        return res

    def split_str_to_list(self, input_str: str, sep: str):
        """
        This Function formats the string to list
        to alternate index value
        """
        out = input_str.split(sep)
        i = 0
        num = len(out)
        while i < num - 1:
            out[i] = out[i] + "}" + "}" + "]" + "}" + "}"
            result = super().format_str_to_dict(out[i])
            LOGGER.info(result["health"]["status"])
            LOGGER.info(result["health"]["description"])
            i = i + 2
        return result

    def convert_to_list_format(self, input_str: str, sep: str):
        """
        This Function formats the string
         to list to index value 1
        """
        out = input_str.split(sep)
        i = 0
        num = len(out)
        while i < num - 1:
            out[i] = out[i] + "}"
            result = super().format_str_to_dict(out[i])
            LOGGER.info(result["health"]["status"])
            LOGGER.info(result["health"]["description"])
            i = i + 1
        result = super().format_str_to_dict(out[i])
        LOGGER.info(result["health"]["status"])
        LOGGER.info(result["health"]["description"])
        return result
