# -*- coding: utf-8 -*-
# !/usr/bin/python
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
""" Data Integrity framework base file.
"""
import logging
import boto3
from botocore.exceptions import ClientError
from logging.handlers import SysLogHandler
from config import DATA_PATH_CFG
from commons.utils import assert_utils
from commons.utils.system_utils import run_local_cmd
from commons.params import S3_ENDPOINT

LOGGER = logging.getLogger(__name__)


class SysLogger:
    FACILITY = {'kern': 0, 'user': 1, 'mail': 2, 'daemon': 3,
                'auth': 4, 'syslog': 5, 'lpr': 6, 'news': 7,
                'uucp': 8, 'cron': 9, 'authpriv': 10, 'ftp': 11,
                'local0': 16, 'local1': 17, 'local2': 18, 'local3': 19,
                'local4': 20, 'local5': 21, 'local6': 22, 'local7': 23,
                }

    LEVEL = {'emerg': 0, 'alert': 1, 'crit': 2, 'err': 3,
             'warning': 4, 'notice': 5, 'info': 6, 'debug': 7
             }

    @classmethod
    def log(cls, logger, address, msg):
        host, port = address
        logger.addHandler(SysLogHandler(address=(host, port), facility=cls.FACILITY.get('user')))
        logging.info(f"{msg}")


def init_s3_connections(users):
    """Init s3 connections pool for a multiple  user"""
    s3_objects = dict()

    for user, keys in users.items():
        user_name = user
        access_key = keys["accesskey"]
        secret_key = keys["secretkey"]
        s3_objects[user_name] = _init_s3_conn(access_key, secret_key, user_name)
    return s3_objects


def init_s3_conn(user_name, keys, nworkers):
    """Init s3 connections pool for a single user"""
    access_key = keys[0]
    secret_key = keys[1]
    pool = list()
    for ix in range(nworkers + 1):
        pool.append(_init_s3_conn(access_key, secret_key, user_name))
        LOGGER.info('Initialized s3 connection %s', str(ix))
    return pool


def _init_s3_conn(access_key, secret_key, user_name):
    """Protected function to create a single s3 resource."""
    s3 = None
    try:
        s3 = boto3.resource('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                            endpoint_url=S3_ENDPOINT)
        LOGGER.info(f's3 resource created for user {user_name}')
    except (ClientError, Exception) as exc:
        LOGGER.error(
            f'could not create s3 object for user {user_name} with '
            f'access key {access_key} secret key {secret_key} exception:{exc}')
    return s3


def run_s3bench(test_conf, bucket, keys):
    """
    concurrent users operations using S3bench
    yum install go
    go get github.com/igneous-systems/s3bench
    git clone https://github.com/igneous-systems/s3bench at /root/go/src/
    :param keys: access key and secret key
    :param test_conf: test config
    :type test_conf: dict
    :param bucket: already created bucket name
    :type bucket: str
    :return: None
    """
    LOGGER.info("concurrent users TC using S3bench")
    access_key, secret_key = keys
    cmd = DATA_PATH_CFG["data_path"]["s3bench_cmd"].format(access_key,
                                                           secret_key,
                                                           bucket,
                                                           DATA_PATH_CFG["data_path"]["endpoint"],
                                                           DATA_PATH_CFG["data_path"]["clients"],
                                                           DATA_PATH_CFG["data_path"]["samples"],
                                                           test_conf["obj_prefix"],
                                                           DATA_PATH_CFG["data_path"]["obj_size"])
    resp = run_local_cmd(cmd)
    LOGGER.debug(resp)
    assert_utils.assert_true(resp[0], resp[1])
    assert_utils.assert_is_not_none(resp[1], resp)
    resp_split = resp[1].split("\\n")
    resp_filtered = [i for i in resp_split if 'Number of Errors' in i]
    for response in resp_filtered:
        LOGGER.debug(response)
        assert_utils.assert_equal(int(response.split(":")[1].strip()), 0, response)
