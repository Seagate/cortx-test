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

import logging
from datetime import datetime
import json
import pandas as pd

from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import path_exists, run_local_cmd, make_dirs

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
    with open(path, "a", encoding="utf-8") as fd_write:
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
                  "does not exist", "InternalError", "send request failed"]
    error_found = False
    LOGGER.info("Debug: Log File Path %s",file_path)
    with open(file_path, "r", encoding="utf-8") as hs_log_file:
        for line in hs_log_file:
            for error in errors:
                if error.lower() in line.lower():
                    error_found = True
                    LOGGER.error("%s Found in HSBench Run : %s",error, line)
                    return error_found
    return error_found

# pylint: disable-msg=too-many-arguments
# pylint: disable-msg=too-many-locals
def hsbench(
        access_key,
        secret_key,
        end_point="https://s3.seagate.com",
        obj_size="4K",
        test_duration=1,
        threads=1,
        bucket=1,
        json_path="file1",
        report_interval=1,
        mode_order=False,
        bucket_prefix=False,
        obj_name_pref=False,
        num_test_repeat=False,
        key_retrive_once_blist=False,
        no_objects=False,
        csv_path=False,
        region=False,
        log_file_prefix=""):
    """
    To run hsbench tool
    :param access_key: S3 access key
    :param secret_key: S3 secret key
    :param end_point: Endpoint for the operations
    :param obj_size: Object size to be used e.g. 1Kb, 2Mb, 4Gb
    :param test_duration: Maximum test duration in seconds <-1 for unlimited>
                          (default 60)
    :param threads: Number of threads to run
    :param bucket: Number of buckets to distribute IOs across
    :param json_path: Write JSON output to this file
    :param report_interval(float): Number of seconds between report intervals
                                   (default 1)
    :param mode_order(str): Run modes in order.  See NOTES for more info
                            (default "cxiplgdcx")
    :param bucket_prefix(str): Prefix for buckets (default "hotsauce_bench")
    :param obj_name_pref(str): Prefix for objects
    :param num_test_repeat(int): Number of times to repeat test (default 1)
    :param key_retrive_once_blist(int): Maximum number of keys to retreive
                                        at once for bucket listings (default 1000)
    :param no_objects(int): Maximum number of objects <-1 for unlimited>
                            (default -1)
    :param csv_path(str): Write CSV output to this file
    :param region(str): Region for testing (default "us-east-1")
    :param log_file_prefix: Test number prefix for log file
    :return: tuple with json response and log path
    """
    result = []
    # Creating log file
    log_path = create_log(result, log_file_prefix, obj_size)
    LOGGER.info("Running hsbench tool")
    # GO command formatter
    cmd = f"./hsbench -a={access_key} -s={secret_key} " \
          f"-u={end_point} -d={test_duration} -z={obj_size} " \
          f"-t={threads} -b={bucket} -j={json_path} -ri={report_interval}"

    if mode_order:
        cmd = cmd + " -m=" + mode_order
    if bucket_prefix:
        cmd = cmd + " -bp=" + bucket_prefix
    if obj_name_pref:
        cmd = cmd + " -op=" + obj_name_pref
    if num_test_repeat:
        cmd = cmd + " -l=" + str(num_test_repeat)
    if key_retrive_once_blist:
        cmd = cmd + " -mk=" + str(key_retrive_once_blist)
    if no_objects:
        cmd = cmd + " -n=" + str(no_objects)
    if csv_path:
        cmd = cmd + " -o=" + csv_path
    if region:
        cmd = cmd + " -r=" + region

    cmd = f"{cmd}>> {log_path} 2>&1"

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
    json_data = []
    keys = ['Mode', 'Seconds', 'Ops', 'Mbps',
            'Iops', 'MinLat', 'AvgLat', 'MaxLat']
    values = []
    with open(file_path, 'r', encoding="utf-8") as list_ops:
        json_data = json.load(list_ops)
    for data in json_data:
        value = []
        if data['IntervalName'] == 'TOTAL':
            for key in keys:
                value.append(data[key])
            values.append(value)
    table_op = pd.DataFrame(values, columns=keys)
    table_op.reset_index(inplace=False)
    data_dict = table_op.to_dict("records")
    return data_dict

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
    vv1 = []
    tt1 = []
    for in_line_data in parse_data:
        for modes in mode_type:
            if in_line_data['Mode'] == modes:
                if in_line_data[operation]:
                    vv1.append(int(in_line_data[operation]))
                    tt1.append(int(in_line_data['Seconds']))
    return metric_name, str(vv1[0]+vv1[1]), tt1[0]+tt1[1]
