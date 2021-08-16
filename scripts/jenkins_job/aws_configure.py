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
import subprocess
from time import perf_counter_ns
from commons import pswdmanager
from libs.csm.csm_setup import CSMConfigsCheck
from libs.s3.cortxcli_test_lib import CortxCliTestLib

# Global Constants
LOGGER = logging.getLogger(__name__)

config_file = 'scripts/jenkins_job/config.ini'
config = configparser.ConfigParser()
config.read(config_file)
cortx_obj = CortxCliTestLib()
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


def test_create_acc_aws_conf():
    LOGGER.info("Getting access and secret key for configuring AWS")
    acc_name = "nightly_s3acc{}".format(perf_counter_ns())
    acc_email = "nightly_s3acc{}@seagate.com".format(perf_counter_ns())
    acc_passwd = pswdmanager.decrypt(config['s3creds']['acc_passwd'])
    resp = cortx_obj.create_account_cortxcli(acc_name, acc_email, acc_passwd)
    print("Response for account creation: {}".format(resp))
    access_key = resp[1]["access_key"]
    secret_key = resp[1]["secret_key"]
    configure_awscli(access_key, secret_key)
    cortx_obj.close_connection()


def create_s3_account():
    LOGGER.info("Getting access and secret key for configuring AWS")
    acc_name = "switch_setup_s3acc{}".format(perf_counter_ns())
    acc_email = "switch_setup_s3acc{}@seagate.com".format(perf_counter_ns())
    acc_passwd = pswdmanager.decrypt(config['s3creds']['acc_passwd'])
    resp = cortx_obj.create_account_cortxcli(acc_name, acc_email, acc_passwd)
    print("Response for account creation: {}".format(resp))
    access_key = resp[1]["access_key"]
    secret_key = resp[1]["secret_key"]
    cortx_obj.close_connection()
    with open('s3acc_secrets', 'w') as ptr:
        ptr.write(access_key + ' ' + secret_key)


def test_preboarding():
    """
    Test for verifying csm pre-boarding using restapi
    """
    admin_user = os.getenv('ADMIN_USR', pswdmanager.decrypt(config['csmboarding']['username']))
    old_passwd = pswdmanager.decrypt(config['csmboarding']['password'])
    new_passwd = os.getenv('ADMIN_PWD', old_passwd)
    resp = config_chk.preboarding(admin_user, old_passwd, new_passwd)
    assert resp, "Preboarding Failed"


if __name__ == '__main':
    create_s3_account()
