# -*- coding: utf-8 -*-
# !/usr/bin/python
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

"""S3 configs are initialized here."""

import sys
import ast

from commons import configmanager
from commons.params import S3_CONFIG
from commons.params import DEL_CFG_PATH
from commons.params import S3_OBJ_TEST_CONFIG
from commons.params import S3_BKT_TEST_CONFIG
from commons.params import S3CMD_TEST_CONFIG
from commons.params import S3_BLACK_BOX_CONFIG_PATH
from commons.params import S3_USER_ACC_MGMT_CONFIG_PATH
from commons.params import S3_TEMP_CRED_CONFIG_PATH
from commons.params import S3_MPART_CFG_PATH
from commons.params import DEL_CFG_PATH
from commons.params import S3_LDAP_TEST_CONFIG

pytest_args = list()
for arg in sys.argv:
    if arg.find('=') != -1:
        pytest_args.extend(arg.split('='))
    else:
        pytest_args.extend([arg])

_target = '-tg' if '-tg' in pytest_args else '--target' if '--target' in pytest_args else None
target = pytest_args[pytest_args.index(_target) + 1] if _target else None

_use_ssl = '-s' if '-s' in pytest_args else '--use_ssl' if '--use_ssl' in pytest_args else None
use_ssl = pytest_args[pytest_args.index(_use_ssl) + 1] if _use_ssl else True

_validate_certs = '-c' if '-c' in pytest_args else '--validate_certs' if '--validate_certs' in pytest_args else None
validate_certs = pytest_args[pytest_args.index(_validate_certs) + 1] if _validate_certs else True


def build_s3_endpoints() -> dict:
    """This function will create s3/iam url based on certificates availability and ssl usages."""
    s3_conf = configmanager.get_config_wrapper(fpath=S3_CONFIG)
    setup_details = configmanager.get_config_wrapper(target=target)
    lb_flg = setup_details.get('lb') not in [None, '', "FQDN without protocol(http/s)"]
    s3_url = setup_details.get('lb') if lb_flg else "s3.seagate.com"
    iam_url = setup_details.get('lb') if lb_flg else "iam.seagate.com"
    ssl_flg = ast.literal_eval(str(use_ssl).title())
    cert_flg = ast.literal_eval(str(validate_certs).title())
    s3_conf["s3_url"] = f"{'https' if ssl_flg else 'http'}://{s3_url}"
    if ssl_flg:
        s3_conf["iam_url"] = f"https://{iam_url}:{s3_conf['https_iam_port']}"
    else:
        s3_conf["iam_url"] = f"http://{iam_url}:{s3_conf['http_iam_port']}"
    s3_conf["s3b_url"] = f"{'https' if cert_flg else 'http'}://{s3_url}"
    s3_conf["use_ssl"] = ssl_flg
    s3_conf["validate_certs"] = cert_flg

    return s3_conf


if target:
    S3_CFG = build_s3_endpoints()
else:
    S3_CFG = configmanager.get_config_wrapper(fpath=S3_CONFIG)
DEL_CFG = configmanager.get_config_wrapper(fpath=DEL_CFG_PATH)
S3_OBJ_TST = configmanager.get_config_wrapper(fpath=S3_OBJ_TEST_CONFIG)
S3_BKT_TST = configmanager.get_config_wrapper(fpath=S3_BKT_TEST_CONFIG)
S3CMD_CNF = configmanager.get_config_wrapper(fpath=S3CMD_TEST_CONFIG)
S3_USER_ACC_MGMT_CONFIG = configmanager.get_config_wrapper(fpath=S3_USER_ACC_MGMT_CONFIG_PATH)
S3_BLKBOX_CFG = configmanager.get_config_wrapper(fpath=S3_BLACK_BOX_CONFIG_PATH)
S3_TMP_CRED_CFG = configmanager.get_config_wrapper(fpath=S3_TEMP_CRED_CONFIG_PATH)
MPART_CFG = configmanager.get_config_wrapper(fpath=S3_MPART_CFG_PATH)
DEL_CFG = configmanager.get_config_wrapper(fpath=DEL_CFG_PATH)
S3_LDAP_TST_CFG = configmanager.get_config_wrapper(fpath=S3_LDAP_TEST_CONFIG)
