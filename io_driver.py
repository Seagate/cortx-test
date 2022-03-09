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
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#
"""
IO driver for scheduling and managing all tests.
Consists of Schedular which parses yaml based inputs and schedules, monitor jobs accordingly.
IO driver will also be responsible for performing health checks and
support bundle collection on regular intervals.
"""
import argparse
import logging
import os
import random
import sched
import sys
import time
from datetime import datetime
from distutils.util import strtobool
from multiprocessing import Process, Manager

import psutil

from src.commons.io.io_logger import StreamToLogger
from src.commons.params import NFS_SERVER_DIR, MOUNT_DIR
from src.commons.utils import assert_utils
from src.commons.utils.system_utils import mount_nfs_server
from config import IO_DRIVER_CFG
from config import S3_CFG
from src.io import yaml_parser
from src.io.cluster_services import collect_upload_sb_to_nfs_server, check_cluster_services
from src.io.tools.s3bench import S3bench

logger = logging.getLogger()

sched_obj = sched.scheduler(time.time, time.sleep)
manager = Manager()
process_states = manager.dict()
event_list = list()
nfs_dir = NFS_SERVER_DIR
mount_dir = MOUNT_DIR


def initialize_loghandler(level=logging.DEBUG):
    """
    Initialize s3 driver runner logging with stream and file handlers.
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
    """Commandline arguments for CorIO Driver."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-ti", "--test-input", type=str,
                        help="test data configuration yaml.")
    parser.add_argument("-ll", "--logging-level", type=int, default=10,
                        help="log level value as defined below: " +
                             "CRITICAL=50 " +
                             "ERROR=40 " +
                             "WARNING=30 " +
                             "INFO=20 " +
                             "DEBUG=10"
                        )
    parser.add_argument("-us", "--use-ssl", type=lambda x: bool(strtobool(str(x))), default=True,
                        help="Use HTTPS/SSL connection for S3 endpoint.")
    parser.add_argument("-sd", "--seed", type=int, help="seed.",
                        default=random.SystemRandom().randint(1, 9999999))
    parser.add_argument("-sk", "--secret-key", type=str, help="s3 secret Key.")
    parser.add_argument("-ak", "--access-key", type=str, help="s3 access Key.")
    parser.add_argument("-ep", "--endpoint", type=str,
                        help="fqdn of s3 endpoint for s3 operations.", default="s3.seagate.com")
    parser.add_argument("-nn", "--number-of-nodes", type=int, default=1,
                        help="number of nodes in k8s system")
    return parser.parse_args()


def launch_process(test_id, value, seed=None):
    """
    This method is intended to Start the process and add PID to dictionary.
    param test_id: Jira Test id
    param value: argument for specific test
    param seed: Seed value for random value generator for S3 operations
    """
    access = S3_CFG.access_key
    secret = S3_CFG.secret_key
    endpoint = S3_CFG.endpoint
    logger.info("Seed Used : %s", seed)
    process_type = value['tool'].lower()
    if process_type == 's3bench':
        process = Process(target=run_s3bench,
                          args=(access, secret, endpoint, value['TEST_ID'],
                                value['sessions_per_node'], value['samples'],
                                value['object_size']["start"], value['object_size']["end"],
                                seed, value['part_size']["start"], value['part_size']["end"]))
    elif process_type == 'warp':
        process = Process(target=run_warp)
    elif process_type == 'support_bundle':
        process = Process(target=collect_sb, args=(value['sb_identifier'],))
    elif process_type == 'health_check':
        process = Process(target=perform_health_check)
    else:
        logger.error("Process type not defined!!")
        sys.exit(1)
    process.start()
    pid = process.pid
    logger.info("Started Process PID: %s TEST_ID: %s TYPE: %s", pid, test_id,
                process_type)
    new_proc_data = manager.dict()
    new_proc_data['state'] = 'started'
    new_proc_data['type'] = process_type
    new_proc_data['start_time'] = datetime.now()
    process_states[pid] = new_proc_data


def update_process_termination(return_status):
    """
    Update the required structures with return status from process.
    param return_status: Return status from the executed process
    """
    pid = os.getpid()
    logger.info("Process terminated : %s Response: %s", pid, return_status)
    process_states[pid]['state'] = 'done'
    process_states[pid]['ret_status'] = return_status[0]
    process_states[pid]['response'] = return_status[1]
    logger.info("Proc state post termination : %s %s", pid,
                process_states[pid]['state'])


# pylint: disable=too-many-arguments
def run_s3bench(access, secret, endpoint, test_id, clients, samples, size_low,
                size_high, seed, part_low, part_high, duration=None):
    """Execute S3bench tool and update error code if any, to process_state on termination."""
    logger.info("Start S3bench run ")
    s3bench = S3bench(access=access, secret=secret, endpoint=endpoint, test_id=test_id,
                      clients=clients, samples=samples, size_low=size_low, size_high=size_high,
                      seed=seed, part_low=part_low, part_high=part_high, duration=duration)
    ret = s3bench.run_check()
    update_process_termination(return_status=ret)
    logger.info("Completed S3bench run ")


