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

import sys
import ast
import munch
from typing import List
from commons import configmanager
from commons.params import S3_CONFIG
from commons.params import IO_DRIVER_CFG_PATH


def split_args(sys_cmd: List):
    """split args and make it compliant."""
    eq_splitted = list()
    for item in sys_cmd:
        if item.find('=') != -1:
            eq_splitted.extend(item.split('='))
        else:
            eq_splitted.extend([item])

    return eq_splitted


io_driver_args = split_args(sys.argv)
_use_ssl = '-us' if '-us' in io_driver_args else '--use_ssl'
ssl_flg = io_driver_args[io_driver_args.index(_use_ssl) + 1] if _use_ssl else True
_endpoint = '-ep' if '-ep' in io_driver_args else '--endpoint'
s3_url = io_driver_args[io_driver_args.index(_endpoint) + 1] if _endpoint else "s3.seagate.com"

use_ssl = ast.literal_eval(str(ssl_flg).title())
s3_endpoint = f"{'https' if ssl_flg else 'http'}://{s3_url}"

S3_CFG = configmanager.get_config_yaml(fpath=S3_CONFIG)
S3_CFG["use_ssl"] = use_ssl
S3_CFG["s3_url"] = s3_endpoint
IO_DRIVER_CFG = configmanager.get_config_yaml(IO_DRIVER_CFG_PATH)
# Munched configs. These can be used by dot "." operator.

s3_cfg = munch.munchify(S3_CFG)
