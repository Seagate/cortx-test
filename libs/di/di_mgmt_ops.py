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

#!/usr/bin/env python3
import os
import random
import sys
import queue
import threading
import logging
import csv
import fcntl
import hashlib
import multiprocessing as mp
import boto3
import re
import json
import time
import errno
from pathlib import Path
from string import Template
from jsonschema import validate
from eos_test.s3 import iam_test_lib
from eos_test.s3 import iam_core_lib
from eos_test.di import di_lib
from eos_test.di.di_lib import init_loghandler
#from eos_test.csm.rest.csm_rest_core_lib import RestClient
#from eos_test.csm.rest import constants as const

CM_CFG = di_lib.read_yaml("config/common_config.yaml")
S3_CFG = di_lib.read_yaml("config/s3/s3_config.yaml")
DI_CFG = di_lib.read_yaml("config/di/di_config.yaml")

logger = logging.getLogger(__name__)


users = {"user1":["AKIAmtbCV5W4ShaEpS_vkf6ctg","GDYm8JSyRHHd5WSWKJ5ATg9nPE8f9hbuMNI2KRpm"],
         "user2":["AKIAz8u06dSFTjSpOYyNAjQKDQ","fOmgD2CeJkLyox59ipab58FI5i5a+WZNfVsiGIKo"],
         "user3":["AKIAAXDoYwa5TK6YvWblkeKh1Q","9TsqOZRXH11X+6zn5556BBABc9jcAM0yCZqbj24q"],
         "user4":["AKIA8SJZDP5KSxNZDtQNj5x4dA","7oXQ5KWFaK6CxeX6sH1jx2A7I7Dzkl1iNaUbSiHI"],
         "user5":["AKIAwisYTwy_QQSmcPQOzxfsjw","VCB6n+/4LgvhAXVo4gUikt66hg7iCpSdOVsNdSvW"],
         "user6":["AKIAuIhQYM6VSGCx6VG01yUfBA","N+Xl68Orwurc++aZBdS7dbXKvri+R/3vR0bAnJTj"],
         "user7":["AKIAW9MuqGhiTNOCjhjyvgNq8g","wfRSzvww+8GWyOoksIy/W8/wQAcsRHsvlz109use"],
         "user8":["AKIAaZ4tTS4ZSAANFsaNzsKySw","fd/1ZYhnESGCw4DIw3W/WA+xU3HhG5eQl/pEEsrQ"],
         "user9":["AKIA7meXEoemSpSNkQwyJ0KNDQ","kiQ1HiIwnWMq0EdeGQfW4ixB/wjseKKt1Q6k9xs9"],
         "user10":["AKIA4F9Z3gLsTBeFqAzqXgG5Xw","teFxABFnyVOjpwSPhuvEP90w14MngM3vLmnpPD7X"]}


