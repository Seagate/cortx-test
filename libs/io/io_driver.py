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
"""
IOdriver for scheduling and managing all tests.
"""

import logging
import os
import sched
import time
from copy import deepcopy
from multiprocessing import Process, Queue

from s3bench import S3bench

ACCESS_KEY = ""
SECRET_KEY = ""

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('io_driver.log')
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)
# add the handlers to logger
logger.addHandler(ch)
logger.addHandler(fh)


def s3bench_run(return_q, access, secret, endpoint, bucket, object_prefix, log_file, clients,
                samples,
                object_size, head, skip_read, skip_write, skip_cleanup, validate, duration):
    s3bench = S3bench(access, secret, endpoint, bucket, object_prefix, log_file, clients, samples,
                      object_size, head, skip_read, skip_write, skip_cleanup, validate, duration)
    error, ops = s3bench.run_check()
    pid = os.getpid()
    logger.info("S3bench %s PID", bucket)
    ret = {pid: (error, deepcopy(ops))}
    return_q.put(ret)
    logger.info("S3bench %s complete PID = %s", bucket, pid)


def launch_process(process: Process, process_states: dict):
    """
    This method is intended to Start the process and add PID to dictionary.
    :param process: Object of Process
    :process_states : Dictionary of process as key and pid as value
    """
    logger.info("Launching process")
    process.start()
    pid = process.pid
    logger.info("Started Process %s", pid)
    process_states[process] = pid


def main():
    started_process = {}
    # instance is created
    scheduler = sched.scheduler(time.time, time.sleep)
    return_q = Queue()
    bucket1 = "test-bucket-1"
    bucket2 = "test-bucket-2"
    p1 = Process(target=s3bench_run,
                 args=(return_q, ACCESS_KEY, SECRET_KEY, "https://s3.seagate.com",
                       bucket1, "test-obj", "1kb_10_100-1", 10, 100,
                       "1Kb", True, True, False, False, True, "00h01m"))
    started_process[p1] = None
    p2 = Process(target=s3bench_run,
                 args=(return_q, ACCESS_KEY, SECRET_KEY, "https://s3.seagate.com",
                       bucket2, "test-obj", "1kb_10_100-2", 10, 100,
                       "1Kb", True, True, False, False, True, "00h01m"))
    started_process[p2] = None
    # first event with delay of 1 second
    scheduler.enter(1, 1, launch_process, (p1, started_process))
    scheduler.enter(10, 1, launch_process, (p2, started_process))
    # executing the events
    scheduler.run()
    logger.info("Started schedular")
    stop = False
    completed_process = {}
    while True:
        time.sleep(1)
        for process, pid in started_process.items():
            alive = process.is_alive()
            if pid and not alive:
                # check returns for this process
                if not return_q.empty():
                    message = return_q.get(False)
                    logger.debug("Returned = %s", message)
                    if pid in message:
                        # Valid response frm subprocess, Stop if error returned
                        status = message[pid]
                        logger.debug("Process %s, Returned %s", pid, status)
                        completed_process[process] = pid
                    else:
                        logger.error("Not Empty: Process %s terminated without response", pid)
                        stop = True
                        break
                else:
                    logger.error("Empty: Process %s terminated without response", pid)
                    stop = True
                    break
        logger.debug("CPs: %s", completed_process.items())
        logger.debug("SPs: %s", started_process.items())
        for _, pid in completed_process.items():
            started_process = {k: v for k, v in started_process.items() if v != pid}
        if stop or not started_process:
            if not started_process:
                logger.info("No running process,exiting scheduler")
            else:
                logger.error("Process terminated without response. Exiting scheduler")
            break
    logger.info("IO Driver Complete")


if __name__ == '__main__':
    main()
