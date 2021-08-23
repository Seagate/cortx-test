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
from time import perf_counter_ns, time, sleep
from commons import pswdmanager
from commons.helpers.node_helper import Node
from commons.utils import  config_utils
from config import CMN_CFG
from libs.csm.csm_setup import CSMConfigsCheck
from libs.s3.cortxcli_test_lib import CortxCliTestLib
from multiprocessing import Process

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


def test_preboarding():
    """
    Test for verifying csm pre-boarding using restapi
    """
    admin_user = os.getenv('ADMIN_USR', pswdmanager.decrypt(config['csmboarding']['username']))
    old_passwd = pswdmanager.decrypt(config['csmboarding']['password'])
    new_passwd = os.getenv('ADMIN_PWD', old_passwd)
    resp = config_chk.preboarding(admin_user, old_passwd, new_passwd)
    assert resp, "Preboarding Failed"


def create_support_bundle(node, username, password, remote_dir, local_dir):
    """
    Collect support bundles from various components
    :param node: Node hostname on which support bundle to be generated
    :param username: username of the node
    :param password: password of the node
    :param remote_dir: Directory on node where support bundles will be collected
    :param local_dir: Local directory where support bundles will be copied
    :return: None
    """
    node_obj = Node(hostname=node, username=username, password=password)
    if node_obj.path_exists(remote_dir):
        node_obj.remove_dir(remote_dir)
    node_obj.create_dir_sftp(remote_dir)
    LOGGER.info("Generating support bundle on node %s", node)
    node_obj.execute_cmd("/usr/bin/sspl_bundle_generate support_bundle {}".format(remote_dir))
    node_obj.execute_cmd("sh /opt/seagate/cortx/s3/scripts/s3_bundle_generate.sh support_bundle {}".format(remote_dir))
    node_obj.execute_cmd("/usr/bin/manifest_support_bundle support_bundle {}".format(remote_dir))
    node_obj.execute_cmd("/opt/seagate/cortx/motr/libexec/m0reportbug-bundler support_bundle {}".format(remote_dir))
    node_obj.execute_cmd("/opt/seagate/cortx/hare/bin/hare_setup support_bundle support_bundle {}".format(remote_dir))
    node_obj.execute_cmd("/opt/seagate/cortx/provisioner/cli/provisioner-bundler support_bundle {}".format(remote_dir))
    node_obj.execute_cmd("cortx support_bundle create support_bundle {}".format(remote_dir))
    node_obj.execute_cmd("cortxcli csm_bundle_generate csm support_bundle {}".format(remote_dir))

    LOGGER.info("Copying generated support bundle to local")
    dir_list = node_obj.list_dir(remote_dir)
    for dir in dir_list:
        files = node_obj.list_dir(os.path.join(remote_dir, dir))
        for file in files:
            if not os.path.exists(local_dir):
                os.mkdir(local_dir)
            if file.endswith(".tar.gz") or file.endswith(".tar.xz") or file.endswith(".tar"):
                remote_file = os.path.join(remote_dir, dir, file)
                local_file = os.path.join(local_dir, file)
                LOGGER.debug("copying {}".format(remote_file))
                node_obj.copy_file_to_local(remote_file, local_file)


def create_support_bundle_single_cmd(remote_dir, local_dir, bundle_name):
    """
    Collect support bundles from various components using single support bundle cmd
    :param remote_dir: Directory on node where support bundles will be collected
    :param local_dir: Local directory where support bundles will be copied
    :param bundle_name: Name of bundle
    :return: None
    """
    primary_node_obj = Node(hostname=CMN_CFG["nodes"][0]["hostname"], username=CMN_CFG["nodes"][0]["username"], password=CMN_CFG["nodes"][0]["password"])
    shared_path = "glusterfs://{}".format(remote_dir)
    remote_dir = os.path.join(remote_dir, "support_bundle")
    if primary_node_obj.path_exists(remote_dir):
        primary_node_obj.remove_dir(remote_dir)
    primary_node_obj.create_dir_sftp(remote_dir)

    LOGGER.info("Updating shared path for support bundle %s", shared_path)
    cortx_conf = "/etc/cortx/cortx.conf"
    temp_conf = os.path.join(os.getcwd(), "cortx.conf")
    primary_node_obj.copy_file_to_local(cortx_conf, temp_conf)
    conf = config_utils.read_content_json(temp_conf)
    conf["support"]["shared_path"] = shared_path
    config_utils.create_content_json(temp_conf, conf)
    for node in CMN_CFG["nodes"]:
        node_obj = Node(node["hostname"], node["username"], node["password"])
        node_obj.copy_file_to_remote(temp_conf, cortx_conf)

    LOGGER.info("Starting support bundle creation")
    primary_node_obj.execute_cmd("support_bundle generate {}".format(bundle_name))
    start_time = time()
    timeout = 1800
    bundle_id = primary_node_obj.list_dir(remote_dir)[0]
    LOGGER.info(bundle_id)
    bundle_dir = os.path.join(remote_dir, bundle_id)
    success_msg = "Support bundle generation completed."
    while timeout > time() - start_time:
        sleep(180)
        status = primary_node_obj.execute_cmd("support_bundle get_status -b {}".format(bundle_id))
        if status.count(success_msg) == len(CMN_CFG["nodes"]):
            sb_tar_file = "".join([bundle_id, ".tar"])
            remote_sb_path = os.path.join(remote_dir, sb_tar_file)
            local_sb_path = os.path.join(local_dir, sb_tar_file)
            tar_sb_cmd = "tar -cvf {} {}".format(remote_sb_path, bundle_dir)
            primary_node_obj.execute_cmd(tar_sb_cmd)
            primary_node_obj.copy_file_to_local(remote_sb_path, local_sb_path)
            break
    else:
        LOGGER.error("Timeout while generating support bundle")


def test_collect_support_bundle():
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
        local_dir = os.path.join(bundle_dir, node["host"], "")
        p = Process(target=create_support_bundle, args=(node["hostname"], node["username"], node["password"], remote_dir, local_dir))
        p.start()
        prcs.append(p)

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
    remote_dir = "/var/lib/seagate/cortx/provisioner/shared"
    create_support_bundle_single_cmd(remote_dir, bundle_dir, bundle_name)


if __name__ == '__main':
    create_s3_account()
