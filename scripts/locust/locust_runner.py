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

import os
import argparse
import subprocess
import configparser

locust_cfg = configparser.ConfigParser()
locust_cfg.read('scripts/Locust/locust_config.ini')


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
    host_url = locust_cfg['default']['ENDPOINT_URL']
    hatch_rate = int(locust_cfg['default']['HATCH_RATE'])
    log_file = locust_cfg['default']['LOGFILE']
    ulimit_cmd = "ulimit -n 100000"
    locust_cmd = "locust --host={} -f {} --no-web -c {} -r {} --run-time {} --only-summary > {} 2>&1"

    parser = argparse.ArgumentParser(description='Run locust tool.')
    parser.add_argument('file_path', help='locust.py file path')
    parser.add_argument('--h', dest='host_url', help='host URL', nargs='?', const=host_url,
                        type=str, default=host_url)
    parser.add_argument('--u', dest='user_count', help='number of Locust users to spawn', nargs='?',
                        type=int)
    parser.add_argument('--r', dest='hatch_rate', help='specifies the hatch rate (number of users to spawn per second)',
                        nargs='?', const=hatch_rate, type=int, default=hatch_rate)
    parser.add_argument('--t', dest='duration', help='specify the run time for a test, eg:1h30m', nargs='?',
                        type=str)
    parser.add_argument('--l', dest='log_file', help='specify the path to store logs', nargs='?',
                        const=log_file, type=str, default=log_file)

    args = parser.parse_args()

    os.write(1, str.encode("Setting ulimit for locust\n"))
    ulimit_command = ulimit_cmd
    locust_command = locust_cmd.format(args.host_url, args.file_path, args.user_count, args.hatch_rate, args.duration, args.log_file)
    cmd = "{}; {}\n".format(ulimit_command, locust_command)
    run_cmd(cmd)
