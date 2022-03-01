# -*- coding: utf-8 -*-
# !/usr/bin/python
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
import logging
from typing import List
from typing import Tuple
from typing import Any
from typing import Dict
from queue import Queue
from threading import Thread
from confluent_kafka.admin import AdminClient
from confluent_kafka.admin import NewTopic
from core import rpcserver
from core import report_rpc
from core import runner
from core import producer
from commons.utils import system_utils
from commons.utils import jira_utils
from commons.utils import config_utils
from commons import worker
from commons import params
from commons import cortxlogging

LCK_FILE = 'DistRunLockFile.lck'
INT_IP = '0.0.0.0'
INT_PORT = 9092

LOGGER = logging.getLogger(__name__)


class RunnerException(RuntimeError):
    pass


def parse_args(argv):
    """Argument parser for Jenkins supplied args."""

    parser = argparse.ArgumentParser(description='DTR')
    parser.add_argument("-te", "--tickets", nargs='+', type=str,
                        help="Jira xray test execution ticket ids")
    parser.add_argument("-tp", "--test_plan", type=str,
                        help="jira xray test plan id")
    parser.add_argument("-l", "--log_level", type=int, default=10,
                        help="Log level numeric value [1-10]")
    parser.add_argument("-t", "--targets", nargs='+', type=str,
                        help="Target setup details separated by space")
    parser.add_argument("-b", "--build", type=str, default='',
                        help="Builds number deployed on target")
    parser.add_argument("-bt", "--build_type", type=str, default='',
                        help="Build type (beta/stable)")
    parser.add_argument("-er", "--enable_async_report", type=bool, default=False,
                        help="Enable async reporting to Jira and MongoDB")
    parser.add_argument("-c", "--cancel_run", type=bool, default=False,
                        help="Enable Cancel run")
    return parser.parse_args(args=argv)


def initialize_handlers(log) -> None:
    """Initialize drunner logging with stream and file handlers."""
    log.setLevel(logging.DEBUG)
    cwd = os.getcwd()
    dir_path = os.path.join(os.path.join(cwd, params.LOG_DIR_NAME, params.LATEST_LOG_FOLDER))
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    name = os.path.splitext(os.path.basename(__file__))[0]
    name = os.path.join(dir_path, name + '.log')
    cortxlogging.set_log_handlers(log, name, mode='w')


