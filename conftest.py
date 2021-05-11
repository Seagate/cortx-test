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
"""This file is core of the framework and it contains Pytest fixtures and hooks."""
import ast
import random
import string
import os
import glob
import pathlib
import json
import logging
import csv
import time
import datetime
import pytest
import requests
import tempfile
from datetime import date
from _pytest.nodes import Item
from _pytest.runner import CallInfo
from _pytest.main import Session
from testfixtures import LogCapture
from strip_ansi import strip_ansi
from typing import List
from filelock import FileLock
from commons.utils import config_utils
from commons.utils import jira_utils
from commons.utils import system_utils
from commons import Globals
from commons import cortxlogging
from commons import constants
from commons import report_client
from core.runner import LRUCache
from core.runner import get_jira_credential
from core.runner import get_db_credential
from commons import params
from config import CMN_CFG

FAILURES_FILE = "failures.txt"
LOG_DIR = 'log'
CACHE = LRUCache(1024 * 10)
CACHE_JSON = 'nodes-cache.yaml'
REPORT_CLIENT = None
DT_PATTERN = '%Y-%m-%d_%H:%M:%S'

LOGGER = logging.getLogger(__name__)


SKIP_MARKS = ("dataprovider", "test", "run", "skip", "usefixtures",
              "filterwarnings", "skipif", "xfail", "parametrize",
              "tags")

BASE_COMPONENTS_MARKS = ('csm', 's3', 'ha', 'ras', 'di', 'stress', 'combinational')


def _get_items_from_cache():
    """Intended for internal use after modifying collected items."""
    return CACHE.table


@pytest.fixture(autouse=True, scope='session')
def read_project_config(request):
    f = pathlib.Path(request.node.fspath.strpath)
    config = f.joinpath('config.json')
    with config.open() as fp:
        return json.load(fp)


@pytest.fixture(autouse=True)
def capture():
    with LogCapture() as logs:
        yield logs


@pytest.fixture(scope='session')
def formatter():
    format_log_message = '%(asctime)s\t%(levelname)s\t%(filename)s\t%(funcName)s' \
                         '\t%(processName)s\t%(message)s'
    formatter = logging.Formatter(fmt=format_log_message, datefmt='%Y-%m-%d %H:%M:%S')
    return formatter


@pytest.fixture(scope='session')
def logger():
    """
    Gets session scoped logger which can be used in test methods or functions.
    :return: logger instance
    """
    logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    cortxlogging.init_loghandler(logger)
    return logger


def expensive_data():
    """Dummy expensive data function to be implemented later."""
    return dict()


@pytest.fixture(scope="session")
def session_data(tmp_path_factory, worker_id):
    """Session level fixture to load expensive data."""
    if worker_id == "master":
        # not executing in with multiple workers, just produce the data and let
        # pytest's fixture caching do its job
        return ()

    # get the temp directory shared by all workers
    root_tmp_dir = tmp_path_factory.getbasetemp().parent

    name = root_tmp_dir / "data.json"
    with FileLock(str(name) + ".lock"):
        if name.is_file():
            data = json.loads(name.read_text())
        else:
            data = expensive_data()
            name.write_text(json.dumps(data))
    return data


@pytest.fixture()
def csm_user(worker_id):
    """
    Use a different csm account in each worker.
    PYTEST_XDIST_WORKER env variable can be used to get worker name.
    """
    return "csm_%s" % worker_id


@pytest.fixture(scope='function')
def log_cutter(request, formatter):
    """
    Fixture to create test log for each test case. Developer need to use this
    fixture in the test method argument as shown below
    test_demo(requests, log_cutter)
    :param request:
    :param formatter:
    :return:
    """
    name = request.function.__name__
    records = dict()
    yield records
    records = Globals.records.get(name)
    print("teardown")
    with open(name, 'w') as f:
        for rec in records:
            f.write(formatter.format(rec) + '\n')
    del Globals.records[name]


# content of conftest.py

