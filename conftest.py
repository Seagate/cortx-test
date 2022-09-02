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
"""This file is core of the framework and it contains Pytest fixtures and hooks."""
import ast
import csv
import datetime
import glob
import json
import logging
import os
import pathlib
import random
import shutil
import string
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from threading import Thread
from typing import List

import pytest
import requests
from _pytest.main import Session
from filelock import FileLock
from strip_ansi import strip_ansi

from commons import Globals
from commons import cortxlogging
from commons import params
from commons import report_client
from commons import constants as const
from commons.helpers.health_helper import Health
from commons.utils import assert_utils
from commons.utils import config_utils
from commons.utils import jira_utils
from commons.utils import system_utils
from config import CMN_CFG
from core.runner import LRUCache
from core.runner import get_db_credential
from core.runner import get_jira_credential
from libs.di.di_mgmt_ops import ManagementOPs
from libs.di.di_run_man import RunDataCheckManager
from libs.di.fi_adapter import S3FailureInjection

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
SKIP_DBG_LOGGING = ['boto', 'boto3', 'botocore', 'nose', 'paramiko', 's3transfer', 'urllib3']

Globals.ALL_RESULT = None
Globals.CSM_LOGS = None


def _get_items_from_cache():
    """Intended for internal use after modifying collected items."""
    return CACHE.table


