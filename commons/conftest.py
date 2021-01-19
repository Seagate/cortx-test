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
import csv
from _pytest.nodes import Item
from _pytest.runner import CallInfo
from testfixtures import LogCapture
from commons.utils import yaml_utils
from commons import Globals
from commons import cortxlogging

FAILURES_FILE = "failures.txt"

@pytest.fixture(autouse=True)
def _read_project_config(request):
    file = pathlib.Path(request.node.fspath)
    print('current test file:', file)
    config = file.with_name('config.json')
    print('current config file:', config)
    with config.open() as fp:
        contents = json.load(fp)
    print('config contents:', contents)


@pytest.fixture
def data():
    pytest.req_timeout_global = 30


def test_config():
    test_cfg = yaml_utils.read_yaml('di_config.yaml')
    yield
