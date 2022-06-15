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
import os
import sys
import ast
import re
import munch
from typing import List
from commons import configmanager
from commons.params import S3_CONFIG
from commons.params import DURABILITY_CFG_PATH
from commons.params import COMMON_CONFIG
from commons.params import CSM_CONFIG
from commons.params import RAS_CONFIG_PATH
from commons.params import SSPL_TEST_CONFIG_PATH
from commons.params import COMMON_DESTRUCTIVE_CONFIG_PATH
from commons.params import PROV_TEST_CONFIG_PATH
from commons.params import DEPLOY_TEST_CONFIG_PATH
from commons.params import DI_CONFIG_PATH
from commons.params import DATA_PATH_CONFIG_PATH
from commons.params import HA_TEST_CONFIG_PATH
from commons.params import PROV_CONFIG_PATH
from commons.constants import PROD_FAMILY_LC
from commons.constants import S3_ENGINE_RGW
from commons.params import DTM_TEST_CFG_PATH


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
CSM_CHECKS = False
if proc_name == 'pytest' and '--local' in pytest_args and '--target' in pytest_args:
    # This condition will execute when args ore in format ['--target','<target name'>]
    if pytest_args[pytest_args.index("--local") + 1]:
        target = pytest_args[pytest_args.index("--target") + 1]
    os.environ["TARGET"] = target
elif proc_name == 'pytest' and '--target' in pytest_args and '--local' not in pytest_args:
    # This condition will execute for non local test runner execution
    target = pytest_args[pytest_args.index("--target") + 1].lower()
elif proc_name == 'pytest' and '--target' in pytest_args:
    # This condition will execute when args ore in format ['--target=<target name'>]
    target = list(filter(target_filter.match, pytest_args))[0].split("=")[1].lower()
elif proc_name == 'pytest' and os.getenv('TARGET') is not None:  # test runner process
    # This condition will execute when target is passed from environment
    target = os.environ["TARGET"]
elif proc_name not in ["testrunner.py", "testrunner"]:
    target = os.environ.get("TARGET")
# Will revisit this once we fix the singleton/s3helper issue
elif proc_name in ["testrunner.py", "testrunner"]:
    if '-tg' in pytest_args:
        target = pytest_args[pytest_args.index("-tg") + 1]
    elif '--target' in pytest_args:
        target = pytest_args[pytest_args.index("--target") + 1]
    else:
        target = os.environ.get("TARGET") if os.environ.get("TARGET") else None
else:
    target = None
if target and proc_name in ["testrunner.py", "testrunner", "pytest"]:
    _use_ssl = ('-s' if '-s' in pytest_args else (
         '--use_ssl' if '--use_ssl' in pytest_args else None))
    use_ssl = pytest_args[
        pytest_args.index(_use_ssl) + 1] if _use_ssl else True
    os.environ["USE_SSL"] = str(use_ssl)

    _csm_checks = ('-csm' if '-csm' in pytest_args else (
        '--csm_checks' if '--csm_checks' in pytest_args else None))
    CSM_CHECKS = pytest_args[
        pytest_args.index(_csm_checks) + 1] if _csm_checks else False
    data = {'True': True, 'False': False , True : True , False : False }
    CSM_CHECKS = data.get(CSM_CHECKS)

    _validate_certs = ('-c' if '-c' in pytest_args else (
        '--validate_certs' if '--validate_certs' in pytest_args else None))
    validate_certs = pytest_args[
        pytest_args.index(_validate_certs) + 1] if _validate_certs else True
    os.environ["VALIDATE_CERTS"] = str(validate_certs)

def build_s3_endpoints() -> dict:
    """This function will create s3/iam url based on certificates availability and ssl usages."""
    s3_conf = configmanager.get_config_wrapper(fpath=S3_CONFIG)
    setup_details = configmanager.get_config_wrapper(target=target)
    lb_flg = setup_details.get('lb') not in [None, '', "FQDN without protocol(http/s)"]
    s3_url = setup_details.get('lb') if lb_flg else "s3.seagate.com"
    iam_url = setup_details.get('lb') if lb_flg else "iam.seagate.com"
    ssl_flg = ast.literal_eval(str(os.environ.get("USE_SSL")).title())
    cert_flg = ast.literal_eval(str(os.environ.get("VALIDATE_CERTS")).title())
    s3_conf["host_port"] = s3_url  # may be of LB/Host Entry/Node.
    s3_conf["s3_url"] = f"{'https' if ssl_flg else 'http'}://{s3_url}"
    if ssl_flg:
        s3_conf["iam_url"] = f"https://{iam_url}:{s3_conf['https_iam_port']}"
    else:
        s3_conf["iam_url"] = f"http://{iam_url}:{s3_conf['http_iam_port']}"
    s3_conf["use_ssl"] = ssl_flg
    s3_conf["validate_certs"] = cert_flg

    return s3_conf


if target:
    S3_CFG = build_s3_endpoints()  # Importing S3cfg from config init can be dangerous.Use s3 init.
else:
    S3_CFG = configmanager.get_config_wrapper(fpath=S3_CONFIG)

CMN_CFG = configmanager.get_config_wrapper(fpath=COMMON_CONFIG, target=target)
if S3_ENGINE_RGW == CMN_CFG["s3_engine"]:
    S3_CFG["region"] = "default"
CMN_CFG.update(S3_CFG)
JMETER_CFG = configmanager.get_config_wrapper(
    fpath=CSM_CONFIG, config_key="JMeterConfig", target=target, target_key="csm")

if PROD_FAMILY_LC == CMN_CFG["product_family"]:
    CSM_REST_CFG = configmanager.get_config_wrapper(
        fpath=CSM_CONFIG, config_key="Restcall_LC", target=target, target_key="csm")
else:
    CSM_REST_CFG = configmanager.get_config_wrapper(
        fpath=CSM_CONFIG, config_key="Restcall", target=target, target_key="csm")

CSM_CFG = configmanager.get_config_wrapper(fpath=CSM_CONFIG)
if CSM_CHECKS:
    CSM_REST_CFG["msg_check"] = "enable"
    CSM_CFG["Restcall"]["msg_check"] = "enable"
RAS_VAL = configmanager.get_config_wrapper(
    fpath=RAS_CONFIG_PATH, target=target, target_key="csm")
CMN_DESTRUCTIVE_CFG = configmanager.get_config_wrapper(fpath=COMMON_DESTRUCTIVE_CONFIG_PATH)
RAS_TEST_CFG = configmanager.get_config_wrapper(fpath=SSPL_TEST_CONFIG_PATH)
PROV_CFG = configmanager.get_config_wrapper(fpath=PROV_TEST_CONFIG_PATH)
HA_CFG = configmanager.get_config_wrapper(fpath=HA_TEST_CONFIG_PATH)
PROV_TEST_CFG = configmanager.get_config_wrapper(fpath=PROV_CONFIG_PATH)
DTM_CFG = configmanager.get_config_wrapper(fpath=DTM_TEST_CFG_PATH)
DEPLOY_CFG = configmanager.get_config_wrapper(fpath=DEPLOY_TEST_CONFIG_PATH)

DI_CFG = configmanager.get_config_wrapper(fpath=DI_CONFIG_PATH)
DATA_PATH_CFG = configmanager.get_config_wrapper(fpath=DATA_PATH_CONFIG_PATH, target=target)
DURABILITY_CFG = configmanager.get_config_wrapper(fpath=DURABILITY_CFG_PATH)
# Munched configs. These can be used by dot "." operator.

di_cfg = munch.munchify(DI_CFG)
cmn_cfg = munch.munchify(CMN_CFG)