def pytest_addoption(parser):
    """
    Hook to add options at runtime to pytest command
    :param parser:
    :return:
    """
    parser.addoption(
        "--is_parallel", action="store", default=False, help="option: True or False"
    )
    parser.addoption(
        "--te_tkt", action="store", default="", help="TE ticket's ID"
    )
    parser.addoption(
        "--log_path", action="store", default=None, help="Log root folder path"
    )
    parser.addoption(
        "--local", action="store", default=False, help="Decide whether run is dev local"
    )
    parser.addoption(
        "--build", action="store", default=None, help="Build number"
    )
    parser.addoption(
        "--build_type", action="store", default='Release', help="Build Type(Release)"
    )
    parser.addoption(
        "--tp_ticket", action="store", default='', help="Test Plan ticket"
    )
    parser.addoption(
        "--force_serial_run", action="store", default=False, help="Force serial execution"
    )
    parser.addoption(
        "--target", action="store", default="automation", help="Target or setup under test"
    )
    parser.addoption(
        "--nodes", action="store", default=[], help="Nodes of a setup"
    )
    parser.addoption(
        "--distributed", action="store", default=False,
        help="Decide whether run is in distributed env"
    )
    parser.addoption(
        "--readmetadata", action="store", default=False,
        help="Read test metadata"
    )
    parser.addoption(
        "--db_update", action="store", default=True,
        help="Decide whether to update reporting DB."
    )
    parser.addoption(
        "--data_integrity_chk", action="store", default=False,
        help="Decide whether to perform DI Check or not for a I/O test case."
    )
    parser.addoption(
        "--jira_update", action="store", default=True,
        help="Decide whether to update Jira."
    )


def read_test_list_csv() -> List:
    try:
        tests = list()
        with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_TEST_LIST)) as f:
            reader = csv.reader(f)
            test_list = list(reader)
            for test_row in test_list:
                if not test_row:
                    continue
                tests.append(test_row[0])
        return tests
    except Exception as e:
        print(e)


def read_dist_test_list_csv() -> List:
    """
    Read distributed test csv file
    """
    tests = list()
    try:
        with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_DIST_TEST_LIST)) \
                as test_file:
            reader = csv.reader(test_file)
            test_list = list(reader)
            for test_row in test_list:
                if not test_row:
                    continue
                tests.append(test_row[0])
    except EnvironmentError as err:
        print(err)
    return tests


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """Remove handlers from all loggers."""
    # todo add html hook file = session.config._htmlfile
    loggers = [logging.getLogger()] + list(logging.Logger.manager.loggerDict.values())
    for _logger in loggers:
        handlers = getattr(_logger, 'handlers', [])
        for handler in handlers:
            _logger.removeHandler(handler)

    resp = system_utils.umount_dir(mnt_dir=params.MOUNT_DIR)
    if resp[0]:
        LOGGER.info("Successfully unmounted directory")


def get_test_metadata_from_tp_meta(item):
    tests_meta = Globals.tp_meta['test_meta']
    flg = Globals.tp_meta['test_plan_label']
    tp_label = Globals.tp_meta['test_plan_label'][0] if flg else 'regular'  # first is significant
    te_meta = Globals.tp_meta['te_meta']
    te_label = te_meta['te_label'][0]
    te_component = Globals.tp_meta['te_meta']['te_components']
    test_id = CACHE.lookup(item.nodeid)
    for it in tests_meta:
        if it['test_id'] == test_id:
            it['tp_label'] = tp_label
            it['te_label'] = te_label
            it['te_component'] = te_component
            return it


def get_marks_for_test_item(item):
    marks = list()
    for mark in item.iter_markers():
        if mark.name in SKIP_MARKS:
            continue
        marks.append(mark.name)
    return marks


