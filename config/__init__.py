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
import os.path
import sys
import ast
import munch
from typing import List
from commons import configmanager
from commons.utils import config_utils
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


def get_local_aws_keys():
    """Fetch local aws access secret keys."""
    path = S3_CFG["aws_path"]
    section = S3_CFG["aws_cred_section"]
    if os.path.exists(path):
        try:
            aws_access_key = config_utils.get_config(path, section, "aws_access_key_id")
            aws_secret_key = config_utils.get_config(path, section, "aws_secret_access_key")
            return aws_access_key, aws_secret_key
        except BaseException:
            pass
    return None, None


IO_DRIVER_CFG = configmanager.get_config_yaml(IO_DRIVER_CFG_PATH)
S3_CFG = configmanager.get_config_yaml(fpath=S3_CONFIG)

io_driver_args = split_args(sys.argv)
_use_ssl = '-us' if '-us' in io_driver_args else '--use_ssl' if '--use_ssl' in io_driver_args\
    else None
ssl_flg = io_driver_args[io_driver_args.index(_use_ssl) + 1] if _use_ssl else True
_endpoint = '-ep' if '-ep' in io_driver_args else '--endpoint' if '--endpoint' in io_driver_args\
    else None
s3_url = io_driver_args[io_driver_args.index(_endpoint) + 1] if _endpoint else "s3.seagate.com"
_access_key = "-ak" if '-ak' in io_driver_args else '--access_key' if '--access_key' in\
                                                                      io_driver_args else None
access_key = io_driver_args[io_driver_args.index(_access_key) + 1] if _access_key else None
_secret_key = "-ak" if '-ak' in io_driver_args else '--secret_key' if '--secret_key' in\
                                                                      io_driver_args else None
secret_key = io_driver_args[io_driver_args.index(_secret_key) + 1] if _secret_key else None
use_ssl = ast.literal_eval(str(ssl_flg).title())
s3_endpoint = f"{'https' if ssl_flg else 'http'}://{s3_url}"


ACCESS_KEY = access_key if access_key else get_local_aws_keys()[0]
SECRET_KEY = secret_key if secret_key else get_local_aws_keys()[1]
S3_CFG["use_ssl"] = use_ssl
S3_CFG["endpoint"] = s3_endpoint

# Munched configs. These can be used by dot "." operator.
S3_CFG = munch.munchify(S3_CFG)
