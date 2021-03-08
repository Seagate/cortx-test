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

import logging
import time
from commons.helpers.host import Host


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
        session_obj = kwargs.get("session_obj", None)
        self.port = kwargs.get("port", 22)

        if not session_obj:
            self.host_obj = Host(
                hostname=self.host,
                username=self.username,
                password=self.password)
            self.host_obj.connect(True, port=self.port)
            self.session_obj = self.host_obj.shell_obj
        else:
            self.session_obj = session_obj

    def execute_cli_commands(self, cmd: str, time_out: int = 500, sleep_time: int = 6) -> str:
        """
        This function executes command on interactive shell on csm server and returns output
        :param str cmd: command to execute on shell
        :param int time_out: max time to wait for command execution output
        :param int sleep_time: wait time for receiving data
        :return: output of executed command
        """
        output = ""
        cmd = "".join([cmd, "\n"])
        self.log.info("Sending command: %s", cmd)
        self.session_obj.send(cmd)
        poll = time.time() + time_out  # max timeout
        while poll > time.time():
            time.sleep(sleep_time)
            if self.session_obj.recv_ready():
                output = output + \
                    self.session_obj.recv(9999).decode("utf-8")
            else:
                break

        return output

    def close_connection(self):
        """
        This function will close the ssh connection created in init
        :return: None
        """
        self.session_obj.close()
        self.host_obj.disconnect()
