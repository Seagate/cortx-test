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
""" This is a core library which will execute commands on interactive cortxcli"""

import platform
import logging

try:
    if platform.system() == "Linux":
        import redexpect
except ModuleNotFoundError as error:
    logging.error(error)


class CortxCliClient:
    """
    This class is responsible to establish connection to CSM server
    and execute commands on interactive cortxcli
    """

    def __init__(
            self,
            host: str,
            username: str,
            password: str,
            **kwargs):
        """
        Initialize credentials of CSM server
        :param str host: host/ip of CSM server
        :param str username: username of CSM server
        :param str password: password of CSM server
        :keyword object session_obj: session object of host connection if already established
        :keyword int port: port number
        """
        self.log = logging.getLogger(__name__)
        self.host = host
        self.username = username
        self.password = password
        self.session_obj = kwargs.get("session_obj", None)
        self.port = kwargs.get("port", 22)
        self.expect_timeout = kwargs.get("expect_timeout", 300)
        self.host_obj = None

    def open_connection(self):
        """
        This function will open the ssh connection with host
        :return: None
        """
        if not self.session_obj:
            self.session_obj = redexpect.RedExpect(
                expect_timeout=self.expect_timeout)
            self.session_obj.login(
                hostname=self.host,
                username=self.username,
                password=self.password,
                allow_agent=True)
            self.log.debug("Opened an ssh connection with host: %s", self.host)

    def execute_cli_commands(
            self,
            cmd: str,
            patterns: list,
            time_out: int) -> tuple:
        """
        This function executes command on interactive shell on csm server and returns output
        :param str cmd: command to execute on shell
        :param list patterns: list of patterns to expect in the command output
        :param int time_out: time to wait for command execution output
        :return: index of matched pattern and output of executed command
        """
        cmd = "".join([cmd, "\n"])
        self.log.info("Sending command: %s", cmd)
        self.session_obj.send(cmd)
        index = self.session_obj.expect(re_strings=patterns, timeout=time_out)
        output = self.session_obj.current_output

        return index, output

    def close_connection(self):
        """
        This function will close the ssh connection created in init
        :return: None
        """
        self.session_obj.exit()
        self.log.debug("Closed ssh connection with host %s", self.host)
