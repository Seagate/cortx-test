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
"""Configs are initialized here."""
import os
import sys
import re
from typing import List
from commons.utils import config_utils
from commons import configmanager
from commons.params import COMMON_CONFIG, CSM_CONFIG, S3_CONFIG
from commons.params import S3_OBJ_TEST_CONFIG
from commons.params import RAS_CONFIG_PATH
from commons.params import SSPL_TEST_CONFIG_PATH
from commons.params import COMMON_DESTRUCTIVE_CONFIG_PATH
from commons.params import PROV_TEST_CONFIG_PATH


def split_args(sys_cmd: List):
    """split args and make it compliant."""
    eq_splitted = list()
    for item in sys_cmd:
        if item.find('=') != -1:
            eq_splitted.extend(item.split('='))
        else:
            eq_splitted.extend([item])
    return eq_splitted


pytest_args = sys.argv
proc_name = os.path.split(pytest_args[0])[-1]
target_filter = re.compile(".*--target")
pytest_args = split_args(pytest_args)  # sanitize

if proc_name == 'pytest' and '--local' in pytest_args and '--target' in pytest_args:
    # This condition will execute when args ore in format ['--target','<target name'>]
    if pytest_args[pytest_args.index("--local") + 1]:
        target = pytest_args[pytest_args.index("--target") + 1]
elif proc_name == 'pytest' and '--target' in pytest_args and '--local' not in pytest_args:
    # This condition will execute for non local test runner execution
    target = pytest_args[pytest_args.index("--target") + 1].lower()
elif proc_name == 'pytest' and '--target' in pytest_args:
    # This condition will execute when args ore in format ['--target=<target name'>]
    target = list(filter(target_filter.match, pytest_args))[0].split("=")[1].lower()
elif proc_name == 'pytest' and os.getenv('TARGET') is not None:  # test runner process
    # This condition will execute when target is passed from environment
    target = os.environ["TARGET"]
else:
    target = None

CMN_CFG = configmanager.get_config_wrapper(fpath=COMMON_CONFIG, target=target)
CSM_REST_CFG = configmanager.get_config_wrapper(fpath=CSM_CONFIG, config_key="Restcall",
                                                target=target, target_key="csm")
CSM_CFG = configmanager.get_config_wrapper(fpath=CSM_CONFIG)
S3_CFG = configmanager.get_config_wrapper(fpath=S3_CONFIG, target=target, target_key="s3")
S3_OBJ_TST = configmanager.get_config_wrapper(fpath=S3_OBJ_TEST_CONFIG, target=target, target_key="s3")
RAS_VAL = configmanager.get_config_wrapper(fpath=RAS_CONFIG_PATH,
                                           target=target, target_key="csm")
CMN_DESTRUCTIVE_CFG = configmanager.get_config_wrapper(fpath=COMMON_DESTRUCTIVE_CONFIG_PATH)
RAS_TEST_CFG = configmanager.get_config_wrapper(fpath=SSPL_TEST_CONFIG_PATH)
PROV_CFG = configmanager.get_config_wrapper(fpath=PROV_TEST_CONFIG_PATH)
