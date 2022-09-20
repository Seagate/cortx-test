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
"""Test bot or worker which filters the tests based on Jira Test Plan or Kafka Message.
Runs test sequentially or in parallel and report the results to DB and Jira.
"""
import os
import sys
import subprocess
import argparse
import csv
import json
import logging
import requests
from datetime import datetime
from multiprocessing import Process
from jira import JIRA
from core import runner
from core import kafka_consumer
from core.health_status_check_update import HealthCheck
from core.client_config import ClientConfig
from core.locking_server import LockingServer
from commons.utils.jira_utils import JiraTask
from commons import configmanager
from commons.utils import config_utils
from commons.utils import system_utils
from commons import params
from commons import cortxlogging
from commons import constants as common_cnst

LOGGER = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", "--json_file", type=str,
                        help="json file name")
    parser.add_argument("-r", "--html_report", type=str, default='report.html',
                        help="html report name")
    parser.add_argument("-d", "--db_update", type=str_to_bool,
                        default=True,
                        help="Update Reports DB. Can be false in case reports db is down")
    parser.add_argument("-u", "--jira_update", type=str_to_bool,
                        default=True,
                        help="Update Jira. Can be false in case Jira is down")
    parser.add_argument("-csm", "--csm_checks", type=str_to_bool, default=False,
                        help="Execute tests with error code & msg check enabled.")
    parser.add_argument("-te", "--te_ticket", type=str,
                        help="jira xray test execution id")
    parser.add_argument("-pe", "--parallel_exe", type=str, default=False,
                        help="parallel_exe: True for parallel, False for sequential")
    parser.add_argument("-tp", "--test_plan", type=str,
                        help="jira xray test plan id")
    parser.add_argument("-b", "--build", type=str, default='',
                        help="Build number")
    parser.add_argument("-t", "--build_type", type=str, default='',
                        help="Build type (Release/Dev)")
    parser.add_argument("-tg", "--target", type=str,
                        default='', help="Target setup details")
    parser.add_argument("-ll", "--log_level", type=int, default=10,
                        help="log level value as defined below" +
                             "CRITICAL = 50" +
                             "FATAL = CRITICAL" +
                             "ERROR = 40" +
                             "WARNING = 30 WARN = WARNING" +
                             "INFO = 20 DEBUG = 10"
                        )
    parser.add_argument("-p", "--prc_cnt", type=int, default=2,
                        help="number of parallel processes")
    parser.add_argument("-f", "--force_serial_run", type=str_to_bool,
                        default=False, nargs='?', const=True,
                        help="Force sequential run if you face problems with parallel run")
    parser.add_argument("-i", "--data_integrity_chk", type=str_to_bool,
                        default=False, help="Helps set DI check enabled so that tests "
                                            "perform additional checksum check")
    parser.add_argument("-tt", "--test_type", nargs='+', type=str,
                        default=['ALL'], help="Space separated test types")
    parser.add_argument("--xml_report", type=str_to_bool, default=False,
                        help="Generates xml format report if set True, default is False")
    parser.add_argument("--stop_on_first_error", "-x", dest="stop_on_first_error",
                        action="store_true", help="Stop test execution on first failure")
    parser.add_argument("-pf", "--product_family", type=str, default='LC',
                        help="Product family LR or LC.")
    parser.add_argument("-c", "--validate_certs", type=str_to_bool, default=True,
                        help="Validate HTTPS/SSL certificate to S3 endpoint.")
    parser.add_argument("-s", "--use_ssl", type=str_to_bool, default=True,
                        help="Use HTTPS/SSL connection for S3 endpoint.")
    parser.add_argument("-hc", "--health_check", type=str_to_bool, default=True,
                        help="Decide whether to do health check.")
    return parser.parse_args()


def initialize_loghandler(log, level=logging.DEBUG) -> None:
    """Initialize test runner logging with stream and file handlers."""
    log.setLevel(level)
    cwd = os.getcwd()
    dir_path = os.path.join(os.path.join(cwd, params.LOG_DIR_NAME, params.LATEST_LOG_FOLDER))
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    name = os.path.splitext(os.path.basename(__file__))[0]
    name = os.path.join(dir_path, name + '.log')
    cortxlogging.set_log_handlers(log, name, mode='w')