class Runner:
    """Runs the RPC server for aysnc reporting."""

    def __init__(self, wqueue):
        self.work_queue = wqueue

    def wait_for_parent(self):
        """Process using this function will exit if parent exited/killed."""
        lk_file = LCK_FILE % os.getpid()
        e_mutex, _ = system_utils.file_lock(lk_file)
        system_utils.file_unlock(e_mutex, lk_file)
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
    test_plan = opts.test_plan
    topic = params.TEST_EXEC_TOPIC
    # collect the test universe
    run_pytest_collect_only_cmd(opts)

    tp_meta = dict()  # test plan meta
    jira_id, jira_pwd = runner.get_jira_credential()
    jira_obj = jira_utils.JiraTask(jira_id, jira_pwd)
    tp_resp = jira_obj.get_issue_details(test_plan)  # test plan id
    tp_meta['test_plan_label'] = tp_resp.fields.labels
    tp_meta['environment'] = tp_resp.fields.environment
    build = tp_resp.fields.customfield_22980
    branch = tp_resp.fields.customfield_22981
    tp_meta['build'] = build if build else 0
    tp_meta['branch'] = branch if branch else 'stable'

    if not opts.build and not opts.build_type:
        opts.build, opts.build_type = tp_meta['build'], tp_meta['branch']

    log_home = create_log_dir_if_not_exists()
    # Create a reverse map of test id as key and values as node_id, tags
    meta_data = dict()  # test universe collected
    test_map = dict()  # tid: (test_mark, test_meta.get('nodeid'), test_meta.get('marks')
    rev_tag_map = dict()  # mark: dict(parallel=set(), sequential=set())}
    skip_marks = ("dataprovider", "test", "run", "skip", "usefixtures",
                  "filterwarnings", "skipif", "xfail", "parametrize")

    internal_skip_marks = ('release_regression', 'sanity')
    base_components_marks = ('cluster_user_ops', 'cluster_management_ops', 's3_ops',
                             'ha', 'stress', 'longevity', 'scalability',
                             'combinational')
    skip_test = list()
    selected_tag_map = dict()
    meta_file = os.path.join(log_home, 'te_meta.json')
    if not os.path.exists(meta_file):
        print("test meta file does not exists... check if pytest_collection ran. Exiting...")
        sys.exit(-1)
    meta_data = config_utils.read_content_json(meta_file, mode='rb')
    create_test_map(base_components_marks, meta_data,
                    rev_tag_map, skip_marks, skip_test,
                    test_map, internal_skip_marks)

    develop_execution_plan(rev_tag_map, selected_tag_map, skip_test, test_map, tickets)
    kafka_admin_conf = {"bootstrap.servers": params.BOOTSTRAP_SERVERS}
    kafka_client = AdminClient(kafka_admin_conf)
    delete_topic(client=kafka_client, topics=[params.TEST_EXEC_TOPIC])
    # This topic could be deleted during execution of a distributed execution.
    # Ensure that only 1 execution is run with multiple targets. This will be enhanced
    # when we start running multiple distributed executions for multiple targets.
    create_topic(kafka_client)
    work_queue = worker.WorkQ(producer.produce, 1024)
    finish = False  # Use finish to exit loop
    # start kafka producer
    _producer = Thread(target=producer.server,
                       args=(topic, work_queue))  # Use finish in server
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
        set_t = parallel_set if len(parallel_set) else sequential_set
        witem.tickets = test_map[next(iter(set_t))][-1]
        witem.build = opts.build
        witem.build_type = opts.build_type
        witem.test_plan = test_plan
        work_queue.put(witem)
        for set_item in sequential_set:
            w_item = Queue()
            w_item.put([set_item])
            w_item.tag = tg
            w_item.parallel = False
            w_item.targets = targets
            w_item.tickets = test_map[set_item][-1]
            w_item.build = opts.build
            w_item.build_type = opts.build_type
            w_item.test_plan = test_plan
            work_queue.put(w_item)
    work_queue.put(None)  # poison
    work_queue.join()
    _producer.join()


def develop_execution_plan(rev_tag_map, selected_tag_map, skip_test, test_map, tickets):
    """Develop Test execution plan to be followed by test runners."""
    for ticket in tickets:
        # get the te meta and create an execution plan
        test_list, ignore = get_te_tickets_data(ticket)
        print(f"Ignoring TE tag field {ignore}")
        # group test_list into narrow feature groups
        # with each feature group create parallel and non parallel groups
        for test in test_list:
            if test in skip_test:
                continue
            if test in test_map:
                tmark, nid, _tags = test_map.get(test)
                if not tmark:
                    LOGGER.error("Test %s having %s found with no marker."
                                 " Skipping it in execution.", test, nid)
                    continue
                test_map.update({test: (tmark, nid, _tags, ticket)})
            else:
                LOGGER.error("Unknown Test %s found Continue...", test)
                continue
            tdict = rev_tag_map.get(tmark)
            if not tdict:
                LOGGER.error("Reverse test map entry %s is empty for %s", tmark,
                             test)
                continue
            p_set, s_set = tdict['parallel'], tdict['sequential']

            if tmark not in selected_tag_map:
                p_s = set()
                s_s = set()
                if test in p_set:
                    p_s.add(test)
                else:
                    s_s.add(test)
                selected_tag_map.update({tmark: [p_s, s_s]})
            else:
                t_l = selected_tag_map.get(tmark)
                if test in p_set:
                    t_l[0].add(test)
                else:
                    t_l[1].add(test)


