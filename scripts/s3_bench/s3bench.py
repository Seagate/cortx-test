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
#

"""Script will be responsible to invoke and execute s3bench tool."""

import argparse
import logging
import os
from datetime import datetime, timedelta

from commons.utils import assert_utils
from commons.utils.config_utils import read_yaml
from commons.utils.system_utils import path_exists, run_local_cmd, make_dirs
from libs.s3 import ACCESS_KEY, SECRET_KEY

LOGGER = logging.getLogger(__name__)
cfg_obj = read_yaml("scripts/s3_bench/config.yaml")[1]
LOG_DIR = cfg_obj["log_dir"]
S3_BENCH_PATH = cfg_obj["s3bench_path"]
S3_BENCH_BINARY = cfg_obj["s3bench_binary"]


def setup_s3bench():
    """
    Configuring client machine with s3bench dependencies.

    :return bool: True/False
    """
    ret = run_local_cmd("s3bench --help")
    if not ret[0]:
        LOGGER.info("ERROR: s3bench is not installed. Installing s3bench.")
        ret = os.system(f"wget -O {S3_BENCH_PATH} {S3_BENCH_BINARY}")
        if ret:
            LOGGER.error("ERROR: Unable to download s3bench binary from github")
            return False
        ret = run_local_cmd(f"chmod +x {S3_BENCH_PATH}")
        if not ret[0]:
            LOGGER.error("ERROR: Unable to add execute permission to s3bench")
            return False
        ret = os.system("s3bench --help")
        if ret:
            LOGGER.error("ERROR: Unable to install s3bench")
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
                     access_key=ACCESS_KEY, secret_key=SECRET_KEY, validate_certs=True):
    """S3bench Workload worker can be used to run multiple workloads in parallel"""
    LOGGER.info("Workload: %s objects of %s with %s parallel clients", sample, object_size, client)
    resp = s3bench(access_key, secret_key, bucket=f"{bucket_name}", num_clients=client,
                   num_sample=sample, obj_name_pref="loadgen_test_", obj_size=object_size,
                   skip_cleanup=False, log_file_prefix=log_prefix, end_point=end_point,
                   validate_certs=validate_certs)
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
    LOGGER.info("Debug: Log File Path %s", file_path)
    resp_filtered = []
    with open(file_path, "r") as s3blog_obj:
        for line in s3blog_obj:
            for error in errors:
                if error.lower() in line.lower():
                    error_found = True
                    LOGGER.error("%s Found in S3Bench Run: %s", error, line)
                    return error_found
            if 'Errors Count:' in line and "reportFormat" not in line:
                resp_filtered.append(line)
    LOGGER.info("'Error count' filtered list: %s", resp_filtered)
    for response in resp_filtered:
        error_found = int(response.split(":")[1].strip()) != 0
    if not resp_filtered:
        error_found = True

    return error_found


# pylint: disable=too-many-arguments
# pylint: disable-msg=too-many-locals
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
        region="us-east-1",
        log_file_prefix="",
        validate_certs=True,
        **kwargs):
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
    :param region: Region name
    :param log_file_prefix: Test number prefix for log file
    :param validate_certs: Validate SSL certificates
    :keyword int max_retries: maximum retry for any request
    :keyword int response_header_timeout: Response header Timeout in ms
    :return: tuple with json response and log path
    """
    max_retries = kwargs.get("max_retries", None)
    response_header_timeout = kwargs.get("response_header_timeout", None)
    result = []
    # Creating log file
    log_path = create_log(result, log_file_prefix, num_clients, num_sample, obj_size)
    LOGGER.info("Running s3 bench tool")
    # GO command formatter
    cmd = f"s3bench -accessKey={access_key} -accessSecret={secret_key} " \
          f"-bucket={bucket} -endpoint={end_point} -numClients={num_clients} " \
          f"-numSamples={num_sample} -objectNamePrefix={obj_name_pref} -objectSize={obj_size} " \
          f"-skipSSLCertVerification={not validate_certs} "
    if max_retries:
        cmd = cmd + f"-s3MaxRetries={max_retries} "
    if response_header_timeout:
        cmd = cmd + f"-responseHeaderTimeout={response_header_timeout} "
    if region:
        cmd = cmd + f"-region {region} "
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
    parser.add_argument(
        "--vc",
        dest="validateCertificates",
        help="validate SSL certificate. (default: True)",
        action="store_true",
        default=True)
    s3arg = parser.parse_args()
    # Calling s3bench with passed cli options
    LOGGER.info("Starting S3bench run.")
    res = s3bench(
        access_key=s3arg.accessKey,
        secret_key=s3arg.accessSecret,
        bucket=s3arg.bucket,
        end_point=s3arg.endpoint,
        num_clients=s3arg.nClients,
        num_sample=s3arg.numSamples,
        obj_name_pref=s3arg.objectNamePrefix,
        obj_size=s3arg.objectSize,
        region=s3arg.region,
        skip_cleanup=s3arg.skipCleanup,
        duration=s3arg.duration,
        verbose=s3arg.verbose,
        validate_certs=s3arg.validateCertificates)
    LOGGER.info("Detailed log file path: %s", res[1])
    LOGGER.info("S3bench run ended.")