def str_to_bool(val):
    """To convert a string value to bool."""
    if isinstance(val, bool):
        return val
    if val.lower() in ('yes', 'true', 'y', '1'):
        return True
    elif val.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def run_pytest_cmd(args, te_tag=None, parallel_exe=False, env=None, re_execution=False):
    """Form a pytest command for execution."""
    env['TARGET'] = args.target
    build, build_type = args.build, args.build_type

    run_type = ''
    is_distributed = ''
    try:
        run_type = env['pytest_run']
    except (KeyError, AttributeError):
        is_distributed = "--distributed=" + str(False)

    if run_type == 'distributed':
        is_distributed = "--distributed=" + str(True)

    is_parallel = "--is_parallel=" + str(parallel_exe)
    log_level = "--log-cli-level=" + str(args.log_level)
    # we intend to use --log-level instead of cli

    force_serial_run = "--force_serial_run="
    serial_run = "True" if args.force_serial_run else "False"
    force_serial_run = force_serial_run + serial_run
    prc_cnt = str(args.prc_cnt) + "*popen"
    te_id = ''
    if args.te_ticket:
        te_id = str(args.te_ticket) + "_"
    if re_execution:
        te_tag = None
        report_name = "--html=log/re_non_parallel_" + te_id +\
                      datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S-%f') + args.html_report
        cmd_line = ["pytest", "--continue-on-collection-errors", is_parallel, is_distributed,
                    log_level, report_name]
    else:
        if parallel_exe and not args.force_serial_run:
            report_name = "--html=log/parallel_" + te_id + \
                          datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S-%f') + args.html_report
            cmd_line = ["pytest", is_parallel, is_distributed,
                        log_level, report_name, '-d', "--tx",
                        prc_cnt, force_serial_run]
        elif parallel_exe and args.force_serial_run:
            report_name = "--html=log/parallel_" + te_id + \
                          datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S-%f') + args.html_report
            cmd_line = ["pytest", is_parallel, is_distributed,
                        log_level, report_name, force_serial_run]
        else:
            report_name = "--html=log/non_parallel_" + te_id +\
                          datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S-%f') + args.html_report
            cmd_line = ["pytest", is_parallel, is_distributed,
                        log_level, report_name, force_serial_run]

    if args.te_ticket:
        cmd_line = cmd_line + ["--te_tkt=" + str(args.te_ticket)]

    if args.target:
        cmd_line = cmd_line + ["--target=" + args.target]

    if te_tag:
        tag = '-m ' + te_tag
        cmd_line = cmd_line + [tag]

    read_metadata = "--readmetadata=" + str(True)
    cmd_line = cmd_line + [read_metadata]

    if not args.db_update:
        cmd_line = cmd_line + ["--db_update=" + str(False)]

    if not args.jira_update:
        cmd_line = cmd_line + ["--jira_update=" + str(False)]

    if args.data_integrity_chk:  # redo for kafka tests remove when drunner is supported.
        cmd_line = cmd_line + ["--data_integrity_chk=" + str(True)]

    if args.xml_report:
        if parallel_exe:
            cmd_line = cmd_line + ["--junitxml=log/parallel_" + te_id + "report.xml"]
        else:
            cmd_line = cmd_line + ["--junitxml=log/non_parallel_" + te_id + "report.xml"]

    if args.stop_on_first_error:
        cmd_line = cmd_line + ["-x"]

    cmd_line = cmd_line + ['--build=' + str(build), '--build_type=' + str(build_type),
                           '--tp_ticket=' + args.test_plan,
                           '--product_family=' + args.product_family,
                           '--validate_certs=' + str(args.validate_certs),
                           '--use_ssl=' + str(args.use_ssl),
                           '--csm_checks=' + str(args.csm_checks),
                           '--health_check=' + str(args.health_check)]
    LOGGER.debug('Running pytest command %s', cmd_line)
    prc = subprocess.Popen(cmd_line, env=env)
    prc.communicate()
    if prc.returncode == 3:
        print('Exiting test runner due to bad health of deployment')
        sys.exit(1)
    if prc.returncode == 4:
        print('Exiting test runner due to health check script error')
        sys.exit(2)


def delete_status_files():
    file_list = ['failed_tests.log', 'passed_tests.log', 'other_test_calls.log']
    for file in file_list:
        if os.path.exists(file):
            os.remove(file)


