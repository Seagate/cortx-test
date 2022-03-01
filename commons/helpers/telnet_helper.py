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

import socket
import logging

from telnetlib import Telnet as Tnet
from typing import Union, Tuple, List
log = logging.getLogger(__name__)


class Telnet:
    """
    Telnet Class Lib used to write wrapper methods.
    Telnet from python is used to create generic calls and further extensions are added.
    """

    def __init__(self, host: str, port: str, user: str, pwd: str, timeout: int = 20) -> None:
        """
        Constructor to connect to controller and perform CRUD operations.
        :param host: primary node host.
        :param port: valid port number.
        :param user: primary node username.
        :param pwd: primary node password.
        :param timeout: waiting time
        :type timeout: int
        :return: None
        :rtype: None.
        """
        self.host = host
        self.port = port
        self.user = user if isinstance(user, bytes) else user.encode()
        self.pwd = pwd if isinstance(pwd, bytes) else pwd.encode()
        self.timeout = timeout
        try:
            self.tn = Tnet(host=self.host, port=self.port,
                           timeout=self.timeout)
        except (socket.error, Exception) as error:
            log.error(f"Error in {Telnet.__init__.__name__}. error: {error}")
        else:
            log.debug(f"Connected to host {self.host} successfully.")

    def connect(self) -> Tuple[bool, str]:
        """
        Connect to GEM console with valid loging, password.
        :return: True/False, response.
        :rtype: tuple.
        """
        try:
            self.tn.write(b'\n')
            if b'GEM>' in (self.read()):
                log.debug(
                    "GEM Console connected successfully without login/password.")
                return True, "Connected."
            if b'Password:' in self.read():
                resp = self._write(self.pwd)
                log.debug(resp)
                return self.login(resp)
            else:
                resp = self.read()
                log.debug(resp)
                return self.login(resp)
        except Exception as error:
            log.error(
                f"Error in {Telnet.connect.__name__}. Could not establish connection: error: {error}")

        return False, "Failed to connect."

    def login(self, resp: bytes) -> Tuple[bool, str]:
        """
        Checks for Login console, Password and returns connection status.
        :return: True/False, response.
        :rtype: tuple.
        """
        try:
            if b'Login:' in resp:
                resp = self._write(self.user)
                if b'Password:' in resp:
                    resp = self._write(self.pwd)
                    if b'GEM>' in resp:
                        log.debug("Login Successful with login and password.")
                        return True, "Connected."
        except Exception as error:
            log.error(
                f"Error in {Telnet.login.__name__}, ConnectionRefusedError:{error}")

        return False, "Failed to connect."

    def __del__(self):
        """
        Destructor for cleaning up connection object.
        :return: None.
        :rtype: None.
        """
        try:
            self.tn.close()
        except (AttributeError, Exception) as error:
            log.error(f"Error in destroy telnet, Error:{error}")

    def read(self,
             b_str: Union[bytes, str] = b' GEM>',
             timeout: int = 20) -> bytes:
        """
        Read the response from telnet console.
        :param b_str: bytes or string.
        :type b_str: bytes/str.
        :param timeout: read timeout.
        :type timeout: int
        :return: response in the form of bytes
        :rtype: bytes.
        """
        read_response = b""
        try:
            # convert string to bytes.
            b_str = b_str if isinstance(b_str, bytes) else b_str.encode()
            read_response = self.tn.read_until(b_str, timeout)
        except Exception as error:
            log.error(f"Error in {Telnet.read.__name__}, Error:{error}")

        return read_response

    def read_all(self) -> bytes:
        """
        Read the ALL response from telnet console.
        :return: Read all response.
        :rtype: bytes.
        """
        read_all_response = b""
        read_all_response = self.tn.read_all()
        log.debug(f"Read all response: {read_all_response}")
        return read_all_response

    def _write(self,
               b_str: Union[bytes, str]
               ) -> bytes:
        """
        write a byte string to terminal and get response.
        :param b_str: bytes string.
        :return: response.
        :rtype: bytes.
        """
        write_response = b""
        # convert string to bytes.
        b_str = b_str if isinstance(b_str, bytes) else b_str.encode()
        self.tn.write(b_str)
        self.tn.write(b'\n')
        write_response = self.read()
        log.debug(f"Write response: {write_response}")
        return write_response

    def execute_cmd(self,
                    cmd: Union[bytes, str]
                    ) -> Tuple[bool, Union[list, bytes]]:
        """
        Execute command(cmd) on console and return response.
        :param cmd: command to be executed on console.
        :type cmd: bytes/str
        :return: True/False, response List.
        :rtype: List[bool, list]
        """
        flag, response = True, b""
        # convert string to bytes.
        cmd = cmd if isinstance(cmd, bytes) else cmd.encode()
        response = self._write(cmd)
        if b'Invalid Command.' in response:
            flag = False
        if b'This command can only be run from the master' in response:
            flag = False
        if b'Unknown command.' in response:
            flag = False
        if b'Authentication failed' in response:
            flag = False
        response = self.result(response)
        if not response:
            flag = False
        log.debug(f"Execute cmd response: {response}")
        return flag, response

    @staticmethod
    def result(response: Union[bytes, str]) -> list:
        """
        Take string or bytes and split it around \r\n and strip first, last element.
        :param response: bytes or string.
        :type response: bytes/str.
        :return: list.
        :rtype: List.
        """
        response = response.decode("utf-8") if isinstance(response,
                                                          bytes) else response  # convert to string.
        # Output cleanup: split text around \r\n, skip first, last element.
        response = response.split("\r\n")[1:-1]
        return response