@pytest.fixture(autouse=True, scope='session')
def read_project_config(request):
    f = pathlib.Path(request.node.fspath.strpath)
    config = f.joinpath('config.json')
    with config.open() as fp:
        return json.load(fp)


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
    logger.setLevel(Globals.LOG_LEVEL)
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
        "--build_type", action="store", default='stable', help="Build Type(Release)"
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
    parser.addoption(
        "--csm_checks", action="store", default=False,
        help="Execute tests with error code & msg check enabled."
    )
    parser.addoption(
        "--health_check", action="store", default=True,
        help="Decide whether to do health check in local mode."
    )
    parser.addoption(
        "--product_family", action="store", default='LC',
        help="Product Type LR or LC."
    )
    parser.addoption(
        "--validate_certs", action="store", default=True,
        help="Decide whether to Validate HTTPS/SSL certificate to S3 endpoint."
    )
    parser.addoption(
        "--use_ssl", action="store", default=True,
        help="Decide whether to use HTTPS/SSL connection for S3 endpoint."
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

    try:
        resp = system_utils.umount_dir(mnt_dir=params.MOUNT_DIR)
        if resp[0]:
            print("Successfully unmounted directory")
    except Exception as fault:
        print("Exception occurred while unmounting directory")
    filter_report_session_finish(session)


def get_test_metadata_from_tp_meta(item):
    tp_meta = Globals.tp_meta
    tests_meta = tp_meta['test_meta']
    flg = tp_meta['test_plan_label']
    tp_label = tp_meta['test_plan_label'][0] if flg else 'default'  # first is significant
    te_meta = tp_meta['te_meta']
    te_label = te_meta['te_label'][0] if te_meta['te_label'] else ''
    te_component = tp_meta['te_meta']['te_components']
    test_id = CACHE.lookup(item.nodeid)
    # tp_meta with defaults

    for it in tests_meta:
        if it['test_id'] == test_id:
            it['tp_label'] = tp_label
            it['te_label'] = te_label
            it['te_component'] = te_component
            it['build'] = tp_meta['build']
            it['branch'] = tp_meta['branch']
            it['platform_type'] = tp_meta['platform_type']
            it['server_type'] = tp_meta['server_type']
            it['enclosure_type'] = tp_meta['enclosure_type']
            return it
    return dict()


def get_marks_for_test_item(item):
    marks = list()
    for mark in item.iter_markers():
        if mark.name in SKIP_MARKS:
            continue
        marks.append(mark.name)
    return marks


def _capture_exec_info(report, call):
    """Inner function to capture exec info. Needs improvement."""
    exec_info = None
    if call.excinfo is None:
        return exec_info
    if hasattr(report, "wasxfail"):
        # Exception was expected.
        return exec_info
    return call.excinfo.value


def capture_exec_info(report, call, item):
    """Purpose is to accurately find exception info."""
    exec_info = None
    if item.rep_setup.failed or item.rep_teardown.failed:
        exec_info = _capture_exec_info(report, call)
    elif item.rep_setup.passed and (item.rep_call.failed or item.rep_teardown.failed):
        exec_info = _capture_exec_info(report, call)
    elif item.rep_setup.passed and item.rep_call.passed and item.rep_teardown.passed:
        return None
    return exec_info


def create_report_payload(item, call, final_result, d_u, d_pass):
    """Create Report Payload for POST request to put data in Report DB."""
    os_ver = system_utils.get_os_version()
    _item_dict = get_test_metadata_from_tp_meta(item) # item dict has all item, tp and te metadata
    marks = get_marks_for_test_item(item)
    are_logs_collected = True
    if final_result == 'FAIL':
        health_chk_res = "TODO"
    elif final_result in ['PASS', 'BLOCKED']:
        health_chk_res = "NA"
    log_path = getattr(item, 'logpath')
    nodes = len(CMN_CFG['nodes'])  # number of target hosts
    nodes_hostnames = [n['hostname'] for n in CMN_CFG['nodes']]
    exec_info = ''
    try:
        call_duration = getattr(item, 'call_duration')
    except AttributeError:
        call_duration = 0
    data_kwargs = dict(os=os_ver,
                       build=item.config.option.build,
                       build_type=item.config.option.build_type,
                       client_hostname=system_utils.get_host_name(),
                       execution_type=_item_dict['execution_type'],
                       health_chk_res=health_chk_res,
                       are_logs_collected=are_logs_collected,
                       log_path=log_path,
                       testPlanLabel=_item_dict['tp_label'],  # get from TP
                       testExecutionLabel=_item_dict['te_label'],  # get from TE
                       nodes=nodes,
                       nodes_hostnames=nodes_hostnames,
                       test_exec_id=item.config.option.te_tkt,
                       test_exec_time=call_duration,
                       test_name=_item_dict['test_name'],
                       test_id=_item_dict['test_id'],
                       test_id_labels=_item_dict['labels'],
                       test_plan_id=item.config.option.tp_ticket,
                       test_result=final_result,  # call start needs correction
                       start_time=time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(call.start)),
                       tags=marks,  # in mem te_meta
                       test_team=_item_dict['te_component'],  # TE te.fields.components[0].name
                       test_type='Pytest',  # TE Avocado/CFT/Locust/S3bench/Pytest check marks
                       latest=True,
                       # feature is read from individual test case Jira.
                       feature=_item_dict.get('test_domain', 'None'),
                       dr_id=_item_dict['dr_id'],
                       feature_id=_item_dict['feature_id'],
                       platform_type=_item_dict['platform_type'],
                       server_type=_item_dict['server_type'],
                       enclosure_type=_item_dict['enclosure_type'],
                       failure_string=exec_info,
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
    pytest.dns_rr_counter = 0


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
    reset_imported_module_log_level(session)


def reset_imported_module_log_level(session):
    """Reset logging level of imported modules.
    Add check for imported module logger.
    """
    log_level = session.config.option.log_cli_level
    if not log_level:
        log_level = logging.DEBUG  # default=10 for pytest direct invocation without log cli level
    Globals.LOG_LEVEL = log_level
    loggers = [logging.getLogger()] + list(logging.Logger.manager.loggerDict.values())
    for _logger in loggers:
        # Handle Place holders logging
        if isinstance(_logger, logging.PlaceHolder):
            LOGGER.info("Skipping placeholder to reset logging level")
            continue
        if _logger.name in SKIP_DBG_LOGGING:
            _logger.setLevel(logging.WARNING)

    for pkg in ['boto', 'boto3', 'botocore', 'nose', 'paramiko', 's3transfer', 'urllib3']:
        logging.getLogger(pkg).setLevel(logging.WARNING)


@pytest.hookimpl(tryfirst=True)
def pytest_collection(session):
    """Collect tests in master and filter out test from TE ticket."""
    items = session.perform_collect()
    config = session.config
    _local = ast.literal_eval(str(config.option.local))
    _distributed = ast.literal_eval(str(config.option.distributed))
    is_parallel = ast.literal_eval(str(config.option.is_parallel))
    health_check = ast.literal_eval(str(config.option.health_check))
    required_tests = list()
    global CACHE
    CACHE = LRUCache(1024 * 10)
    Globals.LOCAL_RUN = _local
    Globals.HEALTH_CHK = health_check
    Globals.TP_TKT = config.option.tp_ticket
    Globals.BUILD = config.option.build
    Globals.TARGET = config.option.target
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
        selected_items = [None] * len(required_tests)
        selected_tests = [None] * len(required_tests)
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
                    index = required_tests.index(test_found)
                    selected_items[index] = item
                    selected_tests[index] = test_found
            CACHE.store(item.nodeid, test_found)
        selected_items = list(filter(lambda x: x, selected_items))
        selected_tests = list(filter(lambda x: x, selected_tests))
        LOGGER.info("Items = %s", selected_tests)
        with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, params.JIRA_SELECTED_TESTS), 'w') \
                as test_file:
            write = csv.writer(test_file)
            for test in selected_tests:
                write.writerow([test])
        if is_parallel:
            te_selected_csv = str(config.option.te_tkt) + "_parallel.csv"
        else:
            te_selected_csv = str(config.option.te_tkt) + "_non_parallel.csv"
        with open(os.path.join(os.getcwd(), params.LOG_DIR_NAME, te_selected_csv), 'w') \
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
    Globals.ALL_RESULT = report
    setattr(item, "rep_" + report.when, report)
    try:
        attr = getattr(item, 'call_duration')
        LOGGER.info('Setting attribute call_duration')
    except AttributeError as attr_error:
        LOGGER.warning('Exception %s occurred', str(attr_error))
        setattr(item, "call_duration", call.duration)
    else:
        setattr(item, "call_duration", call.duration + attr)

    _local = bool(item.config.option.local)
    Globals.LOCAL_RUN = _local
    fail_file = 'failed_tests.log'
    pass_file = 'passed_tests.log'
    current_file = 'other_test_calls.log'
    jira_update = ast.literal_eval(str(item.config.option.jira_update))
    db_update = ast.literal_eval(str(item.config.option.db_update))
    test_id = CACHE.lookup(report.nodeid)
    if report.when == 'setup':
        Globals.CSM_LOGS = f"{LOG_DIR}/latest/{test_id}_Gui_Logs/"
        if os.path.exists(Globals.CSM_LOGS):
            shutil.rmtree(Globals.CSM_LOGS)
        os.mkdir(Globals.CSM_LOGS)
    if not _local:
        if report.when == 'setup' and item.rep_setup.failed:
            # Fail eagerly in Jira, when you know setup failed.
            # The status is again anyhow updated in teardown as it was earlier.
            try:
                if jira_update:
                    jira_id, jira_pwd = get_jira_credential()
                    task = jira_utils.JiraTask(jira_id, jira_pwd)
                    task.update_test_jira_status(item.config.option.te_tkt, test_id, 'FAIL')
            except (requests.exceptions.RequestException, Exception) as fault:
                LOGGER.exception(str(fault))
                LOGGER.error("Failed to execute Jira update for %s", test_id)
        elif report.when == 'teardown':
            try:
                remote_path = os.path.join(params.NFS_BASE_DIR,
                                           Globals.BUILD, Globals.TP_TKT,
                                           Globals.TE_TKT, test_id,
                                           datetime.datetime.fromtimestamp(
                                               time.time()).strftime(DT_PATTERN)
                                           )
                setattr(report, "logpath", remote_path)
                setattr(item, "logpath", remote_path)
                if jira_update:
                    db_user, db_pass = get_db_credential()
                    jira_id, jira_pwd = get_jira_credential()
                    task = jira_utils.JiraTask(jira_id, jira_pwd)

                if item.rep_setup.failed or item.rep_teardown.failed:
                    try:
                        if jira_update:
                            task.update_test_jira_status(item.config.option.te_tkt, test_id, 'FAIL')
                        if db_update:
                            # capture exec info
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
        mode = "a"  # defaults
        current_file = os.path.join(os.getcwd(), LOG_DIR, 'latest', current_file)
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
        elif item.rep_setup.skipped or item.rep_call.skipped or item.rep_teardown.skipped:
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
    if log == 'csm_gui':
        support_logs = glob.glob(f"{LOG_DIR}/latest/{test_id}_Gui_Logs/*")
    elif log == 's3bench':
        support_logs = glob.glob(f"{LOG_DIR}/latest/{test_id}_{log}_*")
    else:
        support_logs = glob.glob(f"{LOG_DIR}/latest/logs-cortx-cloud-*")
    LOGGER.debug("support logs is %s", support_logs)
    for support_log in support_logs:
        resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                   mnt_dir=params.MOUNT_DIR,
                                                   remote_path=remote_path,
                                                   local_path=support_log)
        if resp[0]:
            LOGGER.info("Supporting log files are uploaded at location : %s", resp[1])
            if os.path.isfile(support_log):
                os.remove(support_log)
                LOGGER.info("Removed the files from local path after uploading to NFS share")
        else:
            LOGGER.error("Failed to supporting log file at location %s", resp[1])


