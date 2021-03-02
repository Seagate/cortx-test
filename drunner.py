# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""Parallel Test Executor discovers tests as per the TE Plan provided.

   It creates an execution plan from tickets set obtained from TE Ticket.
   This execution plan will group tickets according provided Execution Strategy.
   It creates Kafka messages to run contained tickets on different test runner
   processes on same or different machine.

   It Provides a way to utilize multiple testing targets in test execution.

"""
import argparse
import sys
import os
import multiprocessing
import threading
import csv
import subprocess
from multiprocessing import Queue
from typing import List
from typing import Tuple
from typing import Any
from typing import Dict
from threading import Thread
from core import rpcserver
from core import report_rpc
from core import runner
from core import producer
from commons.utils import system_utils
from commons.utils import jira_utils
from commons.utils import config_utils
from commons import worker
from config import params

sys.path.insert(0, os.getcwd())  # Has to be placed before core.

LCK_FILE = 'lockfile-%s'
INT_IP = '0.0.0.0'
INT_PORT = 9092


class RunnerException(RuntimeError):
    pass


def parse_args(argv):
    """Argument parser for Jenkins supplied args."""

    parser = argparse.ArgumentParser(description='DTR')
    parser.add_argument("-te", "--tickets", nargs='+', type=str,
                        help="Jira xray test execution ticket ids")
    parser.add_argument("-l", "--log_level", type=int, default=10,
                        help="Log level numeric value [1-10]")
    parser.add_argument("-t", "--targets", nargs='+', type=str,
                        help="Target setup details separated by space")
    parser.add_argument("-b", "--build", type=str,
                        help="Builds number deployed on target")
    parser.add_argument("-er", "--enable_async_report", type=bool, default=False,
                        help="Enable async reporting to Jira and MongoDB")
    parser.add_argument("-c", "--cancel_run", type=bool, default=False,
                        help="Enable Cancel run")
    parser.add_argument("-p", "--pause_run", type=bool, default=False,
                        help="Pause test run")
    parser.add_argument("-r", "--resume_run", type=bool, default=False,
                        help="Resume from paused state")
    parser.add_argument("-s", "--stop_on_error", type=bool, default=False,
                        help="Resume from paused state")
    return parser.parse_args(args=argv)


class Runner:
    """Runs the RPC server for aysnc reporting."""

    def __init__(self, wqueue):
        self.work_queue = wqueue

    def wait_for_parent(self):
        """Process using this function will exit if parent exited/killed."""
        lk_file = LCK_FILE % os.getpid()
        e_mutex, _ = system_utils.FileLock(lk_file)
        system_utils.file_unlock(e_mutex)
        sys.exit(0)  # os._exit(0)

    def run(self):
        """Run method to bootstrap RPC server."""
        main_th = threading.Thread(target=self.wait_for_parent)
        main_th.start()
        # Start the report client rpc server
        srv = rpcserver.Server((INT_IP, INT_PORT, report_rpc.register))
        srv.start()
        print("Report Client started...")
        sys.exit(0)


def get_pid():
    """Different handling for macOS"""
    return os.getpid()


def start_rpc_server(_queue: Any) -> None:
    """
    Starts RPC Server.
    :param _queue:
    """
    server = Runner(_queue)
    server.run()


def run(opts: dict) -> None:
    """Main entry point of distributed test executor."""
    _queue = Queue
    if opts.enable_async_report:
        start_rpc_server(_queue)  # starts an rpc server for async reporting task management
    tickets = opts.tickets
    targets = opts.targets
    build = opts.build
    topic = params.TEST_EXEC_TOPIC
    # collect the test universe
    run_pytest_collect_only_cmd()
    log_home = create_log_dir_if_not_exists()
    # Create a reverse map of test id as key and values as node_id, tags
    meta_data = dict()
    test_map = dict()
    rev_tag_map = dict()
    skip_marks = ("dataprovider", "test", "run", "skip", "usefixtures",
                  "filterwarnings", "skipif", "xfail", "parametrize")
    base_components_marks = ('csm', 's3', 'ha', 'ras', 'stress', 'combinational')
    skip_test = list()
    selected_tag_map = dict()
    meta_file = os.path.join(log_home, 'te_meta.json')
    if not os.path.exists(meta_file):
        print("test meta file does not exists... check if pytest_collection ran. Exiting...")
        sys.exit(-1)

    meta_data = config_utils.read_content_json(meta_file)
    create_test_map(base_components_marks, meta_data,
                    rev_tag_map, skip_marks, skip_test,
                    test_map)

    for ticket in tickets:
        # get the te meta and create an execution plan
        test_list, ignore = get_te_tickets_data(ticket)
        print(f"Ignoring TE tag {ignore}")
        # group test_list into narrow feature groups
        # with each feature group create parallel and non parallel groups
        for test in test_list:
            if test in test_map:
                tm, nid, _tags = test_map.get(test)
            tdict = rev_tag_map.get(tm)
            p_set, s_set = tdict['parallel'], tdict['sequential']
            if tm not in selected_tag_map:
                p_s = set()
                s_s = set()
                if test in p_set:
                    p_s.add(test)
                else:
                    s_s.add(test)
                selected_tag_map.update({tm: [p_s, s_s]})
            else:
                t_l = selected_tag_map.get(tm)
                if test in p_set:
                    t_l[0].add(test)
                else:
                    t_l[1].add(test)

    work_queue = worker.WorkQ(producer.produce, 1024)
    finish = False  # Use finish to exit loop

    # start kafka producer
    _producer = Thread(target=producer.server, args=(topic, work_queue))  # Use finish in server
    _producer.setDaemon(True)
    _producer.start()
    # for parallel group create a kafka entry
    # for each non parallel group item create a kafka entry
    for tg in selected_tag_map:
        parallel_set, sequential_set = selected_tag_map[tg]
        witem = Queue()
        witem.put(parallel_set)
        witem.tag = tg
        witem.parallel = True
        witem.targets = targets
        witem.tickets = tickets
        witem.build = build
        work_queue.put(witem)
        for set_item in sequential_set:
            w_item = Queue()
            w_item.put(set_item)
            w_item.tag = tg
            w_item.parallel = False
            w_item.targets = targets
            w_item.tickets = tickets
            w_item.build = build
            work_queue.put(w_item)


def create_test_map(base_components_marks: Tuple,
                    meta_data: Dict,
                    rev_tag_map: Dict,
                    skip_marks: Dict,
                    skip_test: List,
                    test_map: Dict) -> None:
    """Create a test metadata dict and tag reverse dict."""
    for test_meta in meta_data:
        tid = test_meta.get('test_id')
        if not tid:
            continue
        parent_marks = list()
        for mark in test_meta.get('marks'):
            if mark in ('skip',):
                skip_test.append(tid)
                break
        parallel = False
        for mark in test_meta.get('marks'):
            if mark in ('parallel',):
                parallel = True
                break
        test_mark = ''
        for mark in test_meta.get('marks'):
            if mark in skip_marks:
                continue
            if mark in base_components_marks:
                parent_marks.append(mark)
                continue

            if mark not in rev_tag_map:
                rev_tag_map.update({mark, dict(parallel=set(), sequential=set())})
                v_dict = rev_tag_map.get(mark)
                _set = v_dict['parallel'] if parallel else v_dict['sequential']
                _set.add(tid)

            else:
                v_dict = rev_tag_map.get(mark)
                _set = v_dict['parallel'] if parallel else v_dict['sequential']
                _set.add(tid)
            test_mark = mark
        test_map.update({tid: (test_mark, test_meta.get('nodeid'), test_meta.get('marks'))})


def create_log_dir_if_not_exists():
    """
    Create log dir if not exists in main entry.
    :return:
    """
    log_home = os.path.join(os.getcwd(), params.LOG_DIR_NAME)
    if not os.path.exists(log_home):
        print("log dir does not exists... creating")
        os.makedirs(log_home)
    return log_home


def run_pytest_collect_only_cmd(te_tag=None):
    """Form a pytest command to collect tests in TE ticket."""
    tag = '-m ' + te_tag if te_tag else None
    collect_only = '--collect-only'
    local = '--local=True'
    if tag:
        cmd_line = ["pytest", collect_only, local, tag]
    else:
        cmd_line = ["pytest", collect_only, local]
    prc = subprocess.Popen(cmd_line)
    prc.communicate()


def get_te_tickets_data(ticket: str) -> Tuple[list, str]:
    """
    Gets TE test list and te tag.
    :param ticket:
    :return:
    """
    jira_id, jira_pwd = runner.get_jira_credential()
    jira_obj = jira_utils.JiraTask(jira_id, jira_pwd)
    test_list, te_tag = jira_obj.get_test_ids_from_te(ticket)
    if len(test_list) == 0 or te_tag == "":
        raise EnvironmentError("Please check TE provided, tests or tag is missing")
    return test_list, te_tag


def save_to_logdir(test_list: List) -> None:
    """Currently unused."""
    # writing the data into the file
    with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_TEST_LIST), 'w') as fptr:
        write = csv.writer(fptr)
        for test in test_list:
            write.writerow([test])


def main(argv=None):
    """
    Handles argument parser.
    :param argv:
    :return:
    """
    program_name = os.path.basename(sys.argv[0])
    program_desc = '''Distributed Test runner'''
    if argv is None:
        argv = sys.argv[1:]

    try:
        opts = parse_args(argv)
        run(opts)
    except RunnerException as fault:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + "\n")
        sys.stderr.write(program_desc + ": " + repr(fault) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2
    return 0


if __name__ == "__main__":
    lock_file = LCK_FILE % os.getpid()
    emutex, flag = system_utils.FileLock(lock_file)
    name = multiprocessing.current_process().name
    print("Starting %s \n" % name)
    main()
    print("Exiting %s \n" % name)
    system_utils.FileUnlock(emutex)
    sys.exit(0)
