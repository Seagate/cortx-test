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
Consists of Schedular which parses yaml based inputs and schedules, monitor jobs accordingly.
IO driver will also be responsible for performing health checks and
support bundle collection on regular intervals.
"""

import logging
import os
import sched
import sys
import time
from datetime import datetime
from multiprocessing import Process, Manager

io_driver_config = "config/io/io_driver_config.yaml"
io_driver_log = "io_driver.log"

log = logging.getLogger()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = logging.FileHandler(io_driver_log)
ch = logging.StreamHandler()

log.setLevel(logging.DEBUG)
fh.setLevel(logging.DEBUG)
ch.setLevel(logging.INFO)

ch.setFormatter(formatter)
fh.setFormatter(formatter)

log.addHandler(ch)
log.addHandler(fh)

sched_obj = sched.scheduler(time.time, time.sleep)
manager = Manager()
process_states = manager.dict()
process_list = manager.list()


def launch_process(process, process_type):
    """
    This method is intended to Start the process and add PID to dictionary.
    process_states : Dictionary of process as key and pid as value
    process: Object of Process
    process_type: Type of tool invoked by process
    """
    log.info(f"Launching process : {process}")
    process.start()
    pid = process.pid
    log.info("Started Process %s", pid)
    new_proc_data = manager.dict()
    new_proc_data['state'] = 'started'
    new_proc_data['type'] = process_type
    new_proc_data['start_time'] = datetime.now()
    process_states[pid] = new_proc_data
    log.info(f"launch : proc state {process_states}")


def update_process_termination(return_status):
    """
    Update the required structures with return status from process.
    """
    pid = os.getpid()
    log.info("Process terminated : %s Response: %s", pid, return_status)
    log.info(f"Proc state: {process_states}")
    process_states[pid]['state'] = 'done'
    process_states[pid]['ret_status'] = return_status[0]
    process_states[pid]['response'] = return_status[1]
    log.info(f"Proc state post termination : {process_states[pid]['state']}")


def run_s3bench():
    """
    Execute S3bench tool and update error code if any, to process_state on termination.
    """
    log.info("Start S3bench run ")
    time.sleep(30)
    ret = (True, True)
    update_process_termination(return_status=ret)
    log.info("Completed S3bench run ")


def run_warp():
    """
    Execute warp tool and update error code if any, to process_state on termination.
    """
    log.info("Start warp run ")
    time.sleep(150)
    ret = (True, True)
    update_process_termination(return_status=ret)
    log.info("Completed warp run ")


def periodic_sb(interval):
    sched_obj.enter(interval, 2, periodic_sb, (interval))
    process = Process(target=collect_sb)
    launch_process(process, 'support_bundle')


def collect_sb():
    """
    Collect support bundle and update error code if any, to process_state on termination.
    """
    log.info("collect sb")
    time.sleep(10)
    log.info("collect sb done!!")


def main():
    # Retrieve output(dict) from yaml parser
    test_input = {'p1': {'tool': 's3bench', 'time': 10}, 'p2': {'tool': 's3bench', 'time': 30},
                  'p3': {'tool': 'warp', 'time': 50}}
    for key, value in test_input.items():
        process_type = value['tool'].lower()
        if process_type == 's3bench':
            process = Process(target=run_s3bench)
        elif process_type == 'warp':
            process = Process(target=run_warp)
        elif process_type == 'support_bundle':
            process = Process(target=collect_sb)
        else:
            log.error(f"Error! Tool type not defined : {process_type}")
            sys.exit(1)
        sched_obj.enter(value['time'], 1, launch_process, (process, process_type))
    # periodic_sb(20)
    time.sleep(2)
    log.info("*****Starting schedular*****")
    sched_obj.run()

    while True:
        time.sleep(30)
        log.info('.')
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
            log.error(f"Error observed in process {error_proc} {error_proc_data}")
            log.error(f"Terminating schedular..")
            sys.exit(0)

        # Terminate if no process scheduled or running.
        if sched_obj.empty() and not is_process_running:
            log.info("No jobs scheduled in schedular,exiting..!!")
            sys.exit(0)


if __name__ == '__main__':
    main()