def create_report_payload(item, call, final_result, d_u, d_pass):
    """Create Report Payload for POST request to put data in Report DB."""
    os_ver = system_utils.get_os_version()
    _item_dict = get_test_metadata_from_tp_meta(item)
    marks = get_marks_for_test_item(item)
    are_logs_collected = True
    if final_result == 'FAIL':
        health_chk_res = "TODO"
    elif final_result in ['PASS', 'BLOCKED']:
        health_chk_res = "NA"
    log_path = "NA"
    nodes = len(CMN_CFG['nodes'])  # number of target hosts
    nodes_hostnames = [n['hostname'] for n in CMN_CFG['nodes']]
    data_kwargs = dict(os=os_ver,
                       build=item.config.option.build,
                       build_type=item.config.option.build_type,
                       client_hostname=system_utils.get_host_name(),
                       execution_type="Automated",
                       health_chk_res=health_chk_res,
                       are_logs_collected=are_logs_collected,
                       log_path=log_path,
                       testPlanLabel=_item_dict['tp_label'],  # get from TP    tp.fields.labels
                       testExecutionLabel=_item_dict['te_label'],  # get from TE  te.fields.labels
                       nodes=nodes,
                       nodes_hostnames=nodes_hostnames,
                       test_exec_id=item.config.option.te_tkt,
                       test_exec_time=call.duration,
                       test_name=_item_dict['test_name'],
                       test_id=_item_dict['test_id'],
                       test_id_labels=_item_dict['labels'],
                       test_plan_id=item.config.option.tp_ticket,
                       test_result=final_result,
                       start_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(call.start)),
                       tags=marks,  # in mem te_meta
                       test_team=_item_dict['te_component'],  # TE te.fields.components[0].name
                       test_type='Pytest',  # TE Avocado/CFT/Locust/S3bench/Pytest
                       latest=True,
                       # feature Should be read from master test plan board.
                       feature=_item_dict.get('test_domain', 'None'),
                       db_username=d_u,
                       db_password=d_pass
                       )
    return data_kwargs


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """pytest configure hook runs before collection."""
    if not config.option.nodes:
        config.option.nodes = []  # CMN_CFG.nodes
    if not config.option.local:
        jira_update = ast.literal_eval(str(config.option.jira_update))
        if jira_update:
            Globals.JIRA_UPDATE = True
            LOGGER.info(f'Jira update pytest switch is set to {Globals.JIRA_UPDATE}')
        else:
            Globals.JIRA_UPDATE = False

    # Handle parallel execution.
    if not hasattr(config, 'workerinput'):
        config.shared_directory = tempfile.mkdtemp()


def pytest_configure_node(node):
    """xdist hook."""
    if not node.config.option.local:
        jira_update = ast.literal_eval(str(node.config.option.jira_update))
        if jira_update:
            Globals.JIRA_UPDATE = True
            LOGGER.info(f'Jira update pytest switch is set to {Globals.JIRA_UPDATE}')
        else:
            Globals.JIRA_UPDATE = False

    node.workerinput['shared_dir'] = node.config.shared_directory


def pytest_sessionstart(session: Session) -> None:
    """Called after the ``Session`` object has been created and before performing collection
    and entering the run test loop.

    :param pytest.Session session: The pytest session object.
    """
    # db_user, db_passwd = CMN_CFG.db_user, CMN_CFG.db_passwd
    # init_instance db_user=None, db_passwd=None
    global REPORT_CLIENT
    report_client.ReportClient.init_instance()
    REPORT_CLIENT = report_client.ReportClient.get_instance()
    reset_imported_module_log_level()


def reset_imported_module_log_level():
    """Reset logging level of imported modules.
    Add check for imported module logger.
    """
    loggers = [logging.getLogger()] + list(logging.Logger.manager.loggerDict.values())
    for _logger in loggers:
        if isinstance(_logger, logging.PlaceHolder):
            LOGGER.info("Skipping placeholder to reset logging level")
            continue
    for pkg in ['boto', 'boto3', 'botocore', 'nose', 'paramiko', 's3transfer', 'urllib3']:
        logging.getLogger(pkg).setLevel(logging.WARNING)


