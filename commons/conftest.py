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
import pathlib
import json
import logging
from testfixtures import LogCapture
from commons.utils import yaml_utils
from commons import Globals

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()
    print(rep)
    # we only look at actual failing test calls, not setup/teardown
    fail_file = 'failed_tests.log'
    pass_file = 'passed_tests.log'
    current_file = 'other_test_calls.log'
    if rep.failed:
        current_file = fail_file
    elif rep.passed:
        current_file = pass_file
    mode = "a" if os.path.exists(current_file) else "w"
    with open(current_file, mode) as f:
        # let's also access a fixture
        if "tmpdir" in item.fixturenames:
            extra = " ({})".format(item.funcargs["tmpdir"])
        else:
            extra = ""
        f.write(rep.nodeid + extra + "\n")

@pytest.fixture(autouse=True)
def _read_project_config(request):
    file = pathlib.Path(request.node.fspath)
    print('current test file:', file)
    config = file.with_name('config.json')
    print('current config file:', config)
    with config.open() as fp:
        contents = json.load(fp)
    print('config contents:', contents)


@pytest.fixture(autouse=True)
def read_project_config(request):
    f = pathlib.Path(request.node.fspath.strpath)
    config = f.with_name('config.json')
    with config.open() as fp:
        return json.load(fp)


def init_loghandler(log): #TODO needs to be removed after framework Logger is developed
    log.setLevel(logging.DEBUG)
    fh = logging.FileHandler('pytestfeatures.log', mode='a')
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    log.addHandler(fh)
    log.addHandler(ch)


@pytest.fixture(autouse=True)
def capture():
    with LogCapture() as logs:
        yield logs


@pytest.fixture(scope='session')
def formatter():
    format_log_message = '%(asctime)s\t%(levelname)s\t%(filename)s\t%(funcName)s\t%(processName)s\t%(message)s'
    formatter = logging.Formatter(fmt=format_log_message, datefmt='%Y-%m-%d %H:%M:%S')
    return formatter

@pytest.fixture(scope='session')
def logger():
    logging.basicConfig(format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    init_loghandler(logger)  #TODO reference
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


@pytest.fixture
def data():
    pytest.req_timeout_global = 30


def test_config():
    test_cfg = yaml_utils.read_yaml('di_config.yaml')
    yield

# content of conftest.py


def pytest_collection_modifyitems(session, config, items):
    for item in items:
        for marker in item.iter_markers(name="test_id"):
            test_id = marker.args[0]
            item.user_properties.append(("test_id", test_id))


