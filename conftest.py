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
# -*- coding: utf-8 -*-
# !/usr/bin/python
import pytest
import os
import pathlib
import json
import logging
import csv
import re
import builtins
import datetime
from _pytest.nodes import Item
from _pytest.runner import CallInfo
from testfixtures import LogCapture
from strip_ansi import strip_ansi
from commons.utils import yaml_utils
from commons import Globals
from commons import cortxlogging
from commons.utils import jira_utils
from core.runner import LRUCache
from core.runner import get_jira_credential

pytest_plugins = [
    "commons.conftest",
]

FAILURES_FILE = "failures.txt"
LOG_DIR = 'log'
CACHE = LRUCache(1024 * 10)

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


@pytest.fixture(autouse=True, scope='session')
def cleanup(request):
    """
    This Fixture renames the the log/latest folder to a name with current timestamp
    and creates a folder named latest.
    :param request:
    :return:
    """
    root_dir = pathlib.Path(request.node.fspath.strpath)
    log_dir = os.path.join(root_dir, 'log')
    now = str(datetime.datetime.now())
    now = now.replace(' ', '-')  #now has a space in timestamp
    now = now.replace(':', '_')
    if os.path.exists(log_dir) and os.path.isdir(log_dir):
        latest = os.path.join(log_dir,'latest')
        if os.path.isdir(latest) and os.path.exists(latest):
            os.rename(latest, os.path.join(log_dir, now))
        os.makedirs(latest)
    else:
        os.makedirs(os.path.join(log_dir,'latest'))


# content of conftest.py

def pytest_addoption(parser) :
    """
    Hook to add options at runtime to pytest command
    :param parser:
    :return:
    """
    parser.addoption(
        "--is_parallel", action="store", default="false", help="option: true or false"
    )
    parser.addoption(
        "--te_tkt", action="store", default="", help="TE ticket's ID"
    )
    parser.addoption(
        "--logpath", action="store", default=None, help="Log root folder path"
    )


def read_test_list_csv() :
    try :
        with open('test_lists.csv') as f :
            reader = csv.reader(f)
            test_list = list(reader)
            return test_list
    except Exception as e :
        print(e)


def pytest_collection_modifyitems(config, items):
    """
    A hooks which gets called after pytest collects items. This provides an intercept
     to modify items at run time based on tags. Intention is to group TE tests into
     parallel and non parallel groups.
     This function's behaviour will change depending on the test execution framework
     integration.
    :param config:
    :param items:
    :return:
    """
    required_tests = read_test_list_csv() # e.g. ['TEST-17413', 'TEST-17414']
    Globals.TE_TKT = config.option.te_tkt
    selected_items = []
    for item in items:
        parallel_found = 'false'
        test_found = ''
        for mark in item.iter_markers():
            if mark.name == 'parallel':
                parallel_found = 'true'
                if config.option.is_parallel == 'false':
                    break
            elif mark.name == 'tags' :
                test_found = mark.args[0]
        if parallel_found == config.option.is_parallel and test_found != '':
            if test_found in required_tests:
                selected_items.append(item)
        CACHE.store(item.nodeid, test_found)
    items[:] = selected_items


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Execute all other hooks to obtain the report object. Follow the pytest execution protocol
    to understand where does this fucntion fits in. In short this function will help to create
    failed, passed lists in multiple runs. The clean up of logs files should happen before the
    test runs starts.
    All code prior to yield statement would be ran prior
    to any other of the same fixtures defined
    :param item:
    :param call:
    :return:
    """
    outcome = yield
    rep = outcome.get_result()
    # print(rep)
    # we only look at actual failing test calls, not setup/teardown
    fail_file = 'failed_tests.log'
    pass_file = 'passed_tests.log'
    current_file = 'other_test_calls.log'
    if rep.failed :
        current_file = fail_file
    elif rep.passed :
        current_file = pass_file
    current_file = os.path.join(os.getcwd(), LOG_DIR, 'latest', current_file)
    mode = "a" if os.path.exists(current_file) else "w"
    with open(current_file, mode) as f :
        # let's also access a fixture
        if "tmpdir" in item.fixturenames :
            extra = " ({})".format(item.funcargs["tmpdir"])
        else :
            extra = ""
        f.write(rep.nodeid + extra + "\n")


def pytest_runtest_logreport(report: "TestReport") -> None:
    """
    Provides an intercept to create a) generate log per test case
    b) Update Jira with result at different phases within a test (setup, call, teardown)
    c) Call Reports REST API to update Report DB (Mongo)
    :param report:
    :return:
    """
    jira_id, jira_pwd = get_jira_credential()
    task = jira_utils.JiraTask(jira_id, jira_pwd)
    test_id = CACHE.lookup(report.nodeid)
    if report.when == 'setup':
        task.update_test_jira_status(Globals.TE_TKT, test_id, 'Executing')
        pass
    elif report.when == 'call':
        task.update_test_jira_status(Globals.TE_TKT, test_id, 'Executing')
        pass
    elif report.when == 'teardown':
        log = report.caplog
        log = strip_ansi(log)
        logs = log.split('\n')
        test_id = CACHE.lookup(report.nodeid)
        name = str(test_id) + '_' + report.nodeid.split('::')[1]
        test_log = os.path.join(os.getcwd(), LOG_DIR, 'latest', name)
        with open(test_log, 'w') as fp:
            for rec in logs:
                fp.write(rec + '\n')
        if report.outcome in ['passed', 'Passed']:
            task.update_test_jira_status(Globals.TE_TKT, test_id, 'PASS')
        elif report.outcome in ['failed', 'Failed']:
            task.update_test_jira_status(Globals.TE_TKT, test_id, 'FAIL')





