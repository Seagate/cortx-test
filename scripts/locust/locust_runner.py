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
"""
Locust runner file
"""
import argparse
import logging
import time

from commons.utils.system_utils import run_local_cmd
from scripts.locust import LOCUST_CFG

LOGGER = logging.getLogger(__name__)


def check_log_file(file_path, errors):
    """
    Function to find out error is reported in given file or not
    :param str file_path: the file in which error is to be searched
    :param list errors: error strings to be searched for
    :return: errorFound: True (if error is seen) else False
    :rtype: Boolean
    """
    error_found = False
    LOGGER.info("Debug: Log File Path %s", file_path)
    with open(file_path, "r") as log_file:
        for line in log_file:
            for error in errors:
                if error.lower() in line.lower():
                    error_found = True
                    LOGGER.info("checkLogFileError: Error Found in Locust Run : %s", line)
                    return error_found

    LOGGER.info("No Error Found")
    return error_found


def run_locust(
        test_id: str, host: str, locust_file: str, users: int, hatch_rate: int = 1,
        duration: str = "3m") -> tuple:
    """
    Function to run locust.
    :param test_id: test number
    :param host: host FQDN
    :param locust_file: path to the locust file
    :param users: number of concurrent users
    :param hatch_rate: rate at which number of user to be increase per sec
    :param duration: total time for execution
    :return: tupple resp with over all execution and log and html file path
    """
    upper_limit_cmd = "ulimit -n 100000"
    log_dir = "log/latest/"
    time_str = str(time.strftime("%Y%m%d-%H%M%S"))
    log_file = f"{log_dir}{test_id}-{LOCUST_CFG['default']['LOGFILE']}-{time_str}.log"
    html_file = f"{log_dir}{test_id}-{LOCUST_CFG['default']['HTMLFILE']}-{time_str}.html"
    locust_run_cmd = \
        "locust --host={} -f {} --headless -u {} -r {} --run-time {} --html {} --logfile {}"
    LOGGER.info("Setting ulimit for locust\n")
    locust_run_cmd = locust_run_cmd.format(
        host,
        locust_file,
        int(users),
        hatch_rate,
        duration,
        html_file,
        log_file)
    cmd = "{}; {}\n".format(upper_limit_cmd, locust_run_cmd)
    res = run_local_cmd(cmd)
    LOGGER.info("Locust run completed.")
    res1 = {"log-file": log_file, "html-file": html_file}

    return res, res1


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

    LOGGER.info("Setting ulimit for locust\n")
    LOCUST_RUN_CMD = LOCUST_RUN_CMD.format(
        args.host_url,
        args.file_path,
        args.user_count,
        args.hatch_rate,
        args.duration,
        HTML_FILE,
        args.log_file)
    CMD = "{}; {}\n".format(ULIMIT_CMD, LOCUST_RUN_CMD)
    run_local_cmd(CMD)
    LOGGER.info("Locust run completed.")
