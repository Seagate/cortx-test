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
# Interface Classes
################################################################################

class Host():
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
                                  port=22,
                                  timeout=30,
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

