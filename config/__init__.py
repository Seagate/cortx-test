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
"""Configs are initialized here."""
import ast
import os.path
import sys
from typing import List

import munch

from src.commons import configmanager
from src.commons.params import IO_DRIVER_CFG_PATH
from src.commons.params import S3_CONFIG
from src.commons.params import S3_IO_CFG_PATH
from src.commons.utils import config_utils


def split_args(sys_cmd: List):
    """split args and make it compliant."""
    _args = list()
    for item in sys_cmd:
        if item.find('=') != -1:
            _args.extend(item.split('='))
        else:
            _args.extend([item])

    return _args


def get_local_aws_keys():
    """Fetch local aws access secret keys."""
    path = S3_CFG["aws_path"]
    section = S3_CFG["aws_cred_section"]
    if os.path.exists(path):
        try:
            aws_access_key = config_utils.get_config(path, section, "aws_access_key_id")
            aws_secret_key = config_utils.get_config(path, section, "aws_secret_access_key")
            return aws_access_key, aws_secret_key
        except KeyError:
            pass
    return None, None


IO_DRIVER_CFG = configmanager.get_config_yaml(IO_DRIVER_CFG_PATH)
S3_CFG = configmanager.get_config_yaml(fpath=S3_CONFIG)
CMN_CFG = configmanager.get_config_wrapper(fpath=S3_IO_CFG_PATH)

io_driver_args = split_args(sys.argv)
_use_ssl = '-us' if '-us' in io_driver_args else '--use_ssl' if '--use_ssl' in io_driver_args \
    else None
ssl_flg = io_driver_args[io_driver_args.index(_use_ssl) + 1] if _use_ssl else True
_endpoint = '-ep' if '-ep' in io_driver_args else '--endpoint' if '--endpoint' in io_driver_args \
    else None
s3_url = io_driver_args[io_driver_args.index(_endpoint) + 1] if _endpoint else "s3.seagate.com"
_access_key = "-ak" if '-ak' in io_driver_args else '--access_key' if '--access_key' in \
                                                                      io_driver_args else None
access_key = io_driver_args[io_driver_args.index(_access_key) + 1] if _access_key else None
_secret_key = "-sk" if '-sk' in io_driver_args else '--secret_key' if '--secret_key' in \
                                                                      io_driver_args else None
secret_key = io_driver_args[io_driver_args.index(_secret_key) + 1] if _secret_key else None
use_ssl = ast.literal_eval(str(ssl_flg).title())
s3_endpoint = f"{'https' if use_ssl else 'http'}://{s3_url}"

S3_CFG["access_key"] = access_key if access_key else get_local_aws_keys()[0]
S3_CFG["secret_key"] = secret_key if secret_key else get_local_aws_keys()[1]
S3_CFG["use_ssl"] = use_ssl
S3_CFG["endpoint"] = s3_endpoint

# Munched configs. These can be used by dot "." operator.
S3_CFG = munch.munchify(S3_CFG)