def process_test_list(test):
    """
    Get test list in format [test_id, test_summary,test_to_run]
    process the input list to get pytest cmd/test to run
    """
    test_name = test[2]
    cmd = test_name.replace('test_name:', '')
    test_id = test[0]
    test_html_report = str(test_id) + '.html'
    return cmd, test_id, test_html_report


def check_test_status(test_name):
    """
    Check whether test name is present in failed_tests.log file
    If its present, then that means given test is failed.
    """
    fail_file = 'failed_tests.log'
    test_status = 'PASS'
    test_name = test_name.replace("\\", "/")
    if os.path.exists(fail_file):
        with open(fail_file) as fp:
            lines = fp.readlines()
            for line in lines:
                if test_name.strip() in line.strip():
                    test_status = 'FAIL'
                    break
    return test_status


def get_ticket_meta_from_test_list():
    """Creates a json file which can be used by cache for data that is static to test.
    This file saves test metadata once in test runner cycle.
    :argument file_path  Fix codacy issue.
    """
    pass


def get_tests_from_te(jira_obj, args, test_type=None):
    """
    Get tests from given test execution
    """
    if test_type is None:
        test_type = ['ALL']
    test_tuple, tag = jira_obj.get_test_ids_from_te(args.te_ticket, test_type)
    if test_tuple:
        test_list = list(list(zip(*test_tuple))[0])
        if len(test_list) == 0 or tag == "":
            raise EnvironmentError("Please check TE provided, tests or tag is missing")
    else:
        test_list = []
    return test_list, tag


def trigger_unexecuted_tests(args, test_list):
    """
    Check if some tests are not executed in earlier TE
    Rerun those tests in seqential manner.
    """
    jira_id, jira_pwd = runner.get_jira_credential()
    jira_obj = JiraTask(jira_id, jira_pwd)
    te_test_list, tag = get_tests_from_te(jira_obj, args, ['TODO'])
    if len(te_test_list) != 0:
        # check if there are any selected tests with todo status
        unexecuted_test_list = [test for test in test_list if test in te_test_list]
        if len(unexecuted_test_list) != 0:
            # run those selected todo tests sequential
            args.parallel_exe = False
            with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME,
                                   params.JIRA_DIST_TEST_LIST), 'w') as test_file:
                write = csv.writer(test_file)
                for test in unexecuted_test_list:
                    write.writerow([test])
            _env = os.environ.copy()
            _env['pytest_run'] = 'distributed'
            run_pytest_cmd(args, te_tag=tag, parallel_exe=args.parallel_exe,
                           env=_env, re_execution=True)


