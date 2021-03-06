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
from commons.params import COMMON_CONFIG, CSM_CONFIG, S3_CONFIG
from commons.params import RAS_CONFIG_PATH
from commons.params import SSPL_TEST_CONFIG_PATH
from commons.params import COMMON_DESTRUCTIVE_CONFIG_PATH
import pdb
pdb.set_trace()
pytest_args = sys.argv
if '--local' in pytest_args and '--target' in pytest_args:
    if pytest_args[pytest_args.index("--local") + 1]:
        target = pytest_args[pytest_args.index("--target") + 1]
elif os.getenv('TARGET') is not None:
    target = os.environ["TARGET"]
else:
    target = None

CMN_CFG = configmanager.get_config_wrapper(fpath=COMMON_CONFIG, target=target)
CSM_REST_CFG = configmanager.get_config_wrapper(fpath=CSM_CONFIG, config_key="Restcall",
                                                target=target, target_key="csm")
CSM_CFG = configmanager.get_config_wrapper(fpath=CSM_CONFIG)
S3_CFG = configmanager.get_config_wrapper(fpath=S3_CONFIG, target=target, target_key="s3")
RAS_VAL = configmanager.get_config_wrapper(fpath=RAS_CONFIG_PATH)
CMN_DESTRUCTIVE_CFG = configmanager.get_config_wrapper(fpath=COMMON_DESTRUCTIVE_CONFIG_PATH)
RAS_TEST_CFG = config_utils.read_yaml(SSPL_TEST_CONFIG_PATH)[1]
