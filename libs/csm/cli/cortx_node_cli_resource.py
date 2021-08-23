import os
import logging
from commons import commands
from commons.helpers.host import Host
from commons.helpers import node_helper
from config import CMN_CFG
from libs.csm.cli.cortx_node_cli import CortxNodeCli

LOGGER = logging.getLogger(__name__)


class CortxNodeCLIResourceOps(CortxNodeCli):

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
        node_utils = node_helper.Node(hostname=self.host, username=self.username, password=self.password)
        res = node_utils.execute_cmd(cmd=commands.CMD_RESOURCE_DISCOVER)
        if not res:
            LOGGER.info("Command completed successfully %s", res)
            return True, res
        else:
            LOGGER.error("Failed to execute the command %s", res)
            return False, res

    def resource_health_show_node_cli(self, timeout: int):
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
        default_patterns = [
            "Error",
            "exception",
            "usage:",
            "Plugged",
            "Location",
            "command not found"]
        cmd = commands.CMD_RESOURCE_SHOW_HEALTH_RES + " " + "'node>storage[0]>hw>psu'"
        self.log.info("The command to be executed is %s", cmd)
        res = super().execute_cli_commands(cmd=cmd,
                                           patterns=default_patterns, time_out=timeout)
        return res

    def resource_health_show_invalid_param(self, timeout: int):
        # ToDo: Complete function
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
