#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Library for integrating jmeter with the framework
"""

import string
import os
import logging
import re
from commons.commands import JMX_CMD
from commons.utils import system_utils
from config import JMETER_CFG, CSM_REST_CFG


class JmeterInt():
    """Class for integrating jmeter with the framework
    """

    def __init__(self):
        """Initialization of attributes
        """
        self.log = logging.getLogger(__name__)
        self.jmeter_path = JMETER_CFG["jmeter_path"]
        self.jmx_path = JMETER_CFG["jmx_path"]
        self.jtl_log_path = JMETER_CFG["jtl_log_path"]

    def append_log(self, log_file: str):
        """Append and verify log to the log file.

        :param log_file: log file name
        """
        with open(log_file) as file:
            content = file.read()
        self.log.debug(content)

    def run_jmx(self, jmx_file: str):
        """Set the user properties and run the jmx file and verify the logs

        :param jmx_file: jmx file located in the JMX_PATH
        :return [tuple]: boolean, Error message
        """
        content = {"test.environment.hostname": JMETER_CFG["mgmt_vip"],
                   "test.environment.port": CSM_REST_CFG["port"],
                   "test.environment.protocol": "https",
                   "test.environment.adminuser": JMETER_CFG["csm_admin_user"]["username"],
                   "test.environment.adminpswd": JMETER_CFG["csm_admin_user"]["password"]}
        self.log.info("Updating : %s ", content)
        resp = self.update_user_properties(content)
        if not resp:
            return False, "Failed to update the file."

        self.log.info(self.parse_user_properties())
        jmx_file_path = os.path.join(self.jmx_path, jmx_file)
        self.log.info("JMX file : %s", jmx_file_path)
        log_file = jmx_file.split(".")[0] + ".jtl"
        log_file_path = os.path.join(self.jtl_log_path, log_file)
        self.log.info("Log file name : %s ", log_file_path)
        cmd = JMX_CMD.format(self.jmeter_path, jmx_file_path, log_file_path, self.jtl_log_path)
        self.log.info("Executing JMeter command : %s", cmd)
        result, resp = system_utils.run_local_cmd(cmd)
        self.log.info("Verify if any errors are reported...")
        if result:
            self.log.info("Jmeter execution completed.")
            result = re.match(r"Err:\s*0\s*.*", resp) is not None
        self.log.info("No Errors are reported in the Jmeter execution.")
        self.append_log(log_file_path)
        return resp

    def update_user_properties(self, content: dict):
        """Update the user.properties file in the JMX_PATH/bin

        :param content: content to be updated. Below new parameter are added to user.properties.
        {"test.environment.hostname": <Server machine IP address> ,
         "test.environment.port": <REST API Port number>,
         "test.environment.protocol": "https" / "hhtp",
         "test.environment.adminuser": <CSM admin user name>,
         "test.environment.adminpswd": <CSM Admin password>}
        :return [bool]: True is updated successfully.
        """
        result = False
        try:
            lines = self.read_user_properties()
            counter = len(lines) + 1
            for key, value in content.items():
                key = key.translate({ord(c): None for c in string.whitespace})
                if isinstance(value, str):
                    value = value.translate({ord(c): None for c in string.whitespace})
                updated = False
                for index, line in enumerate(lines):
                    if key in line:
                        lines[index] = key + " = " + str(value) + "\n"
                        updated = True
                if not updated:
                    lines.append(key + " = " + str(value) + "\n")
                    counter = counter + 1

            fpath = os.path.join(self.jmeter_path, "user.properties")
            with open(fpath, 'w') as file:
                self.log.info("Writing : %s", lines)
                file.writelines(lines)
            read_lines = self.read_user_properties()
            return read_lines == lines
        except Exception:
            self.log.error("Failed in updating the file")
        return result

    def parse_user_properties(self):
        """Read and parse the contents of the JMX_PATH/bin/user.properties file

        :return [dict]: return dictionary of the key value pairs.
        """
        lines = self.read_user_properties()
        content = {}
        for line in lines:
            if line[0] != "#" and "=" in line:
                key, value = line.split("=")
                key = key.translate({ord(c): None for c in string.whitespace})
                value = value.translate({ord(c): None for c in string.whitespace})
                content.update({key: value})
        return content

    def read_user_properties(self):
        """Read the JMX_PATH/bin/user.properties file

        :return [list]: returns list of lines in the file.
        """
        fpath = os.path.join(self.jmeter_path, "user.properties")
        with open(fpath) as stream:
            lines = stream.readlines()
        return lines
