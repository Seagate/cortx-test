#!/usr/bin/py
import socket
import logging

from telnetlib import Telnet
from typing import Union, Tuple, List
log = logging.getLogger(__name__)


class TelnetLib:
    """
    Telnet Class Lib used to write wrapper methods.
    Telnet from python is used to create generic calls and further extensions are added.
    """

    def __init__(self,host: str,port: str,user: str,pwd: str,timeout: int = 20) -> None:
        """
        Constructor to connect to controller and perform CRUD operations.
        :param host: primary node host.
        :type host: str.
        :param port: valid port number.
        :type port: str
        :param user: primary node username.
        :type user: str.
        :param pwd: primary node password.
        :type pwd: str.
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
            self.tn = Telnet(host=self.host, port=self.port, timeout=self.timeout)
        except (socket.error, Exception) as error:
            log.error(f"Error in {TelnetLib.__init__.__name__}. error: {error}")
        else:
            log.info(f"Connected to host {self.host} successfully.")

    def connect(self) -> Tuple[bool, str]:
        """
        Connect to GEM console with valid loging, password.
        :return: True/False, response.
        :rtype: tuple.
        """
        try:
            self.tn.write(b'\n')
            if b'GEM>' in (self.read()):
                log.info("GEM Console connected successfully without login/password.")
                return True, "Connected."
            if b'Password:' in self.read():
                resp = self._write(self.pwd)
                log.info(resp)
                return self.login(resp)
            else:
                resp = self.read()
                log.info(resp)
                return self.login(resp)
        except Exception as error:
            log.error(f"Error in {TelnetLib.connect.__name__}. Could not establish connection: error: {error}")

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
                        log.info("Login Successful with login and password.")
                        return True, "Connected."
        except Exception as error:
            log.error(f"Error in {TelnetLib.login.__name__}, ConnectionRefusedError:{error}")

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
            b_str = b_str if isinstance(b_str, bytes) else b_str.encode()  # convert string to bytes.
            read_response = self.tn.read_until(b_str, timeout)
        except Exception as error:
            log.error(f"Error in {TelnetLib.read.__name__}, Error:{error}")

        return read_response

    def read_all(self) -> bytes:
        """
        Read the ALL response from telnet console.
        :return: Read all response.
        :rtype: bytes.
        """
        read_all_response = b""
        try:
            read_all_response = self.tn.read_all()
            log.info(f"Read all response: {read_all_response}")
        except Exception as error:
            log.error(f"Error in {TelnetLib.read_all.__name__}, Error:{error}")

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
        try:
            b_str = b_str if isinstance(b_str, bytes) else b_str.encode()  # convert string to bytes.
            self.tn.write(b_str)
            self.tn.write(b'\n')
            write_response = self.read()
            log.info(f"Write response: {write_response}")
        except Exception as error:
            log.error(f"Error in {TelnetLib._write.__name__}, Error:{error}")

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
        try:
            cmd = cmd if isinstance(cmd, bytes) else cmd.encode()  # convert string to bytes.
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
            log.info(f"Execute cmd response: {response}")
        except Exception as error:
            log.error(f"Error in {TelnetLib.execute_cmd.__name__}, Error:{error}")

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
        try:
            response = response.decode("utf-8") if isinstance(response, bytes) else response  # convert to string.
            response = response.split("\r\n")[1:-1]  # Output cleanup: split text around \r\n, skip first, last element.
        except Exception as error:
            log.error(f"Error in {TelnetLib.result.__name__}, Error:{error}")

        return response
