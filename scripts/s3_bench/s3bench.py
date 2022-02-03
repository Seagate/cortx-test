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

"""Script will be responsible to invoke and execute s3bench tool."""

import argparse
import logging
from datetime import datetime, timedelta

from commons.utils import assert_utils
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import path_exists, run_local_cmd, make_dirs, remove_dirs
from libs.s3 import ACCESS_KEY, SECRET_KEY

LOGGER = logging.getLogger(__name__)
cfg_obj = read_yaml("scripts/s3_bench/config.yaml")[1]
LOG_DIR = cfg_obj["log_dir"]
S3_BENCH_PATH = cfg_obj["s3bench_path"]


def setup_s3bench(
        get_cmd=cfg_obj["s3bench_get"]):
    """
    Configuring client machine with s3bench dependencies.
    :param get_cmd: S3Bench go get command
    :return bool: True/False
    """
    LOGGER.debug("Installing go/s3bench.")
    # Install go
    ret = run_local_cmd(cfg_obj["cmd_go"])
    if not ret[0]:
        LOGGER.error("%s", ret[1])
        return False
    # Install go get for s3bench
    ret = run_local_cmd(get_cmd)
    if not ret[0]:
        LOGGER.error("%s", ret[1])
        return False
    ret = run_local_cmd(cfg_obj["s3bench_trust"])
    if not ret[0]:
        LOGGER.error("%s", ret[1])
        return False
    # Remove old directory if present
    if path_exists(S3_BENCH_PATH):
        resp = remove_dirs(S3_BENCH_PATH)
        if not resp:
            LOGGER.error("Unable to remove %s", S3_BENCH_PATH)
            return False
    ret = run_local_cmd(cfg_obj["s3bench_git"].format(S3_BENCH_PATH))
    if not ret[0]:
        LOGGER.error("%s", ret[1])
        return False

    return True


