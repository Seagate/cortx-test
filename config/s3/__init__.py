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
"""S3 configs are initialized here."""

import os
import sys
import ast

from commons import configmanager
from commons.params import S3_CONFIG
from commons.configmanager import get_config_db

pytest_args = list()
for arg in sys.argv:
    if arg.find('=') != -1:
        pytest_args.extend(arg.split('='))
    else:
        pytest_args.extend([arg])

_target = '-tg' if '-tg' in pytest_args else '--target' if '--target' in pytest_args else None
if _target:
    target = pytest_args[pytest_args.index(_target) + 1]

_use_ssl = '-s' if '-s' in pytest_args else '--use_ssl' if '--use_ssl' in pytest_args else True
if _use_ssl:
    use_ssl = pytest_args[pytest_args.index(_use_ssl) + 1]

_validate_certs = '-c' if '-c' in pytest_args else '--validate_certs' if '--validate_certs' in pytest_args else True
if _validate_certs:
    validate_certs = pytest_args[pytest_args.index(_validate_certs) + 1]


def build_s3_endpoints() -> dict:
    """This function will create s3/iam url based on certificates availability and ssl usages."""
    setup_query = {"setupname": target}
    s3_conf = configmanager.get_config_wrapper(fpath=S3_CONFIG)
    setup_details = get_config_db(setup_query=setup_query)[target]
    lb_flg = setup_details.get('lb') not in [None, '', "FQDN without protocol(http/s)"]
    s3_url = setup_details.get('lb') if lb_flg else "s3.seagate.com"
    iam_url = setup_details.get('lb') if lb_flg else "iam.seagate.com"
    ssl_flg = ast.literal_eval(str(use_ssl).title())
    cert_flg = ast.literal_eval(str(validate_certs).title())
    s3_conf["s3_url"] = f"{'https' if ssl_flg else 'http'}://{s3_url}"
    # As per observation iam operations required https only.
    s3_conf["iam_url"] = f"https://{iam_url}:{s3_conf['iam_port']}"
    s3_conf["use_ssl"] = ssl_flg
    s3_conf["validate_certs"] = cert_flg
    if not os.path.exists(s3_conf["s3_cert_path"]) and cert_flg:
        raise IOError(f'Certificate path {s3_conf["s3_cert_path"]} does not exists.')

    return s3_conf


if _target:
    S3_CFG = build_s3_endpoints()
else:
    S3_CFG = configmanager.get_config_wrapper(fpath=S3_CONFIG)
