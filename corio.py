#!/usr/bin/python
# -*- coding: utf-8 -*-
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
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
"""
Perform parallel S3 operations as per the given test input YAML using Asyncio.
"""
import argparse
import asyncio
import glob
import logging
import multiprocessing
import os
import random
import sys
from distutils.util import strtobool
from pprint import pformat

from commons.io.io_logger import StreamToLogger
from commons.params import NFS_SERVER_DIR, MOUNT_DIR
from commons.utils.system_utils import mount_nfs_server
from config import S3_CFG
from io_driver import logger
from libs.io import yaml_parser
from tests.io import test_s3_bucket_io_stability
from tests.io import test_s3_copy_object
from tests.io import test_s3_multipart_io_stability
from tests.io import test_s3_object_io_stability
from tests.io import test_s3api_multipart_partcopy_io_stability

nfs_dir = NFS_SERVER_DIR
mount_dir = MOUNT_DIR
function_mapping = {
    'copy_object': [test_s3_copy_object.TestS3CopyObjects, 'execute_copy_object_workload'],
    'bucket': [test_s3_bucket_io_stability.TestBucketOps, 'execute_bucket_workload'],
    'multipart': [test_s3_multipart_io_stability.TestMultiParts, 'execute_multipart_workload'],
    'object': [test_s3_object_io_stability.TestS3Object, 'execute_object_workload'],
    'multipart_partcopy': [test_s3api_multipart_partcopy_io_stability.TestMultiPartsPartCopy,
                           'execute_multipart_partcopy_workload']
}


def initialize_loghandler(level=logging.INFO):
    """
    Initialize io driver runner logging with stream and file handlers.
    param level: logging level used in CorIO tool.
    """
    logger.setLevel(level)
    dir_path = os.path.join(os.path.join(os.getcwd(), "log", "latest"))
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    name = os.path.splitext(os.path.basename(__file__))[0]
    name = os.path.join(dir_path, f"{name}_console.log")
    StreamToLogger(name, logger)


def parse_args():
    """Commandline arguments for CORIO Driver."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-ti", "--test_input", type=str,
                        help="Directory path containing test data input yaml files.")
    parser.add_argument("-ll", "--logging-level", type=int, default=20,
                        help="log level value as defined below: " +
                             "CRITICAL=50 " +
                             "ERROR=40 " +
                             "WARNING=30 " +
                             "INFO=20 " +
                             "DEBUG=10"
                        )
    parser.add_argument("-us", "--use_ssl", type=lambda x: bool(strtobool(str(x))), default=True,
                        help="Use HTTPS/SSL connection for S3 endpoint.")
    parser.add_argument("-sd", "--seed", type=int, help="seed.",
                        default=random.SystemRandom().randint(1, 9999999))
    parser.add_argument("-sk", "--secret_key", type=str, help="s3 secret Key.")
    parser.add_argument("-ak", "--access_key", type=str, help="s3 access Key.")
    parser.add_argument("-ep", "--endpoint", type=str,
                        help="fqdn of s3 endpoint for io operations.", default="s3.seagate.com")
    parser.add_argument("-nn", "--number_of_nodes", type=int,
                        help="number of nodes in k8s system", default=1)
    return parser.parse_args()


async def create_session(funct: list, session: str, start_time: float, **kwargs) -> None:
    """
    Execute the test function in sessions.
    :param funct: List of class name and method name to be called
    :param session: session name
    :param start_time: Start time for session
    """
    await asyncio.sleep(start_time)
    logger.info("Starting Session %s, PID - %s", session, os.getpid())
    logger.info("kwargs : %s", kwargs)
    func = getattr(funct[0](**kwargs), funct[1])
    await func()
    logger.info("Ended Session %s, PID - %s", session, os.getpid())


async def schedule_sessions(test_plan: str, test_plan_value: dict, common_params: dict) -> None:
    """
    Create and Schedule specified number of sessions for each test in test_plan
    :param test_plan: YAML file name for specific S3 operation
    :param test_plan_value: Parsed test_plan values
    :param common_params: Common arguments to be sent to function
    """
    process_name = f"Test [Process {os.getpid()}, test_num {test_plan}]"
    tasks = []
    for _, each in test_plan_value.items():
        params = {'test_id': each['TEST_ID'],
                  'object_size': each['object_size']}
        if 'part_range' in each.keys():
            params['part_range'] = each['part_range']
        params.update(common_params)
        for i in range(int(each['sessions'])):
            tasks.append(create_session(funct=each['operation'],
                                        session=each['TEST_ID'] + "_session" + str(i),
                                        start_time=each['start_time'].total_seconds(),
                                        **params))

    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    logger.info("Completed task %s", done)
    for task in pending:
        task.cancel()
    for task in done:
        task.result()
    logger.info("%s terminating", process_name)


def schedule_test_plan(test_plan: str, test_plan_values: dict, common_params: dict) -> None:
    """
    Create event loop for each test plan
    :param test_plan: YAML file name for specific S3 operation
    :param test_plan_values: Parsed yaml file values
    :param common_params: Common arguments to be passed to function.
    """
    process_name = f"TestPlan [Process {os.getpid()}, topic {test_plan}]"
    logger.info("%s Started ", process_name)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(schedule_sessions(test_plan, test_plan_values, common_params))
    except KeyboardInterrupt:
        logger.info("%s Loop interrupted", process_name)
        loop.stop()
    logger.info("%s terminating", process_name)


def setup_environment():
    """
    Tool installations for test execution
    """
    ret = mount_nfs_server(nfs_dir, mount_dir)
    assert ret, "Error while Mounting NFS directory"


def main(options):
    """
    Main function for CORIO
    :param options: Parsed Arguments
    """
    logger.info("Setting up environment!!")
    setup_environment()

    commons_params = {'access_key': S3_CFG.access_key,
                      'secret_key': S3_CFG.secret_key,
                      'endpoint_url': S3_CFG.endpoint,
                      'use_ssl': S3_CFG["use_ssl"],
                      'seed': options.seed
                      }
    file_list = glob.glob(options.test_input + "/*")
    logger.info("Test YAML Files to be executed : %s", file_list)
    parsed_input = {}
    for each in file_list:
        parsed_input[each] = yaml_parser.test_parser(each, options.number_of_nodes)

    for _, value in parsed_input.items():
        for test_key, test_value in value.items():
            logger.info("Test Values : %s", value)
            if 'operation' in test_value.keys():
                test_value['operation'] = function_mapping[test_value['operation']]
                value[test_key] = test_value

    logger.info("Parsed input files : ")
    logger.info(pformat(parsed_input))
    processes = []
    for test_plan, test_plan_value in parsed_input.items():
        process = multiprocessing.Process(target=schedule_test_plan,
                                          args=(test_plan, test_plan_value, commons_params))
        processes.append(process)
    # TODO: Add support to schedule support bundle and health check periodically

    try:
        for process in processes:
            process.start()
        terminate = False
        while True:
            for process in processes:
                if not process.is_alive():
                    logger.info("Process with PID %s Name %s exited. Stopping other Process.",
                                process.pid, process.name)
                    terminate = True
            if terminate:
                raise KeyboardInterrupt
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()
            process.join()
        # TODO: cleanup object files created
        sys.exit()


if __name__ == '__main__':
    opts = parse_args()
    log_level = logging.getLevelName(opts.logging_level)
    initialize_loghandler(level=log_level)
    logger.info("Arguments: %s", opts)
    main(opts)