def create_log(resp, log_file_prefix, client, samples, size):
    """
    To create log file for s3bench run
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
    path = f"{LOG_DIR}{log_file_prefix}_s3bench_{client}_{samples}_{size}_{now}.log"
    # Writing complete response in file, appends response in case of duration
    # given
    with open(path, "a") as fd_write:
        for i in resp:
            fd_write.write(i)

    return path


def create_json_reps(list_resp):
    """
    Create json data
    :param list_resp:
    :return: json response
    """
    js_res = []
    ds_dict = {}
    LOGGER.debug("list response %s", list_resp)
    for res_el in list_resp:
        # Splitting each response
        split_res = res_el.split("\n")
        for ele in split_res:
            if ":" in ele:
                list_split = ele.replace("\n", "").split(":")
                # adding in single dictionary
                ds_dict[list_split[0]] = list_split[1].strip()
        # appending dictionary to list
        js_res.append(ds_dict)

    return js_res


# pylint: disable-msg=too-many-arguments
def s3bench_workload(end_point, bucket_name, log_prefix, object_size, client, sample,
                     access_key=ACCESS_KEY, secret_key=SECRET_KEY):
    """S3bench Workload worker can be used to run multiple workloads in parallel"""
    LOGGER.info("Workload: %s objects of %s with %s parallel clients", sample, object_size, client)
    resp = s3bench(access_key, secret_key, bucket=f"{bucket_name}", num_clients=client,
                   num_sample=sample, obj_name_pref="loadgen_test_", obj_size=object_size,
                   skip_cleanup=False, log_file_prefix=log_prefix, end_point=end_point)
    LOGGER.info("Log Path %s", resp[1])
    assert_utils.assert_false(check_log_file_error(resp[1]),
                              f"S3bench workload on bucket {bucket_name} with {client} "
                              f"client failed. Please read log file {resp[1]}")


def check_log_file_error(file_path, errors=None):
    """
    Function to find out error is reported in given file or not
    :param str file_path: the file in which error is to be searched
    :param list(str) errors: error strings to be searched for
    :return: errorFound: True (if error is seen) else False
    :rtype: Boolean
    """
    if not errors:
        errors = ["with error ", "panic", "status code",
                  "flag provided but not defined", "InternalError", "ServiceUnavailable"]
    error_found = False
    LOGGER.info("Debug: Log File Path {}".format(file_path))
    resp_filtered = []
    with open(file_path, "r") as s3LogFile:
        for line in s3LogFile:
            for error in errors:
                if error.lower() in line.lower():
                    error_found = True
                    LOGGER.error(f"{error} Found in S3Bench Run : {line}")
                    return error_found
            if 'Errors Count:' in line and "reportFormat" not in line:
                resp_filtered.append(line)
    LOGGER.info("'Error count' filtered list: %s", resp_filtered)
    for response in resp_filtered:
        error_found = int(response.split(":")[1].strip()) != 0
    if not resp_filtered:
        error_found = True

    return error_found


def s3bench(
        access_key,
        secret_key,
        bucket="bucketname",
        end_point="https://s3.seagate.com",
        num_clients=40,
        num_sample=200,
        obj_name_pref="loadgen_test_",
        obj_size="4Kb",
        skip_write=False,
        skip_cleanup=False,
        skip_read=False,
        validate=True,
        duration=None,
        verbose=False,
        log_file_prefix=""):
    """
    To run s3bench tool
    :param access_key: S3 access key
    :param secret_key: S3 secret key
    :param bucket: Bucket to be used
    :param end_point: Endpoint for the operations
    :param num_clients: Number of clients/workers
    :param num_sample: Number of read and write
    :param obj_name_pref: Name prefix for the object
    :param obj_size: Object size to be used e.g. 1Kb, 2Mb, 4Gb
    :param skip_read: Skip reading objects created in this run
    :param skip_cleanup: skip deleting objects created in this run
    :param skip_write: Skip writing objects
    :param validate: Validate checksum for the objects
        This option will download the object and give error if checksum is wrong
    :param duration: Execute same ops with defined time. 1h24m10s|0h22m0s else None
    :param verbose: verbose per thread status write and read
    :param log_file_prefix: Test number prefix for log file
    :return: tuple with json response and log path
    """
    result = []
    # Creating log file
    log_path = create_log(result, log_file_prefix, num_clients, num_sample, obj_size)
    LOGGER.info("Running s3 bench tool")
    # GO command formatter
    cmd = f"go run s3bench -accessKey={access_key} -accessSecret={secret_key} " \
          f"-bucket={bucket} -endpoint={end_point} -numClients={num_clients} " \
          f"-numSamples={num_sample} -objectNamePrefix={obj_name_pref} -objectSize={obj_size} "

    if skip_write:
        cmd = cmd + "-skipWrite "
    if skip_read:
        cmd = cmd + "-skipRead "
    if skip_cleanup:
        cmd = cmd + "-skipCleanup "
    if validate:
        cmd = cmd + "-validate "
    if verbose:
        cmd = cmd + "-verbose "
    cmd = f"{cmd}>> {log_path} 2>&1"
    LOGGER.info("Workload execution started.")
    if duration:
        if not duration.lower().endswith("s"):
            duration += "0s"
        # Calculating execution time based on the duration given
        hour, mins, secs = duration.lower().replace(
            "h", ":").replace("m", ":").replace("s", "").split(":")
        dur_time = datetime.now() + timedelta(hours=int(hour), minutes=int(mins), seconds=int(secs))
        # Executing s3bench based on the current time and expected duration time calculated.
        while datetime.now() <= dur_time:
            res1 = run_local_cmd(cmd)
            LOGGER.debug("Response: %s", res1)
            result.append(res1[1])
    else:  # In case duration is None
        res1 = run_local_cmd(cmd)
        LOGGER.debug("Response: %s", res1)
        result.append(res1[1])
    LOGGER.info("Workload execution completed.")

    # Creating json response this function skips the verbose data
    json_resp = create_json_reps(result)

    return json_resp, log_path


if __name__ == "__main__":
    # Parser for CLI
    parser = argparse.ArgumentParser(description="Run S3bench CLI tool.")
    parser.add_argument(
        "--a",
        dest="accessKey",
        action='store',
        help="the S3 access key",
        required=True)
    parser.add_argument(
        "--s",
        dest="accessSecret",
        action='store',
        help="the S3 access secret",
        required=True)
    parser.add_argument(
        "--b",
        dest="bucket",
        help="the bucket for which to run the test (default: bucketname)",
        nargs="?",
        type=str,
        required=True,
        default="bucketname")
    parser.add_argument(
        "--e",
        dest="endpoint",
        help="S3 endpoint(s) comma separated (default: https://s3.seagate.com)",
        action="store",
        default="https://s3.seagate.com")
    parser.add_argument(
        "--w",
        dest="nClients",
        help="number of concurrent clients (default: 40)",
        action="store",
        type=int,
        default=40)
    parser.add_argument(
        "--ns",
        dest="numSamples",
        help="total number of requests to send (default: 200)",
        action="store",
        type=int,
        default=200)
    parser.add_argument(
        "--np",
        dest="objectNamePrefix",
        help="prefix of the object name that will be used (default: loadgen_test_)",
        nargs="?",
        const="loadgen_test_",
        type=str,
        default="loadgen_test_")
    parser.add_argument(
        "--os",
        dest="objectSize",
        help="size of individual requests in bytes (must be smaller than main memory). (default: "
             "83886080)",
        nargs="?",
        const=83886080,
        type=int,
        default=83886080)
    parser.add_argument(
        "--t",
        dest="duration",
        help="specify the run time for a test, eg:1h30m. (default: None)",
        nargs="?",
        type=str,
        default=None)
    parser.add_argument(
        "--region",
        dest="region",
        help="AWS region to use, eg: us-west-1|us-east-1, etc (default: 'igneous-test')",
        nargs="?",
        const="US",
        type=str,
        default="igneous-test")
    parser.add_argument(
        "--sc",
        dest="skipCleanup",
        help="skip deleting objects created by this tool at the end of the run. (default: False)",
        action="store_true",
        default=False)
    parser.add_argument(
        "--v",
        dest="verbose",
        help="print verbose per thread status. (default: False)",
        action="store_true",
        default=False)
    s3arg = parser.parse_args()
    # Calling s3bench with passed cli options
    LOGGER.info("Starting S3bench run.")
    res = s3bench(
        s3arg.accessKey,
        s3arg.accessSecret,
        s3arg.bucket,
        s3arg.endpoint,
        s3arg.nClients,
        s3arg.numSamples,
        s3arg.objectNamePrefix,
        s3arg.objectSize,
        s3arg.region,
        s3arg.skipCleanup,
        s3arg.duration,
        s3arg.verbose)
    print("\n Detailed log file path: {}".format(res[1]))
    LOGGER.info("S3bench run ended.")