def check_cortx_cluster_health():
    """Check the cluster health before each test is picked up for run."""
    LOGGER.info("Check cluster status for all nodes.")
    nodes = CMN_CFG["nodes"]
    for node in nodes:
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            if node["node_type"].lower() != "master":
                continue
        hostname = node['hostname']
        health = Health(hostname=hostname,
                        username=node['username'],
                        password=node['password'])
        result = health.check_node_health()
        assert_utils.assert_true(result[0],
                                 f'Cluster Node {hostname} failed in health check. Reason: {result}')
        health.disconnect()
    LOGGER.info("Cluster status is healthy.")


def check_cluster_storage():
    """Checks nodes storage and accepts till 98 % occupancy."""
    LOGGER.info("Check cluster storage for all nodes.")
    nodes = CMN_CFG["nodes"]
    for node in nodes:
        if CMN_CFG.get("product_family") == const.PROD_FAMILY_LC:
            if node["node_type"].lower() != "master":
                continue
        hostname = node['hostname']
        health = Health(hostname=hostname,
                        username=node['username'],
                        password=node['password'])
        ha_total, ha_avail, ha_used = health.get_sys_capacity()
        ha_used_percent = round((ha_used / ha_total) * 100, 1)
        assert ha_used_percent < 98.0, f'Cluster Node {hostname} failed space check.'
        health.disconnect()


