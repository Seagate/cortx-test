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

################################################################################
# Standard libraries
################################################################################
import logging
import paramiko
import os
import re
import shutil
import subprocess
import time
import random
import socket

import pysftp
import posixpath
import stat
import mdstat
from hashlib import md5
from subprocess import Popen, PIPE

################################################################################
# Local libraries
################################################################################
from eos_test.provisioner import constants
from eos_test.s3 import constants as cons
from eos_test.ha import constants as ha_cons
from eos_test.ras import constants as ras_cons
from ctp.utils import ctpyaml


################################################################################
# Constants
################################################################################
log = logging.getLogger(__name__)

################################################################################
# Classes
################################################################################

class host():
    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.host_obj = None
    ############################################################################
    # remote connection options
    ############################################################################
    def connect(self, shell=True, **kwargs):
        """
        Connect to remote host.
        :param host: host ip address
        :type host: str
        :param username: host username
        :type username: str
        :param password: host password
        :type password: str
        :param shell: In case required shell invocation
        :return: Boolean, Whether ssh connection establish or not
        """
        try:
            self.host_obj = paramiko.SSHClient()
            self.host_obj.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            log.debug(f"Connecting to host: {host}")
            self.host_obj.connect(hostname=self.hostname, 
                                  username=self.username, 
                                  password=self.password,
                                  **kwargs)
            if shell:
                shell = self.host_obj.invoke_shell()
        except paramiko.AuthenticationException:
            log.error(constants.SERVER_AUTH_FAIL)
            result = False
        except paramiko.SSHException as ssh_exception:
            log.error(
                "Could not establish ssh connection: %s",
                ssh_exception)
            result = False
        except socket.timeout as timeout_exception:
            log.error(
                "Could not establish connection because of timeout: %s",
                timeout_exception)
            result = False
        except Exception as error:
            log.error(constants.SERVER_CONNECT_ERR)
            log.error(f"Error message: {error}")
            result = False
            if shell:
                self.host_obj.close()
            if not isinstance(shell, bool):
                shell.close()
        else:
            result = True
        return result

    def connect_pysftp(self, private_key=None, private_key_pass=None):
        """
        Connect to remote host using pysftp
        :param str host: The Hostname or IP of the remote machine
        :param str username: Your username at the remote machine
        :param str pwd: Your password at the remote machine
        :param str private_key: path to private key file(str) or paramiko.AgentKey
        :param str private_key_pass:  password to use, if private_key is encrypted
        :return: connection object based on the success
        :rtype: pysftp.Connection
        """
        try:
            log.debug(f"Connecting to host: {host}")
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None
            result = pysftp.Connection( host=self.hostname,
                                        username=self.username,
                                        password=self.password,
                                        private_key=private_key,
                                        private_key_pass=private_key_pass,
                                        cnopts=cnopts)
            self.host_obj = result
            result = True
        except socket.timeout as timeout_exception:
            log.error(
                "Could not establish connection because of timeout: %s",
                timeout_exception)
            result = False
        except Exception as error:
            log.error(constants.SERVER_CONNECT_ERR)
            log.error(f"Error message: {error}")
            result = False
        return result

    ################################################################################
    # remote execution
    ################################################################################
    def execute_cmd(self, cmd, read_lines=True, read_nbytes=-1):
        """
        Execute any command on remote machine/VM
        :param host: Host IP
        :param user: Host user name
        :param password: Host password
        :param cmd: command user wants to execute on host
        :param read_lines: Response will be return using readlines() else using read()
        :return: response
        """
        try:
            stdin, stdout, stderr = self.host_obj.exec_command(cmd)
            if read_lines:
                result = stdout.readlines()
            else:
                result = stdout.read(read_nbytes)
            return result
        except BaseException as error:
            log.error(error)
            return error

    ################################################################################
    # remote file operations
    ################################################################################
    def create_file(self, file_name, count):
        """
        Creates a new file, size(count) in MB
        :param str file_name: Name of the file with path
        :param int count: size of the file in MB
        :return: output of remote execution cmd
        :rtype: str:
        """
        cmd = "dd if=/dev/zero of={} bs=1M count={}".format(file_name, count)
        log.debug(cmd)
        if remote:
            result = self.execute_cmd(
                host=self.hostname,
                user=self.username,
                password=self.password,
                cmd=cmd,
                shell=False)
        else:
            result = self.run_cmd(cmd)
        log.debug("output = {}".format(result))
        return result

    def copy_file_to_remote(
            self,
            local_path,
            remote_file_path,
            host=CM_CFG["host"],
            user=CM_CFG["username"],
            pwd=CM_CFG["password"],
            shell=True):
        """
        copy file from local to local remote
        :param str local_path: local path
        :param str remote_file_path: remote path
        :param str host: host ip or domain name
        :param str user: host machine user name
        :param str pwd: host machine password
        :return: boolean, remote_path/error
        :rtype: tuple
        """
        try:
            client = self.connect(
                host, username=user, password=pwd, shell=shell)
            log.info("client connected")
            sftp = client.open_sftp()
            log.info("sftp connected")
            sftp.put(local_path, remote_file_path)
            log.info("file copied to : {}".format(remote_file_path))
            sftp.close()
            client.close()
            return True, remote_file_path
        except BaseException as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.copy_file_to_remote.__name__,
                error))
            return False, error

    ################################################################################
    # remote directory operations
    ################################################################################
    def is_directory_exists(self, path, dir_name, remote_machine=False):
        """
        This function is use to check directory is exist or not
        :param path: path of directory
        :type path: string
        :param dir_name: directory name
        :type dir_name: string
        :return: boolean True if directory find, False otherwise.
        """
        try:
            if remote_machine:
                out_flag, directories = self.execute_command(
                    command=f"ls {path}", host=PRVSNR_CFG['machine1'])
            else:
                out_flag, directories = self.execute_command(
                    command=f"ls {path}")
            # decode utf 8 is to convert bytes to string
            # directories = (directories.decode("utf-8")).split("\n")
            directories = (directory.split("\n")[0]
                           for directory in directories)
            if dir_name in directories:
                return True
            else:
                return False
        except Exception as error:
            log.error("{} {}: {}".format(
                cons.EXCEPTION_ERROR, Utility.is_directory_exists.__name__,
                error))
            return False

    ################################################################################
    # Remote process operations
    ################################################################################
    def kill_remote_process(self, process_name, host=CM_CFG["host"],
                            user=CM_CFG["username"], pwd=CM_CFG["password"]):
        """
        Kill all process matching the process_name at s3 server
        :param process_name: Name of the process to be killed
        :param host: IP of the host
        :param user: user name of the host
        :param pwd: password for the user
        :return:
        """
        return self.remote_execution(
            host, user, pwd, cons.PKIL_CMD.format(process_name))