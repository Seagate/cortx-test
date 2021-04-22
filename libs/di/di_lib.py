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
import time
import sys
import logging
import hashlib
from pathlib import Path
from fabric import Connection
from fabric import Config
from fabric import ThreadingGroup, SerialGroup
from libs.di.di_mgmt_ops import ManagementOPs
from libs.di import di_base
from commons.exceptions import TestException
from commons import params
from commons.utils import assert_utils

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
        raise TestException('User dict is empty')
    try:
        user_name = user_dict.get('name')
        access_key = user_dict.get('access_key')
        secret_key = user_dict.get('secret_key')
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        buckets = [user_name + '-' + timestamp + '-bucket' + str(i) for i in range(nbuckets)]
        s3 = di_base._init_s3_conn(access_key=access_key, secret_key=secret_key,
                                   user_name=user_name)
        if not s3:
            raise TestException('S3 resource could not be created')
        for bucket in buckets:
            try:

                s3.create_bucket(Bucket=bucket)
            except Exception as e:
                LOGGER.info(f'could not create create bucket {bucket} exception:{e}')
            else:
                LOGGER.info(f'create bucket {bucket} Done')

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