def pytest_runtest_logstart(nodeid, location):
    """
    Hook used to identify if it is good to start next test.
    Should also work with parallel execution.
    :param nodeid: Node identifier for a test case. An absolute class path till function.
    :param location: file, line, test name.
    :return:
    """
    current_suite = None
    skip_health_check = False  # Skip health check for provisioner.
    breadcrumbs = os.path.split(location[0])
    for prefix in params.PROV_SKIP_TEST_FILES_HEALTH_CHECK_PREFIX:
        if breadcrumbs[-1].startswith(prefix):
            skip_health_check = True
            break
    path = "file://" + os.path.realpath(location[0])
    if location[1]:
        path += ":" + str(location[1] + 1)
    current_file = nodeid.split("::")[0]
    file_suite = current_file.split("/")[-1]
    if location[2].find(".") != -1:
        suite = location[2].split(".")[0]
        name = location[2].split(".")[-1]
    else:
        name = location[2]
        splitted = nodeid.split("::")
        try:
            ind = splitted.index(name.split("[")[0])
        except ValueError:
            try:
                ind = splitted.index(name)
            except ValueError:
                ind = 0
        if splitted[ind - 1] == current_file:
            suite = None
        else:
            suite = current_suite
    # Check health status of target
    target = Globals.TARGET
    h_chk = Globals.HEALTH_CHK
    if h_chk and not skip_health_check:
        check_health(target)


def check_health(target):
    try:
        check_cortx_cluster_health()
        try:
            check_cluster_storage()
        except (AssertionError, Exception) as fault:
            LOGGER.error(f"Cluster Storage {fault}")
    except AssertionError as fault:
        LOGGER.error(f"Health check failed for setup with exception {fault}")
        pytest.exit(f'Health check failed for cluster {target}', 3)
    except Exception as fault:
        # This could be permission issues as exception of anytype is handled.
        LOGGER.error(f"Health check script failed with exception {fault}")
        pytest.exit(f'Cannot continue as Health check script failed for {target}', 4)


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
    if report.when == 'setup' and report.outcome == 'passed':
        # If you reach here and when you know setup passed.
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
        remote_path = getattr(report, 'logpath').replace(":", "_")
        resp = system_utils.mount_upload_to_server(host_dir=params.NFS_SERVER_DIR,
                                                   mnt_dir=params.MOUNT_DIR,
                                                   remote_path=remote_path,
                                                   local_path=test_log)
        if resp[0]:
            LOGGER.info("Log file is uploaded at location : %s", resp[1])
        else:
            LOGGER.error("Failed to upload log file at location %s", resp[1])
        upload_supporting_logs(test_id, remote_path, "s3bench")
        upload_supporting_logs(test_id, remote_path, "")
        upload_supporting_logs(test_id, remote_path, "csm_gui")
        LOGGER.info("Adding log file path to %s", test_id)
        comment = "Log file path: {}".format(os.path.join(resp[1], name))
        if Globals.JIRA_UPDATE:
            jira_id, jira_pwd = get_jira_credential()
            task = jira_utils.JiraTask(jira_id, jira_pwd)
            try:
                if Globals.tp_meta['te_meta']['te_id'] == Globals.TE_TKT:
                    test_run_id = next(d['test_run_id'] for i, d in enumerate(
                        Globals.tp_meta['test_meta']) if d['test_id'] ==
                                       test_id)
                    resp = task.update_execution_details(
                        test_run_id=test_run_id, test_id=test_id,
                        comment=comment)
                    if resp:
                        LOGGER.info("Added execution details comment in: %s",
                                    test_id)
                    else:
                        LOGGER.error("Failed to comment to %s", test_id)
                else:
                    LOGGER.error("Failed to get correct TE id. \nExpected: "
                                 "%s\nActual: %s", Globals.TE_TKT,
                                 Globals.tp_meta['te_meta']['te_id'])
            except KeyError:
                LOGGER.error("KeyError: Failed to add log file path to %s",
                             test_id)