def create_test_meta_data_file(args, test_list, jira_obj=None):
    """
    Create test meta data file
    """
    tp_meta = dict()  # test plan meta
    jira_id, jira_pwd = runner.get_jira_credential()
    if not jira_obj:
        jira_obj = JiraTask(jira_id, jira_pwd)
    # Any how create Jira object to pass to get_issue_details to save on instance creation.
    jira_url = "https://jts.seagate.com/"
    options = {'server': jira_url}
    auth = (jira_id, jira_pwd)
    auth_jira = JIRA(options, basic_auth=auth)
    # Create test meta file for reporting TR.
    tp_meta_file = os.path.join(os.getcwd(),
                                params.LOG_DIR_NAME,
                                params.JIRA_TEST_META_JSON)
    with open(tp_meta_file, 'w') as t_meta:
        test_meta = list()
        tp_resp = jira_obj.get_issue_details(args.test_plan, auth_jira=auth_jira)  # test plan id
        tp_meta['test_plan_label'] = tp_resp.fields.labels
        tp_meta['environment'] = tp_resp.fields.environment  # deprecated
        c_fields = dict(build=tp_resp.fields.customfield_22980,
                        branch=tp_resp.fields.customfield_22981,
                        plat_type=tp_resp.fields.customfield_22982,
                        srv_type=tp_resp.fields.customfield_22983,
                        enc_type=tp_resp.fields.customfield_22984)
        # tp_meta with defaults
        tp_meta['build'] = c_fields['build'][0] if c_fields['build'] else 0
        tp_meta['branch'] = c_fields['branch'][0] if c_fields['branch'] else 'stable'
        tp_meta['platform_type'] = c_fields['plat_type'][0] if c_fields['plat_type'] else 'VM_HW'
        tp_meta['server_type'] = c_fields['srv_type'][0] if c_fields['srv_type'] else 'VM'
        tp_meta['enclosure_type'] = c_fields['enc_type'][0] if c_fields['enc_type'] else '5U84'

        te_resp = jira_obj.get_issue_details(args.te_ticket, auth_jira=auth_jira)  # test exec id
        te_components = 'Automation'  # default
        if te_resp.fields.components:
            te_components = te_resp.fields.components[0].name
        tp_meta['te_meta'] = dict(te_id=args.te_ticket,
                                  te_label=te_resp.fields.labels,
                                  te_components=te_components)
        test_tuple, te_tag = jira_obj.get_test_ids_from_te(
            test_exe_id=args.te_ticket)
        test_dict = dict(test_tuple)
        # test_name, test_id, test_id_labels, test_team, test_type
        for test in test_list:
            item = dict()
            item['test_id'] = test
            resp = jira_obj.get_issue_details(test, auth_jira=auth_jira)
            item['test_name'] = resp.fields.summary
            item['labels'] = resp.fields.labels if resp.fields.labels else list()
            if resp.fields.components:
                component = resp.fields.components[0].name  # First items is of interest
            else:
                component = list()
            item['component'] = component
            c_fields = dict(domain=resp.fields.customfield_21087,
                            dr_id=resp.fields.customfield_22882,
                            feature_id=resp.fields.customfield_22881)
            domain = c_fields['domain'].value if c_fields['domain'] else 'None'
            item['test_domain'] = domain
            item['dr_id'] = c_fields['dr_id'] if c_fields['dr_id'] else ['DR-0']
            item['feature_id'] = c_fields['feature_id'] if c_fields['feature_id'] else ['F-0']
            lbls = item['labels']
            item['execution_type'] = lbls[0] if lbls and isinstance(lbls, list) else 'R2Automated'
            item['test_run_id'] = test_dict[test]
            test_meta.append(item)
        tp_meta['test_meta'] = test_meta
        json.dump(tp_meta, t_meta, ensure_ascii=False)
    return tp_meta


def trigger_runner_process(args, kafka_msg, client):
    """
        Runner process to trigger tests in kafka msg on available target
    """
    lock_task = LockingServer()
    trigger_tests_from_kafka_msg(args, kafka_msg)
    # rerun unexecuted tests in case of parallel execution
    if kafka_msg.parallel and args.force_serial_run != "True":
        trigger_unexecuted_tests(args, kafka_msg.test_list)
    # Release lock on acquired target.
    lock_released = lock_task.unlock_target(args.target, client)
    if lock_released:
        LOGGER.debug("lock released on target {}".format(args.target))
    else:
        LOGGER.error("Error in releasing lock on target {}".format(args.target))


def trigger_tests_from_kafka_msg(args, kafka_msg):
    """
    Trigger pytest execution for received test list
    """
    # writing the data into the file
    with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME,
                           params.JIRA_DIST_TEST_LIST), 'w') as f:
        write = csv.writer(f)
        for test in kafka_msg.test_list:
            write.writerow([test])

    create_test_meta_data_file(args, kafka_msg.test_list)  # why this data is needed in kafka exec
    _env = os.environ.copy()
    _env['pytest_run'] = 'distributed'

    # First execute all tests with parallel tag which are mentioned in given tag.
    run_pytest_cmd(args, te_tag=None, parallel_exe=kafka_msg.parallel, env=_env)
    LOGGER.debug("Executed tests %s on target %s", kafka_msg.test_list, args.target)


def read_selected_tests_csv():
    """
    Read tests which were selected for last execution
    """
    tests = list()
    try:
        with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_SELECTED_TESTS)) \
                as test_file:
            reader = csv.reader(test_file)
            test_list = list(reader)
            for test_row in test_list:
                if not test_row:
                    continue
                tests.append(test_row[0])
        return tests
    except EnvironmentError:
        return tests


