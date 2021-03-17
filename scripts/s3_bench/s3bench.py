"""
Author: 720678<dhananjay.dandapat@seagate.com>
Date: 06 Feb 2020
Description: Script will be responsible to envoke and execute s3bench tool
"""

import os
import logging
from datetime import datetime, timedelta
import argparse
from ctp.utils import ctpyaml
from eos_test.utility import utility

UT_OBJ = utility.Utility()
logger = logging.getLogger(__name__)
cfg_obj = ctpyaml.read_yaml("scripts/s3_bench/config.yaml")

LOG_DIR = cfg_obj["log_dir"]


def setup_s3bench(
        get_cmd=cfg_obj["s3bench_get"],
        git_url=cfg_obj["s3bench_git"],
        path=cfg_obj["go_path"]):
    """
    Configurig client machine with s3bench dependencies.
    :param string get_cmd: S3Bench go get command
    :param string git_url: S3Bench git url command
    :param string path: Go src path
    :return bool: True/False
    """
    try:
        if not (
            UT_OBJ.is_path_exists(path) or UT_OBJ.is_path_exists(
                cfg_obj["s3bench_path"])):
            UT_OBJ.run_cmd(cfg_obj["cmd_go"])
            # executing go get for s3bench
            UT_OBJ.run_cmd(get_cmd)
            # Clone s3bench to go src
            UT_OBJ.run_cmd(git_url.format(cfg_obj["s3bench_path"]))
        return True
    except Exception as err:
        logger.error(err)
        return False


def create_log(resp, log_dir=LOG_DIR):
    """
    To create log file for s3bench run
    :param resp: List of string rersponse
    :param log_dir: Directory path for creating log file
    :return: Path of the log file
    """
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    path = f"{log_dir}s3bench{str(datetime.now()).replace(' ', '-').replace(':', '-').replace('.', '-')}.log"

    # Writing complete response in file, appends respose in case of duration
    # given
    with open(path, "a") as fd:
        for i in resp:
            fd.write(i)

    return path


def create_json_reps(list_resp):
    """
    Create json data
    :param list_resp:
    :return: json response
    """
    js_res = []
    ds = {}
    logger.debug(f"list response {list_resp}")
    for res_el in list_resp:
        # Splitting each response
        split_res = res_el.split("\n")
        for el in split_res:
            if ":" in el:
                list_split = el.replace("\n", "").split(":")
                # adding in single dictionary
                ds[list_split[0]] = list_split[1].strip()
        # appending dictionary to list
        js_res.append(ds)

    return js_res


def s3bench(
        access_key,
        secret_key,
        bucket="bucketname",
        end_point="https://s3.seagate.com",
        num_clients=40,
        num_sample=200,
        obj_name_pref="loadgen_test_",
        obj_size=83886080,
        region="igneous-test",
        skip_cleanup=False,
        duration=None,
        verbose=False):
    """
    To run s3bench tool
    :param access_key: S3 access key
    :param secret_key: S3 secret key
    :param bucket: Bucket to be used
    :param end_point: Endpoint for the operations
    :param num_clients: Number of clients/workers
    :param num_sample: Number of read and write
    :param obj_name_pref: Name prefix for the object
    :param obj_size: Object size to be used 80*1024*1024
    :param region: AWS region to use, eg: us-west-1|us-east-1, etc (default 'igneous-test')
    :param skip_cleanup: skip deleting objects created by this tool at the end of the run
    :param duration: Execute same ops with defined time. 1h24m|0h22m else None
    :param verbose: verbose per thread status write and read
    :return: tuple with json response and log path
    """
    result = []

    # if verbose:
    #     verbs = "-verbose"
    # else:
    #     verbs = " "

    # Creating log file
    log_path = create_log(result)

    logger.info("Running s3 bench tool")
    # GO command formatter
    cmd = f"go run s3bench -accessKey={access_key} -accessSecret={secret_key}" \
        f" -bucket={bucket} -endpoint={end_point} -numClients={num_clients} -numSamples={num_sample}" \
        f" -objectNamePrefix={obj_name_pref} -objectSize={obj_size} -region={region} " \
        f"-skipCleanup={skip_cleanup} -verbose={verbose} > {log_path} 2>&1"

    # In case duration is None
    if not duration:
        duration = "0h0m"

    # Calculating execution time based on the duration given
    hour, mins = duration.lower().replace("h", ":").replace("m", "").split(":")
    dur_time = str(
        datetime.now() +
        timedelta(
            hours=int(hour),
            minutes=int(mins)))[
        11:19]

    # Executing s3bench based on the current time and expected duration time
    # calculated
    while str(datetime.now())[11:19] <= dur_time:
        res = UT_OBJ.execute_cmd(cmd)
        logger.debug(f"Response: {res}")
        result.append(res[1])

    with open(log_path, "r") as r_fd:
        r_data = r_fd.readlines()

    for line in r_data:
        logger.debug(line)
    # Creating log file
    # log_path = create_log(result)
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
        help="size of individual requests in bytes (must be smaller than main memory). (default: 83886080)",
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
    parser.add_argument("--v", dest="verbose",
                        help="print verbose per thread status. (default: False)",
                        action="store_true", default=False)
    s3arg = parser.parse_args()
    # Calling s3bench with passed cli options
    logger.info("Starting S3bench run.")
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
    logger.info("S3bench run ended.")