@pytest.fixture(scope='function')
def generate_random_string():
    """
    This fixture will return random string with lowercase
    :return: random string
    :rtype: str
    """
    return ''.join(random.choice(string.ascii_lowercase) for i in range(5))


def get_test_status(request, obj, max_timeout=5000):
    poll = time.time() + max_timeout  # max timeout
    while poll > time.time():
        time.sleep(2)
        if request.session.testsfailed:
            obj.event.set()
            break
        if Globals.ALL_RESULT:
            outcome = Globals.ALL_RESULT.outcome
            when = Globals.ALL_RESULT.when
            if 'passed' in outcome and 'call' in when:
                obj.event.set()
                break
            if 'error' in outcome and 'call' in when:
                obj.event.set()
                break


@pytest.fixture(scope='function', autouse=False)
def run_io_async(request):
    if request.config.option.data_integrity_chk:
        mgm_ops = ManagementOPs()
        secret_range = random.SystemRandom()

        if 'param' not in dir(request):
            nuser = secret_range.randint(2, 4)
            nbuckets = secret_range.randint(3, 3)
            file_counts = secret_range.randint(8, 25)
            prefs_dict = {'prefix_dir': f"async_io_{uuid.uuid4().hex}"}
        else:
            nuser = request.param["user"]
            nbuckets = request.param["buckets"]
            file_counts = request.param["files_count"]
            prefs_dict = request.param["prefs"]
        users = mgm_ops.create_account_users(nusers=nuser, use_cortx_cli=False)
        users_buckets = mgm_ops.create_buckets(nbuckets=nbuckets, users=users)
        run_data_check_obj = RunDataCheckManager(users=users_buckets)
        p = Thread(
            target=get_test_status, args=(request, run_data_check_obj))
        p.start()
        yield run_data_check_obj.start_io_async(
            users=users_buckets, buckets=None, files_count=file_counts,
            prefs=prefs_dict)
        # To stop upload running on the basis of test status
        p.join()
        run_data_check_obj.stop_io_async(
            users=users_buckets,
            di_check=request.config.option.data_integrity_chk,
        )
    else:
        yield


def filter_report_session_finish(session):
    if session.config.option.xmlpath:
        path = session.config.option.xmlpath
        tree = ET.parse(path)
        root = tree.getroot()
        with open(path, "w", encoding="utf-8") as logfile:
            logfile.write('<?xml version="1.0" encoding="UTF-8"?>')
            root[0].attrib["package"] = "root"
            for element in root[0]:
                element.attrib["classname"] = element.attrib[
                    "classname"].split(".")[-1]

            logfile.write(ET.tostring(root[0], encoding="unicode"))


@pytest.fixture(scope="class", autouse=False)
def restart_s3server_with_fault_injection(request):
    """Fixture to restart s3 server with fault injection."""
    request.cls.log = logging.getLogger(__name__)
    request.cls.log.info("Restart S3 Server with Fault Injection option")
    request.cls.log.info("Enable Fault Injection")
    fi_adapter = S3FailureInjection(cmn_cfg=CMN_CFG)
    resp = fi_adapter.set_fault_injection(flag=True)
    request.cls.fault_injection = True
    assert resp[0], resp[1]
    yield
    resp = fi_adapter.set_fault_injection(flag=False)
    request.cls.fault_injection = False
    assert resp[0], resp[1]