def trigger_tests_from_te(args, jira_obj):
    """
    Get the tests from test execution
    Trigger those tests using pytest command
    """
    # test_list, te_tag = jira_obj.get_test_ids_from_te(args.te_ticket)
    # if len(test_list) == 0 or te_tag == "":
    #     assert False, "Please check TE provided, tests or tag is missing"
    test_type_arg = args.test_type
    test_types = [ele.strip() for ele in test_type_arg]

    test_list, te_tag = get_tests_from_te(jira_obj, args, test_types)

    if test_list:
        # writing the data into the file
        with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_TEST_LIST), 'w') \
                as test_file:
            write = csv.writer(test_file)
            for test in test_list:
                write.writerow([test])

        tp_metadata = create_test_meta_data_file(args, test_list)
        if not args.build and not args.build_type:
            args.build, args.build_type = tp_metadata['build'], tp_metadata['branch']

        if args.data_integrity_chk:
            thread_io, event = runner.start_parallel_io(args)

        _env = os.environ.copy()
        te_label = tp_metadata['te_meta']['te_label']
        if te_label is not None and "stop_on_first_error" in te_label:
            args.stop_on_first_error = True

        if not args.force_serial_run:
            # First execute all tests with parallel tag which are mentioned in given tag.
            run_pytest_cmd(args, te_tag, True, env=_env)

            # Sequentially executes test which didn't execute during parallel execution
            test_list = read_selected_tests_csv()
            trigger_unexecuted_tests(args, test_list)

            # Execute all tests having no parallel tag and which are mentioned in given tag.
            run_pytest_cmd(args, te_tag, False, env=_env)
        else:
            # Sequentially execute all tests with parallel tag which are mentioned in given tag.
            run_pytest_cmd(args, te_tag, True, env=_env)
            # Execute all other tests not having parallel tag with given component tag.
            run_pytest_cmd(args, te_tag, False, env=_env)

        if args.data_integrity_chk:
            runner.stop_parallel_io(thread_io, event)


def acquire_target(target, client, lock_type, convert_to_shared=False):
    """
    Check for target which will be used for sequential execution.
    """
    lock_task = LockingServer()
    found_target = ""
    if target != "":
        LOGGER.debug("target found {}".format(target))
        lock_success = lock_task.lock_target(target, client, lock_type, convert_to_shared)
        if lock_success:
            LOGGER.debug("lock acquired {}".format(target))
            confirm_lock_success = lock_task.is_target_locked(target, client, lock_type)
            if confirm_lock_success:
                found_target = target
                LOGGER.debug("lock confirmed {}".format(target))
    return found_target


def get_available_target(kafka_msg, client):
    """
    Check available target from target list
    Get lock on target if available
    """
    lock_task = LockingServer()
    acquired_target = ""
    HealthCheck(runner.get_db_credential()).health_check(kafka_msg.target_list)
    LOGGER.info("Acquiring available target for test execution.")
    while acquired_target == "":
        if kafka_msg.parallel:
            target = lock_task.find_free_target(kafka_msg.target_list, common_cnst.SHARED_LOCK)
            if target == "":
                seq_target = lock_task.find_free_target(kafka_msg.target_list,
                                                        common_cnst.EXCLUSIVE_LOCK)
                if seq_target != "":
                    acquired_target = acquire_target(seq_target, client, common_cnst.SHARED_LOCK,
                                                     True)
            else:
                acquired_target = acquire_target(target, client, common_cnst.SHARED_LOCK)
        else:
            seq_target = lock_task.find_free_target(kafka_msg.target_list,
                                                    common_cnst.EXCLUSIVE_LOCK)
            if seq_target != "":
                acquired_target = acquire_target(seq_target, client,
                                                 common_cnst.EXCLUSIVE_LOCK)
    LOGGER.info("Acquired available target %s for test execution.", str(acquired_target))
    return acquired_target


