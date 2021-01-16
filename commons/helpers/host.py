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

import time
import socket
import logging
import pysftp
import paramiko

from typing import Union, Tuple, List

log = logging.getLogger(__name__)


class Host():
    """ Interface class for establishing connections. """

    def __init__(self, hostname: str, username: str, password: str) -> None:
        self.hostname = hostname
        self.username = username
        self.password = password
        self.host_obj = None
        self.shell_obj = None

    def connect(self, shell: bool = False, retry: int = 1, timeout: int = 400, **kwargs) -> None:
        """
        Connect to remote host using hostname, username and password attribute.
        :param shell: In case required shell invocation.
        :param timeout: timeout in seconds.
        :param retry: retry to connect.
        :param kwargs: Optional keyword arguments for SSHClient.connect func call.
        """
        try:
            self.host_obj = paramiko.SSHClient()
            self.host_obj.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            log.debug(f"Connecting to host: {self.hostname}")
            self.host_obj.connect(hostname=self.hostname,
                                  username=self.username,
                                  password=self.password,
                                  timeout=timeout,
                                  **kwargs)
            if shell:
                self.shell_obj = self.host_obj.invoke_shell()

        except socket.timeout as timeout_exception:
            log.error("Could not establish connection because of timeout: %s",
                      timeout_exception)
            self.reconnect(retry, shell=shell, timeout=timeout, **kwargs)
        except Exception as error:
            log.error("Exception while connecting to server")
            log.error(f"Error message: {error}")
            if shell:
                self.host_obj.close()
            if not isinstance(shell, bool):
                shell.close()
            raise error

    def connect_pysftp(self, private_key: str = None, private_key_pass: str = None) -> None:
        """
        Connect to remote host using pysftp.
        :param private_key: path to private key file(str) or paramiko.AgentKey
        :param private_key_pass:  password to use, if private_key is encrypted
        """
        log.debug(f"Connecting to host: {self.hostname}")
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        result = pysftp.Connection(host=self.hostname,
                                   username=self.username,
                                   password=self.password,
                                   private_key=private_key,
                                   private_key_pass=private_key_pass,
                                   cnopts=cnopts)
        self.host_obj = result

    def disconnect(self) -> None:
        """
        Disconnects the host obj.
        """
        if self.shell_obj is not None:
            self.shell_obj.close()
        self.host_obj.close()
        self.host_obj = None
        self.shell_obj = None

    def reconnect(self, retry_count: int, **kwargs) -> None:
        """
        This method re-connect to host machine
        :param retry_count: host retry count
        """
        while retry_count:
            try:
                self.connect(**kwargs)
                break
            except:
                log.debug("Attempting to reconnect")
                retry_count -= 1
                time.sleep(1)

    def execute_cmd(self, cmd: str, inputs: str = None, read_lines: bool = False,
                    read_nbytes: int = -1, timeout: int = 400, **kwargs) -> Tuple[Union[List[str], str, bytes]]:
        """
        If connection is not established,  it will establish the connection and 
        Execute any command on remote machine/VM
        :param cmd: command user wants to execute on host.
        :param read_lines: Response will be return using readlines() else using read().
        :param inputs: used to pass yes argument to commands.
        :param nbytes: nbytes returns string buffer.
        :param timeout: command and connect timeout.
        :param read_nbytes: maximum number of bytes to read.
        :return: stdout/strerr.
        """
        self.connect(timeout=timeout, **kwargs)
        stdin, stdout, stderr = self.host_obj.exec_command(cmd, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status()
        log.debug(exit_status)
        if exit_status != 0:
            err = stderr.readlines()
            err = [r.strip().strip("\n").strip() for r in err]
            log.debug("Error: %s" % str(err))
            if err:
                raise IOError(err)
            raise IOError(stdout.readlines())
        else:
            if inputs:
                stdin.write('\n'.join(inputs))
                stdin.write('\n')
                stdin.flush()
            if read_lines:
                return stdout.readlines()
            else:
                return stdout.read(read_nbytes)
