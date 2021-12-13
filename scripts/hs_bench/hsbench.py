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
#

"""Script will be responsible to invoke hsbench tool."""

import argparse
import logging
from datetime import datetime, timedelta
import pandas as pd

from commons.utils import assert_utils
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import path_exists, run_local_cmd, make_dirs, remove_dirs
from libs.s3 import ACCESS_KEY, SECRET_KEY

LOGGER = logging.getLogger(__name__)
cfg_obj = read_yaml("scripts/hs_bench/config.yaml")[1]
LOG_DIR = cfg_obj["log_dir"]

def create_log(resp, log_file_prefix, size):
    """
    To create log file for hsbench run
    :param resp: List of string response
    :param log_file_prefix: Log file prefix
    :param client: number of clients
    :param samples: number of samples
    :param size: object size
    :return: Path of the log file
    """
    if not path_exists(LOG_DIR):
        make_dirs(LOG_DIR)

    now = datetime.now().strftime("%d-%m-%Y-%H-%M-%S-%f")
    path = f"{LOG_DIR}{log_file_prefix}_hsbench_{size}_{now}.log"
    # Writing complete response in file, appends response in case of duration
    # given
    with open(path, "a") as fd_write:
        for i in resp:
            fd_write.write(i)

    return path

def check_log_file_error(file_path, errors=None):
    """
    Function to find out error is reported in given file or not
    :param str file_path: the file in which error is to be searched
    :param list(str) errors: error strings to be searched for
    :return: errorFound: True (if error is seen) else False
    :rtype: Boolean
    """
    if not errors:
        errors = ["failed ", "panic", "status code",
                  "does not exist", "InternalError", "ServiceUnavailable"]
    error_found = False
    LOGGER.info("Debug: Log File Path {}".format(file_path))
    resp_filtered = []
    with open(file_path, "r") as hsLogFile:
        for line in hsLogFile:
            for error in errors:
                if error.lower() in line.lower():
                    error_found = True
                    LOGGER.error(f"{error} Found in HSBench Run : {line}")
                    return error_found
    return error_found

def hsbench(
        access_key,
        secret_key,
        end_point="https://s3.seagate.com",
        obj_size="4K",
        test_duration=10,
        threads=10,
        bucket=1,
        json_path="file1",
        duration=None,
        log_file_prefix=""):
    """
    To run hsbench tool
    :param access_key: S3 access key
    :param secret_key: S3 secret key
    :param end_point: Endpoint for the operations
    :param obj_size: Object size to be used e.g. 1Kb, 2Mb, 4Gb
    :test_duration: Maximum test duration in seconds <-1 for unlimited> (default 60)
    :param threads: Number of threads to run
    :param bucket: Number of buckets to distribute IOs across
    :param log_file_prefix: Test number prefix for log file
    :json_path: Write JSON output to this file
    :return: tuple with json response and log path
    """
    result = []
    # Creating log file
    log_path = create_log(result, log_file_prefix, obj_size)
    LOGGER.info("Running hs bench tool")
    # GO command formatter
    cmd = f"./hsbench -a={access_key} -s={secret_key} " \
          f"-u={end_point} -d={test_duration} -z={obj_size} -t={threads} -b={bucket} -j={json_path} "

    cmd = f"{cmd}>> {log_path} 2>&1"

    # In case duration is None
    if not duration:
        duration = "0h0m"

    # Calculating execution time based on the duration given
    hour, mins = duration.lower().replace("h", ":").replace("m", "").split(":")
    dur_time = str(
        datetime.now() +
        timedelta(
            hours=int(hour),
            minutes=int(mins)))[11:19]

    # Executing hsbench based on the current time and expected duration time
    # calculated
    while str(datetime.now())[11:19] <= dur_time:
        res1 = run_local_cmd(cmd)
        LOGGER.debug("Response: %s", res1)
        result.append(res1[1])

    return json_path, log_path

def parse_hsbench_output(file_path):
    """
    To parse hsbench output
    :file_path: Generated JSON file after hsbench tool
    :return: dictionary/list of the content
    """
    try:
        json_data = []
        keys = ['Mode', 'Seconds', 'Ops', 'Mbps',
                'Iops', 'MinLat', 'AvgLat', 'MaxLat']
        values = []
        with open(file_path, 'r') as list_ops:
            json_data = json.load(list_ops)
        for data in json_data:
            value = []
            if(data['IntervalName'] == 'TOTAL'):
                for key in keys:
                    value.append(data[key])
                values.append(value)
        table_op = pd.DataFrame(values, columns=keys)
        table_op.reset_index(inplace=False)
        data_dict = table_op.to_dict("records")
        return data_dict

    except Exception as exc:
        print(f"Encountered error in file: {file_path} , and Exeption is" , exc)

#Todo not supported more than 2 mode_type
def parse_metrics_value(metric_name, mode_type, operation, parse_data):
    """
    :param metric_name: Name of Metrics 
    :param mode_type:list(str): Type of Mode i.e GET, PUT, BINIT, LIST
    :param operation: Type of operation i.e Mbps, Iops, Ops, AvgLat
    :param parse_data: dictionary/list of the content
    :return: tuple with metrics name, value and time
    """
    if len(mode_type) == 1:
        for in_line_data in parse_data:
            if in_line_data['Mode'] == mode_type[0]:
                if in_line_data[operation]:
                    return metric_name, str(in_line_data[operation]), in_line_data['Seconds']
    else:
        vv1 = []
        tt1 = []
        for in_line_data in parse_data:
            for modes in mode_type:
                if in_line_data['Mode'] == modes:
                    if in_line_data[operation]:
                        vv1.append(int(in_line_data[operation]))
                        tt1.append(int(in_line_data['Seconds']))
        return metric_name, str(vv1[0]+vv1[1]), tt1[0]+tt1[1]
