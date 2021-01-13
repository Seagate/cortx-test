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
import csv


def pytest_addoption(parser) :
    parser.addoption(
        "--is_parallel", action="store", default="false", help="option: true or false"
    )


def read_test_list_csv() :
    try :
        with open('test_lists.csv') as f :
            reader = csv.reader(f)
            test_list = list(reader)
            return test_list
    except Exception as e :
        print(e)


def pytest_collection_modifyitems(config, items) :
    required_tests = read_test_list_csv()
    selected_items = []
    for item in items :
        parallel_found = 'false'
        test_found = ''
        for mark in item.iter_markers() :
            if mark.name == 'parallel' :
                parallel_found = 'true'
                if config.option.is_parallel == 'false' :
                    break
            elif mark.name == 'tags' :
                test_found = mark.args[0]
        if parallel_found == config.option.is_parallel and test_found != '' :
            if [test_found] in required_tests :
                selected_items.append(item)
    items[:] = selected_items


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call) :
    # execute all other hooks to obtain the report object
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
    mode = "a" if os.path.exists(current_file) else "w"
    with open(current_file, mode) as f :
        # let's also access a fixture
        if "tmpdir" in item.fixturenames :
            extra = " ({})".format(item.funcargs["tmpdir"])
        else :
            extra = ""
        f.write(rep.nodeid + extra + "\n")