def create_test_map(base_components_marks: Tuple,
                    meta_data: Dict,
                    rev_tag_map: Dict,
                    skip_marks: Dict,
                    skip_test: List,
                    test_map: Dict,
                    internal_skip_marks: Tuple) -> None:
    """Create a test metadata dict and tag reverse dict."""
    special_mark = ('parallel',)
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
            if mark in skip_marks + special_mark:
                continue
            if mark in internal_skip_marks:
                continue
            if mark in base_components_marks:
                parent_marks.append(mark)
                continue
            update_rev_tag_map(mark, parallel, rev_tag_map, tid)
            test_mark = mark
        if not test_mark and parent_marks:
            test_mark = parent_marks[0]  # anyhow use first parent marker now

            # a case when a test is decorated with a base component mark
            update_rev_tag_map(mark, parallel, rev_tag_map, tid)

        test_map.update({tid: (test_mark, test_meta.get('nodeid'), test_meta.get('marks'))})


def update_rev_tag_map(mark, parallel, rev_tag_map, tid):
    """Update reverse tag map."""
    if mark not in rev_tag_map:
        rev_tag_map.update({mark: dict(parallel=set(), sequential=set())})
        v_dict = rev_tag_map.get(mark)
        _set = v_dict['parallel'] if parallel else v_dict['sequential']
        _set.add(tid)
    else:
        v_dict = rev_tag_map.get(mark)
        _set = v_dict['parallel'] if parallel else v_dict['sequential']
        _set.add(tid)


def create_log_dir_if_not_exists():
    """
    Create log dir if not exists in main entry.
    :return: Path created dir
    """
    log_home = os.path.join(os.getcwd(), params.LOG_DIR_NAME)
    if not os.path.exists(log_home):
        print("log dir does not exists... creating")
        os.makedirs(log_home)
    return log_home


def run_pytest_collect_only_cmd(opts, te_tag=None):
    """Form a pytest command to collect tests in TE ticket.
    Target default to automation as a nominal value for collection.
    """
    env = os.environ.copy()
    env['TARGET'] = opts.targets[0] #needs dummy target
    tag = '-m ' + te_tag if te_tag else None
    collect_only = '--collect-only'
    local = '--local=True'
    target = '--target=' + env['TARGET']
    if tag:
        cmd_line = ["pytest", collect_only, local, tag]
    else:
        cmd_line = ["pytest", collect_only, local]
    cmd_line = cmd_line + [target]
    prc = subprocess.Popen(cmd_line, env=env)
    prc.communicate()


def get_te_tickets_data(ticket: str) -> Tuple[list, str]:
    """
    Gets TE test list and te tag.
    :param ticket:
    :return:
    """
    jira_id, jira_pwd = runner.get_jira_credential()
    jira_obj = jira_utils.JiraTask(jira_id, jira_pwd)
    test_tuple, te_tag = jira_obj.get_test_ids_from_te(ticket)
    test_list = list(list(zip(*test_tuple))[0])
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


def create_topic(admin_client: AdminClient):
    topic_list = [NewTopic(params.TEST_EXEC_TOPIC, 2, 1)]
    admin_client.create_topics(topic_list)


def delete_topic(client, topics):
    """ Call delete_topic to asynchronously delete topics, a future is returned.
    By default this operation on the broker returns immediately while
    topics are deleted in the background. Timeout (30s) is given
    to propagate in the cluster before returning.
    """
    fs = client.delete_topics(topics, operation_timeout=30)
    for topic, f in fs.items():  # Returns a dict of <topic,future>.
        try:
            f.result()  # The result itself is None
            LOGGER.info("Topic {} deleted".format(topic))
        except Exception as e:
            LOGGER.info("Failed to delete topic {}: {}".format(topic, e))


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
    lock_file = LCK_FILE
    mutex, flag = system_utils.file_lock(lock_file)
    name = multiprocessing.current_process().name
    print("Starting %s \n" % name)
    initialize_handlers(LOGGER)
    main()
    print("Exiting %s \n" % name)
    system_utils.file_unlock(mutex, lock_file)
    sys.exit(0)
