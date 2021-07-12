import logging

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

    def resource_discover_node_cli(self, timeout: int):
        # ToDo: Complete function
        default_patterns = [
            "Error",
            "exception",
            "usage:",
            "command not found"]
        res = super().execute_cli_commands(cmd="resource discover",
                                           patterns=default_patterns, time_out=timeout)
        return res[1]

    def resource_health_show_node_cli(self, timeout: int):
        # ToDo: Complete function
        default_patterns = [
            "Error",
            "exception",
            "usage:",
            "command not found"]
        res = super().execute_cli_commands(cmd="resource health --show",
                                           patterns=default_patterns, time_out=timeout)
        return res[1]

    def resource_health_show_rpath_node_cli(self, timeout: int, rpath: str):
        # ToDo: Complete function
        default_patterns = [
            "Error",
            "exception",
            "usage:",
            "command not found"]
        res = super().execute_cli_commands(cmd=f"resource health --show rpath {rpath}",
                                           patterns=default_patterns, time_out=timeout)
        return res[1]
