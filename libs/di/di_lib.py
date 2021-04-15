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


IAM_UTYPE = 1
S3_ACC_UTYPE = 2
s3connections = list()

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

diusers = {"user1":["AKIAvVRBu_qhRc2eOpMJwXOBjQ","cT1tEIKo8SztEBpqHF5OroZkqda7kpph7DFQfZAz"],
         "user2":["AKIAwxH4rqnwRqmXoX5HzyV8xA","C5dBsRcL73wLyLEZr858nymh2h70abFvxINNSkRa"],
         "user3":["AKIAql9gSmpcQnGyuHbiziTzng","Ow6mYLCji2nBMCrMZDzG7/u2tu9WX0FjFI0ihOlG"],
         "user4":["AKIA3iswZrw0R7mKtHJZizImKg","TcvKJRfJnYS8H4f53B2g0urn/8+7uFG44vStPiwt"],
         "user5":["AKIAZxC27C5kSRKomFywnCUE_A","OLkz+6+eyV1IsXA2HBx6wtmRdihW0o/wktoCLCZf"],
         "user6":["AKIA1s420Uw3RnWuRH_jU5YL9g","JUq17VoBHInxd2Oftec592v/nVuNXlT185KsPc/N"],
         "user7":["AKIAvzZoU96eQPucwPCYvD7kWw","D7A+mEI/hu+0EAe02dZYbPZFD9BcmBPvdB5yaRRy"],
         "user8":["AKIAdLhZ3gGSSCW3Ul1ECrjq2g","OKGEDDWS4D+ohrOf0w8nYcgCXGZ0GE2WTVL6zAOC"],
         "user9":["AKIA5Hx6gvLNTCuOAc7k6MYQ0w","+xx/Y6IJWDQEGLzclUIwNVeSa3DfX09jGbbhi+M+"],
         "user10":["AKIARmsEWm0NTvi2NJ5HD4sIzw","TlIjEvDS2Q4LoEXbESqhyJ/CdC531f5Za4Bbwcmy"]}


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
                                endpoint_url="https://s3.seagate.com")
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


class Workers(object):
    """ A thread pool for I/O bound tasks """
    def wStartWorkers(self, nworkers=NWORKERS, func=None):
        self.w_workQ = WorkQ(func, nworkers)     # queue.Queue()
        self.w_workers = []
        for i in range(nworkers):
            w = Thread(target=self.wWorker)
            w.start()
            self.w_workers.append(w)

    def wWorker(self):
        while True:
            wq = self.w_workQ.get()
            if wq is None:
                self.w_workQ.task_done()
                break
            wi = wq.get()
            wq.func(wi)
            wq.task_done()
            self.w_workQ.task_done()

    def wEnque(self, item):
        self.w_workQ.put(item)

    def wEndWorkers(self):
        for i in range(len(self.w_workers)):
            self.w_workQ.put(None)
        self.w_workQ.join()
        logger.info('shutdown all workers')
        logger.info('Joining all threads to main thread')
        for i in range(len(self.w_workers)):
            self.w_workers[i].join()


class YamlError(Exception):
    def __init__(self, name, message=""):
        self.message = message
        self.name = name
        super().__init__(self.message)

    def __str__(self):
        return '{} has an invalid yaml syntax'.format(self.name)


def read_yaml(fpath):
    """Read yaml file and return dictionary/list of the content"""
    cwd = os.getcwd()
    fpath = os.path.join(cwd, fpath)
    if os.path.isfile(fpath):
        with open(fpath) as fin:
            try:
                data = yaml.safe_load(fin)
            except yaml.YAMLError as exc:
                try:
                    data = yaml.load(fin.read(), Loader=yaml.Loader)
                except yaml.YAMLError as exc:
                    err_msg = "Failed to parse: {}\n{}".format(fpath, str(exc))
                    raise YamlError(fpath, 'YAML file syntax error')

    else:
        err_msg = "Specified file doesn't exist: {}".format(fpath)
        raise YamlError(fpath, 'YAML file missing')
    return data


