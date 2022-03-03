#!/usr/bin/python
# -*- coding: utf-8 -*-
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

"""
AWS configuration file with access key and secret key
"""
import os
import configparser
import logging
import shutil
import subprocess
from time import perf_counter_ns
from multiprocessing import Process
from commons import pswdmanager
from commons.utils import support_bundle_utils as sb
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


def run_cmd(cmd):
    """
    Execute bash commands on the host
    :param str cmd: command to be executed
    :return: command output
    :rtype: string
    """
    print("Executing command: {}".format(cmd))
    proc = subprocess.Popen(cmd, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    result = str(proc.communicate())
    return result


def configure_awscli(access_key, secret_key):
    """
    Method to configure awscli on the host
    :return: None
    """
    run_cmd("python3.7 -m pip install awscli -i https://pypi.python.org/simple/.")
    run_cmd("python3.7 -m pip install awscli-plugin-endpoint -i https://pypi.python.org/simple/.")
    aws_configure = "aws configure"
    local_s3_cert_path = "/etc/ssl/stx-s3-clients/s3/ca.crt"
    proc = subprocess.Popen(aws_configure, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)

    proc.stdin.write(str.encode(access_key) + b"\n")
    proc.stdin.flush()
    proc.stdin.write(str.encode(secret_key) + b"\n")
    proc.stdin.flush()
    proc.stdin.write(b"US\n")
    proc.stdin.flush()
    proc.stdin.write(b"json\n")
    proc.stdin.flush()

    result = str(proc.communicate())
    print("output = {}".format(result))
    run_cmd("aws configure set plugins.endpoint awscli_plugin_endpoint")
    run_cmd("aws configure set s3.endpoint_url https://s3.seagate.com")
    run_cmd("aws configure set s3api.endpoint_url https://s3.seagate.com")
    run_cmd("aws configure set ca_bundle {}".format(local_s3_cert_path))


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
    s3_engine = CMN_CFG["s3_engine"]
    print("Installing s3 tools")
    if s3_engine == 2: # for RGW
        resp = run_cmd("make all-rgw --makefile=scripts/s3_tools/Makefile ACCESS={} SECRET={} "
                   "endpoint={}".format(access_key, secret_key, endpoint))
    else:
        resp = run_cmd("make all --makefile=scripts/s3_tools/Makefile ACCESS={} SECRET={} "
                       "endpoint={}".format(access_key, secret_key, endpoint))
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
