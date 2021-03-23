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
"""
Locust runner file
"""

import os
import argparse
import subprocess
import time
from scripts.locust import LOCUST_CFG


def run_cmd(cmd):
    """
    Execute Shell command
    :param str cmd: cmd to be executed
    :return: output of command from console
    :rtype: str
    """
    os.write(1, str.encode(cmd))
    proc = subprocess.Popen(cmd, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    result = str(proc.communicate())
    return result


if __name__ == '__main__':
    HOST_URL = LOCUST_CFG['default']['ENDPOINT_URL']
    HATCH_RATE = int(LOCUST_CFG['default']['HATCH_RATE'])
    LOG_FILE = "".join([LOCUST_CFG['default']['LOGFILE'],
                        str(time.strftime("-%Y%m%d-%H%M%S")), ".log"])
    HTML_FILE = "".join([LOCUST_CFG['default']['HTMLFILE'], str(
        time.strftime("-%Y%m%d-%H%M%S")), ".html"])
    ULIMIT_CMD = "ulimit -n 100000"
    LOCUST_RUN_CMD = \
        "locust --host={} -f {} --headless -u {} -r {} --run-time {} --html {} --logfile {}"

    parser = argparse.ArgumentParser(description='Run locust tool.')
    parser.add_argument('file_path', help='locust.py file path')
    parser.add_argument('--host', dest='host_url', help='host URL', nargs='?', const=HOST_URL,
                        type=str, default=HOST_URL)
    parser.add_argument(
        '--u', dest='user_count', help='number of Locust users to spawn', nargs='?', type=int)
    parser.add_argument(
        '--r', dest='hatch_rate',
        help='specifies the hatch rate (number of users to spawn per second)',
        nargs='?', const=HATCH_RATE, type=int, default=HATCH_RATE)
    parser.add_argument(
        '--t', dest='duration', help='specify the run time for a test, eg:1h30m',
        nargs='?', type=str)
    parser.add_argument(
        '--logfile', dest='log_file', help='specify the path to store logs', nargs='?',
        const=LOG_FILE, type=str, default=LOG_FILE)

    args = parser.parse_args()

    os.write(1, str.encode("Setting ulimit for locust\n"))
    LOCUST_RUN_CMD = LOCUST_RUN_CMD.format(
        args.host_url,
        args.file_path,
        args.user_count,
        args.hatch_rate,
        args.duration,
        HTML_FILE,
        args.log_file)
    CMD = "{}; {}\n".format(ULIMIT_CMD, LOCUST_RUN_CMD)
    run_cmd(CMD)
