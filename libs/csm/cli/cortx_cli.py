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
This library contains common methods for CORTX CLI which will be used
across all other libraries and test suites
"""

import logging
import json
import xmltodict
import commons.errorcodes as err
from commons import commands
from commons.exceptions import CTException
from config import CMN_CFG
from libs.csm.cli.cortx_cli_client import CortxCliClient


class CortxCli(CortxCliClient):
    """This class contains common methods for CORTX CLI derived from cli client lib"""

    def __init__(
            self,
            host: str = CMN_CFG["csm"]["mgmt_vip"],
            #username: str = CMN_CFG["csm"]["csm_admin_user"]["username"],
            #password: str = CMN_CFG["csm"]["csm_admin_user"]["password"],
            username: str = CMN_CFG["nodes"][0]["username"],
            password: str = CMN_CFG["nodes"][0]["password"],
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
        session_obj = kwargs.get("session_obj", None)
        port = kwargs.get("port", 22)
        super().__init__(
            host=host,
            username=username,
            password=password,
            session_obj=session_obj,
            port=port)

    def execute_cli_commands(self, cmd: str, time_out: int = 800, sleep_time: int = 2) -> tuple:
        """
        This function executes command on interactive shell on csm server and returns output
        :param str cmd: command to execute on shell
        :param int time_out: max time to wait for command execution output
        :param int sleep_time: wait time for receiving data
        :return: output of executed command
        """
        try:
            output = super().execute_cli_commands(cmd=cmd, time_out=time_out, sleep_time=sleep_time)
            if "error" in output.lower() or "exception" in output.lower():
                return False, output
            return True, output
        except Exception as error:
            self.log.error(
                "An error in %s: %s:",
                CortxCli.execute_cli_commands.__name__,
                error)
            raise CTException(err.CLI_ERROR, error.args[0]) from error

    def login_cortx_cli(
            self,
            username: str = CMN_CFG["csm"]["csm_admin_user"]["username"],
            password: str = CMN_CFG["csm"]["csm_admin_user"]["password"],
            **kwargs) -> tuple:
        """
        This function will be used to login to CORTX CLI with given credentials
        :param str username: User name to login
        :param str password: User password
        :keyword username_param: username to pass as argument
        :keyword login_cortxcli: command for login to CLI
        :return: True/False and output
        """
        username_param = kwargs.get("username_param", None)
        login_cortxcli = kwargs.get("cmd", commands.CMD_LOGIN_CORTXCLI)
        if username_param:
            login_cortxcli = " ".join(
                [login_cortxcli, "--username", username_param])

        self.log.info("Opening interactive CORTX CLI session....")
        output = self.execute_cli_commands(login_cortxcli)[1]

        if "Username:" in output:
            self.log.info("Logging in CORTX CLI as user %s", username)
            output = self.execute_cli_commands(cmd=username)[1]
            if "Password:" in output:
                output = self.execute_cli_commands(cmd=password)[1]
                if "CORTX Interactive Shell" in output:
                    self.log.info(
                        "Logged in CORTX CLI as user %s successfully", username)
                    return True, output

        return False, output

    def logout_cortx_cli(self) -> tuple:
        """
        This function will be used to logout of CORTX CLI
        :return: True/False and output
        """
        output = self.execute_cli_commands(cmd=commands.CMD_HELP_OPTION)[1]
        if "usage: cortxcli" in output:
            self.log.info("Logging out of CORTX CLI")
            output = self.execute_cli_commands(
                cmd=commands.CMD_LOGOUT_CORTXCLI)[1]
            if "Successfully logged out" in output:
                return True, output

        self.log.info("Response returned: \n%s", output)

        return False, output

    def format_str_to_dict(self, input_str: str) -> dict:
        """
        This function will convert the given string into dictionary.
        :param str input_str: Input string which will be converted to dictionary.
        :return: Dictionary created from given input string.
        :rtype: dict
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
        formatted_data = input_str.replace("\r\n  ", "").replace(
            "\r\n", ",").replace(",</", "</").split(",")[1:-1]
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
        response = str(ip_response).split('\r\n')

        # Splitting values of each row column-wise
        for i, string in enumerate(response):
            response[i] = string.split('|')
            for j in range(len(response[i])):
                response[i][j] = response[i][j].strip()
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
                CortxCli.close_connection.__name__,
                error)
            raise CTException(err.CLI_ERROR, error.args[0]) from error
