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
# -*- coding: utf-8 -*-
# !/usr/bin/python
import pytest
import pathlib
import json
from commons.utils import config_utils

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


@pytest.fixture
def test_config():
    test_cfg = config_utils.read_yaml('di_config.yaml')
    yield test_cfg
