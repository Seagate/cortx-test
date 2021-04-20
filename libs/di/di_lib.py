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
import queue
import threading
import time
import os
import sys
import logging
import socket
import paramiko
import yaml
import traceback
import re
import base64
import datetime
import json
import gevent
import boto3

from fabric import Connection
from fabric import Config
from fabric import ThreadingGroup, SerialGroup
from fabric import runners
from fabric.exceptions import GroupException
from threading import Thread
from gevent.pool import Group
from gevent.queue import Queue, Empty
from gevent.queue import JoinableQueue
from gevent.lock import BoundedSemaphore
from libs.di import di_params
from libs.di.di_mgmt_ops import ManagementOPs
from commons.exceptions import TestException
from commons import params
from commons.utils import assert_utils
IAM_UTYPE = 1
S3_ACC_UTYPE = 2
s3connections = list()

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

        try:
            s3 = boto3.resource('s3', aws_access_key_id=access_key,
                                aws_secret_access_key=secret_key,
                                endpoint_url=params.S3_ENDPOINT)
        except Exception as e:
            LOGGER.info(f'could not create s3 object for '
                        f'user {user_name} with access key {access_key} '
                        f'secret key {secret_key} exception:{e}')
            return

        for bucket in buckets:
            try:
                file1 = open(di_params.DATASET_FILES,"r")
                obj_file_paths = file1.readlines()
            except Exception as e:
                LOGGER.info(f'could not access file {di_params.DATASET_FILES} exception:{e}')
                return
            else:
                LOGGER.info(f'able to access file {di_params.DATASET_FILES}')

            try:

                s3.create_bucket(Bucket=bucket)
            except Exception as e:
                LOGGER.info(f'could not create create bucket {bucket} exception:{e}')
            else:
                LOGGER.info(f'create bucket {bucket} Done')

    except Exception as fault:
        LOGGER.error(f"An error {fault} occurred in creating users of type {utype}")
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


if __name__ == '__main__':
    pass
