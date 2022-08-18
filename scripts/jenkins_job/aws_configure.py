#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""
AWS configuration file with access key and secret key
"""
import os
import configparser
import logging
import shutil
from time import perf_counter_ns
from multiprocessing import Process
from commons import pswdmanager
from commons.utils import support_bundle_utils as sb
from commons.utils import system_utils as sysutils
from commons import constants as const
from config import CMN_CFG
from libs.csm.csm_setup import CSMConfigsCheck
from libs.s3.s3_restapi_test_lib import S3AccountOperationsRestAPI

# Global Constants
LOGGER = logging.getLogger(__name__)

config_file = 'scripts/jenkins_job/config.ini'
config = configparser.ConfigParser()
config.read(config_file)
rest_obj = S3AccountOperationsRestAPI()
config_chk = CSMConfigsCheck()

def create_s3_account():
    LOGGER.info("Getting access and secret key for configuring AWS")
    acc_name = "switch_setup_s3acc{}".format(perf_counter_ns())
    acc_email = "switch_setup_s3acc{}@seagate.com".format(perf_counter_ns())
    acc_passwd = pswdmanager.decrypt(config['s3creds']['acc_passwd'])
    resp = rest_obj.create_s3_account(acc_name, acc_email, acc_passwd)
    print("Response for account creation: {}".format(resp))
    access_key = resp[1]["access_key"]
    secret_key = resp[1]["secret_key"]
    with open('s3acc_secrets', 'w') as ptr:
        ptr.write(access_key + ' ' + secret_key)


def test_create_acc_aws_conf():
    LOGGER.info("Getting access and secret key for configuring AWS")
    acc_name = "nightly_s3acc{}".format(perf_counter_ns())
    acc_email = "nightly_s3acc{}@seagate.com".format(perf_counter_ns())
    acc_passwd = pswdmanager.decrypt(config['s3creds']['acc_passwd'])
    resp = rest_obj.create_s3_account(acc_name, acc_email, acc_passwd)
    print("Response for account creation: {}".format(resp))
    access_key = resp[1]["access_key"]
    secret_key = resp[1]["secret_key"]
    endpoint = CMN_CFG["lb"]
    endpoint = "https://{}".format(endpoint)
    s3_engine = CMN_CFG["s3_engine"]
    print("Installing s3 tools")
    if s3_engine == const.S3_ENGINE_RGW: # for RGW
        resp = sysutils.execute_cmd(cmd="make all-rgw --makefile=scripts/s3_tools/Makefile "
                                        "ACCESS={} SECRET={} "
                                        "endpoint={}".format(access_key, secret_key, endpoint))
    else:
        resp = sysutils.execute_cmd(cmd="make all --makefile=scripts/s3_tools/Makefile ACCESS={} "
                                        "SECRET={}".format(access_key, secret_key))
    print("Response for tools install: {}".format(resp))


def test_preboarding():
    """
    Test for verifying csm pre-boarding using restapi
    """
    admin_user = os.getenv(
        'ADMIN_USR', pswdmanager.decrypt(
            config['csmboarding']['username']))
    old_passwd = pswdmanager.decrypt(config['csmboarding']['password'])
    new_passwd = os.getenv('ADMIN_PWD', old_passwd)
    resp = config_chk.preboarding(admin_user, old_passwd, new_passwd)
    assert resp, "Preboarding Failed"


def test_collect_support_bundle_individual_cmds():
    """
    Collect support bundles from various components on all the nodes
    """
    prcs = list()
    bundle_dir = os.path.join(os.getcwd(), "support_bundle")
    if os.path.exists(bundle_dir):
        LOGGER.info("Removing existing directory %s", bundle_dir)
        shutil.rmtree(bundle_dir)
    os.mkdir(bundle_dir)
    for node in CMN_CFG["nodes"]:
        remote_dir = os.path.join("/root", node["host"], "")
        proc = Process(
            target=sb.create_support_bundle_individual_cmd,
            args=(
                node["hostname"],
                node["username"],
                node["password"],
                remote_dir,
                bundle_dir))
        proc.start()
        prcs.append(proc)

    for prc in prcs:
        prc.join()


def test_collect_support_bundle_single_cmd():
    """
    Collect support bundles from various components using single support bundle cmd
    """
    bundle_dir = os.path.join(os.getcwd(), "support_bundle")
    bundle_name = "sanity"
    if os.path.exists(bundle_dir):
        LOGGER.info("Removing existing directory %s", bundle_dir)
        shutil.rmtree(bundle_dir)
    os.mkdir(bundle_dir)
    if CMN_CFG["product_family"] == "LC":
        sb.collect_support_bundle_k8s(local_dir_path=bundle_dir)
    else:
        sb.create_support_bundle_single_cmd(bundle_dir, bundle_name)

def test_collect_crash_files():
    """
    Collect crash files from existing locations.
    """
    crash_dir = os.path.join(os.getcwd(), "crash_files")
    if os.path.exists(crash_dir):
        LOGGER.info("Removing existing directory %s", crash_dir)
        shutil.rmtree(crash_dir)
    os.mkdir(crash_dir)
    if CMN_CFG["product_family"] == "LC":
        sb.collect_crash_files_k8s(local_dir_path=crash_dir)
    else:
        sb.collect_crash_files(crash_dir)


if __name__ == '__main':
    create_s3_account()