def check_kafka_msg_trigger_test(args):
    """
    Get message from kafka consumer
    Trigger tests specified in kafka message
    """
    consumer = kafka_consumer.get_consumer()
    print(consumer)
    received_stop_signal = False
    max_iteration = 0
    while not received_stop_signal:
        try:
            # SIGINT can't be handled when polling, limit timeout to 60 seconds.
            msg = consumer.poll(60)
            if msg is None:
                max_iteration += 1
                # break while in case consumer doesn't have any further messages
                if max_iteration >= 4:
                    received_stop_signal = True
                continue
            kafka_msg = msg.value()
            print(kafka_msg)
            if kafka_msg is None:
                continue
            if kafka_msg.te_ticket == "STOP":
                received_stop_signal = True
            elif not len(kafka_msg.test_list):
                continue
            else:
                current_time_ms = datetime.utcnow().strftime('%Y-%m-%d_%H:%M:%S.%f')
                client = system_utils.get_host_name() + "_" + current_time_ms
                acquired_target = get_available_target(kafka_msg, client)
                ClientConfig(runner.get_db_credential()).client_configure_for_given_target(acquired_target)
                args.te_ticket = kafka_msg.te_ticket
                args.parallel_exe = kafka_msg.parallel
                args.build = kafka_msg.build
                args.build_type = kafka_msg.build_type
                args.test_plan = kafka_msg.test_plan
                args.target = acquired_target
                # force serial run within testrunner till xdist issue is fixed
                args.force_serial_run = "True"
                p = Process(target=trigger_runner_process, args=(args, kafka_msg, client))
                p.start()
                p.join()
        except KeyboardInterrupt:
            break
        except BaseException as exce:
            print(exce)
            received_stop_signal = True
    consumer.close()


def get_setup_details(args):
    if not os.path.exists(params.LOG_DIR_NAME):
        os.mkdir(params.LOG_DIR_NAME)
        LOGGER.info("Log directory created...")
    setups = None
    try:
        LOGGER.info("Fetching setups details from database...")
        setups = configmanager.get_config_db(setup_query={})
        if os.path.exists(params.SETUPS_FPATH):
            os.remove(params.SETUPS_FPATH)
            LOGGER.info("Removed the stale setups.json file...")
        config_utils.create_content_json(params.SETUPS_FPATH, setups, ensure_ascii=False)
        LOGGER.info("Updated setups.json can be found under log directory...")
    except requests.exceptions.RequestException as fault:
        LOGGER.exception(str(fault))
        if args.db_update:
            raise Exception from fault
    except Exception as fault:
        if not os.path.exists(params.SETUPS_FPATH):
            raise Exception from fault
        if args.db_update and not setups:
            LOGGER.warning("Using the cached data from setups.json")
            # check for existence of target in setups.json
            exists = False
            json_data = config_utils.read_content_json(params.SETUPS_FPATH, 'r')
            for key in json_data:
                if key == args.target:
                    exists = True
                    break
            if not exists:
                raise Exception(f'target {args.target} Data does not exists in setups.json')


def get_ordered_test_executions(jira_obj, test_plan):
    """Order Test Executions to execute HA test lastly."""
    result = []
    test_executions = jira_obj.get_test_plan_details(test_plan)
    for test_execution in test_executions:
        if test_execution["testEnvironments"]:
            marker = test_execution["testEnvironments"][0].lower()
        else:
            continue
        summary = test_execution["summary"].lower()
        if "ha" in summary or "ha" in marker:
            result.append(test_execution["key"])
        elif "ceph" in summary or "ceph" in marker:
            continue
        else:
            result.insert(0, test_execution["key"])
    return result


def main(args):
    """Main Entry function using argument parser to parse options and forming pyttest command.
    It renames up the latest folder and parses TE ticket to create detailed test details csv.
    """
    get_setup_details(args)
    jira_id, jira_pwd = runner.get_jira_credential()
    jira_obj = JiraTask(jira_id, jira_pwd)
    if args.json_file:
        json_dict, cmd, run_using = runner.parse_json(args.json_file)
        cmd_line = runner.get_cmd_line(cmd, run_using, args.html_report, args.log_level)
        prc = subprocess.Popen(cmd_line)
        out, err = prc.communicate()
    elif not args.te_ticket and args.test_plan:
        test_executions = get_ordered_test_executions(jira_obj, args.test_plan)
        for test_execution in test_executions:
            args.te_ticket = test_execution
            trigger_tests_from_te(args, jira_obj)
    elif args.te_ticket:
        trigger_tests_from_te(args, jira_obj)
    else:
        check_kafka_msg_trigger_test(args)


if __name__ == '__main__':
    runner.cleanup()
    opts = parse_args()
    level = opts.log_level
    level = logging.getLevelName(level)
    opts.log_level = level
    initialize_loghandler(LOGGER, level=level)
    main(opts)