@pytest.hookimpl(tryfirst=True)
def pytest_collection(session):
    """Collect tests in master and filter out test from TE ticket."""
    items = session.perform_collect()
    LOGGER.info(dir(session.config))
    config = session.config
    _local = ast.literal_eval(str(config.option.local))
    _distributed = ast.literal_eval(str(config.option.distributed))
    is_parallel = ast.literal_eval(str(config.option.is_parallel))
    required_tests = list()
    global CACHE
    CACHE = LRUCache(1024 * 10)
    Globals.LOCAL_RUN = _local
    Globals.TP_TKT = config.option.tp_ticket
    Globals.BUILD = config.option.build
    if _distributed:
        required_tests = read_dist_test_list_csv()
        Globals.TE_TKT = config.option.te_tkt
        selected_items = []
        for item in items:
            test_found = ''
            for mark in item.iter_markers():
                if mark.name == 'tags':
                    test_found = mark.args[0]
                    if test_found in required_tests:
                        selected_items.append(item)
            CACHE.store(item.nodeid, test_found)
        items[:] = selected_items
    elif _local:
        meta = list()
        for item in items:
            test_id = ''
            _marks = list()
            for mark in item.iter_markers():
                if mark.name == 'tags':
                    test_id = mark.args[0]
                else:
                    _marks.append(mark.name)
            CACHE.store(item.nodeid, test_id)
            meta.append(dict(nodeid=item.nodeid, test_id=test_id, marks=_marks))
    else:
        required_tests = read_test_list_csv()  # e.g. required_tests = ['TEST-17413', 'TEST-17414']
        Globals.TE_TKT = config.option.te_tkt
        selected_items = []
        selected_tests = []
        for item in items:
            parallel_found = False
            test_found = ''
            for mark in item.iter_markers():
                if mark.name == 'parallel':
                    parallel_found = True
                    if not is_parallel:
                        break
                elif mark.name == 'tags':
                    test_found = mark.args[0]
            if parallel_found == is_parallel and test_found != '':
                if test_found in required_tests:
                    selected_items.append(item)
                    selected_tests.append(test_found)
            CACHE.store(item.nodeid, test_found)
        with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_SELECTED_TESTS), 'w') \
                as test_file:
            write = csv.writer(test_file)
            for test in selected_tests:
                write.writerow([test])
        items[:] = selected_items
    cache_home = os.path.join(os.getcwd(), LOG_DIR)
    cache_path = os.path.join(cache_home, CACHE_JSON)
    if not os.path.exists(cache_home):
        try:
            system_utils.make_dir(cache_home)
        except OSError as error:
            LOGGER.error(str(error))
    latest = os.path.join(cache_home, 'latest')
    if not os.path.exists(latest):
        os.makedirs(latest)
    _path = config_utils.create_content_json(cache_path, _get_items_from_cache(), ensure_ascii=False)
    if not os.path.exists(_path):
        LOGGER.info("Items Cache file %s not created" % (_path,))
    if session.config.option.collectonly:
        te_meta = config_utils.create_content_json(os.path.join(cache_home, 'te_meta.json'), meta,
                                                   ensure_ascii=False)
        LOGGER.debug("Items meta dict %s created at %s", meta, te_meta)
        Globals.te_meta = te_meta
    if not _local and session.config.option.readmetadata:
        tp_meta_file = os.path.join(os.getcwd(),
                                    params.LOG_DIR_NAME,
                                    params.JIRA_TEST_META_JSON)
        tp_meta = config_utils.read_content_json(tp_meta_file, mode='rb')
        Globals.tp_meta = tp_meta
        LOGGER.debug("Reading test plan meta dict %s", tp_meta)
    return items


