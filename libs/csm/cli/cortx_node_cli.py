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
This library contains methods for S3 Account operations using CORTX CLI
"""
import json
import logging
import platform
import xmltodict
try:
    if platform.system() == "Linux":
        import redexpect
except ModuleNotFoundError as err:
    logging.error(err)

import commons.errorcodes as err
from commons.exceptions import CTException
from config import CMN_CFG
from libs.csm.cli.cortx_cli_client import CortxCliClient


class CortxNodeCli(CortxCliClient):
    """This class contains common methods for CORTX CLI derived from cli client lib"""

    def __init__(
            self,
            host: str = None,
            username: str = None,
            password: str = None,
            **kwargs):
        """
        This method initializes members of CortxCli and its parent class
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

    def execute_cli_commands(
            self,
            cmd: str,
            patterns: list,
            time_out: int = 300) -> tuple:
        """
        This function executes command on interactive shell on csm server and returns output
        :param str cmd: command to execute on shell
        :param list patterns: max time to wait for command execution output
        :param int time_out: wait time for receiving data
        :return: output of executed command
        """
        try:
            default_patterns = []
            default_patterns.extend(patterns)
            self.log.debug("Default patterns : %s", default_patterns)
            index, output = super().execute_cli_commands(
                cmd=cmd, patterns=default_patterns, time_out=time_out)
            if index in range(2):
                return False, output
            return True, output
        except redexpect.exceptions.ExpectTimeout as error:
            self.log.debug(
                "Current output \n %s",
                self.session_obj.current_output)
            self.log.error("Timeout waiting for expected response!")
            raise TimeoutError from error
        except Exception as error:
            self.log.error(
                "An error in %s: %s:",
                CortxNodeCli.execute_cli_commands.__name__,
                error)
            raise CTException(err.CLI_ERROR, error.args[0]) from error

    def login_node_cli(
            self,
            username: str,
            password: str,
            **kwargs) -> tuple:
        """
        This function will be used to login to CORTX CLI with given credentials
        :param str username: User name to login
        :param str password: User password
        :keyword username_param: username to pass as argument
        :keyword login_cortxcli: command for login to CLI
        :return: True/False and output
        """
        # ToDo: Once we node cli is delivered

    def logout_node_cli(self) -> tuple:
        """
        This function will be used to logout of CORTX CLI
        :return: True/False and output
        """
        # ToDo: Once we node cli is delivered

    def format_str_to_dict(self, input_str: str):
        """
        This function will convert the given string into dictionary.
        :param str input_str: Input string which will be converted to dictionary.
        :return: Dictionary created from given input string.
        """
        if not input_str:
            self.log.error("Empty string received!!")
            return None
        self.log.debug("Data received \n %s", input_str)
        start_index = input_str.find("{")
        end_index = input_str.rfind("}") + 1
        json_data = json.loads(input_str[start_index:end_index])
        self.log.debug("JSON output \n %s", json_data)
        return json_data

    def xml_data_parsing(self, input_str: str) -> list:
        """
        This is a helper method which will parse the given XML formatted string
        :param str input_str: XML formatted string to be converted
        :return: List of dictionary
        """
        resp_list = []
        if not input_str:
            self.log.error("String is empty")
            return resp_list
        self.log.debug("Data received \n %s", input_str)
        formatted_data = input_str.replace("\n  ", "").replace(
            "\n", ",").replace(",</", "</").split(",")[1:-1]
        for node in formatted_data:
            temp_dict = json.dumps(xmltodict.parse(node))
            json_format = json.loads(temp_dict)
            resp_list.append(json_format)
        self.log.debug("Extracted output \n %s", resp_list)
        return resp_list

    def split_table_response(self, ip_response: str) -> list:
        """
        This function will split response into list making it suitable for verification
        :param ip_response: response which is to be split
        :return: List formed after splitting response
        """
        # Splitting response row-wise
        response = str(ip_response).split('\n')
        # Splitting values of each row column-wise
        for i, string in enumerate(response):
            response[i] = string.split('|')
            for j in range(len(response[i])):
                response[i][j] = response[i][j].strip()
            response[i] = response[i][1:-1]
        response = response[4:len(response) - 2]
        self.log.info(response)
        return response

    def close_connection(self):
        """
        This function will close the ssh connection created in init
        :return: None
        """
        try:
            super().close_connection()
        except Exception as error:
            self.log.error(
                "An error in %s: %s:",
                CortxNodeCli.close_connection.__name__,
                error)
            raise CTException(err.CLI_ERROR, error.args[0]) from error
