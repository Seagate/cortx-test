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
import os
import re
import shutil
import subprocess
import time
import random
import socket
import configparser
import paramiko
import pysftp
import posixpath
import stat
import json
import yaml
import mdstat
from hashlib import md5
from subprocess import Popen, PIPE
import xml.etree.ElementTree
from configparser import ConfigParser
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
# salt functions
################################################################################
def get_pillar_values(
        self,
        component,
        keys,
        decrypt=False,
        host=CM_CFG["host"],
        username=CM_CFG["username"],
        password=CM_CFG["password"]):
    """
    Fetch pillar values for given keys from given component
    :param str component: name of pillar component to fetch value from
    :param list keys: list of level wise nested keys e.g., [0th level, 1st level,..]
    :param bool decrypt: True for decrypted output
    :param str host: hostname or IP of remote host
    :param str username: username of the host
    :param str password: password of the host
    :return: True/False and pillar output value
    :rtype: bool, str
    """
    pillar_key = ":".join([component, *keys])
    get_pillar_cmd = "salt-call pillar.get {} --output=newline_values_only".format(
        pillar_key)
    logger.info(
        "Fetching pillar value with cmd: {}".format(get_pillar_cmd))
    output = self.remote_execution(
        host=host,
        user=username,
        password=password,
        cmd=get_pillar_cmd,
        shell=False)
    if not output:
        err_msg = "Pillar value not found for {}".format(pillar_key)
        return False, err_msg

    pillar_value = output[0].strip("\n")
    logger.info(
        "Pillar value for {} is {}".format(
            pillar_key, pillar_value))
    if decrypt:
        if len(pillar_value) != 100:
            err_msg = "Invalid Token passed for decryption: {}".format(
                pillar_value)
            return False, err_msg
        decrypt_cmd = "salt-call lyveutil.decrypt {} {} --output=newline_values_only".format(
            component, pillar_value)
        output = self.remote_execution(
            host=host,
            user=username,
            password=password,
            cmd=decrypt_cmd,
            shell=False)
        pillar_value = output[0].strip("\n")
        logger.info(
            "Decrypted Pillar value for {} is {}".format(
                pillar_key, pillar_value))

    return True, pillar_value