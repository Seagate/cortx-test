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

"""Data Integrity test library"""
import os
import datetime
import time
import sys
import logging
import hashlib
import random
from time import perf_counter_ns
from hashlib import md5
from pathlib import Path
from fabric import Connection
from fabric import Config
from fabric import ThreadingGroup, SerialGroup
from paramiko.ssh_exception import SSHException
from commons.exceptions import CortxTestException
from commons.constants import MB
from commons.constants import POD_NAME_PREFIX, PROD_FAMILY_LC, PROD_TYPE_K8S
from commons import params
from commons.helpers.pods_helper import LogicalNode
from commons.utils import assert_utils
from commons import constants as const
from commons.helpers.node_helper import Node
from config import cmn_cfg
from libs.di.di_mgmt_ops import ManagementOPs
from libs.di.di_base import _init_s3_conn
from libs.di.file_formats import all_extensions

IAM_UTYPE = 1
S3_ACC_UTYPE = 2
s3connections = list()
CKSUM_ALGO_1 = 'md5'
CKSUM_ALGO_2 = 'sha1'

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


def create_users(utype=S3_ACC_UTYPE, nusers=10):
    """Creates account users with default user name prefix.
    user_prefix should be supported later.
    """
    try:
        if utype == S3_ACC_UTYPE:
            users = ManagementOPs.create_account_users(nusers=nusers)
        elif utype == IAM_UTYPE:
            users = ManagementOPs.create_iam_users(nusers=nusers)
        return users
    except Exception as fault:
        LOGGER.error(f"An error {fault} occurred in creating users of type {utype}")
        raise fault


def create_buckets(user_dict, s3_prefix, nbuckets):
    """Create buckets with default name prefix."""
    if not user_dict:
        raise CortxTestException('User dict is empty')
    try:
        user_name = user_dict.get('name')
        access_key = user_dict.get('access_key')
        secret_key = user_dict.get('secret_key')
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        buckets = [user_name + '-' + timestamp + '-bucket' + str(i) for i in range(nbuckets)]
        s3 = _init_s3_conn(access_key=access_key, secret_key=secret_key,
                                   user_name=user_name)
        if not s3:
            raise CortxTestException('S3 resource could not be created')
        for bucket in buckets:
            try:

                s3.create_bucket(Bucket=bucket)
            except Exception as e:
                LOGGER.info(f'could not create create bucket {bucket} exception:{e}')
            else:
                LOGGER.info(f'create bucket {bucket} Done with {s3_prefix}')

    except Exception as fault:
        LOGGER.error(f"An error {fault} occurred in creating buckets.")
        raise fault


class NodeOps:

    def __init__(self):
        self.connection = None
        self.ctg = None

    def init_Connection(self, host: str, user: str, password: str) -> str:
        self.connection = Connection(host, user=user, connect_kwargs={'password': password},
                                     config=Config(overrides={'sudo': {'password': password}}))

        assert_utils.assert_true('Linux' in self.connection.run('uname -s', pty=False).stdout,
                                 "Node {} not reachable".format(host))
        self.ctg = SerialGroup.from_connections(self.connections)

    def start_service(self, c, services):
        command = "systemctl start "
        for svc in services:
            csts = self.status(c, svc)
            if csts[c.host] != "Running":
                coutput = c.run(command + svc, pty=False)
                LOGGER.info("Starting: %s " % c.host)

    def status(self, cn, svc_list):
        for svc in svc_list:
            coutput = cn.run("hostname && ps -ef | grep " + svc, hide="both")
            msg = {cn.host + svc: "Stopped"}
            if svc in coutput.stdout:
                msg[cn.host + svc] = "Running"
        return msg

    def stop_service(self, c, services):
        core_command = "sudo systemctl stop"  # stop services
        for svc in services:
            coutput = c.run(core_command + svc)
            time.sleep(2)
            csts = self.status(c, services)
            LOGGER.info(c.host, csts[c.host])

    def run_command(self, conn, cmd, options=None):
        conn.run(cmd, pty=False)


def sigint_handler(signum, frame):
    print('SIGINT handler called with signal ', signum)
    LOGGER.info('Signal handler called with signal {}, exiting process'.format(signum))
    sys.exit(0)


def read_file(filepath, size=0, algo=CKSUM_ALGO_1):
    """Find checksum of file as per algo."""
    if not size:
        sz = Path(filepath).stat().st_size

    read_sz = 8192  # blk sz
    c_sum = ''
    if algo == CKSUM_ALGO_1:
        file_hash = hashlib.md5()
    elif algo == CKSUM_ALGO_2:
        file_hash = hashlib.sha1()

    with open(filepath, 'rb') as fp:
        if sz < read_sz:
            buf = fp.read(sz)
        else:
            buf = fp.read(read_sz)
        while buf:
            file_hash.update(buf)
            buf = fp.read(read_sz)
        c_sum = file_hash.hexdigest()
    return c_sum.strip()  # not required. Recheck.


