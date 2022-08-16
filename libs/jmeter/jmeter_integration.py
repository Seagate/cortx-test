#!/usr/bin/python
# -*- coding: utf-8 -*-
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
"""Library for integrating jmeter with the framework
"""

import string
import os
import logging
import re
import json
from commons.commands import JMX_CMD
from commons.utils import system_utils
from commons.utils import config_utils
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
        self.test_data_csv = JMETER_CFG["test_data_csv"]
        self.log_file_path = ""

    def append_log(self, log_file: str):
        """Append and verify log to the log file.

        :param log_file: log file name
        """
        with open(log_file) as file:
            content = file.read()
        self.log.debug(content)

    def run_jmx(self, jmx_file: str, threads:int=25, rampup:int=1, loop:int=1, test_cfg:str=None):
        """Set the user properties and run the jmx file
        :param jmx_file: jmx file located in the JMX_PATH
        :return [tuple]: response of command
        """
        if test_cfg is None:
            test_cfg = os.path.join(self.jmeter_path, self.test_data_csv)
        content = {"test.environment.hostname": JMETER_CFG["mgmt_vip"],
                   "test.environment.port": CSM_REST_CFG["port"],
                   "test.environment.protocol": "https",
                   "test.environment.adminuser": JMETER_CFG["csm_admin_user"]["username"],
                   "test.environment.adminpswd": JMETER_CFG["csm_admin_user"]["password"],
                   "test.environment.threads": threads,
                   "test.environment.rampup": rampup,
                   "test.environment.loop": loop,
                   "test.environment.config":test_cfg }
        self.log.info("Updating : %s ", content)
        resp = self.update_user_properties(content)
        if not resp:
            return False, "Failed to update the file."

        self.log.info(self.parse_user_properties())
        jmx_file_path = os.path.join(self.jmx_path, jmx_file)
        self.log.info("JMX file : %s", jmx_file_path)
        log_file = jmx_file.split(".")[0] + ".jtl"
        self.log_file_path = os.path.join(self.jtl_log_path, log_file)
        self.log.info("Log file name : %s ", self.log_file_path)
        cmd = JMX_CMD.format(self.jmeter_path, jmx_file_path, self.log_file_path, self.jtl_log_path)
        self.log.info("Executing JMeter command : %s", cmd)
        result, resp = system_utils.run_local_cmd(cmd, chk_stderr=True)
        if result:
            self.log.info("Jmeter execution completed.")
        else:
            assert result, "Failed to execute command."
        self.append_log(self.log_file_path)
        return resp

    # pylint: disable=too-many-arguments
    def run_verify_jmx(
        self,
        jmx_file: str,
        threads:int=25,
        rampup:int=1,
        loop:int=1,
        test_cfg:str=None
        ):
        """Set the user properties and run the jmx file and verify the logs
        :param jmx_file: jmx file located in the JMX_PATH
        :return [bool]: True if error count is expected in jmx result log
        """
        resp = self.run_jmx(jmx_file, threads, rampup, loop, test_cfg)
        resp = resp.replace("\\n","\n")
        summary_txt = re.findall(r"summary =\s*.*",resp)[-1]
        err_list = re.findall(r"Err:[^(]*", summary_txt)[-1]
        error_count = re.findall(r'\d+', err_list)[-1]
        result = (int(error_count) == 0)
        if result is False:
            self.log.info("error_counts : %s", error_count)
        return result

    # pylint: disable=too-many-arguments
    def run_verify_jmx_with_message(
        self,
        jmx_file: str,
        expect_count = 0,
        expect_message = "",
        threads:int=25,
        rampup:int=1,
        loop:int=1,
        test_cfg:str=None
        ):
        """Set the user properties and run the jmx file and verify the logs
        :param jmx_file: jmx file located in the JMX_PATH
        :return [bool]: True if error count is expected in jmx result log
        """
        self.run_jmx(jmx_file, threads, rampup, loop, test_cfg)
        result = False
        if os.path.exists(self.log_file_path):
            file = open(self.log_file_path, "r")
            message_count = file.read().count(expect_message)
            result = (message_count == expect_count)
            self.log.info("self.log_file_path : %s", self.log_file_path)
            if result is False:
                self.log.info("error_counts : %s", message_count)
                self.log.info("expect_error_count : %s", expect_count)
        return result

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

    def get_err_cnt(self,fpath):
        """
        Read the error count parameter from statistics.json file
        :param fpath: Statistics.json file path
        """
        data = config_utils.read_content_json(fpath)
        self.log.debug("Request Statistics : \n%s",json.dumps(data,indent=4, sort_keys=True))
        return int(data["Total"]["errorCount"]), int(data["Total"]["sampleCount"])
