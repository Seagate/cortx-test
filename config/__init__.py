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
from commons.utils import config_utils
from commons import configmanager
from config.params import COMMON_CONFIG, CSM_CONFIG
from config.params import RAS_CONFIG_PATH
from config.params import SSPL_TEST_CONFIG_PATH
from config.params import COMMON_DESTRUCTIVE_CONFIG_PATH


RAS_VAL = config_utils.read_yaml(RAS_CONFIG_PATH)[1]
RAS_TEST_CFG = config_utils.read_yaml(SSPL_TEST_CONFIG_PATH)[1]
CMN_DESTRUCTIVE_CFG = config_utils.read_yaml(COMMON_DESTRUCTIVE_CONFIG_PATH)[1]
CSM_CFG = configmanager.get_config_wrapper(fpath=CSM_CONFIG)

pytest_args = sys.argv
pytest_args = dict(zip(pytest_args[::2],pytest_args[1::2]))

if '--local' in pytest_args and pytest_args['--local']:
    target = pytest_args['--target']
elif os.getenv('TARGET') is not None:
    target = os.environ["TARGET"]

CMN_CFG = configmanager.get_config_wrapper(fpath=COMMON_CONFIG, target=target)