class ManagementOPs(object):

    email_suffix = "@seagate.com"
    user_prefix = 'tuser'

    @classmethod
    def create_iam_users(cls, nusers=10):
        """
        Creates s3 iam users to upload DI test data. This function uses S3IamCli
        to create account and iam user
        :param nusers: number of iam users to create
        :return:
        """
        user = 's3' + cls.user_prefix + str(random.randint(100, 1000))
        email = user + cls.email_suffix
        # Create S3 account user
        cli = iam_core_lib.S3IamCli()
        resp = cli.create_account_s3iamcli(email,
                                           DI_CFG['ldap_username'],
                                           DI_CFG['ldap_passwd'])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]

        # iam_cert_path = S3_CFG['iam_cert_path']
        # endpoint_url = S3_CFG['iam_url']
        # cli = iam_core_lib.IamLib(access_key, secret_key, endpoint_url, iam_cert_path)

        users = {"{}{}".format(cls.user_prefix, i): tuple() for i in range(1, nusers + 1)}

        # Create IAM users
        for i in range(1, nusers + 1):
            udict = dict()
            user = cls.user_prefix + str(i)
            email = user + cls.email_suffix
            udict.update({'emailid': email})
            cli.create_user_using_s3iamcli(user, access_key, secret_key)
            resp = cli.create_access_key(user)
            user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
            user_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
            users[user] = user_access_key, user_secret_key, email
        return users

    @classmethod
    def create_account_users(cls, nusers=10):
        """
        Creates s3 account users to upload DI test data. This function uses S3IamCli
        to create users.
        :param nusers: number of users to create
        :return:
        """
        users = {"{}{}".format(cls.user_prefix, i): dict() for i in range(1, nusers + 1)}

        for i in range(1, nusers + 1):
            udict = dict()
            user = cls.user_prefix + str(i)
            email = user + cls.email_suffix
            udict.update({'user_name': user})
            udict.update({'emailid': email})
            # Create S3 account
            cli = iam_test_lib.IamTestLib()
            try:
                resp = cli.create_account_s3iamcli(user, email,
                                                   DI_CFG['ldap_username'],
                                                   DI_CFG['ldap_passwd'])

            except Exception as ctpe:
                # check if s3 account already exists and get keys
                ret = cli.list_accounts_s3iamcli(DI_CFG['ldap_username'], DI_CFG['ldap_passwd'])
                accounts = ret[1]
                for account in accounts:
                    if account.get('AccountName') == user:
                        udict.update({'accesskey': account["access_key"]})
                        udict.update({'secretkey': account["secret_key"]})
            else:
                udict.update({'accesskey': resp[1]["access_key"]})
                udict.update({'secretkey': resp[1]["secret_key"]})

            users.update({user: udict})
        return users


    @classmethod
    def crud_csm_users(cls):
        """
        Perform continuous cruds on cached users. Cache will be typically a hashmap or lru cache
        :return:
        """
        pass

    @classmethod
    def crud_iam_users(cls):
        """
        Perform continuous cruds on cached iam users. These users and buckets should be
        different from those used for IOs in DI runs.
        :return:
        """
        pass

    @classmethod
    def crud_buckets(cls):
        """
        Perform continuous cruds on cached buckets of users. These users and buckets should be
        different from those used for IOs in DI runs.
        :return:
        """
        pass

    @classmethod
    def crud_policy(cls):
        """
        Perform continuous cruds on cached policies. These policies should be
        different from those used for IOs in DI runs.
        :return:
        """
        pass

    @classmethod
    def safe_crud_account_users(cls):
        """
        Perform continuous cruds on cached s3 account users used for IOs.
        :return:
        """
        pass

    @classmethod
    def safe_crud_iam_users(cls):
        """
        Perform continuous cruds on cached iam users. These users and buckets should be
        same as those used for IOs in DI runs.
        :return:
        """
        pass

    @classmethod
    def safe_crud_buckets(cls):
        """
        Perform continuous cruds on cached buckets which are used for IOs in DI test runs.
        :return:
        """

    @classmethod
    def safe_crud_policy(cls):
        """
        Perform continuous cruds on cached policies belonging to buckets used for
        IOs in DI test runs
        :return:
        """
        pass

    @classmethod
    def create_users_and_buckets(cls, maxusers=100, maxbuckets=100):
        """
        Creates random users and random buckets for each user. This api
        caches users and their buckets for continuous crud operations on
        them.
        :param maxusers:
        :param maxbuckets:
        :return:
        """
        users = dict()

        # Create S3 account
        cli = iam_core_lib.S3IamCli()
        resp = cli.create_account_s3iamcli(CM_CFG['emailid'],
                                           CM_CFG['ldap_username'],
                                           CM_CFG['ldap_passwd'])
        access_key = resp[1]["access_key"]
        secret_key = resp[1]["secret_key"]

        """Creating Connection"""
        iam = boto3.client('iam', verify=S3_CFG['iam_cert_path'],
                           aws_access_key_id=access_key,
                           aws_secret_access_key=secret_key,
                           endpoint_url=S3_CFG['iam_url'])

        users = {"user{}".format(i): tuple() for i in range(1, maxusers + 1)}
        buckets = {"user{}".format(i): list() for i in range(1, maxbuckets + 1)}
        # Create IAM users
        for i in range(1, maxusers + 1):
            cli.create_user_using_s3iamcli("user{}".format(i), access_key, secret_key)
            resp = cli.create_access_key("user{}".format(i))
            user_access_key = resp[1]["AccessKey"]["AccessKeyId"]
            user_secret_key = resp[1]["AccessKey"]["SecretAccessKey"]
            users["user{}".format(i)] = user_access_key, user_secret_key
        # create 10 buckets per user
        for k in users:
            bkts = [cli.create_bucket('{}bucket{}'.format(k, i)) for i in range(1, maxbuckets + 1)]
            buckets[k] = bkts


