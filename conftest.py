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
from _pytest.nodes import Item
from _pytest.runner import CallInfo
from testfixtures import LogCapture
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
    logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    cortxlogging.init_loghandler(logger)  #TODO reference
    return logger


@pytest.fixture(scope='function')
def log_cutter(request, formatter):
    print("setup")
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
def pytest_addoption(parser) :
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
    required_tests = read_test_list_csv()
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
            if [test_found] in required_tests:
                selected_items.append(item)
        CACHE.store(item.nodeid, test_found)
    items[:] = selected_items


# @pytest.hookimpl(hookwrapper=True)
# def pytest_runtest_makereport(item: Item, call: CallInfo):
#     # All code prior to yield statement would be ran prior
#     # to any other of the same fixtures defined
#
#     outcome = yield  # Run all other pytest_runtest_makereport non wrapped hooks
#     result = outcome.get_result()
#     if result.when == "call" and result.failed:
#         try:  # Just to not crash py.test reporting
#             with open(str(FAILURES_FILE), "a") as f:
#                 f.write(result.nodeid + "\n")
#         except Exception as e:
#             print("ERROR", e)
#             pass


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call) :
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()
    # we only look at actual failing test calls, not setup/teardown
    fail_file = 'failed_tests.log'
    pass_file = 'passed_tests.log'
    current_file = 'other_test_calls.log'
    if rep.failed :
        current_file = fail_file
    elif rep.passed :
        current_file = pass_file
    mode = "a" if os.path.exists(current_file) else "w"
    with open(current_file, mode) as f :
        # let's also access a fixture
        if "tmpdir" in item.fixturenames :
            extra = " ({})".format(item.funcargs["tmpdir"])
        else :
            extra = ""
        f.write(rep.nodeid + extra + "\n")


def pytest_runtest_logreport(report: "TestReport") -> None:
    if report.when == 'teardown':
        log = report.caplog
        ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
        ansi_escape.sub('', log)
        logs = log.split('\n')
        test_id = CACHE.lookup(report.nodeid)
        name = str(test_id) + report.nodeid.split('::')[1]
        with open(name, 'w') as fp:
            for rec in logs:
                fp.write(rec + '\n')
        jira_id, jira_pwd = get_jira_credential()
        task = jira_utils.JiraTask(jira_id, jira_pwd)
        task.update_test_jira_status(Globals.TE_TKT, test_id, report.outcome.capitalize())