# pylint: disable=too-many-arguments
def db_and_jira_update(task, test_id, item, call, status, db_user, db_pass):
    try:
        jira_update = ast.literal_eval(str(item.config.option.jira_update))
        db_update = ast.literal_eval(str(item.config.option.db_update))
        if jira_update:
            task.update_test_jira_status(item.config.option.te_tkt, test_id, status)
        if db_update:
            payload = create_report_payload(item, call, status, db_user, db_pass)
            REPORT_CLIENT.create_db_entry(**payload)
    except (requests.exceptions.RequestException, Exception) as fault:
        LOGGER.exception(str(fault))
        LOGGER.error("Failed to execute DB update for %s", test_id)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Execute all other hooks to obtain the report object. Follow the pytest execution protocol
    to understand where does this function fits in. In short this function will help to create
    failed, passed lists in multiple runs. The clean up of logs files should happen before the
    test runs starts.
    All code prior to yield statement would be ran prior
    to any other of the same fixtures defined
    :param item:
    :param call:
    :return:
    """
    outcome = yield
    report = outcome.get_result()
    setattr(item, "rep_" + report.when, report)
    _local = bool(item.config.option.local)
    Globals.LOCAL_RUN = _local
    fail_file = 'failed_tests.log'
    pass_file = 'passed_tests.log'
    current_file = 'other_test_calls.log'
    jira_update = ast.literal_eval(str(item.config.option.jira_update))
    db_update = ast.literal_eval(str(item.config.option.db_update))
    if not _local:
        test_id = CACHE.lookup(report.nodeid)
        if report.when == 'teardown':
            try:
                if jira_update:
                    db_user, db_pass = get_db_credential()
                    jira_id, jira_pwd = get_jira_credential()
                    task = jira_utils.JiraTask(jira_id, jira_pwd)

                if item.rep_setup.failed or item.rep_teardown.failed:
                    try:
                        if jira_update:
                            task.update_test_jira_status(item.config.option.te_tkt, test_id, 'FAIL')
                        if db_update:
                            payload = create_report_payload(item, call, 'FAIL', db_user, db_pass)
                            REPORT_CLIENT.create_db_entry(**payload)
                    except (requests.exceptions.RequestException, Exception) as fault:
                        LOGGER.exception(str(fault))
                        LOGGER.error("Failed to execute DB update for %s", test_id)
                elif item.rep_setup.passed and (item.rep_call.failed or item.rep_teardown.failed):
                    try:
                        if jira_update:
                            task.update_test_jira_status(item.config.option.te_tkt, test_id, 'FAIL')
                        if db_update:
                            payload = create_report_payload(item, call, 'FAIL', db_user, db_pass)
                            REPORT_CLIENT.create_db_entry(**payload)
                    except (requests.exceptions.RequestException, Exception) as fault:
                        LOGGER.exception(str(fault))
                        LOGGER.error("Failed to execute DB update for %s", test_id)
                elif item.rep_setup.passed and item.rep_call.passed and item.rep_teardown.passed:
                    try:
                        if jira_update:
                            task.update_test_jira_status(item.config.option.te_tkt, test_id, 'PASS')
                        if db_update:
                            payload = create_report_payload(item, call, 'PASS', db_user, db_pass)
                            REPORT_CLIENT.create_db_entry(**payload)
                    except (requests.exceptions.RequestException, Exception) as fault:
                        LOGGER.exception(str(fault))
                        LOGGER.error("Failed to execute DB update for %s", test_id)
                elif item.rep_setup.skipped and \
                        (item.rep_teardown.skipped or item.rep_teardown.passed):
                    # Jira reporting of skipped cases does not contain skipped option
                    # Reporting it blocked and updating db.
                    try:
                        if jira_update:
                            task.update_test_jira_status(item.config.option.te_tkt, test_id, 'BLOCKED')
                        if db_update:
                            payload = create_report_payload(item, call, 'BLOCKED', db_user, db_pass)
                            REPORT_CLIENT.create_db_entry(**payload)
                    except (requests.exceptions.RequestException, Exception) as fault:
                        LOGGER.exception(str(fault))
                        LOGGER.error("Failed to execute DB update for %s", test_id)

            except Exception as exception:
                LOGGER.error("Exception %s occurred in reporting for test %s.",
                             str(exception), test_id)
    if report.when == 'teardown':
        if item.rep_setup.failed or item.rep_teardown.failed:
            current_file = fail_file
            current_file = os.path.join(os.getcwd(), LOG_DIR, 'latest', current_file)
            mode = "a" if os.path.exists(current_file) else "w"
        elif item.rep_setup.passed and (item.rep_call.failed or item.rep_teardown.failed):
            current_file = fail_file
            current_file = os.path.join(os.getcwd(), LOG_DIR, 'latest', current_file)
            mode = "a" if os.path.exists(current_file) else "w"
        elif item.rep_setup.passed and item.rep_call.passed and item.rep_teardown.passed:
            current_file = pass_file
            current_file = os.path.join(os.getcwd(), LOG_DIR, 'latest', current_file)
            mode = "a" if os.path.exists(current_file) else "w"
        elif item.rep_setup.skipped and (item.rep_teardown.skipped or item.rep_teardown.passed):
            current_file = os.path.join(os.getcwd(), LOG_DIR, 'latest', current_file)
            mode = "a" if os.path.exists(current_file) else "w"
        with open(current_file, mode) as f:
            if "tmpdir" in item.fixturenames:
                extra = " ({})".format(item.funcargs["tmpdir"])
            else:
                extra = ""
            f.write(report.nodeid + extra + "\n")


def upload_supporting_logs(test_id: str, remote_path: str, log: str):
    """
    Upload all supporting (s3bench) log files to nfs share
    :param test_id: test number in file name
    :param remote_path: path on NFS share
    :param log: log file string e.g. s3bench
    """
    support_logs = glob.glob(f"{LOG_DIR}/latest/{test_id}_{log}_*")
    for support_log in support_logs:
        resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                   mnt_dir=params.MOUNT_DIR,
                                                   remote_path=remote_path,
                                                   local_path=support_log)
        if resp[0]:
            LOGGER.info("Supporting log files are uploaded at location : %s", resp[1])
        else:
            LOGGER.error("Failed to supporting log file at location %s", resp[1])


def pytest_runtest_logreport(report: "TestReport") -> None:
    """
    Provides an intercept to create a) generate log per test case
    b) Update Jira with result at different phases within a test (setup, call, teardown)
    c) Call Reports REST API to update Report DB (Mongo)
    :param report:
    :return:
    """
    if Globals.LOCAL_RUN:
        if report.when == 'teardown':
            log = report.caplog
            log = strip_ansi(log)
            logs = log.split('\n')
            test_id = CACHE.lookup(report.nodeid)
            name = str(test_id) + '_' + report.nodeid.split('::')[1] + '_' \
                   + datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S') \
                   + '.log'
            test_log = os.path.join(os.getcwd(), LOG_DIR, 'latest', name)
            with open(test_log, 'w') as fp:
                for rec in logs:
                    fp.write(rec + '\n')
        return
    test_id = CACHE.lookup(report.nodeid)
    if report.when == 'setup':
        if Globals.JIRA_UPDATE:
            jira_id, jira_pwd = get_jira_credential()
            task = jira_utils.JiraTask(jira_id, jira_pwd)
            task.update_test_jira_status(Globals.TE_TKT, test_id, 'Executing')
    elif report.when == 'call':
        pass
    elif report.when == 'teardown':
        log = report.caplog
        log = strip_ansi(log)
        logs = log.split('\n')
        test_id = CACHE.lookup(report.nodeid)
        name = str(test_id) + '_' + report.nodeid.split('::')[1] + '_' + \
               datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d%H%M%S') + \
               '.log'
        test_log = os.path.join(os.getcwd(), LOG_DIR, 'latest', name)
        with open(test_log, 'w') as fp:
            for rec in logs:
                fp.write(rec + '\n')
        LOGGER.info("Uploading test log file to NFS server")
        remote_path = os.path.join(params.NFS_BASE_DIR,
                                   Globals.BUILD, Globals.TP_TKT,
                                   Globals.TE_TKT, test_id,
                                   datetime.datetime.fromtimestamp(
                                       time.time()).strftime(DT_PATTERN)
                                   )
        resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                   mnt_dir=params.MOUNT_DIR,
                                                   remote_path=remote_path,
                                                   local_path=test_log)
        if resp[0]:
            LOGGER.info("Log file is uploaded at location : %s", resp[1])
        else:
            LOGGER.error("Failed to upload log file at location %s", resp[1])
        upload_supporting_logs(test_id, remote_path, "s3bench")
        LOGGER.info("Adding log file path to %s", test_id)
        comment = "Log file path: {}".format(resp[1])
        if Globals.JIRA_UPDATE:
            jira_id, jira_pwd = get_jira_credential()
            task = jira_utils.JiraTask(jira_id, jira_pwd)
            data = task.get_test_details(test_exe_id=Globals.TE_TKT)
            if data:
                resp = task.update_execution_details(data=data, test_id=test_id,
                                                     comment=comment)
                if resp:
                    LOGGER.info("Added execution details comment in: %s", test_id)
                else:
                    LOGGER.error("Failed to comment to %s", test_id)
            else:
                LOGGER.error("Failed to add log file path to %s", test_id)


@pytest.fixture(scope='function')
def generate_random_string():
    """
    This fixture will return random string with lowercase
    :return: random string
    :rtype: str
    """
    return ''.join(random.choice(string.ascii_lowercase) for i in range(5))
