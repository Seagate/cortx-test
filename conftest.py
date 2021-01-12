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
from _pytest.nodes import Item
from _pytest.runner import CallInfo
from testfixtures import LogCapture
from commons.utils import yaml_utils
from commons import Globals
from commons import cortxlogging

pytest_plugins = [
    "commons.conftest",
]

FAILURES_FILE = "failures.txt"


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