class NodeOps():

    def init_Connection(self, host, user, password):
        self.connection = Connection(host, user=user, connect_kwargs={'password': password},
                                      config=Config(overrides={'sudo': {'password': password}}))

        assert 'Linux' in self.connection.run('uname -s', pty=False).stdout,\
            "Node {} not reachable".format(host)
        self.ctg = SerialGroup.from_connections(self.connections)

    def start_service(self, c, services):
        command = "systemctl start "
        for svc in services:
            csts = self.status(c, svc)
            if csts[c.host] != "Running":
                coutput = c.run(command + svc, pty=False)
                logger.info("Starting: %s " % c.host)

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
            logger.info(c.host, csts[c.host])

    def run_command(self, conn, cmd, options=None):
        conn.run(cmd, pty=False)




def create_iter_content_json(home, data):
    pth = os.path.join(home, di_params.USER_JSON)
    with open(pth, 'w') as outfile:
        json.dump(data, outfile, ensure_ascii=False)


def read_iter_content_json(home, file=di_params.USER_JSON):
    pth = os.path.join(home, file)
    data = None
    with open(pth, 'rb') as json_file:
        data = json.loads(json_file.read())
    return data


def sigint_handler(signum, frame):
    print('SIGINT handler called with signal ', signum)
    logger.info('Signal handler called with signal {}, exiting process'.format(signum))
    sys.exit(0)


class GWorkQ(JoinableQueue):
    def __init__(self, func, maxsize):
        self.lock_req = maxsize != 0
        self.func = func
        self.semaphore = BoundedSemaphore(maxsize)
        JoinableQueue.__init__(self, maxsize)

    def put(self, item):
        if self.lock_req:
            self.semaphore.acquire()
        JoinableQueue.put(self, item)

    def task_done(self):
        if self.lock_req:
            self.semaphore.release()
        JoinableQueue.task_done(self)


class GWorker:
    """ A greenlet pool for I/O bound tasks """

    def __init__(self, ngreenlets=32):
        self.w_workQ = Queue(maxsize=ngreenlets)     # Gevent Queue or GWorkQ with dummy function
        self.qlen = ngreenlets

    def start(self):
        def run_user(user):
            """
            Main function for User greenlet. It's important that this function takes the user
            instance as an argument, since we use greenlet_instance.args[0] to retrieve a reference to the
            User instance.
            """
            user.gWorker()

        gevent.joinall([
            gevent.spawn(self.boss),
            gevent.spawn(run_user, self),
            gevent.spawn(run_user, self),
            gevent.spawn(run_user, self),
            gevent.spawn(run_user, self),
            gevent.spawn(run_user, self),
            gevent.spawn(run_user, self),
            gevent.spawn(run_user, self),
            gevent.spawn(run_user, self),
            ])

    # todo remove from lib
    def boss(self):
        """
        Boss will wait to hand out work until a individual worker is
        free since the maxsize of the task queue is 3.
        """
        for i in range(1,10):
            self.w_workQ.put(i)
        print('Assigned all work in iteration 1')

        for i in range(10,100):
            self.w_workQ.put(i)
        print('Assigned all work in iteration 2')

    def gWorker(self):
        try:
            while True:
                #wq = self.w_workQ.get(1)
                # if wq is None:
                #     self.w_workQ.task_done()
                #     break
                #wi = wq.get()
                #wq.func(wi)
                wi = self.w_workQ.get(1)
                print('Worker got task %s' % (wi))
                #wq.task_done()
                #self.w_workQ.task_done()
                gevent.sleep(0)
        except Empty:
            print('Bye!')
            logger.info('shutdown gworker')

    def wEnque(self, item):
        self.w_workQ.put(item)

    def wEndWorkers(self):
        for i in range(1):
            self.w_workQ.put(None)
        self.w_workQ.join()
        logger.info('shutdown greenlet worker')


if __name__ == '__main__':
    w = GWorker()
    w.start()