def run_warp():
    """
    Execute warp tool and update error code if any, to process_state on termination.
    """
    logger.info("Start warp run ")
    time.sleep(50)
    ret = (False, True)  # TODO: add warp tool support
    update_process_termination(return_status=ret)
    logger.info("Completed warp run ")


def collect_sb(sb_identifier):
    """
    Collect support bundle and update error code if any, to process_state on termination.
    """
    logger.info("Collect Support bundle")
    ret = collect_upload_sb_to_nfs_server(mount_dir, sb_identifier,
                                          max_sb=IO_DRIVER_CFG['max_no_of_sb'])
    update_process_termination(return_status=ret)
    logger.info("Support bundle collection done!!")


def perform_health_check():
    """
    Collect support bundle and update error code if any, to process_state on termination.
    """
    logger.info("Performing health check")
    ret = check_cluster_services()
    update_process_termination(return_status=ret)
    logger.info("Health check done!!")


def periodic_sb(sb_identifier):
    """
    Perform Periodic support bundle collection
    """
    sb_interval = IO_DRIVER_CFG['sb_interval_mins'] * 60
    event_list.append(sched_obj.enter(sb_interval, 1, periodic_sb, argument=(sb_identifier,)))
    launch_process(None, {'sb_identifier': sb_identifier, 'tool': 'support_bundle'}, None)


def periodic_hc():
    """
    Perform periodic health check
    """
    hc_interval = IO_DRIVER_CFG['hc_interval_mins'] * 60
    event_list.append(sched_obj.enter(hc_interval, 1, periodic_hc))
    launch_process(None, {'tool': 'health_check'}, None)


def ps_kill(proc_pid):
    """
    Kills process with proc_pid and its child process
    :param proc_pid: Pid of process to be killed
    """
    logger.info("Killing %s", proc_pid)
    process = psutil.Process(proc_pid)
    for proc in process.children(recursive=True):
        proc.kill()
    process.kill()


def monitor_proc():
    """
    Monitor all started processes
    """
    logger.info("Monitoring Processes..")
    while True:
        time.sleep(30)
        logger.info(".")
        error_proc = None
        error_proc_data = None
        terminate_run = False
        is_process_running = False

        for key, value in process_states.items():
            if value['state'] == 'done':
                if not value['ret_status']:
                    terminate_run = True
                    error_proc = key
                    error_proc_data = value
            if value['state'] == 'started':
                is_process_running = True

        # Terminate if error observed in any process
        if terminate_run:
            logger.error("Error observed in process %s %s", error_proc,
                         error_proc_data)
            logger.error("Terminating schedular..")
            for pid, value in process_states.items():
                if value['state'] != 'done':
                    logger.info('pid : %s state: %s', pid, value['state'])
                    ps_kill(pid)
            for event in event_list:
                try:
                    logger.info("Cancelling event %s", event)
                    sched_obj.cancel(event)
                except ValueError:
                    logger.info("Event not present %s", event)
            sys.exit(0)

        # Terminate if no process scheduled or running.
        if sched_obj.empty() and not is_process_running:
            logger.info("No jobs scheduled in schedular,exiting..!!")
            sys.exit(0)


def setup_environment():
    """
    Tool installations for test execution
    """
    ret = mount_nfs_server(nfs_dir, mount_dir)
    assert_utils.assert_true(ret, "Error while Mounting NFS directory")


def main(options):
    """Main Entry function using argument parser to parse options and start execution."""
    logger.info("Performing tools installations")
    setup_environment()

    test_input = options.test_input
    test_input = yaml_parser.test_parser(test_input, options.number_of_nodes)  # Read test data

    for key, value in test_input.items():
        logger.info("Test No : %s", key)
        logger.info("Test Values : %s", value)
        event_list.append(
            sched_obj.enter(value['start_time'].total_seconds(), 1, launch_process,
                            (key, value, options.seed)))
    sb_identifier = int(time.time())
    if IO_DRIVER_CFG['capture_support_bundle']:
        logger.info("Scheduling Support bundle collection")
        logger.debug("Scheduling sb at interval : %s", IO_DRIVER_CFG['sb_interval_mins'] * 60)
        event_list.append(
            sched_obj.enter(IO_DRIVER_CFG['sb_interval_mins'] * 60, 1, periodic_sb,
                            argument=(sb_identifier,)))

    if IO_DRIVER_CFG['perform_health_check']:
        logger.info("Scheduling health check")
        logger.debug("Scheduling health check at interval : %s",
                     IO_DRIVER_CFG['hc_interval_mins'] * 60)
        event_list.append(sched_obj.enter(IO_DRIVER_CFG['hc_interval_mins'] * 60, 1, periodic_hc))

    logger.info("Starting scheduler")
    sched_process = Process(target=sched_obj.run)
    sched_process.start()
    logger.info('Scheduler PID : %s', sched_process.pid)
    logger.info("Starting monitor process")
    monitor_process = Process(target=monitor_proc)
    monitor_process.start()
    logger.info('Monitor Process PID : %s', monitor_process.pid)

    monitor_process.join()
    sched_process.terminate()


if __name__ == '__main__':
    opts = parse_args()
    log_level = logging.getLevelName(opts.logging_level)
    initialize_loghandler(level=log_level)
    logger.info("Arguments: %s", opts)
    main(opts)