def copy_local_to_s3_config(self, **kwargs) -> tuple:
    """
    Copy files to remote server
    # :param host: IP of the host.
    # :param user: user name of the host.
    # :param password: password for the user.
    # :param backup_path: backup_path.
    :return: True/False, response.
    """
    host = kwargs.get("host", self.host)
    user = kwargs.get("username", self.user)
    pwd = kwargs.get("password", self.pwd)
    backup_path = kwargs.get("backup_path", const.LOCAL_S3_CONFIG)
    try:
        nobj = Node(hostname=host, username=user, password=pwd)
        status, resp = nobj.copy_file_to_remote(backup_path, const.S3_CONFIG)
        if not status:
            return status, resp
        if os.path.exists(backup_path):
            os.remove(backup_path)
        nobj.disconnect()

        return status
    except (SSHException, OSError) as error:
        LOGGER.error(
            "Error in %s: %s", copy_local_to_s3_config, error)
        return False, error


def get_random_bucket_name():
    """
    Function will return a random bucket name.
    This function is not thread safe or does not work for nano sec granularity.
    """
    return "di-test-bkt-{}".format(datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f'))


def get_random_object_name():
    """
    Function will return a random object name.
    This function is not thread safe or does not work for nano sec granularity.
    """
    return "di-test-obj-{}".format(datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f'))


def get_random_account_name():
    """
    Function will return a random account name.
    This function is not thread safe or does not work for nano sec granularity.
    """
    return "data_durability_acc{}".format(perf_counter_ns())


def get_email_id(account_name: str):
    """
    Function will return an email id with account_name
    This function is not thread safe or does not work for nano sec granularity.
    """
    return "{}@seagate.com".format(account_name)


def get_random_file_name():
    """
    Function will return a random filename name.
    This function is not thread safe or does not work for nano sec granularity.
    """
    ext = random.sample(all_extensions, 1)[0]
    return "data_durability{}{}".format(perf_counter_ns(), ext)


def calc_checksum(buf: object):
    """
    calc checksum from buffer / bytes.
    :param buf: byte/buffer stream
    :param hash_algo: md5 or sha1
    :return:
    """
    file_hash = md5()  # nosec
    file_hash.update(buf)
    return file_hash.hexdigest()


def kill_s3_process_in_k8s(master_node: LogicalNode, data_pods: list, namespace):
    """
    kill s3 processes in given list of pods
    """
    for pod in data_pods:
        s3_containers = master_node.get_container_of_pod(pod_name=pod,
                                                         container_prefix="cortx-s3-0")
        for s3_container in s3_containers:
            cmd = "pkill -9 s3server"
            LOGGER.info("cmd : %s", cmd)
            retry_count = 2
            while retry_count > 0:
                try:
                    master_node.send_k8s_cmd(operation="exec", pod=pod, namespace=namespace,
                                             command_suffix=f"-c {s3_container} -- {cmd}",
                                             decode=True)
                    break
                except IOError as err:
                    LOGGER.info("err: %s ", err)
                    retry_count -= 1
            if retry_count <= 0:
                return False
    return True


def check_s3_process_in_k8s(master_node: LogicalNode, data_pods: list, namespace):
    """
    check s3 process in given list of pods
    """
    for pod in data_pods:
        s3_containers = master_node.get_container_of_pod(pod_name=pod,
                                                         container_prefix="cortx-s3-0")
        for s3_container in s3_containers:
            counter = 0
            resp = None
            while counter < 5:
                try:
                    cmd = "pgrep s3server 2> /dev/null"
                    resp = master_node.send_k8s_cmd(operation="exec", pod=pod, namespace=namespace,
                                                    command_suffix=f"-c {s3_container} -- "
                                                                   f"{cmd}", decode=True)
                    LOGGER.info("resp : %s", resp)
                    LOGGER.info("counter is : %s", counter)
                    if resp:
                        LOGGER.info("Breaking while loop for container %s of pod %s",
                                    s3_container, pod)
                        break
                except IOError as err:
                    LOGGER.info("err: %s ", err)
                    counter = counter + 1
                    time.sleep(30)
            if not resp:
                return False
    return True


def restart_s3_processes_k8s():
    """
    restart s3 processes for k8s based setup
    """
    if cmn_cfg["product_family"] == PROD_FAMILY_LC and cmn_cfg["product_type"] == PROD_TYPE_K8S:
        nodes = cmn_cfg["nodes"]
        master_node_list = list()
        for node in nodes:
            if node["node_type"].lower() == "master":
                node_obj = LogicalNode(hostname=node["hostname"], username=node["username"],
                                       password=node["password"])
                master_node_list.append(node_obj)
        master_node = master_node_list[0]
        LOGGER.info(master_node)
        data_pods = master_node.get_all_pods(POD_NAME_PREFIX)
        LOGGER.info(data_pods)
        kill_status = kill_s3_process_in_k8s(master_node=master_node, data_pods=data_pods,
                                             namespace=const.NAMESPACE)
        if kill_status:
            status = check_s3_process_in_k8s(master_node=master_node, data_pods=data_pods,
                                             namespace=const.NAMESPACE)
            return status
    return False


def get_random_ranges(size: int, greater_than_unit_size: bool = False):
    """
    will return random range
    :param size: in bytes
    :param greater_than_unit_size: true/false
    if true, range will be returned between 1 MB and rest of size
    """
    start = 0
    end = size
    if greater_than_unit_size:
        start = 1 * MB
    first = random.SystemRandom().randint(start, end)
    second = random.SystemRandom().randint(start, end)
    if second < first:
        return second, first
    return first, second
